'use client';

import { useState } from 'react';
import { getPerCaseResults, classifyScore, formatScore } from '../lib/data';

function AsciiBar({ score, width = 8 }) {
  const filled = Math.round(score * width);
  const empty = width - filled;
  return (
    <span className="ascii-bar">
      <span className="filled">{'█'.repeat(filled)}</span>
      {'░'.repeat(empty)}
    </span>
  );
}

export default function ExplorePage() {
  const cases = getPerCaseResults();
  const [selectedCase, setSelectedCase] = useState(null);
  const [view, setView] = useState('grid');

  return (
    <>
      <div className="section-header">
        <h1 className="section-title">Results Explorer</h1>
        <p className="section-subtitle">
          Per-case, per-model evaluation results.
          Click any case to expand pillar breakdowns.
        </p>
      </div>

      <hr className="divider" />

      <div className="tabs-brutal">
        <button className={`tab-brutal ${view === 'grid' ? 'active' : ''}`} onClick={() => setView('grid')}>
          [cards]
        </button>
        <button className={`tab-brutal ${view === 'table' ? 'active' : ''}`} onClick={() => setView('table')}>
          [table]
        </button>
      </div>

      {view === 'table' ? (
        <div style={{ overflowX: 'auto' }}>
          <table className="terminal-table">
            <thead>
              <tr>
                <th>Case</th>
                <th>Model</th>
                <th>Composite</th>
                <th>NLI</th>
                <th>Judge</th>
                <th>Coverage</th>
              </tr>
            </thead>
            <tbody>
              {cases.flatMap((c) => {
                if (!c.models.length) {
                  return (
                    <tr key={`${c.caseName}-empty`}>
                      <td
                        style={{
                          maxWidth: '220px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          fontWeight: 500,
                        }}
                      >
                        {c.caseName}
                      </td>
                      <td colSpan={5} style={{ color: 'var(--text-muted)' }}>
                        No model output available in current snapshot.
                      </td>
                    </tr>
                  );
                }

                return c.models.map((m) => (
                  <tr key={`${c.caseName}-${m.model}`}>
                    <td
                      style={{
                        maxWidth: '220px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        fontWeight: 500,
                      }}
                    >
                      {c.caseName}
                    </td>
                    <td>{m.shortName}</td>
                    <td>
                      <span className="ascii-score">
                        <span className={`value score-${classifyScore(m.composite_score)}`}>{formatScore(m.composite_score)}</span>
                        <AsciiBar score={m.composite_score} />
                      </span>
                    </td>
                    <td className={`score-${classifyScore(m.nli_score)}`}>{formatScore(m.nli_score)}</td>
                    <td className={`score-${classifyScore(m.judge_score)}`}>{formatScore(m.judge_score)}</td>
                    <td className={`score-${classifyScore(m.coverage_score)}`}>{formatScore(m.coverage_score)}</td>
                  </tr>
                ));
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
            gap: '1px',
            background: 'var(--border)',
          }}
        >
          {cases.map((c) => {
            const isExpanded = selectedCase === c.caseName;
            const hasModels = c.models.length > 0;
            const sortedModels = [...c.models].sort((a, b) => b.composite_score - a.composite_score);
            const bestModel = sortedModels[0];

            return (
              <div
                key={c.caseName}
                className={`card-brutal ${isExpanded ? 'active' : ''}`}
                onClick={() => setSelectedCase(isExpanded ? null : c.caseName)}
                style={{ cursor: 'pointer' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.625rem' }}>
                  <span
                    style={{
                      fontFamily: 'var(--font-display)',
                      fontSize: '0.95rem',
                      fontWeight: 600,
                      lineHeight: 1.2,
                    }}
                  >
                    {c.caseName}
                  </span>
                </div>

                {hasModels ? (
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
                      gap: '0.5rem',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.75rem',
                    }}
                  >
                    {c.models.map((m) => (
                      <div key={m.model}>
                        <div
                          style={{
                            color: 'var(--text-muted)',
                            marginBottom: '0.2rem',
                            fontSize: '0.625rem',
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                            lineHeight: 1.25,
                            wordBreak: 'break-word',
                          }}
                        >
                          {m.shortName}
                        </div>
                        <span className={`score-${classifyScore(m.composite_score)}`}>{formatScore(m.composite_score)}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    No model output available in current snapshot.
                  </div>
                )}

                {isExpanded && (
                  <div style={{ marginTop: '0.75rem', borderTop: '1px dashed var(--border-strong)', paddingTop: '0.625rem' }}>
                    {hasModels ? (
                      <div style={{ overflowX: 'auto', paddingBottom: '0.125rem' }}>
                        <table className="terminal-table" style={{ fontSize: '0.75rem', minWidth: '380px' }}>
                          <thead>
                            <tr>
                              <th style={{ padding: '0.375rem 0.25rem', width: '160px' }}>Model</th>
                              <th style={{ padding: '0.375rem 0.25rem' }}>
                                <span className="pillar-indicator pillar-nli" />NLI
                              </th>
                              <th style={{ padding: '0.375rem 0.25rem' }}>
                                <span className="pillar-indicator pillar-judge" />Judge
                              </th>
                              <th style={{ padding: '0.375rem 0.25rem' }}>
                                <span className="pillar-indicator pillar-coverage" />Cov
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {sortedModels.map((m) => (
                              <tr key={m.model}>
                                <td
                                  style={{
                                    padding: '0.375rem 0.25rem',
                                    fontWeight: 500,
                                    maxWidth: '160px',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                  }}
                                  title={m.shortName}
                                >
                                  {m.shortName}
                                  {m.model === bestModel?.model && (
                                    <span style={{ color: 'var(--text-secondary)', marginLeft: '0.25rem' }}>*</span>
                                  )}
                                </td>
                                <td style={{ padding: '0.375rem 0.25rem' }} className={`score-${classifyScore(m.nli_score)}`}>
                                  {formatScore(m.nli_score)}
                                </td>
                                <td style={{ padding: '0.375rem 0.25rem' }} className={`score-${classifyScore(m.judge_score)}`}>
                                  {formatScore(m.judge_score)}
                                </td>
                                <td style={{ padding: '0.375rem 0.25rem' }} className={`score-${classifyScore(m.coverage_score)}`}>
                                  {formatScore(m.coverage_score)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        This case currently has no per-model scores in the data snapshot.
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
