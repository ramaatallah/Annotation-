'use client';

import { useTheme } from '@/context/ThemeContext';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      aria-label="تبديل المظهر"
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: '6px 10px',
        cursor: 'pointer',
        fontSize: 15,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--ink)',
        transition: '.15s ease',
      }}
      title={theme === 'light' ? 'الوضع الداكن' : 'الوضع الفاتح'}
    >
      {theme === 'light' ? '🌙' : '🌞'}
    </button>
  );
}
