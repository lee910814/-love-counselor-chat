import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from './context/AuthContext';
import AuthPage from './pages/AuthPage';
import ChatWindow from './components/ChatWindow';
import InputBox from './components/InputBox';
import Sidebar from './components/Sidebar';
import { chatAPI, sessionsAPI, Message } from './services/api';

function App() {
  const { isLoggedIn, isGuest, isRestoring } = useAuth();
  const queryClient = useQueryClient();

  // 페이지 로드 시 세션 복구가 끝날 때까지 대기 (AuthPage 깜빡임 방지)
  if (isRestoring) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-100">
        <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isLoggedIn) return <AuthPage />;
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);

  // 세션 불러오기 (로그인 유저만)
  const { data: sessionDetail } = useQuery({
    queryKey: ['session', activeSessionId],
    queryFn: () => sessionsAPI.get(activeSessionId!),
    enabled: activeSessionId !== null && !isGuest,
  });

  // sessionDetail 변경 시 메시지 동기화
  useState(() => {
    if (sessionDetail) {
      setMessages(sessionDetail.messages.map(m => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
      })));
    }
  });

  // 새 대화 시작
  const handleNewSession = () => {
    setActiveSessionId(null);
    setMessages([]);
  };

  // 메시지 전송
  const handleSendMessage = async (content: string) => {
    // 세션 없으면 새로 생성 (로그인 유저만)
    let sessionId = activeSessionId;
    if (!sessionId && !isGuest) {
      const newSession = await sessionsAPI.create();
      sessionId = newSession.id;
      setActiveSessionId(sessionId);
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    }

    const userMessage: Message = { role: 'user', content };
    const historySnapshot = [...messages];
    const withUser = [...historySnapshot, userMessage];
    setMessages(withUser);
    setIsLoading(true);

    try {
      const stream = chatAPI.streamMessage({ message: content, history: historySnapshot });
      let started = false;
      let assistantContent = '';

      for await (const chunk of stream) {
        if (chunk.type === 'sources') continue;

        if (chunk.type === 'token') {
          assistantContent += chunk.content;
          if (!started) {
            setMessages(prev => [...prev, { role: 'assistant', content: chunk.content }]);
            setIsLoading(false);
            setIsStreaming(true);
            started = true;
          } else {
            setMessages(prev => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (!last) return prev;
              next[next.length - 1] = { ...last, content: (last.content ?? '') + chunk.content };
              return next;
            });
          }
        }

        if (chunk.type === 'done') {
          setIsStreaming(false);
          // DB에 저장 (로그인 유저만)
          if (!isGuest && sessionId) {
            await sessionsAPI.saveMessages(sessionId, [
              { role: 'user', content },
              { role: 'assistant', content: assistantContent },
            ]);
            queryClient.invalidateQueries({ queryKey: ['sessions'] });
          }
        }
      }
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: '죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.' },
      ]);
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
    }
  };

  return (
    <div className="h-screen flex bg-gray-100">
      <Sidebar
        activeSessionId={activeSessionId}
        onSelectSession={(id) => {
          setActiveSessionId(id);
          queryClient.fetchQuery({
            queryKey: ['session', id],
            queryFn: () => sessionsAPI.get(id),
          }).then((detail) => {
            setMessages(detail.messages.map(m => ({
              role: m.role as 'user' | 'assistant',
              content: m.content,
            })));
          });
        }}
        onNewSession={handleNewSession}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b border-gray-200 px-6 py-3.5 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </div>
            <div>
              <h1 className="text-sm font-semibold text-gray-900">연애 상담사</h1>
              <p className="text-xs text-gray-400">RAG 기반 AI 상담</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span className="text-xs text-gray-400">온라인</span>
          </div>
        </header>

        <ChatWindow messages={messages} isLoading={isLoading} isStreaming={isStreaming} />
        <InputBox onSend={handleSendMessage} disabled={isLoading || isStreaming} />
      </div>
    </div>
  );
}

export default App;
