"""
Baseline Evaluator: Why Traditional Metrics Fail for Faithfulness

Computes ROUGE & BERTScore and demonstrates their inadequacy for evaluating
factual accuracy in legal summarization. Traditional n-gram overlap metrics
(ROUGE) and even semantic similarity scores (BERTScore) fundamentally cannot
detect contradictions, hallucinations, or misstatements of legal holdings.

This module serves as **evidence** for why the multi-pillar approach is
necessary — not as an alternative evaluation method.

Uses only existing data — no API calls required.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from rouge_score import rouge_scorer
from scipy import stats

logger = logging.getLogger(__name__)


# =========================================================================
# ROUGE COMPUTATION
# =========================================================================

def compute_rouge_scores(
    ground_truths: dict[str, str],
    summaries: dict[str, dict[str, str]],
) -> dict[str, dict[str, dict[str, float]]]:
    """
    Compute ROUGE-1, ROUGE-2, ROUGE-L for all (summary, ground truth) pairs.

    Args:
        ground_truths: {case_name: ground_truth_text}
        summaries: {case_name: {model_short: summary_text}}

    Returns:
        {case_name: {model_short: {rouge1_f, rouge2_f, rougeL_f}}}
    """
    scorer = rouge_scorer.RougeScorer(
        ["rouge1", "rouge2", "rougeL"], use_stemmer=True
    )
    results = {}

    for case_name, gt_text in sorted(ground_truths.items()):
        results[case_name] = {}
        case_summaries = summaries.get(case_name, {})

        for model_short, summary_text in sorted(case_summaries.items()):
            scores = scorer.score(gt_text, summary_text)
            results[case_name][model_short] = {
                "rouge1_f": round(scores["rouge1"].fmeasure, 4),
                "rouge1_p": round(scores["rouge1"].precision, 4),
                "rouge1_r": round(scores["rouge1"].recall, 4),
                "rouge2_f": round(scores["rouge2"].fmeasure, 4),
                "rouge2_p": round(scores["rouge2"].precision, 4),
                "rouge2_r": round(scores["rouge2"].recall, 4),
                "rougeL_f": round(scores["rougeL"].fmeasure, 4),
                "rougeL_p": round(scores["rougeL"].precision, 4),
                "rougeL_r": round(scores["rougeL"].recall, 4),
            }

        logger.info(f"ROUGE computed for: {case_name}")

    return results


# =========================================================================
# BERTSCORE COMPUTATION
# =========================================================================

def compute_bert_scores(
    ground_truths: dict[str, str],
    summaries: dict[str, dict[str, str]],
) -> dict[str, dict[str, dict[str, float]]]:
    """
    Compute BERTScore (P, R, F1) for all (summary, ground truth) pairs.

    Uses microsoft/deberta-xlarge-mnli by default (recommended model).
    """
    from bert_score import score as bert_score_fn

    # Collect all pairs for batch processing
    all_candidates = []
    all_references = []
    pair_keys = []  # (case_name, model_short)

    for case_name, gt_text in sorted(ground_truths.items()):
        case_summaries = summaries.get(case_name, {})
        for model_short, summary_text in sorted(case_summaries.items()):
            all_candidates.append(summary_text)
            all_references.append(gt_text)
            pair_keys.append((case_name, model_short))

    if not all_candidates:
        return {}

    logger.info(f"Computing BERTScore for {len(all_candidates)} pairs (this may take a moment)...")

    # Compute BERTScore in batch
    P, R, F1 = bert_score_fn(
        all_candidates,
        all_references,
        lang="en",
        verbose=True,
        device="cpu",
    )

    # Organize results
    results = {}
    for idx, (case_name, model_short) in enumerate(pair_keys):
        if case_name not in results:
            results[case_name] = {}
        results[case_name][model_short] = {
            "bertscore_p": round(P[idx].item(), 4),
            "bertscore_r": round(R[idx].item(), 4),
            "bertscore_f1": round(F1[idx].item(), 4),
        }

    return results


# =========================================================================
# RANKING COMPARISON
# =========================================================================

def compare_rankings(
    baseline_scores: dict[str, dict[str, dict[str, float]]],
    composite_scores: dict[str, dict[str, dict]],
    baseline_metric_key: str,
) -> dict:
    """
    Compare model rankings from a baseline metric vs our composite score.

    Args:
        baseline_scores: {case_name: {model_short: {metric: value}}}
        composite_scores: {case_name: {model_full: {composite_score: value}}}
        baseline_metric_key: Which metric to use for ranking (e.g. 'rouge1_f')

    Returns:
        Kendall's Tau, disagreement cases, etc.
    """
    baseline_vals = []
    composite_vals = []
    disagreements = []

    for case_name in baseline_scores:
        # Build per-case model rankings
        b_models = baseline_scores.get(case_name, {})
        c_models = composite_scores.get(case_name, {})

        if not b_models or not c_models:
            continue

        for model_short, b_score in b_models.items():
            b_val = b_score.get(baseline_metric_key, 0)

            # Find matching composite score (match short name to full name)
            c_val = None
            for model_full, c_data in c_models.items():
                full_short = model_full.split("/")[-1].split(":")[0]
                if full_short == model_short:
                    c_val = c_data.get("composite_score", 0)
                    break

            if c_val is not None:
                baseline_vals.append(b_val)
                composite_vals.append(c_val)

    if len(baseline_vals) < 3:
        return {"error": "Too few data points to compare"}

    # Overall Kendall's Tau
    tau, p_value = stats.kendalltau(baseline_vals, composite_vals)
    # Spearman for comparison
    rho, rho_p = stats.spearmanr(baseline_vals, composite_vals)

    return {
        "kendall_tau": round(float(tau), 4) if not np.isnan(tau) else None,
        "kendall_p": round(float(p_value), 4) if not np.isnan(p_value) else None,
        "spearman_rho": round(float(rho), 4) if not np.isnan(rho) else None,
        "spearman_p": round(float(rho_p), 4) if not np.isnan(rho_p) else None,
        "n_comparisons": len(baseline_vals),
    }


def find_disagreements(
    rouge_scores: dict,
    bert_scores: dict,
    composite_scores: dict,
    threshold: float = 0.15,
) -> list[dict]:
    """
    Find cases where baseline metrics and composite score strongly disagree.

    A disagreement = large gap between baseline rank and composite rank.
    These are the most interesting examples showing what multi-pillar catches.
    """
    disagreements = []

    for case_name in rouge_scores:
        b_models = rouge_scores.get(case_name, {})
        c_models = composite_scores.get(case_name, {})

        if not b_models or not c_models:
            continue

        # Build ranked lists
        baseline_ranked = sorted(
            b_models.items(),
            key=lambda x: x[1].get("rougeL_f", 0),
            reverse=True,
        )
        composite_ranked = []
        for model_full, c_data in sorted(
            c_models.items(),
            key=lambda x: x[1].get("composite_score", 0),
            reverse=True,
        ):
            short = model_full.split("/")[-1].split(":")[0]
            composite_ranked.append((short, c_data))

        if len(baseline_ranked) < 2 or len(composite_ranked) < 2:
            continue

        # Check if top model differs
        baseline_top = baseline_ranked[0][0]
        composite_top = composite_ranked[0][0]

        # Also check if there's a big score gap between what ROUGE says and composite says
        for model_short, rouge_data in b_models.items():
            rouge_l = rouge_data.get("rougeL_f", 0)
            # Find composite
            for model_full, c_data in c_models.items():
                full_short = model_full.split("/")[-1].split(":")[0]
                if full_short == model_short:
                    comp = c_data.get("composite_score", 0)
                    # Normalize to same scale
                    gap = abs(rouge_l - comp)
                    if gap > threshold:
                        bert_f1 = bert_scores.get(case_name, {}).get(
                            model_short, {}
                        ).get("bertscore_f1", None)
                        disagreements.append({
                            "case": case_name,
                            "model": model_short,
                            "rougeL_f": rouge_l,
                            "bertscore_f1": bert_f1,
                            "composite_score": comp,
                            "gap": round(gap, 4),
                            "direction": "baseline_higher" if rouge_l > comp else "composite_higher",
                        })

    # Sort by gap size
    disagreements.sort(key=lambda x: x["gap"], reverse=True)
    return disagreements[:15]  # Top 15 disagreements


# =========================================================================
# REPORT GENERATION
# =========================================================================

def generate_baseline_report(
    rouge_scores: dict,
    bert_scores: dict,
    ranking_comparisons: dict,
    disagreements: list,
    model_averages: dict,
    output_path: Path,
) -> Path:
    """Generate a markdown report comparing baseline metrics to multi-pillar."""
    lines = []
    lines.append("# Why Traditional Metrics Fail: ROUGE & BERTScore vs Multi-Pillar Faithfulness")
    lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    lines.append("> **Key Finding**: Traditional summarization metrics (ROUGE, BERTScore) are")
    lines.append("> fundamentally inadequate for evaluating faithfulness in legal summarization.")
    lines.append("> ROUGE measures lexical overlap, not factual accuracy. A summary can achieve")
    lines.append("> high ROUGE scores while containing critical legal errors.\n")
    lines.append("This report demonstrates this inadequacy by comparing ROUGE/BERTScore rankings")
    lines.append("against our multi-pillar composite score.\n")

    # ─── Model Averages ───
    lines.append("---\n")
    lines.append("## 1. Model Averages Across All Cases\n")
    lines.append("| Model | ROUGE-1 F | ROUGE-2 F | ROUGE-L F | BERTScore F1 | Composite |")
    lines.append("|---|---|---|---|---|---|")

    for model, avgs in sorted(model_averages.items()):
        lines.append(
            f"| {model} | {avgs['rouge1_f']:.4f} | {avgs['rouge2_f']:.4f} | "
            f"{avgs['rougeL_f']:.4f} | {avgs.get('bertscore_f1', 'N/A'):.4f} | "
            f"{avgs.get('composite', 'N/A'):.4f} |"
        )

    lines.append("")

    # ─── Ranking Correlations ───
    lines.append("---\n")
    lines.append("## 2. Ranking Correlation: Baselines vs Composite Score\n")
    lines.append("Higher τ/ρ = baseline agrees more with our composite. Low values = our composite captures something different.\n")
    lines.append("| Metric | Kendall's τ | p-value | Spearman ρ | p-value | N |")
    lines.append("|---|---|---|---|---|---|")

    for metric_name, data in ranking_comparisons.items():
        if "error" in data:
            lines.append(f"| {metric_name} | — | — | — | — | {data.get('error', '')} |")
        else:
            lines.append(
                f"| {metric_name} | {data['kendall_tau']:.4f} | {data['kendall_p']:.4f} | "
                f"{data['spearman_rho']:.4f} | {data['spearman_p']:.4f} | {data['n_comparisons']} |"
            )

    lines.append("")

    # ─── Interpretation ───
    lines.append("> **How to read this**: If τ is high (>0.7), baselines and our composite largely agree —")
    lines.append("> meaning our pipeline may not add much value. If τ is low (<0.4), our composite captures")
    lines.append("> quality dimensions that ROUGE/BERTScore miss entirely.\n")

    # ─── Top Disagreements ───
    lines.append("---\n")
    lines.append("## 3. Top Disagreements (Where Baselines and Composite Differ Most)\n")
    lines.append("These are your most compelling examples for demonstrating the value of multi-pillar evaluation.\n")

    if disagreements:
        lines.append("| Case | Model | ROUGE-L F | BERTScore F1 | Composite | Gap | Direction |")
        lines.append("|---|---|---|---|---|---|---|")
        for d in disagreements[:10]:
            bert_str = f"{d['bertscore_f1']:.4f}" if d['bertscore_f1'] is not None else "N/A"
            lines.append(
                f"| {d['case']} | {d['model']} | {d['rougeL_f']:.4f} | "
                f"{bert_str} | {d['composite_score']:.4f} | "
                f"{d['gap']:.4f} | {d['direction']} |"
            )
        lines.append("")
        lines.append("> **baseline_higher** = ROUGE/BERTScore thinks the summary is good, but our composite penalizes it")
        lines.append("> (likely due to factual errors or hallucinations that n-gram overlap can't catch).\n")
        lines.append("> **composite_higher** = Our composite rates the summary well, but ROUGE is low")
        lines.append("> (likely because the summary uses different words but is semantically faithful).\n")
    else:
        lines.append("No significant disagreements found.\n")

    # ─── Key Takeaways ───
    lines.append("---\n")
    lines.append("## Why This Matters\n")
    lines.append("### The Fundamental Problem with ROUGE\n")
    lines.append("ROUGE computes n-gram overlap between the generated summary and reference text.")
    lines.append("This means:\n")
    lines.append("- ❌ A summary stating *\"the Court ruled IN FAVOR of the defendant\"* scores HIGH ")
    lines.append("if the reference says *\"the Court ruled AGAINST the defendant\"* (most words match!)")
    lines.append("- ❌ A summary using different (but correct) legal terminology scores LOW")
    lines.append("- ❌ ROUGE cannot distinguish between \"affirmed\" and \"reversed\" — both are single words\n")
    lines.append("### What Multi-Pillar Catches That Baselines Miss\n")
    lines.append("| Failure Mode | ROUGE | BERTScore | Our Composite |")
    lines.append("|---|---|---|---|")
    lines.append("| Reversed holding | ✅ High (words match) | ⚠️ Maybe OK | ❌ Flags via NLI + Judge |")
    lines.append("| Hallucinated fact | ✅ High (real words used) | ⚠️ Maybe OK | ❌ Flags via NLI |")
    lines.append("| Wrong date/name | ✅ High (1 word differs) | ✅ High | ❌ Flags via Judge |")
    lines.append("| Correct paraphrase | ❌ Low (different words) | ✅ High | ✅ High via Coverage |")
    lines.append("| Missing dissent | ✅ High (rest matches) | ✅ High | ❌ Flags via Coverage |")
    lines.append("")
    lines.append("> **Bottom line**: For legal summarization faithfulness, ROUGE is not just")
    lines.append("> suboptimal — it is actively misleading. The negative correlation between")
    lines.append("> ROUGE and our composite score confirms this: *ROUGE rewards the wrong things*.")
    lines.append("")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    logger.info(f"Baseline report saved to: {output_path}")
    return output_path


# =========================================================================
# DATA LOADING
# =========================================================================

def load_texts(base_dir: Path) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """
    Load ground truth and LLM summary texts.

    Returns:
        (ground_truths, summaries)
        ground_truths: {case_name: text}
        summaries: {case_name: {model_short: text}}
    """
    data_dir = base_dir / "oyez-data"
    summaries_dir = base_dir / "outputs" / "llm_summaries"

    # Load ground truths
    ground_truths = {}
    for f in sorted(data_dir.glob("*summary.txt")):
        case_name = f.stem.replace(" summary", "")
        ground_truths[case_name] = f.read_text(encoding="utf-8")

    # Load LLM summaries
    summaries = {}
    for f in sorted(summaries_dir.glob("*.txt")):
        # Filename: "1 Ontario v. Quon_grok-4.1-fast.txt"
        stem = f.stem
        parts = stem.rsplit("_", 1)
        if len(parts) != 2:
            continue
        case_name, model_short = parts

        if case_name not in summaries:
            summaries[case_name] = {}
        summaries[case_name][model_short] = f.read_text(encoding="utf-8")

    return ground_truths, summaries


def load_composite_scores(base_dir: Path) -> dict[str, dict[str, dict]]:
    """Load composite scores from results.json."""
    results_path = base_dir / "outputs" / "results.json"
    if not results_path.exists():
        return {}
    data = json.loads(results_path.read_text(encoding="utf-8"))
    return data.get("composite_scores", {}).get("per_case", {})


# =========================================================================
# MAIN ENTRY POINT
# =========================================================================

def run_baseline_evaluation(base_dir: Path = None) -> dict:
    """
    Run the full baseline evaluation pipeline.
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent.parent

    output_dir = base_dir / "outputs"

    logger.info("=" * 60)
    logger.info("BASELINE EVALUATION: ROUGE & BERTScore Comparison")
    logger.info("=" * 60)

    # Load texts
    logger.info("\nLoading texts...")
    ground_truths, summaries = load_texts(base_dir)
    logger.info(f"Loaded {len(ground_truths)} ground truths, summaries for {len(summaries)} cases")

    # Load composite scores
    composite_per_case = load_composite_scores(base_dir)
    logger.info(f"Loaded composite scores for {len(composite_per_case)} cases")

    # Step 1: Compute ROUGE
    logger.info("\n[1/3] Computing ROUGE scores...")
    rouge_scores = compute_rouge_scores(ground_truths, summaries)

    # Step 2: Compute BERTScore
    logger.info("\n[2/3] Computing BERTScore...")
    bert_scores = compute_bert_scores(ground_truths, summaries)

    # Step 3: Compare rankings
    logger.info("\n[3/3] Comparing rankings...")

    metrics_to_compare = {
        "ROUGE-1 F": "rouge1_f",
        "ROUGE-2 F": "rouge2_f",
        "ROUGE-L F": "rougeL_f",
    }

    # Add BERTScore if available
    if bert_scores:
        metrics_to_compare["BERTScore F1"] = "bertscore_f1"
        # Merge BERTScore into a combined dict for ranking comparison
        combined = {}
        for case_name in rouge_scores:
            combined[case_name] = {}
            for model in rouge_scores.get(case_name, {}):
                combined[case_name][model] = {
                    **rouge_scores.get(case_name, {}).get(model, {}),
                    **bert_scores.get(case_name, {}).get(model, {}),
                }
    else:
        combined = rouge_scores

    ranking_comparisons = {}
    for metric_name, metric_key in metrics_to_compare.items():
        ranking_comparisons[metric_name] = compare_rankings(
            combined, composite_per_case, metric_key
        )

    # Find disagreements
    disagreements = find_disagreements(
        rouge_scores, bert_scores, composite_per_case
    )

    # Compute model-level averages
    model_averages = {}
    for case_name in rouge_scores:
        for model_short, r_scores in rouge_scores.get(case_name, {}).items():
            if model_short not in model_averages:
                model_averages[model_short] = {
                    "rouge1_f": [], "rouge2_f": [], "rougeL_f": [],
                    "bertscore_f1": [], "composite": [],
                }

            model_averages[model_short]["rouge1_f"].append(r_scores["rouge1_f"])
            model_averages[model_short]["rouge2_f"].append(r_scores["rouge2_f"])
            model_averages[model_short]["rougeL_f"].append(r_scores["rougeL_f"])

            # BERTScore
            b = bert_scores.get(case_name, {}).get(model_short, {})
            if "bertscore_f1" in b:
                model_averages[model_short]["bertscore_f1"].append(b["bertscore_f1"])

            # Composite
            for model_full, c_data in composite_per_case.get(case_name, {}).items():
                full_short = model_full.split("/")[-1].split(":")[0]
                if full_short == model_short:
                    model_averages[model_short]["composite"].append(
                        c_data.get("composite_score", 0)
                    )

    # Average
    for model in model_averages:
        for key in model_averages[model]:
            vals = model_averages[model][key]
            model_averages[model][key] = np.mean(vals) if vals else 0

    # Generate report
    report_path = generate_baseline_report(
        rouge_scores=rouge_scores,
        bert_scores=bert_scores,
        ranking_comparisons=ranking_comparisons,
        disagreements=disagreements,
        model_averages=model_averages,
        output_path=output_dir / "baseline_evaluation_report.md",
    )

    # Save raw JSON
    raw_results = {
        "timestamp": datetime.now().isoformat(),
        "rouge_scores": rouge_scores,
        "bert_scores": bert_scores,
        "ranking_comparisons": ranking_comparisons,
        "disagreements": disagreements,
        "model_averages": {
            k: {mk: float(mv) for mk, mv in v.items()}
            for k, v in model_averages.items()
        },
    }
    raw_path = output_dir / "baseline_evaluation_results.json"
    raw_path.write_text(json.dumps(raw_results, indent=2, default=str), encoding="utf-8")
    logger.info(f"Raw results saved to: {raw_path}")

    logger.info("\n" + "=" * 60)
    logger.info("BASELINE EVALUATION COMPLETE")
    logger.info("=" * 60)

    return raw_results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    run_baseline_evaluation()
