import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi } from '@/lib/api';

type User = {
  email: string;
  name: string;
  questionnaire: Record<string, any>;
  profile_picture_url?: string;
};

type AuthContextType = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string, phone?: string) => Promise<void>;
  googleLogin: () => Promise<void>;
  googleCallback: (code: string, state: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (u: User) => void;
  hasQuestionnaire: boolean;
};

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authApi.me().then(({ user }) => setUser(user)).catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { user } = await authApi.login({ email, password });
    setUser(user);
  }, []);

  const register = useCallback(async (email: string, password: string, name: string, phone?: string) => {
    const { user } = await authApi.register({ email, password, name, phone_number: phone || null });
    setUser(user);
  }, []);

  const googleLogin = useCallback(async () => {
    const { url } = await authApi.googleUrl();
    if (url) window.location.href = url;
    else throw new Error('Google OAuth not configured');
  }, []);

  const googleCallback = useCallback(async (code: string, state: string) => {
    const result = await authApi.googleCallback(code, state);
    setUser(result.user);
    return result;
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
  }, []);

  const hasQuestionnaire = !!user?.questionnaire && Object.keys(user.questionnaire).length > 0;

  return (
    <AuthContext.Provider value={{ user, loading, login, register, googleLogin, googleCallback, logout, setUser, hasQuestionnaire }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
};
