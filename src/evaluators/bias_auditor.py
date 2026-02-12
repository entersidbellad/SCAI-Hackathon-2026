"""
Bias Auditor: Length Bias & Self-Consistency Testing

Answers: "Do our judges have systematic biases?"

1. Length Bias — correlates summary word count with judge score
2. Self-Consistency — re-evaluates a subset of summaries to measure test-retest reliability

Length bias uses existing data. Self-consistency requires API calls.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

# Judge model identifiers for OpenRouter
JUDGE_MODELS = {
    "claude-opus-4.5": "anthropic/claude-opus-4.5",
    "gemini-3-flash-preview": "google/gemini-3-flash-preview",
    "minimax-m2.1": "minimax/minimax-m2.1",
}


# =========================================================================
# 1. LENGTH BIAS ANALYSIS
# =========================================================================

def compute_length_bias(
    judge_results_dir: Path,
    summaries_dir: Path,
) -> dict:
    """
    Correlate summary word count with judge scores.

    If |r| > 0.5, the judge is likely biased toward longer/shorter summaries.
    """
    results = {}

    # Build word count lookup: {case_model_key: word_count}
    word_counts = {}
    for f in sorted(summaries_dir.glob("*.txt")):
        stem = f.stem
        parts = stem.rsplit("_", 1)
        if len(parts) == 2:
            key = f"{parts[0]}|{parts[1]}"
            word_counts[key] = len(f.read_text(encoding="utf-8").split())

    for judge_dir in sorted(judge_results_dir.iterdir()):
        if not judge_dir.is_dir():
            continue

        judge_name = judge_dir.name
        scores = []
        lengths = []
        data_points = []

        for json_file in sorted(judge_dir.glob("*_judge.json")):
            data = json.loads(json_file.read_text(encoding="utf-8"))
            stem = json_file.stem.replace("_judge", "")
            parts = stem.rsplit("_", 1)
            if len(parts) != 2:
                continue

            case_name, model_short = parts
            key = f"{case_name}|{model_short}"

            wc = word_counts.get(key)
            if wc is None:
                continue

            js = data.get("judge_score", 0)
            fa = data.get("factual_accuracy", 0)
            comp = data.get("completeness", 0)

            scores.append(js)
            lengths.append(wc)
            data_points.append({
                "case": case_name,
                "model": model_short,
                "word_count": wc,
                "judge_score": js,
                "factual_accuracy": fa,
                "completeness": comp,
            })

        if len(scores) < 5:
            results[judge_name] = {"error": "Too few data points"}
            continue

        scores_arr = np.array(scores)
        lengths_arr = np.array(lengths)

        # Pearson correlation
        pearson_r, pearson_p = stats.pearsonr(lengths_arr, scores_arr)
        # Spearman for robustness
        spearman_rho, spearman_p = stats.spearmanr(lengths_arr, scores_arr)

        # Also check factual_accuracy & completeness separately
        fa_scores = [d["factual_accuracy"] for d in data_points]
        comp_scores = [d["completeness"] for d in data_points]

        fa_r, fa_p = stats.pearsonr(lengths_arr, np.array(fa_scores))
        comp_r, comp_p = stats.pearsonr(lengths_arr, np.array(comp_scores))

        bias_detected = abs(pearson_r) > 0.3

        results[judge_name] = {
            "n_evaluations": len(scores),
            "pearson_r": round(float(pearson_r), 4),
            "pearson_p": round(float(pearson_p), 4),
            "spearman_rho": round(float(spearman_rho), 4),
            "spearman_p": round(float(spearman_p), 4),
            "factual_accuracy_r": round(float(fa_r), 4),
            "completeness_r": round(float(comp_r), 4),
            "summary_lengths": {
                "mean": round(float(lengths_arr.mean()), 1),
                "min": int(lengths_arr.min()),
                "max": int(lengths_arr.max()),
                "std": round(float(lengths_arr.std()), 1),
            },
            "bias_detected": bias_detected,
            "interpretation": _interpret_length_bias(pearson_r),
        }

    return results


def _interpret_length_bias(r: float) -> str:
    abs_r = abs(r)
    direction = "longer" if r > 0 else "shorter"
    if abs_r > 0.5:
        return f"Strong bias toward {direction} summaries (r={r:.3f})"
    elif abs_r > 0.3:
        return f"Moderate bias toward {direction} summaries (r={r:.3f})"
    elif abs_r > 0.1:
        return f"Slight tendency toward {direction} summaries (r={r:.3f}), not significant"
    else:
        return f"No length bias detected (r={r:.3f})"


# =========================================================================
# 2. SELF-CONSISTENCY TEST
# =========================================================================

def run_self_consistency_test(
    judge_results_dir: Path,
    summaries_dir: Path,
    ground_truths_dir: Path,
    output_dir: Path,
    n_samples: int = 5,
) -> dict:
    """
    Re-evaluate a subset of summaries with each judge and compare scores.

    Measures test-retest reliability (same input → same output?).
    """
    from dotenv import load_dotenv
    load_dotenv()

    from src.openrouter_client import OpenRouterClient
    from src.evaluators.judge_evaluator import JudgeEvaluator

    client = OpenRouterClient()
    results = {}

    # Load ground truths
    ground_truths = {}
    for f in sorted(ground_truths_dir.glob("*summary.txt")):
        case_name = f.stem.replace(" summary", "")
        ground_truths[case_name] = f.read_text(encoding="utf-8")

    # Pick sample cases — select those with diverse original scores
    sample_files = _select_diverse_samples(judge_results_dir, n_samples)

    for judge_name, judge_model in JUDGE_MODELS.items():
        judge_dir = judge_results_dir / judge_name
        if not judge_dir.exists():
            continue

        logger.info(f"\n--- Self-consistency test for: {judge_name} ---")
        evaluator = JudgeEvaluator(client, judge_model)

        retest_results = []
        for sample_file in sample_files:
            original_file = judge_dir / sample_file
            if not original_file.exists():
                continue

            # Load original result
            original = json.loads(original_file.read_text(encoding="utf-8"))
            original_score = original.get("judge_score", 0)
            original_fa = original.get("factual_accuracy", 0)
            original_comp = original.get("completeness", 0)

            # Parse case/model from filename
            stem = sample_file.replace("_judge.json", "")
            parts = stem.rsplit("_", 1)
            if len(parts) != 2:
                continue
            case_name, model_short = parts

            # Load ground truth and summary
            gt_text = ground_truths.get(case_name)
            summary_file = summaries_dir / f"{case_name}_{model_short}.txt"

            if gt_text is None or not summary_file.exists():
                logger.warning(f"Skipping {stem}: missing ground truth or summary")
                continue

            summary_text = summary_file.read_text(encoding="utf-8")

            # Re-evaluate
            logger.info(f"  Re-evaluating: {stem}")
            try:
                retest = evaluator.evaluate_summary(
                    ground_truth=gt_text,
                    llm_summary=summary_text,
                    case_name=case_name,
                    summarizer_model=model_short,
                )

                retest_score = retest.get("judge_score", 0)
                retest_fa = retest.get("factual_accuracy", 0)
                retest_comp = retest.get("completeness", 0)

                retest_results.append({
                    "case": case_name,
                    "model": model_short,
                    "original_score": original_score,
                    "retest_score": retest_score,
                    "score_diff": round(abs(retest_score - original_score), 4),
                    "original_fa": original_fa,
                    "retest_fa": retest_fa,
                    "fa_diff": abs(retest_fa - original_fa),
                    "original_comp": original_comp,
                    "retest_comp": retest_comp,
                    "comp_diff": abs(retest_comp - original_comp),
                })

                # Save retest result
                retest_dir = output_dir / "self_consistency" / judge_name
                retest_dir.mkdir(parents=True, exist_ok=True)
                retest_path = retest_dir / f"{stem}_retest.json"
                retest_path.write_text(
                    json.dumps(retest, indent=2, default=str),
                    encoding="utf-8",
                )

                # Rate limit
                time.sleep(2)

            except Exception as e:
                logger.error(f"  Failed to re-evaluate {stem}: {e}")
                continue

        if not retest_results:
            results[judge_name] = {"error": "No successful retests"}
            continue

        # Compute consistency metrics
        score_diffs = [r["score_diff"] for r in retest_results]
        fa_diffs = [r["fa_diff"] for r in retest_results]
        comp_diffs = [r["comp_diff"] for r in retest_results]

        # Exact match rate
        exact_matches = sum(1 for d in score_diffs if d == 0)
        close_matches = sum(1 for d in score_diffs if d <= 0.1)

        results[judge_name] = {
            "n_retests": len(retest_results),
            "mean_score_diff": round(float(np.mean(score_diffs)), 4),
            "max_score_diff": round(float(np.max(score_diffs)), 4),
            "exact_match_rate": round(exact_matches / len(retest_results), 4),
            "close_match_rate": round(close_matches / len(retest_results), 4),
            "mean_fa_diff": round(float(np.mean(fa_diffs)), 4),
            "mean_comp_diff": round(float(np.mean(comp_diffs)), 4),
            "details": retest_results,
            "interpretation": _interpret_consistency(np.mean(score_diffs)),
        }

    return results


def _select_diverse_samples(judge_results_dir: Path, n: int) -> list[str]:
    """Select n diverse sample files for retesting across score range."""
    # Use the first judge directory as reference
    for judge_dir in sorted(judge_results_dir.iterdir()):
        if not judge_dir.is_dir():
            continue

        files_with_scores = []
        for f in sorted(judge_dir.glob("*_judge.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            score = data.get("judge_score", 0)
            files_with_scores.append((f.name, score))

        # Sort by score and pick evenly spaced samples
        files_with_scores.sort(key=lambda x: x[1])
        if len(files_with_scores) <= n:
            return [f[0] for f in files_with_scores]

        indices = np.linspace(0, len(files_with_scores) - 1, n, dtype=int)
        return [files_with_scores[i][0] for i in indices]

    return []


def _interpret_consistency(mean_diff: float) -> str:
    if mean_diff <= 0.05:
        return "Highly consistent (excellent test-retest reliability)"
    elif mean_diff <= 0.1:
        return "Good consistency (acceptable variation)"
    elif mean_diff <= 0.2:
        return "Moderate consistency (some variation, use caution)"
    else:
        return "Poor consistency (unreliable judge)"


# =========================================================================
# REPORT GENERATION
# =========================================================================

def generate_bias_report(
    length_bias: dict,
    consistency: dict,
    output_path: Path,
) -> Path:
    """Generate a markdown report for bias auditing results."""
    lines = []
    lines.append("# Bias Auditing Report: Length Bias & Self-Consistency")
    lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    lines.append("This report checks whether our judges have systematic biases")
    lines.append("that could undermine the evaluation's reliability.\n")

    # ─── Length Bias ───
    lines.append("---\n")
    lines.append("## 1. Length Bias Analysis\n")
    lines.append("Tests whether judges give higher scores to longer summaries (or vice versa).\n")
    lines.append("| Judge | Pearson r | p-value | Spearman ρ | Bias? | Interpretation |")
    lines.append("|---|---|---|---|---|---|")

    for judge, data in length_bias.items():
        if "error" in data:
            lines.append(f"| {judge} | — | — | — | — | {data['error']} |")
            continue

        bias_flag = "⚠️ YES" if data["bias_detected"] else "✅ No"
        lines.append(
            f"| {judge} | {data['pearson_r']:.4f} | {data['pearson_p']:.4f} | "
            f"{data['spearman_rho']:.4f} | {bias_flag} | {data['interpretation']} |"
        )

    lines.append("")

    # Sub-dimension correlations
    lines.append("### Length Correlation by Dimension\n")
    lines.append("| Judge | Length ↔ Factual Accuracy r | Length ↔ Completeness r |")
    lines.append("|---|---|---|")

    for judge, data in length_bias.items():
        if "error" in data:
            continue
        lines.append(
            f"| {judge} | {data['factual_accuracy_r']:.4f} | {data['completeness_r']:.4f} |"
        )

    lines.append("")
    lines.append("> **Note**: A positive correlation with completeness is expected and benign —")
    lines.append("> longer summaries naturally cover more content. A positive correlation with")
    lines.append("> *factual accuracy* would be concerning (length shouldn't affect truthfulness).\n")

    # Summary length stats
    lines.append("### Summary Length Statistics\n")
    lines.append("| Judge | Mean Words | Min | Max | Std |")
    lines.append("|---|---|---|---|---|")

    for judge, data in length_bias.items():
        if "error" in data:
            continue
        sl = data["summary_lengths"]
        lines.append(f"| {judge} | {sl['mean']} | {sl['min']} | {sl['max']} | {sl['std']} |")

    lines.append("")

    # ─── Self-Consistency ───
    lines.append("---\n")
    lines.append("## 2. Self-Consistency (Test-Retest Reliability)\n")
    lines.append("Re-sent the same summaries to each judge and compared scores.\n")

    if consistency:
        lines.append("| Judge | N Retests | Mean Δ Score | Max Δ | Exact Match % | Close Match % (≤0.1) | Interpretation |")
        lines.append("|---|---|---|---|---|---|---|")

        for judge, data in consistency.items():
            if "error" in data:
                lines.append(f"| {judge} | — | — | — | — | — | {data['error']} |")
                continue

            lines.append(
                f"| {judge} | {data['n_retests']} | {data['mean_score_diff']:.4f} | "
                f"{data['max_score_diff']:.4f} | {data['exact_match_rate']*100:.0f}% | "
                f"{data['close_match_rate']*100:.0f}% | {data['interpretation']} |"
            )

        lines.append("")

        # Detail table
        for judge, data in consistency.items():
            if "error" in data or "details" not in data:
                continue

            lines.append(f"### {judge} — Detailed Results\n")
            lines.append("| Case | Model | Original | Retest | Δ Score | Δ FA | Δ Comp |")
            lines.append("|---|---|---|---|---|---|---|")

            for d in data["details"]:
                lines.append(
                    f"| {d['case'][:30]} | {d['model']} | {d['original_score']:.2f} | "
                    f"{d['retest_score']:.2f} | {d['score_diff']:.2f} | "
                    f"{d['fa_diff']} | {d['comp_diff']} |"
                )

            lines.append("")
    else:
        lines.append("*Self-consistency test was not run.*\n")

    # ─── Key Takeaways ───
    lines.append("---\n")
    lines.append("## Key Takeaways\n")
    lines.append("- **Length bias < 0.3**: Judge scores are NOT primarily driven by summary length ✅")
    lines.append("- **Completeness ↔ length** correlation is expected — longer summaries cover more")
    lines.append("- **Factual accuracy ↔ length** correlation should be near zero (truth ≠ length)")
    lines.append("- **Self-consistency**: Mean Δ ≤ 0.1 indicates reliable judges")
    lines.append("")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    logger.info(f"Bias report saved to: {output_path}")
    return output_path


# =========================================================================
# MAIN ENTRY POINT
# =========================================================================

def run_bias_audit(base_dir: Path = None, skip_consistency: bool = False) -> dict:
    """
    Run the full bias auditing pipeline.

    Args:
        base_dir: Project root directory
        skip_consistency: If True, skip self-consistency test (no API calls)
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent.parent

    output_dir = base_dir / "outputs"
    judge_dir = output_dir / "judge_results"
    summaries_dir = output_dir / "llm_summaries"
    gt_dir = base_dir / "oyez-data"

    logger.info("=" * 60)
    logger.info("BIAS AUDITING: Length Bias & Self-Consistency")
    logger.info("=" * 60)

    # Step 1: Length Bias
    logger.info("\n[1/2] Computing length bias...")
    length_bias = compute_length_bias(judge_dir, summaries_dir)

    for judge, data in length_bias.items():
        if "error" not in data:
            logger.info(f"  {judge}: r={data['pearson_r']:.4f} — {data['interpretation']}")

    # Step 2: Self-Consistency
    consistency_results = {}
    if not skip_consistency:
        logger.info("\n[2/2] Running self-consistency test (API calls)...")
        consistency_results = run_self_consistency_test(
            judge_results_dir=judge_dir,
            summaries_dir=summaries_dir,
            ground_truths_dir=gt_dir,
            output_dir=output_dir,
            n_samples=5,
        )
    else:
        logger.info("\n[2/2] Skipping self-consistency test (--skip-consistency)")

    # Generate report
    report_path = generate_bias_report(
        length_bias=length_bias,
        consistency=consistency_results,
        output_path=output_dir / "bias_audit_report.md",
    )

    # Save raw JSON
    raw_results = {
        "timestamp": datetime.now().isoformat(),
        "length_bias": length_bias,
        "self_consistency": consistency_results,
    }
    raw_path = output_dir / "bias_audit_results.json"
    raw_path.write_text(json.dumps(raw_results, indent=2, default=str), encoding="utf-8")
    logger.info(f"Raw results saved to: {raw_path}")

    logger.info("\n" + "=" * 60)
    logger.info("BIAS AUDITING COMPLETE")
    logger.info("=" * 60)

    return raw_results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    skip = "--skip-consistency" in sys.argv
    run_bias_audit(skip_consistency=skip)
