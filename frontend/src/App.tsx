import { useState, useEffect } from 'react';
import ChatWindow from './components/ChatWindow';
import InputBox from './components/InputBox';
import { chatAPI, Message, SourceInfo } from './services/api';

const STORAGE_KEY = 'love-counselor-chat-history';

function App() {
  const [messages, setMessages] = useState<Message[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (!saved) return [];
      const parsed = JSON.parse(saved);
      return Array.isArray(parsed)
        ? parsed.filter((m): m is Message => !!m && typeof m.content === 'string')
        : [];
    } catch {
      return [];
    }
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = { role: 'user', content };
    const historySnapshot = [...messages];
    const withUser = [...historySnapshot, userMessage];
    setMessages(withUser);
    setIsLoading(true);

    try {
      const stream = chatAPI.streamMessage({ message: content, history: historySnapshot });
      let started = false;

      for await (const chunk of stream) {
        if (chunk.type === 'sources') {
          // sources는 현재 UI에서 사용하지 않지만 확장 가능
          continue;
        }
        if (chunk.type === 'token') {
          if (!started) {
            // 첫 토큰 도착 시 빈 assistant 메시지 추가
            setMessages(prev => [...prev, { role: 'assistant', content: chunk.content }]);
            setIsLoading(false);
            setIsStreaming(true);
            started = true;
          } else {
            setMessages(prev => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (!last) return prev;
              next[next.length - 1] = {
                ...last,
                content: (last.content ?? '') + chunk.content,
              };
              return next;
            });
          }
        }
        if (chunk.type === 'done') {
          setIsStreaming(false);
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: '죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.' },
      ]);
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">💕</span>
            <div>
              <h1 className="text-lg font-bold text-gray-800">연애 상담 챗봇</h1>
              <p className="text-xs text-gray-500">당신의 연애 고민을 들어드려요</p>
            </div>
          </div>
          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="text-sm text-gray-500 hover:text-gray-700
                         px-3 py-1 rounded-lg hover:bg-gray-100 transition-colors"
            >
              새 대화
            </button>
          )}
        </div>
      </header>

      {/* Chat Area */}
      <ChatWindow messages={messages} isLoading={isLoading} isStreaming={isStreaming} />

      {/* Input Area */}
      <InputBox onSend={handleSendMessage} disabled={isLoading || isStreaming} />
    </div>
  );
}

export default App;
