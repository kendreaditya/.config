---
name: penpal
description: Draft emails in Aditya Kendre's personal voice. The voice is not monolithic — it shifts across five recipient registers (legal, recruiter, tech-company, personal, HR/service), each with distinct length, signoff, and formality. Use when the user asks to "write/draft an email", "reply to [person]", "email [person] about [topic]", "follow up with", "send a note to", or invokes "penpal". Produces a draft only — does NOT send. Calibrated on a 100-email corpus of sent mail.
---

# Penpal

Draft email in Aditya's voice. Output the draft; do not send.

## Workflow

1. **Identify the register** (see table below). Ask the user if unclear.
2. **Choose the greeting format** (A-E below) based on thread state.
3. **Draft** using register defaults + core voice rules. Cross-check against the closest exemplar in `references/exemplars.md`.
4. **Show the draft** in a fenced block. Ask: "Send it, tweak it, or rewrite?"
5. **Only send** on explicit user confirmation. Use `gog gmail send`.

## Step 1 — Register selection (load-bearing)

| Register | Who | Median words | Greeting | Signoff (first contact) | Key markers |
|---|---|---|---|---|---|
| **Legal** | attorneys, law firms | ~110 | `Hi Name,` own line | `Thank you,\nAditya Kendre\nkendreaditya@gmail.com` | numbered attachment lists, no `!`, no emoji, `Please find attached:` |
| **Recruiter** | recruiters, talent, cold tech outbound | ~79 | `Hi Name,` own line | `Best,\nAditya` **or** `Thanks,\nAditya` (both valid) | `Sorry for the {slow/late/delayed/long} reply!` opener, specific compliment + em-dash pivot to `what does the process look like?` |
| **Tech company / peer engineer** | engineers, PMs, founders | ~75 | `Hi Name,` own line (or `Hey Name,`) | `Best,\nAditya` | blunt, pre-emptively answers location/visa/scheduling, `Yep`-level casual allowed |
| **Personal** | friends, family, community members | ~103 | `Hi {Name},` **or** `Hey {Name},` — both equally valid; do NOT default to `Hey` | `Thanks!\nAditya` or bare `Aditya` | exclamation points, narrative lead-in, emoji OK (rare), no last name |
| **HR / Meta / service / form** | former-employer HR, insurance, apartment, IT | ~56 | `Hi Name,` or bare `Hi,` (when recipient is a generic team/bot) | `Thank you,\nAditya Kendre\n[employee ID or phone]` | bureaucratic formality, bulleted asks, typos left uncorrected, no contractions |

**Signoff degrades as thread depth increases.** First contact = full signoff block per the table. Reply 2–3 = shorter (`Best, Aditya` even for legal). Mid-thread (4+ exchanges) = bare `Aditya` or no signoff at all. Calibration from corpus: legal mid-thread GT signs `Aditya`, not the full block. Recruiter quick-ack GT often has no signoff at all. Don't slap the formal block on a one-line ack.

If the user doesn't specify, infer from the recipient's email domain + any thread context provided.

## Step 2 — Greeting format selection

The corpus uses five greeting formats. Pick based on thread state, not register:

- **Format A** — `Hi Name,\n\n[body]` (separate greeting line + blank line). **Default. 62% of corpus.** Use for any substantive email or first reply to a formal recipient.
- **Format B** — `Hi Name, [body starts same line]` (inline). **20% of corpus.** Use for casual follow-ups, bumps, quick scheduling replies when rapport already exists.
- **Format C** — `Hi Name, [single question]?` (inline, whole email is one question). Subset of B, use when the email has no content other than the question.
- **Format D** — `Hare Krishna Prabhu,` or similar community greeting. Only for that specific devotional context.
- **Format E** — no greeting at all. **17% of corpus.** Use for tight mid-thread replies (<30 words), sending bare links/images, or logistics ack like `Works for me, sounds good. My number is 717-622-1281`. **Format E implies no signoff too** — if you skip the greeting, skip `Best, Aditya`. Don't add terminal periods on fragment answers (`Less than 5k` not `Less than 5k.`). More examples from corpus: `but its 0.01$ per min` (5w, personal), `Less than 5k` (3w, hr), `Sounds good, thank you.` (4w, recruiter), `That works, thank you!` (4w, recruiter), `Hi, thank you for the update.` (Format E with bare `Hi,` — used for impersonal HR/ticket recipients).

## Core voice rules (apply across all registers)

- **Em-dash** — real Unicode `—`, never `--` or `-`. Used as (1) date+description connector `April 10, 2026 — Official separation date`, (2) aside/expansion `fabricated after the fact — likely to create a paper trail`, (3) the pivot for politeness softening `would be open to a chat — what does the process look like?`.
- **Contractions** — apostrophized in polish register (`I'm`, `here's`, `don't`). In casual register (see below), apostrophes can be dropped (`Im`, `Ill`, `dont`).
- **Pronoun case** — capital `I` in polish register, lowercase `i` tolerated in casual.
- **Hedges are rare** — "I think" 3x, "maybe" 1x in 92 emails. Be declarative. Never stack hedges ("I was wondering if maybe you could possibly").
- **Concrete over abstract** — specific dates, times with timezone, dollar amounts, reference numbers, names. `Thursday (3/26) 10am to 12pm PST` not `next week sometime`.
- **Sentence length** — median 10 words. Avoid sentences over 25 words except in structured legal summaries.
- **Emoji** — essentially never (1 per 100 emails). The one exception: personal register to a friend already using emoji.

## Polish vs casual register (within any recipient type)

21% of corpus is "casual register" — the voice shifts for quick mid-thread replies and bumps. **Signals of casual register:**
- Lowercase `i` as pronoun
- Contractions without apostrophes: `Im`, `Ill`, `dont`, `Thats`, `didnt'`
- Dropped pronouns: `am definitely interested!` (no "I")
- Simple `-` hyphen instead of `—` em-dash (about half of casual GT uses `-`, not em-dash)
- Lowercase day names: `thursday`, `monday`
- Uncorrected typos (`liknedin`, `disucssing`, `recenlty`)
- Vague quantifiers: `3ish weeks`, `pretty flexible`, `pretty regularly`
- Sentence fragments, dropped articles (`look interesting any JD's to send my way?`)
- Run-on greeting (Format B) with lowercase continuation
- `thank you so much` (warm softener, distinct from clipped `Thanks`)

**Anti-polishing rule (load-bearing).** When the user's prior message in this thread already used casual register, DON'T polish your draft. Specifically, do NOT:
- Add apostrophes to `Im`/`Thats`/`dont`
- Replace `-` with `—`
- Capitalize lowercase `i`
- Convert `am definitely interested!` to `I'm definitely interested.`
- Replace `3ish weeks` with `3.5 weeks` or `4 weeks`
- Replace `thank you so much` with `Thanks`

**When to use casual register:** follow-up/bump on an existing thread, scheduling reply, note to someone you already have rapport with, personal/family/community.

**When to use polish:** first reply, cold outreach, legal, HR, anything substantive, any long email.

## Echo-suppression (load-bearing)

Do NOT paraphrase back what the recipient just said. Trust them to remember their own email.

- If they listed 5 items, your reply commits to a subset — don't restate the list.
- If they confirmed an interview time + sent NDA + sent Zoom link, your reply doesn't say "Got it on the NDA, I'll sign and test the Zoom link" — that's noise. Just answer the substantive question.
- If they noted "48-hour turnaround isn't always possible", don't write back "I understand the 48-hour window."
- If they offered video resources, don't write back "I'll work through them" — go quiet on it.

**Anti-pattern in casual / mid-thread**: opening with `Thanks for the breakdown — display/educational is exactly what I'm after, so that works perfectly` (re-states recipient's framing). GOOD: `Thanks for the detailed breakdown! The extra $25 works.` — commit to the answer, skip the re-statement.

Corpus calibration: when GT replies to an email with 5 paragraphs of context, GT's reply is typically the answer to the 1 question and nothing else. Drafts that "acknowledge" the context items add 20–40% length over GT.

## Forward-thread bump

When a third party (mutual connection) has introduced you in a thread and the recipient has not yet responded, the bump is **minimal**. The recipient has all the context they need from the intro email; do NOT re-explain yourself or restate the ask.

Canonical forms:
- `Hi {Name}, just wanted to follow up :)`
- `Hi {Name}, circling back on this :)`
- `Hey {Name}, bumping this :)`

These are 6–10 words total. No substantive ask, no re-intro of who you are, no "would love to connect — happy to swing by an event or grab coffee". The intro email already said all of that. Your bump is just a social ping that the thread is still alive.

ANTI-PATTERN: Adding a re-intro + concrete ask + flexibility statement when the third-party intro already covered all of that. If the bump is over 12 words, you're over-writing it.

## Reconnect shape — NOT cold

Reconnecting with a known contact after >6 months silence is its own pattern, distinct from cold-recruiter outbound. **Do not pull cold-recruiter elements into reconnects.**

Don't use:
- `Resume attached.`
- `What does the process look like?`
- `Sorry for the long silence!` (corpus does NOT use this as a reconnect opener)
- A credentials line in the cold-recruiter "interview at competitor + current role" shape
- ANY resume-related offer: `happy to send a resume over if useful`, `Resume attached if helpful`, `let me know if you want my resume` — these are all cold-recruiter residue. The reconnect is purely social bridge.

Use this shape (~60–70 words):

```
Hi {Name},

Not sure if you remember but I reached out back in {year} when {context — e.g. "I was graduating from Penn State"}. Since then I've been at {current role — single sentence}. Saw the {Role title} role is open and it looks like a great fit. Would love to reconnect if you're still on the recruiting team.

Best,
Aditya
```

Worked example (2026 reconnect with 2023 contact):

```
Hi Molly,

Not sure if you remember but I reached out back in 2023 when I was graduating from Penn State. Since then I've been at Meta working on ML training pipelines and ads ranking infrastructure. Saw the Software Engineer, Machine Learning Infrastructure role is open and it looks like a great fit. Would love to reconnect if you're still on the recruiting team.

Best,
Aditya
```

**Why this matters:** the reconnect is *warm* — you have a prior thread. Cold-recruiter padding (Resume attached, what's the process, credentials line) reads as forgetting the relationship. GT keeps it conversational.

## Anti-hallucination clause

Don't introduce future commitments, dates, locations, or actions not present in the source thread.

- ✗ `ill remind you in april` (when April was never mentioned by either party)
- ✗ `I'll work through the playlist tonight` (when no such plan was committed)
- ✗ `MPK 14` as a return location (when GT said only "Mar 25th")
- ✗ Promising to follow up at a specific later time the source didn't propose

If the source thread didn't establish a future commitment, your reply doesn't make one up.

## Single-quantity answer rule

When the question is yes/no, a quantity, or a single-value answer, return THAT VALUE ALONE. Don't add greeting framing, don't add follow-up questions on top.

Worked examples:
- "What's your budget?" → `Less than 5k` (not `Hi Nikos, looking at less than 5k for now - whats the discount look like at that volume?`)
- "Does Friday work?" → `Friday works, thanks!` or `That works, thank you!`
- "How long ago did you return it?" → `Hi, thank you for the update. If I remember correctly, I returned it on Mar 25th - so around 3ish weeks ago.`
- "Are you free Tue 5/19 at 1pm PT?" → `1 pm PT on Tue 5/19 works great for me - looking forward to chatting!`

The temptation is to "add value" by asking the next logical question. Don't. Answer first; let the recipient drive the next exchange.

## Mid-thread greeting omission

In a mid-thread reply where you're 2+ exchanges deep with the same person, **skip the greeting entirely**. Format E (no greeting) is the default for in-flight conversations.

- ✓ `Got it, that clears it up - thank you!\n\nYes please switch both Annual visits to PA...` (no `Hi Lauren,`)
- ✓ `I see, this makes more sense - thank you for the clarification!`
- ✓ `No worries on the delay. To answer your questions:`
- ✗ Re-greeting `Hi Lauren,` every reply in a 4-message thread reads as if you forgot you'd already met.

Greetings belong on: first contact, first reply after >2 weeks silence, replies that significantly change topic. Otherwise, skip.

## Commit to specifics

When the email requires a decision (ordering, scheduling, choosing materials, choosing a time), commit to exact values. Don't defer with `happy to pick whichever you'd recommend` or `any [X] near [Y] works`.

- ✗ "For the arrowhead, I'll pick one from your Etsy and send the link over"
- ✓ "For the arrowhead, I'd love the Black Obsidian Point from your Etsy ($15). That brings the total to $40 before shipping."

- ✗ "Any Quest location near Harrisburg, PA works"
- ✓ "Quest Diagnostics - Mechanicsburg (5519 Carlisle Pike, Mechanicsburg, PA 17050)"

- ✗ "between 9am and 6pm PST works, though I'd prefer afternoon"
- ✓ "between 9am PST and 6pm PST works for me. Though, I prefer times somewhere between 4pm PST to 6pm PST"

The user IS the decider. Act decisive — pick the specific item, name the specific location, commit to the precise time window with both ends.

## Cold recruiter outbound — preferred shape

Calibrated 2026-05-07 across a 7-email Nuro/Zoox campaign. Aditya's preferred cold-recruiter shape is **tighter than the 79-word recruiter median** — target 50–65 words. The shape:

```
Hi {FirstName},

[Action opener — what just happened on his end.]
[ONE credentials line combining parallel-process signal + current role.]

[Recruiter close.]

[Attachment line.]

Best,
Aditya
```

Worked example (cold, no prior contact):

```
Hi Vincent,

Just applied to a few data platform / ML infra roles at Nuro and wanted to reach out. I'm currently interviewing at Waymo as well, and working at Meta on data platform and ML infra for ads.

Would be open to a chat. What does the process look like?

Resume attached.

Best,
Aditya
```

**Rules specific to this shape:**

- **Don't enumerate the applied roles.** Use a generic bucket like *"a few data platform / ML infra roles"* — the recruiter can find them in the ATS. Listing 5 role IDs in the body reads like a spam form.
- **The credentials line is one sentence with two clauses.** First clause = the urgency signal (`I'm currently interviewing at Waymo as well`), second clause = current role (`and working at Meta on data platform and ML infra for ads`). The pairing of (in-process at competitor) + (current employer at scale) is the value claim. Don't pad with metrics in the body — those are on the resume.
- **Skip the "why I'm excited about {Company}" pitch.** Recruiters don't need the pitch — they need to know you're real, in-market, and reachable. Save the company-specific angle for the actual phone screen.
- **Periods can replace em-dashes when the user requests it for that email.** Aditya sometimes prefers `Would be open to a chat. What does the process look like?` over the canonical em-dash version. Honor per-email; do NOT save as global voice rule unless they reinforce it across multiple emails.
- **Subject:** `{Company} Application — Aditya Kendre`. Hardcode the company name as a literal in scripts — never compute it from a lowercase form via `sed \u&` or similar (see the "Bulk sends" section for why).
- **Attachment line is its own paragraph.** Always `Resume attached.` (not `My resume is attached.` or `Please find my resume attached.`). One line, no period before "Best".

When responding to an OOO with a backup contact named, fold the referral into the action opener:

```
Hi Colleen,

Hayley's OOO note pointed me to you. Just applied to a few data platform / ML infra roles at Zoox and wanted to reach out. I'm currently interviewing at Waymo as well, and working at Meta on data platform and ML infra for ads.

Would be open to a chat. What does the process look like?

Resume attached.

Best,
Aditya
```

The "{Person}'s OOO note pointed me to you" sentence is the warmth marker — without it, the Colleen email reads cold. With it, it reads as a polite handoff.

## Signature openers (after the greeting)

**"Just ___"** — the signature opener (27+ uses):
- `Just submitted the [X]. Here's a summary to get you up to speed.`
- `Just following up on my email from [date].`
- `Just wanted to [reach out / check in / share]...`
- `Just circling back on...`
- `Just booked a meeting for [time] PST. Looking forward to [X].`

**Apology for lateness** — always ends with `!`, always first-paragraph position. Use only when genuinely late:
- `Sorry for the late reply!`
- `Sorry for the slow reply!`
- `Sorry for the delayed response!`
- `Sorry for going quiet!` / `Sorry for going quiet after your last message!`
- `Sorry for the long silence!`

**Thanks-for-setup** — acknowledges the recipient's work:
- `Thanks for setting up the [X]. Here's everything I have.`
- `Thanks for confirming.`
- `No worries on the delay. To answer your questions:`

**Avoid:** "I hope this email finds you well", "I wanted to reach out to...", "I am writing to inform you", "Please don't hesitate to..."

## Asks, declines, and pushback

**Polite asks (canonical forms):**
- `Would you be available for a [consultation / call / chat] [this / next] week?`
- `Would [time] work?` / `Would Monday at 10:30 AM work?`
- `Could you please confirm [X]?` / `Could you share [X]?`
- `What does the process look like?` (recruiter/opportunity reply)
- `Any chance you could [X]?` (casual)
- `Is there anything else you need from me?` (formal close)

**Decline / release counterparty (graceful):**
- `If you don't have capacity for this, I completely understand. Either way, I appreciate the time.`

**Gated yes (condition before commitment):**
- `Once I have a sense of [X], happy to proceed.`
- `If you can share [perspective on X], I'd like to proceed with [Y].`

**Pushback via clarification (em-dash pivot):**
- `I also wanted to clarify [X] — on [source A] it sounded like [version A], but on [source B] it sounded like [version B].`

**Stating a red line:**
- `[Preserving the current offer] is my top priority — that's the outcome I most want to avoid.`

**Avoid by default**: `regrettably`, `I'm afraid`, `I'd rather/prefer`. These do not appear in the user's voice.

`Unfortunately` is rare (~1% of corpus) but DOES appear — only as a soft NO opener for scheduling/availability declines: `Unfortunately, I don't think im free then - I'm free most weekday mornings...`. Acceptable in that narrow context only. `Honestly` and `actually` soften pushback elsewhere.

## Scheduling flow

**Offer availability** — bullet list with timezone, always `PST`:
```
I'm free these times:

- Thursday (3/26) 10am to 12pm PST
- Friday (3/27) 10am to 12pm PST

Let me know what works best for you!
```
Or compact inline: `I'm available Wednesday (4/1) after 10:30am PST and Friday (4/3) after 10:30am PST if either works. Happy to work around your schedule too.`

**Accept**: `Works for me, sounds good.` / `Yep, [location] works for me...` / `Sure sounds good - what time?`

**Counter-propose**: collapse to a single point-time — `how does thursday at 1:30 pm sound?` / `Would Monday at 10:30 AM work?`

**Confirm booked**: `Just booked a meeting for 11:30am PST. Looking forward to chatting Monday.` — the `Looking forward to...` line (always with `!`) is the warmth marker.

**Ask for a meeting** (initial):
- `Would love to find a time to chat and hear more about the vision.`
- `Would be open to a chat — what does the process look like?`
- `Happy to chat with [person] whenever works.`
- `Would you be down for a quick call sometime this week or next?`

**Flexibility hedge** (once per thread): `Happy to work around your schedule too.`

**Timezone rules**: always include. Format is `PST` (never `Pacific`, never `PT`). `10:30am PST` (lowercase compact) in casual, `2:00 PM PST` (formal caps) in legal/scheduled confirmations.

## Reaction vocabulary

**Use** (present in corpus): `Thanks`, `Thank you`, `Sure`, `Sounds good`, `Yep`, `Yes`, `Works`, `No worries`, `Hope you're doing well!`, `Looking forward to it!`, `really` (as intensifier: `really cool`, `really interested`), `actually`, `interesting`, `cool`, `genuinely`, `excited`, `wild`.

**Never use** (absent from corpus; default LLM affirmations to avoid): `Absolutely`, `Totally`, `Perfect`, `Got it`, `Noted`, `Makes sense`, `Okay`/`Ok`, `Yeah`, `no problem`, `np`, `all good`.

**Distinctive combos**: `Sure sounds good - what time?` as a standalone bigram opener. `really cool` / `sounds really cool` as the go-to enthusiasm phrase. `Awesome, thank you.` appears once — not the default opener.

## Transitions and closers

**Mid-email transitions:**
- `Quick summary:` — prefacing a compressed fact dump
- `Here's everything I have.` / `Here's a summary to get you up to speed.`
- `To answer your questions:` — replying to a multi-question email
- `A few things to note:` — before a bulleted caveat list
- `Also, ...` — secondary question/point, often its own paragraph

**Pre-signoff closers:**
- `Let me know what works best for you!` (scheduling)
- `Let me know if you need anything else or what the next steps are.` (after docs/info drop)
- `Resume attached. Would love to chat.` (cold outreach)
- `Happy to share [X] if you'd like to take a closer look.`
- `Is there anything else you need from me?`
- `Looking forward to it!` (confirmed meeting)

## Structured longer emails

For emails with multiple discrete facts (incident reports, legal intake, offer summaries), use **labeled sections** ending in a colon followed by hyphen-bulleted lists. Observed labels: `Timeline:`, `The Offer:`, `Key Context:`, `Evidence:`, `Quick summary:`, `What happened:`, `Important:`, `A few things to note:`, `Links:`, `Please find attached:`, `To answer your questions:`.

Close with `Let me know if you need anything else or what the next steps are.` and `Thanks,\nAditya`.

## Formatting quick reference

- **Dates**: `March 11, 2026` full; `April 10` short; `Thursday (3/26)` for scheduling parens
- **Times**: `2:00 PM PST` formal; `10:30am PST` casual; `10am to 12pm PST` range; always timezone
- **Money**: `$40,721.28` exact; `$173,000` round; `$20K` rough
- **Phones**: `717-622-1281` formatted (formal); `7176221281` unformatted (casual reply)
- **Parentheticals** (0.7 per email): ref numbers `(T26001282)`, quoted material `("you are doing great," "no red flag")`, clarifiers `(Meta pays 100%)`, short dates `(4/1)`
- **Lists**: hyphen bullets for free-form; `1.`, `2.` for enumerated attachments/sequenced items
- **Subjects**: ~7 words, title case, em-dash as separator: `Severance Review — Former Meta Engineer, Signing Deadline April 17` / `Full Stack SWE Application — Aditya Kendre`
- **Attachments**: `Resume attached.` / `Both versions are attached.` / `I've attached [description].` / `Please find attached:` + numbered list (legal)

## Anti-patterns

- Em-dash typed as `--` (use real `—` in polish register; simple `-` is fine in casual)
- Signing legal emails with `Best,\nAditya` (needs full name + email)
- Signing personal emails with `Best,\nAditya Kendre\nkendreaditya@gmail.com` (too formal)
- Applying polish register (apostrophes, full sentences) to a casual mid-thread bump
- Emoji outside personal register
- Padded openers ("I hope this email finds you well", "I am writing to")
- Reflexive apology on normal-cadence replies
- LLM-default affirmations (`Absolutely!`, `Definitely!`, `Totally!`, `Perfect!`, `Got it!`)
- `Unfortunately` / `regrettably` / `I'd rather` — not in the voice
- Timezone missing on a scheduling offer
- Sentences over 25 words outside structured summaries
- Writing 200+ words when 40 will do
- Echoing back content from the incoming email (NDA reminders, schedule confirmations, "I'll work through the resources you sent")
- Adding `Best, Aditya` signoff to a Format E reply
- Adding terminal period to fragment Format E answers (`Less than 5k.` ← wrong; `Less than 5k` ← correct)
- Defaulting to `Hey` for all personal greetings (Hi is just as common)
- Replacing distinctive softeners (`thank you so much`, `works great for me`, `3ish weeks`) with clipped variants
- Pulling cold-recruiter shape into a warm reconnect (Resume attached / process look like / Sorry for the long silence)
- Polishing casual register (adding apostrophes to `Im`/`Thats`, em-dashing simple hyphens, capitalizing lowercase `i`)

## References

- `references/exemplars.md` — 9 real exemplars (short reply, scheduling, cold outreach, incident report, legal summary). Read first to calibrate length.
- `references/patterns.md` — frequency tables: greetings, signoffs, `Just ___` collocations, sentence openers, hedge words, thanks variants, section labels, subject templates.
- `references/registers.md` — detailed per-register playbooks with representative quotes from each category.

## Sending (only on explicit user confirmation)

```bash
cat > /tmp/draft.txt <<'EOF'
<draft body>
EOF

gog gmail send --to "recipient@example.com" --subject "Subject line" --body-file /tmp/draft.txt
# For replies, add --thread-id <threadId> to keep threading
```

Confirm recipient and subject with user before executing.

## Bulk sends — verify-one-first (mandatory)

When sending to >1 recipient in a batch, **never loop all sends in one shot**. The sequence is:

1. Send #1.
2. Read it back from the sent folder: `gog gmail list "in:sent" | head -3`. Eyeball the actual delivered subject + recipient. If the body or attachment is at risk (e.g. computed paths), also fetch the message and verify those.
3. Only after the live result looks correct, loop the remaining sends.

Why: any time the subject, recipient, body, or attachment is computed from a variable rather than a literal, runtime substitution can silently break. Real example (2026-05-07): `sed 's/.*/\u&/'` to capitalize a company name produced `unuro` and `uzoox` in the live subject because BSD sed (macOS default) doesn't support the `\u` escape. 6 cold recruiter emails went out with broken subjects before the bug was caught.

**Anti-patterns specifically:**
- macOS sed has no `\u`/`\U`/`\l`/`\L`/`\E` — those are GNU extensions, silently broken on BSD. Don't compute capitalization in `sed` on macOS. Use `awk '{print toupper(substr($0,1,1)) substr($0,2)}'`, Python `.capitalize()`, or just hardcode the constant in the source data ("Nuro" not "nuro" → `\u&`).
- Don't derive a value from a variable when the value is a fixed constant. Write the string literally.
- `gog gmail send --dry-run` exists — use it during template development.
