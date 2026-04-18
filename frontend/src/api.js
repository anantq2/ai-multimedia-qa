import axios from 'axios';

// In Docker: nginx serves frontend on port 80 and proxies /api → backend.
// In local dev (Vite on :5173): hit the backend directly on :8000.
const isDev = window.location.port === '5173';
const baseURL = isDev
  ? `http://${window.location.hostname || '127.0.0.1'}:8000/api`
  : '/api';

// Full backend origin (for SSE streaming + media)
export const backendOrigin = isDev
  ? `http://${window.location.hostname || '127.0.0.1'}:8000`
  : '';

const api = axios.create({ baseURL });

// ── Attach JWT token to every request ────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Auto logout on 401 ──────────────────────────────────────────────────
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      // Don't auto-logout on login/register failures
      const url = err.config?.url || '';
      if (!url.includes('/auth/')) {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        window.location.reload();
      }
    }
    return Promise.reject(err);
  }
);

// ── Auth ─────────────────────────────────────────────────────────────────
export const register = async (username, email, password) => {
  const response = await api.post('/auth/register', { username, email, password });
  return response.data;
};

export const login = async (username, password) => {
  const response = await api.post('/auth/login', { username, password });
  return response.data;
};

// ── File Operations ──────────────────────────────────────────────────────
export const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const checkStatus = async (fileId) => {
  const response = await api.get(`/status/${fileId}`);
  return response.data;
};

export const askQuestion = async (fileId, question) => {
  const response = await api.post('/ask', { file_id: fileId, question });
  return response.data;
};

export const getSummary = async (fileId) => {
  const response = await api.post('/summary', { file_id: fileId });
  return response.data;
};

// ── Streaming Q&A (SSE) ─────────────────────────────────────────────────
export const askQuestionStream = async (fileId, question, onToken, onDone, onError) => {
  const token = localStorage.getItem('auth_token');

  try {
    const response = await fetch(`${baseURL}/ask-stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ file_id: fileId, question }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'token') {
              onToken(data.content);
            } else if (data.type === 'done') {
              onDone(data);
            }
          } catch (e) {
            // Skip malformed SSE lines
          }
        }
      }
    }
  } catch (err) {
    onError(err);
  }
};
