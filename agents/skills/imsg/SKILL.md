---
name: imsg
description: iMessage/SMS CLI for listing chats, history, and sending messages via Messages.app.
homepage: https://imsg.to
metadata:
  {
    "openclaw":
      {
        "emoji": "📨",
        "os": ["darwin"],
        "requires": { "bins": ["imsg"] },
        "install":
          [
            {
              "id": "brew",
              "kind": "brew",
              "formula": "steipete/tap/imsg",
              "bins": ["imsg"],
              "label": "Install imsg (brew)",
            },
          ],
      },
  }
---

# imsg

Use `imsg` to read and send iMessage/SMS via macOS Messages.app.

## When to Use

✅ **USE this skill when:**

- User explicitly asks to send iMessage or SMS
- Reading iMessage conversation history
- Checking recent Messages.app chats
- Sending to phone numbers or Apple IDs

## When NOT to Use

❌ **DON'T use this skill when:**

- Telegram messages → use `message` tool with `channel:telegram`
- Signal messages → use Signal channel if configured
- WhatsApp messages → use WhatsApp channel if configured
- Discord messages → use `message` tool with `channel:discord`
- Slack messages → use `slack` skill
- Group chat management (adding/removing members) → not supported
- Bulk/mass messaging → always confirm with user first
- Replying in current conversation → just reply normally (OpenClaw routes automatically)

## Requirements

- macOS with Messages.app signed in
- Full Disk Access for terminal
- Automation permission for Messages.app (for sending)

## Common Commands

### List Chats

```bash
imsg chats --limit 10 --json
```

### View History

```bash
# By chat ID
imsg history --chat-id 1 --limit 20 --json

# With attachments info
imsg history --chat-id 1 --limit 20 --attachments --json
```

### Watch for New Messages

```bash
imsg watch --chat-id 1 --attachments
```

### Send Messages

```bash
# Text only
imsg send --to "+14155551212" --text "Hello!"

# With attachment
imsg send --to "+14155551212" --text "Check this out" --file /path/to/image.jpg

# Specify service
imsg send --to "+14155551212" --text "Hi" --service imessage
imsg send --to "+14155551212" --text "Hi" --service sms
```

## Service Options

- `--service imessage` — Force iMessage (requires recipient has iMessage)
- `--service sms` — Force SMS (green bubble)
- `--service auto` — Let Messages.app decide (default)

## Safety Rules

1. **Always confirm recipient and message content** before sending
2. **Never send to unknown numbers** without explicit user approval
3. **Be careful with attachments** — confirm file path exists
4. **Rate limit yourself** — don't spam

## Example Workflow

User: "Text mom that I'll be late"

```bash
# 1. Find mom's chat
imsg chats --limit 20 --json | jq '.[] | select(.displayName | contains("Mom"))'

# 2. Confirm with user
# "Found Mom at +1555123456. Send 'I'll be late' via iMessage?"

# 3. Send after confirmation
imsg send --to "+1555123456" --text "I'll be late"
```

## Capability Limits — When to Use Manual SQL Instead

`imsg` reads from `~/Library/Messages/chat.db` (same source), but requires a numeric `--chat-id` from `imsg chats`. It **cannot**:

- Search by contact email/phone to find chat IDs — must be looked up via SQL first
- Merge multiple handles (email + phone) for the same person into one export
- Export all messages to a file (needs shell redirection + manual loop over chat IDs)
- Resolve raw phone numbers to contact names in output
- Access messages not linked via `chat_message_join` (some synced messages are handle-only)

Note: `imsg chats` output is newline-delimited JSON (NDJSON), not a JSON array — parse line by line.

**Decision guide:**

| Task | Tool |
|---|---|
| Read recent messages, watch live | `imsg history / watch` |
| Send a message | `imsg send` |
| Find which group chats a contact is in | SQL (`handle` + `chat_handle_join`) |
| Bulk export all messages to file | Manual SQL + Python |
| Merge phone + email handles for one contact | Manual SQL |
| Get reactions as structured data | `imsg` (`reactions` field in JSON output) |

## Manual SQL Approach (bulk export / contact search)

**Database:** `~/Library/Messages/chat.db`

**Key tables:** `handle` (contact identifiers), `message` (texts + blobs), `chat_handle_join`, `chat_message_join`, `attachment`

```bash
# Find all handles (phone/email) for a contact
sqlite3 ~/Library/Messages/chat.db \
  "SELECT ROWID, id, service FROM handle WHERE id LIKE '%search_term%';"

# Find which chats a contact participates in
sqlite3 ~/Library/Messages/chat.db "
  SELECT c.ROWID, c.chat_identifier, c.display_name, COUNT(cmj.message_id) as msgs
  FROM chat c
  JOIN chat_handle_join chj ON c.ROWID = chj.chat_id
  JOIN handle h ON chj.handle_id = h.ROWID
  LEFT JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
  WHERE h.id IN ('+1XXXXXXXXXX', 'email@example.com')
  GROUP BY c.ROWID ORDER BY msgs DESC;"
```

**Decoding NSAttributedString blobs** — messages where `text` is NULL store content as binary blobs:

```python
import sqlite3, os, json
from datetime import datetime, timezone, timedelta

APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)

def decode_blob(blob):
    """Extract plain text from NSAttributedString streamtyped blob."""
    if not blob: return None
    raw = bytes(blob)
    marker = b'\x01\x94\x84\x01\x2b'
    idx = raw.find(marker)
    if idx == -1: return None
    pos = idx + len(marker)
    lb = raw[pos]; pos += 1
    if lb == 0x81:   length = (raw[pos] << 8) | raw[pos+1]; pos += 2
    elif lb == 0x82: length = int.from_bytes(raw[pos:pos+4], 'big'); pos += 4
    else:            length = lb
    return raw[pos:pos+length].decode('utf-8', errors='replace')

def apple_ts(ts):
    if not ts: return ""
    return (APPLE_EPOCH + timedelta(seconds=ts/1_000_000_000)).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

# Export all messages from multiple handles (phone + email) merged and sorted
DB = os.path.expanduser("~/Library/Messages/chat.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

HANDLES = ["+1XXXXXXXXXX", "email@example.com"]
placeholders = ",".join("?" * len(HANDLES))
cur.execute(f"""
    SELECT m.date, m.is_from_me, m.text, m.attributedBody, h.id, m.service
    FROM message m JOIN handle h ON m.handle_id = h.ROWID
    WHERE h.id IN ({placeholders})
    ORDER BY m.date ASC
""", HANDLES)

messages = []
for row in cur.fetchall():
    text = row["text"] or decode_blob(row["attributedBody"]) or ""
    messages.append({
        "date": apple_ts(row["date"]),
        "from": "Me" if row["is_from_me"] else row["id"],
        "text": text,
        "service": row["service"]
    })

with open(os.path.expanduser("~/Desktop/imessage_export.json"), "w") as f:
    json.dump(messages, f, ensure_ascii=False, indent=2)
```
