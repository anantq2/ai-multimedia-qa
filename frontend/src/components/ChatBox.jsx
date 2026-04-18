import { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, PlayCircle } from 'lucide-react';

export default function ChatBox({ messages, onSendMessage, isLoading, onPlayTimestamp, fileName, isReady }) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input);
    setInput('');
  };

  const formatTime = (seconds) => {
    if (seconds === null || seconds === undefined) return '';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const statusLabel = isReady ? fileName || 'Ready to chat' : 'Upload a file to begin';

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'linear-gradient(180deg, rgba(255,255,255,0.03), rgba(8,17,31,0.04))' }}>
      <div style={{ padding: '1.15rem 1.5rem', borderBottom: '1px solid var(--border-light)', background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.1), rgba(255, 126, 95, 0.1))', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <p style={{ fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--text-secondary)', margin: '0 0 0.3rem 0' }}>Document Q&amp;A</p>
          <h3 style={{ fontSize: '1.1rem', margin: 0 }}>Ask about your content</h3>
        </div>

        <span style={{ padding: '0.45rem 0.8rem', borderRadius: '999px', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)', color: 'var(--text-secondary)', maxWidth: '100%', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {statusLabel}
        </span>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem', background: 'linear-gradient(180deg, rgba(10,18,34,0.2), rgba(8,17,31,0.05))' }}>
        {messages.length === 0 ? (
          <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--text-muted)', maxWidth: '26rem' }}>
            <div style={{ width: '4.5rem', height: '4.5rem', margin: '0 auto 1rem auto', borderRadius: '1.5rem', display: 'grid', placeItems: 'center', background: 'linear-gradient(135deg, rgba(255, 126, 95, 0.24), rgba(56, 189, 248, 0.24))', border: '1px solid rgba(255,255,255,0.08)' }}>
              <Bot size={34} style={{ opacity: 0.9 }} />
            </div>
            <p style={{ color: 'var(--text-primary)', marginBottom: '0.35rem' }}>Ask anything about the uploaded document</p>
            <p style={{ fontSize: '0.92rem' }}>Questions, facts, summaries, and timestamps all work better from here.</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className="animate-fade-in" style={{ display: 'flex', gap: '1rem', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: msg.role === 'user'
                    ? 'linear-gradient(135deg, rgba(255, 126, 95, 0.92), rgba(251, 191, 36, 0.92))'
                    : 'linear-gradient(135deg, rgba(56, 189, 248, 0.92), rgba(14, 165, 233, 0.92))',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                {msg.role === 'user' ? <User size={18} color="white" /> : <Bot size={18} color="white" />}
              </div>

              <div
                style={{
                  background: msg.role === 'user'
                    ? 'linear-gradient(135deg, rgba(255, 126, 95, 0.16), rgba(251, 191, 36, 0.12))'
                    : 'linear-gradient(135deg, rgba(20, 33, 58, 0.94), rgba(12, 21, 38, 0.96))',
                  padding: '1rem 1.25rem',
                  borderRadius: 'var(--radius-lg)',
                  borderTopRightRadius: msg.role === 'user' ? 0 : 'var(--radius-lg)',
                  borderTopLeftRadius: msg.role === 'ai' ? 0 : 'var(--radius-lg)',
                  maxWidth: '85%',
                  border: msg.role === 'user' ? '1px solid rgba(255, 190, 110, 0.18)' : '1px solid var(--border-light)',
                  boxShadow: '0 14px 28px rgba(8, 17, 31, 0.12)',
                }}
              >
                <p style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.95rem', overflowWrap: 'anywhere' }}>{msg.content}</p>

                {msg.role === 'ai' && msg.timestamp !== null && msg.timestamp !== undefined && (
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => onPlayTimestamp(msg.timestamp)}
                    style={{ marginTop: '1rem', padding: '0.4rem 0.8rem', fontSize: '0.85rem', borderColor: 'var(--accent-primary)', color: 'var(--accent-primary)' }}
                  >
                    <PlayCircle size={16} />
                    Play relevant segment ({formatTime(msg.timestamp)})
                  </button>
                )}
              </div>
            </div>
          ))
        )}

        {isLoading && (
          <div className="animate-fade-in" style={{ display: 'flex', gap: '1rem' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.92), rgba(14, 165, 233, 0.92))', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Bot size={18} color="white" />
            </div>
            <div style={{ background: 'linear-gradient(135deg, rgba(20, 33, 58, 0.94), rgba(12, 21, 38, 0.96))', padding: '1rem 1.25rem', borderRadius: '0 var(--radius-lg) var(--radius-lg) var(--radius-lg)', border: '1px solid var(--border-light)', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <div className="typing-dot" style={{ animationDelay: '0s' }}></div>
              <div className="typing-dot" style={{ animationDelay: '0.2s' }}></div>
              <div className="typing-dot" style={{ animationDelay: '0.4s' }}></div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div style={{ padding: '1rem 1.5rem', borderTop: '1px solid var(--border-light)', background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.08), rgba(255, 126, 95, 0.08))' }}>
        <form onSubmit={handleSubmit} style={{ position: 'relative' }}>
          <input
            type="text"
            className="input-field"
            placeholder="Type your question..."
            value={input}
            onChange={(event) => setInput(event.target.value)}
            disabled={isLoading}
            style={{ paddingRight: '3rem', height: '50px' }}
          />

          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            style={{
              position: 'absolute',
              right: '8px',
              top: '8px',
              width: '34px',
              height: '34px',
              borderRadius: '4px',
              background: input.trim() && !isLoading ? 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))' : 'transparent',
              color: input.trim() && !isLoading ? 'white' : 'var(--text-muted)',
              border: 'none',
              cursor: input.trim() && !isLoading ? 'pointer' : 'not-allowed',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s ease',
            }}
          >
            <Send size={18} />
          </button>
        </form>
      </div>

      <style>{`
        .typing-dot {
          width: 8px;
          height: 8px;
          background-color: var(--accent-primary);
          border-radius: 50%;
          animation: typing 1.4s infinite ease-in-out both;
        }

        @keyframes typing {
          0%, 80%, 100% { transform: scale(0); opacity: 0.5; }
          40% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
