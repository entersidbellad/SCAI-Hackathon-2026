'use client';

import { getJudgeAgreement, getScoreDistributions, getPillarCorrelations, formatScore } from '../lib/data';

const sectionTitleStyle = {
  fontFamily: 'var(--font-display)',
  fontSize: '1.5rem',
  fontWeight: 600,
  textTransform: 'uppercase',
  marginBottom: '0.375rem',
};

const sectionNoteStyle = {
  fontSize: '0.75rem',
  color: 'var(--text-secondary)',
  marginBottom: '0.875rem',
};

function KappaInterpret(value) {
  if (value >= 0.81) return 'near-perfect';
  if (value >= 0.61) return 'substantial';
  if (value >= 0.41) return 'moderate';
  if (value >= 0.21) return 'fair';
  return 'poor';
}

function AsciiHistogram({ distribution, label }) {
  if (!distribution) return null;
  const maxCount = Math.max(...Object.values(distribution));

  return (
    <div style={{ marginTop: '0.5rem' }}>
      <div
        style={{
          fontSize: '0.625rem',
          color: 'var(--text-muted)',
          marginBottom: '0.25rem',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
        }}
      >
        {label}
      </div>
      {Object.entries(distribution).map(([score, count]) => {
        const barWidth = maxCount > 0 ? Math.round((count / maxCount) * 20) : 0;
        return (
          <div
            key={score}
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.6875rem',
              lineHeight: 1.65,
              display: 'flex',
              gap: '0.5rem',
            }}
          >
            <span style={{ color: 'var(--text-muted)', width: '1em', textAlign: 'right' }}>{score}</span>
            <span style={{ color: 'var(--accent)' }}>{'█'.repeat(barWidth)}</span>
            <span style={{ color: 'var(--text-dim)' }}>{'░'.repeat(20 - barWidth)}</span>
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.625rem' }}>({count})</span>
          </div>
        );
      })}
    </div>
  );
}

export default function ReliabilityPage() {
  const { kappaPairs, tauPairs } = getJudgeAgreement();
  const distributions = getScoreDistributions();
  const correlations = getPillarCorrelations();

  return (
    <>
      <div className="section-header">
        <h1 className="section-title">Judge Reliability</h1>
        <p className="section-subtitle">
          Inter-judge agreement analysis. Cohen&apos;s Kappa (primary AI↔AI).
          Kendall&apos;s Tau (supplementary rank correlation).
        </p>
      </div>

      <hr className="divider" />

      <h2 style={sectionTitleStyle}>Cohen&apos;s Kappa</h2>
      <p style={sectionNoteStyle}>Primary AI to AI metric. k &gt;= 0.6 = substantial, k &gt;= 0.8 = near-perfect.</p>

      <div style={{ overflowX: 'auto' }}>
        <table className="terminal-table">
          <thead>
            <tr>
              <th>Judge Pair</th>
              <th>Accuracy κ</th>
              <th>95% CI</th>
              <th>Completeness κ</th>
              <th>95% CI</th>
              <th>Level</th>
              <th>N</th>
            </tr>
          </thead>
          <tbody>
            {kappaPairs.map((pair, idx) => (
              <tr key={idx}>
                <td style={{ fontWeight: 500 }}>
                  {pair.judges[0]} ↔ {pair.judges[1]}
                </td>
                <td>
                  <span className={`score-${pair.accuracyKappa >= 0.6 ? 'excellent' : pair.accuracyKappa >= 0.4 ? 'good' : 'moderate'}`}>
                    {formatScore(pair.accuracyKappa, 4)}
                  </span>
                </td>
                <td>
                  <span className="ci-range">
                    {pair.accuracyCi95
                      ? `[${formatScore(pair.accuracyCi95.lower, 3)}, ${formatScore(pair.accuracyCi95.upper, 3)}]`
                      : '—'}
                  </span>
                </td>
                <td>
                  <span className={`score-${pair.completenessKappa >= 0.6 ? 'excellent' : pair.completenessKappa >= 0.4 ? 'good' : 'moderate'}`}>
                    {formatScore(pair.completenessKappa, 4)}
                  </span>
                </td>
                <td>
                  <span className="ci-range">
                    {pair.completenessCi95
                      ? `[${formatScore(pair.completenessCi95.lower, 3)}, ${formatScore(pair.completenessCi95.upper, 3)}]`
                      : '—'}
                  </span>
                </td>
                <td style={{ color: 'var(--text-secondary)', fontSize: '0.6875rem' }}>
                  {KappaInterpret(pair.accuracyKappa)} / {KappaInterpret(pair.completenessKappa)}
                </td>
                <td style={{ color: 'var(--text-secondary)' }}>{pair.n}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <hr className="divider" />

      <h2 style={sectionTitleStyle}>Kendall&apos;s Tau</h2>
      <p style={sectionNoteStyle}>Supplementary rank correlation. t &gt; 0.7 = strong agreement.</p>

      <div style={{ overflowX: 'auto' }}>
        <table className="terminal-table">
          <thead>
            <tr>
              <th>Judge Pair</th>
              <th>Overall τ</th>
              <th>95% CI</th>
              <th>p-value</th>
              <th>N</th>
            </tr>
          </thead>
          <tbody>
            {tauPairs.map((pair, idx) => (
              <tr key={idx}>
                <td style={{ fontWeight: 500 }}>
                  {pair.judges[0]} ↔ {pair.judges[1]}
                </td>
                <td>
                  <span className={`score-${pair.overallTau >= 0.6 ? 'excellent' : pair.overallTau >= 0.4 ? 'good' : 'moderate'}`}>
                    {formatScore(pair.overallTau, 4)}
                  </span>
                </td>
                <td>
                  <span className="ci-range">
                    {pair.ci95Lower != null
                      ? `[${formatScore(pair.ci95Lower, 3)}, ${formatScore(pair.ci95Upper, 3)}]`
                      : '—'}
                  </span>
                </td>
                <td style={{ color: pair.pValue != null && pair.pValue < 0.05 ? 'var(--text)' : 'var(--text-muted)' }}>
                  {pair.pValue != null ? pair.pValue.toFixed(4) : '—'}
                </td>
                <td style={{ color: 'var(--text-secondary)' }}>{pair.n}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <hr className="divider" />

      <h2 style={sectionTitleStyle}>Score Distributions</h2>
      <p style={sectionNoteStyle}>How each judge uses the 1-5 scale.</p>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '1px',
          background: 'var(--border)',
        }}
      >
        {Object.entries(distributions).map(([judge, data]) => (
          <div key={judge} className="card-brutal">
            <div
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '1rem',
                fontWeight: 600,
                marginBottom: '0.375rem',
                textTransform: 'uppercase',
              }}
            >
              {judge}
            </div>
            <div style={{ fontSize: '0.6875rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              N={data.count} &nbsp; μ_acc={formatScore(data.factualAccuracy?.mean, 2)} &nbsp; σ_acc={formatScore(data.factualAccuracy?.std, 2)}
            </div>

            <AsciiHistogram distribution={data.factualAccuracy?.distribution} label="Factual Accuracy" />
            <AsciiHistogram distribution={data.completeness?.distribution} label="Completeness" />
          </div>
        ))}
      </div>

      <hr className="divider" />

      <h2 style={sectionTitleStyle}>Pillar Correlations</h2>
      <p style={sectionNoteStyle}>Low |ρ| = complementary pillars. High |ρ| = redundant.</p>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '1px',
          background: 'var(--border)',
        }}
      >
        {Object.entries(correlations).map(([judge, pairs]) => (
          <div key={judge} className="card-brutal">
            <div
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '1rem',
                fontWeight: 600,
                marginBottom: '0.5rem',
                textTransform: 'uppercase',
              }}
            >
              {judge}
            </div>
            {(pairs || []).map((pair, i) => (
              <div
                key={i}
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.6875rem',
                  lineHeight: 1.8,
                  display: 'flex',
                  gap: '0.75rem',
                  borderBottom: i < pairs.length - 1 ? '1px solid var(--border)' : 'none',
                  paddingBottom: '0.2rem',
                  paddingTop: '0.1rem',
                }}
              >
                <span style={{ color: 'var(--text-secondary)', minWidth: '170px', fontSize: '0.625rem' }}>
                  {pair.pairLabel}
                </span>
                <span className={`score-${Math.abs(pair.rho) < 0.3 ? 'excellent' : Math.abs(pair.rho) < 0.6 ? 'good' : 'moderate'}`}>
                  ρ={formatScore(pair.rho, 4)}
                </span>
                <span style={{ color: 'var(--text-muted)' }}>p={formatScore(pair.pValue, 4)}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </>
  );
}
