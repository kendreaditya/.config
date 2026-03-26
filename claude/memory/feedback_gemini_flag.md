---
name: feedback-gemini-y-flag
description: Gemini CLI must always use -y flag when tools or files are involved
type: feedback
---

When using Gemini CLI, always run with `-y` flag if the prompt needs tools or file access.

**Why:** User explicitly requested this on 2026-03-23 — without `-y`, Gemini prompts for confirmation which blocks non-interactive execution.

**How to apply:** Any Gemini CLI invocation that reads files or uses tools should include `-y`. Add this to the Gemini skill if not already present.
