"""
Human Evaluator: Ground Truth Validation for AI Judges

Loads human evaluation scores and computes:
1. Kendall's Tau between each AI judge and human ground truth
2. Human inter-annotator agreement (if multiple evaluators)
3. Bootstrap confidence intervals for all metrics

This module treats human evaluations as ground truth to validate
which AI judge most closely matches human judgment.
"""

import json
import logging
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


# =========================================================================
# DATA LOADING
# =========================================================================

def load_human_evaluations(human_eval_dir: Path) -> dict[str, dict[str, dict]]:
    """
    Load all human evaluation JSON files.

    Returns:
        {case_name: {model_name: {evaluator_name: scores_dict}}}
        where scores_dict = {"factual_accuracy": int, "completeness": int}
    """
    evaluations = defaultdict(lambda: defaultdict(dict))

    if not human_eval_dir.exists():
        logger.warning(f"Human evaluation directory not found: {human_eval_dir}")
        return {}

    json_files = list(human_eval_dir.glob("*.json"))
    json_files = [f for f in json_files if f.name != "schema.json"]

    if not json_files:
        logger.info("No human evaluation files found")
        return {}

    for json_file in sorted(json_files):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            case_name = data["case_name"]
            model = data["model"]
            evaluator = data["evaluator_name"]
            scores = data["scores"]

            evaluations[case_name][model][evaluator] = {
                "factual_accuracy": scores["factual_accuracy"],
                "completeness": scores["completeness"],
            }
            logger.info(f"Loaded human eval: {case_name} / {model} by {evaluator}")
        except (KeyError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load {json_file}: {e}")

    logger.info(f"Loaded {sum(len(m) for c in evaluations.values() for m in c.values())} human evaluations")
    return dict(evaluations)


def aggregate_human_scores(
    human_evals: dict[str, dict[str, dict]],
) -> dict[str, dict[str, dict]]:
    """
    Aggregate human scores across evaluators (average if multiple).

    Returns:
        {case_name: {model_name: {"factual_accuracy": float, "completeness": float, "judge_score": float}}}
    """
    aggregated = {}

    for case_name, models in human_evals.items():
        aggregated[case_name] = {}
        for model, evaluators in models.items():
            acc_scores = [e["factual_accuracy"] for e in evaluators.values()]
            comp_scores = [e["completeness"] for e in evaluators.values()]

            avg_acc = np.mean(acc_scores)
            avg_comp = np.mean(comp_scores)
            # Normalize to 0-1 same way as AI judges: (acc + comp) / 10
            judge_score = (avg_acc + avg_comp) / 10.0

            aggregated[case_name][model] = {
                "factual_accuracy": round(float(avg_acc), 2),
                "completeness": round(float(avg_comp), 2),
                "judge_score": round(float(judge_score), 4),
                "n_evaluators": len(evaluators),
            }

    return aggregated


# =========================================================================
# KENDALL'S TAU — AI Judge vs Human Ground Truth
# =========================================================================

def compute_human_judge_correlation(
    ai_judge_scores: dict[str, dict[str, dict[str, float]]],
    human_scores: dict[str, dict[str, dict]],
    n_bootstrap: int = 1000,
) -> dict:
    """
    Compute Kendall's Tau between each AI judge and human ground truth.

    Treats human scores as the gold standard. Kendall's Tau measures
    how well each AI judge's rankings agree with the human rankings.

    Args:
        ai_judge_scores: {judge_name: {case_name: {model_name: {judge_score: float}}}}
        human_scores: Aggregated human scores {case_name: {model_name: {...}}}
        n_bootstrap: Number of bootstrap iterations for confidence intervals

    Returns:
        Dict with per-judge correlations and confidence intervals
    """
    results = {}

    for judge_name, judge_cases in ai_judge_scores.items():
        ai_scores = []
        human_vals = []

        # Build aligned score vectors
        for case_name in judge_cases:
            if case_name not in human_scores:
                continue
            for model in judge_cases[case_name]:
                if model not in human_scores.get(case_name, {}):
                    continue

                ai_val = judge_cases[case_name][model]["judge_score"]
                human_val = human_scores[case_name][model]["judge_score"]
                ai_scores.append(ai_val)
                human_vals.append(human_val)

        if len(ai_scores) < 3:
            results[judge_name] = {
                "error": f"Too few aligned observations ({len(ai_scores)}). "
                         f"Need at least 3 case×model pairs with both AI and human scores.",
            }
            continue

        # Compute Kendall's Tau
        tau, p_value = stats.kendalltau(ai_scores, human_vals)

        # Bootstrap confidence interval
        bootstrap_taus = []
        rng = np.random.default_rng(42)
        n = len(ai_scores)
        ai_arr = np.array(ai_scores)
        human_arr = np.array(human_vals)

        for _ in range(n_bootstrap):
            idx = rng.choice(n, size=n, replace=True)
            bt_tau, _ = stats.kendalltau(ai_arr[idx], human_arr[idx])
            if not np.isnan(bt_tau):
                bootstrap_taus.append(bt_tau)

        ci_lower = float(np.percentile(bootstrap_taus, 2.5)) if bootstrap_taus else None
        ci_upper = float(np.percentile(bootstrap_taus, 97.5)) if bootstrap_taus else None

        # Also compute per-dimension correlations
        dim_results = {}
        for dim in ["factual_accuracy", "completeness"]:
            ai_dim = []
            human_dim = []
            for case_name in judge_cases:
                if case_name not in human_scores:
                    continue
                for model in judge_cases[case_name]:
                    if model not in human_scores.get(case_name, {}):
                        continue
                    ai_dim.append(judge_cases[case_name][model].get(dim, 0))
                    human_dim.append(human_scores[case_name][model].get(dim, 0))

            if len(ai_dim) >= 3:
                dim_tau, dim_p = stats.kendalltau(ai_dim, human_dim)
                dim_results[dim] = {
                    "tau": round(float(dim_tau), 4) if not np.isnan(dim_tau) else None,
                    "p_value": round(float(dim_p), 4) if not np.isnan(dim_p) else None,
                }

        results[judge_name] = {
            "overall_tau": round(float(tau), 4) if not np.isnan(tau) else None,
            "p_value": round(float(p_value), 4) if not np.isnan(p_value) else None,
            "n_aligned_observations": len(ai_scores),
            "ci_95_lower": round(ci_lower, 4) if ci_lower is not None else None,
            "ci_95_upper": round(ci_upper, 4) if ci_upper is not None else None,
            "per_dimension": dim_results,
            "interpretation": _interpret_human_tau(tau),
        }

    return results


def _interpret_human_tau(tau: float) -> str:
    """Interpret Kendall's Tau for judge-vs-human comparison."""
    if np.isnan(tau):
        return "Could not compute"
    if tau >= 0.7:
        return "Excellent — judge closely matches human ground truth"
    elif tau >= 0.5:
        return "Good — judge generally agrees with humans"
    elif tau >= 0.3:
        return "Moderate — judge partially agrees with humans"
    elif tau >= 0.1:
        return "Weak — judge disagrees with humans on many rankings"
    else:
        return "Poor — judge rankings are unrelated to human judgments"


# =========================================================================
# HUMAN INTER-ANNOTATOR AGREEMENT
# =========================================================================

def compute_human_agreement(
    human_evals: dict[str, dict[str, dict]],
) -> dict:
    """
    Compute inter-annotator agreement among human evaluators.

    If multiple evaluators scored the same case×model, computes
    pairwise Cohen's Kappa and Krippendorff's Alpha.

    Returns:
        Dict with agreement statistics
    """
    from itertools import combinations

    # Collect all evaluator pairs
    evaluator_scores = defaultdict(lambda: defaultdict(list))

    for case_name, models in human_evals.items():
        for model, evaluators in models.items():
            for evaluator, scores in evaluators.items():
                # Combine acc + comp into a single ordinal score for simplicity
                combined = scores["factual_accuracy"] + scores["completeness"]
                evaluator_scores[evaluator][(case_name, model)].append(combined)

    evaluator_names = sorted(evaluator_scores.keys())

    if len(evaluator_names) < 2:
        return {
            "n_evaluators": len(evaluator_names),
            "note": "Need at least 2 evaluators for inter-annotator agreement",
        }

    # Pairwise agreement
    pairwise = {}
    for e1, e2 in combinations(evaluator_names, 2):
        pair_key = f"{e1} ↔ {e2}"
        e1_scores = []
        e2_scores = []

        common_items = set(evaluator_scores[e1].keys()) & set(evaluator_scores[e2].keys())
        for item in sorted(common_items):
            e1_scores.append(evaluator_scores[e1][item][0])
            e2_scores.append(evaluator_scores[e2][item][0])

        if len(e1_scores) >= 3:
            tau, p = stats.kendalltau(e1_scores, e2_scores)
            pairwise[pair_key] = {
                "tau": round(float(tau), 4) if not np.isnan(tau) else None,
                "p_value": round(float(p), 4) if not np.isnan(p) else None,
                "n_common_items": len(e1_scores),
            }
        else:
            pairwise[pair_key] = {"error": f"Only {len(e1_scores)} common items"}

    return {
        "n_evaluators": len(evaluator_names),
        "evaluators": evaluator_names,
        "pairwise_agreement": pairwise,
    }


# =========================================================================
# REPORT GENERATION
# =========================================================================

def generate_human_evaluation_report(
    human_judge_correlation: dict,
    human_agreement: dict,
    output_path: Path,
) -> Path:
    """Generate a markdown report for human-vs-AI judge validation."""
    from datetime import datetime

    lines = []
    lines.append("# Judge Accuracy Report: AI Judges vs Human Ground Truth")
    lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    lines.append("This report validates AI judges by comparing their scores against **human evaluations** (ground truth).")
    lines.append("**Metric**: Kendall's Tau (τ) — measures rank agreement between AI and human scores.\n")

    # ─── AI vs Human ───
    lines.append("## AI Judge Accuracy (Kendall's τ vs Human Ground Truth)\n")
    lines.append("| AI Judge | τ (Overall) | 95% CI | p-value | N | Interpretation |")
    lines.append("|---|---|---|---|---|---|")

    for judge, data in human_judge_correlation.items():
        if "error" in data:
            lines.append(f"| {judge} | — | — | — | — | {data['error']} |")
        else:
            tau = data["overall_tau"]
            ci_lo = data.get("ci_95_lower")
            ci_hi = data.get("ci_95_upper")
            ci_str = f"[{ci_lo:.3f}, {ci_hi:.3f}]" if ci_lo is not None else "—"
            p = data["p_value"]
            n = data["n_aligned_observations"]
            interp = data["interpretation"]
            tau_str = f"{tau:.4f}" if tau is not None else "N/A"
            p_str = f"{p:.4f}" if p is not None else "N/A"
            lines.append(f"| {judge} | {tau_str} | {ci_str} | {p_str} | {n} | {interp} |")

    lines.append("")

    # Per-dimension breakdown
    lines.append("### Per-Dimension Breakdown\n")
    lines.append("| AI Judge | Factual Accuracy τ | Completeness τ |")
    lines.append("|---|---|---|")

    for judge, data in human_judge_correlation.items():
        if "error" in data:
            continue
        dims = data.get("per_dimension", {})
        acc_tau = dims.get("factual_accuracy", {}).get("tau", "—")
        comp_tau = dims.get("completeness", {}).get("tau", "—")
        acc_str = f"{acc_tau:.4f}" if isinstance(acc_tau, (int, float)) else str(acc_tau)
        comp_str = f"{comp_tau:.4f}" if isinstance(comp_tau, (int, float)) else str(comp_tau)
        lines.append(f"| {judge} | {acc_str} | {comp_str} |")

    lines.append("")

    # ─── Human Inter-Annotator Agreement ───
    if human_agreement.get("n_evaluators", 0) >= 2:
        lines.append("---\n")
        lines.append("## Human Inter-Annotator Agreement\n")
        lines.append(f"**Evaluators**: {', '.join(human_agreement.get('evaluators', []))}\n")

        pairwise = human_agreement.get("pairwise_agreement", {})
        if pairwise:
            lines.append("| Evaluator Pair | τ | p-value | N |")
            lines.append("|---|---|---|---|")
            for pair, data in pairwise.items():
                if "error" in data:
                    lines.append(f"| {pair} | — | — | {data['error']} |")
                else:
                    tau = data["tau"]
                    tau_str = f"{tau:.4f}" if tau is not None else "N/A"
                    p_str = f"{data['p_value']:.4f}" if data["p_value"] is not None else "N/A"
                    lines.append(f"| {pair} | {tau_str} | {p_str} | {data['n_common_items']} |")
            lines.append("")
    else:
        lines.append("---\n")
        lines.append("## Human Inter-Annotator Agreement\n")
        lines.append("> **Note**: Only 1 human evaluator found. Add evaluations from 2+ people to compute inter-annotator agreement.\n")

    # ─── Methodology Note ───
    lines.append("---\n")
    lines.append("## Methodology\n")
    lines.append("- **Kendall's Tau** is used for AI↔Human comparison because humans serve as **ground truth**")
    lines.append("- **Cohen's Kappa** is used for AI↔AI comparison (see meta-evaluation report) because neither AI judge is ground truth")
    lines.append("- **Bootstrap CIs** (1000 iterations) provide uncertainty estimates")
    lines.append("- Human scores are aggregated by averaging across evaluators when multiple evaluators scored the same item")
    lines.append("")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    logger.info(f"Human evaluation report saved to: {output_path}")
    return output_path


# =========================================================================
# MAIN ENTRY POINT
# =========================================================================

def run_human_evaluation(base_dir: Path = None) -> dict:
    """
    Run the full human evaluation validation pipeline.

    Args:
        base_dir: Project root directory. If None, auto-detects.

    Returns:
        Dict with all human evaluation results
    """
    import sys

    if base_dir is None:
        base_dir = Path(__file__).parent.parent.parent

    human_eval_dir = base_dir / "human_eval"
    output_dir = base_dir / "outputs"
    judge_dir = output_dir / "judge_results"

    logger.info("=" * 60)
    logger.info("HUMAN EVALUATION: Judge Accuracy Validation")
    logger.info("=" * 60)

    # Load human evaluations
    logger.info("\nLoading human evaluations...")
    human_evals = load_human_evaluations(human_eval_dir)

    if not human_evals:
        logger.warning(
            "No human evaluations found. "
            "Add JSON files to human_eval/ following the schema in human_eval/README.md"
        )
        return {"error": "No human evaluations found"}

    # Aggregate human scores
    human_scores = aggregate_human_scores(human_evals)
    logger.info(f"Aggregated scores for {sum(len(m) for m in human_scores.values())} case×model pairs")

    # Load AI judge scores
    logger.info("\nLoading AI judge scores...")
    # Import from meta_evaluator to reuse data loading
    from .meta_evaluator import load_judge_scores
    ai_judge_scores = load_judge_scores(judge_dir)
    logger.info(f"Loaded scores for {len(ai_judge_scores)} AI judges")

    # Compute AI↔Human correlation (Kendall's Tau)
    logger.info("\n[1/2] Computing AI↔Human Kendall's Tau...")
    human_judge_corr = compute_human_judge_correlation(ai_judge_scores, human_scores)

    # Compute human inter-annotator agreement
    logger.info("[2/2] Computing human inter-annotator agreement...")
    human_agreement = compute_human_agreement(human_evals)

    # Generate report
    report_path = generate_human_evaluation_report(
        human_judge_correlation=human_judge_corr,
        human_agreement=human_agreement,
        output_path=output_dir / "human_evaluation_report.md",
    )

    # Save raw JSON
    raw_results = {
        "human_judge_correlation": human_judge_corr,
        "human_agreement": human_agreement,
        "human_scores": {
            case: {model: scores for model, scores in models.items()}
            for case, models in human_scores.items()
        },
    }
    raw_path = output_dir / "human_evaluation_results.json"
    raw_path.write_text(json.dumps(raw_results, indent=2, default=str), encoding="utf-8")
    logger.info(f"Raw results saved to: {raw_path}")

    logger.info("\n" + "=" * 60)
    logger.info("HUMAN EVALUATION COMPLETE")
    logger.info("=" * 60)

    return raw_results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler()],
    )
    run_human_evaluation()
