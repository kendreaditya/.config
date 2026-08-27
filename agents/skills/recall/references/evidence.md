# Why you forget what you discussed with an AI, and what actually helps

*Load this when a `recall` claim needs a real number, when citing a study's method or limits,
or when the user asks whether any of this is actually established.*

Companion to `comprehension-debt/references/`, which covers the **code** case (does AI-written
code degrade the author's understanding). This file covers the **discussion** case: why
conclusions reached in conversation don't stick, and which interventions have evidence.

## The causes, ranked by how well supported they are

### 1. Cognitive offloading — well established as a mechanism, weakly established for AI specifically

- **Sparrow, Liu & Wegner (2011)**, *Science* 333(6043):776–778, "Google Effects on Memory."
  Participants told a typed fact would be **saved** recalled it worse than those told it would be
  erased; they remembered *which folder* it went in better than the fact itself. Framed via
  Wegner's transactive memory: the tool becomes a memory partner and you encode the retrieval
  path instead of the content. [DOI 10.1126/science.1207745](https://doi.org/10.1126/science.1207745)
  - Caveat: the Stroop experiment in this paper has had replication difficulty, and the authors
    framed it as a *redistribution* of cognitive labor, not a deficit. Media turned it into
    "the internet makes us stupid" — don't repeat that framing.
- **Gerlich (2025)**, *Societies* 15(1):6. n=666 survey + 50 interviews; **r = −0.68, p < 0.001**
  between AI tool use frequency and critical thinking scores, mediated by cognitive offloading;
  younger participants more dependent, higher education protective.
  [DOI 10.3390/soc15010006](https://doi.org/10.3390/soc15010006)
  - Caveat, and it's a large one: **correlational and self-reported on both sides**. Reverse
    causation is fully plausible (weaker critical thinkers may reach for AI more). Shared-method
    variance inflates r. Cite as a correlation, never as an effect of AI use.
- **GPS analogue** — heavier satnav use predicted worse unaided spatial memory (n=50, with a
  3-year follow-up n=13 showing steeper decline); hippocampal/prefrontal activity rose during
  self-guided navigation but not while following satnav (n=24). Tiny samples; useful as a
  same-shape precedent, not proof. [Nature Sci Rep](https://www.nature.com/articles/s41598-020-62877-0)

### 2. Effort reduction tracks reduced critical engagement — self-report only

- **Lee, Sarkar, Tankelevitch, Drosos, Rintel, Banks & Wilson (2025)**, CHI 2025 (Microsoft
  Research + CMU HCII). 319 knowledge workers, 936 first-hand examples. Where workers perceived
  GenAI reduced their effort, they also perceived reduced critical thinking. **Higher confidence
  in the AI → less critical thinking; higher self-confidence → more.** Documents a shift "from
  information gathering to information verification; from problem-solving to AI response
  integration; from task execution to task stewardship."
  [Microsoft Research](https://www.microsoft.com/en-us/research/publication/the-impact-of-generative-ai-on-critical-thinking-self-reported-reductions-in-cognitive-effort-and-confidence-effects-from-knowledge-workers/)
  - Caveat: **entirely self-reported perceptions**, correlational, no objective performance
    measure. The authors say so. The Forbes/404 Media "atrophied and unprepared" headline is a
    quote from the paper's discussion, not a measured finding.
  - Most useful part for this skill: their named **awareness barrier** — people don't notice
    critical thinking was needed. A scheduled quiz is an external trigger for exactly that.

### 3. Not encoding your own reasoning because you didn't generate it — strongest evidence

- **Generation effect**: producing beats reading, **d = 0.40** across 86 studies / 445 effect
  sizes; >10% memory advantage replicated across 126 articles / 310 experiments.
  [Bertsch et al.](https://link.springer.com/article/10.3758/BF03193441)
- **Anthropic RCT (2026)**: 52 mostly-junior engineers, unfamiliar Python library. AI-assisted
  group scored **50%** on a post-task comprehension quiz vs **67%** hand-coders, with only ~2
  min time saved (not significant). Critically: participants who used AI to *ask questions and
  request explanations while still coding themselves* retained comprehension; those who
  delegated generation did not.
  [anthropic.com](https://www.anthropic.com/research/AI-assistance-coding-skills)
  - Caveat: small n, junior-weighted, immediate post-task only. Authors state it's unresolved
    whether quiz score predicts longer-term skill.
- **PNAS 2025 field RCT**, ~1,000 high-school math students: GPT-4 access raised practice
  scores 48–127%, but on a later **unaided** test the unrestricted-access group scored **17%
  lower** than students who never had AI. Same performance-up / unaided-down split in a
  different domain. [pnas.org](https://www.pnas.org/doi/pdf/10.1073/pnas.2422633122)
- **Kosmyna et al. (2025)**, "Your Brain on ChatGPT" (arXiv:2506.08872). 54 adults, 32-channel
  EEG, SAT essays. LLM group showed weakest neural coupling; **83% of LLM users couldn't quote a
  single sentence from the essay they had just written** (~11% in search/brain-only groups); the
  Brain-to-LLM order (think first, then AI) showed *increased* connectivity vs LLM-to-Brain.
  [arxiv.org](https://arxiv.org/abs/2506.08872)
  - Caveat, mandatory when citing: **preprint, unreviewed, n=54 with only 18 in the much-quoted
    switching condition**, one narrow task. EEG connectivity is not learning. Kosmyna publicly
    rejected the "makes you dumber" framing. Cite the 83%-recall figure as suggestive, and the
    sequencing implication as the author's own interpretation.
  - Still the closest thing to a direct measurement of *this user's stated problem*: not
    remembering the content of work you just did with an LLM.

### 4. Mechanical, specific to Claude Code — verifiable locally, no literature needed

- **Compaction is lossy by construction.** Long conversations get summarized; detail that isn't
  in the summary is gone from context. `docs/memory.md` has a whole troubleshooting entry,
  "Instructions seem lost after `/compact`."
- **Sessions are ephemeral to the human.** Transcripts persist as JSONL in
  `~/.claude/projects/<slug>/` but nothing surfaces them. On this machine, 2026-08-26:
  **417 session files, 439 MB, all inside ~26 days** (~16 sessions/day, with 92 on one day) —
  and `~/.claude/projects/-Users-akendre-workspace/memory/` was **empty**. Volume is the
  aggravating factor: high session count with no consolidation step.
- **No retrieval loop anywhere in the stack.** Auto memory and CLAUDE.md are read *by Claude*,
  never *by the user*. `parlai`, `session-logs`, and `memex` make history searchable but are
  pull-only — they require already remembering that something exists. Nothing in the harness
  ever asks the user a question. That's the actual gap `recall` fills.

## The interventions, ranked by evidence per unit of effort

- **Retrieval practice** — one of only two techniques rated **high utility** in Dunlosky,
  Rawson, Marsh, Nathan & Willingham (2013), *Psychological Science in the Public Interest*
  14(1):4–58, out of ten reviewed. Meta-analytic testing effect commonly **g ≈ 0.50–0.70**
  (Rowland 2014 g≈0.50; Adesope et al. 2017 g≈0.61).
  [DOI 10.1177/1529100612453266](https://doi.org/10.1177/1529100612453266)
  - The key asymmetry, **Roediger & Karpicke (2006)**: repeated retrieval gave **61%** recall at
    one week vs **40%** for repeated restudy — even though restudy looked *better* on an
    immediate 5-minute test (83% vs 71%). Rereading wins the test you take now and loses the one
    that matters. [purdue.edu](https://learninglab.psych.purdue.edu/downloads/2006/2006_Roediger_Karpicke_PsychSci.pdf)
- **Spacing** — the other high-utility technique. Cepeda et al. (2006) meta-analysis, 254
  studies / ~14,000 participants: spaced beat massed in **259 of 271** comparisons. Optimal lag
  scales with intended retention interval, which is exactly what SM-2 approximates.
- **Pretesting** — guessing before seeing the answer, *even wrongly*, improves retention of that
  item: **g = 0.54 (k=97)**. But it does **not** transfer to unpredicted material in the same
  lesson (g = 0.04, k=91) — so it must be applied per card, not once per session. This is why
  `recall` hints before revealing. [Springer](https://link.springer.com/content/pdf/10.3758/s13423-023-02353-8.pdf)
- **Self-explanation** — 2018 meta-analysis, 69 effect sizes, **g = 0.55** favoring
  self-explanation prompts. [ERIC](https://eric.ed.gov/?id=EJ1186664)
- **Illusion of competence** (Koriat & R. Bjork) — judging your learning while the material is
  still visible overestimates what survives once it's gone. The mechanism reason `due` hides
  answers. [bjorklab](https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/07/Koriat_RBjork_2005.pdf)
- **Active reconstruction beats reading, in programming specifically** — reordering scrambled
  code (Parsons problem) matched one-week retention of writing the same code from scratch, in
  less time; students given an AI-generated puzzle to reconstruct recalled more than students
  who read the AI's full solution (CodeTailor). [arxiv.org](https://arxiv.org/html/2401.12125v2)

### Weaker than folklore claims — don't oversell these

- **Teach-it-back / explain-to-Claude**: 2024 meta-analysis of 39 studies, **g = 0.27** overall;
  **g = 0.48** if you studied *intending* to teach; **g = −0.02** if teaching is decided only
  afterward. So "explain it back to me at the end" is near-worthless unless the user knew going
  in. [Springer](https://link.springer.com/content/pdf/10.1007/s10648-024-09871-4.pdf)
- **Summarization and rereading**: both rated **low utility** by Dunlosky et al. Summarization
  works only for trained summarizers. Highlighting is near-zero and can hurt. A session-summary
  file is, on this evidence, close to useless for retention — which is why `recall` is a quiz
  and not a digest.

## What is asserted, not measured

- **The "collector's fallacy"** (Christian Tietze, 2013) — confusing *acquiring* information
  with *knowing* it; Ahrens' *How to Take Smart Notes* (2017) on notes as "graveyards." Widely
  cited, describes this exact failure well, and is **not** an empirical finding.
- **Spaced repetition applied to personal knowledge management** is under-tested. The lab work
  is on discrete factual material — vocabulary, definitions, paired associates — not on
  synthesizing engineering judgment. Matuschak ("Why books don't work") and Nielsen
  ("Augmenting Long-term Memory") are thoughtful and explicitly exploratory. Matuschak has
  written candidly about how hard it is to write good prompts for *conceptual* material.
  The mechanism transfers in principle; the practice is a reasonable bet, not a proven protocol.
- **"X% of notes are never re-read"** — no rigorous source found. Numbers circulating in
  productivity writing appear invented. Don't quote a figure.

## What died in fact-checking

- **Gerlich's r = −0.68** is real and correctly quoted, but a version circulating as **−0.75**
  is wrong. Check before citing.
- **"MIT proved ChatGPT causes brain damage / cognitive decline"** — the study measured EEG
  connectivity during a task over ~4 months, is a preprint, and its lead author explicitly
  rejected this reading. Never state it as settled.
- **"Microsoft found AI reduces critical thinking"** — it found workers *reported* perceiving
  reduced critical thinking where they perceived reduced effort. Different claim.

## What survives, stated narrowly

For conclusions the user wants to still hold weeks later — a decision and its rationale, a root
cause, a constraint — the evidence supports one thing clearly: **being asked to produce the
answer from memory, on a spaced schedule, retains better than rereading it, and rereading feels
better while working worse.** That is a robust finding about discrete retrievable material
(Dunlosky high-utility; Roediger & Karpicke 61% vs 40% at one week) and a well-motivated
extrapolation for engineering judgment. The claim that *AI specifically* accelerates forgetting
is plausible, mechanistically consistent with offloading research, supported by two controlled
studies showing an unaided-performance gap (Anthropic RCT, PNAS 2025) — and still young,
partly preprint, and largely correlational where it concerns knowledge workers.

The intervention is cheap and the downside is bounded (time spent reviewing). But an unreviewed
card store is strictly worse than nothing: it adds guilt and no retention. If review stops for
a few weeks, delete the store.
