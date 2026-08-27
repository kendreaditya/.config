# The Post-AI Evidence Base

*Load this when you need to check whether a comprehension-debt claim is backed by a real number, need a study's actual method and limitations before citing it, or need to know what survived the strongest counterarguments.*

## The distinction that names the problem

- Classic technical debt (Cunningham's metaphor, formalized by Fowler/Kruchten): code the team understands but hasn't cleaned up — a known shortcut, a known cost.
- Comprehension debt, as used by the one paper that names it directly, is different in kind: code nobody currently understands, independent of whether it's "clean" — the cost is epistemic, not stylistic.
- Supported: program comprehension is a real, separately measured activity — professionals spend ~58% of working time on it — and reading/explaining code is a distinct, only-correlated skill from writing it, not the same thing wearing a different hat.
- Framing, not measured: no source here operationalizes "comprehension debt" as a countable quantity the way duplicated lines or defect counts are counted. The only paper using the exact term studied 207 students' diaries over eight weeks — a qualitative pattern catalog, not a metric.
- The metaphor extension is contested even for ordinary tech debt: the concept was already "diluted" from overuse before AI entered the picture, and program-comprehension research has historically defined "comprehension" implicitly by whatever task happens to measure it, not one agreed construct.

## What is measured

### Code-quality trends and vendor surveys

- **Vendor dataset, GitClear:** 211M changed lines, Jan 2020-Dec 2024, from repos tied to Google/Microsoft/Meta/enterprise/OSS; roughly two-thirds of the sample is GitClear's own paying customers who opted in, one-third OSS. [gitclear.com](https://www.gitclear.com/ai_assistant_code_quality_2025_research)
- Copy-pasted code rose 8.3% to 12.3% of changed lines, 2021-2024; refactored ("moved") lines fell from ~25% to under 10% over the same window.
- Trade-press coverage of the same dataset (not GitClear's own headline) reports 5+-line duplicate blocks up 8x in 2024; GitClear's own page instead headlines "4x more code cloning" as a separate aggregate — two different metrics inside one report, often conflated when quoted. [devclass.com](https://www.devclass.com/ai-ml/2025/02/20/ai-is-eroding-code-quality-states-new-in-depth-report/1626250)
- Observational trend analysis, not a controlled experiment; no independent non-vendor replication exists.
- **Vendor survey, Google DORA 2025:** ~5,000 professionals, 100+ hours qualitative data. 90% use AI at work, >80% believe it raised their productivity, 30% report little-or-no trust in AI-generated code. [PDF](https://services.google.com/fh/files/misc/2025_state_of_ai_assisted_software_development.pdf)
- DORA 2025's own framing: AI is "an amplifier" of an org's existing strengths and dysfunctions, not a fix by itself. [dora.dev](https://dora.dev/research/2025/dora-report/)
- **Vendor survey, Google DORA 2024:** 39,000+ professionals. A 25% rise in AI adoption tracked with +3.4% code quality, +7.5% documentation quality, +3.1% review speed — and -1.5% delivery throughput, -7.2% delivery stability. [research.google](https://research.google/pubs/dora-accelerate-state-of-devops-2024-report/) All self-reported correlations, not measured defect counts.
- **Vendor survey, Sonar 2026:** ~1,100-1,149 developers, fielded ~October 2025. [sonarsource.com](https://www.sonarsource.com/company/press-releases/sonar-data-reveals-critical-verification-gap-in-ai-coding/)
- 96% don't fully trust that AI code is functionally correct; only 48% always check AI code before committing; AI is ~42% of committed code today, projected 65% by 2027; 38% say reviewing AI code takes more effort than reviewing a human colleague's.
- Same survey: 93% report positive effects on tech debt overall *and* 88% report negative effects (53% say AI generates unreliable code, 40% unnecessary/duplicative code) — split, not one-sided, inside one vendor's own numbers.
- **Vendor survey, Stack Overflow 2025:** 33,244 respondents on trust — 3.1% highly trust AI output, 29.6% somewhat trust, 26.1% somewhat distrust, 19.6% highly distrust. [survey.stackoverflow.co](https://survey.stackoverflow.co/2025/ai)
- Separately, 31,476 respondents ranked frustrations: "almost right but not quite" 66%, "debugging AI code is more time-consuming" 45.2%, "less confident in my own problem-solving" 20%, "hard to understand how or why the code works" 16.3%.

### Studies of AI-authored code itself

- **arXiv:2603.28592**, "Debt Behind the AI Boom": 302,600 verified AI-authored commits, 6,299 GitHub repos, five assistants (Copilot, Claude, Cursor, Gemini, Devin). [arxiv.org](https://arxiv.org/abs/2603.28592)
- Attribution via Git metadata (bot logins, author emails, Co-authored-by trailers), not a style classifier; scanned Jan 2024-Oct 2025.
- 484,366 distinct issues found via before/after static analysis (Pylint/Bandit, ESLint/njsscan); 89.3% were code smells; >15% of commits from every assistant introduced at least one issue; 22.7% of tracked issues survived to the latest revision.
- No human-authored baseline for comparison — this shows what's in AI commits, not whether it's worse than the human equivalent.
- **GitHub's own RCT:** 202 developers (5+ yrs experience), Copilot vs. none on a Python API task; a blind Phase 2 reviewed 1,293 code reviews from 25 developers. [github.blog](https://github.blog/news-insights/research/does-github-copilot-improve-code-quality-heres-what-the-data-says/)
- Copilot users 53.2% more likely to pass all 10 unit tests (p<0.01); blind reviewers rated Copilot-assisted code more readable (+3.62%, p=.003), reliable (+2.94%, p=.01), maintainable (+2.47%, p=.041); 5% more likely to approve it (p=.014).
- GitHub's own product, one short task — a real controlled counter-example to "AI always degrades quality," but silent on long-horizon maintainability.

### Productivity vs. self-perception

- **METR RCT:** 16 experienced OSS developers, 246 real issues in mature repos they already knew (mostly Cursor Pro + Claude 3.5/3.7 Sonnet), randomized AI-allowed vs. disallowed. [arxiv.org/abs/2507.09089](https://arxiv.org/abs/2507.09089)
- Measured 19% *slower* with AI, despite predicting a 24% speedup beforehand and still believing afterward they'd been ~20% faster.
- Authors explicitly scope this to experienced maintainers on large, familiar, mature codebases — not a general claim.
- METR's own Feb 2026 correction: a follow-up produced an "unreliable signal" (-18% CI[-38%,+9%] returning devs, -4% CI[-15%,+9%] new devs), blamed on selection effects (only devs willing to work AI-free enrolled), a pay cut from $150/hr to $50/hr, and broken time measurement under concurrent agents. METR states the original 19%-slower result is "out of date." [metr.org](https://metr.org/blog/2026-02-24-uplift-update/)

### Program comprehension and time allocation

- Xia et al. (IEEE TSE 2018): 78 professional developers, 7 real projects, 3,148 logged hours — ~58% of time spent on program-comprehension activities. [ink.library.smu.edu.sg](https://ink.library.smu.edu.sg/sis_research/3779/) Predates AI assistants entirely — it's the baseline any AI-era shift has to argue against, not evidence of one.
- Lopez et al.: code-tracing and "explain in plain English" ability both correlate with code-writing ability but are measurably distinct skills. [opus.lib.uts.edu.au](https://opus.lib.uts.edu.au/bitstream/10453/10806/1/2008001530.pdf)
- Ivanova et al. (fMRI): code comprehension strongly recruits the brain's multiple-demand system (math/logic/problem-solving), not the language system, despite superficially resembling reading prose. [mit.edu](https://www.mit.edu/~hopekean/files/braincode.pdf)

### The two controlled AI-comprehension studies

- **Anthropic RCT (2026):** 52 mostly-junior engineers building features in an unfamiliar Python library (Trio). [anthropic.com](https://www.anthropic.com/research/AI-assistance-coding-skills)
- AI-assisted group scored 50% on a post-task quiz (debugging/reading/concepts) vs. 67% for hand-coders — "nearly two letter grades" — with the AI group only ~2 minutes faster, not statistically significant.
- Within the same study, participants who used AI to ask follow-up questions or request explanations while still coding independently retained comprehension; those who delegated code generation outright did not.
- Small sample; authors state it's unresolved whether quiz score predicts longer-term skill.
- **Farley et al. RCT** ("Echoes of AI," arXiv:2507.00788): 151 professional developers — one group built a feature with/without AI, an independent blind group later maintained the result.
- No significant maintainability difference (CodeScene code health, test coverage, SPACE framework) between AI-assisted and non-AI-assisted code; AI users ~30% faster (habitual users ~55% faster).
- This is the direct counter-data to the Anthropic result: comprehension cost and code-artifact quality are separate, separately measured constructs — one study found a real effect on the human, the other found null on the artifact.

### Learning-science mechanics behind the pattern

- Generation effect: self-producing beats reading, d=0.40 across 86 studies/445 effect sizes; a >10% memory advantage replicated across 126 articles/310 experiments. [springer.com](https://link.springer.com/article/10.3758/BF03193441)
- Retrieval beats rereading only at a delay: repeated retrieval produced 61% recall at one week vs. 40% for repeated restudy — even though restudy looked *better* on a 5-minute immediate test (83% vs. 71%). [purdue.edu](https://learninglab.psych.purdue.edu/downloads/2006/2006_Roediger_Karpicke_PsychSci.pdf)
- Koriat & Bjork's "illusion of competence": judging learning while material is still visible overestimates what survives once it's gone — why a diff that "makes sense" now can still not stick. [bjorklab.psych.ucla.edu](https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/07/Koriat_RBjork_2005.pdf)
- Expertise reversal effect (Kalyuga, Chandler, Tuovinen & Sweller, 2001): novice apprentices learned better from worked examples, but as experience grew, doing it yourself became superior and the worked example turned into redundant load. [eric.ed.gov](https://eric.ed.gov/?id=EJ640537) The single strongest finding for gating AI-reliance by skill level rather than applying one rule to everyone.
- Self-explanation while studying a worked example predicts better example-independent understanding; a 2018 meta-analysis of 69 effect sizes found g=0.55 favoring self-explanation prompts. [ERIC](https://eric.ed.gov/?id=EJ1186664)
- Pretesting effect: guessing before seeing the answer, even wrongly, improves later retention of that item (g=0.54, k=97) but doesn't transfer to unpredicted material in the same lesson (g=0.04, k=91) — must be applied per decision point, not once per session. [Springer](https://link.springer.com/content/pdf/10.3758/s13423-023-02353-8.pdf)
- Teach-it-back is weaker than folklore claims: a 2024 meta-analysis of 39 studies found g=0.27 overall, rising to g=0.48 if you studied *intending* to teach, but falling near zero (g=-0.02) if teaching is decided only afterward. [Springer](https://link.springer.com/content/pdf/10.1007/s10648-024-09871-4.pdf)
- Deliberate practice's explanatory power is domain-dependent and weak in open-ended professional skill: 26% of variance in games, 21% music, 18% sports, 4% education, <1% professions (Macnamara, Hambrick & Oswald 2014); a 2019 replication of Ericsson's violinist study found a much smaller effect than originally reported. [gwern.net](https://gwern.net/doc/psychology/2014-macnamara.pdf)
- Offloading analogues outside code: heavier GPS use predicted worse unaided spatial memory (n=50), with a 3-year follow-up (n=13) showing steeper decline with more use; hippocampal/prefrontal activity rose during self-guided navigation but not while following satnav (n=24); expecting information to stay saved reduces recall of its content while improving recall of where to find it. [nature.com](https://www.nature.com/articles/s41598-020-62877-0)
- PNAS 2025 field RCT, ~1,000 high-school math students: GPT-4 access raised practice scores 48-127%, but on a later unaided test, students with unrestricted access scored 17% *lower* than students who'd never had AI at all — the same performance-up/unaided-down split as the Anthropic coding RCT, in a different domain. [pnas.org](https://www.pnas.org/doi/pdf/10.1073/pnas.2422633122)
- Active reconstruction beats passive reading in programming specifically: reordering scrambled code (a Parsons problem) matched the one-week retention of writing the same code from scratch, in less time; in CodeTailor's study, students given an AI-generated puzzle to reconstruct recalled more than students who just read the AI's full solution. [arxiv.org](https://arxiv.org/html/2401.12125v2)

## What is only asserted

- Simon Willison's definition: "vibe coding" means building with an LLM *without reviewing* its output; reviewing, testing, and understanding every line makes it professional AI-assisted programming instead — a distinction routinely erased when the two get conflated. [simonwillison.net](https://simonwillison.net/2025/Mar/19/vibe-coding/?s=09)
- Willison separately argues review, not generation, is now "the natural bottleneck," then later (2026) that "eyeballing every line... has never been the most effective way to validate a change" — his own stated position has moved. [simonwillison.net](https://simonwillison.net/2026/Aug/22/more-than-just-code-review/)
- Anthropic's product docs assert that without a runnable check, "you become the verification loop," and recommend Plan Mode plus an adversarial subagent pass — practice advice, not a measured result. [code.claude.com](https://code.claude.com/docs/en/best-practices)
- OpenAI's alignment team asserts AI-generated code volume "can exceed the limits of thorough human oversight" and treats automated review as a compensating control — a stated engineering judgment, not a study. [alignment.openai.com](https://alignment.openai.com/scaling-code-verification/)
- Böckeler (Thoughtworks) asserts LLMs are "inferrers," not deterministic compilers, making AI-assisted development "a matter of ongoing risk assessment rather than one-time trust," and separately documents agents claiming success despite failing tests as complexity rises. [martinfowler.com](https://martinfowler.com/articles/pushing-ai-autonomy.html)
- Reported policy responses are asserted, not measured outcomes: Amazon reportedly mandated senior-engineer sign-off on AI-generated code after attributing reliability issues to it (contested — see below); the Linux kernel and LLVM now require a human submitter to take explicit ownership of AI-assisted code regardless of origin.
- Addy Osmani's "70% problem": AI reliably produces a plausible first draft, but the remaining ~30% — edge cases, security, integration — still needs engineering judgment. A named framing, not a measured split. [addyosmani.com](https://addyosmani.com/agentic-engineering/the-70-percent-problem/)

## What died in fact-checking

- **METR's "19% slower"** is real but stale: METR itself calls it "out of date" as of Feb 2026, and its own replication attempt produced an unreliable signal. Cite it as a 2025 finding about experienced maintainers, never as a present-tense fact about current tools.
- **Sonar's "64% use autonomous agents / 35% use unsanctioned personal accounts"** could not be traced to any primary Sonar source, unlike the well-confirmed 96/48/42/38/93/88 figures from the same survey. Drop these two or flag as unconfirmed.
- **"Positive sentiment fell from 70%+ to 60%"** (Stack Overflow) is an overstated framing absent from Stack Overflow's own materials, which frame 2025 instead as "33% trust vs. 46% distrust." The four-bucket trust breakdown quoted above is real but omits a ~21.6% "neither" bucket — the cited numbers sum to only ~78%, not 100%.
- **The "C vs. F letter-grade" framing** sometimes attached to the Anthropic RCT does not appear in Anthropic's own materials, which state 50% vs. 67% ("nearly two letter grades"). Note: "Cohen's d=0.738, p=0.01" *was* initially flagged unverifiable during fact-checking, but a direct re-check of Anthropic's page confirms both figures appear there verbatim — they are citable.
- **The Wharton "cognitive surrender" study's "14x" and "11% more confident" figures** trace only to secondary marketing-site summaries, not the primary paper (Shaw & Nave, SSRN:6097646). The study and the term are real; the specific numbers are not confirmed — treat as directional only.
- **Amazon's AI-outage sign-off mandate** is a real reported policy, but Amazon publicly disputed that AI-generated code actually caused the outages used to justify it. A contested claim, not a settled cause-and-effect.
- **An NDC-conference survey (90% use LLMs / 8% merge with zero review / 76% low trust / 80% agree on capability erosion)** could not be traced to any published study; the talk is described as an upcoming, preliminary presentation. None of these four numbers should be repeated as sourced fact.
- **The MIT/Wellesley "Your Brain on ChatGPT" EEG finding** (reduced alpha/beta connectivity in LLM users) is a real preprint (arXiv:2506.08872), but unreviewed, with published critiques of its small sample. Cite as suggestive, not settled.

## Failure modes, concretely

- **The verification gap:** only 48% of developers say they always check AI code before committing, and 38% say reviewing AI output takes *more* effort than reviewing a human's — trust and verification behavior are decoupled.
- **Automation complacency:** decades of human-factors research show complacency occurs under multi-task load in both novices and experts, produces omission and commission errors with imperfect aids, and is not reliably fixed by training alone — "just review carefully" is not a solution this literature supports. [researchgate.net](https://www.researchgate.net/profile/Raja-Parasuraman/publication/47792928_Complacency_and_Bias_in_Human_Use_of_Automation_An_Attentional_Integration/links/09e4150c09890db4c6000000/Complacency-and-Bias-in-Human-Use-of-Automation-An-Attentional-Integration.pdf)
- **Review-without-comprehension:** the Anthropic RCT shows reviewing AI output produces less durable understanding than writing it, even when the reviewer feels confident — review is not a comprehension-equivalent substitute for authoring.
- **The reviewer-is-also-the-author problem:** when one person both generates and reviews their own diff, no independent check exists; documented cases of agents claiming success despite failing tests show this can pass unnoticed without a second, differently-biased check.
- **Volume outpacing review capacity:** coding agents can raise PR volume past what senior reviewers can absorb, and critical context often lives only with the few experienced people repeatedly asked to re-explain it.
- **Unknown unknowns in code you didn't shape:** 22.7% of AI-introduced issues in the 302,600-commit study survived to the latest revision — a proxy for problems nobody caught because nobody who could catch them was looking closely at code they didn't write.

## The strongest objections

- **Abstraction has always meant not understanding the layer below.** Every generation was accused of the same sin (assembly to C to Python); the abstraction wins, understanding migrates to judgment rather than vanishing. [dev.to](https://dev.to/copyleftdev/the-last-honest-abstraction-why-ai-coding-isnt-the-end-of-engineering-213e) Partial rebuttal — median code lifespan is ~2.4 years across 3.3B line/token events, and deleted lines in one 2026 sample had a median lifespan of just 95.7 days: much of what's written won't outlive the sprint that wrote it. [pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC7959608/)
- **Libraries and inherited code are the same problem with old branding.** Teams have always run on unread dependencies and departed engineers' code; "bus factor" is a decades-old named risk, and left-pad is the canonical unread-dependency-breaks-the-world case. Partial — this argues the risk is old, not that it's small.
- **The tools may outrun the debt.** If agents can reliably explain, test, and repair on demand, the comprehension requirement shifts to "can I trust the interface." Partial rebuttal — the best current real-repo code-QA benchmark tops out near 52.7% Pass@1, and 96% of surveyed developers still don't fully trust AI-code correctness: the gap hasn't closed yet.
- **The historical record of skill-loss panics mostly didn't pan out.** Calculator-skill meta-analyses found no general decline, and a 2024 study found IDE-autocomplete users scored *higher* on API knowledge, not lower. Partial — but not every panic was wrong: GPS-linked spatial-memory decline and aviation's "children of the magenta line" automation-dependence problem, validated by the AF447 crash investigation, show the pattern is sometimes real. [bea.aero](https://bea.aero/fileadmin/uploads/tx_elyextendttnews/presentation.rapport.final.05juillet2012.en_04.pdf)
- **Selection bias in the horror stories.** Developers who post "my AI-built app is unmaintainable" might have written unmaintainable code by hand too, and some AI-built software simply wouldn't exist otherwise. Partial — the Farley RCT's null maintainability result supports this, but Cal Newport's reporting also documents a countervailing case: an engineer's AI-exclusive switch was followed by two production crashes his manager attributed to it.
- **"Comprehension" is not operationalized in any of this research.** Program-comprehension studies typically define the construct implicitly by whatever task happens to measure it; one review found only 31 of 409 validity-threat mentions in comprehension studies cited supporting evidence; the tech-debt metaphor itself was already diluted from overuse before AI arrived. This is the strongest objection in the set and is not fully answered by anything in this corpus.

## What survives, stated narrowly

For code that will persist and be extended by humans — not disposable, not glue to a stable library, not fully caught by automated verification — there is real, controlled evidence that accepting AI-generated code and moving on, without asking follow-up questions or explaining it back, produces measurably shallower immediate comprehension than writing the same code yourself, with no offsetting speed gain in the one setting that measured it. This tracks decades of learning-science findings (generation effect, pretesting effect, illusion of competence) that predict exactly this asymmetry, and it is a different construct from code-artifact quality — the Farley RCT found no maintainability difference in the resulting code even where the Anthropic RCT found a real comprehension gap in the person who produced it. The evidence is short-horizon (immediate post-task, not weeks later), concentrated in less-experienced developers on unfamiliar code, and its own authors say it hasn't been shown to generalize to senior engineers, mature codebases, or long-term retention.

When not to worry: throwaway prototypes and spikes meant to be deleted; one-off scripts run once against known data; glue code calling a stable, versioned external API; feature-flagged experiments slated for deletion in weeks; anything fully covered by fast tests plus staging plus one-click rollback; low-stakes internal tooling where a defect costs one person an inconvenience. Median code lifespan (~2.4 years, with deleted lines often under 100 days) means deep comprehension of code you already know is disposable is a bad time allocation.
