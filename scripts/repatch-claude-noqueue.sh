#!/usr/bin/env bash
#
# repatch-claude-noqueue.sh
#
# Patches the active Claude Code binary IN PLACE so that:
#   1. It does NOT inject mid-turn <system-reminder> attachments into the
#      running turn when the user types a new message. (No "steering" of
#      in-flight turns.)
#   2. It does NOT bundle multiple queued user messages into a single user
#      turn. Each queued message drains one-at-a-time as its own turn.
#
# After running, the standard `claude` launcher (~/.local/bin/claude) uses
# the patched binary directly — no second launcher, no `-noqueue` suffix.
#
# Auto-update flow:
#   When Claude Code auto-updates it writes a NEW versioned binary at a new
#   path and repoints ~/.local/bin/claude → that new versions/<X> file.
#   The new binary is unpatched. Re-run this script after any update to
#   re-apply the patches to the now-current binary.
#
# Backup / reversibility:
#   On first patch of any given versioned binary, the original bytes are
#   saved alongside as <binary>.unpatched. The script is idempotent — if the
#   current binary already has both patches applied, it exits early without
#   re-doing anything. To roll back manually:
#       cp <binary>.unpatched <binary>
#       codesign --force --sign - --preserve-metadata=entitlements <binary>
#   (the original signature can't be restored; ad-hoc is the only option
#   once bytes have been touched).
#
# ──────────────────────────────────────────────────────────────────────────────
# WHY THIS SCRIPT EXISTS
# ──────────────────────────────────────────────────────────────────────────────
#
# Claude Code's default mid-turn message behavior is "soft steer":
#
#   - When you hit Enter while Claude is working on a turn, your message is
#     enqueued (it does NOT abort the turn).
#   - BUT the next time attachments are built for a tool result, the queued
#     message is also rendered into the model's context as a <system-reminder>
#     attachment with the text:
#         "The user sent a new message while you were working: <msg>
#          IMPORTANT: After completing your current task, you MUST address
#          the user's message above. Do not ignore it."
#   - Result: the model often pivots mid-stream because the reminder language
#     is strong, even though the tool itself wasn't aborted.
#
# Separately, when the queue drains between turns:
#
#   - All queued same-mode commands are dequeued together (`dequeueAllMatching`)
#     and delivered as a SINGLE bundled user message.
#   - Result: if you type "another one" three times while Claude is writing,
#     all three become one user turn and Claude returns one combined response
#     instead of three separate ones.
#
# This script kills both behaviors so user input behaves as a pure FIFO queue:
# each message gets its own complete turn, in order, with no mid-flight steer.
#
# ──────────────────────────────────────────────────────────────────────────────
# HOW WE FOUND THE PATCHES
# ──────────────────────────────────────────────────────────────────────────────
#
# 1. The CLI ships as a single Bun-compiled Mach-O binary (~200MB) at
#    ~/.local/share/claude/versions/<version>. The JS bundle is embedded
#    plaintext inside it — you can grep it with `grep -oa <bytes> <file>`.
#
# 2. We had read-only source access at
#    /Users/kendreaditya/workspace/decision-frontier/src — an unpacked tree
#    of the same release (TypeScript source, no build infra). That let us
#    locate the exact functions we wanted to neutralize. The relevant
#    source files are:
#       - src/utils/attachments.ts       (the INLINE_NOTIFICATION_MODES set)
#       - src/utils/messages.ts          (wrapCommandText — the reminder text)
#       - src/utils/queueProcessor.ts    (processQueueIfReady — bundle vs single)
#       - src/utils/handlePromptSubmit.ts (where enqueue is called mid-turn)
#       - src/utils/messageQueueManager.ts (enqueue/dequeue/priority levels)
#
# 3. For each behavior we wanted to kill, we identified a stable byte
#    sequence in the binary corresponding to a literal in the source, then
#    replaced it with a same-length byte sequence that changes the behavior
#    without changing the surrounding code structure. Same-length is critical
#    so we don't shift any offsets in the binary.
#
# 4. After patching, Anthropic's code signature is broken. We re-sign ad-hoc
#    (no developer cert) so macOS will still launch it from the terminal.
#    Gatekeeper is fine for terminal-launched binaries; only quarantined
#    binaries (downloaded via browser) would be blocked.
#
# ──────────────────────────────────────────────────────────────────────────────
# PATCH #1 — disable mid-turn <system-reminder> injection
# ──────────────────────────────────────────────────────────────────────────────
#
# Source location: src/utils/attachments.ts:1044
#
#     // src/utils/attachments.ts
#     const INLINE_NOTIFICATION_MODES = new Set(['prompt', 'task-notification'])
#     ...
#     // queued commands of these modes are emitted as queued_command
#     // attachments on tool results — i.e. visible to the model mid-turn.
#     const filtered = queuedCommands.filter(_ =>
#       INLINE_NOTIFICATION_MODES.has(_.mode),
#     )
#
# The queued-command attachment then gets rendered with the steering language:
#
#     // src/utils/messages.ts:5510 (wrapCommandText)
#     return `The user sent a new message while you were working:
#     ${raw}
#     IMPORTANT: After completing your current task, you MUST address the
#     user's message above. Do not ignore it.`
#
# Modes in PromptInputMode (src/types/textInputTypes.ts:265):
#     'bash' | 'prompt' | 'orphaned-permission' | 'task-notification'
#
# 'prompt' is the mode tag for normal user-typed text (the default when you
# type something and press Enter). 'task-notification' is used by background
# agents reporting back — it's LOAD-BEARING for proactive loops (SleepTool
# wake-up), so we must keep it in the set.
#
# Strategy: rewrite the Set literal so 'prompt' is no longer a member, but
# 'task-notification' still is. The exact bytes in the minified JS:
#
#     OLD:  new Set(["prompt","task-notification"])
#     NEW:  new Set(["__off_","task-notification"])
#
# Both are exactly 39 bytes. "__off_" (6 chars) replaces "prompt" (6 chars),
# preserving the byte count. "__off_" never matches any real PromptInputMode,
# so the Set's `has(_.mode)` returns false for user-typed 'prompt'-mode
# commands and they are never inlined as attachments.
#
# Net effect: user keystrokes still enqueue, but the model never sees them
# mid-turn. They are only delivered as a normal user turn after the current
# turn fully completes.
#
# ──────────────────────────────────────────────────────────────────────────────
# PATCH #2 — disable per-mode queue bundling
# ──────────────────────────────────────────────────────────────────────────────
#
# Source location: src/utils/queueProcessor.ts:52 (processQueueIfReady)
#
#     export function processQueueIfReady({ executeInput }) {
#       const isMainThread = cmd => cmd.agentId === undefined
#       const next = peek(isMainThread)
#       if (!next) return { processed: false }
#       // Slash commands and bash run one at a time (per-command isolation)
#       if (isSlashCommand(next) || next.mode === 'bash') {
#         const cmd = dequeue(isMainThread)!
#         void executeInput([cmd])
#         return { processed: true }
#       }
#       // Everything else (incl. 'prompt') is BUNDLED:
#       const targetMode = next.mode
#       const commands = dequeueAllMatching(
#         cmd => isMainThread(cmd) && !isSlashCommand(cmd) && cmd.mode === targetMode,
#       )
#       if (commands.length === 0) return { processed: false }
#       void executeInput(commands)   // ← one user turn with N commands
#       return { processed: true }
#     }
#
# In the minified binary this function (renamed PFK) looks like:
#
#     function PFK({executeInput:H}){
#       let _=(T)=>T.agentId===void 0,    // isMainThread
#           q=JGH(_);                      // peek(isMainThread)
#       if(!q)return{processed:!1};
#       if(XFK(q)||q.mode==="bash"){       // ← THE CHECK we're flipping
#         let T=tUH(_);                    // dequeue
#         return H([T]),{processed:!0}     // single-item executeInput
#       }
#       let K=q.mode,
#           O=eUH((T)=>_(T)&&!XFK(T)&&T.mode===K);  // dequeueAllMatching
#       if(O.length===0)return{processed:!1};
#       return H(O),{processed:!0}                   // BUNDLED executeInput
#     }
#
# We force every queued command through the single-item branch by making
# the if-condition always true. Trick: replace the string literal "bash"
# with `q.mode` itself, so `q.mode === q.mode` is tautologically true.
#
#     OLD:  XFK(q)||q.mode==="bash"
#     NEW:  XFK(q)||q.mode===q.mode
#
# Both are exactly 23 bytes. After patching, every queued command goes
# through the dequeue() + executeInput([cmd]) branch — one at a time, as its
# own user turn. The bundling drain `dequeueAllMatching` is now unreachable.
#
# Why this specific replacement vs. alternatives:
#
#   - Flipping `===` to `!==` ("==!"bash") would route prompt/orphaned/
#     task-notification through single-item but break BASH mode (which the
#     original explicitly wanted single-item too). Net regression for bash.
#
#   - Replacing "bash" with another 4-char literal would break uniqueness or
#     match nothing (e.g. "prom" is never a real mode → still bundles).
#
#   - `q.mode===q.mode` is the cleanest: always-true, 23 bytes, no regression
#     in bash handling, preserves the type signature of the condition.
#
# Caveat: `task-notification` mode also bundles in the original. After this
# patch, task notifications drain one-at-a-time too. This is benign — each
# notification represents a separate background-agent completion and was
# never required to bundle for correctness, just performance.
#
# ──────────────────────────────────────────────────────────────────────────────
# UNIQUENESS / SAFETY
# ──────────────────────────────────────────────────────────────────────────────
#
# Both target byte sequences are unique in the binary (verified by grep -oac).
# The script aborts if uniqueness ever changes — that would mean Anthropic
# changed the minified naming (XFK, PFK, JGH, tUH, eUH) or the literal,
# and the patch needs to be re-derived against the new source.
#
# To re-derive after a breaking update:
#   1. Look at the new src/utils/queueProcessor.ts and src/utils/attachments.ts
#   2. Find the new minified function names by searching the new binary for
#      distinctive bytes (e.g. ".agentId===void 0" still uniquely fingerprints
#      processQueueIfReady's isMainThread arrow).
#   3. Update the OLD_* / NEW_* byte sequences below.
#
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Resolve the active Claude Code binary ────────────────────────────────────
CLAUDE_LAUNCHER="$HOME/.local/bin/claude"
if [[ ! -L "$CLAUDE_LAUNCHER" ]]; then
  echo "error: $CLAUDE_LAUNCHER is not a symlink — non-standard install layout" >&2
  exit 1
fi

BINARY="$(readlink -f "$CLAUDE_LAUNCHER")"
if [[ ! -f "$BINARY" ]]; then
  echo "error: binary $BINARY does not exist" >&2
  exit 1
fi

VERSION="$(basename "$BINARY")"
BACKUP="${BINARY}.unpatched"

echo "Detected Claude Code version: $VERSION"
echo "  binary:  $BINARY"
echo "  backup:  $BACKUP"
echo

# ── Apply both patches via Python (handles binary safely + idempotency) ──────
/usr/bin/env python3 - "$BINARY" "$BACKUP" <<'PY'
import os, sys, shutil
binary_path, backup_path = sys.argv[1], sys.argv[2]

# Patch #1: disable mid-turn <system-reminder> injection for user input.
# Source: src/utils/attachments.ts:1044 — INLINE_NOTIFICATION_MODES Set.
# Removing 'prompt' from the set means user-typed messages are no longer
# emitted as queued_command attachments mid-turn. The 'task-notification'
# entry is preserved (load-bearing for proactive-loop SleepTool wake-up).
PATCH1_OLD = b'new Set(["prompt","task-notification"])'
PATCH1_NEW = b'new Set(["__off_","task-notification"])'

# Patch #2: disable queue bundling in processQueueIfReady.
# Source: src/utils/queueProcessor.ts:52 — the single-item drain branch is
# gated on `isSlashCommand(next) || next.mode === 'bash'`. Replacing the
# bash check with the tautology `q.mode === q.mode` makes the gate always
# true, forcing every queued command through the single-item dequeue path.
PATCH2_OLD = b'XFK(q)||q.mode==="bash"'
PATCH2_NEW = b'XFK(q)||q.mode===q.mode'

# Patch #3: stop the mid-turn `removeFromQueue` from evicting prompt-mode
# commands that patch #1 prevented from being attached.
#
# Source: src/query.ts:1632 — the streaming loop, right after attachments
# are built for the tool result, runs:
#
#   const consumedCommands = queuedCommandsSnapshot.filter(
#     cmd => cmd.mode === 'prompt' || cmd.mode === 'task-notification',
#   )
#   ...
#   removeFromQueue(consumedCommands)
#
# This is the "consumed = attached" half of the mid-turn drain machinery.
# Its filter is HARDCODED to {'prompt','task-notification'} and assumes
# anything matching was already turned into a queued_command attachment by
# getQueuedCommandAttachments (which uses INLINE_NOTIFICATION_MODES).
#
# Patch #1 broke that invariant: we removed 'prompt' from
# INLINE_NOTIFICATION_MODES (so prompt commands are no longer attached
# mid-turn) but left this filter alone — so prompt commands were still
# being REMOVED from the queue, without ever being delivered. Result: user
# messages typed mid-turn were silently dropped instead of draining
# post-turn via queueProcessor. Symptom: "my whole queue disappeared when
# you ran bash."
#
# Fix: rewrite the filter so it no longer matches 'prompt'. Same trick as
# patch #1 — replace the literal "prompt" with "__off_" (6 chars, never a
# real mode). The 'task-notification' branch is preserved so background
# subagent notifications still get attached AND removed (their original,
# correct behavior).
PATCH3_OLD = b'T_.mode==="prompt"||T_.mode==="task-notification"'
PATCH3_NEW = b'T_.mode==="__off_"||T_.mode==="task-notification"'

PATCHES = [
    ("PATCH #1 INLINE_NOTIFICATION_MODES", PATCH1_OLD, PATCH1_NEW),
    ("PATCH #2 processQueueIfReady",       PATCH2_OLD, PATCH2_NEW),
    ("PATCH #3 query.ts mid-turn remove",  PATCH3_OLD, PATCH3_NEW),
]

for name, old, new in PATCHES:
    if len(old) != len(new):
        sys.exit(f"length mismatch on {name}: {len(old)} vs {len(new)}")

with open(binary_path, "rb") as f:
    data = f.read()

# Idempotency: if both patches are already present, exit early.
already_applied = all(data.count(new) == 1 and data.count(old) == 0
                       for _, old, new in PATCHES)
if already_applied:
    print("[skip] binary already has both patches applied. Nothing to do.")
    sys.exit(0)

# First-time patch: snapshot pristine bytes (only if no backup yet).
if not os.path.exists(backup_path):
    shutil.copy2(binary_path, backup_path)
    print(f"[backup] saved pristine bytes to {backup_path}")
else:
    print(f"[backup] {backup_path} already exists — leaving as-is "
          "(it should be the pristine Anthropic-signed bytes from before "
          "the first patch).")

for name, old, new in PATCHES:
    n_old = data.count(old)
    n_new = data.count(new)
    if n_new == 1 and n_old == 0:
        print(f"  ✓ {name}: already applied, skipping")
        continue
    if n_old != 1:
        sys.exit(
            f"{name}: expected exactly 1 occurrence of {old!r} in the binary, found {n_old}. "
            "The minified naming or literal probably changed in this Claude Code "
            "release. Re-derive the patch against the new src/utils source — see "
            "the 'UNIQUENESS / SAFETY' section at the top of this script."
        )
    data = data.replace(old, new)
    print(f"  ✓ applied {name}")

with open(binary_path, "wb") as f:
    f.write(data)
PY

# ── Re-sign ad-hoc (Anthropic's signature is now invalid) ────────────────────
# `--force` overwrites the existing (now-broken) signature.
# Empty `--sign -` means ad-hoc — no developer identity needed.
# `--preserve-metadata=entitlements` keeps any hardened-runtime entitlements
# that came with the original binary.
echo
echo "Re-signing ad-hoc..."
codesign --force --sign - --preserve-metadata=entitlements "$BINARY" 2>&1

# ── Smoke-test ───────────────────────────────────────────────────────────────
echo
echo "Verifying..."
"$CLAUDE_LAUNCHER" --version
echo
echo "Done. The standard 'claude' command now uses the patched binary."
echo "On the next Claude Code auto-update, re-run this script to re-patch:"
echo "    $0"
