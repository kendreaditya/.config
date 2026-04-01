---
name: Subagent Security Constraints
description: Security rules for subagents — no keychain access, no broad credential dumps, explicit instructions required
type: feedback
---

When spawning subagents, explicitly instruct them on security boundaries. Subagents don't inherit the parent's feedback memories, so constraints must be stated in the prompt.

**Rules to always include in subagent prompts when credentials are involved:**
1. Never access macOS Keychain directly (`security find-generic-password`, `security dump-keychain`, etc.)
2. Use app-level token export commands only (e.g., `gog auth tokens export`)
3. Clean up any temporary credential files after use
4. Never log or print full tokens/secrets

**Why:** On 2026-03-31, a subagent ran `security dump-keychain` to get a Google OAuth token, which would have broadly listed keychain metadata. User flagged this as a huge security risk. The safe path is `gog auth tokens export` → exchange refresh token via OAuth endpoint.

**How to apply:** Any time a subagent needs API credentials, include explicit security instructions in the agent prompt. Don't assume subagents will follow the parent's safety constraints.
