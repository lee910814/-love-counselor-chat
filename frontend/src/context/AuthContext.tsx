import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authAPI, setMemoryToken } from '../services/api';

interface AuthUser {
  id: number;
  username: string;
}

interface AuthContextType {
  user: AuthUser | null;
  isLoggedIn: boolean;
  isGuest: boolean;
  isRestoring: boolean;
  login: (access_token: string, user: AuthUser) => void;
  loginAsGuest: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isGuest, setIsGuest] = useState<boolean>(false);
  // 페이지 로드 시 refresh 시도가 끝날 때까지 UI 마운트 대기
  const [isRestoring, setIsRestoring] = useState<boolean>(true);

  // 페이지 로드: httpOnly 쿠키로 세션 복구
  useEffect(() => {
    authAPI
      .refresh()
      .then(({ access_token, user_id, username }) => {
        setMemoryToken(access_token);
        setUser({ id: user_id, username });
        setIsGuest(false);
      })
      .catch(() => {
        // 저장된 리프레시 토큰 없음 → 게스트 상태 복구
        const savedGuest = localStorage.getItem('guest') === 'true';
        setIsGuest(savedGuest);
      })
      .finally(() => setIsRestoring(false));

    // 인터셉터가 갱신 실패 시 발생시키는 이벤트 구독
    const handleForceLogout = () => {
      setUser(null);
      setIsGuest(false);
      setMemoryToken(null);
    };
    window.addEventListener('auth:logout', handleForceLogout);
    return () => window.removeEventListener('auth:logout', handleForceLogout);
  }, []);

  const login = (access_token: string, newUser: AuthUser) => {
    setMemoryToken(access_token);
    setUser(newUser);
    setIsGuest(false);
    localStorage.removeItem('guest');
  };

  const loginAsGuest = () => {
    setMemoryToken(null);
    setUser(null);
    setIsGuest(true);
    localStorage.setItem('guest', 'true');
  };

  const logout = async () => {
    try {
      await authAPI.logout();
    } catch {
      // 서버 오류가 있어도 클라이언트는 로그아웃
    }
    setMemoryToken(null);
    setUser(null);
    setIsGuest(false);
    localStorage.removeItem('guest');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isGuest,
        isRestoring,
        isLoggedIn: !!user || isGuest,
        login,
        loginAsGuest,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
