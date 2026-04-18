import { FileText, Sparkles } from 'lucide-react';

export default function SummaryPanel({ summary, isLoading }) {
  return (
    <div className="glass-panel" style={{ padding: '1.5rem', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
        <Sparkles size={20} color="var(--accent-primary)" />
        <h3 style={{ fontSize: '1.1rem' }}>AI Summary</h3>
      </div>
      
      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '0.5rem' }}>
        {isLoading ? (
          <div className="animate-fade-in" style={{ display: 'flex', gap: '1rem', padding: '1rem', background: 'rgba(15, 23, 42, 0.4)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ flex: 1 }}>
              <div style={{ height: '1rem', background: 'var(--border-light)', borderRadius: '4px', width: '90%', marginBottom: '0.75rem', animation: 'pulse 1.5s infinite ease-in-out' }}></div>
              <div style={{ height: '1rem', background: 'var(--border-light)', borderRadius: '4px', width: '100%', marginBottom: '0.75rem', animation: 'pulse 1.5s infinite ease-in-out 0.2s' }}></div>
              <div style={{ height: '1rem', background: 'var(--border-light)', borderRadius: '4px', width: '80%', animation: 'pulse 1.5s infinite ease-in-out 0.4s' }}></div>
            </div>
          </div>
        ) : summary ? (
          <div className="animate-fade-in" style={{ 
            fontSize: '0.95rem', 
            color: 'var(--text-primary)',
            background: 'rgba(15, 23, 42, 0.4)',
            padding: '1.5rem',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-light)'
          }}>
            <div dangerouslySetInnerHTML={{ __html: formatSummary(summary) }} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }} />
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
            <FileText size={48} style={{ opacity: 0.2, marginBottom: '1rem' }} />
            <p>Upload a file to see its summary</p>
          </div>
        )}
      </div>
      
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        .summary-bullet {
          position: relative;
          padding-left: 1.5rem;
        }
        .summary-bullet::before {
          content: '•';
          position: absolute;
          left: 0.5rem;
          color: var(--accent-primary);
          font-weight: bold;
        }
      `}</style>
    </div>
  );
}

// Simple formatter to parse typical markdown-style bullets from LLM into styled divs
function formatSummary(text) {
  if (!text) return '';
  return text.split('\n')
    .filter(line => line.trim().length > 0)
    .map(line => {
      let cleanLine = line.replace(/^-\s*/, '').replace(/^\*\s*/, '').replace(/^\d+\.\s*/, '');
      cleanLine = cleanLine.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      return `<div class="summary-bullet">${cleanLine}</div>`;
    })
    .join('');
}
