import React, { useState, useRef, KeyboardEvent } from 'react';

interface InputBoxProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

const InputBox: React.FC<InputBoxProps> = ({ onSend, disabled = false }) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  };

  return (
    <div className="bg-white border-t border-gray-200">
      <div className="max-w-2xl mx-auto px-4 py-4">
        <div className="flex items-end gap-3 bg-white border border-gray-300 rounded-2xl px-4 py-3
                        focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-transparent
                        transition shadow-sm">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={e => { setMessage(e.target.value); handleInput(); }}
            onKeyDown={handleKeyDown}
            placeholder="고민을 편하게 말씀해 주세요..."
            disabled={disabled}
            rows={1}
            className="flex-1 resize-none bg-transparent text-sm text-gray-800 placeholder-gray-400
                       focus:outline-none disabled:cursor-not-allowed leading-relaxed
                       min-h-[24px] max-h-[160px] py-0.5"
          />

          <button
            onClick={handleSend}
            disabled={disabled || !message.trim()}
            className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors
                       bg-indigo-600 hover:bg-indigo-700 text-white
                       disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed"
          >
            {disabled ? (
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            )}
          </button>
        </div>
        <p className="text-xs text-gray-400 text-center mt-2">
          Enter로 전송 · Shift+Enter로 줄바꿈
        </p>
      </div>
    </div>
  );
};

export default InputBox;
