"""
Meta-Evaluator: Judge Calibration & Pillar Correlation Analysis

Answers the question: "How do you know your judges are performing well?"

Computes:
1. Kendall's Tau (τ) — rank correlation between judge pairs
2. Score Distribution Analysis — histogram stats per judge
3. Cohen's Kappa — inter-judge agreement on ordinal 1-5 scale
4. Pillar Correlation Matrix — Spearman ρ between NLI, Judge, Coverage

Uses only existing output data — no API calls required.
"""

import json
import logging
import sys
from collections import defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


# =========================================================================
# DATA LOADING
# =========================================================================

def load_judge_scores(judge_results_dir: Path) -> dict[str, dict[str, dict[str, float]]]:
    """
    Load all judge scores from disk.

    Returns:
        {judge_name: {case_name: {model_name: judge_score}}}
    """
    scores = {}

    for judge_dir in sorted(judge_results_dir.iterdir()):
        if not judge_dir.is_dir():
            continue

        judge_name = judge_dir.name
        scores[judge_name] = {}

        for json_file in sorted(judge_dir.glob("*_judge.json")):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))

                # Always parse from filename for consistency across judges.
                # Filename format: "1 Ontario v. Quon_grok-4.1-fast_judge.json"
                stem = json_file.stem.replace("_judge", "")
                parts = stem.rsplit("_", 1)
                case_name = parts[0] if len(parts) == 2 else stem
                model_short = parts[1] if len(parts) == 2 else "unknown"

                if case_name not in scores[judge_name]:
                    scores[judge_name][case_name] = {}

                scores[judge_name][case_name][model_short] = {
                    "judge_score": data.get("judge_score", 0),
                    "factual_accuracy": data.get("factual_accuracy", 0),
                    "completeness": data.get("completeness", 0),
                }
            except Exception as e:
                logger.warning(f"Failed to load {json_file}: {e}")

    return scores


def load_nli_scores(nli_results_dir: Path) -> dict[str, dict[str, float]]:
    """
    Load all NLI scores from disk.

    Returns:
        {case_name: {model_name: nli_score}}
    """
    scores = {}

    for json_file in sorted(nli_results_dir.glob("*_nli.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            # Parse case and model from filename: "1 Ontario v. Quon_grok-4.1-fast_nli.json"
            stem = json_file.stem.replace("_nli", "")
            # Find the last underscore that separates case from model
            # Model names contain hyphens but not spaces, case names contain spaces
            parts = stem.rsplit("_", 1)
            if len(parts) == 2:
                case_name, model_short = parts
            else:
                continue

            if case_name not in scores:
                scores[case_name] = {}
            scores[case_name][model_short] = data.get("nli_score", 0)
        except Exception as e:
            logger.warning(f"Failed to load {json_file}: {e}")

    return scores


def load_coverage_scores(coverage_results_dir: Path) -> dict[str, dict[str, float]]:
    """
    Load all coverage scores from disk.

    Returns:
        {case_name: {model_name: coverage_score}}
    """
    scores = {}

    for json_file in sorted(coverage_results_dir.glob("*_coverage.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            stem = json_file.stem.replace("_coverage", "")
            parts = stem.rsplit("_", 1)
            if len(parts) == 2:
                case_name, model_short = parts
            else:
                continue

            if case_name not in scores:
                scores[case_name] = {}
            scores[case_name][model_short] = data.get("coverage_score", 0)
        except Exception as e:
            logger.warning(f"Failed to load {json_file}: {e}")

    return scores


# =========================================================================
# 1. KENDALL'S TAU — Rank Correlation Between Judges
# =========================================================================

def compute_kendall_tau(
    judge_scores: dict[str, dict[str, dict[str, float]]],
) -> dict:
    """
    Compute Kendall's Tau between every pair of judges.

    For each case, ranks the summarization models by judge_score,
    then computes τ between each judge pair.

    Returns:
        Dict with per-case and overall τ values
    """
    judge_names = sorted(judge_scores.keys())
    if len(judge_names) < 2:
        return {"error": "Need at least 2 judges to compute Kendall's Tau"}

    results = {
        "pairwise": {},
        "per_case": {},
        "overall_summary": {},
    }

    for j1, j2 in combinations(judge_names, 2):
        pair_key = f"{j1} ↔ {j2}"
        per_case_taus = []
        all_scores_j1 = []
        all_scores_j2 = []

        # Get common cases
        common_cases = set(judge_scores[j1].keys()) & set(judge_scores[j2].keys())

        for case_name in sorted(common_cases):
            models_j1 = judge_scores[j1].get(case_name, {})
            models_j2 = judge_scores[j2].get(case_name, {})
            common_models = set(models_j1.keys()) & set(models_j2.keys())

            if len(common_models) < 2:
                continue

            scores_j1 = [models_j1[m]["judge_score"] for m in sorted(common_models)]
            scores_j2 = [models_j2[m]["judge_score"] for m in sorted(common_models)]

            all_scores_j1.extend(scores_j1)
            all_scores_j2.extend(scores_j2)

            # Per-case tau (may be NaN if all scores are tied)
            if len(set(scores_j1)) > 1 or len(set(scores_j2)) > 1:
                tau, p_value = stats.kendalltau(scores_j1, scores_j2)
                if not np.isnan(tau):
                    per_case_taus.append({
                        "case": case_name,
                        "tau": round(tau, 4),
                        "p_value": round(p_value, 4),
                    })

        # Overall tau across all cases
        if len(all_scores_j1) >= 3:
            overall_tau, overall_p = stats.kendalltau(all_scores_j1, all_scores_j2)
            results["pairwise"][pair_key] = {
                "overall_tau": round(float(overall_tau), 4) if not np.isnan(overall_tau) else None,
                "overall_p_value": round(float(overall_p), 4) if not np.isnan(overall_p) else None,
                "n_comparisons": len(all_scores_j1),
                "n_cases_with_tau": len(per_case_taus),
                "mean_per_case_tau": round(
                    np.mean([t["tau"] for t in per_case_taus]), 4
                ) if per_case_taus else None,
            }
            results["per_case"][pair_key] = per_case_taus

    # Interpretation
    for pair, data in results["pairwise"].items():
        tau = data.get("overall_tau")
        if tau is None:
            data["interpretation"] = "Could not compute (all scores tied)"
        elif abs(tau) >= 0.7:
            data["interpretation"] = "Strong agreement"
        elif abs(tau) >= 0.4:
            data["interpretation"] = "Moderate agreement"
        elif abs(tau) >= 0.2:
            data["interpretation"] = "Weak agreement"
        else:
            data["interpretation"] = "No meaningful agreement"

    return results


# =========================================================================
# 2. SCORE DISTRIBUTION ANALYSIS
# =========================================================================

def compute_score_distributions(
    judge_scores: dict[str, dict[str, dict[str, float]]],
) -> dict:
    """
    Analyze how each judge distributes scores across the 1-5 range.

    Flags judges with low discriminative power (clustered scores).
    """
    results = {}

    for judge_name, cases in judge_scores.items():
        accuracy_scores = []
        completeness_scores = []
        judge_score_vals = []

        for case_name, models in cases.items():
            for model, scores in models.items():
                accuracy_scores.append(scores["factual_accuracy"])
                completeness_scores.append(scores["completeness"])
                judge_score_vals.append(scores["judge_score"])

        if not accuracy_scores:
            continue

        # Frequency distribution for factual_accuracy (1-5)
        accuracy_dist = {i: accuracy_scores.count(i) for i in range(1, 6)}
        completeness_dist = {i: completeness_scores.count(i) for i in range(1, 6)}

        # Stats
        n = len(accuracy_scores)
        acc_arr = np.array(accuracy_scores)
        comp_arr = np.array(completeness_scores)
        js_arr = np.array(judge_score_vals)

        results[judge_name] = {
            "n_evaluations": n,
            "factual_accuracy": {
                "distribution": accuracy_dist,
                "mean": round(float(acc_arr.mean()), 3),
                "std": round(float(acc_arr.std()), 3),
                "min": int(acc_arr.min()),
                "max": int(acc_arr.max()),
                "range_used": int(acc_arr.max()) - int(acc_arr.min()),
            },
            "completeness": {
                "distribution": completeness_dist,
                "mean": round(float(comp_arr.mean()), 3),
                "std": round(float(comp_arr.std()), 3),
                "min": int(comp_arr.min()),
                "max": int(comp_arr.max()),
                "range_used": int(comp_arr.max()) - int(comp_arr.min()),
            },
            "judge_score_normalized": {
                "mean": round(float(js_arr.mean()), 4),
                "std": round(float(js_arr.std()), 4),
                "min": round(float(js_arr.min()), 4),
                "max": round(float(js_arr.max()), 4),
            },
            "warnings": [],
        }

        # Flag low discriminative power
        if acc_arr.std() < 0.5:
            results[judge_name]["warnings"].append(
                f"Low discriminative power on factual_accuracy (std={acc_arr.std():.3f}). "
                f"Scores cluster too tightly, making it hard to differentiate models."
            )
        if comp_arr.std() < 0.5:
            results[judge_name]["warnings"].append(
                f"Low discriminative power on completeness (std={comp_arr.std():.3f}). "
                f"Scores cluster too tightly."
            )

        # Flag if not using full range
        if int(acc_arr.max()) - int(acc_arr.min()) <= 1:
            results[judge_name]["warnings"].append(
                f"Only using {int(acc_arr.min())}-{int(acc_arr.max())} of the 1-5 range for factual_accuracy."
            )

    return results


# =========================================================================
# 3. COHEN'S KAPPA — Inter-Judge Agreement
# =========================================================================

def compute_cohens_kappa(
    judge_scores: dict[str, dict[str, dict[str, float]]],
) -> dict:
    """
    Compute weighted Cohen's Kappa between each pair of judges.

    Uses quadratic weights (appropriate for ordinal 1-5 scale).
    """
    judge_names = sorted(judge_scores.keys())
    if len(judge_names) < 2:
        return {"error": "Need at least 2 judges"}

    results = {}

    for j1, j2 in combinations(judge_names, 2):
        pair_key = f"{j1} ↔ {j2}"

        # Collect paired factual_accuracy scores
        accuracy_pairs = []
        completeness_pairs = []

        common_cases = set(judge_scores[j1].keys()) & set(judge_scores[j2].keys())

        for case_name in sorted(common_cases):
            common_models = set(
                judge_scores[j1].get(case_name, {}).keys()
            ) & set(
                judge_scores[j2].get(case_name, {}).keys()
            )

            for model in sorted(common_models):
                s1 = judge_scores[j1][case_name][model]
                s2 = judge_scores[j2][case_name][model]
                accuracy_pairs.append((s1["factual_accuracy"], s2["factual_accuracy"]))
                completeness_pairs.append((s1["completeness"], s2["completeness"]))

        if len(accuracy_pairs) < 3:
            results[pair_key] = {"error": "Too few paired observations"}
            continue

        # Compute quadratic-weighted kappa
        acc_kappa = _weighted_kappa(
            [p[0] for p in accuracy_pairs],
            [p[1] for p in accuracy_pairs],
            categories=list(range(1, 6)),
        )
        comp_kappa = _weighted_kappa(
            [p[0] for p in completeness_pairs],
            [p[1] for p in completeness_pairs],
            categories=list(range(1, 6)),
        )

        results[pair_key] = {
            "factual_accuracy_kappa": round(acc_kappa, 4),
            "completeness_kappa": round(comp_kappa, 4),
            "n_paired_observations": len(accuracy_pairs),
            "interpretation_accuracy": _interpret_kappa(acc_kappa),
            "interpretation_completeness": _interpret_kappa(comp_kappa),
        }

    return results


def _weighted_kappa(
    rater1: list[int],
    rater2: list[int],
    categories: list[int],
) -> float:
    """Compute quadratic-weighted Cohen's Kappa."""
    n = len(rater1)
    k = len(categories)
    cat_to_idx = {c: i for i, c in enumerate(categories)}

    # Build confusion matrix
    confusion = np.zeros((k, k))
    for r1, r2 in zip(rater1, rater2):
        i = cat_to_idx.get(r1, 0)
        j = cat_to_idx.get(r2, 0)
        confusion[i][j] += 1

    # Normalize
    confusion = confusion / n

    # Marginals
    row_marginals = confusion.sum(axis=1)
    col_marginals = confusion.sum(axis=0)

    # Expected matrix (outer product of marginals)
    expected = np.outer(row_marginals, col_marginals)

    # Quadratic weight matrix
    weights = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            weights[i][j] = (i - j) ** 2 / (k - 1) ** 2

    # Weighted kappa
    observed_disagreement = (weights * confusion).sum()
    expected_disagreement = (weights * expected).sum()

    if expected_disagreement == 0:
        return 1.0  # Perfect agreement

    kappa = 1 - (observed_disagreement / expected_disagreement)
    return float(kappa)


def _interpret_kappa(kappa: float) -> str:
    """Interpret Cohen's Kappa value using Landis & Koch scale."""
    if kappa < 0:
        return "Poor (worse than chance)"
    elif kappa < 0.20:
        return "Slight agreement"
    elif kappa < 0.40:
        return "Fair agreement"
    elif kappa < 0.60:
        return "Moderate agreement"
    elif kappa < 0.80:
        return "Substantial agreement"
    else:
        return "Near-perfect agreement"


# =========================================================================
# 4. PILLAR CORRELATION MATRIX
# =========================================================================

def compute_pillar_correlations(
    judge_scores: dict[str, dict[str, dict[str, float]]],
    nli_scores: dict[str, dict[str, float]],
    coverage_scores: dict[str, dict[str, float]],
) -> dict:
    """
    Compute Spearman rank correlation between all pillars.

    Answers: "Are the three pillars measuring different things?"
    """
    results = {}

    # For each judge, build aligned vectors with NLI and Coverage
    for judge_name, cases in judge_scores.items():
        judge_vals = []
        nli_vals = []
        coverage_vals = []

        for case_name, models in cases.items():
            for model_short, scores in models.items():
                # All loaders now use short model names consistently

                # Find matching NLI and Coverage scores
                nli_case = nli_scores.get(case_name, {})
                cov_case = coverage_scores.get(case_name, {})

                nli_val = nli_case.get(model_short)
                cov_val = cov_case.get(model_short)

                if nli_val is not None and cov_val is not None:
                    judge_vals.append(scores["judge_score"])
                    nli_vals.append(nli_val)
                    coverage_vals.append(cov_val)

        if len(judge_vals) < 3:
            results[judge_name] = {"error": "Too few aligned data points"}
            continue

        # Compute Spearman correlations
        judge_nli_rho, judge_nli_p = stats.spearmanr(judge_vals, nli_vals)
        judge_cov_rho, judge_cov_p = stats.spearmanr(judge_vals, coverage_vals)
        nli_cov_rho, nli_cov_p = stats.spearmanr(nli_vals, coverage_vals)

        results[judge_name] = {
            "n_aligned_observations": len(judge_vals),
            "correlations": {
                f"Judge ({judge_name}) ↔ NLI": {
                    "spearman_rho": round(float(judge_nli_rho), 4),
                    "p_value": round(float(judge_nli_p), 4),
                    "interpretation": _interpret_correlation(judge_nli_rho),
                },
                f"Judge ({judge_name}) ↔ Coverage": {
                    "spearman_rho": round(float(judge_cov_rho), 4),
                    "p_value": round(float(judge_cov_p), 4),
                    "interpretation": _interpret_correlation(judge_cov_rho),
                },
                "NLI ↔ Coverage": {
                    "spearman_rho": round(float(nli_cov_rho), 4),
                    "p_value": round(float(nli_cov_p), 4),
                    "interpretation": _interpret_correlation(nli_cov_rho),
                },
            },
        }

    return results


def _interpret_correlation(rho: float) -> str:
    """Interpret Spearman correlation strength."""
    abs_rho = abs(rho)
    if abs_rho >= 0.7:
        strength = "Strong"
    elif abs_rho >= 0.4:
        strength = "Moderate"
    elif abs_rho >= 0.2:
        strength = "Weak"
    else:
        strength = "Negligible"

    direction = "positive" if rho >= 0 else "negative"
    return f"{strength} {direction} correlation"


# =========================================================================
# REPORT GENERATION
# =========================================================================

def generate_meta_evaluation_report(
    kendall_results: dict,
    distribution_results: dict,
    kappa_results: dict,
    correlation_results: dict,
    output_path: Path,
) -> Path:
    """Generate a markdown report summarizing all meta-evaluation findings."""
    lines = []
    lines.append("# Meta-Evaluation Report: Judge Calibration & Pillar Analysis")
    lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    lines.append("This report evaluates the reliability of the evaluation pipeline itself.")
    lines.append("It answers: **\"How do we know our judges are performing well?\"**\n")

    # ─── Section 1: Kendall's Tau ───
    lines.append("---\n")
    lines.append("## 1. Kendall's Tau (τ) — Rank Correlation Between Judges\n")
    lines.append("Measures whether judges **rank models in the same order**, even if they disagree on absolute scores.\n")
    lines.append("| Judge Pair | Overall τ | p-value | Interpretation | N |")
    lines.append("|---|---|---|---|---|")

    for pair, data in kendall_results.get("pairwise", {}).items():
        tau = data.get("overall_tau", "N/A")
        p = data.get("overall_p_value", "N/A")
        interp = data.get("interpretation", "N/A")
        n = data.get("n_comparisons", 0)
        tau_str = f"{tau:.4f}" if isinstance(tau, (int, float)) else str(tau)
        p_str = f"{p:.4f}" if isinstance(p, (int, float)) else str(p)
        lines.append(f"| {pair} | {tau_str} | {p_str} | {interp} | {n} |")

    lines.append("")

    # ─── Section 2: Score Distributions ───
    lines.append("---\n")
    lines.append("## 2. Score Distribution Analysis\n")
    lines.append("Shows whether judges use the full 1-5 scoring range or cluster around certain values.\n")

    for judge_name, data in distribution_results.items():
        lines.append(f"### {judge_name}\n")
        lines.append(f"- **N evaluations**: {data['n_evaluations']}")

        # Factual accuracy
        acc = data["factual_accuracy"]
        lines.append(f"- **Factual Accuracy**: mean={acc['mean']}, std={acc['std']}, range=[{acc['min']}-{acc['max']}]")
        dist_str = ", ".join(f"{k}→{v}" for k, v in acc["distribution"].items())
        lines.append(f"  - Distribution: {dist_str}")

        # Completeness
        comp = data["completeness"]
        lines.append(f"- **Completeness**: mean={comp['mean']}, std={comp['std']}, range=[{comp['min']}-{comp['max']}]")
        dist_str = ", ".join(f"{k}→{v}" for k, v in comp["distribution"].items())
        lines.append(f"  - Distribution: {dist_str}")

        # Normalized judge score
        js = data["judge_score_normalized"]
        lines.append(f"- **Normalized Judge Score**: mean={js['mean']}, std={js['std']}, range=[{js['min']}-{js['max']}]")

        # Warnings
        if data["warnings"]:
            lines.append("")
            for w in data["warnings"]:
                lines.append(f"> ⚠️ **Warning**: {w}")

        lines.append("")

    # ─── Section 3: Cohen's Kappa ───
    lines.append("---\n")
    lines.append("## 3. Cohen's Kappa — Inter-Judge Agreement\n")
    lines.append("Measures agreement on the 1-5 ordinal scale, adjusted for chance. Uses **quadratic weights** (appropriate for ordinal data).\n")
    lines.append("| Judge Pair | Accuracy κ | Interpretation | Completeness κ | Interpretation | N |")
    lines.append("|---|---|---|---|---|---|")

    for pair, data in kappa_results.items():
        if "error" in data:
            lines.append(f"| {pair} | — | {data['error']} | — | — | — |")
        else:
            lines.append(
                f"| {pair} | {data['factual_accuracy_kappa']:.4f} | "
                f"{data['interpretation_accuracy']} | "
                f"{data['completeness_kappa']:.4f} | "
                f"{data['interpretation_completeness']} | "
                f"{data['n_paired_observations']} |"
            )

    lines.append("")

    # ─── Section 4: Pillar Correlations ───
    lines.append("---\n")
    lines.append("## 4. Pillar Correlation Matrix (Spearman ρ)\n")
    lines.append("Answers: **\"Are the three pillars measuring different things or are they redundant?\"**\n")
    lines.append("Low correlation = pillars capture distinct aspects of quality. High correlation = potential redundancy.\n")

    for judge_name, data in correlation_results.items():
        if "error" in data:
            lines.append(f"### {judge_name}\n{data['error']}\n")
            continue

        lines.append(f"### {judge_name} (N={data['n_aligned_observations']})\n")
        lines.append("| Pillar Pair | Spearman ρ | p-value | Interpretation |")
        lines.append("|---|---|---|---|")

        for pair, corr in data["correlations"].items():
            lines.append(
                f"| {pair} | {corr['spearman_rho']:.4f} | "
                f"{corr['p_value']:.4f} | {corr['interpretation']} |"
            )

        lines.append("")

    # ─── Key Takeaways ───
    lines.append("---\n")
    lines.append("## Key Takeaways\n")
    lines.append("*Interpretation guide:*\n")
    lines.append("- **Kendall's τ**: >0.7 = strong agreement, 0.4-0.7 = moderate, <0.4 = weak")
    lines.append("- **Cohen's κ**: >0.8 = near-perfect, 0.6-0.8 = substantial, 0.4-0.6 = moderate, <0.4 = poor")
    lines.append("- **Spearman ρ**: >0.7 = high redundancy between pillars, <0.3 = pillars measure distinct things")
    lines.append("")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    logger.info(f"Meta-evaluation report saved to: {output_path}")
    return output_path


# =========================================================================
# MAIN ENTRY POINT
# =========================================================================

def run_meta_evaluation(base_dir: Path = None) -> dict:
    """
    Run the full meta-evaluation pipeline.

    Args:
        base_dir: Project root directory. If None, auto-detects.

    Returns:
        Dict with all meta-evaluation results
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent.parent

    output_dir = base_dir / "outputs"
    judge_dir = output_dir / "judge_results"
    nli_dir = output_dir / "nli_results"
    coverage_dir = output_dir / "coverage_results"

    logger.info("=" * 60)
    logger.info("META-EVALUATION: Judge Calibration Analysis")
    logger.info("=" * 60)

    # Load all data
    logger.info("\nLoading judge scores...")
    judge_scores = load_judge_scores(judge_dir)
    logger.info(f"Loaded scores for {len(judge_scores)} judges")

    logger.info("Loading NLI scores...")
    nli_scores = load_nli_scores(nli_dir)
    logger.info(f"Loaded NLI scores for {len(nli_scores)} cases")

    logger.info("Loading coverage scores...")
    coverage_scores = load_coverage_scores(coverage_dir)
    logger.info(f"Loaded coverage scores for {len(coverage_scores)} cases")

    # Run analyses
    logger.info("\n[1/4] Computing Kendall's Tau...")
    kendall_results = compute_kendall_tau(judge_scores)

    logger.info("[2/4] Computing score distributions...")
    distribution_results = compute_score_distributions(judge_scores)

    logger.info("[3/4] Computing Cohen's Kappa...")
    kappa_results = compute_cohens_kappa(judge_scores)

    logger.info("[4/4] Computing pillar correlations...")
    correlation_results = compute_pillar_correlations(
        judge_scores, nli_scores, coverage_scores
    )

    # Generate report
    report_path = generate_meta_evaluation_report(
        kendall_results=kendall_results,
        distribution_results=distribution_results,
        kappa_results=kappa_results,
        correlation_results=correlation_results,
        output_path=output_dir / "meta_evaluation_report.md",
    )

    # Also save raw JSON for programmatic access
    raw_results = {
        "timestamp": datetime.now().isoformat(),
        "kendall_tau": kendall_results,
        "score_distributions": distribution_results,
        "cohens_kappa": kappa_results,
        "pillar_correlations": correlation_results,
    }
    raw_path = output_dir / "meta_evaluation_results.json"
    raw_path.write_text(json.dumps(raw_results, indent=2, default=str), encoding="utf-8")
    logger.info(f"Raw results saved to: {raw_path}")

    logger.info("\n" + "=" * 60)
    logger.info("META-EVALUATION COMPLETE")
    logger.info("=" * 60)

    return raw_results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    run_meta_evaluation()
