import { useState } from 'react';
import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import HowItWorks from '../components/HowItWorks';
import Features from '../components/Features';
import TryPage from './TryPage';

export default function HomePage() {
  const [page, setPage] = useState('home');

  return (
    <>
      <Navbar active={page} onNavigate={setPage} onLogin={() => alert('TODO: نافذة تسجيل الدخول (Supabase)')} />
      <main>
        {page === 'try' ? (
          <TryPage />
        ) : (
          <>
            <Hero onTry={() => setPage('try')} />
            <HowItWorks />
            <Features />
          </>
        )}
      </main>
    </>
  );
}
