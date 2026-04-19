# Deep Pattern Reference

Statistical patterns from 92 analyzed emails (last 100 sent, minus 8 auto/empty). Load this only when drafting a situation not clearly covered by an exemplar.

## Corpus summary

- 92 emails analyzed
- Median length: 44 words, 4 lines
- Average sentence length: 13.9 words; median: 10 words
- 128 hyphen-bulleted lines, 109 numbered lines (numbered is for sequenced/enumerated items)
- 145 em-dashes vs 4 en-dashes — em-dash is the correct glyph
- 1 emoji across the entire corpus

## Greeting frequencies

| Greeting token | Count | Share |
|---|---|---|
| `Hi [Name]` | 73 | 73% |
| `Hey [Name]` | 8 | 8% |
| `Hello`, `Hare Krishna`, other | ~5 | minor |
| No greeting (mid-thread casual) | remainder | — |

Comma is the canonical ending (62 of 75 standard greetings). Exceptions: `?` (3x, used when the greeting *is* the question, e.g. `Hi Katherine, this is what i see when I click the link?`), no punctuation (rare casual continuation).

## Signoff frequencies

| Signoff | Count |
|---|---|
| `Best,\nAditya` | 20 |
| `Thank you,\nAditya` | 13 |
| `Thanks,\nAditya` | 8 |
| `Thanks!\nAditya` | 2 |
| No signoff, just `Aditya` | ~15 |
| Full "Aditya Kendre" | 20 (all legal/formal) |
| Specific: `Looking forward to it!` / `Thanks again!` | ~3 |

## "Just ___" opener collocations (27 total)

| Phrase | Count |
|---|---|
| `Just wanted to` | 8 |
| `Just following up` | 5 |
| `Just submitted the` | 3 |
| `Just booked a` | 2 |
| `Just circling back` | 1 |
| `Just applied to` | 1 |
| `Just filed the` | 1 |

## Question bigrams (top 15 starters)

| Starter | Count |
|---|---|
| `Would you` | 7 |
| `Could you` | 3 |
| `Would be` | 3 |
| `Are there` | 2 |
| `What does` | 2 |
| `Is there` | 1 |
| `Any chance` | 1 |
| `One quick` | 1 |

Canonical ask: `Would you be available for a [consultation/call/chat] [this/next] week?`

## Apology templates (all end with `!`)

From the corpus:
- `Sorry for the late reply!`
- `Sorry for the slow reply!`
- `Sorry for the delayed response!`
- `Sorry for going quiet!`
- `Sorry for going quiet after your last message!`
- `Sorry for the long silence!`

Never `My apologies for...`, never `I'm so sorry about...`, never `Please excuse the delay`.

## Thank-you phrase frequencies

| Phrase | Count |
|---|---|
| `Thank you,` (signoff) | 13 |
| `Thanks,` (signoff) | 8 |
| `Thanks for setting up [X]` | 1 |
| `Thanks for confirming` | 1 |
| `Thanks for the options` | 1 |
| `Thanks for reaching out` | 1 |
| `Thanks for letting me know` | 1 |
| `Thanks again` / `Thanks again for the conversation` | 2 |

"Appreciate" is used 3x in the corpus — rare, reserved for genuine high-value thanks.

## Hedge-word frequencies (rare — be declarative)

| Hedge | Count |
|---|---|
| `just wanted to` | 8 (as friendly opener, not hedge) |
| `I believe` | 5 |
| `I think` | 3 |
| `might` | 3 |
| `possibly` | 2 |
| `kind of` | 2 |
| `maybe` | 1 |
| `perhaps` / `I suppose` / `sort of` | 0 |

If you find yourself writing "I was wondering if maybe", stop — that register does not appear in the corpus.

## Section-label inventory

Observed labeled sections (always end in colon, followed by bulleted content):

- `Timeline:`
- `The Offer:`
- `Key Context:`
- `Evidence:`
- `Quick summary:`
- `What happened:`
- `Important:`
- `A few things to note:`
- `Links:`
- `Please find attached:`
- `To answer your questions:`

## Sentence-opener frequencies (top 10 first words, greetings/closings excluded)

| Opener | Count |
|---|---|
| `I` | 45 |
| `My` | 25 |
| `I'm` | 21 |
| `Would` | 20 |
| `The` | 14 |
| `Happy` | 8 |
| `Here's` | 5 |
| `Let` | 5 |
| `No` | 5 |
| `Just` | 4 |

## Non-first paragraph openers (top 10)

| Opener | Count |
|---|---|
| `I` | 29 |
| `Best,` | 21 |
| `Aditya` | 19 |
| `I'm` | 18 |
| `Thanks,` | 18 |
| `Thank you,` | 17 |
| `-` (bullet) | 14 |
| `Sorry` | 10 |
| `Would` | 9 |
| `Just` | 9 |

## Attachment-introduction templates

- `Resume attached.` (2-word minimum pattern)
- `Both versions are attached.`
- `All key documents are attached.`
- `I've attached a [description] showing [X].`
- `I can attach the [X] if helpful.`
- `Please find attached:` + numbered list (most formal)

## Date/time/money formatting rules

### Dates
- Canonical long: `March 11, 2026` (used 3x for the same event in the corpus)
- Short: `April 10`, `March 25` (when year is obvious)
- Scheduling parens: `Thursday (3/26)`, `Friday (4/3)`
- Month-only: `October and November 2025`

### Times
- Formal: `2:00 PM PST` (all caps AM/PM, space before, timezone follows)
- Casual range: `10am to 12pm PST`, `10:30am PST` (lowercase when compact)
- Always include timezone when proposing a time

### Money
- Exact with comma and cents: `$40,721.28`
- Exact round: `$173,000`
- Rough: `$20K` (K, not k)
- In context: `roughly $20K below what laid-off employees received`

### Phone
- Formatted: `717-622-1281` (used in formal contexts)
- Unformatted: `7176221281` (used in one-line casual reply)

## Subject-line templates

Observed patterns:
- `[Topic] — [Detail], [Constraint]` — `Severance Review — Former Meta Engineer, Signing Deadline April 17`
- `[Role] Application — Aditya Kendre` — `Full Stack SWE Application — Aditya Kendre`
- `[Topic] Report - [Date]` — `Car Accident Report - March 31`
- `Follow-Up — [Topic]` — `Follow-Up — Additional Context & Fee Clarification`
- Casual: `Request to buy an arrow`, `EA/LW/ACX South Bay events`

Average: 7 words, 49 chars, title case. Em-dash used as separator (not colon, not pipe).

## Register-calibration rules of thumb

- **Cold outreach to a professional** (attorney, recruiter) → 60-180 words, `Best,\nAditya` or `Thank you,\nAditya`, formal em-dash subject line
- **Reply to a peer/friend already engaged** → 20-50 words, `Best,\nAditya` or no signoff
- **Thanks acknowledgment** → 30-80 words, `Thanks,\nAditya`
- **Document/info drop to existing contact** → short prose + numbered list, `Aditya` (no signoff adverb)
- **Status summary to new stakeholder** → 200-400 words, labeled sections, `Thanks,\nAditya`
- **Legal/contractual** → any length, `Aditya Kendre` (full name only here)
