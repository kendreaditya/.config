---
name: No Keychain Access
description: Never access macOS Keychain directly — use app-level token export commands instead
type: feedback
---

Never use `security find-generic-password`, `security dump-keychain`, or any direct macOS Keychain commands to extract tokens or credentials. This is a huge security risk.

**Why:** Subagent tried to read OAuth tokens directly from Keychain to make API calls. The `dump-keychain` command is especially dangerous as it broadly lists keychain metadata. User flagged this as a serious security violation.

**How to apply:** When you need an access token for an API (e.g., Google Docs API), always use the app's own export mechanism (e.g., `gog auth tokens export` → exchange refresh token via OAuth endpoint). Never bypass the app layer to read secrets directly from the OS keychain. This applies to all subagents too — explicitly instruct them not to access the keychain.
