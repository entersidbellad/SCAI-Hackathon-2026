/**
 * Data loading utilities for ∑val benchmark results.
 * 
 * Loads data from static JSON files copied from the pipeline output.
 * In production, these would be API calls to the FastAPI backend.
 */

import results from '../../data/results.json';
import metaEval from '../../data/meta_evaluation_results.json';

/**
 * Get the full results data
 */
export function getResults() {
    return results;
}

/**
 * Get meta-evaluation data
 */
export function getMetaEvaluation() {
    return metaEval;
}

/**
 * Get sorted model rankings from composite scores
 */
export function getModelRankings() {
    const perModel = results.composite_scores?.per_model || {};

    return Object.entries(perModel)
        .map(([model, stats]) => ({
            model,
            shortName: model.split('/').pop()?.split(':')[0] || model,
            provider: model.split('/')[0] || 'unknown',
            avgComposite: stats.avg_composite_score || 0,
            avgNli: stats.avg_nli_score || 0,
            avgJudge: stats.avg_judge_score || 0,
            avgCoverage: stats.avg_coverage_score || 0,
            numCases: stats.num_cases || 0,
            ci95: stats.composite_ci_95 || null,
            stdError: stats.composite_std_error || null,
        }))
        .sort((a, b) => b.avgComposite - a.avgComposite);
}

/**
 * Get per-case results
 */
export function getPerCaseResults() {
    const perCase = results.composite_scores?.per_case || {};

    return Object.entries(perCase).map(([caseName, models]) => ({
        caseName,
        models: Object.entries(models).map(([model, scores]) => ({
            model,
            shortName: model.split('/').pop()?.split(':')[0] || model,
            ...scores,
        })),
    }));
}

/**
 * Get detailed results for a specific model
 */
export function getModelDetails(modelName) {
    const perCase = results.composite_scores?.per_case || {};
    const cases = [];

    for (const [caseName, models] of Object.entries(perCase)) {
        for (const [model, scores] of Object.entries(models)) {
            if (model === modelName || model.includes(modelName)) {
                cases.push({ caseName, ...scores });
            }
        }
    }

    return cases.sort((a, b) => b.composite_score - a.composite_score);
}

/**
 * Get pairwise significance data
 */
export function getPairwiseSignificance() {
    return results.composite_scores?.pairwise_significance || {};
}

/**
 * Get summary stats
 */
export function getSummaryStats() {
    const rankings = getModelRankings();
    const perCase = results.composite_scores?.per_case || {};

    return {
        numModels: rankings.length,
        numCases: Object.keys(perCase).length,
        bestModel: results.summary?.best_model || 'N/A',
        bestScore: results.summary?.best_avg_score || 0,
        generatedAt: results.metadata?.generated_at || '',
    };
}

/**
 * Get benchmark score spread summary for non-technical explainers.
 */
export function getScoreSpreadSummary() {
    const rankings = getModelRankings();
    const scores = rankings
        .map((model) => model.avgComposite)
        .filter((score) => Number.isFinite(score));

    if (!scores.length) {
        return {
            hasData: false,
            count: 0,
            topScore: null,
            medianScore: null,
            bottomScore: null,
            spread: null,
        };
    }

    const sorted = [...scores].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    const medianScore = sorted.length % 2 === 0
        ? (sorted[mid - 1] + sorted[mid]) / 2
        : sorted[mid];
    const topScore = sorted[sorted.length - 1];
    const bottomScore = sorted[0];

    return {
        hasData: true,
        count: sorted.length,
        topScore,
        medianScore,
        bottomScore,
        spread: topScore - bottomScore,
    };
}

/**
 * Get judge agreement data from meta-evaluation
 */
export function getJudgeAgreement() {
    // Cohen's Kappa: dict of { "judge1 ↔ judge2": { factual_accuracy_kappa, completeness_kappa, ... } }
    const rawKappa = metaEval.cohens_kappa || {};
    const kappaPairs = Object.entries(rawKappa).map(([pairName, data]) => ({
        pairName,
        judges: pairName.split(' ↔ '),
        accuracyKappa: data.factual_accuracy_kappa,
        completenessKappa: data.completeness_kappa,
        n: data.n_paired_observations,
        accuracyCi95: data.accuracy_ci_95 || null,
        completenessCi95: data.completeness_ci_95 || null,
        interpretationAccuracy: data.interpretation_accuracy,
        interpretationCompleteness: data.interpretation_completeness,
    }));

    // Kendall's Tau: pairwise dict
    const rawTau = metaEval.kendall_tau?.pairwise || {};
    const tauPairs = Object.entries(rawTau).map(([pairName, data]) => ({
        pairName,
        judges: pairName.split(' ↔ '),
        overallTau: data.overall_tau,
        pValue: data.overall_p_value,
        n: data.n_comparisons,
        ci95Lower: data.ci_95_lower,
        ci95Upper: data.ci_95_upper,
        interpretation: data.interpretation,
    }));

    return { kappaPairs, tauPairs };
}

/**
 * Get score distributions from meta-evaluation
 * Returns: { judgeName: { count, factualAccuracy: {mean, std, distribution}, completeness: {...} } }
 */
export function getScoreDistributions() {
    const raw = metaEval.score_distributions || {};
    const result = {};
    for (const [judge, data] of Object.entries(raw)) {
        result[judge] = {
            count: data.n_evaluations,
            factualAccuracy: data.factual_accuracy,
            completeness: data.completeness,
            normalizedJudge: data.normalized_judge_score,
        };
    }
    return result;
}

/**
 * Get pillar correlations from meta-evaluation
 * Returns: { judgeName: [ { pairLabel, rho, pValue, interpretation } ] }
 */
export function getPillarCorrelations() {
    const raw = metaEval.pillar_correlations || {};
    const result = {};
    for (const [judge, data] of Object.entries(raw)) {
        const correlations = data.correlations || {};
        result[judge] = Object.entries(correlations).map(([pairLabel, corr]) => ({
            pairLabel,
            rho: corr.spearman_rho,
            pValue: corr.p_value,
            interpretation: corr.interpretation,
        }));
    }
    return result;
}

/**
 * Utility: classify a score value for styling
 */
export function classifyScore(score) {
    if (score >= 0.85) return 'excellent';
    if (score >= 0.7) return 'good';
    if (score >= 0.5) return 'moderate';
    return 'poor';
}

/**
 * Format a score with optional CI
 */
export function formatScore(score, decimals = 3) {
    if (score === null || score === undefined) return '—';
    return score.toFixed(decimals);
}
