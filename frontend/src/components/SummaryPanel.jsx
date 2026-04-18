import { useEffect, useState } from 'react';
import { Expand, FileText, Sparkles, X } from 'lucide-react';

export default function SummaryPanel({ summary, isLoading }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const summaryItems = formatSummary(summary);
  const hasSummary = summaryItems.length > 0;

  useEffect(() => {
    if (!hasSummary) {
      setIsExpanded(false);
    }
  }, [hasSummary]);

  useEffect(() => {
    if (!isExpanded) return undefined;

    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        setIsExpanded(false);
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isExpanded]);

  return (
    <>
      <div className="glass-panel summary-panel">
        <div className="summary-panel-header">
          <div className="summary-title-wrap">
            <div className="summary-icon-shell">
              <Sparkles size={18} color="var(--text-primary)" />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', margin: 0 }}>AI Summary</h3>
              <p className="summary-subtitle">{hasSummary ? 'Quick scan for the uploaded content' : 'A readable summary will appear here'}</p>
            </div>
          </div>

          {hasSummary && (
            <button type="button" className="summary-action-btn" onClick={() => setIsExpanded(true)}>
              <Expand size={16} />
              Expand
            </button>
          )}
        </div>

        <div className="summary-scroll-shell">
          {isLoading ? (
            <div className="animate-fade-in summary-loading-card">
              <div style={{ flex: 1 }}>
                <div style={{ height: '1rem', background: 'var(--border-light)', borderRadius: '4px', width: '90%', marginBottom: '0.75rem', animation: 'pulse 1.5s infinite ease-in-out' }}></div>
                <div style={{ height: '1rem', background: 'var(--border-light)', borderRadius: '4px', width: '100%', marginBottom: '0.75rem', animation: 'pulse 1.5s infinite ease-in-out 0.2s' }}></div>
                <div style={{ height: '1rem', background: 'var(--border-light)', borderRadius: '4px', width: '80%', animation: 'pulse 1.5s infinite ease-in-out 0.4s' }}></div>
              </div>
            </div>
          ) : hasSummary ? (
            <div className="animate-fade-in summary-card-body summary-card-preview">
              <span className="summary-highlight">Quick read</span>
              <div className="summary-list">{summaryItems}</div>
            </div>
          ) : (
            <div className="summary-empty-state">
              <FileText size={48} style={{ opacity: 0.22, marginBottom: '1rem' }} />
              <p>Upload a file to see its summary</p>
            </div>
          )}
        </div>
      </div>

      {isExpanded && hasSummary && (
        <div className="summary-modal-backdrop" onClick={() => setIsExpanded(false)}>
          <div className="glass-panel summary-modal" role="dialog" aria-modal="true" aria-label="Expanded AI summary" onClick={(event) => event.stopPropagation()}>
            <div className="summary-modal-header">
              <div>
                <p className="summary-subtitle" style={{ marginBottom: '0.25rem' }}>Expanded view</p>
                <h3 style={{ margin: 0, fontSize: '1.3rem' }}>Full AI Summary</h3>
              </div>
              <button type="button" className="summary-close-btn" onClick={() => setIsExpanded(false)}>
                <X size={18} />
              </button>
            </div>
            <div className="summary-modal-body">
              <div className="summary-card-body">
                <span className="summary-highlight">Readable mode</span>
                <div className="summary-list">{summaryItems}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        .summary-panel {
          padding: 1.35rem;
          height: 100%;
          display: flex;
          flex-direction: column;
          background:
            radial-gradient(circle at top right, rgba(56, 189, 248, 0.12), transparent 24%),
            linear-gradient(180deg, rgba(255, 255, 255, 0.02), rgba(8, 17, 31, 0.02));
        }

        .summary-panel-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
          margin-bottom: 1rem;
        }

        .summary-title-wrap {
          display: flex;
          align-items: center;
          gap: 0.85rem;
        }

        .summary-icon-shell {
          width: 2.5rem;
          height: 2.5rem;
          border-radius: 0.9rem;
          display: grid;
          place-items: center;
          background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
          box-shadow: 0 10px 24px rgba(8, 17, 31, 0.3);
        }

        .summary-subtitle {
          margin: 0.2rem 0 0;
          color: var(--text-secondary);
          font-size: 0.86rem;
        }

        .summary-action-btn,
        .summary-close-btn {
          border: 1px solid rgba(255, 255, 255, 0.12);
          background: rgba(255, 255, 255, 0.05);
          color: var(--text-primary);
          border-radius: 0.85rem;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 0.45rem;
          transition: transform var(--transition-fast), background var(--transition-fast), border-color var(--transition-fast);
        }

        .summary-action-btn {
          padding: 0.75rem 0.95rem;
          white-space: nowrap;
        }

        .summary-close-btn {
          width: 2.6rem;
          height: 2.6rem;
        }

        .summary-action-btn:hover,
        .summary-close-btn:hover {
          transform: translateY(-1px);
          background: rgba(255, 255, 255, 0.09);
          border-color: rgba(255, 255, 255, 0.18);
        }

        .summary-scroll-shell {
          flex: 1;
          min-height: 0;
          overflow-y: auto;
          padding-right: 0.25rem;
        }

        .summary-loading-card,
        .summary-card-body {
          display: flex;
          flex-direction: column;
          gap: 1rem;
          padding: 1.15rem;
          border-radius: 1.15rem;
          border: 1px solid var(--border-light);
          background: linear-gradient(180deg, rgba(20, 33, 58, 0.95), rgba(10, 18, 34, 0.96));
        }

        .summary-highlight {
          align-self: flex-start;
          padding: 0.35rem 0.7rem;
          border-radius: 999px;
          font-size: 0.75rem;
          font-weight: 600;
          color: #ffe7d6;
          background: linear-gradient(135deg, rgba(255, 126, 95, 0.3), rgba(56, 189, 248, 0.2));
          border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .summary-list {
          display: flex;
          flex-direction: column;
          gap: 0.9rem;
          font-size: 0.96rem;
        }

        .summary-bullet {
          position: relative;
          padding-left: 1.4rem;
          line-height: 1.75;
          color: var(--text-primary);
        }

        .summary-bullet::before {
          content: "";
          position: absolute;
          left: 0.1rem;
          top: 0.7rem;
          width: 0.48rem;
          height: 0.48rem;
          border-radius: 999px;
          background: linear-gradient(135deg, var(--accent-secondary), var(--accent-primary));
          box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.08);
        }

        .summary-empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 100%;
          color: var(--text-muted);
          text-align: center;
          padding: 1rem;
        }

        .summary-modal-backdrop {
          position: fixed;
          inset: 0;
          z-index: 100;
          padding: 1.25rem;
          background: rgba(6, 11, 22, 0.66);
          backdrop-filter: blur(10px);
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .summary-modal {
          width: min(900px, 100%);
          max-height: calc(100vh - 2.5rem);
          padding: 1.2rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
          background:
            radial-gradient(circle at top right, rgba(255, 126, 95, 0.12), transparent 26%),
            linear-gradient(180deg, rgba(17, 24, 39, 0.96), rgba(8, 17, 31, 0.98));
        }

        .summary-modal-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
        }

        .summary-modal-body {
          overflow-y: auto;
          padding-right: 0.25rem;
        }

        @media (max-width: 640px) {
          .summary-panel-header {
            flex-direction: column;
            align-items: stretch;
          }

          .summary-action-btn {
            justify-content: center;
          }
        }
      `}</style>
    </>
  );
}

function formatSummary(text) {
  if (!text) return [];

  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, lineIndex) => {
      const cleanLine = line.replace(/^[-*]\s*/, '').replace(/^\d+\.\s*/, '').trim();
      const parts = cleanLine.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);

      return (
        <div key={`${lineIndex}-${cleanLine.slice(0, 24)}`} className="summary-bullet">
          {parts.map((part, partIndex) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return <strong key={`${lineIndex}-${partIndex}`}>{part.slice(2, -2)}</strong>;
            }

            return <span key={`${lineIndex}-${partIndex}`}>{part}</span>;
          })}
        </div>
      );
    });
}
