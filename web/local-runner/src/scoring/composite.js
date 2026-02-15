const WEIGHTS = {
  nli: 0.35,
  judge: 0.4,
  coverage: 0.25,
};

function clamp(value, min = 0, max = 1) {
  return Math.max(min, Math.min(max, value));
}

function buildComposite(pillars) {
  const available = Object.entries(WEIGHTS).filter(([name]) => Number.isFinite(pillars?.[name]?.value));

  if (!available.length) {
    return {
      composite_score: null,
      composite_confidence: 0,
      score_mode: 'provisional',
      weights_used: {},
      warnings: ['No score pillars were available for composite score.'],
    };
  }

  const weightTotal = available.reduce((sum, [, weight]) => sum + weight, 0);
  const normalizedWeights = {};
  let weightedScore = 0;
  let weightedConfidence = 0;

  for (const [name, weight] of available) {
    const normalizedWeight = weight / weightTotal;
    normalizedWeights[name] = Number(normalizedWeight.toFixed(3));
    weightedScore += (pillars[name].value || 0) * normalizedWeight;
    weightedConfidence += (pillars[name].confidence || 0) * normalizedWeight;
  }

  const scoreMode = weightTotal === 1 ? 'full' : 'provisional';
  const warnings = [];

  if (scoreMode === 'provisional') {
    warnings.push('Reference summary missing. Composite is provisional and not leaderboard-comparable.');
  }

  return {
    composite_score: clamp(weightedScore),
    composite_confidence: clamp(weightedConfidence),
    score_mode: scoreMode,
    weights_used: normalizedWeights,
    warnings,
  };
}

module.exports = {
  WEIGHTS,
  buildComposite,
};
