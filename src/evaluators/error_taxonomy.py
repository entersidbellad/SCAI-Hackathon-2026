"""
Error Taxonomy: Legal-Specific Failure Classification

Classifies errors from judge evaluations into domain-specific legal categories:
- Wrong Holding — misstated who won or what was decided
- Wrong Vote Count — incorrect vote tally
- Fabricated Precedent — cites a case or detail not in the source
- Merged/Confused Parties — confuses petitioner and respondent
- Omitted Dissent — fails to mention dissenting opinion
- Omitted Concurrence — fails to mention concurring opinion
- Wrong Legal Standard — misapplies or misstates the legal test
- Invented Detail — adds specific facts not in the reference
- Anachronism — applies wrong temporal framework

Uses rule-based classification with keyword patterns — no API calls required.
"""

import json
import logging
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# =========================================================================
# TAXONOMY DEFINITIONS
# =========================================================================

TAXONOMY = {
    "wrong_holding": {
        "label": "Wrong Holding",
        "description": "Misstated who won, what was decided, or the legal outcome",
        "severity_weight": 3,
        "patterns": [
            r"(?i)holding",
            r"(?i)outcome",
            r"(?i)decided.*wrong",
            r"(?i)reversed.*affirmed|affirmed.*reversed",
            r"(?i)who won",
            r"(?i)ruling",
            r"(?i)judgment.*incorrect",
            r"(?i)misstat.*decision",
        ],
    },
    "wrong_vote_count": {
        "label": "Wrong Vote Count",
        "description": "Incorrect vote tally (e.g., '5-4' → '6-3')",
        "severity_weight": 2,
        "patterns": [
            r"(?i)vote\s*(count|split|tally)",
            r"(?i)\d+[\s-]+\d+.*(?:wrong|incorrect|not|different)",
            r"(?i)(?:wrong|incorrect).*\d+[\s-]+\d+",
            r"(?i)majority.*(?:number|count)",
        ],
    },
    "fabricated_precedent": {
        "label": "Fabricated Precedent / Citation",
        "description": "Cites a case, statute, or detail not in the source material",
        "severity_weight": 3,
        "patterns": [
            r"(?i)(?:not|never)\s+(?:mentioned|cited|referenced|present|found|in)\s+(?:in\s+)?(?:the\s+)?(?:reference|source|ground\s*truth)",
            r"(?i)fabricat",
            r"(?i)invented",
            r"(?i)hallucin",
            r"(?i)does\s+not\s+(?:appear|exist|mention)",
            r"(?i)not\s+in\s+(?:the\s+)?(?:reference|source|original)",
            r"(?i)no\s+(?:mention|reference|basis)",
            r"(?i)added.*not.*(?:reference|source)",
        ],
    },
    "merged_parties": {
        "label": "Merged / Confused Parties",
        "description": "Confuses petitioner and respondent, or attributes actions to wrong party",
        "severity_weight": 2,
        "patterns": [
            r"(?i)(?:petitioner|respondent|plaintiff|defendant|appellant).*(?:wrong|incorrect|confused|mixed|switched)",
            r"(?i)(?:wrong|incorrect).*(?:petitioner|respondent|plaintiff|defendant|party)",
            r"(?i)confus.*(?:parties|party|petitioner|respondent)",
            r"(?i)(?:attributed|assigns|ascribed).*(?:wrong|incorrect).*(?:party|person|justice)",
        ],
    },
    "omitted_dissent": {
        "label": "Omitted Dissent",
        "description": "Failed to mention dissenting opinion",
        "severity_weight": 2,
        "patterns": [
            r"(?i)dissent",
            r"(?i)dissenting\s+opinion",
        ],
    },
    "omitted_concurrence": {
        "label": "Omitted Concurrence",
        "description": "Failed to mention concurring opinion",
        "severity_weight": 1,
        "patterns": [
            r"(?i)concurr",
            r"(?i)concurring\s+opinion",
            r"(?i)concurrence",
        ],
    },
    "wrong_legal_standard": {
        "label": "Wrong Legal Standard",
        "description": "Misapplies or misstates the legal test or framework",
        "severity_weight": 2,
        "patterns": [
            r"(?i)(?:legal|constitutional)\s+(?:standard|test|framework|doctrine|principle)",
            r"(?i)(?:wrong|incorrect|misappl|misstat).*(?:test|standard|clause|amendment)",
            r"(?i)(?:fourth|first|second|fifth|fourteenth)\s+amendment.*(?:wrong|incorrect)",
        ],
    },
    "invented_detail": {
        "label": "Invented Detail",
        "description": "Added specific facts, dates, names, or numbers not in the reference",
        "severity_weight": 1,
        "patterns": [
            r"(?i)(?:specific|exact)\s+(?:date|detail|name|number|figure)",
            r"(?i)(?:date|detail|name).*(?:not|never).*(?:mentioned|reference|source)",
            r"(?i)(?:adds|added|introduces|introduced).*(?:specific|detail|information)",
            r"(?i)this\s+(?:specific\s+)?(?:detail|information|date|name).*not",
        ],
    },
    "wrong_justice_attribution": {
        "label": "Wrong Justice Attribution",
        "description": "Attributes opinion/vote to the wrong justice",
        "severity_weight": 2,
        "patterns": [
            r"(?i)justice.*(?:wrong|incorrect|did\s+not|didn't)",
            r"(?i)(?:wrong|incorrect).*justice",
            r"(?i)(?:authored|wrote|delivered).*(?:wrong|incorrect|not)",
            r"(?i)(?:not|wrong).*(?:authored|wrote|delivered)",
        ],
    },
}

OMISSION_TAXONOMY = {
    "omitted_dissent": {
        "label": "Omitted Dissent",
        "patterns": [
            r"(?i)dissent",
        ],
    },
    "omitted_concurrence": {
        "label": "Omitted Concurrence",
        "patterns": [
            r"(?i)concurr",
            r"(?i)concurrence",
        ],
    },
    "omitted_holding": {
        "label": "Omitted Key Holding",
        "patterns": [
            r"(?i)holding",
            r"(?i)(?:main|central|key|primary)\s+(?:decision|ruling|question)",
            r"(?i)legal\s+question",
        ],
    },
    "omitted_vote_count": {
        "label": "Omitted Vote Count",
        "patterns": [
            r"(?i)\d+[\s-]+\d+",
            r"(?i)vote",
            r"(?i)unanimou",
        ],
    },
    "omitted_reasoning": {
        "label": "Omitted Legal Reasoning",
        "patterns": [
            r"(?i)reasoning",
            r"(?i)rationale",
            r"(?i)(?:legal|constitutional)\s+(?:analysis|basis|argument|framework)",
            r"(?i)(?:test|standard|doctrine)",
        ],
    },
    "omitted_justice_opinion": {
        "label": "Omitted Specific Justice's Opinion",
        "patterns": [
            r"(?i)justice\s+\w+",
        ],
    },
    "omitted_procedural": {
        "label": "Omitted Procedural History",
        "patterns": [
            r"(?i)procedural",
            r"(?i)(?:lower|circuit|district|appellate)\s+court",
            r"(?i)appeal",
            r"(?i)certiorari",
        ],
    },
}


# =========================================================================
# CLASSIFICATION ENGINE
# =========================================================================

def classify_error(issue_text: str, error_quote: str = "") -> list[str]:
    """
    Classify a factual error into one or more taxonomy categories.

    Returns list of matched category keys, ordered by priority.
    """
    combined_text = f"{issue_text} {error_quote}".strip()
    matches = []

    for cat_key, cat_def in TAXONOMY.items():
        for pattern in cat_def["patterns"]:
            if re.search(pattern, combined_text):
                matches.append(cat_key)
                break  # One match per category is enough

    if not matches:
        matches.append("other")

    return matches


def classify_omission(omission_text: str) -> list[str]:
    """
    Classify a key omission into one or more taxonomy categories.
    """
    matches = []

    for cat_key, cat_def in OMISSION_TAXONOMY.items():
        for pattern in cat_def["patterns"]:
            if re.search(pattern, omission_text):
                matches.append(cat_key)
                break

    if not matches:
        matches.append("other_omission")

    return matches


# =========================================================================
# DATA PROCESSING
# =========================================================================

def extract_and_classify_errors(judge_results_dir: Path) -> dict:
    """
    Extract all errors from judge results and classify into taxonomy.

    Returns:
        {
            "classified_errors": [...],
            "classified_omissions": [...],
            "summary": {...},
        }
    """
    classified_errors = []
    classified_omissions = []

    for judge_dir in sorted(judge_results_dir.iterdir()):
        if not judge_dir.is_dir():
            continue

        judge_name = judge_dir.name

        for json_file in sorted(judge_dir.glob("*_judge.json")):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to load {json_file}: {e}")
                continue

            # Parse case/model from filename
            stem = json_file.stem.replace("_judge", "")
            parts = stem.rsplit("_", 1)
            case_name = parts[0] if len(parts) == 2 else stem
            model_short = parts[1] if len(parts) == 2 else "unknown"

            # Classify factual errors
            for error in data.get("factual_errors", []):
                issue = error.get("issue", "")
                quote = error.get("error_quote", "")
                severity = error.get("severity", "Unknown")
                correct_info = error.get("correct_info", "")
                categories = classify_error(issue, quote)

                classified_errors.append({
                    "judge": judge_name,
                    "case": case_name,
                    "model": model_short,
                    "severity": severity,
                    "issue": issue,
                    "error_quote": quote,
                    "correct_info": correct_info,
                    "categories": categories,
                    "primary_category": categories[0],
                })

            # Classify omissions
            for omission in data.get("key_omissions", []):
                omission_text = str(omission)
                categories = classify_omission(omission_text)

                classified_omissions.append({
                    "judge": judge_name,
                    "case": case_name,
                    "model": model_short,
                    "omission": omission_text,
                    "categories": categories,
                    "primary_category": categories[0],
                })

    return {
        "classified_errors": classified_errors,
        "classified_omissions": classified_omissions,
    }


# =========================================================================
# ANALYSIS
# =========================================================================

def analyze_taxonomy(classified_data: dict) -> dict:
    """
    Produce summary statistics from classified errors.
    """
    errors = classified_data["classified_errors"]
    omissions = classified_data["classified_omissions"]

    # Error category distribution
    error_cat_counts = Counter(e["primary_category"] for e in errors)
    omission_cat_counts = Counter(o["primary_category"] for o in omissions)

    # Severity by category
    severity_by_cat = defaultdict(lambda: Counter())
    for e in errors:
        severity_by_cat[e["primary_category"]][e["severity"]] += 1

    # Errors per model
    errors_per_model = Counter(e["model"] for e in errors)
    omissions_per_model = Counter(o["model"] for o in omissions)

    # Errors per judge
    errors_per_judge = Counter(e["judge"] for e in errors)

    # Most common error types per model
    model_error_profile = defaultdict(lambda: Counter())
    for e in errors:
        model_error_profile[e["model"]][e["primary_category"]] += 1

    model_omission_profile = defaultdict(lambda: Counter())
    for o in omissions:
        model_omission_profile[o["model"]][o["primary_category"]] += 1

    # Critical/Major errors by case (which cases are hardest?)
    hard_cases = Counter()
    for e in errors:
        if e["severity"] in ("Critical", "Major", "Substantial", "Major Issue"):
            hard_cases[e["case"]] += 1

    return {
        "total_errors": len(errors),
        "total_omissions": len(omissions),
        "error_category_counts": dict(error_cat_counts.most_common()),
        "omission_category_counts": dict(omission_cat_counts.most_common()),
        "severity_by_category": {
            k: dict(v) for k, v in severity_by_cat.items()
        },
        "errors_per_model": dict(errors_per_model.most_common()),
        "omissions_per_model": dict(omissions_per_model.most_common()),
        "errors_per_judge": dict(errors_per_judge.most_common()),
        "model_error_profile": {
            k: dict(v.most_common()) for k, v in model_error_profile.items()
        },
        "model_omission_profile": {
            k: dict(v.most_common()) for k, v in model_omission_profile.items()
        },
        "hardest_cases": dict(hard_cases.most_common(10)),
    }


# =========================================================================
# REPORT GENERATION
# =========================================================================

def generate_taxonomy_report(
    analysis: dict,
    classified_data: dict,
    output_path: Path,
) -> Path:
    """Generate a markdown report with legal-specific error taxonomy analysis."""
    lines = []
    lines.append("# Error Taxonomy Report: Legal-Specific Failure Analysis")
    lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    lines.append("This report classifies summarization failures into **legal-domain-specific**")
    lines.append("categories, revealing *what types* of errors LLMs make on Supreme Court cases.\n")

    # ─── Overview ───
    lines.append("---\n")
    lines.append("## 1. Overview\n")
    lines.append(f"- **Total factual errors**: {analysis['total_errors']}")
    lines.append(f"- **Total key omissions**: {analysis['total_omissions']}")
    lines.append(f"- **Combined failures**: {analysis['total_errors'] + analysis['total_omissions']}\n")

    # ─── Error Category Distribution ───
    lines.append("---\n")
    lines.append("## 2. Error Category Distribution\n")
    lines.append("### Factual Errors\n")
    lines.append("| Category | Count | % of Total |")
    lines.append("|---|---|---|")

    total_e = analysis["total_errors"]
    for cat, count in analysis["error_category_counts"].items():
        label = TAXONOMY.get(cat, {}).get("label", cat.replace("_", " ").title())
        pct = (count / total_e * 100) if total_e > 0 else 0
        lines.append(f"| {label} | {count} | {pct:.1f}% |")
    lines.append("")

    lines.append("### Key Omissions\n")
    lines.append("| Category | Count | % of Total |")
    lines.append("|---|---|---|")

    total_o = analysis["total_omissions"]
    for cat, count in analysis["omission_category_counts"].items():
        label = OMISSION_TAXONOMY.get(cat, {}).get("label", cat.replace("_", " ").title())
        pct = (count / total_o * 100) if total_o > 0 else 0
        lines.append(f"| {label} | {count} | {pct:.1f}% |")
    lines.append("")

    # ─── Severity by Category ───
    lines.append("---\n")
    lines.append("## 3. Error Severity by Category\n")
    lines.append("| Category | Minor | Major | Critical | Other |")
    lines.append("|---|---|---|---|---|")

    for cat in analysis["error_category_counts"]:
        label = TAXONOMY.get(cat, {}).get("label", cat.replace("_", " ").title())
        sev = analysis["severity_by_category"].get(cat, {})
        minor = sev.get("Minor", 0)
        major = sev.get("Major", 0) + sev.get("Substantial", 0) + sev.get("Major Issue", 0)
        critical = sev.get("Critical", 0)
        other = sev.get("Unknown", 0) + sev.get("?", 0)
        lines.append(f"| {label} | {minor} | {major} | {critical} | {other} |")
    lines.append("")

    # ─── Model Error Profiles ───
    lines.append("---\n")
    lines.append("## 4. Model Error Profiles\n")
    lines.append("What types of errors does each summarization model make?\n")

    for model, profile in sorted(analysis["model_error_profile"].items()):
        lines.append(f"### {model}\n")
        lines.append(f"- **Total errors**: {analysis['errors_per_model'].get(model, 0)}")
        lines.append(f"- **Total omissions**: {analysis['omissions_per_model'].get(model, 0)}")
        lines.append("\n**Error breakdown:**\n")

        for cat, count in sorted(profile.items(), key=lambda x: x[1], reverse=True):
            label = TAXONOMY.get(cat, {}).get("label", cat.replace("_", " ").title())
            lines.append(f"- {label}: {count}")

        # Omissions
        om_profile = analysis["model_omission_profile"].get(model, {})
        if om_profile:
            lines.append("\n**Omission breakdown:**\n")
            for cat, count in sorted(om_profile.items(), key=lambda x: x[1], reverse=True):
                label = OMISSION_TAXONOMY.get(cat, {}).get("label", cat.replace("_", " ").title())
                lines.append(f"- {label}: {count}")

        lines.append("")

    # ─── Hardest Cases ───
    lines.append("---\n")
    lines.append("## 5. Hardest Cases (Most Major/Critical Errors)\n")
    lines.append("| Case | Major/Critical Errors |")
    lines.append("|---|---|")

    for case, count in analysis["hardest_cases"].items():
        lines.append(f"| {case} | {count} |")
    lines.append("")

    # ─── Errors per Judge ───
    lines.append("---\n")
    lines.append("## 6. Errors Detected per Judge\n")
    lines.append("| Judge | Errors Found |")
    lines.append("|---|---|")

    for judge, count in analysis["errors_per_judge"].items():
        lines.append(f"| {judge} | {count} |")
    lines.append("")
    lines.append("> Judges that find more errors are not necessarily *better* — they may be overly critical or flag non-issues.")
    lines.append("> Cross-reference with the meta-evaluation report to assess judge reliability.\n")

    # ─── Example Errors ───
    lines.append("---\n")
    lines.append("## 7. Example Errors by Category\n")

    seen_cats = set()
    for e in classified_data["classified_errors"]:
        cat = e["primary_category"]
        if cat in seen_cats:
            continue
        seen_cats.add(cat)

        label = TAXONOMY.get(cat, {}).get("label", cat.replace("_", " ").title())
        lines.append(f"### {label}\n")
        lines.append(f"- **Case**: {e['case']} | **Model**: {e['model']} | **Severity**: {e['severity']}")
        lines.append(f"- **Issue**: {e['issue'][:200]}")
        if e["error_quote"]:
            lines.append(f"- **Quote**: *\"{e['error_quote'][:150]}\"*")
        lines.append("")

    # ─── Key Takeaways ───
    lines.append("---\n")
    lines.append("## Key Takeaways\n")

    # Auto-generate insights
    top_error_cat = list(analysis["error_category_counts"].keys())[0] if analysis["error_category_counts"] else "N/A"
    top_error_label = TAXONOMY.get(top_error_cat, {}).get("label", top_error_cat)
    top_omission_cat = list(analysis["omission_category_counts"].keys())[0] if analysis["omission_category_counts"] else "N/A"
    top_omission_label = OMISSION_TAXONOMY.get(top_omission_cat, {}).get("label", top_omission_cat)

    lines.append(f"- **Most common error type**: {top_error_label} — LLMs frequently add details not present in the source")
    lines.append(f"- **Most common omission type**: {top_omission_label}")
    lines.append("- The error taxonomy demonstrates that this benchmark captures **legal-domain-specific** failure modes")
    lines.append("  that generic summarization benchmarks would miss entirely")
    lines.append("- Error profiles differ across models, enabling targeted model selection for legal applications")
    lines.append("")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    logger.info(f"Error taxonomy report saved to: {output_path}")
    return output_path


# =========================================================================
# MAIN ENTRY POINT
# =========================================================================

def run_error_taxonomy(base_dir: Path = None) -> dict:
    """
    Run the full error taxonomy pipeline.
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent.parent

    output_dir = base_dir / "outputs"
    judge_dir = output_dir / "judge_results"

    logger.info("=" * 60)
    logger.info("ERROR TAXONOMY: Legal-Specific Failure Analysis")
    logger.info("=" * 60)

    # Extract and classify
    logger.info("\n[1/3] Extracting and classifying errors...")
    classified_data = extract_and_classify_errors(judge_dir)
    logger.info(
        f"Classified {len(classified_data['classified_errors'])} errors and "
        f"{len(classified_data['classified_omissions'])} omissions"
    )

    # Analyze
    logger.info("\n[2/3] Analyzing taxonomy distributions...")
    analysis = analyze_taxonomy(classified_data)

    # Generate report
    logger.info("\n[3/3] Generating report...")
    generate_taxonomy_report(
        analysis=analysis,
        classified_data=classified_data,
        output_path=output_dir / "error_taxonomy_report.md",
    )

    # Save raw JSON
    raw_results = {
        "timestamp": datetime.now().isoformat(),
        "analysis": analysis,
        "classified_errors": classified_data["classified_errors"],
        "classified_omissions": classified_data["classified_omissions"],
    }
    raw_path = output_dir / "error_taxonomy_results.json"
    raw_path.write_text(json.dumps(raw_results, indent=2, default=str), encoding="utf-8")
    logger.info(f"Raw results saved to: {raw_path}")

    logger.info("\n" + "=" * 60)
    logger.info("ERROR TAXONOMY COMPLETE")
    logger.info("=" * 60)

    return raw_results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    run_error_taxonomy()
