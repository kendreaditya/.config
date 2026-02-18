# Knowledge Recap Skill

## Purpose

Combat the "cognitive debt" created by AI conversations. Research shows that AI gives fast, effortless (System 1) access to knowledge but bypasses the slow, effortful (System 2) processing required to actually learn. An MIT study found 83% of ChatGPT-reliant users couldn't recall key points from their own AI-assisted work. However, a Wharton study (Bastani et al., 2024) found that AI *with guardrails* -- where the AI prompts users to solve problems themselves rather than giving direct answers -- improved exam performance by 18% over unassisted controls. This skill implements those guardrails: it uses spaced repetition, retrieval practice, and the generation effect to convert AI conversations into durable knowledge.

## Background: Why You Forget What You Discuss With AI

### The Forgetting Curve (Ebbinghaus, 1885; replicated Murre & Dros, 2015)

| Time After Discussion | Typical Retention (No Review) |
|---|---|
| 1 hour | ~44% remaining |
| 24 hours | ~33% remaining |
| 1 week | ~25% remaining |
| 1 month | ~21% remaining |

### Root Causes

- **Google Effect / Digital Amnesia** (Sparrow et al., 2011, *Science*): People remember *where to find* information rather than the information itself when they know it's accessible. Fisher, Goddu & Keil (2015) showed that Google users rated their *own* knowledge as higher even for topics they hadn't searched -- access to information is confused with possession of knowledge. AI amplifies this because the conversational format feels even more like "thinking" than a search does.

- **Fluency Illusion / Illusion of Competence**: Clear AI explanations create recognition fluency that the brain misinterprets as understanding. Karpicke, Butler & Roediger (2009) showed students who reread material rated their learning as high but performed poorly on delayed tests. Confidence and competence often correlate *negatively* (Kornell & Bjork, 2008).

- **Missing Generation Effect** (Slamecka & Graf, 1978): Generating an answer yourself produces better memory than reading the same answer. Completing "hot:c_ld" leads to better recall of "cold" than reading "hot:cold." AI conversations invert this -- you receive the answer without generating it.

- **No Desirable Difficulty** (Bjork, 1994): The productive struggle AI removes is precisely what builds durable memory. Pre-testing alone raises retention ~30% (Kornell, Hays & Bjork, 2009). The MIT study coined "cognitive debt" to describe the long-term costs of this removal.

- **Metacognitive Laziness**: AI users engage less in planning, monitoring, and evaluation (System 2 functions). While immediate task performance improves, the ability to apply knowledge in novel contexts does not.

- **AI-Amplified Dunning-Kruger**: When AI produces expert-level output on the user's behalf, it eliminates the errors and confusion that normally serve as calibration signals. Users may remain on the peak of overconfidence because the AI prevents them from encountering the failures that would reveal gaps.

## Skill Specification

### Data Sources

The skill relies on a **conversation history database** with two queryable layers:

1. **Daily logs**: Individual conversations searchable by date, with extracted topics, key concepts, and discussion summaries
2. **Monthly digests**: Aggregated topic clusters showing what was discussed across an entire month, with frequency counts and concept relationships

### Review Schedule (Spaced Repetition Intervals)

Based on Ebbinghaus forgetting curve research, the Leitner system, and the optimal spacing ratio (Cepeda et al., 2008: optimal inter-study interval is ~10-20% of the desired retention interval):

| Review | Interval | Focus |
|---|---|---|
| R1 | 1 day | Immediate recall of yesterday's discussions |
| R2 | 3 days | Short-term consolidation |
| R3 | 1 week | Bridge to medium-term memory |
| R4 | 2 weeks | Strengthening medium-term retention |
| R5 | 1 month | Long-term encoding |
| R6 | 3 months | Deep consolidation |
| R7 | 1 year | Permanent retention check |

**Adaptive scheduling**: If a user fails recall at any level, the topic resets to the previous interval. If recall is strong, the topic advances to the next interval. This mirrors the SM-2 algorithm (Wozniak, 1990) used by Anki. Modern FSRS (Free Spaced Repetition Scheduler, Ye, 2022) can further optimize per-topic based on the user's individual forgetting patterns.

**Key research finding**: Rawson & Dunlosky (2011) found that **3 successful spaced retrievals** is the sweet spot for durable learning -- beyond that, diminishing returns set in. Items practiced to 3x correct recall with spacing showed ~80% retention after one week vs. ~35% for items practiced to 1x correct with massing.

### Session Structure: The Recap Conversation

Each session follows a structured flow. The optimal time split based on research (Roediger & Karpicke, 2006; Karpicke & Blunt, 2011; Adesope et al., 2017) is approximately **70% retrieval practice / 30% restudy-elaboration**.

#### Phase 1: Retrieval Priming (Generation Effect)

Before showing any information from past conversations, prompt the user to recall on their own:

```
Over the past [interval], you discussed topics related to [broad category hint].

Before I show you anything:
- What do you remember discussing?
- What were the key takeaways?
- What concepts or facts stood out to you?
```

**Why**: The generation effect shows that attempting retrieval *before* seeing answers strengthens memory far more than passive review. Even failed retrieval attempts improve subsequent learning (Kornell, Hays & Bjork, 2009 -- the "pretesting effect" / "productive failure" yields 20-30% learning gains over direct instruction alone).

#### Phase 2: Targeted Retrieval Practice (Testing Effect)

Ask specific questions derived from past conversation content. Do NOT present the answers -- make the user generate them:

```
Q: You asked about [topic X]. Can you explain [specific concept] in your own words?
Q: What was the key difference between [A] and [B] that we discussed?
Q: You were solving [problem]. What approach did you end up using, and why?
```

**Question types ranked by encoding depth** (Craig et al., 2006; Chi & Wylie, 2014 ICAP framework):
1. **Application/transfer**: "How would you use this in situation X?" (deepest)
2. **Causal/mechanistic**: "Why does this work?" / "What causes X?"
3. **Comparative**: "How is this different from Y?"
4. **Elaborative**: "Can you explain this in your own words?"
5. **Factual recall**: "What is X?" (shallowest, but still valuable)

**Scoring**: Track whether the user answers correctly, partially, or incorrectly. This determines the next review interval for each topic.

| Recall Quality | Action |
|---|---|
| Strong (correct, detailed, fast) | Advance to next interval |
| Partial (correct idea, missing details, slow) | Keep at current interval |
| Weak (incorrect or blank) | Reset to previous interval |

**Confidence calibration**: Before answering, ask the user to rate their confidence (1-5). Track calibration over time. Prioritize items where the user is overconfident (high confidence + incorrect) -- these are the most dangerous knowledge gaps. High-confidence errors, once corrected, are actually remembered better than low-confidence errors (Butterfield & Metcalfe, 2001 -- the "hypercorrection effect").

#### Phase 3: Elaborative Interrogation

For topics the user recalled, push deeper with "why" and "how" questions to strengthen understanding beyond surface-level recall:

```
You correctly recalled [concept]. Now:
- Why does this work the way it does?
- How would you apply this in a different context?
- What would happen if [condition changed]?
- Can you explain this to someone who has never heard of it? (Feynman technique)
```

**Why**: Elaborative interrogation forces connections between new knowledge and existing schemas, creating multiple retrieval pathways. Pressley et al. (1987) showed "why" questions produced ~72% retention vs. ~37% for simply reading facts. The Feynman technique (teaching-back) combines retrieval practice with elaboration, hitting two of the most powerful learning strategies simultaneously. VanLehn (2011) meta-analysis found dialog-based Socratic tutoring produced effect sizes of ~0.76 vs. ~0.40 for non-interactive instruction.

#### Phase 4: Interleaved Review

Mix topics from different conversations and time periods rather than reviewing them in chronological order. This forces the user to discriminate between concepts:

```
Let's mix things up. Consider these three topics you discussed at different times:
1. [Topic from 2 days ago]
2. [Topic from 2 weeks ago]
3. [Topic from 1 month ago]

How do they relate to each other? Are there connections you didn't see before?
```

**Why**: Interleaving (Bjork) produces 20-25% better transfer to novel problems compared to blocked practice. Rohrer & Taylor (2007) showed interleaving improved discrimination and long-term retention by 43% compared to blocked practice.

#### Phase 5: Gap Identification and Correction

Reveal what the user forgot or got wrong, and discuss it conversationally rather than just presenting the answer:

```
Here's what you discussed on [date] that you didn't recall today:
- [Missed concept 1]: [Brief context from original conversation]
- [Missed concept 2]: [Brief context from original conversation]

Let's talk through these briefly. What do you think [missed concept 1] means?
```

**Why**: Corrective feedback after retrieval attempts is more effective than re-reading, especially when the user first attempts to reason about the missed concept. This leverages the hypercorrection effect.

#### Phase 6: Reflection and Forward Scheduling

End the session with metacognitive reflection and scheduling:

```
Session Summary:
- Strong recall: [topics] -- next review in [longer interval]
- Partial recall: [topics] -- reviewing again in [same interval]
- Needs work: [topics] -- reviewing again in [shorter interval]

Reflection:
- What was the hardest thing to recall today? Why?
- What patterns do you notice in what you retain vs. forget?

Your next recap session covers topics from [date range].
```

**Why**: Stefano et al. (2014, Harvard Business School) found workers who spent 15 minutes reflecting on lessons learned performed 23% better after 10 days compared to workers who spent that time on additional practice. Metacognitive reflection has outsized benefits.

### Topic Priority System

Not everything discussed in AI conversations is worth memorizing. Use the **Surprise + Usefulness filter**:

Rate each topic on two dimensions:
- **Surprise** (1-5): How much did this change my understanding?
- **Usefulness** (1-5): How often will I need this?

Only create review items for knowledge scoring >= 3 on at least one dimension and >= 2 on the other.

**Priority signals that a topic is worth retaining:**
1. **User-flagged importance**: Topics the user explicitly marks as "want to remember"
2. **Depth of original discussion**: Multi-turn deep dives suggest higher importance than quick one-off questions
3. **Recurrence**: Topics that come up across multiple conversations
4. **Domain relevance**: Topics aligned with the user's stated learning goals or professional domain
5. **Surprise value**: Information that contradicted prior beliefs (high encoding potential)
6. **Hard to re-find**: Not easily googleable in 10 seconds

**Signals a topic is NOT worth retaining:**
- Easily searchable in seconds (syntax lookups, configuration values)
- Ephemeral details that will change (version numbers, current statistics)
- Tangents unrelated to the user's goals
- The user showed no engagement or curiosity about it

**Tier classification:**

| Tier | Review Schedule | Examples |
|---|---|---|
| Core | Full spaced repetition schedule (R1-R7) | Key professional concepts, important decisions, deep-dive topics |
| Standard | Abbreviated schedule (R1, R3, R5) | Moderately important topics, useful techniques |
| Reference | No active review, searchable | Syntax lookups, one-off questions, configuration details |

### Session Formats by Interval

Different intervals call for different session depths and context matching.

**Graduated context variation** (based on encoding specificity principle, Tulving & Thomson, 1973; combined with desirable difficulty, Bjork & Bjork, 2011):
- **Early reviews (R1-R2)**: Same conversational format as original learning (leverages context-dependent memory for initial consolidation)
- **Mid reviews (R3-R4)**: Mixed format -- some conversational, some direct Q&A
- **Late reviews (R5+)**: Primarily decontextualized -- direct recall, application to novel scenarios (the memory is now robust enough that format variation strengthens it)

**Daily recap (R1, R2)** -- 5-10 minutes
- Quick-fire recall questions in conversational format
- Focus on key facts and takeaways from recent conversations
- 5-8 questions maximum
- Aim for 70% retrieval, 30% elaboration

**Weekly recap (R3)** -- 10-15 minutes
- Retrieval practice + elaborative interrogation
- Interleave topics from different days
- Include 1-2 "teach-back" prompts (Feynman technique)
- Mix conversational and direct Q&A formats

**Monthly recap (R5)** -- 10-15 minutes
- Deep conceptual review
- Focus on connections between topics discussed across the month
- Include application scenarios ("How would you use X in situation Y?")
- Identify knowledge gaps that need dedicated re-learning
- Primarily direct recall and novel application

**Quarterly/Annual recap (R6, R7)** -- 10-15 minutes
- High-level conceptual review only
- Focus on principles and mental models rather than details
- Test transfer to novel contexts
- Flag decayed topics for re-learning cycles

### Integration With Daily Workflow

The skill is designed to be used as a daily check-in, similar to opening Anki:

```
User: /recap

AI: Good morning. Let's do your knowledge recap.

Today's session covers:
- 3 topics from yesterday (R1 review)
- 2 topics from last week (R3 review)
- 1 topic from last month (R5 review)

Estimated session: ~10 minutes.

Let's start. Yesterday you discussed [topic category].
What do you remember about it?
```

### Conversation History Query Patterns

The skill needs to interface with the conversation database using these query patterns:

```
# Get yesterday's conversation topics
GET /conversations?date=yesterday&fields=topics,key_concepts,summary

# Get conversations from N days ago
GET /conversations?date=YYYY-MM-DD&fields=topics,key_concepts,summary

# Get monthly topic digest
GET /conversations/digest?month=YYYY-MM&fields=topic_clusters,frequency,concepts

# Get topics due for review (based on last review date + interval)
GET /review_queue?due_before=today&sort=priority_tier,interval

# Update review status after session
POST /review_status
{
  "topic_id": "...",
  "recall_quality": "strong|partial|weak",
  "confidence_rating": 1-5,
  "response_time_seconds": N,
  "next_review": "YYYY-MM-DD"
}
```

### Knowledge Extraction From Conversations

After each substantive AI conversation, auto-extract 3-7 key learnings using this process:

1. **Identify knowledge atoms**: Discrete facts, concepts, procedures, or insights from the conversation
2. **Apply Surprise + Usefulness filter**: Score each atom, discard low-priority items
3. **Generate multi-format review prompts** for each retained atom:
   - Factual recall: "What is X?"
   - Reverse: "X is the [concept] for which [domain]?"
   - Cloze: "The key advantage of X over Y is ___."
   - Application: "If you encountered [scenario], how would X apply?"
4. **Assign tier and initial review date**
5. **Link back to source conversation** for context retrieval if needed

**Progressive summarization** (adapted from Tiago Forte):
- Layer 1: Raw conversation saved
- Layer 2: Key sentences bolded
- Layer 3: Most important points highlighted
- Layer 4: User writes executive summary in their own words (this IS the learning)

### Anti-Patterns to Avoid

1. **Passive re-reading**: Never just show the user a summary of past conversations. Always require active generation first.
2. **Overwhelming sessions**: Cap daily review at 15 minutes and 10-12 topics. Prioritize ruthlessly. Sustained attention declines after ~20 minutes (Bradbury, 2016).
3. **Binary scoring**: Use a gradient (strong/partial/weak) rather than right/wrong. Partial credit maintains motivation.
4. **Reviewing everything**: Not all AI conversations contain learnable material. Aggressively filter for genuine knowledge.
5. **Skipping the struggle**: Never shortcut the retrieval attempt phase. The discomfort of not-quite-remembering IS the learning mechanism.
6. **Format monotony**: Vary question types (recall, explain, apply, compare) to prevent habituation and autopilot mode.
7. **Ignoring overconfidence**: Track confidence calibration. "Confidently wrong" is the most dangerous state -- the system should specifically target these cases.

### Measuring Effectiveness

Track these metrics over time to validate the skill is working:

- **Recall rate per interval**: What percentage of topics are recalled at each spaced interval?
- **Interval advancement rate**: Are topics consistently moving to longer intervals (indicating consolidation)?
- **Topic decay rate**: How often do topics fall back to shorter intervals?
- **Coverage**: What percentage of "Core" and "Standard" topics have entered the review cycle?
- **Session completion rate**: Is the user actually doing their daily recaps?
- **Confidence calibration accuracy**: Is the gap between predicted and actual recall narrowing over time?

Expected benchmarks with consistent use:
- R1 (1-day) recall: 70-85%
- R3 (1-week) recall: 60-75%
- R5 (1-month) recall: 50-65%
- R7 (1-year) recall: 40-55%

Without the recap skill, 1-year retention of AI-discussed topics is expected to be under 5%.

## Example Session Transcript

```
AI: Good morning. Time for your knowledge recap.

Today's queue:
- 2 topics from yesterday [R1]
- 1 topic from 3 days ago [R2]
- 1 topic from last week [R3]

--- R1: Yesterday's Topics ---

Yesterday you had a conversation about database design.
Before I show details, what do you remember discussing?

User: We talked about database indexing... B-trees I think?
And something about when NOT to use indexes.

AI: Good start. Let me test specifics.

Before you answer, rate your confidence (1-5) on how
well you understand B-tree indexing trade-offs.

User: I'd say a 4.

AI: Noted. Let's see.

Q1: What is the time complexity of a B-tree lookup, and why
does this matter for database queries?

User: O(log n) because of the tree structure... each level
narrows the search space.

AI: Correct. You also discussed a specific scenario where
adding an index actually hurts performance. What was it?

User: Hmm... something about tables with lots of writes?

AI: Partial recall. You discussed that indexes slow down
INSERT/UPDATE/DELETE operations because the index must be
updated alongside the data. You specifically noted that for
write-heavy tables with few reads, indexes create net overhead.

Can you explain WHY the index needs updating on writes?

User: Because the B-tree structure needs to stay sorted, so
inserting a new row means potentially rebalancing the tree.

AI: Strong answer. Now let's go deeper -- you rated yourself
a 4, but you missed the write overhead scenario initially.
That's good to be aware of for calibration.

--- R3: Last Week's Topic ---

Switching context. Last week you discussed Python decorators.
Without any hints -- what is a decorator and why would you
use one?

[Session continues with interleaved topics...]

--- Reflection ---

AI: Session complete.

Summary:
- B-tree lookup complexity: Strong -> next review in 1 week
- Index write overhead: Partial -> reviewing again in 3 days
- Python decorators: [result] -> [next interval]

What was the hardest thing to recall today?

User: The write overhead for indexes. I knew it intuitively
but couldn't articulate it.

AI: That's a common pattern -- recognition without recall.
The fact that you could reason through it when prompted
(rebalancing the tree) shows the knowledge is there but
needs more retrieval practice to become fluent.

Your next recap is tomorrow morning.
```

## References

### Foundational Learning Science
- Ebbinghaus, H. (1885). *Memory: A Contribution to Experimental Psychology*
- Murre, J.M.J., & Dros, J. (2015). Replication and analysis of Ebbinghaus' forgetting curve. *PLOS ONE*
- Craik, F.I.M., & Lockhart, R.S. (1972). Levels of processing: A framework for memory research
- Kahneman, D. (2011). *Thinking, Fast and Slow*

### Desirable Difficulties and Generation Effect
- Bjork, R.A. (1994). Memory and metamemory considerations in the training of human beings
- Bjork, E.L., & Bjork, R.A. (2011). Making things hard on yourself, but in a good way: Creating desirable difficulties to enhance learning
- Slamecka, N.J., & Graf, P. (1978). The generation effect: Delineation of a phenomenon
- Kornell, N., Hays, M.J., & Bjork, R.A. (2009). Unsuccessful retrieval attempts enhance subsequent learning

### Testing Effect and Retrieval Practice
- Roediger, H.L., & Karpicke, J.D. (2006). Test-enhanced learning. *Psychological Science*
- Karpicke, J.D., & Blunt, J.R. (2011). Retrieval practice produces more learning than elaborative studying. *Science*
- Karpicke, J.D., & Roediger, H.L. (2008). The critical importance of retrieval for learning. *Science*
- Rowland, C.A. (2014). The effect of testing versus restudy on retention: A meta-analytic review
- Adesope, O.O., et al. (2017). Rethinking the use of tests: A meta-analysis of practice testing

### Spacing Effect
- Cepeda, N.J., et al. (2006). Distributed practice in verbal recall tasks: A review and quantitative synthesis. *Psychological Bulletin*
- Cepeda, N.J., et al. (2008). Spacing effects in learning: A temporal ridgeline of optimal retention. *Psychological Science*
- Rawson, K.A., & Dunlosky, J. (2011). Optimizing schedules of retrieval practice for durable and efficient learning

### Metacognition and Illusions of Competence
- Karpicke, J.D., Butler, A.C., & Roediger, H.L. (2009). Metacognitive strategies in student learning
- Kornell, N., & Bjork, R.A. (2008). Learning concepts and categories: Is spacing the enemy of induction?
- Kruger, J., & Dunning, D. (1999). Unskilled and unaware of it
- Butterfield, B., & Metcalfe, J. (2001). Errors committed with high confidence are hypercorrected

### AI and Cognitive Offloading
- Sparrow, B., Liu, J., & Wegner, D.M. (2011). Google effects on memory. *Science*
- Fisher, M., Goddu, M.K., & Keil, F.C. (2015). Searching for explanations: How the Internet inflates estimates of internal knowledge
- Bastani, H., et al. (2024). Generative AI can harm learning. Wharton working paper
- MIT Generative AI & Cognitive Function Study (2025). Effects of LLM reliance on memory, creativity, and neural connectivity

### Elaboration, Reflection, and Socratic Method
- Pressley, M., et al. (1987). Elaborative interrogation facilitates acquisition of confusing facts
- Chi, M.T.H., et al. (1989). Self-explanations: How students study and use examples in learning
- Stefano, G.D., et al. (2014). Learning by thinking: How reflection aids performance. Harvard Business School
- VanLehn, K. (2011). The relative effectiveness of human tutoring, intelligent tutoring systems, and other tutoring systems
- Craig, S.D., et al. (2006). Deep-level reasoning questions effect
- Chi, M.T.H., & Wylie, R. (2014). The ICAP framework

### Interleaving and Context
- Rohrer, D., & Taylor, K. (2007). The shuffling of mathematics problems improves learning
- Tulving, E., & Thomson, D.M. (1973). Encoding specificity and retrieval processes in episodic memory

### Spaced Repetition Systems
- Wozniak, P.A. (1990). SM-2 algorithm. SuperMemo
- Ye, J. (2022). FSRS: Free Spaced Repetition Scheduler
- Dunlosky, J., et al. (2013). Improving students' learning with effective learning techniques. *Psychological Science in the Public Interest*
