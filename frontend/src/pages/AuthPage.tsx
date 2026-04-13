import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../services/api';

export default function AuthPage() {
  const { login, loginAsGuest } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = mode === 'login'
        ? await authAPI.login(form.email, form.password)
        : await authAPI.register(form.username, form.email, form.password);
      login(res.access_token, { id: res.user_id, username: res.username });
    } catch (err: any) {
      setError(err.response?.data?.detail || '오류가 발생했어요. 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  };

  const field = (label: string, type: string, key: keyof typeof form, placeholder: string) => (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <input
        type={type}
        placeholder={placeholder}
        value={form[key]}
        onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
        required
        className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-gray-300
                   bg-white placeholder-gray-400 text-gray-900
                   focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                   transition"
      />
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
      {/* 로고 */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-indigo-600 mb-4">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-gray-900">연애 상담 챗봇</h1>
        <p className="text-sm text-gray-500 mt-1">당신의 연애 고민을 들어드려요</p>
      </div>

      {/* 카드 */}
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
        {/* 탭 */}
        <div className="flex gap-1 p-1 bg-gray-100 rounded-xl mb-6">
          {(['login', 'register'] as const).map(m => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(''); }}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all
                ${mode === m
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'}`}
            >
              {m === 'login' ? '로그인' : '회원가입'}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'register' && field('아이디', 'text', 'username', 'username')}
          {field('이메일', 'email', 'email', 'name@example.com')}
          {field('비밀번호', 'password', 'password', '••••••••')}

          {error && (
            <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 px-3 py-2.5 rounded-lg">
              <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white
                       text-sm font-semibold rounded-lg transition-colors
                       focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2
                       disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading && (
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {loading ? '잠깐만요...' : mode === 'login' ? '로그인' : '회원가입'}
          </button>

          {/* 구분선 */}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-gray-200" />
            <span className="text-xs text-gray-400">또는</span>
            <div className="flex-1 h-px bg-gray-200" />
          </div>

          <button
            type="button"
            onClick={loginAsGuest}
            className="w-full py-2.5 px-4 bg-white hover:bg-gray-50 text-gray-700
                       text-sm font-medium rounded-lg border border-gray-300 transition-colors
                       focus:outline-none focus:ring-2 focus:ring-gray-300"
          >
            비회원으로 시작하기
          </button>
        </form>
      </div>

      <p className="text-xs text-gray-400 mt-6">
        {mode === 'login' ? '아직 계정이 없으신가요? ' : '이미 계정이 있으신가요? '}
        <button
          onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}
          className="text-indigo-600 hover:underline font-medium"
        >
          {mode === 'login' ? '회원가입' : '로그인'}
        </button>
      </p>
    </div>
  );
}
