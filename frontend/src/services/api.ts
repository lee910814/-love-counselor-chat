import axios from 'axios';

const API_BASE_URL = '/api';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  message: string;
  history?: Message[];
}

export interface SourceInfo {
  content: string;
  score: number;
}

export interface ChatResponse {
  response: string;
  sources: SourceInfo[];
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export type StreamChunk =
  | { type: 'token'; content: string }
  | { type: 'sources'; sources: SourceInfo[] }
  | { type: 'done' };

export const chatAPI = {
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>('/chat/', request);
    return response.data;
  },

  async *streamMessage(request: ChatRequest): AsyncGenerator<StreamChunk> {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok || !response.body) {
      throw new Error(`HTTP error: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            yield JSON.parse(line.slice(6)) as StreamChunk;
          } catch {
            // 파싱 실패 무시
          }
        }
      }
    }
  },

  healthCheck: async (): Promise<{ status: string }> => {
    const response = await api.get('/chat/health');
    return response.data;
  },
};

// --- 인증 API ---

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
}

export const authAPI = {
  register: async (username: string, email: string, password: string): Promise<AuthResponse> => {
    const res = await api.post('/auth/register', { username, email, password });
    return res.data;
  },
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const res = await api.post('/auth/login', { email, password });
    return res.data;
  },
};

// --- 세션 API ---

export interface Session {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface SessionDetail extends Session {
  messages: { id: number; role: string; content: string; created_at: string }[];
}

export const sessionsAPI = {
  create: async (title = '새 대화'): Promise<Session> => {
    const res = await api.post('/sessions/', { title });
    return res.data;
  },

  list: async (): Promise<Session[]> => {
    const res = await api.get('/sessions/');
    return res.data;
  },

  get: async (id: number): Promise<SessionDetail> => {
    const res = await api.get(`/sessions/${id}`);
    return res.data;
  },

  saveMessages: async (sessionId: number, messages: { role: string; content: string }[]) => {
    await api.post(`/sessions/${sessionId}/messages`, {
      session_id: sessionId,
      messages,
    });
  },

  delete: async (id: number) => {
    await api.delete(`/sessions/${id}`);
  },
};

export default api;
