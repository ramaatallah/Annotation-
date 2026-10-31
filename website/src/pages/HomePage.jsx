import { useState } from 'react';
import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import TryIt from '../components/TryIt';
import HowItWorks from '../components/HowItWorks';
import Features from '../components/Features';

// "how" و"about" أقسام داخل الصفحة الرئيسية، والباقي صفحات تتبدّل
const SCROLL_TARGET = { how: 'how', about: 'features' };

export default function HomePage() {
  const [page, setPage] = useState('home');

  const goTo = (id) => {
    setPage(id);
    const target = SCROLL_TARGET[id];
    if (target) {
      setPage(id === 'how' ? 'how' : 'about'); // لتمييز الزر في الـ Navbar
      setTimeout(() => document.getElementById(target)?.scrollIntoView({ behavior: 'smooth' }), 0);
    } else {
      window.scrollTo({ top: 0 });
    }
  };

  const showHome = ['home', 'how', 'about'].includes(page);

  return (
    <>
      <Navbar active={page} onNavigate={goTo} onLogin={() => alert('TODO: نافذة تسجيل الدخول (Supabase)')} />
      <main>
        {showHome && (
          <>
            <Hero onTry={() => goTo('try')} />
            <HowItWorks />
            <Features />
          </>
        )}
        {page === 'try' && <TryIt />}
        {page === 'library' && (
          <section className="container" style={{ padding: '80px 20px', textAlign: 'center', color: 'var(--muted)' }}>
            <h2 style={{ color: 'var(--ink)', fontSize: 32 }}>مكتبتي</h2>
            <p>TODO: عرض التظليلات والملاحظات المحفوظة (بعد تسجيل الدخول).</p>
          </section>
        )}
      </main>
    </>
  );
}
