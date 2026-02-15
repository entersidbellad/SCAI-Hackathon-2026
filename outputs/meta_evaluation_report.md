# Meta-Evaluation Report: Judge Calibration & Pillar Analysis

*Generated: 2026-02-14 11:36:14*

This report evaluates the reliability of the evaluation pipeline itself.
It answers: **"How do we know our judges are performing well?"**

> **Statistical Methodology**: This report uses **Cohen's Kappa** as the primary
> metric for AI↔AI agreement (appropriate when neither rater is ground truth).
> For AI↔Human validation, see the **Human Evaluation Report** which
> uses **Kendall's Tau** (appropriate when one rater is ground truth).

---

## 1. Cohen's Kappa — Inter-Judge Agreement (Primary AI↔AI Metric)

Measures agreement on the 1-5 ordinal scale, adjusted for chance agreement.
Uses **quadratic weights** (appropriate for ordinal data).

> **Why Cohen's Kappa for AI↔AI?** When comparing two AI judges, neither is
> ground truth. Cohen's Kappa measures whether the raters agree beyond what
> chance alone would predict, making it ideal for this comparison.

| Judge Pair | Accuracy κ | 95% CI | Completeness κ | 95% CI | Interpretation | N |
|---|---|---|---|---|---|---|
| claude-opus-4.5 ↔ gemini-3-flash-preview | 0.4248 | [0.072, 0.645] | 0.8604 | [0.745, 0.927] | Moderate agreement / Near-perfect agreement | 57 |
| claude-opus-4.5 ↔ minimax-m2.1 | 0.5550 | [0.263, 0.721] | 0.3710 | [0.058, 0.602] | Moderate agreement / Fair agreement | 57 |
| gemini-3-flash-preview ↔ minimax-m2.1 | 0.3605 | [0.029, 0.585] | 0.3040 | [-0.022, 0.561] | Fair agreement / Fair agreement | 57 |

---

## 2. Kendall's Tau (τ) — Supplementary Rank Correlation

Measures whether judges **rank models in the same order**, even if they disagree on absolute scores.

> **Note**: For AI↔AI comparison, Cohen's Kappa (Section 1) is the primary metric.
> Kendall's Tau is shown here for supplementary context. For AI↔Human rank correlation
> (treating human as ground truth), see the Human Evaluation Report.

| Judge Pair | Overall τ | 95% CI | p-value | Interpretation | N |
|---|---|---|---|---|---|
| claude-opus-4.5 ↔ gemini-3-flash-preview | 0.6547 | [0.506, 0.779] | 0.0000 | Moderate agreement | 57 |
| claude-opus-4.5 ↔ minimax-m2.1 | 0.2768 | [0.055, 0.475] | 0.0098 | Weak agreement | 57 |
| gemini-3-flash-preview ↔ minimax-m2.1 | 0.2050 | [-0.037, 0.433] | 0.0538 | Weak agreement | 57 |

---

## 3. Score Distribution Analysis

Shows whether judges use the full 1-5 scoring range or cluster around certain values.

### claude-opus-4.5

- **N evaluations**: 57
- **Factual Accuracy**: mean=3.579, std=0.674, range=[1-4]
  - Distribution: 1→2, 2→0, 3→18, 4→37, 5→0
- **Completeness**: mean=3.649, std=1.068, range=[1-5]
  - Distribution: 1→2, 2→3, 3→25, 4→10, 5→17
- **Normalized Judge Score**: mean=0.7228, std=0.1579, range=[0.2-0.9]

### gemini-3-flash-preview

- **N evaluations**: 57
- **Factual Accuracy**: mean=4.246, std=0.996, range=[1-5]
  - Distribution: 1→2, 2→0, 3→11, 4→13, 5→31
- **Completeness**: mean=3.825, std=1.045, range=[1-5]
  - Distribution: 1→2, 2→1, 3→22, 4→12, 5→20
- **Normalized Judge Score**: mean=0.807, std=0.1766, range=[0.2-1.0]

### minimax-m2.1

- **N evaluations**: 57
- **Factual Accuracy**: mean=3.596, std=1.041, range=[1-5]
  - Distribution: 1→2, 2→6, 3→17, 4→20, 5→12
- **Completeness**: mean=3.456, std=0.956, range=[1-5]
  - Distribution: 1→2, 2→3, 3→29, 4→13, 5→10
- **Normalized Judge Score**: mean=0.7053, std=0.1923, range=[0.2-1.0]

---

## 4. Pillar Correlation Matrix (Spearman ρ)

Answers: **"Are the three pillars measuring different things or are they redundant?"**

Low correlation = pillars capture distinct aspects of quality. High correlation = potential redundancy.

### claude-opus-4.5 (N=57)

| Pillar Pair | Spearman ρ | p-value | Interpretation |
|---|---|---|---|
| Judge (claude-opus-4.5) ↔ NLI | -0.4586 | 0.0003 | Moderate negative correlation |
| Judge (claude-opus-4.5) ↔ Coverage | 0.4735 | 0.0002 | Moderate positive correlation |
| NLI ↔ Coverage | -0.4745 | 0.0002 | Moderate negative correlation |

### gemini-3-flash-preview (N=57)

| Pillar Pair | Spearman ρ | p-value | Interpretation |
|---|---|---|---|
| Judge (gemini-3-flash-preview) ↔ NLI | -0.2586 | 0.0521 | Weak negative correlation |
| Judge (gemini-3-flash-preview) ↔ Coverage | 0.4388 | 0.0006 | Moderate positive correlation |
| NLI ↔ Coverage | -0.4745 | 0.0002 | Moderate negative correlation |

### minimax-m2.1 (N=57)

| Pillar Pair | Spearman ρ | p-value | Interpretation |
|---|---|---|---|
| Judge (minimax-m2.1) ↔ NLI | -0.3309 | 0.0119 | Weak negative correlation |
| Judge (minimax-m2.1) ↔ Coverage | 0.2643 | 0.0469 | Weak positive correlation |
| NLI ↔ Coverage | -0.4745 | 0.0002 | Moderate negative correlation |

---

## Key Takeaways

### Statistical Methodology

| Comparison Type | Primary Metric | Rationale |
|---|---|---|
| **AI ↔ AI** (this report) | Cohen's Kappa | Neither judge is ground truth |
| **AI ↔ Human** (human eval report) | Kendall's Tau | Human is treated as ground truth |

### Interpretation Guide

- **Cohen's κ**: >0.8 = near-perfect, 0.6-0.8 = substantial, 0.4-0.6 = moderate, <0.4 = poor
- **Kendall's τ**: >0.7 = strong, 0.4-0.7 = moderate, <0.4 = weak
- **Spearman ρ**: >0.7 = high redundancy between pillars, <0.3 = pillars measure distinct things
- **95% CI**: Bootstrap confidence intervals (1000 iterations) — narrower = more reliable estimate
