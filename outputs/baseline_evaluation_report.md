# Baseline Metrics Report: ROUGE & BERTScore vs Multi-Pillar

*Generated: 2026-02-11 23:22:31*

This report compares traditional summarization metrics (ROUGE, BERTScore)
against our multi-pillar composite score to show what the composite captures
that baselines miss.

---

## 1. Model Averages Across All Cases

| Model | ROUGE-1 F | ROUGE-2 F | ROUGE-L F | BERTScore F1 | Composite |
|---|---|---|---|---|---|
| gemini-2.5-flash-lite | 0.5752 | 0.2504 | 0.2738 | 0.8667 | 0.7735 |
| grok-4.1-fast | 0.4943 | 0.1785 | 0.2150 | 0.8394 | 0.8356 |
| llama-4-maverick | 0.5072 | 0.2212 | 0.2555 | 0.8521 | 0.7395 |

---

## 2. Ranking Correlation: Baselines vs Composite Score

Higher τ/ρ = baseline agrees more with our composite. Low values = our composite captures something different.

| Metric | Kendall's τ | p-value | Spearman ρ | p-value | N |
|---|---|---|---|---|---|
| ROUGE-1 F | -0.0777 | 0.3933 | -0.0996 | 0.4611 | 57 |
| ROUGE-2 F | -0.0884 | 0.3317 | -0.1156 | 0.3919 | 57 |
| ROUGE-L F | -0.1731 | 0.0574 | -0.2282 | 0.0878 | 57 |
| BERTScore F1 | -0.2026 | 0.0262 | -0.2738 | 0.0393 | 57 |

> **How to read this**: If τ is high (>0.7), baselines and our composite largely agree —
> meaning our pipeline may not add much value. If τ is low (<0.4), our composite captures
> quality dimensions that ROUGE/BERTScore miss entirely.

---

## 3. Top Disagreements (Where Baselines and Composite Differ Most)

These are your most compelling examples for demonstrating the value of multi-pillar evaluation.

| Case | Model | ROUGE-L F | BERTScore F1 | Composite | Gap | Direction |
|---|---|---|---|---|---|---|
| 11 NCAA v. Alston | grok-4.1-fast | 0.1915 | 0.8404 | 0.9067 | 0.7152 | composite_higher |
| 17 Gill v. Whitford | grok-4.1-fast | 0.1756 | 0.8257 | 0.8839 | 0.7083 | composite_higher |
| 11 NCAA v. Alston | llama-4-maverick | 0.2468 | 0.8561 | 0.9433 | 0.6965 | composite_higher |
| 13 Espinoza v. Montana Dept of Revenue | grok-4.1-fast | 0.2090 | 0.8499 | 0.8913 | 0.6823 | composite_higher |
| 11 NCAA v. Alston | gemini-2.5-flash-lite | 0.2099 | 0.8625 | 0.8900 | 0.6801 | composite_higher |
| 10 California v. Texas | grok-4.1-fast | 0.2028 | 0.8211 | 0.8750 | 0.6722 | composite_higher |
| 20 Epic Systems v. Lewis | grok-4.1-fast | 0.1949 | 0.8334 | 0.8618 | 0.6669 | composite_higher |
| 12 Financial Oversight Board v. Aurelius | grok-4.1-fast | 0.2337 | 0.8196 | 0.8917 | 0.6580 | composite_higher |
| 2 Allen v. Michigan | grok-4.1-fast | 0.1761 | 0.8326 | 0.8200 | 0.6439 | composite_higher |
| 3 Brown v. Board of Education of Topeka | grok-4.1-fast | 0.1727 | 0.8103 | 0.8125 | 0.6398 | composite_higher |

> **baseline_higher** = ROUGE/BERTScore thinks the summary is good, but our composite penalizes it
> (likely due to factual errors or hallucinations that n-gram overlap can't catch).

> **composite_higher** = Our composite rates the summary well, but ROUGE is low
> (likely because the summary uses different words but is semantically faithful).

---

## Key Takeaways

- ROUGE measures **lexical overlap** — sensitive to word choice, insensitive to factual errors
- BERTScore measures **semantic similarity** — better than ROUGE but still misses contradictions
- Our **composite** catches contradictions (NLI), semantic gaps (coverage), AND qualitative issues (judge)
- Cases where baselines disagree with our composite are evidence for the multi-pillar approach
