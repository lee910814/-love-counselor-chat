import React, { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import { Message } from '../services/api';

interface ChatWindowProps {
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ messages, isLoading, isStreaming }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
      <div className="max-w-4xl mx-auto">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-20">
            <div className="text-6xl mb-4">💕</div>
            <h2 className="text-xl font-semibold text-gray-700 mb-2">
              연애 상담 챗봇에 오신 것을 환영합니다
            </h2>
            <p className="text-gray-500 max-w-md">
              연애에 관한 고민이 있으시면 편하게 말씀해 주세요.
              <br />
              비밀이 보장되며, 따뜻한 조언을 드리겠습니다.
            </p>
            <div className="mt-8 space-y-2 text-sm text-gray-400">
              <p>예시 질문:</p>
              <p>"남자친구가 연락이 뜸해졌어요"</p>
              <p>"첫 데이트 어떻게 하면 좋을까요?"</p>
              <p>"MBTI가 다르면 안 맞을까요?"</p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => {
              const isLastAssistant =
                isStreaming &&
                index === messages.length - 1 &&
                message.role === 'assistant';
              return (
                <MessageBubble
                  key={index}
                  role={message.role}
                  content={message.content}
                  isStreaming={isLastAssistant}
                />
              );
            })}
            {isLoading && (
              <div className="flex justify-start mb-4">
                <div className="bg-white rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-pink-500 font-semibold text-sm">
                      상담사
                    </span>
                  </div>
                  <div className="flex items-center gap-1 mt-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default ChatWindow;
