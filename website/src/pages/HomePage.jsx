import { useState } from 'react';
import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import TryIt from '../components/TryIt';
import HowItWorks from '../components/HowItWorks';
import Features from '../components/Features';
import About from '../components/About';

const scrollToHow = () => setTimeout(() => document.getElementById('how')?.scrollIntoView({ behavior: 'smooth' }), 0);

export default function HomePage() {
  const [page, setPage] = useState('home');

  // "how" قسم داخل الصفحة الرئيسية، والباقي صفحات تتبدّل
  const goTo = (id) => {
    setPage(id);
    if (id === 'how') scrollToHow();
    else window.scrollTo({ top: 0 });
  };

  const showHome = ['home', 'how'].includes(page);

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
        {page === 'about' && <About />}
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
