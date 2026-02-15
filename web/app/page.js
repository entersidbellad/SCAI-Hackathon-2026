'use client';

import { useState } from 'react';
import {
  getModelRankings,
  getSummaryStats,
  getPairwiseSignificance,
  classifyScore,
  formatScore,
} from './lib/data';

function AsciiBar({ score, width = 10 }) {
  const filled = Math.round(score * width);
  const empty = width - filled;
  return (
    <span className="ascii-bar">
      <span className="filled">{'█'.repeat(filled)}</span>
      {'░'.repeat(empty)}
    </span>
  );
}

function SortArrow({ column, sortKey, sortDir }) {
  if (sortKey !== column) return null;
  return <span style={{ marginLeft: "0.25rem" }}>{sortDir === "desc" ? "↓" : "↑"}</span>;
}

export default function LeaderboardPage() {
  const rankings = getModelRankings();
  const stats = getSummaryStats();
  const significance = getPairwiseSignificance();
  const hasAnyCi = rankings.some(
    (model) => model.ci95?.lower != null && model.ci95?.upper != null,
  );
  const [sortKey, setSortKey] = useState('avgComposite');
  const [sortDir, setSortDir] = useState('desc');

  const sortedRankings = [...rankings].sort((a, b) => {
    const mult = sortDir === 'desc' ? -1 : 1;
    return mult * (a[sortKey] - b[sortKey]);
  });

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  return (
    <>
      {/* Hero */}
      <div className="hero">
        <div className="hero-text">
          <div className="hero-motif" aria-hidden="true">
            [:: faithfulness.signal ::] ││░░││
          </div>
          <h1 className="hero-title">
            Faithfulness<br />Benchmark
          </h1>
          <p className="hero-subtitle">
            Evaluating AI summarization of Supreme Court opinions
            across three complementary pillars: NLI contradiction
            detection, LLM-as-Judge scoring, and semantic coverage.
          </p>
        </div>

        {/* Stat Line */}
        <div className="stat-line">
          <div className="stat-item">
            <span className="stat-number">{stats.numCases}</span>
            <span className="stat-label">Cases</span>
          </div>
          <span className="stat-pipe">│</span>
          <div className="stat-item">
            <span className="stat-number">{stats.numModels}</span>
            <span className="stat-label">Models</span>
          </div>
          <span className="stat-pipe">│</span>
          <div className="stat-item">
            <span className="stat-number">3</span>
            <span className="stat-label">Judges</span>
          </div>
          <span className="stat-pipe">│</span>
          <div className="stat-item">
            <span className="stat-number">3</span>
            <span className="stat-label">Pillars</span>
          </div>
        </div>
      </div>

      <hr className="divider" />

      {/* Rankings Table */}
      <h2 style={{
        fontFamily: 'var(--font-display)',
        fontSize: '1.75rem',
        fontWeight: 600,
        textTransform: 'uppercase',
        marginBottom: '0.25rem',
      }}>
        Model Rankings
      </h2>
      <p style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '0.75rem',
        color: 'var(--text-secondary)',
        marginBottom: '0.75rem',
      }}>
        Composite = 0.35 × NLI + 0.40 × Judge + 0.25 × Coverage. Click headers to sort.
        {!hasAnyCi && (
          <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
            [CI not provided in current snapshot]
          </span>
        )}
      </p>

      <div style={{ overflowX: 'auto' }}>
        <table className="terminal-table">
          <thead>
            <tr>
              <th style={{ width: '50px' }}>#</th>
              <th>Model</th>
              <th
                className={sortKey === 'avgComposite' ? 'sorted' : ''}
                onClick={() => handleSort('avgComposite')}
              >
                Composite <SortArrow column="avgComposite" sortKey={sortKey} sortDir={sortDir} />
              </th>
              {hasAnyCi && <th style={{ fontSize: '0.6rem' }}>95% CI</th>}
              <th
                className={sortKey === 'avgNli' ? 'sorted' : ''}
                onClick={() => handleSort('avgNli')}
              >
                <span className="pillar-indicator pillar-nli" />
                NLI <SortArrow column="avgNli" sortKey={sortKey} sortDir={sortDir} />
              </th>
              <th
                className={sortKey === 'avgJudge' ? 'sorted' : ''}
                onClick={() => handleSort('avgJudge')}
              >
                <span className="pillar-indicator pillar-judge" />
                Judge <SortArrow column="avgJudge" sortKey={sortKey} sortDir={sortDir} />
              </th>
              <th
                className={sortKey === 'avgCoverage' ? 'sorted' : ''}
                onClick={() => handleSort('avgCoverage')}
              >
                <span className="pillar-indicator pillar-coverage" />
                Coverage <SortArrow column="avgCoverage" sortKey={sortKey} sortDir={sortDir} />
              </th>
              <th>N</th>
            </tr>
          </thead>
          <tbody>
            {sortedRankings.map((model, idx) => {
              const rank = idx + 1;
              return (
                <tr key={model.model}>
                  <td>
                    <span className={`rank-${rank}`} style={{ fontWeight: 600 }}>
                      {rank}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontWeight: 500 }}>{model.shortName}</span>
                    <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem', fontSize: '0.6875rem' }}>
                      {model.provider}
                    </span>
                  </td>
                  <td>
                    <span className="ascii-score">
                      <span className={`value score-${classifyScore(model.avgComposite)}`}>
                        {formatScore(model.avgComposite)}
                      </span>
                      <AsciiBar score={model.avgComposite} />
                    </span>
                  </td>
                  {hasAnyCi && (
                    <td>
                      {model.ci95?.lower != null ? (
                        <span className="ci-range">
                          [{formatScore(model.ci95.lower)}–{formatScore(model.ci95.upper)}]
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-dim)' }}>—</span>
                      )}
                    </td>
                  )}
                  <td>
                    <span className={`score-${classifyScore(model.avgNli)}`}>
                      {formatScore(model.avgNli)}
                    </span>
                  </td>
                  <td>
                    <span className={`score-${classifyScore(model.avgJudge)}`}>
                      {formatScore(model.avgJudge)}
                    </span>
                  </td>
                  <td>
                    <span className={`score-${classifyScore(model.avgCoverage)}`}>
                      {formatScore(model.avgCoverage)}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-secondary)' }}>{model.numCases}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pairwise Significance */}
      {Object.keys(significance).length > 0 && (
        <>
          <hr className="divider" />
          <h2 style={{
            fontFamily: 'var(--font-display)',
            fontSize: '1.5rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            marginBottom: '0.5rem',
          }}>
            Pairwise Significance
          </h2>

          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem' }}>
            {Object.entries(significance).map(([pair, data]) => (
              <div key={pair} style={{
                padding: '0.375rem 0',
                borderBottom: '1px solid var(--border)',
                display: 'flex',
                gap: '1.5rem',
                alignItems: 'baseline',
                flexWrap: 'wrap',
              }}>
                <span style={{ color: 'var(--text)', minWidth: '280px' }}>
                  {data.winner || pair}
                </span>
                <span style={{ color: 'var(--text-secondary)' }}>
                  Δ={data.mean_diff > 0 ? '+' : ''}{formatScore(data.mean_diff, 4)}
                </span>
                <span style={{ color: 'var(--text-muted)' }}>
                  CI=[{formatScore(data.ci_95_lower, 4)}, {formatScore(data.ci_95_upper, 4)}]
                </span>
                <span className={data.significant ? 'badge-sig' : 'badge-nsig'}>
                  [{data.significant ? 'SIGNIFICANT' : 'NOT SIGNIFICANT'}]
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Scoring Note */}
      <hr className="divider" />
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
        <strong style={{ color: 'var(--text)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Scoring
        </strong>
        <br />
        Composite = 0.35 × NLI + 0.40 × Judge + 0.25 × Coverage.
        NLI = 1 − contradiction_rate (DeBERTa-v3-large).
        Judge = multi-LLM factual accuracy + completeness (1–5 scale).
        Coverage = ground truth sentence coverage via embeddings.
        {hasAnyCi
          ? ' 95% CIs via 1,000-iteration bootstrap.'
          : ' CI fields are not included in this current data snapshot.'}
      </div>
    </>
  );
}
