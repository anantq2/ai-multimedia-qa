import { useState, useRef, useEffect } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { Bot, FileWarning, LogOut } from 'lucide-react';
import FileUploader from './components/FileUploader';
import SummaryPanel from './components/SummaryPanel';
import MediaPlayer from './components/MediaPlayer';
import ChatBox from './components/ChatBox';
import AuthScreen from './components/AuthScreen';
import './App.css';

import * as api from './api';

export default function App() {
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('auth_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const [fileState, setFileState] = useState({
    id: null,
    status: 'idle',
    type: null,
    name: null,
    url: null,
  });

  const [summary, setSummary] = useState(null);
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);

  const [messages, setMessages] = useState([]);
  const [isChatLoading, setIsChatLoading] = useState(false);

  const mediaRef = useRef(null);
  const pollingIntervalRef = useRef(null); // Ref for interval cleanup
  
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    };
  }, []);

  const handleUploadComplete = async (file) => {
    try {
      setSummary(null);
      setMessages([]);
      setFileState((prev) => ({ ...prev, status: 'uploading', name: file.name, url: null }));

      const res = await api.uploadFile(file);
      const newFileId = res.file_id;

      setFileState({
        id: newFileId,
        status: 'processing',
        type: res.file_type,
        name: file.name,
        url: null,
      });

      toast.success('File uploaded successfully! Processing started.');
      pollStatus(newFileId);
    } catch (err) {
      console.error(err);
      setFileState((prev) => ({ ...prev, status: 'error' }));
      toast.error(err.response?.data?.detail || 'Failed to upload file.');
    }
  };

  const pollStatus = async (fileId) => {
    if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const res = await api.checkStatus(fileId);

        if (res.status === 'ready') {
          clearInterval(pollingIntervalRef.current);
          setFileState((prev) => ({ ...prev, status: 'ready' }));
          toast.success('File is ready! You can now ask questions.', { duration: 4000 });
          fetchSummary(fileId);
        } else if (res.status === 'error') {
          clearInterval(pollingIntervalRef.current);
          setFileState((prev) => ({ ...prev, status: 'error' }));
          toast.error(res.error || 'Error processing the file. Please try again.');
        }
      } catch (err) {
        clearInterval(pollingIntervalRef.current);
        console.error('Polling error', err);
      }
    }, 3000);
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

    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setIsChatLoading(true);

    let currentAIResponse = '';

    setMessages((prev) => [...prev, { role: 'ai', content: '', timestamp: null }]);

    const updateLastMessage = (content, timestamp = null) => {
      setMessages((prev) => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1] = { role: 'ai', content, timestamp };
        return newMessages;
      });
    };

    try {
      await api.askQuestionStream(
        fileState.id,
        text,
        (tokenExtracted) => {
          setIsChatLoading(false);
          currentAIResponse += tokenExtracted;
          updateLastMessage(currentAIResponse);
        },
        (metaContext) => {
          setIsChatLoading(false);
          updateLastMessage(currentAIResponse, metaContext.timestamp);
          if (!fileState.url && metaContext.media_url) {
            setFileState((prev) => ({ ...prev, url: metaContext.media_url }));
          }
        },
        (err) => {
          console.error(err);
          setIsChatLoading(false);
          toast.error('Failed to get complete answer stream.');
          updateLastMessage(currentAIResponse || 'Sorry, I encountered an error streaming the response. Please try again.');
        },
      );
    } catch (err) {
      console.error(err);
      setIsChatLoading(false);
      toast.error('Failed to connect to chat.');
      updateLastMessage("Sorry, I couldn't reach the server. Please check your connection.");
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
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-light)',
          },
        }}
      />

      {!user ? (
        <AuthScreen onAuthSuccess={setUser} />
      ) : (
        <div className="app-shell">
          <header className="app-header glass-panel">
            <div className="brand-mark">
              <Bot size={30} color="var(--text-primary)" />
            </div>

            <div className="brand-copy">
             
              <h1 className="app-title">
                Anant <span>Q&amp;A</span>
              </h1>
              <p className="app-subtitle">AI-powered insights for documents, audio, and video with a cleaner reading experience.</p>
            </div>

            <div className="user-actions">
              <span className="user-chip">
                Hi, <strong>{user.username}</strong>
              </span>

              <button
                className="logout-btn"
                onClick={() => {
                  localStorage.removeItem('auth_token');
                  localStorage.removeItem('auth_user');
                  setUser(null);
                }}
              >
                <LogOut size={16} /> Logout
              </button>
            </div>
          </header>

          <main className="app-main">
            <div className="app-sidebar">
              <FileUploader onUploadComplete={handleUploadComplete} isUploading={['uploading', 'processing'].includes(fileState.status)} />

              {fileState.status === 'error' && (
                <div className="glass-panel error-banner">
                  <FileWarning size={20} />
                  <p style={{ fontSize: '0.9rem' }}>There was an error processing your file. Please try a different one.</p>
                </div>
              )}

              <div className="app-summary-slot">
                <SummaryPanel summary={summary} isLoading={isSummaryLoading || fileState.status === 'processing'} />
              </div>
            </div>

            <div className="app-content">
              {fileState.status === 'ready' && ['audio', 'video'].includes(fileState.type) && (
                <div style={{ flexShrink: 0 }}>
                  <MediaPlayer ref={mediaRef} fileUrl={fileState.url} fileType={fileState.type} fileName={fileState.name} />
                </div>
              )}

              <div style={{ flex: 1, minHeight: 0, position: 'relative' }}>
                {fileState.status === 'idle' && (
                  <div
                    style={{
                      position: 'absolute',
                      inset: 0,
                      zIndex: 10,
                      background: 'rgba(15, 23, 42, 0.6)',
                      backdropFilter: 'blur(4px)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: 'var(--radius-lg)',
                    }}
                  >
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
                  fileName={fileState.name}
                  isReady={fileState.status === 'ready'}
                />
              </div>
            </div>
          </main>
        </div>
      )}
    </>
  );
}
