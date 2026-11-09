import { useState } from 'react';

import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import TryIt from '../components/TryIt';
import HowItWorks from '../components/HowItWorks';
import Features from '../components/Features';
import About from '../components/About';
import LoginModal from '../components/LoginModal';

import LibraryPage from './LibraryPage';
import HowItWorksPage from './HowItWorksPage';

export default function HomePage() {
  const [page, setPage] = useState(() => {
    // استرجاع الصفحة النشطة بعد الـ refresh إما من الـ hash أو localStorage
    const hash = window.location.hash.replace('#', '');
    if (hash && ['home', 'try', 'library', 'how', 'about'].includes(hash)) {
      return hash;
    }
    return localStorage.getItem('wahaj_active_page') || 'home';
  });
  const [loginOpen, setLoginOpen] = useState(false);

  const openLogin = () => setLoginOpen(true);

  const goTo = (id) => {
    setPage(id);
    localStorage.setItem('wahaj_active_page', id);
    window.location.hash = id;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <>
      <Navbar
        active={page}
        onNavigate={goTo}
        onLogin={openLogin}
      />

      <main>
        {page === 'library' ? (
          <LibraryPage onLogin={openLogin} />
        ) : page === 'how' ? (
          <HowItWorksPage />
        ) : page === 'try' ? (
          <TryIt />
        ) : page === 'about' ? (
          <About />
        ) : (
          <>
            <Hero onTry={() => goTo('try')} />
            <HowItWorks />
            <Features />
          </>
        )}
      </main>

      <LoginModal
        open={loginOpen}
        onClose={() => setLoginOpen(false)}
      />
    </>
  );
}
