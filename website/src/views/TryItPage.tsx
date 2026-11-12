'use client';

import { useMemo, useState, useEffect } from 'react';
import { analyzeText } from '@/services/analyze';
import type { AnalysisResult, Entity } from '@/types';

const LABELS: Record<string, { name: string; bg: string; fg: string }> = {
  GEOLOGY: { name: 'تضاريس / علوم الأرض', bg: '#ffedd5', fg: '#c2410c' },
  PERSON: { name: 'شخص', bg: '#e9d9ff', fg: '#6a2bb5' },
  LOCATION: { name: 'مكان', bg: '#d8f5e0', fg: '#1d7a3a' },
  ORGANIZATION: { name: 'مؤسسة', bg: '#dbe7ff', fg: '#2f4482' },
  UNIVERSITY: { name: 'جامعة', bg: '#c7d2fe', fg: '#3730a3' },
  DISEASE: { name: 'مرض', bg: '#ffe0e0', fg: '#a12a2a' },
  MEDICAL_TERM: { name: 'مصطلح طبي', bg: '#fce7f3', fg: '#9d174d' },
  TECHNOLOGY: { name: 'تقنية', bg: '#ccfbf1', fg: '#0f766e' },
  FIELD: { name: 'تخصص', bg: '#e0f2fe', fg: '#0369a1' },
  CONCEPT: { name: 'مفهوم', bg: '#fef3c7', fg: '#92400e' },
  DATE: { name: 'تاريخ', bg: '#ffeccc', fg: '#8a5a00' },
  EVENT: { name: 'حدث', bg: '#d6f3f5', fg: '#15737c' },
  MISC: { name: 'أخرى', bg: '#f3f4f6', fg: '#374151' },
};

const LEGEND = ['GEOLOGY', 'PERSON', 'LOCATION', 'ORGANIZATION', 'UNIVERSITY', 'DATE', 'CONCEPT'];
const FALLBACK = { name: 'أخرى', bg: '#eee', fg: '#444' };
const info = (label: string) => LABELS[label] ?? FALLBACK;

const SAMPLE = 'تواصل جامعة النجاح الوطنية تقديم مبادراتها الأكاديمية في مدينة نابلس، وأقام الشاعر محمود درويش أمسيات في رام الله والقدس.';

const card = { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 28, padding: 28 };
const STORAGE_KEY = 'wahaj_tryit_state';

const WandIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M15 4V2M15 16v-2M8 9h2M20 9h2M17.8 11.8L19 13M17.8 6.2L19 5M3 21l9-9M12.2 6.2L11 5" />
  </svg>
);

interface Segment {
  t: string;
  e?: Entity;
}

function toSegments(text: string, entities: Entity[]): Segment[] {
  const segs: Segment[] = [];
  let pos = 0;
  for (const e of entities) {
    if (e.start > pos) segs.push({ t: text.slice(pos, e.start) });
    segs.push({ t: text.slice(e.start, e.end), e });
    pos = e.end;
  }
  if (pos < text.length) segs.push({ t: text.slice(pos) });
  return segs;
}

export default function TryItPage() {
  const [text, setText] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '');
      return saved?.text || '';
    } catch { return ''; }
  });
  const [result, setResult] = useState<AnalysisResult | null>(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '');
      return saved?.result || null;
    } catch { return null; }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (result) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ text, result }));
    }
  }, [text, result]);

  const segments = useMemo(() => (result ? toSegments(result.text, result.entities) : []), [result]);

  async function run() {
    const value = text.trim();
    if (!value) return setError('اكتب نصاً عربياً أولاً.');
    setError('');
    setLoading(true);
    try {
      const { entities, allRoots, mock } = await analyzeText(value);
      setResult({ text: value, entities, allRoots: allRoots || [], mock });
    } catch (err: any) {
      setError(err.message || 'تعذّر التحليل، حاول مرة أخرى.');
    } finally {
      setLoading(false);
    }
  }

  function clearResult() {
    setResult(null);
    localStorage.removeItem(STORAGE_KEY);
  }

  return (
    <section id="try" className="container" style={{ padding: '48px 20px 80px' }}>
      <h2 style={{ fontSize: 44, fontWeight: 800, lineHeight: 1.3, color: 'var(--ink)' }}>مختبر تحليل النصوص</h2>
      <p style={{ color: 'var(--muted)', fontSize: 17, margin: '6px 0 36px' }}>
        أدخل أي نص عربي لاختبار تقنية التعرف على الكيانات واستخراج الجذور اللغوية.
      </p>

      <div style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <label htmlFor="try-text" style={{ fontWeight: 700, fontSize: 17, color: 'var(--ink)' }}>النص المراد تحليله:</label>
          <button onClick={() => setText(SAMPLE)} style={{ font: 'inherit', background: 'none', border: 0, cursor: 'pointer', color: 'var(--navy)', display: 'flex', alignItems: 'center', gap: 6, fontSize: 15, fontWeight: 700 }}>
            <WandIcon /> استخدام نص تجريبي
          </button>
        </div>

        <textarea
          id="try-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="الصق نصًا عربيًا هنا..."
          rows={8}
          style={{ width: '100%', font: 'inherit', fontSize: 18, padding: 20, borderRadius: 20, border: '1.5px solid var(--border)', resize: 'vertical', background: 'var(--bg)', color: 'var(--ink)' }}
        />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 18, gap: 12, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn btn-primary" onClick={run} disabled={loading} style={{ padding: '14px 30px', fontSize: 17 }}>
              {loading ? 'جارٍ التحليل…' : 'حلّل النص'}
            </button>
            {result && (
              <button className="btn btn-outline" onClick={clearResult} style={{ padding: '14px 20px', fontSize: 15 }}>
                مسح النتائج
              </button>
            )}
          </div>
          {error && <span role="alert" style={{ color: '#b3261e', fontSize: 14 }}>{error}</span>}
          <span style={{ color: 'var(--muted)', fontSize: 15 }}>{text.length} حرف</span>
        </div>
      </div>

      {result && (
        <div style={{ marginTop: 24, display: 'grid', gap: 20 }}>
          {result.mock && (
            <p style={{ fontSize: 13, color: '#8a5a00', background: 'var(--note-bg)', border: '1px solid var(--note-border)', borderRadius: 10, padding: '8px 14px' }}>
              نتائج تجريبية: لم يتم ربط الـ API بعد (أضف NEXT_PUBLIC_API_URL في ملف .env.local).
            </p>
          )}

          <div style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <h3 style={{ fontSize: 17, fontWeight: 700, margin: 0, color: 'var(--ink)' }}>النص المظلّل</h3>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', fontSize: 13 }}>
                {LEGEND.map((k) => LABELS[k]).filter(Boolean).map((v) => (
                  <span key={v.name} style={{ background: v.bg, color: v.fg, padding: '2px 10px', borderRadius: 6, fontWeight: 700 }}>{v.name}</span>
                ))}
              </div>
            </div>
            <div style={{
              maxHeight: 280,
              overflowY: 'auto',
              padding: 16,
              borderRadius: 14,
              background: 'var(--bg)',
              border: '1px solid var(--border)',
              lineHeight: 2.4,
              fontSize: 18,
            }}>
              {segments.map((s, i) =>
                s.e ? (
                  <mark key={i} title={`${info(s.e.label).name} • ${s.e.score}%`} style={{ background: info(s.e.label).bg, color: info(s.e.label).fg, padding: '2px 8px', borderRadius: 6, whiteSpace: 'nowrap' }}>{s.t}</mark>
                ) : (
                  <span key={i} style={{ color: 'var(--ink)' }}>{s.t}</span>
                )
              )}
            </div>
          </div>

          <div style={{ ...card, overflowX: 'auto' }}>
            <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 14, color: 'var(--ink)' }}>الكيانات المكتشفة ({result.entities.length})</h3>
            {result.entities.length === 0 ? (
              <p style={{ color: 'var(--muted)' }}>لم يتم العثور على كيانات في هذا النص.</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 16 }}>
                <thead>
                  <tr style={{ textAlign: 'right', color: 'var(--muted)', fontSize: 14 }}>
                    <th style={th}>الكيان</th><th style={th}>التصنيف</th><th style={th}>الدقة</th><th style={th}>الجذور</th>
                  </tr>
                </thead>
                <tbody>
                  {result.entities.map((e, i) => (
                    <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                      <td style={{ ...td, whiteSpace: 'nowrap', fontWeight: 600, color: 'var(--ink)' }}>{e.text}</td>
                      <td style={td}>
                        <span style={{ background: info(e.label).bg, color: info(e.label).fg, padding: '2px 10px', borderRadius: 6, fontSize: 13, fontWeight: 700, whiteSpace: 'nowrap' }}>{info(e.label).name}</span>
                      </td>
                      <td style={td}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{ width: 80, height: 6, background: '#eee', borderRadius: 4 }}>
                            <div style={{ width: `${e.score}%`, height: '100%', background: 'var(--navy)', borderRadius: 4 }} />
                          </div>
                          <span style={{ fontSize: 13, color: 'var(--muted)' }}>{e.score}%</span>
                        </div>
                      </td>
                      <td style={td}>
                        {e.roots && e.roots.length > 0 ? (
                          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                            {e.roots.map((r, j) => (
                              <span key={j} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, padding: '2px 8px', fontSize: 13, whiteSpace: 'nowrap', color: 'var(--ink)' }}>
                                {r.word} → <strong style={{ color: 'var(--navy)' }}>{r.root}</strong>
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span style={{ color: 'var(--muted)', fontSize: 13 }}>—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {result.allRoots && result.allRoots.length > 0 && (
            <div style={card}>
              <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 14, color: 'var(--ink)' }}>الجذور اللغوية ({result.allRoots.length})</h3>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {result.allRoots.map((r, i) => (
                  <div key={i} style={{
                    background: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 10,
                    padding: '6px 14px',
                    textAlign: 'center',
                    fontSize: 14,
                  }}>
                    <div style={{ color: 'var(--muted)', fontSize: 12 }}>{r.word}</div>
                    <div style={{ fontWeight: 800, color: 'var(--navy)', fontSize: 16 }}>{r.root}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

const th = { padding: '8px 10px', fontWeight: 500 };
const td = { padding: '10px' };
