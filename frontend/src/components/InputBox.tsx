import React, { useState, KeyboardEvent } from 'react';

interface InputBoxProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

const InputBox: React.FC<InputBoxProps> = ({ onSend, disabled = false }) => {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t bg-white p-4">
      <div className="flex items-end gap-3 max-w-4xl mx-auto">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="고민을 말씀해 주세요..."
          disabled={disabled}
          className="flex-1 resize-none border border-gray-300 rounded-xl px-4 py-3
                     focus:outline-none focus:border-pink-400 focus:ring-1 focus:ring-pink-400
                     disabled:bg-gray-100 disabled:cursor-not-allowed
                     min-h-[48px] max-h-[120px]"
          rows={1}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !message.trim()}
          className="bg-pink-500 text-white px-6 py-3 rounded-xl font-medium
                     hover:bg-pink-600 transition-colors
                     disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          {disabled ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            </span>
          ) : (
            '전송'
          )}
        </button>
      </div>
      <p className="text-xs text-gray-400 text-center mt-2">
        Shift + Enter로 줄바꿈
      </p>
    </div>
  );
};

export default InputBox;
