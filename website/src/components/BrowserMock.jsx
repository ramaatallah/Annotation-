// بطاقة توضيحية تحاكي صفحة ويب عليها تظليل وملاحظة
export default function BrowserMock() {
  return (
    <div style={{ background: 'var(--surface)', borderRadius: 16, border: '1px solid var(--border)', boxShadow: '0 12px 40px rgba(31,45,100,.12)', overflow: 'hidden', direction: 'rtl' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 14px', borderBottom: '1px solid var(--border)' }}>
        <i style={dot('#ef6a5e')} /><i style={dot('#f5bd4f')} /><i style={dot('#62c554')} />
        <span style={{ marginInlineStart: 12, fontSize: 11, color: 'var(--muted)', direction: 'ltr' }}>https://news.palestine.org/article-88</span>
      </div>

      <div style={{ padding: 20 }}>
        <div style={{ height: 10, background: '#eee', borderRadius: 6, marginBottom: 14 }} />
        <p style={{ fontSize: 15 }}>
          تواصل{' '}
          <mark style={{ background: 'var(--highlight)', color: '#6a2bb5', padding: '1px 6px', borderRadius: 6 }}>جامعة النجاح الوطنية</mark>{' '}
          تقديم مبادراتها الأكاديمية في مدينة{' '}
          <mark style={{ background: '#d8f5e0', color: '#1d7a3a', padding: '1px 6px', borderRadius: 6 }}>نابلس</mark>{' '}
          بالتعاون مع المراكز الأبحاث الدولية.
        </p>

        <div style={{ marginTop: 16, background: 'var(--note-bg)', border: '1px solid var(--note-border)', borderRadius: 10, padding: 12, fontSize: 13 }}>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>📝 ملاحظة محفوظة</div>
          <div>«تم توثيق الكيان وتحديد جذره اللغوي لاستخدامه في أطروحة البحث.»</div>
        </div>
      </div>
    </div>
  );
}
const dot = (c) => ({ width: 10, height: 10, borderRadius: '50%', background: c, display: 'inline-block' });
