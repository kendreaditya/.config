---
name: wacli
description: Send WhatsApp messages to other people or search/sync WhatsApp history via the wacli CLI (not for normal user chats).
homepage: https://wacli.sh
metadata:
  {
    "openclaw":
      {
        "emoji": "📱",
        "requires": { "bins": ["wacli"] },
        "install":
          [
            {
              "id": "brew",
              "kind": "brew",
              "formula": "steipete/tap/wacli",
              "bins": ["wacli"],
              "label": "Install wacli (brew)",
            },
            {
              "id": "go",
              "kind": "go",
              "module": "github.com/steipete/wacli/cmd/wacli@latest",
              "bins": ["wacli"],
              "label": "Install wacli (go)",
            },
          ],
      },
  }
---

# wacli

Use `wacli` only when the user explicitly asks you to message someone else on WhatsApp or when they ask to sync/search WhatsApp history.
Do NOT use `wacli` for normal user chats; OpenClaw routes WhatsApp conversations automatically.
If the user is chatting with you on WhatsApp, you should not reach for this tool unless they ask you to contact a third party.

## Safety

- Require explicit recipient + message text.
- Confirm recipient + message before sending.
- If anything is ambiguous, ask a clarifying question.

## Global flags

Apply to every subcommand:

- `--json` — machine-readable output (use this when parsing).
- `--store <dir>` — store directory (default `$WACLI_STORE_DIR` or `~/.wacli`).
- `--timeout <duration>` — command timeout (default `5m`, non-sync only).

## Auth + sync

- `wacli auth` — QR login + bootstrap sync. Flags: `--follow` (keep syncing after auth), `--download-media`, `--idle-exit <duration>` (default 30s).
- `wacli auth status` — show auth status.
- `wacli auth logout` — invalidate session.
- `wacli sync` — sync messages (requires prior auth, never shows QR). `--follow` is **default true**; pass `--once` to sync until idle and exit. Other flags: `--download-media`, `--refresh-contacts`, `--refresh-groups`, `--max-reconnect <duration>` (default 5m, 0=unlimited), `--idle-exit <duration>`.
- `wacli doctor` — diagnostics for store/auth/search. `--connect` to test live WhatsApp connection.
- `wacli version` — print version.

## Chats

- `wacli chats list --limit 20 --query "name or number"` — list chats from local DB.
- `wacli chats show --jid <jid>` — show one chat.

## Messages

**Important:** `search` requires a non-empty query. To list messages from a chat without a search term, use `messages list`.

- `wacli messages list --chat <jid> --limit 30` — list messages (no query needed). Also supports `--after YYYY-MM-DD` and `--before YYYY-MM-DD`.
- `wacli messages search "<query>" --limit 20 [--chat <jid>] [--from <senderJID>] [--type image|video|audio|document] [--after YYYY-MM-DD] [--before YYYY-MM-DD]` — FTS5 if available, else LIKE. Query is required.
- `wacli messages show --chat <jid> --id <msgID>` — show one message.
- `wacli messages context --chat <jid> --id <msgID> --before 5 --after 5` — show surrounding messages.

## Send

- Text: `wacli send text --to "+14155551212" --message "Hello! Are you free at 3pm?"`
- Group: `wacli send text --to "1234567890-123456789@g.us" --message "Running 5 min late."`
- File: `wacli send file --to "+14155551212" --file /path/agenda.pdf --caption "Agenda" [--filename name.pdf] [--mime application/pdf]`

## History backfill

- `wacli history backfill --chat <jid> --requests 2 --count 50 [--wait 1m] [--idle-exit 5s]` — request older messages from primary device. Best-effort; requires phone online.

## Media

- `wacli media download --chat <jid> --id <msgID> [--output <path-or-dir>]` — download media for a message.

## Contacts

- `wacli contacts search "<query>" --limit 50` — search synced contact metadata.
- `wacli contacts show --jid <jid>` — show one contact.
- `wacli contacts refresh` — import contacts from whatsmeow store into local DB.
- `wacli contacts alias set --jid <jid> --alias "<name>"` / `wacli contacts alias rm --jid <jid>` — local aliases.
- `wacli contacts tags add --jid <jid> --tag "<tag>"` / `wacli contacts tags rm --jid <jid> --tag "<tag>"` — local tags.

## Groups

- `wacli groups list --limit 50 --query "name"` — list known groups (run sync first).
- `wacli groups info --jid <groupJID>` — fetch live info, update local DB.
- `wacli groups refresh` — fetch joined groups (live) into local DB.
- `wacli groups rename --jid <groupJID> --name "<new name>"`.
- `wacli groups join --code <invite-code>` — join via invite link code.
- `wacli groups leave --jid <groupJID>`.
- `wacli groups invite link get --jid <groupJID>` / `wacli groups invite link revoke --jid <groupJID>`.
- `wacli groups participants add|remove|promote|demote --jid <groupJID> --user <phone-or-jid>` (`--user` is repeatable).

## Notes

- JIDs: direct chats look like `<number>@s.whatsapp.net`; groups look like `<id>@g.us`. Use `wacli chats list` or `wacli groups list` to find them.
- Backfill requires your phone online; results are best-effort.
- WhatsApp CLI is not needed for routine user chats — it's for messaging other people.
