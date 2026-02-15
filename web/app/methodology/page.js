'use client';

const sectionTitleStyle = {
  fontFamily: 'var(--font-display)',
  fontSize: '1.5rem',
  fontWeight: 600,
  textTransform: 'uppercase',
  marginBottom: '0.5rem',
};

const sectionTextStyle = {
  fontFamily: 'var(--font-mono)',
  fontSize: '0.75rem',
  color: 'var(--text-secondary)',
  lineHeight: 1.85,
};

const dataLabelStyle = {
  color: 'var(--text)',
  display: 'block',
  marginBottom: '0.25rem',
  fontSize: '0.625rem',
  textTransform: 'uppercase',
  letterSpacing: '0.1em',
};

export default function MethodologyPage() {
  return (
    <>
      <div className="section-header">
        <h1 className="section-title">Methodology</h1>
        <p className="section-subtitle">
          Three-pillar composite scoring for AI summarization faithfulness.
          No single metric captures faithfulness; each pillar catches what the others miss.
        </p>
      </div>

      <hr className="divider" />

      <h2 style={sectionTitleStyle}>Composite Formula</h2>

      <div
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '0.875rem',
          padding: '1rem',
          background: 'var(--bg-elevated)',
          border: '1px dashed var(--border-strong)',
          lineHeight: 1.8,
          marginBottom: '1rem',
        }}
      >
        composite = <span style={{ color: 'var(--text-secondary)' }}>0.35</span> x NLI +{' '}
        <span style={{ color: 'var(--text-secondary)' }}>0.40</span> x Judge +{' '}
        <span style={{ color: 'var(--text-secondary)' }}>0.25</span> x Coverage
        <br />
        <br />
        <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
          | Judge weight highest: human-aligned factual accuracy + completeness
          <br />
          | NLI weight second: automated contradiction detection at scale
          <br />
          | Coverage weight lowest: supplementary sentence-level recall
        </span>
      </div>

      <hr className="divider" />

      <h2 style={sectionTitleStyle}>The Three Pillars</h2>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '1px',
          background: 'var(--border)',
          marginBottom: '1rem',
        }}
      >
        <div className="card-brutal">
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'baseline',
              marginBottom: '0.625rem',
            }}
          >
            <h3
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '1.2rem',
                fontWeight: 600,
                textTransform: 'uppercase',
              }}
            >
              NLI Score
            </h3>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--text-muted)' }}>
              WEIGHT: 0.35
            </span>
          </div>
          <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: '0.75rem' }}>
            NLI = 1 - contradiction_rate
          </div>
          <div style={sectionTextStyle}>
            <strong style={dataLabelStyle}>Model</strong>
            DeBERTa-v3-large fine-tuned on MNLI.
            Each sentence to (premise, hypothesis) pair against source.
            <br />
            <br />
            <strong style={dataLabelStyle}>What It Catches</strong>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem' }}>
              | Hallucinated facts
              <br />
              | Incorrect legal holdings
              <br />
              | Reversed party positions
              <br />
              | Fabricated precedents
            </span>
          </div>
        </div>

        <div className="card-brutal">
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'baseline',
              marginBottom: '0.625rem',
            }}
          >
            <h3
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '1.2rem',
                fontWeight: 600,
                textTransform: 'uppercase',
              }}
            >
              Judge Score
            </h3>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--text-muted)' }}>
              WEIGHT: 0.40
            </span>
          </div>
          <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: '0.75rem' }}>
            Judge = normalize(factual_accuracy + completeness, 1-5 to 0-1)
          </div>
          <div style={sectionTextStyle}>
            <strong style={dataLabelStyle}>Panel</strong>
            Three diverse LLM judges: Claude, Gemini, MiniMax.
            Each scores factual accuracy + completeness on a 1-5 Likert scale.
            <br />
            <br />
            <strong style={dataLabelStyle}>What It Catches</strong>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem' }}>
              | Nuanced legal reasoning errors
              <br />
              | Missing key arguments or dissents
              <br />
              | Tone and framing misrepresentation
              <br />
              | Incomplete procedural history
            </span>
          </div>
        </div>

        <div className="card-brutal">
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'baseline',
              marginBottom: '0.625rem',
            }}
          >
            <h3
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '1.2rem',
                fontWeight: 600,
                textTransform: 'uppercase',
              }}
            >
              Coverage Score
            </h3>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--text-muted)' }}>
              WEIGHT: 0.25
            </span>
          </div>
          <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: '0.75rem' }}>
            Coverage = fraction of source sentences semantically covered
          </div>
          <div style={sectionTextStyle}>
            <strong style={dataLabelStyle}>Model</strong>
            all-MiniLM-L6-v2 sentence embeddings.
            Cosine similarity &gt;= 0.55 threshold.
            <br />
            <br />
            <strong style={dataLabelStyle}>What It Catches</strong>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem' }}>
              | Missing key holdings
              <br />
              | Skipped concurrences/dissents
              <br />
              | Dropped procedural details
              <br />
              | Omitted party arguments
            </span>
          </div>
        </div>
      </div>

      <hr className="divider" />

      <h2 style={sectionTitleStyle}>Why Not ROUGE?</h2>

      <div style={{ ...sectionTextStyle, marginBottom: '1rem' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: '1px',
            background: 'var(--border)',
          }}
        >
          <div className="card-brutal">
            <div
              style={{
                color: 'var(--text-muted)',
                fontSize: '0.625rem',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                marginBottom: '0.375rem',
              }}
            >
              ROUGE Failure Modes
            </div>
            <div style={{ lineHeight: 1.9 }}>
              | Rewards word overlap, not meaning
              <br />
              | Cannot detect paraphrased errors
              <br />
              | Misses reversed legal holdings
              <br />
              | Ignores fabricated citations
              <br />
              | High score does not imply faithfulness
            </div>
          </div>
          <div className="card-brutal">
            <div
              style={{
                color: 'var(--text)',
                fontSize: '0.625rem',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                marginBottom: '0.375rem',
              }}
            >
              ∑VAL Approach
            </div>
            <div style={{ lineHeight: 1.9 }}>
              | Semantic entailment (NLI)
              <br />
              | Human-aligned scoring (Judge)
              <br />
              | Meaning-based recall (Coverage)
              <br />
              | Statistical validation (Kappa)
              <br />
              | Multi-pillar signal
            </div>
          </div>
        </div>
      </div>

      <hr className="divider" />

      <h2 style={sectionTitleStyle}>Statistical Methods</h2>

      <div style={sectionTextStyle}>
        <div style={{ marginBottom: '0.75rem', borderLeft: '1px dashed var(--border-strong)', paddingLeft: '0.875rem' }}>
          <strong style={{ color: 'var(--text)' }}>Cohen&apos;s Kappa (κ)</strong> | Primary AI to AI agreement.
          <br />
          Quadratic-weighted for ordinal 1-5 scale. k &gt;= 0.6 = substantial.
        </div>
        <div style={{ marginBottom: '0.75rem', borderLeft: '1px dashed var(--border-strong)', paddingLeft: '0.875rem' }}>
          <strong style={{ color: 'var(--text)' }}>Kendall&apos;s Tau (τ)</strong> | Supplementary rank correlation.
          <br />
          Do judges rank models in the same order? t &gt; 0.7 = strong.
        </div>
        <div style={{ marginBottom: '0.75rem', borderLeft: '1px dashed var(--border-strong)', paddingLeft: '0.875rem' }}>
          <strong style={{ color: 'var(--text)' }}>Bootstrap CIs</strong> | 1,000-iteration resampling.
          <br />
          95% confidence intervals on model scores and significance tests.
        </div>
        <div style={{ borderLeft: '1px dashed var(--border-strong)', paddingLeft: '0.875rem' }}>
          <strong style={{ color: 'var(--text)' }}>Pairwise Significance</strong> | Paired bootstrap.
          <br />
          Tests whether model score differences are statistically significant at α = 0.05.
        </div>
      </div>

      <hr className="divider" />

      <h2 style={sectionTitleStyle}>Dataset</h2>

      <div style={sectionTextStyle}>
        20 Supreme Court opinions spanning constitutional law, administrative law, criminal procedure, and statutory interpretation.
        Cases selected for diversity of length, complexity, and legal domain.
        <br />
        <br />
        <span style={{ color: 'var(--text-muted)' }}>
          Source: Oyez Project / Supreme Court of the United States
        </span>
      </div>
    </>
  );
}
