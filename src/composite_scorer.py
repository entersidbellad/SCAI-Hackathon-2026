"""
Composite Scorer
Combines the three evaluation pillars into a single faithfulness score.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def compute_composite_score(
    nli_result: dict,
    judge_result: dict,
    coverage_result: dict,
    weight_nli: float = 0.35,
    weight_judge: float = 0.40,
    weight_coverage: float = 0.25,
) -> dict:
    """
    Compute a composite faithfulness score from the three pillars.
    
    Formula:
        Faithfulness = weight_nli × NLI_Score + weight_judge × Judge_Score + weight_coverage × Coverage_Score
    
    Where:
        - NLI_Score = 1 - contradiction_rate (higher is better)
        - Judge_Score = (factual_accuracy + completeness) / 10 (normalized 0-1)
        - Coverage_Score = coverage_percentage / 100 (0-1)
    
    Args:
        nli_result: Results from NLI evaluator
        judge_result: Results from judge evaluator
        coverage_result: Results from coverage evaluator
        weight_nli: Weight for NLI pillar (default 0.35)
        weight_judge: Weight for Judge pillar (default 0.40)
        weight_coverage: Weight for Coverage pillar (default 0.25)
        
    Returns:
        Dict with individual scores and composite score
    """
    # Extract individual pillar scores
    nli_score = nli_result.get("nli_score", 0)
    judge_score = judge_result.get("judge_score", 0)
    coverage_score = coverage_result.get("coverage_score", 0)
    
    # Compute composite
    composite = (
        weight_nli * nli_score +
        weight_judge * judge_score +
        weight_coverage * coverage_score
    )
    
    return {
        "nli_score": nli_score,
        "judge_score": judge_score,
        "coverage_score": coverage_score,
        "weights": {
            "nli": weight_nli,
            "judge": weight_judge,
            "coverage": weight_coverage,
        },
        "composite_score": composite,
    }


def compute_all_composite_scores(
    nli_results: dict[str, dict[str, Any]],
    judge_results: dict[str, dict[str, Any]],
    coverage_results: dict[str, dict[str, Any]],
    weight_nli: float = 0.35,
    weight_judge: float = 0.40,
    weight_coverage: float = 0.25,
) -> dict:
    """
    Compute composite scores for all cases and models.
    
    Args:
        nli_results: NLI results {case: {model: result}}
        judge_results: Judge results {case: {model: result}}
        coverage_results: Coverage results {case: {model: result}}
        weight_*: Weights for each pillar
        
    Returns:
        Nested dict with composite scores per case and model
    """
    all_scores = {}
    model_aggregates = {}  # Track aggregates per model
    
    for case_name in nli_results.keys():
        all_scores[case_name] = {}
        
        for model in nli_results.get(case_name, {}).keys():
            nli_result = nli_results.get(case_name, {}).get(model, {})
            judge_result = judge_results.get(case_name, {}).get(model, {})
            coverage_result = coverage_results.get(case_name, {}).get(model, {})
            
            score = compute_composite_score(
                nli_result,
                judge_result,
                coverage_result,
                weight_nli,
                weight_judge,
                weight_coverage,
            )
            
            all_scores[case_name][model] = score
            
            # Aggregate for model-level stats
            if model not in model_aggregates:
                model_aggregates[model] = {
                    "nli_scores": [],
                    "judge_scores": [],
                    "coverage_scores": [],
                    "composite_scores": [],
                }
            
            model_aggregates[model]["nli_scores"].append(score["nli_score"])
            model_aggregates[model]["judge_scores"].append(score["judge_score"])
            model_aggregates[model]["coverage_scores"].append(score["coverage_score"])
            model_aggregates[model]["composite_scores"].append(score["composite_score"])
            
            logger.info(
                f"{case_name} / {model.split('/')[-1].split(':')[0]}: "
                f"composite={score['composite_score']:.3f}"
            )
    
    # Compute model-level averages
    model_averages = {}
    for model, agg in model_aggregates.items():
        n = len(agg["composite_scores"])
        model_averages[model] = {
            "avg_nli_score": sum(agg["nli_scores"]) / n if n else 0,
            "avg_judge_score": sum(agg["judge_scores"]) / n if n else 0,
            "avg_coverage_score": sum(agg["coverage_scores"]) / n if n else 0,
            "avg_composite_score": sum(agg["composite_scores"]) / n if n else 0,
            "num_cases": n,
        }
    
    # Find best model
    best_model = max(
        model_averages.keys(),
        key=lambda m: model_averages[m]["avg_composite_score"],
    ) if model_averages else None
    
    return {
        "per_case": all_scores,
        "per_model": model_averages,
        "best_model": best_model,
        "best_avg_score": model_averages.get(best_model, {}).get("avg_composite_score", 0),
    }
