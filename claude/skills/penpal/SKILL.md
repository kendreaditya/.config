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

| Register | Who | Median words | Greeting | Signoff | Key markers |
|---|---|---|---|---|---|
| **Legal** | attorneys, law firms | ~110 | `Hi Name,` own line | `Thank you,\nAditya Kendre\nkendreaditya@gmail.com` | numbered attachment lists, no `!`, no emoji, `Please find attached:` |
| **Recruiter** | recruiters, talent, cold tech outbound | ~79 | `Hi Name,` own line | `Best,\nAditya` | `Sorry for the {slow/late/delayed/long} reply!` opener, specific compliment + em-dash pivot to `what does the process look like?` |
| **Tech company / peer engineer** | engineers, PMs, founders | ~75 | `Hi Name,` own line (or `Hey Name,`) | `Best,\nAditya` | blunt, pre-emptively answers location/visa/scheduling, `Yep`-level casual allowed |
| **Personal** | friends, family, community members | ~103 | `Hey Name,` | `Thanks!\nAditya` or bare `Aditya` | exclamation points, narrative lead-in, emoji OK (rare), no last name |
| **HR / Meta / service / form** | former-employer HR, insurance, apartment, IT | ~56 | `Hi Name,` or bare `Hi,` | `Thank you,\nAditya Kendre\n[employee ID or phone]` | bureaucratic formality, bulleted asks, typos left uncorrected, no contractions |

If the user doesn't specify, infer from the recipient's email domain + any thread context provided.

## Step 2 — Greeting format selection

The corpus uses five greeting formats. Pick based on thread state, not register:

- **Format A** — `Hi Name,\n\n[body]` (separate greeting line + blank line). **Default. 62% of corpus.** Use for any substantive email or first reply to a formal recipient.
- **Format B** — `Hi Name, [body starts same line]` (inline). **20% of corpus.** Use for casual follow-ups, bumps, quick scheduling replies when rapport already exists.
- **Format C** — `Hi Name, [single question]?` (inline, whole email is one question). Subset of B, use when the email has no content other than the question.
- **Format D** — `Hare Krishna Prabhu,` or similar community greeting. Only for that specific devotional context.
- **Format E** — no greeting at all. **17% of corpus.** Use for tight mid-thread replies (<30 words), sending bare links/images, or logistics ack like `Works for me, sounds good. My number is 717-622-1281`.

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
- Contractions without apostrophes: `Im`, `Ill`, `dont`
- Lowercase day names: `thursday`, `monday`
- Uncorrected typos (`liknedin`, `disucssing`, `recenlty`)
- Sentence fragments, dropped articles (`look interesting any JD's to send my way?`)
- Run-on greeting (Format B) with lowercase continuation

**When to use casual register:** follow-up/bump on an existing thread, scheduling reply, note to someone you already have rapport with, personal/family/community.

**When to use polish:** first reply, cold outreach, legal, HR, anything substantive, any long email.

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

**Never** use `unfortunately`, `regrettably`, `I'm afraid`, or `I'd rather/prefer`. These do not appear in the user's voice. `Honestly` and `actually` soften pushback instead.

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

- Em-dash typed as `--` or `-` (use real `—`)
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
