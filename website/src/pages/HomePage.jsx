import { useState } from 'react';
import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import HowItWorks from '../components/HowItWorks';
import Features from '../components/Features';

export default function HomePage() {
  const [page, setPage] = useState('home');

  return (
    <>
      <Navbar active={page} onNavigate={setPage} onLogin={() => alert('TODO: نافذة تسجيل الدخول (Supabase)')} />
      <main>
        <Hero onTry={() => setPage('try')} />
        <HowItWorks />
        <Features />
      </main>
    </>
  );
}
