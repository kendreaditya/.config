---
name: LinkedIn multi-profile edge case
description: Some people have multiple LinkedIn profiles — always check alternate profiles before flagging a company mismatch
type: feedback
---

When verifying someone's current employer via LinkedIn, don't assume the first profile found is authoritative. Some people have multiple LinkedIn profiles (e.g., an old one and a current one).

**Why:** Chandru Amarnani had two profiles — `/in/chandruamarnani` (stale, showed Infosys) and `/in/chandru-amarnani-profile` (current, showed Oracle). The sheet was correct but I flagged it as wrong based on the stale profile.

**How to apply:** If the LinkedIn profile data contradicts the sheet, check if there's an alternate profile URL before reporting a mismatch. Also compare the LinkedIn URL stored in the sheet (if any) vs. the one found via search. The sheet's linked URL is likely the authoritative one.
