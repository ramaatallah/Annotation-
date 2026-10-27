import { useState } from 'react';
import Navbar from '../components/Navbar';
import Hero from '../components/Hero';

export default function HomePage() {
  const [page, setPage] = useState('home');

  return (
    <>
      <Navbar active={page} onNavigate={setPage} onLogin={() => alert('TODO: نافذة تسجيل الدخول (Supabase)')} />
      <main>
        <Hero onTry={() => setPage('try')} />
        {/* الخطوات التالية: قسم "كيف تعمل المنصة؟" ثم "مميزات المنصة الذكية" */}
      </main>
    </>
  );
}
