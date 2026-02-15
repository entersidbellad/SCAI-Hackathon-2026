# Human Evaluation Data

This directory holds **human evaluation scores** used as ground truth for validating AI judges.

## How to Add Evaluations

Create JSON files matching the schema in `schema.json`. Each file should contain one evaluation:

```json
{
  "case_name": "1 Ontario v. Quon",
  "model": "grok-4.1-fast",
  "evaluator_name": "your_name",
  "scores": {
    "factual_accuracy": 4,
    "completeness": 4
  },
  "notes": "Minor date error in paragraph 3"
}
```

### File Naming Convention

```
{case_name}_{model}_{evaluator}.json
```

Example: `1 Ontario v. Quon_grok-4.1-fast_sid.json`

### Scoring Rubric (Same as AI Judges)

| Score | Factual Accuracy | Completeness |
|-------|-----------------|--------------|
| **5** | Flawless, all facts correct | Comprehensive, covers all key points |
| **4** | Minor error (trivial date, name spelling) | Missed concurrence or minor detail |
| **3** | Major hallucination or significant error | Missed dissent or substantial section |
| **2** | Holding reversed or critical fact wrong | Missed main holding or critical reasoning |
| **1** | Incoherent or fundamentally wrong | Barely covers anything |

### Minimum Recommended Coverage

- At least **15 evaluations** (5 cases × 3 models)
- Ideally **2-3 human evaluators** for inter-annotator agreement
