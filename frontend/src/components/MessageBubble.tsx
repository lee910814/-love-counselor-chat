import React from 'react';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ role, content, isStreaming = false }) => {
  const isUser = role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-pink-500 text-white rounded-br-sm'
            : 'bg-white text-gray-800 rounded-bl-sm shadow-sm'
        }`}
      >
        {!isUser && (
          <div className="flex items-center mb-2">
            <span className="text-pink-500 font-semibold text-sm">
              상담사
            </span>
          </div>
        )}
        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {content}
          {isStreaming && (
            <span className="inline-block w-0.5 h-4 bg-pink-400 ml-0.5 animate-pulse align-middle" />
          )}
        </p>
      </div>
    </div>
  );
};

export default MessageBubble;
