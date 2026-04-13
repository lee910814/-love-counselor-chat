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

export default api;
