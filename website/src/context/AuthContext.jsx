import { createContext, useContext, useEffect, useState } from 'react';
import { supabase, supabaseReady } from '../lib/supabase';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!supabaseReady) { setLoading(false); return; }
    supabase.auth.getSession().then(({ data }) => {
      setUser(data.session?.user ?? null);
      setLoading(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  async function signIn(email, password) {
    if (!supabaseReady) throw new Error('إعدادات Supabase غير موجودة (تحققي من ملف .env.local)');
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw new Error('البريد الإلكتروني أو كلمة المرور غير صحيحة');
  }

  function signInDemo() {
    setUser({ email: 'demo@wahaj.app', isDemo: true });
  }

  async function signOut() {
    if (supabaseReady && !user?.isDemo) await supabase.auth.signOut();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signInDemo, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}
