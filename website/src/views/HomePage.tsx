'use client';

// الصفحة الرئيسية — Client Component (تتحكم بالـ state للـ navigation)
// الـ Hero, HowItWorks, Features هي Server Components يتم تضمينها هنا

import { useState } from 'react';
import dynamic from 'next/dynamic';
import Navbar from '@/components/Navbar';
import Hero from '@/components/Hero';
import HowItWorks from '@/components/HowItWorks';
import Features from '@/components/Features';

// Client-only pages (lazy-loaded)
const TryIt       = dynamic(() => import('./TryItPage'),    { ssr: false });
const LibraryPage = dynamic(() => import('./LibraryPage'),  { ssr: false });
const HowItWorksPage = dynamic(() => import('./HowItWorksPage'), { ssr: false });
const AboutPage   = dynamic(() => import('./AboutPage'),    { ssr: false });
const LoginModal  = dynamic(() => import('@/components/LoginModal'), { ssr: false });

type PageId = 'home' | 'try' | 'library' | 'how' | 'about';

export default function HomePage() {
  const [page, setPage] = useState<PageId>(() => {
    if (typeof window === 'undefined') return 'home';
    const hash = window.location.hash.replace('#', '') as PageId;
    const valid: PageId[] = ['home', 'try', 'library', 'how', 'about'];
    if (valid.includes(hash)) return hash;
    return (localStorage.getItem('wahaj_active_page') as PageId) || 'home';
  });
  const [loginOpen, setLoginOpen] = useState(false);

  const goTo = (id: string) => {
    setPage(id as PageId);
    localStorage.setItem('wahaj_active_page', id);
    window.location.hash = id;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <>
      <Navbar active={page} onNavigate={goTo} onLogin={() => setLoginOpen(true)} />

      <main>
        {page === 'library' ? (
          <LibraryPage onLogin={() => setLoginOpen(true)} />
        ) : page === 'how' ? (
          <HowItWorksPage />
        ) : page === 'try' ? (
          <TryIt />
        ) : page === 'about' ? (
          <AboutPage />
        ) : (
          <>
            {/* SSR'd sections — fast initial load + good SEO */}
            <Hero onTry={() => goTo('try')} />
            <HowItWorks />
            <Features />
          </>
        )}
      </main>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </>
  );
}
