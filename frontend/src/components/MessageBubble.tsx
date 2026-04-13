import React from 'react';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ role, content, isStreaming = false }) => {
  const isUser = role === 'user';

  return (
    <div className={`flex items-end gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'} mb-5`}>
      {/* 아바타 */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center mb-0.5">
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
        </div>
      )}

      {/* 버블 */}
      <div className={`max-w-[72%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        {!isUser && (
          <div className="flex items-center gap-1.5 ml-1">
            <span className="text-xs font-medium text-gray-500">상담사</span>
            <span className="text-xs text-gray-400">
              {new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        )}
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap
            ${isUser
              ? 'bg-indigo-600 text-white rounded-br-sm'
              : 'bg-white text-gray-800 rounded-bl-sm border border-gray-100 shadow-sm'
            }`}
        >
          {content}
          {isStreaming && (
            <span className="inline-block w-0.5 h-[14px] bg-current ml-0.5 animate-pulse align-middle opacity-70" />
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
