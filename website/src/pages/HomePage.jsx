import { useState } from 'react';
import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import HowItWorks from '../components/HowItWorks';
import Features from '../components/Features';
import LoginModal from '../components/LoginModal';

export default function HomePage() {
  const [page, setPage] = useState('home');
  const [loginOpen, setLoginOpen] = useState(false);

  return (
    <>
      <Navbar active={page} onNavigate={setPage} onLogin={() => setLoginOpen(true)} />
      <main>
        <Hero onTry={() => setPage('try')} />
        <HowItWorks />
        <Features />
      </main>
      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </>
  );
}
