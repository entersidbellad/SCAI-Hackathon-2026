# Meta-Evaluation Report: Judge Calibration & Pillar Analysis

*Generated: 2026-02-11 23:02:51*

This report evaluates the reliability of the evaluation pipeline itself.
It answers: **"How do we know our judges are performing well?"**

---

## 1. Kendall's Tau (τ) — Rank Correlation Between Judges

Measures whether judges **rank models in the same order**, even if they disagree on absolute scores.

| Judge Pair | Overall τ | p-value | Interpretation | N |
|---|---|---|---|---|
| claude-opus-4.5 ↔ gemini-3-flash-preview | 0.6547 | 0.0000 | Moderate agreement | 57 |
| claude-opus-4.5 ↔ minimax-m2.1 | 0.2768 | 0.0098 | Weak agreement | 57 |
| gemini-3-flash-preview ↔ minimax-m2.1 | 0.2050 | 0.0538 | Weak agreement | 57 |

---

## 2. Score Distribution Analysis

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

## 3. Cohen's Kappa — Inter-Judge Agreement

Measures agreement on the 1-5 ordinal scale, adjusted for chance. Uses **quadratic weights** (appropriate for ordinal data).

| Judge Pair | Accuracy κ | Interpretation | Completeness κ | Interpretation | N |
|---|---|---|---|---|---|
| claude-opus-4.5 ↔ gemini-3-flash-preview | 0.4248 | Moderate agreement | 0.8604 | Near-perfect agreement | 57 |
| claude-opus-4.5 ↔ minimax-m2.1 | 0.5550 | Moderate agreement | 0.3710 | Fair agreement | 57 |
| gemini-3-flash-preview ↔ minimax-m2.1 | 0.3605 | Fair agreement | 0.3040 | Fair agreement | 57 |

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

*Interpretation guide:*

- **Kendall's τ**: >0.7 = strong agreement, 0.4-0.7 = moderate, <0.4 = weak
- **Cohen's κ**: >0.8 = near-perfect, 0.6-0.8 = substantial, 0.4-0.6 = moderate, <0.4 = poor
- **Spearman ρ**: >0.7 = high redundancy between pillars, <0.3 = pillars measure distinct things
