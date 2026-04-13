import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import api from '../services/api';

interface AuthUser {
  id: number;
  username: string;
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isLoggedIn: boolean;
  isGuest: boolean;
  login: (token: string, user: AuthUser) => void;
  loginAsGuest: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [user, setUser] = useState<AuthUser | null>(() => {
    const u = localStorage.getItem('user');
    return u ? JSON.parse(u) : null;
  });
  const [isGuest, setIsGuest] = useState<boolean>(
    () => localStorage.getItem('guest') === 'true'
  );

  useEffect(() => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete api.defaults.headers.common['Authorization'];
    }
  }, [token]);

  const login = (newToken: string, newUser: AuthUser) => {
    localStorage.setItem('token', newToken);
    localStorage.setItem('user', JSON.stringify(newUser));
    localStorage.removeItem('guest');
    setToken(newToken);
    setUser(newUser);
    setIsGuest(false);
    api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
  };

  const loginAsGuest = () => {
    localStorage.setItem('guest', 'true');
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setIsGuest(true);
    setToken(null);
    setUser(null);
    delete api.defaults.headers.common['Authorization'];
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('guest');
    setToken(null);
    setUser(null);
    setIsGuest(false);
    delete api.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{
      user, token, isGuest,
      isLoggedIn: !!token || isGuest,
      login, loginAsGuest, logout,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
