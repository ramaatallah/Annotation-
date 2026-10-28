import { useAuth } from '../context/AuthContext';

const links = [
  { id: 'home', label: 'الرئيسية' },
  { id: 'try', label: 'جرّب الآن' },
  { id: 'library', label: 'مكتبتي' },
  { id: 'how', label: 'كيف يعمل' },
  { id: 'about', label: 'عن وهج' },
];

export default function Navbar({ active = 'home', onNavigate, onLogin }) {
  const { user, signOut } = useAuth();

  return (
    <header style={{ padding: '16px 0' }}>
      <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
        <a href="#home" onClick={() => onNavigate?.('home')} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: 'var(--navy)', color: '#fff', display: 'grid', placeItems: 'center', fontWeight: 800 }}>و</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 22, lineHeight: 1 }}>وهج</div>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>ظلّل، دوّن، افهم</div>
          </div>
        </a>

        <nav style={{ display: 'flex', gap: 4, background: 'var(--surface)', padding: 4, borderRadius: 12, border: '1px solid var(--border)' }}>
          {links.map((l) => (
            <button
              key={l.id}
              onClick={() => onNavigate?.(l.id)}
              style={{
                font: 'inherit', fontSize: 14, border: 0, cursor: 'pointer', padding: '6px 14px', borderRadius: 8,
                background: active === l.id ? 'var(--bg)' : 'transparent',
                color: active === l.id ? 'var(--navy)' : 'var(--muted)',
                fontWeight: active === l.id ? 700 : 500,
              }}
            >
              {l.label}
            </button>
          ))}
        </nav>

        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 13, color: 'var(--muted)', direction: 'ltr' }}>{user.isDemo ? 'زائر تجريبي' : user.email}</span>
            <button className="btn btn-outline" onClick={signOut}>خروج</button>
          </div>
        ) : (
          <button className="btn btn-primary" onClick={onLogin}>تسجيل الدخول</button>
        )}
      </div>
    </header>
  );
}
