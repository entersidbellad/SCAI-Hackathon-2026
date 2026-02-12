# Bias Auditing Report: Length Bias & Self-Consistency

*Generated: 2026-02-12 00:56:43*

This report checks whether our judges have systematic biases
that could undermine the evaluation's reliability.

---

## 1. Length Bias Analysis

Tests whether judges give higher scores to longer summaries (or vice versa).

| Judge | Pearson r | p-value | Spearman ρ | Bias? | Interpretation |
|---|---|---|---|---|---|
| claude-opus-4.5 | -0.2736 | 0.0395 | 0.1164 | ✅ No | Slight tendency toward shorter summaries (r=-0.274), not significant |
| gemini-3-flash-preview | -0.1763 | 0.1896 | 0.3253 | ✅ No | Slight tendency toward shorter summaries (r=-0.176), not significant |
| minimax-m2.1 | -0.2486 | 0.0622 | 0.0002 | ✅ No | Slight tendency toward shorter summaries (r=-0.249), not significant |

### Length Correlation by Dimension

| Judge | Length ↔ Factual Accuracy r | Length ↔ Completeness r |
|---|---|---|
| claude-opus-4.5 | -0.5162 | -0.0786 |
| gemini-3-flash-preview | -0.1338 | -0.1704 |
| minimax-m2.1 | -0.2314 | -0.2482 |

> **Note**: A positive correlation with completeness is expected and benign —
> longer summaries naturally cover more content. A positive correlation with
> *factual accuracy* would be concerning (length shouldn't affect truthfulness).

### Summary Length Statistics

| Judge | Mean Words | Min | Max | Std |
|---|---|---|---|---|
| claude-opus-4.5 | 645.6 | 268 | 1759 | 257.5 |
| gemini-3-flash-preview | 645.6 | 268 | 1759 | 257.5 |
| minimax-m2.1 | 645.6 | 268 | 1759 | 257.5 |

---

## 2. Self-Consistency (Test-Retest Reliability)

Re-sent the same summaries to each judge and compared scores.

| Judge | N Retests | Mean Δ Score | Max Δ | Exact Match % | Close Match % (≤0.1) | Interpretation |
|---|---|---|---|---|---|---|
| claude-opus-4.5 | 5 | 0.0000 | 0.0000 | 100% | 100% | Highly consistent (excellent test-retest reliability) |
| gemini-3-flash-preview | 5 | 0.0000 | 0.0000 | 100% | 100% | Highly consistent (excellent test-retest reliability) |
| minimax-m2.1 | 5 | 0.0600 | 0.2000 | 60% | 80% | Good consistency (acceptable variation) |

### claude-opus-4.5 — Detailed Results

| Case | Model | Original | Retest | Δ Score | Δ FA | Δ Comp |
|---|---|---|---|---|---|---|
| 16 Knick v. Township of Scott | llama-4-maverick | 0.20 | 0.20 | 0.00 | 0 | 0 |
| 7 Torres v. Madrid | gemini-2.5-flash-lite | 0.60 | 0.60 | 0.00 | 0 | 0 |
| 5 Citizens United v. Federal E | llama-4-maverick | 0.70 | 0.70 | 0.00 | 0 | 0 |
| 10 California v. Texas | grok-4.1-fast | 0.90 | 0.90 | 0.00 | 0 | 0 |
| 8 Fulton v. City of Philadelph | grok-4.1-fast | 0.90 | 0.90 | 0.00 | 0 | 0 |

### gemini-3-flash-preview — Detailed Results

| Case | Model | Original | Retest | Δ Score | Δ FA | Δ Comp |
|---|---|---|---|---|---|---|
| 16 Knick v. Township of Scott | llama-4-maverick | 0.20 | 0.20 | 0.00 | 0 | 0 |
| 7 Torres v. Madrid | gemini-2.5-flash-lite | 0.60 | 0.60 | 0.00 | 0 | 0 |
| 5 Citizens United v. Federal E | llama-4-maverick | 0.70 | 0.70 | 0.00 | 0 | 0 |
| 10 California v. Texas | grok-4.1-fast | 1.00 | 1.00 | 0.00 | 0 | 0 |
| 8 Fulton v. City of Philadelph | grok-4.1-fast | 1.00 | 1.00 | 0.00 | 0 | 0 |

### minimax-m2.1 — Detailed Results

| Case | Model | Original | Retest | Δ Score | Δ FA | Δ Comp |
|---|---|---|---|---|---|---|
| 16 Knick v. Township of Scott | llama-4-maverick | 0.20 | 0.20 | 0.00 | 0 | 0 |
| 7 Torres v. Madrid | gemini-2.5-flash-lite | 0.40 | 0.60 | 0.20 | 1 | 1 |
| 5 Citizens United v. Federal E | llama-4-maverick | 0.50 | 0.60 | 0.10 | 0 | 1 |
| 10 California v. Texas | grok-4.1-fast | 0.60 | 0.60 | 0.00 | 0 | 0 |
| 8 Fulton v. City of Philadelph | grok-4.1-fast | 0.60 | 0.60 | 0.00 | 1 | 1 |

---

## Key Takeaways

- **Length bias < 0.3**: Judge scores are NOT primarily driven by summary length ✅
- **Completeness ↔ length** correlation is expected — longer summaries cover more
- **Factual accuracy ↔ length** correlation should be near zero (truth ≠ length)
- **Self-consistency**: Mean Δ ≤ 0.1 indicates reliable judges
