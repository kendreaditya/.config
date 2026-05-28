# Roblox ML Interview Prep — Ads Discovery Team
**Interview Date:** Thursday, June 4, 2026 — 10:30am–11:30am PT  
**Interviewers:** Zhen Zhang (Senior MLE) + Yilun Xu (Principal ML Infra Engineer)  
**Format:** 60 min — ~15 min intro + ML discussion + rapid-fire ML questions, ~45 min coding (CodeSignal)

---

## Interview Structure (What Santosh Described)

### Round 1 — This Interview (Phone Screen, 60 min)
- **15 min:** Intro, background chat, ML technique discussion, rapid-fire ML questions
- **45 min:** One coding problem — medium to advanced LeetCode level (no ML, pure DSA)

### Round 2 — Onsite (3 sessions)
1. ML Modeling deep dive (60 min)
2. Project deep dive — pick one accomplishment, present to 2 engineers (60 min)
3. Behavioral with Hiring Manager (45 min)

### Round 3 — Exec
- Behavioral with a Director (45 min)

---

## What Roblox Ads Team Actually Does

From the recruiter call + job context:
- **Ads on Roblox** = Year 2, very early. Currently ads on home feed and search surfaces only.
- **Vision:** Immersive ads, avatar wearable purchases (Nike hoodie on avatar → real purchase)
- **Team:** ~11-12 people, ~60% MLE, ~40% ML Infra
- **Discovery = Home Feed + Search + Ads & Brands**
- The full recommendation pipeline: retrieval → ranking → blending
- They want: two-tower models, Transformer architectures, RL, GNN — stated by Santosh explicitly

---

## Coding — What Gets Asked at Roblox MLE

### Confirmed from real interview writeups

**Rate Limiter** — single most repeated Roblox coding question:
```
Phase 1: sliding window rate limiter (per user)
Phase 2: rate limiter per user AND per experience (game)
         — user AND (user, game) combination must both pass limits
```
LeetCode analog: [LC-362 Design Hit Counter](https://leetcode.com/problems/design-hit-counter/)

**Match-3 Grid** — appeared in Senior MLE phone screen (same level as yours):
```
Stage 1: given a grid of ints, find all horizontal + vertical runs of 3+ identical values
         output (value, count) pairs — vertical first, then horizontal, L→R T→B
Stage 2: zero out matched cells, then "sink" remaining values downward (gravity)
```
Key: careful traversal order, two separate passes, in-place grid mutation.

**Call Stack Parsing** — appeared in IC3 onsite (your equivalent level):
```
Given log lines like: "0:func_a:start", "5:func_a:end", "3:func_b:start"
Find function called most frequently, or compute exclusive times per function.
```
LeetCode: [LC-636 Exclusive Time of Functions](https://leetcode.com/problems/exclusive-time-of-functions/)

**Topological Sort / Avatar Loader** — appeared in phone screens:
```
Given components and dependencies, return valid load order.
If multiple orderings exist, preserve original input order (use priority queue keyed by index).
If circular dependency → return ["Error!"]
```
LeetCode: [LC-210 Course Schedule II](https://leetcode.com/problems/course-schedule-ii/)

**Merge Intervals + Meeting Rooms** — appeared in onsite:
- [LC-56 Merge Intervals](https://leetcode.com/problems/merge-intervals/)
- [LC-253 Meeting Rooms II](https://leetcode.com/problems/meeting-rooms-ii/)

**Other confirmed Roblox problems:**
- [LC-146 LRU Cache](https://leetcode.com/problems/lru-cache/)
- [LC-811 Subdomain Visit Count](https://leetcode.com/problems/subdomain-visit-count/)
- [LC-239 Sliding Window Maximum](https://leetcode.com/problems/sliding-window-maximum/)
- [LC-200 Number of Islands](https://leetcode.com/problems/number-of-islands/)

### Roblox coding interview culture (from IC3 pass writeup)
> "Roblox doesn't like it if you aren't able to one-shot the solution and spend a lot of time debugging."
- Write it right the first time. Think before typing. Narrate edge cases you're considering.
- They use CodeSignal with time pressure — watch the clock.
- Spend time on edge cases upfront: empty input, single element, circular dependencies, duplicate values.

---

## ML Fundamentals — Rapid-Fire Questions to Expect

Confirmed from the **Senior MLE phone screen writeup** (same format as your round):

### Confirmed questions from that writeup:
1. **What loss function is used for classification? Write the formula.**
   - Binary: `L = -[y·log(p) + (1-y)·log(1-p)]`
   - Multiclass: `L = -Σ y_i · log(p_i)`
   - For CTR prediction (binary): binary cross-entropy, sigmoid output

2. **How do you handle categorical features?**
   - Low cardinality: one-hot encoding
   - High cardinality (user IDs, item IDs): learned embeddings (lookup table, trained end-to-end)
   - Very high cardinality: feature hashing (hash trick) — trade collision rate for memory
   - Target encoding: replace category with mean of target (watch for leakage)

3. **What do you do if there's a long-tail phenomenon with ID-type features?**
   - Frequency thresholding: collapse IDs with < N impressions into a single `<UNK>` bucket
   - Log-frequency bucketing: group by log-frequency bin, assign shared embedding
   - Two-stage: train a content-based embedding for cold items, fine-tune with ID embedding when warm
   - Hash IDs into a fixed table size — compresses tail implicitly (collision is acceptable)
   - Warm-start cold items with side-features (item content, category, age)

### Additional ML topics — expect these given the team context:

**Two-Tower Models (TTSS / DSSM):**
- User tower encodes user features → user embedding
- Item tower encodes item features → item embedding
- Dot product → relevance score for retrieval (ANN search at inference)
- Trained with in-batch negatives + hard negatives
- Why two-tower: user and item embeddings can be precomputed and indexed

**Retrieval → Ranking → Blending pipeline:**
- **Retrieval:** billions → thousands; approximate nearest neighbor (FAISS, ScaNN); two-tower; candidate recall
- **Ranking:** thousands → dozens; full feature interaction; DCN-v2, DIN, DLRM; log loss; feature importance
- **Blending/Re-ranking:** dozens → final list; diversity (MMR), business rules, ads injection, position bias correction

**CTR / Ads-specific:**
- Expected value: `pCTR × pCVR × bid_price` — Roblox ads will use this
- Calibration: model may be well-ranked but uncalibrated — Platt scaling, isotonic regression
- Explore/exploit: epsilon-greedy, Thompson sampling, UCB (LinUCB for contextual bandits)
- Delayed feedback problem in CVR: label delay, importance weighting

**Transformers for RecSys:**
- SASRec: self-attention on user action sequence for next-item prediction
- BERT4Rec: bidirectional masked item prediction
- BST (Behavior Sequence Transformer): embeds user behavior sequence into ranking model

**RL for Recommendations:**
- Bandit framing: reward = engagement signal, action = which ad to show
- DQN / policy gradient when sequential reward matters (session-level)
- Offline RL: inverse propensity scoring to correct for logging policy bias

**GNN for RecSys:**
- PinSage (Pinterest): GraphSAGE on bipartite user-item graph
- Use when collaborative filtering signal is sparse and item-item similarity matters

**Evaluation metrics:**
- Offline: AUC-ROC, log loss, NDCG@k, MAP@k, Recall@k
- Online: CTR, CVR, RPM (revenue per thousand impressions), GMV
- Be careful: offline AUC improvement ≠ online metric improvement; always A/B test

**Model drift / training loop:**
- Online learning vs periodic retraining
- Feature drift detection: PSI (population stability index), KS test
- Label drift: distribution shift in user engagement patterns
- Retraining triggers: performance degradation threshold, time-based schedule

**Data pipelines:**
- First-party signals: on-platform engagement (clicks, plays, time-in-game)
- Third-party signals: advertiser conversion data (needs privacy-preserving aggregation)
- Batch vs streaming features: use Kafka + Flink for real-time feature computation
- Feature store: offline (training) vs online (serving) feature consistency

---

## System Design — What Roblox SD Rounds Look Like

**Confirmed from real IC3 interviews:**
- Like/Unlike system at high scale (1M QPS) — Kafka + Flink + Redis
  - Functional: like/unlike, get total count, check if user liked
  - Scale: hot item problem, write amplification, counter sharding
- Marketplace bookmarking / Favorites system with social proof ("X has played this game")
- Delayed payment / payment hold-and-release system
- Multiplayer matchmaking (group by skill level into sessions of 16)
- Rate limiter at scale

**Roblox SD twists:** questions are usually Roblox-flavored (avatar loading, game sessions, marketplace). They dig deep on scale and go beyond the basic design into every detail.

---

## Behavioral — Key Themes

From IC3 pass writeup: **heavy emphasis on high-traffic and scale systems in past experience.**

Map your Meta experience to these:
- "Tell me about a system you built that handled significant scale" → your ranking pipeline, QPS numbers
- "Tell me about a time you debugged a production ML issue" → model drift, signal drift, data pipeline failures
- "0-to-1 project" → they're hiring founding members of Ads team; show you can build from scratch
- "Disagreed with a technical decision" → standard

**Creativity round** (may appear in onsite): Roblox-specific. "How would you redesign X?" Think gaming context. Practice: how would you redesign the Roblox matchmaking lobby? How would you improve the avatar marketplace?

---

## Your Background → Their Needs (Quick Mapping)

| What you've done | What they need |
|---|---|
| TTSM two-tower sparse network at Meta | Two-tower retrieval for ads |
| Transformer/CNN recommenders (level 2/3 ranking) | Ranking model for Roblox ads |
| Trimming billions → hundreds via product signals | Retrieval → ranking → blending pipeline |
| First + third party signal ingestion (Amazon, Temu) | Cross-platform signal integration |
| Model drift + evaluation + A/B testing | Same — they're building from scratch |
| Kafka + data pipelines + monitoring | ML infra for ads serving |

You're a very strong match. Frame your Meta work explicitly in terms of the stages Santosh mentioned (retrieval, ranking, blending) — use those exact words.

---

## Day-Of Prep Checklist

- [ ] Know binary cross-entropy formula by heart — write it without looking
- [ ] Practice rate limiter problem: sliding window, O(1) space variant, per-(user, game) extension
- [ ] Practice the match-3 grid problem (most likely MLE-specific coding question)
- [ ] Practice call stack exclusive time (LC-636)
- [ ] Prepare 2-min pitch on your ranking pipeline at Meta (use: retrieval → ranking → blending language)
- [ ] Be ready to sketch two-tower architecture on the fly
- [ ] Review: long-tail handling, categorical features, CTR/CVR modeling, calibration
- [ ] Set up CodeSignal env ahead of time — the link is provided: `https://app.codesignal.com/live-interview/dpFcYwcZ5Cpwhjmk3`
- [ ] Join Zoom first (Meeting ID: 98237070380, Passcode: tQ8@3Jdi8u), then switch to CodeSignal

---

## Sources

- interviewcoder.co: Senior MLE Roblox phone screen (2025 Q3), ~10 SWE Roblox writeups (2025-2026)
- LeetCode discuss: Roblox IC3 passed (2026), Roblox system design (2025), Roblox phone screen (2025), gaming OA list
- Recruiter call transcript with Santosh Alex (Roblox Talent Partner)
