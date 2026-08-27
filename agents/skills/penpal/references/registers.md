# Register Playbooks

Aditya's voice shifts meaningfully across five recipient categories. This file gives a detailed per-category playbook. Load when the register is unclear or when drafting a first-of-its-kind email for a category.

## Distribution in 100-email corpus

| Register | Count | Median words |
|---|---|---|
| Legal | 32 | 110 |
| Recruiter | 25 | 79 |
| Tech company / peer engineer | 19 | 75 |
| Personal | 12 | 103 |
| Meta HR / service / form | 6 | 56 |
| Insurance | 1 | — |

---

## 1. Legal register (attorneys, law firms)

**Length**: ~110 median words. Longer when laying out facts.

**Greeting**: `Hi Name,\n\n` — always Format A (own line).

**Signoff**: `Thank you,\nAditya Kendre\nkendreaditya@gmail.com` — full name + email. Phone on a separate line for intake emails.

**Markers:**
- Numbered attachment lists (`Please find attached:` followed by `1. ... 2. ... 3. ...`)
- No exclamation points
- No emoji
- Moderate em-dash use (13/32)
- Moderate contractions (19/32) — softened but not absent

**Representative quote:**
> "Thanks for confirming. Please find attached: [numbered list]. Please let me know once you've received everything and we can schedule the intake call."

**Negotiation / decline templates specific to this register:**
- `If you don't have capacity for this, I completely understand. Either way, I appreciate the time.`
- `Once I have a sense of [fee structure / scope], happy to proceed.`
- `[Preserving the current offer] is my top priority — that's the outcome I most want to avoid.`
- Pushback-by-clarification: `I also wanted to clarify [X] — on [source A] it sounded like [version A], but on [source B] it sounded like [version B].`

**Close**: `Let me know if you need anything else or what the next steps are.` then `Thanks,\nAditya Kendre\n...` or `Thank you,\nAditya Kendre\n...`.

---

## 2. Recruiter register (talent, cold tech outbound replies)

**Length**: ~79 median words. 2-3 paragraphs typical.

**Greeting**: `Hi Name,\n\n` usually. Format B for follow-up bumps in an active thread.

**Signoff**: `Best,\nAditya` (first name only).

**Markers:**
- Very common opener: `Sorry for the {slow / late / delayed / long} reply!` (always with `!`)
- Structure: apology → named specific compliment → em-dash pivot → process question
- Frequent em-dashes (10/25)
- `What does the process look like?` as the canonical follow-up question

**Representative quotes:**
> "Sorry for the slow reply! I've actually been using Raindrop for a bit now and really like what they're building. Would be open to a chat — what does the process look like?"

> "Sorry for the delayed response! Hotplate sounds like a cool problem — scaling order management for thousands of independent sellers is a genuinely hard engineering challenge. Would be open to learning more, what does the process look like from here?"

**Enthusiasm phrases**: `really cool`, `sounds like a cool problem`, `sounds interesting`, `genuinely hard engineering challenge`, `really stuck with me`.

**Close**: signoff block `Best,\nAditya`.

---

## 3. Tech company / peer engineer register

**Length**: ~75 median words. Often shorter. Fragments allowed in active threads.

**Greeting**: `Hi Name,` (Format A for first reply, Format B/E for active threads). `Hey Name,` if the prior thread uses `Hey`.

**Signoff**: `Best,\nAditya`.

**Markers:**
- Blunt and direct — less em-dash use than recruiter (6/19)
- Pre-emptively answers logistics (location, visa, scheduling) in one sentence
- `Yep`-level casual register accepted
- Heavy technical detail allowed when the recipient is an engineer

**Representative quote:**
> "Yep, SF works for me and I'm a US citizen so no sponsorship needed. Happy to chat with Tenaya, send over a time whenever works!"

> "Hey Joshua, good chatting with you. Aleph sounds really cool, especially the structured financial data + LLM problem. Happy to move forward if there are next steps on your end."

**Close**: `Best,\nAditya` or bare `Aditya` for tight threads.

---

## 4. Personal register (friends, family, community)

**Length**: ~103 median words but bimodal — either very short (`Hey Vishnu, saw you come up on my liknedin - how have you been?`) or narrative/longer.

**Greeting**: `Hey Name,` — this is the only register where `Hey` is the default rather than `Hi`.

**Signoff**: `Thanks!\nAditya` or bare `Aditya`. No last name, no email, no phone.

**Markers:**
- Exclamation points in greetings and enthusiasm
- Emoji tolerated (rare: `😃`, `:)` appear occasionally)
- Narrative lead-in: "Hey X, I came across Y and saw you're..."
- Typos / lowercase tolerated
- `Would love to` as casual connector

**Representative quote:**
> "Hey Allison, I came across the SF Bay Area EA page and saw you're one of the organizers... Would love to check one out and meet some people. Thanks!"

**Close**: `Thanks!\nAditya`, or bare `Aditya`.

---

## 5. Meta HR / service / form register (bureaucratic)

**Length**: ~56 median words. Short and form-like.

**Greeting**: `Hi Name,` or bare `Hi,` when no contact name is known.

**Signoff**: `Thank you,\nAditya Kendre` + employee ID (`Employee #741007`) and/or phone when relevant.

**Markers:**
- No contractions (`I am`, not `I'm`)
- Bulleted asks — one ask per bullet
- Typos/fragments sometimes tolerated because these are quick tickets/forms
- No em-dashes
- Rare exclamation points
- Formal framing: `I am a departing employee...`, `Could you please provide...`

**Representative quote:**
> "I am a departing employee (Employee #741007) with a separation date of April 10, 2026. Could you please provide a report on the status of my equity awards, including: [bullets]"

**Close**: `Thank you,\nAditya Kendre\nEmployee #[id]`.

---

## Signoff fingerprint (strongest single classifier)

The signoff alone reliably identifies the register:

| Signoff | Register |
|---|---|
| `Thank you,\nAditya Kendre\nkendreaditya@gmail.com` + phone | Legal |
| `Best,\nAditya` | Recruiter or tech/peer |
| `Thanks!\nAditya` or bare `Aditya` (no last name) | Personal |
| `Thank you,\nAditya Kendre\nEmployee #[id]` | Meta HR |
| `Thanks,\nAditya` | Acknowledging help (any register) |

## Greeting fingerprint

| Greeting | Register signal |
|---|---|
| `Hey Name,` on own line | Almost exclusively personal |
| `Hi Name,` on own line | Default for everything else |
| Bare `Hi,` (no name) | Legal/HR form-address when no contact name |
| `Hare Krishna Prabhu,` | Specific devotional community |

## Opener fingerprint

| Opener | Register signal |
|---|---|
| `Sorry for the {slow/late/delayed/long} reply!` | Recruiter (60% of first replies) |
| `Hope you're doing well! Just wanted to follow up...` | Recruiter bump |
| `Please find attached: 1. ... 2. ...` | Legal doc drop |
| `I am a departing employee...` | Meta HR |
| `Hey X, saw you [on X] - how have you been?` | Personal |
| `Just submitted / filed / booked...` | Any register, signals status update |

## When to cross-register

Sometimes a single email spans registers (e.g., a lawyer who is also a friend). Default rules:
- When uncertain, use the more formal register
- If the recipient signals their preferred register first (uses emoji, drops greeting, etc.), match theirs
- Cold first contact → always polish register + Format A greeting, regardless of recipient type
