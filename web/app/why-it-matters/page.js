import Link from 'next/link';
import styles from './page.module.css';
import { getSummaryStats, getScoreSpreadSummary } from '../lib/data';

function toPercent(score) {
  if (score == null) return '—';
  return `${Math.round(score * 100)}%`;
}

function asciiBar(score, width = 18) {
  if (score == null) return '—';
  const filled = Math.max(0, Math.min(width, Math.round(score * width)));
  return `${'█'.repeat(filled)}${'░'.repeat(width - filled)}`;
}

function formatGeneratedDate(value) {
  if (!value) return 'Current static benchmark snapshot';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return 'Current static benchmark snapshot';
  return parsed.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export default function WhyItMattersPage() {
  const stats = getSummaryStats();
  const spread = getScoreSpreadSummary();

  const scoreRows = [
    { label: 'Top score', value: spread.topScore },
    { label: 'Middle score', value: spread.medianScore },
    { label: 'Lower score', value: spread.bottomScore },
  ];

  const pillarRows = [
    {
      label: 'Truth check (NLI)',
      detail: 'Catches statements that conflict with the source.',
      weight: 0.35,
    },
    {
      label: 'Human-style review (Judge)',
      detail: 'Rates factual accuracy and completeness.',
      weight: 0.4,
    },
    {
      label: 'Coverage check',
      detail: 'Checks whether key source points were included.',
      weight: 0.25,
    },
  ];

  return (
    <>
      <div className="section-header">
        <h1 className="section-title">Why This Matters</h1>
        <p className="section-subtitle">
          A plain-language guide to what ∑VAL does, why it matters, and how to use it in under 3 minutes.
        </p>
      </div>

      <hr className="divider" />

      <section className={styles.sectionBlock}>
        <h2 className={styles.chartTitle}>What This Is, In One Minute</h2>
        <p className={styles.heroLead}>
          ∑VAL is a benchmark that checks whether an AI summary is faithful to the original source.
          In other words: did the summary keep the facts straight, include the important points, and avoid making things up?
          This is especially important for legal text, but the same idea matters for news, policy, and medical-style summaries.
        </p>
      </section>

      <hr className="divider" />

      <section className={styles.sectionBlock}>
        <h2 className={styles.chartTitle}>Why People Should Care</h2>
        <p className={styles.sectionSubtitle}>
          A summary can sound confident and still be wrong. Here is where that can hurt in everyday life:
        </p>
        <div className={styles.cardsGrid}>
          <article className={styles.card}>
            <h3 className={styles.cardTitle}>What Can Go Wrong With AI Summaries</h3>
            <p className={styles.cardText}>
              A summary can flip who won a case, drop key exceptions, or blend two different ideas into one.
              If you only read the summary, you can walk away with the wrong conclusion.
            </p>
          </article>
          <article className={styles.card}>
            <h3 className={styles.cardTitle}>What ∑VAL Checks</h3>
            <p className={styles.cardText}>
              ∑VAL checks contradictions, checks whether important details were covered, and adds an additional
              judge-style score for factual quality and completeness.
            </p>
          </article>
          <article className={styles.card}>
            <h3 className={styles.cardTitle}>What A Higher Score Means For You</h3>
            <p className={styles.cardText}>
              A higher score means lower risk of misleading summaries, not guaranteed perfection.
              It is a confidence signal that helps you choose safer models.
            </p>
          </article>
        </div>
      </section>

      <hr className="divider" />

      <section className={styles.sectionBlock}>
        <h2 className={styles.chartTitle}>How ∑VAL Checks Summaries</h2>
        <p className={styles.sectionSubtitle}>
          We use three checks so one weak metric does not decide everything.
        </p>
        <div className={styles.pillarsGrid}>
          {pillarRows.map((pillar) => (
            <article key={pillar.label} className={styles.card}>
              <div className={styles.pillarWeight}>Weight {Math.round(pillar.weight * 100)}%</div>
              <h3 className={styles.cardTitle}>{pillar.label}</h3>
              <p className={styles.cardText}>{pillar.detail}</p>
              <div className={styles.asciiValue}>{asciiBar(pillar.weight)}</div>
            </article>
          ))}
        </div>
      </section>

      <hr className="divider" />

      <section className={styles.sectionBlock}>
        <h2 className={styles.chartTitle}>What Scores Mean</h2>
        <p className={styles.sectionSubtitle}>
          This is a simple snapshot of spread in this benchmark version ({stats.numModels} models, {stats.numCases} cases).
        </p>
        <div className={styles.chartWrap}>
          {spread.hasData ? (
            <>
              {scoreRows.map((row) => (
                <div className={styles.chartRow} key={row.label}>
                  <span className={styles.chartLabel}>{row.label}</span>
                  <div className={styles.barTrack}>
                    <div className={styles.barFill} style={{ width: `${Math.max(0, (row.value || 0) * 100)}%` }} />
                  </div>
                  <span className={styles.chartValue}>{toPercent(row.value)}</span>
                </div>
              ))}
              <div className={styles.callout}>
                Score spread in this run: <strong>{toPercent(spread.spread)}</strong>.
                Larger spread means model choice has a bigger practical impact.
              </div>
            </>
          ) : (
            <div className={styles.callout}>
              We could not load score data for this view yet.
              You can still browse methodology and reliability details while data is refreshed.
            </div>
          )}
        </div>
      </section>

      <hr className="divider" />

      <section className={styles.sectionBlock}>
        <h2 className={styles.chartTitle}>How To Use This Site In 30 Seconds</h2>
        <div className={styles.quickLinksGrid}>
          <Link href="/" className={styles.quickLinkCard}>
            <div className={styles.quickLinkTitle}>See Who Performs Best</div>
            <p className={styles.quickLinkText}>
              Start on Leaderboard to compare overall score confidence signals.
            </p>
          </Link>
          <Link href="/explore" className={styles.quickLinkCard}>
            <div className={styles.quickLinkTitle}>Compare Real Cases</div>
            <p className={styles.quickLinkText}>
              Use Explorer to see per-case model differences and where mistakes happen.
            </p>
          </Link>
          <Link href="/methodology" className={styles.quickLinkCard}>
            <div className={styles.quickLinkTitle}>Understand The Method</div>
            <p className={styles.quickLinkText}>
              Method explains what each score means and why all three are combined.
            </p>
          </Link>
          <Link href="/reliability" className={styles.quickLinkCard}>
            <div className={styles.quickLinkTitle}>Check Reliability</div>
            <p className={styles.quickLinkText}>
              Judges shows agreement and consistency so scores are not from one viewpoint.
            </p>
          </Link>
        </div>
      </section>

      <hr className="divider" />

      <section className={styles.sectionBlock}>
        <h2 className={styles.chartTitle}>Quick FAQ</h2>
        <div className={styles.faqList}>
          <article className={styles.faqItem}>
            <h3 className={styles.faqQ}>Does this tell me which model is always right?</h3>
            <p className={styles.faqA}>
              No. It tells you which models are more reliable on this benchmark.
              Treat it as decision support, not absolute truth.
            </p>
          </article>
          <article className={styles.faqItem}>
            <h3 className={styles.faqQ}>Why not use one single score?</h3>
            <p className={styles.faqA}>
              One metric can miss important failures. Combining multiple checks reduces blind spots.
            </p>
          </article>
          <article className={styles.faqItem}>
            <h3 className={styles.faqQ}>Can non-lawyers use this?</h3>
            <p className={styles.faqA}>
              Yes. You do not need legal or technical background to use the rankings and case explorer as
              confidence signals for safer summaries.
            </p>
          </article>
          <article className={styles.faqItem}>
            <h3 className={styles.faqQ}>How recent is this version?</h3>
            <p className={styles.faqA}>
              Current data snapshot: {formatGeneratedDate(stats.generatedAt)}.
            </p>
          </article>
        </div>
      </section>
    </>
  );
}
