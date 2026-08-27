# The Pre-AI Canon on Technical Debt and System Understanding

*Load this when a claim needs pre-AI grounding — the original meaning of "debt," the complexity/theory-building literature, or evidence for which practices built shared understanding — so you don't reinvent or misattribute what the discipline already knew.*

## What "debt" originally meant

- Ward Cunningham coined the metaphor in his 1992 OOPSLA experience report on the WyCash portfolio management system — the earliest documented use. [Wikipedia](https://en.wikipedia.org/wiki/Ward_Cunningham)
- His own framing: "Shipping first time code is like going into debt. A little debt speeds development so long as it is paid back promptly with a rewrite." [Wikipedia](https://en.wikipedia.org/wiki/Technical_debt)
- Cunningham's own gloss is about a mismatch between the code and the team's *current* understanding of the problem, not about ugly code.
- His words: failing to align the program with what the team had come to understand as the right way to model the domain meant "we were going to continue to stumble on that disagreement, which is like paying interest on a loan." [Agile Alliance](https://www.agilealliance.org/introduction-to-the-technical-debt-concept/)
- That debt is paid down via rewrite as understanding matures — a claim about cognitive alignment between code and current understanding, not about tidiness.
- The popular reading — debt equals sloppy or messy code — drifts from that original financial analogy.
- Cunningham's own examples are about incomplete understanding of the problem domain, which prudent, competent teams accrue too, not just careless ones.
- Fowler's Technical Debt Quadrant crosses two axes — reckless/prudent and deliberate/inadvertent — into four named cases. [Fowler](https://martinfowler.com/bliki/TechnicalDebtQuadrant.html)
  - Deliberate-reckless: "no time for design," which usually backfires because good design actually speeds development up.
  - Deliberate-prudent: a conscious shortcut taken with an accepted, evaluated future cost.
  - Inadvertent-reckless: debt from not yet knowing better design practice.
  - Inadvertent-prudent: the design flaw a competent team only sees once they've built the thing and learned, mid-project, what the right design actually was.
- Fowler: "The debt metaphor reminds us about the choices we can make with design flaws" — the reckless/prudent distinction is the point, not whether something technically qualifies as "debt." [Fowler](https://martinfowler.com/bliki/TechnicalDebtQuadrant.html)
- The inadvertent-prudent quadrant is where the financial parallel strains hardest: it's hard to explain to a manager why debt appeared despite a competent team doing careful work — debt without negligence. [Fowler](https://martinfowler.com/bliki/TechnicalDebtQuadrant.html)
- The metaphor is contested on its own pre-AI terms, independent of any AI question: Kruchten, Nord & Ozkaya (2012) document the term becoming "diluted" from overuse. [Kruchten et al. 2012](https://smallake.kr/wp-content/uploads/2015/09/2012_019_001_58818.pdf)
- "Comprehension" has the same problem one level down: program-comprehension research typically defines the construct implicitly, by whatever the experimental task happens to measure, rather than by one agreed definition. [Wyrich 2023](https://arxiv.org/pdf/2310.11301)
- A review of 409 validity-threat mentions across human-centric SE experiments found only 31 cited supporting evidence.
- For the three most-invoked threats in that same review, 17 of 18 supporting citations didn't meet evidence criteria — a caution against treating any single comprehension metric as more settled than it is. [Munoz Baron et al.](https://arxiv.org/abs/2301.10563)
- Kenny Rubin's awareness-level framework, cited in general technical-debt writing, splits debt by whether the team knows it's there: "happened-upon" (unknown until discovered), "known" (visible but unscheduled), "targeted" (visible and scheduled for repayment). [Wikipedia](https://en.wikipedia.org/wiki/Technical_debt)
- That is a taxonomy of the team's *epistemic* relationship to the debt, not of the code's condition — the same move Cunningham's original framing makes.
- On interest accrual: the standard description is "escalating integration costs" and progressively "riskier and costlier" future modification.
- At the extreme, "entire engineering organizations" can be "brought to a stand-still under the debt load" when it's left unpaid long enough. [Wikipedia](https://en.wikipedia.org/wiki/Technical_debt)

## The complexity canon

- Lehman's Laws of software evolution, eight in total (1974-1996), of which three are load-bearing here. [Wikipedia](https://en.wikipedia.org/wiki/Lehman%27s_laws_of_software_evolution)
  - **Continuing Change** — "an E-type system must be continually adapted or it becomes progressively less satisfactory."
  - **Increasing Complexity** — complexity increases "unless explicit work is done to maintain or reduce it."
  - **Declining Quality** — quality "will appear to be declining unless it is rigorously maintained."
- The remaining five round out the same picture. [Wikipedia](https://en.wikipedia.org/wiki/Lehman%27s_laws_of_software_evolution)
  - **Self Regulation** — evolution is a self-regulating process with normally-distributed measures, not a smooth curve.
  - **Conservation of Organisational Stability** — effective activity rate stays roughly constant over a system's life, i.e. a team can't just permanently accelerate.
  - **Conservation of Familiarity** — average incremental growth per release stays invariant, because mastering the system caps how much change people can absorb at once.
  - **Continuing Growth** — functional content must keep increasing to sustain user satisfaction.
  - **Feedback System** — evolution is a "multi-level, multi-loop, multi-agent feedback system" that must be managed as one, not decomposed into independent parts.
- Read together: continuing change is mandatory, it drives complexity up by default, complexity drives quality down by default, and the pace at which people can absorb the resulting change is itself bounded.
- Four separate empirical claims that jointly explain why "just add more changes faster" was never a stable strategy, even before AI raised the ceiling on how fast changes can be produced.
- Brooks, "No Silver Bullet": complexity splits into accidental and essential. [Wikipedia](https://en.wikipedia.org/wiki/No_Silver_Bullet)
  - Accidental complexity is self-inflicted — e.g. low-level implementation detail — and addressable by better tools and languages.
  - Essential complexity is inherent to the problem itself: thirty required functions are thirty requirements, full stop, and no tool removes them.
- Brooks's claim: no single technique promises a tenfold improvement within a decade, because most remaining effort is essential, not accidental, complexity.
- Brooks on conceptual integrity (*The Mythical Man-Month*): a usable system needs one coherent design vision, achievable only by "separating architecture from implementation." [Wikipedia](https://en.wikipedia.org/wiki/The_Mythical_Man-Month)
- That vision is ideally held by a single chief architect or small group acting on the user's behalf, because "if a system is too complicated to use, many features will go unused."
- Fewer, well-integrated features beat a maximal feature set nobody can hold in their head.
- The conceptual-integrity argument generalizes past one human architect: it requires that *some* small, identifiable set of minds is accountable for the system's coherence and can reject additions that don't fit.
- An agent generating code at high volume across many sessions has no mechanism to enforce that constraint on itself.
- Parnas (1972) on information hiding: organize modules around the design decisions most likely to change, not around function or flowchart step. [Wikipedia](https://en.wikipedia.org/wiki/Information_hiding)
- That way, a change to one decision — e.g. how a data structure is represented — stays local instead of rippling globally.
- A side effect is comprehension: a developer can use a module correctly from its interface alone, without mastering its internals.
- Parnas's point is specifically about *localizing* the cost of not-fully-understanding a system — the pre-AI answer to "how much of this do I need to hold in my head to make this one change safely."
- Ousterhout (*A Philosophy of Software Design*) defines complexity as "anything related to the structure of a software system that makes it hard to understand and modify." [summary](https://www.goodreads.com/book/show/39996759-a-philosophy-of-software-design)
- He diagnoses it via three symptoms:
  - **Change amplification** — a simple, conceptually small change requires edits scattered across many places because the design didn't localize it.
  - **Cognitive load** — how much a developer must hold in their head simultaneously to work on the code safely, independent of line count; short code that relies on unstated assumptions can have high cognitive load.
  - **Unknown unknowns** — the most dangerous symptom: not knowing which code needs to change for a given task, or what you'd even need to know to be confident you're asking the right question.
- Managing these three symptoms is, in his framing, the actual job of software design.
- His "tactical programming" (get this one thing working now) trades all three away for short-term speed — the pre-AI name for the failure mode an agent optimizing purely for "make the tests pass" will default to unless explicitly steered otherwise.

### Naur: the program text is a residue, the theory lives in heads

- Peter Naur's 1985 "Programming as Theory Building" is the load-bearing source for this skill. [Naur 1985](http://pages.cs.wisc.edu/~remzi/Naur.pdf)
- His claim: programming is properly "an activity by which the programmers form or achieve a certain kind of insight, a theory, of the matters at hand" — not, as the common notion has it, the production of a program and other texts.
- He borrows Gilbert Ryle's notion of "theory": a person has a theory when they don't just do something correctly, but can support that doing with explanations, justifications, and answers to queries about it.
- Crucially, having a theory also means recognizing new situations as similar to ones the theory already covers — the way someone who truly has Newton's theory of mechanics recognizes its bearing on a pendulum or a planet without being told.
- This knowledge "could not, in principle, be expressed in terms of rules" — the relevant similarities between situations are of the same kind as similarities between faces, tunes, or wine.
- That is exactly why documentation, which is necessarily rule- and fact-shaped, cannot substitute for it.
- The programmer's knowledge exceeds anything written down in three specific ways:
  1. Explaining how the solution's structure maps onto the real-world activity it serves, including the judgment call of which parts of the world are even relevant.
  2. Explaining *why* each part of the program text is what it is, down to a final, irreducible justification resting on the programmer's own direct, intuitive knowledge.
  3. Responding constructively to a demand for modification, by perceiving the right kind of similarity between the new demand and what the program already does.
- Documentation reliably captures none of these three.
- Case 1, his central example: group A builds a compiler and documents it exhaustively for group B — full annotated program text, extensive design discussion, plus ongoing personal advice.
- Group B still repeatedly proposed changes that "made no use of the facilities... inherent in the structure of the existing compiler but... discussed at length in its documentation," instead patching around it in ways that "destroyed its power and simplicity."
- Group A could spot and fix this instantly because they had the theory, not because they'd read more of the text.
- Ten years later, with no one from group A left, the original structure was "still visible" but had been made "entirely ineffective by amorphous additions."
- Case 2: a 200,000-line real-time monitoring system whose installation-and-fault-diagnosis programmers, after years of continuous contact with the system, could resolve faults from "almost exclusively" their "ready knowledge of the system and the annotated program text."
- Other programmer groups, given the same documentation and full producer guidance, regularly hit problems traceable to "inadequate understanding of the existing documentation," resolved only by consulting the programmers who held the theory.
- Naur's conclusion from both cases: "the continued adaptation, modification, and correction of errors" in large programs is "essentially dependent on a certain kind of knowledge possessed by a group of programmers who are closely and continuously connected with them" — not on the completeness of the documentation they leave behind.
- His formulation of program life and death: "The death of a program happens when the programmer team possessing its theory is dissolved."
- A dead program can keep running and producing correct output; death becomes visible only when a modification is demanded and "cannot be intelligently answered."
- Revival means a new team rebuilding the theory, not reading the code more carefully.
- He explicitly rejects the common expectation that program modifications should be cheap because "a program is a text held in a medium allowing for easy editing" — on the Theory Building View "this whole argument is false," because cost is set by whether the modifier holds the theory, not by how easy the text is to retype.
- This is the same claim Lehman's Declining Quality law makes from the systems-evolution side: quality decays specifically when modification proceeds without the understanding that would keep it sound.
- Consequence for onboarding: it is not enough for a new programmer to become familiar with the program text and documentation.
- What's required is working in close contact with programmers who already hold the theory — an apprenticeship, structurally like learning to write or play an instrument, not a reading assignment.
- Practical upshot for this skill: source code is Naur's "documentation" — a real but insufficient artifact. If no human ever held the theory of a piece of code, that code was never alive in Naur's sense, whatever its test coverage or how clean the diff looks.

## Feathers: legacy code is any code without a theory-holder

- Michael Feathers' definition, deliberately not about age: "Legacy code is code without tests." [understandlegacycode.com](https://understandlegacycode.com/blog/key-points-of-working-effectively-with-legacy-code)
- Code can be six weeks old and already legacy by this definition — age and cleanliness are irrelevant to the label.
- His techniques for building understanding of code you didn't write, before you touch it:
  - **Characterization tests** — "a test that characterizes the actual behavior of a piece of code," pinning down what the code currently does, not what it's supposed to do, giving a safety net for change without requiring full understanding first.
  - **Seams** — "a place to alter program behavior, without changing the code" at that place; in OO languages, classes often serve as convenient seams, letting you substitute or mock a dependency to isolate and study one piece of behavior in controlled conditions.
  - **Sprout method/class** — when time is short, put new logic in a new, separately testable method or class and call it from the legacy code, rather than editing untested code directly.
  - **Scratch refactoring** — deliberately make unsafe, throwaway edits purely to build understanding of how a change would ripple, then discard them and make the real, tested change afterward.
- The order matters: get a test-based safety net around code first, *then* change it — the tests are how you externalize a provisional theory of the code's behavior before you have a full one, and the act of writing them is itself what builds the understanding.
- These techniques transfer directly to AI-written code, and the transfer is not metaphorical: by Feathers' own definition, code an agent just generated is legacy code the moment it lands, whether or not anyone reviewed it, because "no tests written by a theory-holding human" is exactly the condition his definition names.
- The pre-AI toolkit for approaching code nobody currently understands is the toolkit this situation calls for by default, not an analogy borrowed from a different problem.
- Concretely: an agent's freshly generated function has the same epistemic status Feathers assigns a decade-old, undocumented, untested module inherited from a departed colleague — being five minutes old and fluent-sounding changes nothing about whether a human currently holds a theory of it. Seams, characterization tests, and sprout method/class apply to it unmodified.

## Practices that transferred understanding in pre-AI teams

- **Review-as-comprehension.**
  - Capers Jones's analysis of 12,000+ projects found formal (Fagan-style) inspection catches 60-65% of latent defects versus under 50% for informal inspection and roughly 30% for testing alone. [Wikipedia](https://en.wikipedia.org/wiki/Code_review)
  - A competing case study in *Best Kept Secrets of Peer Code Review* found lightweight review catches comparably many bugs, faster and cheaper — the evidence for formal-versus-lightweight review is itself contested.
  - Recommended pace across this literature is 200-400 lines/hour, with "more than a few hundred lines per hour" flagged as too fast for safety-critical code.
  - Separately, up to 75% of review comments concern evolvability/maintainability rather than functionality, and under 15% relate directly to bugs.
  - That split is the evidence that review's main pre-AI function was spreading understanding across a team, not just catching defects.
- **Pair programming.**
  - Knowledge transfer is constant and bidirectional between partners. [Wikipedia](https://en.wikipedia.org/wiki/Pair_programming)
  - "Promiscuous pairing" — deliberately rotating who pairs with whom — was used explicitly to spread system knowledge across a whole team rather than let it pool in one head.
  - A meta-analysis found pairs consider more design alternatives, reach simpler and more maintainable designs, and catch design defects earlier than solo programmers.
  - The same literature documents a net productivity drop when pairing is applied to simple, already-well-understood tasks — the technique has a real cost, and pre-AI teams paid it selectively, not universally.
- **Design docs / RFCs / ADRs.**
  - Nygard's case for Architecture Decision Records: without a record of *why*, a new team member facing an old decision can only "blindly accept" or "blindly change" it. [Cognitect](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
  - Enough unexamined decisions make a team "afraid to change anything" until "the project collapses under its own weight."
  - His prescribed remedy is deliberately lightweight — one or two pages, Title/Context/Decision/Status/Consequences, written "as if a conversation with a future developer" — precisely so it actually gets read and kept current rather than abandoned as overhead.
  - Internet RFCs, decades earlier, solved a related but distinct problem: letting a distributed group propose and refine a design in writing, through open peer comment, before anything was standardized or built.
  - That is evidence-gathering-before-commitment, a separate discipline from ADRs' decision-recording-after-commitment.
- **Code reading as deliberate practice.** Spinellis's *Code Reading* treats reading other people's code as a distinct, teachable skill with its own techniques, not something that falls out automatically from writing code — "if you make a habit of reading good code, you will write better code yourself." [spinellis.gr](https://www.spinellis.gr/codereading/)
- **Production ownership and on-call.**
  - Developers being on-call for software they personally built is documented as standard practice at Google, Amazon, Dropbox, Spotify, and Netflix. [Increment](https://increment.com/on-call/)
  - The mechanism ties comprehension to consequence: the person paged at 3am is, by pre-AI default, the same person who holds the theory of the code that broke.
  - That is Naur's theory-holder requirement enforced by organizational design rather than left to individual choice.
- **Chesterton's Fence.** From G.K. Chesterton's 1929 *The Thing*: "If you don't see the use of it, I certainly won't let you clear it away. Go away and think" — contrasting the reformer who removes what they don't understand against the one who investigates its purpose first. Applied to code: don't delete or "clean up" something until you know why it's there, because the absence of a visible reason is not evidence that there isn't one.

## What AI-assisted development quietly removed

- **Review-as-comprehension** breaks specifically when the same person is both author and reviewer, or review is a rubber stamp — the mechanism assumed a second mind encountering the code fresh, at a human-sustainable pace of roughly 200-400 lines/hour.
- Accepting an agent's diff without that second mind, or skimming a diff far faster than that rate to keep up with agent output volume, means the step is either skipped entirely or performed below the pace the pre-AI evidence says catches anything.
- **Naur's theory-transfer-by-apprenticeship** has no agent equivalent: an agent can produce documentation and explain its own code on request, but it cannot be the thing Naur says a new programmer needs — a human who already holds the theory, working in close contact over time.
- If no human built the theory in the first place, there is no theory to transfer, and no amount of asking the agent to "explain it again" manufactures one — the theory Naur describes is inseparable from having lived through the design decisions, not from being told about them afterward.
- **Pair programming's promiscuous knowledge-spread** disappears in a solo-developer-plus-agent setup: there is no second human absorbing context by rotation, so system knowledge stops distributing across a team by default and starts pooling in whichever single person happened to run the session.
- **ADRs and design docs** are vulnerable to a quiet substitution that no gate catches by inspection alone: a spec file that exists and is technically "approved" says nothing about whether a human authored its reasoning or merely rubber-stamped an agent's draft.
- The artifact Nygard describes can be fully present in the repository while the thing it was meant to preserve — a human's own working-through of the tradeoff — is entirely absent.
- **Chesterton's Fence** assumes someone is around who remembers, or can be asked, why the fence is there; an agent asked to refactor or delete code has no standing memory of intent and will clear the fence as readily as it would build one, unless the "why" was captured in writing beforehand.
- An agent generating new code just as readily builds fences whose purpose it alone currently knows, seeding the exact same problem for whoever encounters that code next.
- **Feathers' forcing function** — you had to write characterization tests before touching code you didn't understand, and that act of writing them is what built the understanding — is easy to skip when the agent's first pass already looks done and already includes tests it wrote itself.
- That removes the exact friction that used to force a human through the comprehension step before modification, not just before merge.
- **Production ownership's consequence-linkage** weakens whenever the person who will be paged did not write, or closely direct, the code that broke.
- On-call only forces theory-holding if the on-call engineer was the one building the theory in the first place; a purely delegated, unreviewed agent session severs that link even when the on-call rotation itself stays formally unchanged.
