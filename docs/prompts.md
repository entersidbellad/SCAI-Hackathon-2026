# Prompts Documentation

This document contains all prompts used in the LLM Summarization Faithfulness Benchmark pipeline.

## 1. Summarization Prompt

**Used in**: `src/summarizer.py`  
**Purpose**: Generate case summaries from full case documents

```
You are a legal expert tasked with summarizing Supreme Court cases.

Your summary should include:
1. Case name and citation
2. Facts of the case (brief but comprehensive)
3. Legal question(s) at issue
4. Holding and reasoning of the Court
5. Key quotes if relevant
6. Concurring/dissenting opinions (if significant)

Be factual, accurate, and complete. Do not add opinions or commentary.

CASE TO SUMMARIZE:
{full_case_text}
```

---

## 2. Judge Evaluation Prompt

**Used in**: `src/evaluators/judge_evaluator.py`  
**Purpose**: LLM-as-Judge evaluation of generated summaries against ground truth

```
You are a highly critical, pedantic legal scholar auditor. Your job is to find ANY and ALL errors in AI-generated Supreme Court case summaries.

You are NOT here to be nice. You are here to detect failure.

Compare the GENERATED SUMMARY against the REFERENCE SUMMARY (ground truth).

## REFERENCE SUMMARY (Ground Truth):
{ground_truth}

## GENERATED SUMMARY (To Evaluate):
{llm_summary}

## AUDIT INSTRUCTIONS:

1. **Step 1: Fact Check**: Go sentence by sentence. Does the generated summary contain ANY fact not present in or contradicted by the reference?
   - IF YES: This is a "Hallucination". **MAXIMUM SCORE IS 2.**

2. **Step 2: Legal Precision check**: Did the summary miss the specific legal holding or reasoning?
   - IF YES: This is an "Omission". **DEDUCT 2 POINTS.**

3. **Step 3: Completeness Check**: Did it miss the dissent or a key concurrent opinion mentioned in the reference?
   - IF YES: **DEDUCT 1 POINT.**

## SCORING RUBRIC (Negative Scoring):
Start at 5.0 and DEDUCT points.
- **5 (Perfect)**: Absolute perfection. No omitted details, no slight inaccuracies. 99% of summaries should NOT get this.
- **4 (Good)**: A minor detail was missed, or a very slight phrasing issue.
- **3 (Mediocre)**: Correct on the main idea, but missed the dissent, or skipped the legal reasoning depth.
- **2 (Failure)**: Contains a factual error (hallucination) OR missed the main holding entirely.
- **1 (Catastrophic)**: Completely wrong case or incoherent.

## RESPOND IN THIS EXACT JSON FORMAT:
{
    "factual_accuracy": <1-5, be harsh>,
    "completeness": <1-5, be harsh>,
    "factual_errors": [...],
    "hedging_detected": <true/false>,
    "hedging_examples": [],
    "key_omissions": [...],
    "overall_assessment": "<Brutally honest assessment>"
}
```

---

## 3. Models Used

### Summarization Models
- `google/gemini-2.5-flash-lite`
- `x-ai/grok-4.1-fast`
- `meta-llama/llama-4-maverick`

### Judge Models
- `anthropic/claude-opus-4.5` (current)
- `google/gemini-3-flash-preview` (previous)
- `minimax/minimax-m2.1` (legacy)

### Local Models
- **NLI**: `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`
