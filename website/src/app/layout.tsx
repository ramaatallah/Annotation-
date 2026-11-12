// Root layout — Server Component
// Wraps everything with providers and sets HTML lang/dir

import type { Metadata } from 'next';
import './globals.css';
import Providers from './providers';

export const metadata: Metadata = {
  title: 'وهج — مساعد القراءة الذكي للنص العربي',
  description: 'إضافة متصفح أكاديمية تظلّل النصوص العربية، تستخرج الكيانات وتحفظها تلقائيًا',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
