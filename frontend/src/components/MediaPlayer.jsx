import { forwardRef, useImperativeHandle, useRef } from 'react';
import { Film, Music } from 'lucide-react';

const MediaPlayer = forwardRef(({ fileUrl, fileType, fileName }, ref) => {
  const internalRef = useRef(null);

  // In Docker: nginx proxies /media/ to backend, so relative URL works.
  // In local dev (Vite on :5173): hit backend directly on :8000.
  const isDev = window.location.port === '5173';
  const mediaBase = isDev
    ? `http://${window.location.hostname || '127.0.0.1'}:8000`
    : '';

  useImperativeHandle(ref, () => ({
    seekTo: (timeInSeconds) => {
      if (internalRef.current) {
        internalRef.current.currentTime = timeInSeconds;
        internalRef.current.play();
      }
    }
  }));

  if (!fileUrl) return null;

  const isVideo = fileType === 'video';
  const isAudio = fileType === 'audio';
  
  const fullUrl = `${mediaBase}${fileUrl}`;

  return (
    <div className="glass-panel" style={{ overflow: 'hidden' }}>
      <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-light)', display: 'flex', alignItems: 'center', gap: '0.75rem', backgroundColor: 'rgba(15, 23, 42, 0.4)' }}>
        {isVideo ? <Film size={18} color="var(--accent-primary)" /> : <Music size={18} color="var(--accent-primary)" />}
        <span style={{ fontSize: '0.9rem', fontWeight: '500', display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {fileName || 'Media Player'}
        </span>
      </div>
      
      <div style={{ background: '#000', width: '100%', display: 'flex', justifyContent: 'center' }}>
        {isVideo && (
          <video 
            ref={internalRef}
            src={fullUrl} 
            controls 
            style={{ width: '100%', maxHeight: '400px', outline: 'none' }} 
          />
        )}
        
        {isAudio && (
          <div style={{ width: '100%', padding: '2rem' }}>
            <audio 
              ref={internalRef}
              src={fullUrl} 
              controls 
              style={{ width: '100%', outline: 'none' }} 
            />
          </div>
        )}
      </div>
    </div>
  );
});

export default MediaPlayer;
