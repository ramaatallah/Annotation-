import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';

const field = {
  width: '100%', padding: '12px 14px', borderRadius: 10, border: '1.5px solid var(--border)',
  font: 'inherit', background: '#fff', outline: 'none',
};

export default function LoginModal({ open, onClose }) {
  const { signIn, signInDemo } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await signIn(email.trim(), password);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      onClick={onClose}
      style={{ position: 'fixed', inset: 0, background: 'rgba(27,37,71,.45)', backdropFilter: 'blur(4px)', display: 'grid', placeItems: 'center', zIndex: 100, padding: 16 }}
    >
      <div
        role="dialog" aria-modal="true" aria-label="تسجيل الدخول"
        onClick={(e) => e.stopPropagation()}
        style={{ width: '100%', maxWidth: 400, background: '#fff', borderRadius: 18, padding: 28, boxShadow: '0 20px 60px rgba(0,0,0,.25)' }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ fontSize: 22, fontWeight: 800 }}>تسجيل الدخول إلى وهج</h2>
          <button onClick={onClose} aria-label="إغلاق" style={{ border: 0, background: 'none', fontSize: 20, cursor: 'pointer', color: 'var(--muted)' }}>✕</button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 14 }}>
          <label style={{ display: 'grid', gap: 6, fontSize: 14, fontWeight: 700 }}>
            البريد الإلكتروني
            <input type="email" required dir="ltr" placeholder="name@example.com" value={email} onChange={(e) => setEmail(e.target.value)} style={field} />
          </label>
          <label style={{ display: 'grid', gap: 6, fontSize: 14, fontWeight: 700 }}>
            كلمة المرور
            <input type="password" required dir="ltr" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} style={field} />
          </label>

          {error && <div style={{ background: '#fdecec', color: '#b42318', borderRadius: 8, padding: '8px 12px', fontSize: 13 }}>{error}</div>}

          <button className="btn btn-primary" type="submit" disabled={busy} style={{ justifyContent: 'center', opacity: busy ? .7 : 1 }}>
            {busy ? 'جارٍ الدخول...' : 'دخول'}
          </button>
        </form>

        <button
          onClick={() => { signInDemo(); onClose(); }}
          style={{ display: 'block', margin: '16px auto 0', border: 0, background: 'none', color: 'var(--navy)', fontSize: 13, cursor: 'pointer', textDecoration: 'underline', font: 'inherit' }}
        >
          الدخول كزائر تجريبي (Demo User)
        </button>
      </div>
    </div>
  );
}
