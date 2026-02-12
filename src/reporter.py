"""
Report Generator
Creates JSON results and markdown summary reports.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def generate_results_json(
    composite_scores: dict,
    nli_results: dict,
    judge_results: dict,
    coverage_results: dict,
    output_path: Path,
) -> Path:
    """
    Generate the full results JSON file.
    
    Args:
        composite_scores: Composite score results
        nli_results: Full NLI results
        judge_results: Full judge results
        coverage_results: Full coverage results
        output_path: Path to save results.json
        
    Returns:
        Path to saved file
    """
    results = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "num_cases": len(composite_scores.get("per_case", {})),
            "num_models": len(composite_scores.get("per_model", {})),
        },
        "summary": {
            "best_model": composite_scores.get("best_model"),
            "best_avg_score": composite_scores.get("best_avg_score"),
            "model_rankings": sorted(
                [
                    {"model": model, "avg_score": stats["avg_composite_score"]}
                    for model, stats in composite_scores.get("per_model", {}).items()
                ],
                key=lambda x: x["avg_score"],
                reverse=True,
            ),
        },
        "composite_scores": composite_scores,
        "nli_results": _clean_for_json(nli_results),
        "judge_results": judge_results,
        "coverage_results": _clean_for_json(coverage_results),
    }
    
    output_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    logger.info(f"Saved results JSON to: {output_path}")
    return output_path


def _clean_for_json(data: dict) -> dict:
    """Clean data for JSON serialization by converting Path objects."""
    if isinstance(data, dict):
        return {k: _clean_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_clean_for_json(v) for v in data]
    elif isinstance(data, Path):
        return str(data)
    return data


def analyze_failure_modes(
    nli_results: dict,
    judge_results: dict,
    coverage_results: dict,
) -> dict:
    """
    Analyze common failure modes across all evaluations.
    
    Returns counts and examples of:
    - Contradictions (from NLI)
    - Omissions (from Coverage)
    - Hedging/Softening (from Judge)
    """
    total_contradictions = 0
    total_omissions = 0
    total_hedging = 0
    total_evaluations = 0
    
    contradiction_examples = []
    omission_examples = []
    hedging_examples = []
    
    for case_name in nli_results.keys():
        for model in nli_results.get(case_name, {}).keys():
            total_evaluations += 1
            model_short = model.split("/")[-1].split(":")[0]
            
            # Count contradictions
            nli = nli_results.get(case_name, {}).get(model, {})
            contradiction_count = nli.get("counts", {}).get("contradiction", 0)
            total_contradictions += contradiction_count
            
            # Get contradiction examples
            for sent_result in nli.get("sentence_results", [])[:2]:
                if sent_result.get("label") == "contradiction":
                    contradiction_examples.append({
                        "case": case_name,
                        "model": model_short,
                        "sentence": sent_result.get("sentence", "")[:200],
                    })
            
            # Count omissions
            coverage = coverage_results.get(case_name, {}).get(model, {})
            omission_count = len(coverage.get("omissions", []))
            total_omissions += omission_count
            
            # Get omission examples
            for omission in coverage.get("omissions", [])[:2]:
                omission_examples.append({
                    "case": case_name,
                    "model": model_short,
                    "sentence": omission.get("sentence", "")[:200],
                    "best_similarity": omission.get("best_similarity", 0),
                })
            
            # Count hedging
            judge = judge_results.get(case_name, {}).get(model, {})
            if judge.get("hedging_detected", False):
                total_hedging += 1
                for example in judge.get("hedging_examples", [])[:2]:
                    # Handle both old string format and new dict format
                    if isinstance(example, dict):
                        example_text = example.get("issue", "") or example.get("summary_says", "")
                    else:
                        example_text = str(example) if example else ""
                    if example_text:
                        hedging_examples.append({
                            "case": case_name,
                            "model": model_short,
                            "example": example_text[:200],
                        })
    
    return {
        "total_evaluations": total_evaluations,
        "contradiction_count": total_contradictions,
        "omission_count": total_omissions,
        "hedging_count": total_hedging,
        "contradiction_examples": contradiction_examples[:5],
        "omission_examples": omission_examples[:5],
        "hedging_examples": hedging_examples[:5],
    }


def generate_summary_report(
    composite_scores: dict,
    nli_results: dict,
    judge_results: dict,
    coverage_results: dict,
    output_path: Path,
) -> Path:
    """
    Generate a markdown summary report.
    
    Args:
        composite_scores: Composite score results
        nli_results: Full NLI results
        judge_results: Full judge results
        coverage_results: Full coverage results
        output_path: Path to save report
        
    Returns:
        Path to saved file
    """
    failures = analyze_failure_modes(nli_results, judge_results, coverage_results)
    
    lines = [
        "# AI Summarization Faithfulness Benchmark Report",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"- **Best Performing Model**: `{composite_scores.get('best_model', 'N/A')}`",
        f"- **Best Average Score**: {composite_scores.get('best_avg_score', 0):.3f} / 1.000",
        f"- **Cases Evaluated**: {len(composite_scores.get('per_case', {}))}",
        f"- **Models Tested**: {len(composite_scores.get('per_model', {}))}",
        "",
        "---",
        "",
        "## Model Rankings",
        "",
        "| Rank | Model | Avg Score | NLI | Judge | Coverage |",
        "|------|-------|-----------|-----|-------|----------|",
    ]
    
    # Sort models by average score
    model_stats = composite_scores.get("per_model", {})
    sorted_models = sorted(
        model_stats.items(),
        key=lambda x: x[1]["avg_composite_score"],
        reverse=True,
    )
    
    for rank, (model, stats) in enumerate(sorted_models, 1):
        model_short = model.split("/")[-1].split(":")[0]
        lines.append(
            f"| {rank} | {model_short} | "
            f"{stats['avg_composite_score']:.3f} | "
            f"{stats['avg_nli_score']:.3f} | "
            f"{stats['avg_judge_score']:.3f} | "
            f"{stats['avg_coverage_score']:.3f} |"
        )
    
    lines.extend([
        "",
        "---",
        "",
        "## Per-Case Results",
        "",
    ])
    
    # Per-case table for each model
    for case_name, case_scores in composite_scores.get("per_case", {}).items():
        lines.append(f"### {case_name}")
        lines.append("")
        lines.append("| Model | Composite | NLI | Judge | Coverage |")
        lines.append("|-------|-----------|-----|-------|----------|")
        
        for model, scores in case_scores.items():
            model_short = model.split("/")[-1].split(":")[0]
            lines.append(
                f"| {model_short} | "
                f"{scores['composite_score']:.3f} | "
                f"{scores['nli_score']:.3f} | "
                f"{scores['judge_score']:.3f} | "
                f"{scores['coverage_score']:.3f} |"
            )
        
        lines.append("")
    
    lines.extend([
        "---",
        "",
        "## Failure Mode Analysis",
        "",
        f"Across all {failures['total_evaluations']} evaluations:",
        "",
        f"- **Total Contradictions Detected**: {failures['contradiction_count']}",
        f"- **Total Omissions Flagged**: {failures['omission_count']}",
        f"- **Hedging/Softening Instances**: {failures['hedging_count']}",
        "",
    ])
    
    # Contradiction examples
    if failures["contradiction_examples"]:
        lines.extend([
            "### Contradiction Examples",
            "",
        ])
        for ex in failures["contradiction_examples"][:3]:
            lines.extend([
                f"**{ex['case']}** ({ex['model']}):",
                f"> {ex['sentence'][:150]}...",
                "",
            ])
    
    # Omission examples
    if failures["omission_examples"]:
        lines.extend([
            "### Omission Examples",
            "",
        ])
        for ex in failures["omission_examples"][:3]:
            lines.extend([
                f"**{ex['case']}** ({ex['model']}) - similarity: {ex['best_similarity']:.2f}:",
                f"> {ex['sentence'][:150]}...",
                "",
            ])
    
    # Hedging examples
    if failures["hedging_examples"]:
        lines.extend([
            "### Hedging/Softening Examples",
            "",
        ])
        for ex in failures["hedging_examples"][:3]:
            if ex["example"]:
                lines.extend([
                    f"**{ex['case']}** ({ex['model']}):",
                    f"> {ex['example'][:150]}...",
                    "",
                ])
    
    lines.extend([
        "---",
        "",
        "## Methodology",
        "",
        "### Composite Score Formula",
        "",
        "```",
        "Faithfulness = 0.35 × NLI_Score + 0.40 × Judge_Score + 0.25 × Coverage_Score",
        "```",
        "",
        "- **NLI Score**: 1 - contradiction_rate (DeBERTa-v3-large-mnli)",
        "- **Judge Score**: (factual_accuracy + completeness) / 10 (LLM-as-Judge)",
        "- **Coverage Score**: % of ground truth sentences covered (embedding similarity)",
        "",
    ])
    
    report_text = "\n".join(lines)
    output_path.write_text(report_text, encoding="utf-8")
    logger.info(f"Saved summary report to: {output_path}")
    return output_path


def update_evaluation_log_csv(
    composite_scores: dict,
    nli_results: dict,
    judge_results: dict,
    coverage_results: dict,
    output_path: Path,
    summarization_prompt: str,
    judge_prompt: str,
) -> Path:
    """
    Append run results to a persistent CSV log.
    
    Args:
        composite_scores: Composite score results
        nli_results: Full NLI results
        judge_results: Full judge results
        coverage_results: Full coverage results
        output_path: Path to CSV log file
        summarization_prompt: The prompt used for summarization
        judge_prompt: The prompt used for judging
        
    Returns:
        Path to the updated CSV file
    """
    import csv
    import os
    
    # Define CSV headers
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
    
    file_exists = output_path.exists()
    
    # Use 'a' for append mode, 'w' for write/create mode if not exists (handled by open)
    # newline="" is recommended for csv module
    try:
        with open(output_path, mode="a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            timestamp = datetime.now().isoformat()
            run_id = f"{timestamp}_{id(composite_scores)}"  # specific run identifier
            
            # Determine judge model name (assuming usually one per run, picking from first result)
            # If mixed judge models, we'd need more complex logic, but usually it's one.
            # We can try to extract from metadata if available, or just infer.
            # Ideally passed in, but let's try to find it.
            judge_model_set = set()
            
            # Iterate through per-case results to build rows
            for case_name, model_scores in composite_scores.get("per_case", {}).items():
                for model, scores in model_scores.items():
                    # Extract individual metrics
                    nli_score = scores.get("nli_score", 0)
                    judge_score = scores.get("judge_score", 0)
                    coverage_score = scores.get("coverage_score", 0)
                    composite = scores.get("composite_score", 0)
                    
                    # Detailed judge stats
                    # judge_results[case][model] might contain more details
                    judge_detail = judge_results.get(case_name, {}).get(model, {})
                    factual_acc = judge_detail.get("factual_accuracy", "")
                    completeness = judge_detail.get("completeness", "")
                    
                    # Try to get metadata from judge result for model name
                    current_judge_model = judge_detail.get("_metadata", {}).get("judge_model", 
                                                                                judge_detail.get("judge_model", "unknown"))
                    if current_judge_model != "unknown":
                        judge_model_set.add(current_judge_model)
                    
                    writer.writerow({
                        "Timestamp": timestamp,
                        "Run_ID": run_id,
                        "Case": case_name,
                        "Summarizer_Model": model,
                        "Judge_Model": current_judge_model,
                        "Composite_Score": f"{composite:.4f}",
                        "NLI_Score": f"{nli_score:.4f}",
                        "Judge_Score": f"{judge_score:.4f}",
                        "Coverage_Score": f"{coverage_score:.4f}",
                        "Factual_Accuracy": factual_acc,
                        "Completeness": completeness,
                        "Summarizer_Prompt": summarization_prompt,
                        "Judge_Prompt": judge_prompt,
                    })
                    
        logger.info(f"Updated evaluation log CSV at: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to update CSV log: {e}")
        return output_path
