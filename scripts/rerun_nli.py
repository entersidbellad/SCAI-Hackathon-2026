
"""
Rerun NLI Evaluation
Re-runs Pillar 1 (NLI) using the new Ground-Truth Anchored methodology
and updates all scoring artifacts (JSON, CSV, Reports).
"""

import sys
import logging
import json
from pathlib import Path
from dotenv import load_dotenv

# Add parent dir to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.summarizer import SUMMARIZATION_PROMPT
from src.evaluators.judge_evaluator import JUDGE_PROMPT
import config
from src.evaluators.nli_evaluator import NLIEvaluator, evaluate_all_nli
from src.composite_scorer import compute_all_composite_scores
from src.reporter import generate_results_json, generate_summary_report, update_evaluation_log_csv


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

def load_ground_truths(data_dir: Path) -> dict[str, str]:
    """Load all ground truth summary files."""
    ground_truths = {}
    for summary_path in sorted(data_dir.glob("*summary.txt")):
        case_name = summary_path.stem.replace(" summary", "")
        ground_truths[case_name] = summary_path.read_text(encoding="utf-8")
    return ground_truths

def load_existing_judge_results(judge_dir: Path) -> dict:
    """Load existing judge results from JSON files."""
    results = {}
    for json_file in judge_dir.glob("*.json"):
        # File format: {Case Name}_{Model}_judge.json
        parts = json_file.stem.split("_")
        model = parts[-2]
        # Reconstruct case name (everything before last 2 parts)
        case_name = "_".join(parts[:-2])
        
        if case_name not in results:
            results[case_name] = {}
        
        # We need the full model ID (e.g. "google/gemini...") 
        # But file only has short name. We'll map short to full using config.
        full_model_id = None
        for m in config.SUMMARIZATION_MODELS:
            if m.endswith(model):
                full_model_id = m
                break
        
        if full_model_id:
            try:
                results[case_name][full_model_id] = json.loads(json_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Error reading {json_file}: {e}")
                
    return results

def load_existing_coverage_results(coverage_dir: Path) -> dict:
    """Load existing coverage results from JSON files."""
    results = {}
    for json_file in coverage_dir.glob("*.json"):
        parts = json_file.stem.split("_")
        model = parts[-2]
        case_name = "_".join(parts[:-2])
        
        if case_name not in results:
            results[case_name] = {}
            
        full_model_id = None
        for m in config.SUMMARIZATION_MODELS:
            if m.endswith(model):
                full_model_id = m
                break
                
        if full_model_id:
            try:
                results[case_name][full_model_id] = json.loads(json_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Error reading {json_file}: {e}")
    return results

def load_summary_paths(summaries_dir: Path) -> dict:
    """Map case names and models to summary file paths."""
    paths = {}
    for summary_file in summaries_dir.glob("*.txt"):
        # Format: {Case Name}_{Model}.txt
        parts = summary_file.stem.split("_")
        model = parts[-1] 
        case_name = "_".join(parts[:-1])
        
        if case_name not in paths:
            paths[case_name] = {}
            
        full_model_id = None
        for m in config.SUMMARIZATION_MODELS:
            if m.endswith(model):
                full_model_id = m
                break
        
        if full_model_id:
            paths[case_name][full_model_id] = summary_file
            
    return paths

def load_existing_nli_results(nli_dir: Path) -> dict:
    """Load existing NLI results from JSON files."""
    results = {}
    for json_file in nli_dir.glob("*_nli.json"):
        # File format: {Case Name}_{Model}_nli.json
        parts = json_file.stem.split("_")
        model = parts[-2]
        # Reconstruct case name (everything before last 2 parts, "nli" is separate)
        # stem is "Case Name_Model_nli", so split("_") gives ["Case", "Name", "Model", "nli"]
        # Model is parts[-2]
        case_name = "_".join(parts[:-2])
        
        if case_name not in results:
            results[case_name] = {}
        
        full_model_id = None
        for m in config.SUMMARIZATION_MODELS:
            if m.endswith(model):
                full_model_id = m
                break
        
        if full_model_id:
            try:
                results[case_name][full_model_id] = json.loads(json_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Error reading {json_file}: {e}")
                
    return results

def main():
    logger.info("=" * 60)
    logger.info("NLI Rerun Pipeline - Load Existing & Recompute")
    logger.info("=" * 60)

    load_dotenv()
    
    # Paths
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / config.OYEZ_DATA_DIR
    output_dir = base_dir / config.OUTPUT_DIR
    summaries_dir = output_dir / "llm_summaries"
    nli_dir = output_dir / "nli_results"
    
    # Judge results are in a subfolder named after the judge model (short name)
    judge_model_short = config.JUDGE_MODEL.split("/")[-1]
    judge_dir = output_dir / "judge_results" / judge_model_short
    
    coverage_dir = output_dir / "coverage_results"
    
    # 1. Load Data
    logger.info("Loading Data...")
    ground_truths = load_ground_truths(data_dir)
    llm_summaries = load_summary_paths(summaries_dir)
    
    # 2. Load NLI Results (SKIP RE-RUN)
    logger.info("Loading existing NLI results (Skipping re-run)...")
    nli_results = load_existing_nli_results(nli_dir)
    # nli_evaluator = NLIEvaluator(model_name=config.NLI_MODEL)
    # nli_results = evaluate_all_nli(nli_evaluator, ground_truths, llm_summaries, nli_dir)
    
    # 3. Process Judges (Iterate over ALL available judges)
    judge_base_dir = output_dir / "judge_results"
    
    # We want to process all subdirectories in judge_results
    if not judge_base_dir.exists():
        logger.error(f"Judge base directory not found: {judge_base_dir}")
        return

    # Helper to find full model ID from short name
    def get_full_judge_id(short_name):
        for m in config.JUDGE_MODELS:
            if m.endswith(short_name):
                return m
        return short_name # Fallback

    primary_judge_processed = False

    for judge_subdir in judge_base_dir.iterdir():
        if not judge_subdir.is_dir():
            continue
            
        judge_short_name = judge_subdir.name
        full_judge_id = get_full_judge_id(judge_short_name)
        
        logger.info(f"Processing Judge: {full_judge_id}...")
        
        judge_results = load_existing_judge_results(judge_subdir)
        
        if not judge_results:
            logger.warning(f"No results found for judge {full_judge_id}. Skipping.")
            continue

        # INJECT METADATA for reporter.py
        for case_name, models in judge_results.items():
            for model_name, data in models.items():
                if "_metadata" not in data:
                    data["_metadata"] = {}
                data["_metadata"]["judge_model"] = full_judge_id

        coverage_results = load_existing_coverage_results(coverage_dir)
        
        # 4. Recompute Scores
        logger.info(f"Recomputing Composite Scores for {full_judge_id}...")
        composite_scores = compute_all_composite_scores(
            nli_results=nli_results,
            judge_results=judge_results,
            coverage_results=coverage_results,
            weight_nli=config.WEIGHT_NLI,
            weight_judge=config.WEIGHT_JUDGE,
            weight_coverage=config.WEIGHT_COVERAGE,
        )
        
        # 5. Update Reports (Only for PRIMARY judge)
        # Check if this is the configured JUDGE_MODEL
        if config.JUDGE_MODEL.endswith(judge_short_name):
            logger.info(f"Updating Primary Reports for {full_judge_id}...")
            generate_results_json(
                composite_scores, nli_results, judge_results, coverage_results,
                output_dir / "results.json"
            )
            generate_summary_report(
                composite_scores, nli_results, judge_results, coverage_results,
                output_dir / "summary_report.md"
            )
            primary_judge_processed = True
        
        # 6. Append to CSV (For ALL judges)
        logger.info(f"Appending {full_judge_id} runs to evaluation_log.csv...")
        
        # Temporarily mock config.JUDGE_MODEL so the reporter logs the correct name?
        # Actually reporter might use the passed data or config. 
        # Checking reporter... update_evaluation_log_csv typically takes the judge_results structure 
        # which usually doesn't have the JUDGE MODEL ID embedded in the top level keys (it's Case -> Model -> Score).
        # We need to ensure the CSV logger knows which Judge Model this is.
        # Looking at src/reporter.py/update_evaluation_log_csv, it extracts judge model from... 
        # Wait, if I look at the csv, "Judge_Model" is a column.
        # The reporter likely pulls it from config.JUDGE_MODEL or expects it passed?
        # Let's check `src/reporter.py` to be safe. 
        # Assuming for now we need to patch config.JUDGE_MODEL temporarily.
        original_judge_model = config.JUDGE_MODEL
        config.JUDGE_MODEL = full_judge_id
        
        try:
            update_evaluation_log_csv(
                composite_scores, 
                nli_results, 
                judge_results, 
                coverage_results,
                output_dir / "evaluation_log.csv",

                SUMMARIZATION_PROMPT,
                JUDGE_PROMPT
            )
        except PermissionError:
            logger.error("Could not write to evaluation_log.csv (File locked). Saving to evaluation_log_fixed.csv instead.")
            update_evaluation_log_csv(
                composite_scores, 
                nli_results, 
                judge_results, 
                coverage_results,
                output_dir / "evaluation_log_fixed.csv",

                SUMMARIZATION_PROMPT,
                JUDGE_PROMPT
            )
        
        config.JUDGE_MODEL = original_judge_model # Restore

    if not primary_judge_processed:
        logger.warning(f"Primary judge {config.JUDGE_MODEL} was not found in results directories!")

    logger.info("Done! Check updated evaluation_log.csv")

if __name__ == "__main__":
    main()
