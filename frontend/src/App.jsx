import { useState, useRef } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { Bot, FileWarning } from 'lucide-react';
import FileUploader from './components/FileUploader';
import SummaryPanel from './components/SummaryPanel';
import MediaPlayer from './components/MediaPlayer';
import ChatBox from './components/ChatBox';

import * as api from './api';

export default function App() {
  const [fileState, setFileState] = useState({
    id: null,
    status: 'idle', // idle, uploading, processing, ready, error
    type: null,
    name: null,
    url: null
  });
  
  const [summary, setSummary] = useState(null);
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);
  
  const [messages, setMessages] = useState([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  
  const mediaRef = useRef(null);

  // Handle file upload and start polling
  const handleUploadComplete = async (file) => {
    try {
      setFileState(prev => ({ ...prev, status: 'uploading', name: file.name }));
      
      const res = await api.uploadFile(file);
      const newFileId = res.file_id;
      
      setFileState({
        id: newFileId,
        status: 'processing',
        type: res.file_type,
        name: file.name,
        url: null
      });
      
      toast.success('File uploaded successfully! Processing started.', { icon: '🚀' });
      
      // Start polling for "ready" state
      pollStatus(newFileId);
      
    } catch (err) {
      console.error(err);
      setFileState(prev => ({ ...prev, status: 'error' }));
      toast.error(err.response?.data?.detail || 'Failed to upload file.');
    }
  };

  const pollStatus = async (fileId) => {
    const interval = setInterval(async () => {
      try {
        const res = await api.checkStatus(fileId);
        
        if (res.status === 'ready') {
          clearInterval(interval);
          setFileState(prev => ({ ...prev, status: 'ready' }));
          toast.success('File is ready! You can now ask questions.', { duration: 4000 });
          
          // Once ready, fetch the summary
          fetchSummary(fileId);
        } else if (res.status === 'error') {
          clearInterval(interval);
          setFileState(prev => ({ ...prev, status: 'error' }));
          toast.error(res.error || 'Error processing the file. Please try again.');
        }
      } catch (err) {
        clearInterval(interval);
        console.error("Polling error", err);
      }
    }, 3000); // Check every 3 seconds
  };

  const fetchSummary = async (fileId) => {
    setIsSummaryLoading(true);
    try {
      const res = await api.getSummary(fileId);
      setSummary(res.summary);
    } catch (err) {
      console.error(err);
      toast.error('Failed to generate summary.');
    } finally {
      setIsSummaryLoading(false);
    }
  };

  const handleSendMessage = async (text) => {
    if (!fileState.id || fileState.status !== 'ready') {
      toast.error('Please wait for the file to be ready.');
      return;
    }

    // Attempt to parse out some local state to immediately show user the message
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setIsChatLoading(true);

    try {
      const res = await api.askQuestion(fileState.id, text);
      
      // If we don't have media url yet (FastAPI ask request returns it), set it
      if (!fileState.url && res.media_url) {
        setFileState(prev => ({ ...prev, url: res.media_url }));
      }
      
      setMessages(prev => [...prev, { 
        role: 'ai', 
        content: res.answer,
        timestamp: res.timestamp // Seconds if audio/video
      }]);
    } catch (err) {
      console.error(err);
      toast.error('Failed to get an answer.');
      setMessages(prev => [...prev, { 
        role: 'ai', 
        content: "Sorry, I encountered an error. Please try again."
      }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handlePlayTimestamp = (timeInSeconds) => {
    if (mediaRef.current) {
      mediaRef.current.seekTo(timeInSeconds);
    } else {
      toast.error('Media player not available.');
    }
  };

  return (
    <>
      <Toaster position="top-right" toastOptions={{
        style: { background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-light)' }
      }}/>
      
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '2rem', display: 'flex', flexDirection: 'column', gap: '2rem', height: '100vh' }}>
        
        {/* Header */}
        <header style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ background: 'var(--accent-glow)', padding: '0.75rem', borderRadius: 'var(--radius-lg)' }}>
            <Bot size={28} color="var(--accent-primary)" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.75rem', margin: 0, textShadow: '0 0 20px rgba(59,130,246,0.3)' }}>Anant <span style={{ color: 'var(--accent-primary)' }}>Q&A</span></h1>
            <p style={{ color: 'var(--text-muted)', margin: 0 }}>AI-Powered Insight for Documents & Media</p>
          </div>
        </header>

        {/* Main Interface */}
        <main style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 350px) 1fr', gap: '2rem', flex: 1, minHeight: 0 }}>
          
          {/* Left Sidebar: Upload & Summary */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', height: '100%', overflowY: 'auto' }}>
            <FileUploader 
              onUploadComplete={handleUploadComplete} 
              isUploading={['uploading', 'processing'].includes(fileState.status)} 
            />
            
            {fileState.status === 'error' && (
              <div className="glass-panel" style={{ padding: '1rem', display: 'flex', gap: '0.75rem', color: 'var(--error)', borderColor: 'rgba(239, 68, 68, 0.3)' }}>
                <FileWarning size={20} />
                <p style={{ fontSize: '0.9rem' }}>There was an error processing your file. Please try a different one.</p>
              </div>
            )}
            
            <div style={{ flex: 1, minHeight: '300px' }}>
              <SummaryPanel summary={summary} isLoading={isSummaryLoading || fileState.status === 'processing'} />
            </div>
          </div>

          {/* Right Main Area: Chat & Media Player */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', height: '100%', minHeight: 0 }}>
            
            {/* Show Media Player if it's Audio/Video and file is ready */}
            {fileState.status === 'ready' && ['audio', 'video'].includes(fileState.type) && (
              <div style={{ flexShrink: 0 }}>
                 <MediaPlayer ref={mediaRef} fileUrl={fileState.url} fileType={fileState.type} fileName={fileState.name} />
              </div>
            )}
            
            {/* Chat Area */}
            <div style={{ flex: 1, minHeight: 0, position: 'relative' }}>
              {fileState.status === 'idle' && (
                <div style={{ position: 'absolute', inset: 0, zIndex: 10, background: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 'var(--radius-lg)' }}>
                  <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center' }}>
                    <h3 style={{ marginBottom: '0.5rem' }}>Awaiting File</h3>
                    <p style={{ color: 'var(--text-muted)' }}>Upload a document or media file to start chatting.</p>
                  </div>
                </div>
              )}
              
              <ChatBox 
                messages={messages} 
                onSendMessage={handleSendMessage} 
                isLoading={isChatLoading || fileState.status === 'processing'}
                onPlayTimestamp={handlePlayTimestamp}
              />
            </div>
            
          </div>
        </main>
      </div>
    </>
  );
}
