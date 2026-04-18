import { useState, useRef } from 'react';
import { UploadCloud, Loader } from 'lucide-react';

export default function FileUploader({ onUploadComplete, isUploading }) {
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const handleDrag = (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (event.type === 'dragenter' || event.type === 'dragover') {
      setDragActive(true);
    } else if (event.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (event) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(false);
    if (event.dataTransfer.files && event.dataTransfer.files[0]) {
      onUploadComplete(event.dataTransfer.files[0]);
    }
  };

  const handleChange = (event) => {
    event.preventDefault();
    if (event.target.files && event.target.files[0]) {
      onUploadComplete(event.target.files[0]);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '1.6rem', textAlign: 'center', background: 'linear-gradient(180deg, rgba(255,255,255,0.03), rgba(8,17,31,0.04))' }}>
      <span style={{ display: 'inline-flex', padding: '0.35rem 0.75rem', borderRadius: '999px', background: 'rgba(255,255,255,0.06)', color: 'var(--text-secondary)', fontSize: '0.78rem', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '0.9rem' }}>
        Upload zone
      </span>
      <h3 style={{ marginBottom: '0.6rem' }}>Upload Document or Media</h3>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>Supports PDF, MP4, MP3, WAV, WEBM</p>

      <form
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        style={{
          border: `2px dashed ${dragActive ? 'var(--accent-primary)' : 'var(--border-light)'}`,
          background: dragActive
            ? 'linear-gradient(135deg, rgba(255, 126, 95, 0.12), rgba(56, 189, 248, 0.12))'
            : 'linear-gradient(180deg, rgba(20, 33, 58, 0.88), rgba(10, 18, 34, 0.92))',
          borderRadius: 'var(--radius-lg)',
          padding: '3rem 2rem',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          position: 'relative',
          boxShadow: dragActive ? '0 18px 38px rgba(8, 17, 31, 0.22)' : 'none',
        }}
        onClick={() => fileInputRef.current?.click()}
      >
        <input ref={fileInputRef} type="file" accept=".pdf,audio/*,video/*" onChange={handleChange} style={{ display: 'none' }} />

        {isUploading ? (
          <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
            <Loader size={40} className="spinner" style={{ animation: 'spin 1s linear infinite', color: 'var(--accent-primary)' }} />
            <p style={{ fontWeight: '500' }}>
              Processing your file...
              <br />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Extracting text and generating embeddings.</span>
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
            <UploadCloud size={48} color={dragActive ? 'var(--accent-primary)' : 'var(--text-secondary)'} />
            <div>
              <p style={{ fontWeight: '500', color: 'var(--text-primary)' }}>Click to upload or drag and drop</p>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginTop: '0.35rem' }}>Your file gets summarized and becomes searchable in chat.</p>
            </div>
          </div>
        )}
      </form>

      <style>{`
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
