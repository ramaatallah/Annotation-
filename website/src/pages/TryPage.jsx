import { useState } from 'react';

// عنوان سيرفر التحليل (Python). غيّريه لما ينرفع السيرفر على الإنترنت
const API_URL = 'http://127.0.0.1:8000/analyze';

const SAMPLE =
  'ولد محمود درويش في 13 مارس 1941 في قرية البروة وهي قرية فلسطينية تقع في الجليل قرب ساحل عكا. انتسب إلى الحزب الشيوعي الإسرائيلي وعمل في صحافة الحزب.';

// ألوان كل نوع كيان (المفاتيح نفس أسماء type اللي بيرجعها الـ API)
const TYPES = {
  PERSON:       { label: 'شخص',    bg: '#e3ecff', fg: '#2b5fd9', dot: '#2f6fed' },
  LOCATION:     { label: 'مكان',   bg: '#dcf6e5', fg: '#1d7a3a', dot: '#1fb26a' },
  ORGANIZATION: { label: 'مؤسسة',  bg: '#efe0ff', fg: '#6a2bb5', dot: '#9333ea' },
  DATE:         { label: 'تاريخ',  bg: '#ffe6d6', fg: '#b4521a', dot: '#ea580c' },
  DISEASE:      { label: 'مرض',    bg: '#ffdde2', fg: '#b3203a', dot: '#e11d48' },
  EVENT:        { label: 'حدث',    bg: '#fff0c2', fg: '#8a5a00', dot: '#d9a400' },
  PRODUCT:      { label: 'منتج',   bg: '#d6f1f5', fg: '#0f6b7a', dot: '#0891b2' },
  COMPETITION:  { label: 'مسابقة', bg: '#fbdcf1', fg: '#a1227f', dot: '#d946a8' },
  PRICE:        { label: 'سعر',    bg: '#e6f2cc', fg: '#4c6b12', dot: '#65a30d' },
  TERM:         { label: 'مصطلح علمي', bg: '#e0e7ff', fg: '#4338ca', dot: '#6366f1' },
};
const OTHER = { label: 'أخرى', bg: '#eceef3', fg: '#4b5563', dot: '#6b7280' };
const styleOf = (type) => TYPES[type] || OTHER;

// لون الدقة: أخضر عالي، برتقالي متوسط، أحمر ضعيف
const confColor = (c) => (c >= 0.8 ? '#16a34a' : c >= 0.6 ? '#d97706' : '#dc2626');

export default function TryPage() {
  const [text, setText] = useState('');
  const [entities, setEntities] = useState([]);
  const [analyzed, setAnalyzed] = useState('');   // النص اللي انحلل فعلاً
  const [filter, setFilter] = useState('ALL');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function analyze() {
    if (!text.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error('bad status');
      const data = await res.json();
      setEntities(data.entities || []);
      setAnalyzed(text);
      setFilter('ALL');
    } catch {
      setError('تعذّر تحليل النص. تأكدي أن سيرفر Python شغّال.');
    } finally {
      setLoading(false);
    }
  }

  // نبني النص المظلّل: قطع عادية + قطع كيانات (حسب start/end)
  function renderHighlighted() {
    const sorted = [...entities]
      .filter((e) => typeof e.start === 'number' && typeof e.end === 'number')
      .sort((a, b) => a.start - b.start);
    const parts = [];
    let pos = 0;
    sorted.forEach((e, i) => {
      if (e.start < pos) return; // تداخل: تجاهليه
      if (e.start > pos) parts.push(analyzed.slice(pos, e.start));
      const s = styleOf(e.type);
      parts.push(
        <mark
          key={i}
          title={e.type_ar}
          style={{ background: s.bg, color: s.fg, padding: '1px 7px', borderRadius: 6, borderBottom: `2px solid ${s.dot}`, fontWeight: 600 }}
        >
          {analyzed.slice(e.start, e.end)}
        </mark>
      );
      pos = e.end;
    });
    parts.push(analyzed.slice(pos));
    return parts;
  }

  // عدّاد لكل نوع، ونعرض فلاتر الأنواع اللي طلعت فعلاً بالنتيجة بس
  const counts = entities.reduce((acc, e) => ({ ...acc, [e.type]: (acc[e.type] || 0) + 1 }), {});
  const presentTypes = Object.keys(counts);
  const shown = entities.filter((e) => filter === 'ALL' || e.type === filter);

  const card = { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 22 };

  return (
    <section className="container" style={{ padding: '40px 20px 80px' }}>
      <div style={{ textAlign: 'center', marginBottom: 28 }}>
        <h2 style={{ fontSize: 32, fontWeight: 800 }}>مختبر تحليل النصوص</h2>
        <p style={{ color: 'var(--muted)', fontSize: 15 }}>أدخل أي نص عربي لاختبار تقنية التعرف على الكيانات واستخراج الجذور اللغوية.</p>
      </div>

      {/* 1) إدخال النص */}
      <div style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <strong>النص المراد تحليله:</strong>
          <button className="btn btn-outline" style={{ padding: '4px 12px', fontSize: 13 }} onClick={() => setText(SAMPLE)}>
            استخدم نص تجريبي
          </button>
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={7}
          maxLength={10000}
          placeholder="اكتب أو الصق النص هنا..."
          style={{ width: '100%', font: 'inherit', padding: 14, borderRadius: 10, border: '1px solid var(--border)', resize: 'vertical' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
          <button className="btn btn-primary" onClick={analyze} disabled={loading || !text.trim()}>
            {loading ? 'جارٍ التحليل...' : 'حلّل النص'}
          </button>
          <span style={{ color: 'var(--muted)', fontSize: 12 }}>{text.length} حرف</span>
        </div>
        {error && <p style={{ color: '#c0392b', marginTop: 10 }}>{error}</p>}
      </div>

      {/* 2) النتائج */}
      {analyzed && !error && (
        <>
          <div style={{ ...card, marginTop: 20 }}>
            <strong style={{ display: 'block', marginBottom: 12, fontSize: 14 }}>النص المظلّل بالكيانات</strong>
            <p style={{ lineHeight: 2.3, fontSize: 16 }}>{renderHighlighted()}</p>
          </div>

          <h3 style={{ margin: '32px 0 14px', fontSize: 20 }}>الكيانات المكتشفة ({entities.length})</h3>

          {entities.length === 0 ? (
            <p style={{ color: 'var(--muted)' }}>
              لم يتم العثور على كيانات (أسماء أشخاص، أماكن، مؤسسات، تواريخ...) في هذا النص.
            </p>
          ) : (
            <>
              {/* الفلاتر: الكل + الأنواع الموجودة بالنتيجة مع عددها */}
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 18 }}>
                {[{ key: 'ALL', label: 'الكل', dot: null, n: entities.length }, ...presentTypes.map((k) => ({ key: k, label: styleOf(k).label, dot: styleOf(k).dot, n: counts[k] }))].map((f) => {
                  const active = filter === f.key;
                  return (
                    <button
                      key={f.key}
                      onClick={() => setFilter(f.key)}
                      style={{
                        font: 'inherit', fontSize: 14, fontWeight: 600, cursor: 'pointer',
                        display: 'inline-flex', alignItems: 'center', gap: 8,
                        padding: '7px 18px', borderRadius: 999,
                        border: '1px solid var(--border)',
                        background: active ? 'var(--navy)' : 'var(--surface)',
                        color: active ? '#fff' : 'var(--ink)',
                      }}
                    >
                      {f.label}
                      {f.dot && <i style={{ width: 9, height: 9, borderRadius: '50%', background: f.dot, display: 'inline-block' }} />}
                      <span style={{ fontSize: 12, opacity: 0.7 }}>{f.n}</span>
                    </button>
                  );
                })}
              </div>

              {/* بطاقات الكيانات */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 18 }}>
                {shown.map((e, i) => {
                  const s = styleOf(e.type);
                  const conf = e.confidence ?? 0;
                  return (
                    <article key={i} style={{ ...card, padding: '18px 22px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
                        <strong style={{ fontSize: 18 }}>{e.text}</strong>
                        <span style={{ background: s.bg, color: s.fg, borderRadius: 999, padding: '2px 14px', fontSize: 13, fontWeight: 700, whiteSpace: 'nowrap' }}>
                          {s.label === 'أخرى' ? (e.type_ar || 'أخرى') : s.label}
                        </span>
                      </div>
                      <div style={{ borderTop: '1px solid var(--border)', marginTop: 14, paddingTop: 12, display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                        <span style={{ color: 'var(--muted)' }}>
                          الجذر اللغوي: <b style={{ color: 'var(--ink)' }}>{e.root || 'غير محدد'}</b>
                        </span>
                        <b style={{ color: confColor(conf) }}>دقة {Math.round(conf * 100)}%</b>
                      </div>
                    </article>
                  );
                })}
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}
