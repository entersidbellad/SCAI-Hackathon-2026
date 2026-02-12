"""
AI Summarization Faithfulness Benchmark Pipeline
Main entry point that orchestrates the entire evaluation process.
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Import configuration
import config

# Import pipeline components
from src.pdf_extractor import extract_all_pdfs
from src.openrouter_client import OpenRouterClient
from src.summarizer import summarize_all_cases, SUMMARIZATION_PROMPT
from src.evaluators.nli_evaluator import NLIEvaluator, evaluate_all_nli
from src.evaluators.judge_evaluator import JudgeEvaluator, evaluate_all_judge, get_judge_prompt
from src.evaluators.coverage_evaluator import CoverageEvaluator, evaluate_all_coverage
from src.composite_scorer import compute_all_composite_scores
from src.reporter import generate_results_json, generate_summary_report, update_evaluation_log_csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log", mode="w"),
    ],
)
logger = logging.getLogger(__name__)


def load_ground_truths(data_dir: Path) -> dict[str, str]:
    """Load all ground truth summary files."""
    ground_truths = {}
    
    for summary_path in sorted(data_dir.glob("*summary.txt")):
        # Extract case name (e.g., "1 Ontario v. Quon")
        case_name = summary_path.stem.replace(" summary", "")
        ground_truths[case_name] = summary_path.read_text(encoding="utf-8")
        logger.info(f"Loaded ground truth: {case_name}")
    
    return ground_truths


def main():
    """Run the complete evaluation pipeline."""
    logger.info("=" * 60)
    logger.info("AI Summarization Faithfulness Benchmark Pipeline")
    logger.info("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    # Set up paths
    base_dir = Path(__file__).parent
    data_dir = base_dir / config.OYEZ_DATA_DIR
    output_dir = base_dir / config.OUTPUT_DIR
    
    # Create output directories
    output_dir.mkdir(exist_ok=True)
    extracted_dir = output_dir / "extracted_texts"
    summaries_dir = output_dir / "llm_summaries"
    nli_dir = output_dir / "nli_results"
    judge_dir = output_dir / "judge_results"
    coverage_dir = output_dir / "coverage_results"
    
    # =========================================================================
    # STEP 1: Extract text from PDFs
    # =========================================================================
    logger.info("")
    logger.info("STEP 1: Extracting text from PDFs")
    logger.info("-" * 40)
    
    extracted_texts = extract_all_pdfs(data_dir, extracted_dir)
    logger.info(f"Extracted text from {len(extracted_texts)} cases")
    
    # =========================================================================
    # STEP 2: Load ground truths
    # =========================================================================
    logger.info("")
    logger.info("STEP 2: Loading ground truth summaries")
    logger.info("-" * 40)
    
    ground_truths = load_ground_truths(data_dir)
    logger.info(f"Loaded {len(ground_truths)} ground truth summaries")
    
    # =========================================================================
    # STEP 3: Generate LLM summaries
    # =========================================================================
    logger.info("")
    logger.info("STEP 3: Generating LLM summaries")
    logger.info("-" * 40)
    
    client = OpenRouterClient()
    llm_summaries = summarize_all_cases(
        client=client,
        models=config.SUMMARIZATION_MODELS,
        extracted_texts=extracted_texts,
        output_dir=summaries_dir,
        delay_between_requests=config.API_DELAY,
    )
    
    # =========================================================================
    # STEP 4: Three-Pillar Evaluation
    # =========================================================================
    logger.info("")
    logger.info("STEP 4: Running three-pillar evaluation")
    logger.info("-" * 40)
    
    # Pillar 1: NLI Contradiction Detection
    logger.info("")
    logger.info("Pillar 1: NLI Contradiction Detection")
    nli_evaluator = NLIEvaluator(model_name=config.NLI_MODEL)
    nli_results = evaluate_all_nli(nli_evaluator, ground_truths, llm_summaries, nli_dir)
    
    # Pillar 2: LLM-as-a-Judge
    logger.info("")
    logger.info("Pillar 2: LLM-as-a-Judge")
    judge_evaluator = JudgeEvaluator(client=client, judge_model=config.JUDGE_MODEL)
    judge_results = evaluate_all_judge(judge_evaluator, ground_truths, llm_summaries, judge_dir)
    
    # Pillar 3: Embedding-based Coverage
    logger.info("")
    logger.info("Pillar 3: Embedding-based Coverage")
    coverage_evaluator = CoverageEvaluator(
        model_name=config.EMBEDDING_MODEL,
        threshold=config.COVERAGE_THRESHOLD,
    )
    coverage_results = evaluate_all_coverage(coverage_evaluator, ground_truths, llm_summaries, coverage_dir)
    
    # =========================================================================
    # STEP 5: Compute Composite Scores
    # =========================================================================
    logger.info("")
    logger.info("STEP 5: Computing composite scores")
    logger.info("-" * 40)
    
    composite_scores = compute_all_composite_scores(
        nli_results=nli_results,
        judge_results=judge_results,
        coverage_results=coverage_results,
        weight_nli=config.WEIGHT_NLI,
        weight_judge=config.WEIGHT_JUDGE,
        weight_coverage=config.WEIGHT_COVERAGE,
    )
    
    logger.info(f"Best model: {composite_scores['best_model']}")
    logger.info(f"Best average score: {composite_scores['best_avg_score']:.3f}")
    
    # =========================================================================
    # STEP 6: Generate Reports
    # =========================================================================
    logger.info("")
    logger.info("STEP 6: Generating reports")
    logger.info("-" * 40)
    
    results_path = generate_results_json(
        composite_scores=composite_scores,
        nli_results=nli_results,
        judge_results=judge_results,
        coverage_results=coverage_results,
        output_path=output_dir / "results.json",
    )
    
    report_path = generate_summary_report(
        composite_scores=composite_scores,
        nli_results=nli_results,
        judge_results=judge_results,
        coverage_results=coverage_results,
        output_path=output_dir / "summary_report.md",
    )
    
    # Generate CSV Log (Persistent)
    csv_path = update_evaluation_log_csv(
        composite_scores=composite_scores,
        nli_results=nli_results,
        judge_results=judge_results,
        coverage_results=coverage_results,
        output_path=output_dir / "evaluation_log.csv",
        summarization_prompt=SUMMARIZATION_PROMPT,
        judge_prompt=get_judge_prompt(),
    )
    
    # =========================================================================
    # Done!
    # =========================================================================
    logger.info("")
    logger.info("=" * 60)
    logger.info("Pipeline complete!")
    logger.info("=" * 60)
    logger.info(f"Results saved to: {output_dir}")
    logger.info(f"  - results.json: Full structured results")
    logger.info(f"  - summary_report.md: Human-readable report")
    logger.info("")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
