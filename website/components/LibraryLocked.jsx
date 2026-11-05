export default function LibraryLocked({ onLogin }) {
  return (
    <div style={{ maxWidth: 520, margin: '60px auto', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 18, padding: '40px 28px', textAlign: 'center', boxShadow: '0 8px 30px rgba(31,45,100,.08)' }}>
      <div style={{ width: 52, height: 52, margin: '0 auto 16px', borderRadius: 14, background: '#eef1fb', display: 'grid', placeItems: 'center', fontSize: 24 }}>🔖</div>
      <h2 style={{ fontSize: 24, fontWeight: 800, marginBottom: 8 }}>مكتبتك الشخصية مقفلة</h2>
      <p style={{ color: 'var(--muted)', fontSize: 15, marginBottom: 22 }}>
        سجّل الدخول للوصول إلى المظلّلات والملاحظات والكيانات التي حفظتها.
      </p>
      <button className="btn btn-primary" onClick={onLogin}>تسجيل الدخول الآن</button>
    </div>
  );
}
