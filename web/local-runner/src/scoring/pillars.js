const STOPWORDS = new Set([
  'a', 'an', 'and', 'are', 'as', 'at', 'be', 'because', 'been', 'being', 'by', 'for', 'from', 'has', 'have', 'i',
  'in', 'is', 'it', 'its', 'of', 'on', 'or', 'that', 'the', 'their', 'there', 'this', 'to', 'was', 'were', 'will',
  'with', 'you', 'your', 'can', 'could', 'would', 'should', 'about', 'into', 'than', 'then', 'they', 'them', 'he',
  'she', 'we', 'our', 'not', 'no', 'but', 'if', 'when', 'which', 'who', 'whom', 'what', 'where', 'why', 'how',
]);

function clamp(value, min = 0, max = 1) {
  return Math.max(min, Math.min(max, value));
}

function tokenize(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .map((token) => token.trim())
    .filter((token) => token.length > 2 && !STOPWORDS.has(token));
}

function toSet(tokens) {
  return new Set(tokens);
}

function overlapRatio(sourceSet, compareSet) {
  if (!sourceSet.size) return 0;
  let hits = 0;
  for (const item of sourceSet) {
    if (compareSet.has(item)) hits += 1;
  }
  return hits / sourceSet.size;
}

function topTerms(tokens, limit = 24) {
  const counts = new Map();
  for (const token of tokens) {
    counts.set(token, (counts.get(token) || 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([token]) => token);
}

function evaluateJudge(caseText, summaryText) {
  const caseTokens = tokenize(caseText);
  const summaryTokens = tokenize(summaryText);
  const caseSet = toSet(caseTokens);
  const summarySet = toSet(summaryTokens);

  if (!summaryTokens.length) {
    return {
      value: 0,
      confidence: 0.1,
      explanation: 'No summary text returned by model.',
      missing_reason: null,
    };
  }

  const tokenOverlap = overlapRatio(summarySet, caseSet);
  const numericSignals = /\d/.test(summaryText) ? 0.08 : 0;
  const lengthSignals = summaryText.length >= 180 ? 0.1 : summaryText.length >= 100 ? 0.05 : -0.08;
  const structureSignals = /\b(therefore|however|because|while|in summary|holding|court)\b/i.test(summaryText)
    ? 0.06
    : 0;

  const score = clamp(0.42 + tokenOverlap * 0.42 + numericSignals + lengthSignals + structureSignals);
  const confidence = clamp(0.45 + tokenOverlap * 0.5);

  return {
    value: score,
    confidence,
    explanation:
      'Judge score heuristic uses lexical overlap, structure quality, and evidence cues. Higher means clearer factual grounding.',
    missing_reason: null,
  };
}

function evaluateCoverage(referenceSummary, summaryText) {
  if (!String(referenceSummary || '').trim()) {
    return {
      value: null,
      confidence: 0,
      explanation: 'Coverage unavailable because no reference summary was provided.',
      missing_reason: 'reference_summary_missing',
    };
  }

  const referenceTokens = tokenize(referenceSummary);
  const summaryTokens = tokenize(summaryText);

  const topReferenceTerms = topTerms(referenceTokens, 28);
  const summarySet = toSet(summaryTokens);

  if (!topReferenceTerms.length) {
    return {
      value: 0,
      confidence: 0.3,
      explanation: 'Coverage score could not identify stable reference terms.',
      missing_reason: null,
    };
  }

  let covered = 0;
  for (const term of topReferenceTerms) {
    if (summarySet.has(term)) covered += 1;
  }

  const coverage = clamp(covered / topReferenceTerms.length);
  const confidence = clamp(0.5 + coverage * 0.45);

  return {
    value: coverage,
    confidence,
    explanation: `Coverage tracks how many key reference terms appear in the model summary (${covered}/${topReferenceTerms.length}).`,
    missing_reason: null,
  };
}

function evaluateNli(caseText, referenceSummary, summaryText) {
  if (!String(referenceSummary || '').trim()) {
    return {
      value: null,
      confidence: 0,
      explanation: 'NLI contradiction score unavailable because no reference summary was provided.',
      missing_reason: 'reference_summary_missing',
    };
  }

  const sourceTokens = tokenize(`${caseText} ${referenceSummary}`);
  const summaryTokens = tokenize(summaryText);
  const sourceSet = toSet(sourceTokens);
  const summarySet = toSet(summaryTokens);

  if (!summarySet.size) {
    return {
      value: 0,
      confidence: 0.1,
      explanation: 'Model returned empty text, so contradiction risk is high.',
      missing_reason: null,
    };
  }

  const support = overlapRatio(summarySet, sourceSet);

  let unsupported = 0;
  for (const token of summarySet) {
    if (!sourceSet.has(token)) unsupported += 1;
  }
  const unsupportedRate = unsupported / Math.max(1, summarySet.size);

  const negationMismatch = /\b(not|never|no)\b/i.test(summaryText) !== /\b(not|never|no)\b/i.test(referenceSummary)
    ? 0.08
    : 0;

  const score = clamp(0.35 + support * 0.7 - unsupportedRate * 0.28 - negationMismatch);
  const confidence = clamp(0.45 + support * 0.45 - unsupportedRate * 0.2);

  return {
    value: score,
    confidence,
    explanation:
      'NLI score approximates contradiction risk from source-support overlap and unsupported-claim penalty.',
    missing_reason: null,
  };
}

function evaluatePillars({ caseText, referenceSummary, summaryText }) {
  const judge = evaluateJudge(caseText, summaryText);
  const nli = evaluateNli(caseText, referenceSummary, summaryText);
  const coverage = evaluateCoverage(referenceSummary, summaryText);

  return {
    nli,
    judge,
    coverage,
  };
}

module.exports = {
  evaluatePillars,
};
