const node = (bg: string, border: string) => ({
  background: bg, border: `1px solid ${border}`, borderRadius: 14, padding: '18px 16px',
  textAlign: 'center' as const, display: 'grid', gap: 6, justifyItems: 'center' as const,
});
const arrow = { fontSize: 22, color: '#b6bccd', alignSelf: 'center', textAlign: 'center' as const };

export default function ArchitectureDiagram() {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 20, padding: '28px 24px', boxShadow: '0 8px 30px rgba(31,45,100,.06)' }}>
      <h3 style={{ textAlign: 'center', fontSize: 17, fontWeight: 800, marginBottom: 22, color: 'var(--ink)' }}>
        المخطط المعماري للمنصة (Architecture Diagram)
      </h3>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 60px 1fr', gap: 8, alignItems: 'start', maxWidth: 560, margin: '0 auto' }}>
        <div style={node('#eef2ff', '#d6defa')}>
          <span style={{ fontSize: 26 }}>🌐</span>
          <strong style={{ fontSize: 14, color: '#1e293b' }}>إضافة المتصفح</strong>
          <small style={{ color: 'var(--muted)' }}>تظلّل النص وترسل الطلب</small>
        </div>

        <div style={{ ...arrow, paddingTop: 36 }}>←</div>

        <div style={node('#f6eeff', '#e5d3fb')}>
          <span style={{ fontSize: 26 }}>🧠</span>
          <strong style={{ fontSize: 14, color: '#1e293b' }}>خدمة التحليل (FastAPI)</strong>
          <small style={{ color: 'var(--muted)' }}>استخراج الكيانات والأنماط</small>
        </div>

        <div style={{ ...arrow, gridColumn: 1, paddingBlock: 2 }}>↓</div>
        <div /><div />

        <div style={node('#fff8e1', '#f3e2a6')}>
          <span style={{ fontSize: 26 }}>🗄️</span>
          <strong style={{ fontSize: 14, color: '#1e293b' }}>قاعدة البيانات</strong>
          <small style={{ color: 'var(--muted)' }}>حفظ الملاحظات والمستندات</small>
        </div>
      </div>
    </div>
  );
}
