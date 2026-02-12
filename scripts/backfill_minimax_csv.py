
import json
import csv
import logging
from pathlib import Path
from datetime import datetime
import sys

# Setup paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
MINIMAX_DIR = OUTPUT_DIR / "judge_results" / "minimax-m2.1"
CSV_PATH = OUTPUT_DIR / "evaluation_log.csv"

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LEGACY_PROMPT = """You are an expert legal evaluator assessing the quality of AI-generated Supreme Court case summaries.

Compare the GENERATED SUMMARY against the REFERENCE SUMMARY (ground truth) and evaluate faithfulness.

## REFERENCE SUMMARY (Ground Truth):
{ground_truth}

## GENERATED SUMMARY (To Evaluate):
{llm_summary}

## EVALUATION CRITERIA:

1. **Factual Accuracy (1-5)**: Does the generated summary accurately represent the facts, parties, legal issues, and holdings? Are there any factual errors or misrepresentations?
   - 5: Perfectly accurate, no errors
   - 4: Minor inaccuracies that don't affect understanding
   - 3: Some errors but core facts correct
   - 2: Significant errors affecting understanding
   - 1: Major factual errors or misrepresentations

2. **Completeness (1-5)**: Does the generated summary cover all key points from the reference?
   - 5: Covers everything important
   - 4: Missing minor details only
   - 3: Missing some notable points
   - 2: Missing significant information
   - 1: Missing critical information

3. **Factual Errors/Inaccuracies**: Identify SPECIFIC factual errors in the generated summary. For each error:
   - Quote the problematic text from the generated summary
   - Explain what is wrong
   - Quote the correct information from the reference

4. **Hedging/Softening Detection**: Did the summary weaken, hedge, or soften any definitive claims from the reference? (e.g., "the Court held" -> "the Court suggested")

5. **Key Omissions**: What specific important information from the reference is missing in the generated summary?

## RESPOND IN THIS EXACT JSON FORMAT:
```json
{
    "factual_accuracy": <1-5>,
    "completeness": <1-5>,
    "factual_errors": [
        {
            "error_quote": "<exact quote from generated summary that is wrong>",
            "issue": "<explanation of what is incorrect>",
            "correct_info": "<what the reference actually says>"
        }
    ],
    "hedging_detected": <true/false>,
    "hedging_examples": [
        {
            "summary_says": "<quote from generated summary>",
            "reference_says": "<quote from reference showing stronger language>",
            "issue": "<explanation of how it was softened>"
        }
    ],
    "key_omissions": ["<specific missing item 1>", "<specific missing item 2>"],
    "overall_assessment": "<brief 2-3 sentence assessment of the summary quality>"
}
```

Return ONLY the JSON, no other text."""

def backfill():
    if not MINIMAX_DIR.exists():
        logger.error(f"Minimax directory not found: {MINIMAX_DIR}")
        return

    # Prepare CSV header if file doesn't exist
    fieldnames = [
        "Timestamp",
        "Run_ID",
        "Case",
        "Summarizer_Model",
        "Judge_Model",
        "Composite_Score",
        "NLI_Score",
        "Judge_Score",
        "Coverage_Score",
        "Factual_Accuracy",
        "Completeness",
        "Summarizer_Prompt",
        "Judge_Prompt",
    ]
    
    file_exists = CSV_PATH.exists()
    
    entries_to_add = []
    
    logger.info(f"Scanning {MINIMAX_DIR} for results...")
    
    for json_file in MINIMAX_DIR.glob("*.json"):
        if json_file.name.startswith("_"): continue # Skip summaries
        
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            
            # Parse filename to get case and model
            # Format: "{case_name}_{model_short}_judge.json"
            # But case name can contain underscores? No, spaces usually.
            # But the suffix is fixed: "_judge.json"
            stem = json_file.stem.replace("_judge", "")
            # Split from right to isolate model
            parts = stem.rsplit("_", 1)
            if len(parts) != 2:
                logger.warning(f"Skipping malformed filename: {json_file.name}")
                continue
                
            case_name = parts[0]
            model_short_map = parts[1]
            
            # Map short model name back to full ID if possible, or just use short
            summarizer_model = model_short_map # Default
            if model_short_map == "gemini-2.5-flash-lite": summarizer_model = "google/gemini-2.5-flash-lite"
            elif model_short_map == "grok-4.1-fast": summarizer_model = "x-ai/grok-4.1-fast"
            elif model_short_map == "llama-4-maverick": summarizer_model = "meta-llama/llama-4-maverick"
            
            judge_model = "minimax/minimax-m2.1"
            
            # Extract scores
            judge_score = data.get("judge_score", 0)
            factual_acc = data.get("factual_accuracy", "")
            completeness = data.get("completeness", "")
            
            # We don't have composite/NLI/Coverage here directly unless we look up results.json
            # But for the log, we might just leave them 0 or empty if not easily available.
            # The user mostly cares about the JUDGE comparison.
            
            # Use file modification time as timestamp
            mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
            timestamp = mtime.isoformat()
            run_id = f"backfill_{timestamp}_{case_name}"
            
            entry = {
                "Timestamp": timestamp,
                "Run_ID": run_id,
                "Case": case_name,
                "Summarizer_Model": summarizer_model,
                "Judge_Model": judge_model,
                "Composite_Score": "0.0000", # Placeholder
                "NLI_Score": "0.0000", # Placeholder
                "Judge_Score": f"{judge_score:.4f}",
                "Coverage_Score": "0.0000", # Placeholder
                "Factual_Accuracy": factual_acc,
                "Completeness": completeness,
                "Summarizer_Prompt": "SEE_SRC_SUMMARIZER_PY",
                "Judge_Prompt": LEGACY_PROMPT,
            }
            entries_to_add.append(entry)
            
        except Exception as e:
            logger.error(f"Failed to process {json_file}: {e}")

    if not entries_to_add:
        logger.info("No minimax entries found to add.")
        return

    logger.info(f"Adding {len(entries_to_add)} legacy entries to CSV...")
    
    with open(CSV_PATH, mode="a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(entries_to_add)
        
    logger.info("Backfill complete.")

if __name__ == "__main__":
    backfill()
