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

// ── 메모리 토큰 관리 ──────────────────────────────────────────────
let _memoryToken: string | null = null;

export function setMemoryToken(token: string | null): void {
  _memoryToken = token;
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
}

export function getMemoryToken(): string | null {
  return _memoryToken;
}

// ── Axios 인스턴스 ────────────────────────────────────────────────
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,   // httpOnly 쿠키 자동 전송
});

// 리프레시용 별도 인스턴스 (인터셉터 제외 → 무한 루프 방지)
const rawApi = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

// ── 401 자동 갱신 인터셉터 ────────────────────────────────────────
let isRefreshing = false;
let refreshQueue: ((token: string) => void)[] = [];

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;

    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    original._retry = true;

    if (isRefreshing) {
      // 이미 갱신 중이면 큐에서 대기
      return new Promise((resolve) => {
        refreshQueue.push((token) => {
          original.headers['Authorization'] = `Bearer ${token}`;
          resolve(api(original));
        });
      });
    }

    isRefreshing = true;
    try {
      const res = await rawApi.post<AuthResponse>('/auth/refresh');
      const { access_token } = res.data;
      setMemoryToken(access_token);
      refreshQueue.forEach((cb) => cb(access_token));
      refreshQueue = [];
      original.headers['Authorization'] = `Bearer ${access_token}`;
      return api(original);
    } catch {
      setMemoryToken(null);
      refreshQueue = [];
      // 갱신 실패 → 로그인 페이지로 이동
      window.dispatchEvent(new CustomEvent('auth:logout'));
      return Promise.reject(error);
    } finally {
      isRefreshing = false;
    }
  },
);

// ── 스트리밍 타입 ─────────────────────────────────────────────────
export type StreamChunk =
  | { type: 'token'; content: string }
  | { type: 'sources'; sources: SourceInfo[] }
  | { type: 'done' };

// ── 채팅 API ──────────────────────────────────────────────────────
export const chatAPI = {
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>('/chat/', request);
    return response.data;
  },

  async *streamMessage(request: ChatRequest): AsyncGenerator<StreamChunk> {
    const token = getMemoryToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers,
      credentials: 'include',
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

// ── 인증 API ──────────────────────────────────────────────────────
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
}

export const authAPI = {
  register: async (username: string, email: string, password: string): Promise<AuthResponse> => {
    const res = await api.post<AuthResponse>('/auth/register', { username, email, password });
    return res.data;
  },

  login: async (email: string, password: string): Promise<AuthResponse> => {
    const res = await api.post<AuthResponse>('/auth/login', { email, password });
    return res.data;
  },

  refresh: async (): Promise<AuthResponse> => {
    const res = await rawApi.post<AuthResponse>('/auth/refresh');
    return res.data;
  },

  logout: async (): Promise<void> => {
    await rawApi.post('/auth/logout');
  },
};

// ── 세션 API ──────────────────────────────────────────────────────
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
