'use client';

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { supabase, supabaseReady } from '@/lib/supabase';
import type { AuthContextValue, AuthUser } from '@/types';

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!supabaseReady || !supabase) { setLoading(false); return; }

    supabase.auth.getSession().then(({ data }) => {
      setUser(data.session?.user ?? null);
      setLoading(false);
    });

    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => sub.subscription.unsubscribe();
  }, []);

  async function signIn(email: string, password: string) {
    if (!supabaseReady || !supabase)
      throw new Error('إعدادات Supabase غير موجودة');
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      const map: Record<string, string> = {
        invalid_credentials: 'بيانات الدخول غير صحيحة',
        email_not_confirmed: 'لم يتم تأكيد البريد الإلكتروني',
      };
      throw new Error(map[error.code ?? ''] ?? error.message);
    }
  }

  function signInDemo() {
    setUser({ email: 'demo@wahaj.app', isDemo: true });
  }

  async function signOut() {
    if (supabaseReady && supabase && !user?.isDemo)
      await supabase.auth.signOut();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signInDemo, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}
