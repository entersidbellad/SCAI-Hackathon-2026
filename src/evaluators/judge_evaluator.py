"""
Pillar 2: LLM-as-a-Judge Evaluation
Uses an LLM to evaluate summaries against ground truth with a structured rubric.

Enhanced Features:
- Organizes results by judge model in separate folders
- Processes cases in numerical order (1, 2, 3...)
- Skips already-completed evaluations
- Documents prompts in output for full traceability
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from ..openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)

JUDGE_PROMPT = """You are a highly critical, pedantic legal scholar auditor. Your job is to find ANY and ALL errors in AI-generated Supreme Court case summaries.

Compare the GENERATED SUMMARY against the REFERENCE SUMMARY (ground truth).

## REFERENCE SUMMARY (Ground Truth):
{ground_truth}

## GENERATED SUMMARY (To Evaluate):
{llm_summary}

## AUDIT INSTRUCTIONS:

1. **Step 1: Accuracy Check (Hallucinations)**:
   - Does the summary contain facts not in the reference?
   - **Severity Assessment**:
     - *Trivial* (Detailed date wrong, minor phrasing): **Minor Issue (-1)**
     - *Substantial* (Invented detail, wrong party name): **Major Issue (-2)**
     - *Critical* (Changes the legal outcome/holding): **Critical Issue (-3)**

2. **Step 2: Legal Precision Check (Holding/Reasoning)**:
   - Did it miss the main holding? **Critical Issue (-3)**
   - Did it miss a key reasoning step? **Major Issue (-2)**

3. **Step 3: Completeness Check (Opinions)**:
   - Missed the **Dissent**? **Major Omission (-2)**
   - Missed a **Concurrence**? **Minor Omission (-1)**

## SCORING RUBRIC (1-5 Integer Scale):
Score based on the *worst* error found. Do not sum penalties below 1.

- **5 (Perfect)**: Flawless. No hallucinations, covers holding, reasoning, concurrences, and dissents.
- **4 (Minor Flaw)**: Generally accurate but missed a **Concurrence** OR has a **Trivial** factual error (e.g., typos, minor date slip).
- **3 (Major Flaw)**: Missed the **Dissent** OR has a **Substantial** hallucination (clearly wrong but doesn't change outcome).
- **2 (Critical Failure)**: Missed the **Main Holding** OR has a **Critical** hallucination (reversed law/facts).
- **1 (Catastrophic)**: Completely wrong case, incoherent, or dangerously misleading.

## RESPOND IN THIS EXACT JSON FORMAT:
```json
{{
    "factual_accuracy": <1-5 integer>,
    "completeness": <1-5 integer>,
    "factual_errors": [
        {{
            "error_quote": "<exact quote>",
            "issue": "<why is this wrong?>",
            "severity": "<Minor/Major/Critical>",
            "correct_info": "<what reference says>"
        }}
    ],
    "hedging_detected": <true/false>,
    "hedging_examples": [],
    "key_omissions": ["<missing item 1>", "<missing item 2>"],
    "overall_assessment": "<Brief explanation of the score based on the rubric buckets>"
}}
```

Return ONLY the JSON."""


def get_judge_prompt():
    """Return the judge prompt template for documentation purposes."""
    return JUDGE_PROMPT


def parse_judge_response(response: str) -> dict:
    """
    Parse the judge model's JSON response.
    
    Args:
        response: Raw response from the judge model
        
    Returns:
        Parsed dictionary
    """
    # Try to extract JSON from the response
    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # If parsing fails, return default structure with error
    logger.warning("Failed to parse judge response, using defaults")
    return {
        "factual_accuracy": 3,
        "completeness": 3,
        "factual_errors": [],
        "hedging_detected": False,
        "hedging_examples": [],
        "key_omissions": [],
        "overall_assessment": "Parse error - could not extract structured evaluation",
        "parse_error": True,
        "raw_response": response[:500] if response else "",
    }


def get_case_sort_key(case_name: str) -> tuple:
    """
    Extract numeric prefix for proper case ordering.
    Returns tuple (number, name) for sorting cases like '1 Ontario v. Quon' before '10 California v. Texas'.
    """
    match = re.match(r'^(\d+)\s+(.+)$', case_name)
    if match:
        return (int(match.group(1)), match.group(2))
    return (999999, case_name)  # Non-numeric cases go last


class JudgeEvaluator:
    """Evaluates summaries using an LLM as a judge."""
    
    def __init__(self, client: OpenRouterClient, judge_model: str):
        """
        Initialize the judge evaluator.
        
        Args:
            client: OpenRouter client instance
            judge_model: Model identifier for the judge
        """
        self.client = client
        self.judge_model = judge_model
        self.judge_model_short = judge_model.split("/")[-1].split(":")[0]
        logger.info(f"Judge evaluator using model: {judge_model}")
    
    def evaluate_summary(
        self,
        ground_truth: str,
        llm_summary: str,
        case_name: str = "",
        summarizer_model: str = "",
    ) -> dict:
        """
        Evaluate an LLM summary against ground truth using LLM-as-judge.
        
        Args:
            ground_truth: The reference summary (Oyez)
            llm_summary: The LLM-generated summary
            case_name: Name of the case being evaluated
            summarizer_model: Model that generated the summary
            
        Returns:
            Dict with structured evaluation scores and metadata
        """
        prompt = JUDGE_PROMPT.format(
            ground_truth=ground_truth,
            llm_summary=llm_summary,
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        response = self.client.chat_completion(
            model=self.judge_model,
            messages=messages,
            temperature=0.0,  # Temperature 0 for deterministic evaluation
        )
        
        result = parse_judge_response(response)
        
        # Calculate normalized judge score (0-1)
        result["judge_score"] = (
            result["factual_accuracy"] + result["completeness"]
        ) / 10
        
        # Add comprehensive metadata for documentation
        result["_metadata"] = {
            "judge_model": self.judge_model,
            "summarizer_model": summarizer_model,
            "case_name": case_name,
            "timestamp": datetime.now().isoformat(),
            "prompt_template": "JUDGE_PROMPT (see docs/prompts.md)",
        }
        
        # Include the full prompt used (for complete documentation)
        result["_prompt_used"] = prompt
        
        return result


def evaluate_all_judge(
    evaluator: JudgeEvaluator,
    ground_truths: dict[str, str],
    llm_summaries: dict[str, dict[str, Path]],
    output_dir: Path,
) -> dict:
    """
    Run judge evaluation on all cases and models.
    
    Features:
    - Organizes results by judge model in subfolders
    - Processes cases in numerical order (1, 2, 3...)
    - Skips already-completed evaluations
    - Includes prompt documentation in output
    
    Args:
        evaluator: JudgeEvaluator instance
        ground_truths: Dict mapping case names to ground truth text
        llm_summaries: Nested dict {case: {model: summary_path}}
        output_dir: Base directory for results
        
    Returns:
        Results dictionary
    """
    # Create subfolder for this judge model
    judge_model_short = evaluator.judge_model_short
    model_output_dir = output_dir / judge_model_short
    model_output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Judge results will be saved to: {model_output_dir}")
    
    all_results = {}
    
    # Sort cases by numeric prefix for ordered processing
    sorted_cases = sorted(ground_truths.keys(), key=get_case_sort_key)
    
    for case_name in sorted_cases:
        gt_text = ground_truths[case_name]
        logger.info(f"Judge evaluation for case: {case_name}")
        all_results[case_name] = {}
        
        case_summaries = llm_summaries.get(case_name, {})
        
        # Sort summarizer models for consistent ordering
        for summarizer_model in sorted(case_summaries.keys()):
            summary_path = case_summaries[summarizer_model]
            if summary_path is None:
                continue
            
            summarizer_short = summarizer_model.split("/")[-1].split(":")[0]
            result_filename = f"{case_name}_{summarizer_short}_judge.json"
            result_path = model_output_dir / result_filename
            
            # Skip if already exists
            if result_path.exists():
                logger.info(f"  {summarizer_short}: SKIPPED (already exists)")
                # Load existing result
                try:
                    existing = json.loads(result_path.read_text(encoding="utf-8"))
                    all_results[case_name][summarizer_model] = existing
                except Exception as e:
                    logger.warning(f"  Failed to load existing result: {e}")
                continue
            
            summary_text = Path(summary_path).read_text(encoding="utf-8")
            
            result = evaluator.evaluate_summary(
                gt_text, 
                summary_text,
                case_name=case_name,
                summarizer_model=summarizer_model,
            )
            all_results[case_name][summarizer_model] = result
            
            # Save individual result
            result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            
            logger.info(
                f"  {summarizer_short}: accuracy={result['factual_accuracy']}/5, "
                f"completeness={result['completeness']}/5, "
                f"judge_score={result['judge_score']:.2f}"
            )
    
    # Save a summary of the evaluation run
    run_summary = {
        "judge_model": evaluator.judge_model,
        "timestamp": datetime.now().isoformat(),
        "cases_evaluated": len(all_results),
        "prompt_template": JUDGE_PROMPT,
    }
    summary_path = model_output_dir / "_run_summary.json"
    summary_path.write_text(json.dumps(run_summary, indent=2), encoding="utf-8")
    
    return all_results
