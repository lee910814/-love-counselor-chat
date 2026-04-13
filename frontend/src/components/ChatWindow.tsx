import React, { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import { Message } from '../services/api';

interface ChatWindowProps {
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
}

const EXAMPLE_QUESTIONS = [
  '남자친구가 연락이 뜸해졌어요',
  '첫 데이트 어떻게 하면 좋을까요?',
  '권태기인 것 같아요, 어떻게 극복하죠?',
];

const ChatWindow: React.FC<ChatWindowProps> = ({ messages, isLoading, isStreaming }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-6">
        {/* 날짜 표시 */}
        {messages.length > 0 && (
          <div className="flex justify-center mb-6">
            <span className="text-xs text-gray-400">
              {new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' })}
            </span>
          </div>
        )}

        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
            <div className="w-16 h-16 rounded-2xl bg-indigo-600 flex items-center justify-center mb-5 shadow-lg">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-gray-800 mb-2">무슨 고민이 있으세요?</h2>
            <p className="text-gray-500 text-sm mb-8 leading-relaxed">
              연애에 관한 어떤 고민이든 편하게 말씀해 주세요.<br />
              따뜻하고 현실적인 조언을 드릴게요.
            </p>
            <div className="flex flex-col gap-2 w-full max-w-sm">
              {EXAMPLE_QUESTIONS.map(q => (
                <div
                  key={q}
                  className="px-4 py-3 bg-white rounded-xl border border-gray-200 text-sm text-gray-600
                             hover:border-indigo-300 hover:bg-indigo-50 cursor-default transition-colors text-left"
                >
                  {q}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => {
              const isLastAssistant = isStreaming && i === messages.length - 1 && msg.role === 'assistant';
              return (
                <MessageBubble
                  key={i}
                  role={msg.role}
                  content={msg.content}
                  isStreaming={isLastAssistant}
                />
              );
            })}

            {isLoading && (
              <div className="flex items-end gap-2.5 mb-5">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center">
                  <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                  </svg>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-gray-500 ml-1">상담사</span>
                  <div className="bg-white border border-gray-100 shadow-sm rounded-2xl rounded-bl-sm px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      {[0, 150, 300].map(delay => (
                        <div
                          key={delay}
                          className="w-2 h-2 bg-gray-300 rounded-full animate-bounce"
                          style={{ animationDelay: `${delay}ms` }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default ChatWindow;
