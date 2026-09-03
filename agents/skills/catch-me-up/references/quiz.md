# Writing the quiz

The quiz's whole job is to distinguish **understanding** from **fluency** — the feeling that
something made sense while reading it. Those come apart badly. The failure this catches is
real and specific: Litt's account is sending a PR he believed he'd read, then being asked the
most basic question by a coworker and having no answer.

## Difficulty target

Medium. Hard enough that answering requires understanding the substance of the change; never
a gotcha. Concretely, a good question is one where:

- Someone who read the diff carefully but didn't build a model gets it wrong.
- Someone who understands the mechanism gets it right without re-opening the file.
- The wrong options are all things a reasonable person might believe.

A bad question is answerable from the section headers, tests trivia (line numbers, filenames,
argument order), or has three obviously-wrong options and one obviously-right one.

## What to ask about

Draw the five from different layers, not five variants of one question:

1. **Mechanism** — what actually happens at the step that matters. "When X arrives, which
   component decides Y?"
2. **Why-this-design** — the load-bearing decision. "Why does this cache the transform instead
   of recomputing it?" The best single question type; the one lever a controlled AI-coding trial
   confirmed preserved comprehension was asking *why* a piece is valid rather than *what* it does.
3. **Propagation** — "If requirement R changed, which file do you open first?" This is the
   question that predicts whether they can actually own the code.
4. **Failure mode** — what breaks, and how it surfaces. "If the upstream returns null here,
   what does the user see?"
5. **Boundary** — what this change deliberately did *not* touch, and why.

## Distractors

Each wrong option should be a **specific plausible misconception**, ideally one you can imagine
a reader forming from the diff alone. Options that are merely vague or obviously silly convert
the question into a giveaway and the quiz into theater.

Good distractor: the thing the old code did before this change.
Good distractor: the thing that would happen if you misread the direction of a transform.
Bad distractor: "the system crashes" when nothing crashes anywhere.

## Grading

You grade, live. That is the entire reason not to embed a self-grading page.

- **Correct** → confirm in one clause and move on. No praise.
- **Wrong** → name the specific misconception the chosen option represents, then correct it.
  Not "incorrect, the answer is B" — *why* the answer they picked is attractive and where it
  diverges. Then offer one follow-up on that same point, because the retention benefit is
  item-specific and doesn't spread.
- **"Other" / free text** → grade it on substance, not wording. A right answer phrased
  unexpectedly is a right answer.

## When the gate fails

Two or more wrong means the explanation didn't land. Say so plainly — no softening, no "close
enough."

Then do the cheapest thing that fixes the specific gap, rather than re-explaining everything:

- Missed the mechanism → walk the data flow again with concrete values, not prose.
- Missed why-this-design → state the alternative that was rejected and what it would have cost.
- Missed propagation → have them trace one requirement change out loud.
- Missed everything → the explanation probably led with the change. Redo Background and
  Intuition; that ordering failure is the usual cause.

Do not proceed to the next task as though the gate passed, and do not hand the change to a
human reviewer. The point of a gate is that it is load-bearing.

## What this is not

Not a test of the user, and never framed as one. It is an instrument aimed at the *explanation*
— when someone fails a question, the first hypothesis is that the document was unclear, not
that they weren't paying attention. Say that when it happens.

Delayed spaced-repetition quizzing (re-testing days later) is deliberately excluded. It is
pedagogically well-supported and it is the first thing everyone drops; a gate that runs once,
at the moment it blocks something, survives.
