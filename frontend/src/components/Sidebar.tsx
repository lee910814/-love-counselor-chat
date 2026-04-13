import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sessionsAPI, Session } from '../services/api';
import { useAuth } from '../context/AuthContext';

interface Props {
  activeSessionId: number | null;
  onSelectSession: (id: number) => void;
  onNewSession: () => void;
}

export default function Sidebar({ activeSessionId, onSelectSession, onNewSession }: Props) {
  const queryClient = useQueryClient();
  const { user, logout } = useAuth();

  const { isGuest } = useAuth();

  const { data: sessions = [], isLoading } = useQuery<Session[]>({
    queryKey: ['sessions'],
    queryFn: sessionsAPI.list,
    enabled: !isGuest,
  });

  const deleteMutation = useMutation({
    mutationFn: sessionsAPI.delete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sessions'] }),
  });

  const formatDate = (iso: string) => {
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
    if (diff === 0) return '오늘';
    if (diff === 1) return '어제';
    if (diff < 7) return `${diff}일 전`;
    return new Date(iso).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
  };

  return (
    <aside className="w-64 bg-gray-900 flex flex-col h-screen select-none">
      {/* 헤더 */}
      <div className="px-4 pt-5 pb-3">
        <div className="flex items-center gap-2.5 mb-4">
          <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
          </div>
          <span className="text-white font-semibold text-sm">연애 상담</span>
        </div>

        <button
          onClick={onNewSession}
          className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm
                     text-gray-300 hover:text-white hover:bg-gray-800 transition-colors
                     border border-gray-700 hover:border-gray-600"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          새 대화
        </button>
      </div>

      {/* 구분선 */}
      <div className="h-px bg-gray-800 mx-4" />

      {/* 세션 목록 */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-0.5">
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <div className="w-5 h-5 border-2 border-gray-600 border-t-gray-400 rounded-full animate-spin" />
          </div>
        )}
        {isGuest && (
          <div className="text-center py-8 px-2">
            <p className="text-gray-600 text-xs leading-relaxed">
              대화 내역은 저장되지 않아요.
              <br />
              <button onClick={logout} className="text-indigo-400 hover:text-indigo-300 mt-2 inline-block">
                로그인하면 저장돼요 →
              </button>
            </p>
          </div>
        )}
        {!isGuest && !isLoading && sessions.length === 0 && (
          <p className="text-gray-600 text-xs text-center py-8">대화 내역이 없어요</p>
        )}
        {sessions.map(s => (
          <div
            key={s.id}
            onClick={() => onSelectSession(s.id)}
            className={`group flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer
                        transition-colors
                        ${activeSessionId === s.id
                          ? 'bg-gray-700 text-white'
                          : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'}`}
          >
            <div className="min-w-0 flex-1">
              <p className="text-sm truncate">{s.title}</p>
              <p className="text-xs text-gray-600 mt-0.5">{formatDate(s.updated_at)}</p>
            </div>
            <button
              onClick={e => { e.stopPropagation(); deleteMutation.mutate(s.id); }}
              className="ml-2 opacity-0 group-hover:opacity-100 p-1 rounded-md
                         text-gray-600 hover:text-red-400 hover:bg-gray-700 transition-all"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ))}
      </div>

      {/* 구분선 */}
      <div className="h-px bg-gray-800 mx-4" />

      {/* 유저 / 로그아웃 */}
      <div className="px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-white text-xs font-bold
            ${isGuest ? 'bg-gray-600' : 'bg-indigo-500'}`}>
            {isGuest ? '?' : user?.username?.[0]?.toUpperCase()}
          </div>
          <span className="text-sm text-gray-300 truncate">
            {isGuest ? '비회원' : user?.username}
          </span>
        </div>
        <button
          onClick={logout}
          title="로그아웃"
          className="p-1.5 rounded-lg text-gray-600 hover:text-gray-300 hover:bg-gray-800 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
        </button>
      </div>
    </aside>
  );
}
