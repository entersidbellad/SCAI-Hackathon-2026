# ∑VAL in Plain English

## 1) What you built (in one minute)
You built a system that checks whether AI summaries of Supreme Court cases are actually trustworthy.

Instead of asking only "does this sound good?", your benchmark asks:
- Did the summary **say anything false**?
- Did it **miss important parts**?
- Did it **read like a legally accurate explanation**?

Then it combines those checks into one final score.

## 2) How scoring works (simple)
You use 3 checks:
- **Truth check (NLI, 35%)**: catches contradictions.
- **Judge check (40%)**: expert-style grading for factual accuracy + completeness.
- **Coverage check (25%)**: checks if key source points were included.

Final score:
- `0.35 × NLI + 0.40 × Judge + 0.25 × Coverage`

Why this matters: one metric alone can miss real mistakes.

## 3) Main results from your benchmark runs
Source snapshot: `outputs/results.json` (generated **2026-02-10**)

- **Models tested**: 3
- **Cases in dataset**: 20 total
- **Cases with scored outputs**: 19
- **Missing scored case**: `18 Ohio v. American Express`

### Overall ranking (higher is better)
1. **grok-4.1-fast**: **0.836**
2. gemini-2.5-flash-lite: 0.773
3. llama-4-maverick: 0.740

### Practical interpretation
- Grok won overall because it did very well on judge quality and coverage.
- Llama did best on contradiction resistance (NLI) but lost points on other dimensions.
- This shows why one metric is not enough.

## 4) "Why not ROUGE?" (short answer)
You ran this test directly.

Source: `outputs/baseline_evaluation_report.md` (2026-02-11)

What you found:
- ROUGE/BERTScore often disagree with your faithfulness score.
- Ranking correlation was weak or negative (meaning baselines missed what your benchmark catches).
- Example pattern: some summaries had low ROUGE but high faithfulness (wording changed but facts still right).

So your method is stronger for **truthfulness**, not just text overlap.

## 5) Are the judges reliable?
Source: `outputs/meta_evaluation_report.md` (2026-02-14)

Simple take:
- **Claude vs Gemini** had solid agreement, especially on completeness.
- Their model ranking agreement was moderate-to-strong overall.
- Minimax was less aligned with the other two.

Plain-English read:
- Your judging setup is not random.
- It is reasonably stable, especially with Claude + Gemini.

## 6) Bias + consistency checks (trust checks)
Source: `outputs/bias_audit_report.md` (2026-02-12)

What you proved:
- No strong evidence judges simply reward longer summaries.
- Claude and Gemini gave highly consistent repeat scores (excellent test-retest).
- Minimax had acceptable but weaker repeat consistency.

Meaning:
- Your scoring is not just "longer summary = better score".

## 7) What errors models make most (from your taxonomy)
Source: `outputs/error_taxonomy_report.md` (2026-02-12)

Across your tagged failures:
- **260 factual errors**
- **517 omissions**
- **777 combined failures**

Most common factual issue:
- **Fabricated precedent/citation** (made-up legal details)

Most common omission issue:
- **Missing concurrences/dissents and other legal context**

Hardest cases included:
- Van Buren v. United States
- American Legion v. American Humanist Assn
- Knick v. Township of Scott
- Torres v. Madrid

## 8) What this means for non-technical people
- Do not trust AI summaries just because they sound polished.
- Use model rankings as a **risk signal**, not absolute truth.
- For legal use, pick models with balanced performance across all 3 checks.
- Always keep a human review layer for high-stakes decisions.

## 9) One-line glossary (no jargon)
- **Kappa (κ)**: "How much judges truly agree, beyond luck."
- **Tau (τ)**: "How similarly judges rank models from best to worst."
- **Correlation**: "Whether two scores move together."
- **Confidence interval**: "Likely range of the true value."

## 10) Honest limitations (important)
- One case currently has missing scored outputs (`Ohio v. American Express`).
- Results are from this dataset and setup; not a universal guarantee.
- Final scores are decision support, not legal advice.

---

If you need a 30-second pitch:

> "I built a legal-summary trust benchmark. It checks if AI summaries are factually correct, complete, and high quality using three independent signals. In our runs, Grok ranked highest overall, and we validated judge reliability, bias, and baseline limitations so the scores are meaningful for real-world model selection." 
