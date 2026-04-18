import { useState, useRef } from 'react';
import { UploadCloud, File, Loader } from 'lucide-react';

export default function FileUploader({ onUploadComplete, isUploading }) {
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onUploadComplete(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      onUploadComplete(e.target.files[0]);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center' }}>
      <h3 style={{ marginBottom: '1rem' }}>Upload Document or Media</h3>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
        Supports PDF, MP4, MP3, WAV, WEBM
      </p>

      <form 
        onDragEnter={handleDrag} 
        onDragLeave={handleDrag} 
        onDragOver={handleDrag} 
        onDrop={handleDrop}
        style={{
          border: `2px dashed ${dragActive ? 'var(--accent-primary)' : 'var(--border-light)'}`,
          backgroundColor: dragActive ? 'rgba(59, 130, 246, 0.05)' : 'rgba(15, 23, 42, 0.4)',
          borderRadius: 'var(--radius-lg)',
          padding: '3rem 2rem',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          position: 'relative'
        }}
        onClick={() => fileInputRef.current?.click()}
      >
        <input 
          ref={fileInputRef}
          type="file" 
          accept=".pdf,audio/*,video/*"
          onChange={handleChange}
          style={{ display: 'none' }}
        />
        
        {isUploading ? (
          <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
            <Loader size={40} className="spinner" style={{ animation: 'spin 1s linear infinite', color: 'var(--accent-primary)' }} />
            <p style={{ fontWeight: '500' }}>Processing your file... <br/><span style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>Extracting text and generating embeddings.</span></p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
            <UploadCloud size={48} color={dragActive ? 'var(--accent-primary)' : 'var(--text-secondary)'} />
            <div>
              <p style={{ fontWeight: '500' }}>Click to upload or drag and drop</p>
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
