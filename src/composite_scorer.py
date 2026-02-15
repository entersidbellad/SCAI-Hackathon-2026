"""
Composite Scorer
Combines the three evaluation pillars into a single faithfulness score.
Includes bootstrap confidence intervals and pairwise significance testing.
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def bootstrap_composite_ci(
    scores: list[float],
    n_bootstrap: int = 1000,
    ci: float = 0.95,
) -> dict:
    """
    Compute bootstrap confidence interval for a model's composite score.

    Args:
        scores: List of per-case composite scores for one model
        n_bootstrap: Number of bootstrap iterations
        ci: Confidence level (default 95%)

    Returns:
        Dict with mean, ci_lower, ci_upper, and std_error
    """
    arr = np.array(scores)
    n = len(arr)

    if n < 2:
        return {
            "mean": float(arr.mean()),
            "ci_lower": None,
            "ci_upper": None,
            "std_error": None,
        }

    rng = np.random.default_rng(42)
    boot_means = []

    for _ in range(n_bootstrap):
        idx = rng.choice(n, size=n, replace=True)
        boot_means.append(float(arr[idx].mean()))

    alpha = (1 - ci) / 2
    ci_lower = float(np.percentile(boot_means, alpha * 100))
    ci_upper = float(np.percentile(boot_means, (1 - alpha) * 100))

    return {
        "mean": float(arr.mean()),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "std_error": round(float(np.std(boot_means)), 4),
    }


def pairwise_significance_test(
    model_scores: dict[str, list[float]],
) -> dict:
    """
    Test whether differences between model pairs are statistically significant.

    Uses paired bootstrap test: for each pair of models, bootstraps the
    difference in means and checks if the 95% CI excludes zero.

    Args:
        model_scores: {model_name: [per-case composite scores]}

    Returns:
        Dict with pairwise comparisons
    """
    from itertools import combinations

    models = sorted(model_scores.keys())
    results = {}

    for m1, m2 in combinations(models, 2):
        scores_1 = np.array(model_scores[m1])
        scores_2 = np.array(model_scores[m2])

        # Only compare on cases where both have scores
        n = min(len(scores_1), len(scores_2))
        if n < 2:
            continue

        scores_1 = scores_1[:n]
        scores_2 = scores_2[:n]

        # Observed difference
        observed_diff = float(scores_1.mean() - scores_2.mean())

        # Bootstrap the difference
        rng = np.random.default_rng(42)
        boot_diffs = []
        for _ in range(1000):
            idx = rng.choice(n, size=n, replace=True)
            boot_diffs.append(float(scores_1[idx].mean() - scores_2[idx].mean()))

        ci_lower = float(np.percentile(boot_diffs, 2.5))
        ci_upper = float(np.percentile(boot_diffs, 97.5))

        # If CI excludes zero, the difference is significant at p < 0.05
        is_significant = (ci_lower > 0) or (ci_upper < 0)

        m1_short = m1.split("/")[-1].split(":")[0]
        m2_short = m2.split("/")[-1].split(":")[0]
        pair_key = f"{m1_short} vs {m2_short}"

        results[pair_key] = {
            "model_a": m1,
            "model_b": m2,
            "mean_diff": round(observed_diff, 4),
            "ci_95_lower": round(ci_lower, 4),
            "ci_95_upper": round(ci_upper, 4),
            "significant": is_significant,
            "winner": m1_short if observed_diff > 0 else m2_short,
        }

    return results


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
    
    # Compute model-level averages with confidence intervals
    model_averages = {}
    model_composite_lists = {}  # For pairwise testing

    for model, agg in model_aggregates.items():
        n = len(agg["composite_scores"])
        ci = bootstrap_composite_ci(agg["composite_scores"])
        model_composite_lists[model] = agg["composite_scores"]

        model_averages[model] = {
            "avg_nli_score": sum(agg["nli_scores"]) / n if n else 0,
            "avg_judge_score": sum(agg["judge_scores"]) / n if n else 0,
            "avg_coverage_score": sum(agg["coverage_scores"]) / n if n else 0,
            "avg_composite_score": sum(agg["composite_scores"]) / n if n else 0,
            "num_cases": n,
            "composite_ci_95": {
                "lower": ci["ci_lower"],
                "upper": ci["ci_upper"],
            },
            "composite_std_error": ci["std_error"],
        }

    # Find best model
    best_model = max(
        model_averages.keys(),
        key=lambda m: model_averages[m]["avg_composite_score"],
    ) if model_averages else None

    # Pairwise significance tests
    significance = pairwise_significance_test(model_composite_lists)

    return {
        "per_case": all_scores,
        "per_model": model_averages,
        "best_model": best_model,
        "best_avg_score": model_averages.get(best_model, {}).get("avg_composite_score", 0),
        "pairwise_significance": significance,
    }
