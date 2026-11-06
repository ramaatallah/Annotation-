import { useState } from 'react';
import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import HowItWorks from '../components/HowItWorks';
import Features from '../components/Features';
import LoginModal from '../components/LoginModal';
import LibraryPage from './LibraryPage';
import HowItWorksPage from './HowItWorksPage';

export default function HomePage() {
  const [page, setPage] = useState('home');
  const [loginOpen, setLoginOpen] = useState(false);
  const openLogin = () => setLoginOpen(true);

  return (
    <>
      <Navbar active={page} onNavigate={setPage} onLogin={openLogin} />
      <main>
      {page === 'library' ? (
          <LibraryPage onLogin={openLogin} />
        ) : page === 'how' ? (
          <HowItWorksPage />
        ) : page === 'try' ? (
          <p className="container" style={{ padding: 60, textAlign: 'center' }}>صفحة «جرّب الآن» قيد العمل (سيرين) 🛠️</p>
        ) : (
          <>
            <Hero onTry={() => setPage('try')} />
            <HowItWorks />
            <Features />
          </>
        )}
      </main>
      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </>
  );
}
