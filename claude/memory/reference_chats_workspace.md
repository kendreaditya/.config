---
name: Chats Workspace
description: AI conversation export pipeline at ~/workspace/chats/ — extracts prompts from Google AI Studio and Claude, combines into single file
type: reference
---

AI conversation history export tools live at `/Users/kendreaditya/workspace/chats/`.

**Pipeline (3 sequential Python scripts):**
1. `extract_aistudio_prompts.py` — walks `aistudio/` dir (828 JSON files from Google AI Studio export) → `aistudio_prompts.json`
2. `extract_claude_prompts.py` — reads `claude/conversations.json` (Claude export, uses ijson for streaming) → `claude_prompts.json`
3. `combine_prompts.py` — merges both sources, prefixes `[AISTUDIO]`/`[CLAUDE]`, truncates long prompts (first+last 600 words), estimates tokens (4 chars/token), writes `combined_prompts.txt` with stats header

**Output files in ~/Downloads/:**
- `AI_Conversation_Questions_Mar2024-Jun2025.md` — 2,423 prompts (1,451 Claude + 972 AI Studio)
- `AI_Conversation_Questions_Mar2024-Oct2025.md` — 4,849 prompts (1,451 Claude + 3,398 AI Studio)

Both generated 2026-02-16. The Oct2025 file is a superset (more AI Studio data from Jun–Oct 2025).

**Dependency:** `ijson>=3.2.0`
