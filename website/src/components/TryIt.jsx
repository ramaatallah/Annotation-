import { useMemo, useState } from 'react';
import { analyzeText } from '../services/analyze';

const LABELS = {
  PER: { name: 'شخص', bg: '#e9d9ff', fg: '#6a2bb5' },
  LOC: { name: 'مكان', bg: '#d8f5e0', fg: '#1d7a3a' },
  ORG: { name: 'مؤسسة', bg: '#dbe7ff', fg: '#2f4482' },
};
const FALLBACK = { name: 'أخرى', bg: '#eee', fg: '#444' };
const info = (label) => LABELS[label] ?? FALLBACK;

const SAMPLE = 'تواصل جامعة النجاح الوطنية تقديم مبادراتها الأكاديمية في مدينة نابلس، وأقام الشاعر محمود درويش أمسيات في رام الله والقدس.';

const card = { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 28, padding: 28 };

const WandIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M15 4V2M15 16v-2M8 9h2M20 9h2M17.8 11.8L19 13M17.8 6.2L19 5M3 21l9-9M12.2 6.2L11 5" />
  </svg>
);

// تقسيم النص إلى أجزاء: نص عادي / كيان
function toSegments(text, entities) {
  const segs = [];
  let pos = 0;
  for (const e of entities) {
    if (e.start > pos) segs.push({ t: text.slice(pos, e.start) });
    segs.push({ t: text.slice(e.start, e.end), e });
    pos = e.end;
  }
  if (pos < text.length) segs.push({ t: text.slice(pos) });
  return segs;
}

export default function TryIt() {
  const [text, setText] = useState('');
  const [result, setResult] = useState(null); // { text, entities, mock }
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const segments = useMemo(() => (result ? toSegments(result.text, result.entities) : []), [result]);

  async function run() {
    const value = text.trim();
    if (!value) return setError('اكتب نصاً عربياً أولاً.');
    setError('');
    setLoading(true);
    try {
      const { entities, mock } = await analyzeText(value);
      setResult({ text: value, entities, mock });
    } catch (err) {
      setError(err.message || 'تعذّر التحليل، حاول مرة أخرى.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section id="try" className="container" style={{ padding: '48px 20px 80px' }}>
      <h2 style={{ fontSize: 44, fontWeight: 800, lineHeight: 1.3 }}>مختبر تحليل النصوص</h2>
      <p style={{ color: 'var(--muted)', fontSize: 17, margin: '6px 0 36px' }}>
        أدخل أي نص عربي لاختبار تقنية التعرف على الكيانات واستخراج الجذور اللغوية.
      </p>

      <div style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <label htmlFor="try-text" style={{ fontWeight: 700, fontSize: 17 }}>النص المراد تحليله:</label>
          <button onClick={() => setText(SAMPLE)} style={{ font: 'inherit', background: 'none', border: 0, cursor: 'pointer', color: 'var(--navy)', display: 'flex', alignItems: 'center', gap: 6, fontSize: 15 }}>
            <WandIcon /> استخدام نص تجريبي
          </button>
        </div>

        <textarea
          id="try-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="الصق نصًا عربيًا هنا..."
          rows={8}
          style={{ width: '100%', font: 'inherit', fontSize: 18, padding: 20, borderRadius: 20, border: '1.5px solid var(--border)', resize: 'vertical', background: '#fdfcfa', color: 'var(--ink)' }}
        />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 18, gap: 12, flexWrap: 'wrap' }}>
          <button className="btn btn-primary" onClick={run} disabled={loading} style={{ padding: '14px 30px', fontSize: 17 }}>
            {loading ? 'جارٍ التحليل…' : 'حلّل النص'}
          </button>
          {error && <span role="alert" style={{ color: '#b3261e', fontSize: 14 }}>{error}</span>}
          <span style={{ color: 'var(--muted)', fontSize: 15 }}>{text.length} حرف</span>
        </div>
      </div>

      {result && (
        <div style={{ marginTop: 24, display: 'grid', gap: 20 }}>
          {result.mock && (
            <p style={{ fontSize: 13, color: '#8a5a00', background: '#fff3d6', border: '1px solid var(--note-border)', borderRadius: 10, padding: '8px 14px' }}>
              نتائج تجريبية: لم يتم ربط الـ API بعد (أضف VITE_API_URL في ملف .env).
            </p>
          )}

          <div style={card}>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 12, fontSize: 13 }}>
              {Object.values(LABELS).map((v) => (
                <span key={v.name} style={{ background: v.bg, color: v.fg, padding: '2px 10px', borderRadius: 6, fontWeight: 700 }}>{v.name}</span>
              ))}
            </div>
            <p style={{ fontSize: 18, lineHeight: 2.2 }}>
              {segments.map((s, i) =>
                s.e ? (
                  <mark key={i} title={`${info(s.e.label).name} • ${s.e.score}%`} style={{ background: info(s.e.label).bg, color: info(s.e.label).fg, padding: '2px 8px', borderRadius: 6 }}>{s.t}</mark>
                ) : (
                  <span key={i}>{s.t}</span>
                )
              )}
            </p>
          </div>

          <div style={{ ...card, overflowX: 'auto' }}>
            {result.entities.length === 0 ? (
              <p style={{ color: 'var(--muted)' }}>لم يتم العثور على كيانات في هذا النص.</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 16 }}>
                <thead>
                  <tr style={{ textAlign: 'right', color: 'var(--muted)', fontSize: 14 }}>
                    <th style={th}>الكيان</th><th style={th}>التصنيف</th><th style={th}>الدقة</th><th style={th}>الجذر</th>
                  </tr>
                </thead>
                <tbody>
                  {result.entities.map((e, i) => (
                    <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                      <td style={td}>{e.text}</td>
                      <td style={td}>
                        <span style={{ background: info(e.label).bg, color: info(e.label).fg, padding: '2px 10px', borderRadius: 6, fontSize: 13, fontWeight: 700 }}>{info(e.label).name}</span>
                      </td>
                      <td style={td}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{ width: 80, height: 6, background: '#eee', borderRadius: 4 }}>
                            <div style={{ width: `${e.score}%`, height: '100%', background: 'var(--navy)', borderRadius: 4 }} />
                          </div>
                          <span style={{ fontSize: 13 }}>{e.score}%</span>
                        </div>
                      </td>
                      <td style={{ ...td, fontWeight: 700 }}>{e.root}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

const th = { padding: '8px 10px', fontWeight: 500 };
const td = { padding: '10px' };
