import './globals.css';
import Navigation from './components/Navigation';
import AsciiParticles from './components/AsciiParticles';

export const metadata = {
  title: '∑VAL — AI Summarization Faithfulness Benchmark',
  description:
    'A multi-pillar benchmark for evaluating the faithfulness of AI-generated legal summaries. Evaluating Supreme Court opinion summarization across NLI, LLM-as-Judge, and semantic coverage.',
  keywords: ['AI benchmark', 'summarization', 'faithfulness', 'NLI', 'legal AI', 'SCAI 2026'],
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <AsciiParticles />
        <img src="/lady-justice.png" alt="" className="watermark" />
        <div className="app-container">
          <Navigation />
          <main className="main-content">{children}</main>
          <footer className="footer">
            ∑VAL &mdash; SCAI Hackathon 2026 &mdash; Duke University
          </footer>
        </div>
      </body>
    </html>
  );
}
