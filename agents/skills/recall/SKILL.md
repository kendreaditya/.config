---
name: recall
description: "Stop losing what you worked out with Claude. Captures the decisions and insights from a session as active-recall cards, then quizzes you on them on a spaced schedule so they stick. Use when the user says they forget what they discussed with Claude, asks to remember or retain something long-term, wants to review or be quizzed on past work, asks what they decided about X weeks ago, or finishes a session with a hard-won conclusion worth keeping. Triggers: 'I forget what we discussed', 'help me remember this', 'quiz me', 'review my cards', 'what's due', 'what did we decide about X', 'capture this', 'recall', 'I keep relearning this'. NOT for facts the repo already records, and NOT a note dump — every card must be answerable from memory."
---

# recall

The problem this solves is **not** a storage problem. Notes, transcripts, and memory
files already exist; 417 Claude Code sessions sat on this machine unread. The problem is
that nothing ever asks the user to *retrieve* anything. This skill is the retrieval loop.

**Retrieval, not rereading.** Rereading a clear explanation feels like learning and mostly
isn't (Koriat & Bjork's illusion of competence). Retrieval practice and spacing are the only
two techniques Dunlosky et al. (2013) rated *high utility* out of ten. So the unit of work
here is a question the user answers from memory — never a summary they skim.
See `references/evidence.md` before making a strong claim about any of this.

```bash
R=~/.config/agents/skills/recall/scripts/recall.py   # stdlib python3, no deps
python3 $R due            # questions due today (answers hidden — this matters)
python3 $R add --q ... --a ...
python3 $R grade <id> 0-5
python3 $R show <id>      # answer + review history
python3 $R stats          # store health, weakest cards
python3 $R list --tag x   # also: edit, rm
```

Cards live one-JSON-per-file in `~/.claude/recall/cards/`, scheduled by SM-2. Readable and
git-diffable without this script.

---

## Mode 1 — Capture (end of substantive work)

Trigger: the user says capture/remember this, or a session just produced a real conclusion
(a decision with a rationale, a non-obvious root cause, a constraint discovered the hard way).

**Capture is cheap; bad cards are expensive.** Three good cards beat fifteen mediocre ones —
every card is a future obligation to review it.

1. **Propose 1–5 candidate cards, do not write them yet.** Show them as `Q → A` one-liners
   and ask which to keep. The user editing your question is itself elaborative work.
2. **What earns a card** — the durable, transferable thing:
   - a decision *and why*, including the option rejected and what would reverse it
   - a root cause that took real work to find
   - a constraint or gotcha that will bite again ("tsh must be version-pinned because…")
   - a mental model of how a system actually behaves
3. **What does not** — anything the repo, git history, or `--help` already answers; syntax
   that is one lookup away; facts only relevant to this week. If it's a stable fact about the
   user or the project, that's the **memory** system, not a card. If it's a repeatable
   procedure, that's **`learn`** → a skill. Say so and route it there.
4. **Write questions that force generation, not recognition.**
   - Bad: *"What did we decide about the cluster auth?"* — cued recall of a whole topic.
   - Good: *"tsh login fails with 'No proxy address specified' — what is the cause and the fix?"*
   - Prefer "why" and "what breaks if" over "what is". One retrievable fact per card.
   - Answers stay short — 1–3 sentences. A paragraph means the card should be split.
5. Tag by domain (`claude-code`, `k8s`, `python`) and set `--source` to the file, PR, or
   session id so a lapse can be traced back to the real thing.

Cards start due immediately: the first review is the encoding.

## Mode 2 — Review (the part that actually works)

Trigger: `recall`, "quiz me", "what's due", or the user opening a session with review in mind.

Run `python3 $R due --limit 7`. Cap it around seven; a wall of cards gets abandoned, and an
abandoned queue is the failure mode that kills every system like this.

For each card, in order:

1. **Ask the question. Stop. Do not continue in the same message.** Wait for a real answer.
   This is the whole intervention — if you show the answer alongside the question you have
   built a rereading tool and thrown away the effect.
2. When they answer, `show` the card and compare honestly. Name what they missed. If they
   were right for the wrong reason, say so — that's a lapse in the model even if the answer
   was right.
3. **Grade it yourself**, then `grade <id> <n>`:
   - **5** correct, immediate, complete · **4** correct with hesitation or a small gap
   - **3** essentially right but effortful or partial · **2** partial, needed a hint
   - **1** wrong but recognized the answer · **0** blank
   Do not inflate. A generous 4 on a shaky answer schedules it a month out and loses it.
   The user asking "was that right?" is not the same as being right.
4. **On a lapse (0–2), rebuild rather than reread.** Open the `source`, re-derive the answer
   with them, and consider whether the card is too big — a card that lapses twice is usually
   two cards.
5. Never reveal the answer before the attempt. If they say "just tell me", give a hint first
   (the pretesting effect means even a wrong guess helps retention of that item); tell them
   on the second ask.

Close a review with one line of `stats`, not a summary of what they got right.

## Mode 3 — Retrospective capture (the 417-session backlog)

Trigger: "what did we decide about X", "I know I worked this out before", or a first-time
setup with an empty store.

The user's history is already searchable — this skill does not re-implement that:
- `parlai search "<query>"` — across ChatGPT/Claude/Gemini/Codex/Claude Code
- `session-logs` — jq over local session JSONL
- `memex` — their notes, Drive, mail, messages

Find the thing, answer the question that was asked, then say: *"want a card for this so you
stop relearning it?"* A repeated lookup is the strongest possible signal a card is warranted.

## Keeping the loop alive

The store is worthless if `due` is never run. Establish exactly one trigger and stop there:

- **A `SessionStart` hook** that prints the due count as context (~5 min of setup, and the
  only option that needs no memory on the user's part). SessionStart stdout becomes context
  Claude can see — so a hook echoing `recall: 6 cards due` is enough for Claude to offer a
  review. Keep it fast and never let it block: append `|| true`.
- **A Desktop scheduled task** — runs daily on this machine with local file access.
- **`/loop`** — session-scoped only; fine for a single sitting, gone tomorrow.

Do not build more than one. Two reminders for the same queue is how it gets muted.

## Honest limits — say these out loud if asked

Spacing and retrieval are extremely well established for discrete factual material. Applying
them to engineering judgment via a personal card store is **extrapolation**: the mechanism is
solid, the specific practice is under-tested, and the causal AI-forgetting literature is
young, largely correlational, and partly preprint. This skill is a reasonable bet, not a
proven protocol. It is also a real ongoing cost — if the user stops reviewing, delete the
store rather than let it rot into guilt.
