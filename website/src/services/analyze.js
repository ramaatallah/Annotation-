// خدمة التواصل مع الـ API: تحليل النص (كيانات + دقة + جذر)
//
// شكل الرد المتوقع من الـ backend (POST {VITE_API_URL}/analyze):
//   body:     { "text": "..." }
//   response: { "entities": [ { "text": "نابلس", "label": "LOC", "score": 0.96, "root": "نبل", "start": 12, "end": 17 } ] }
// start/end اختيارية؛ score يقبل 0-1 أو 0-100.
// إذا ما في VITE_API_URL في ملف .env يشتغل وضع تجريبي (mock) عشان تجرب الواجهة فوراً.

const API_URL = import.meta.env.VITE_API_URL;

export async function analyzeText(text) {
  if (!API_URL) {
    await new Promise((r) => setTimeout(r, 500)); // محاكاة زمن الشبكة
    return { entities: mockEntities(text), mock: true };
  }
  const res = await fetch(`${API_URL}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`فشل الطلب (${res.status})`);
  const data = await res.json();
  return { entities: normalize(text, data.entities ?? []), mock: false };
}

// توحيد الرد: score كنسبة 0-100، وحساب start/end إذا ناقصة
function normalize(text, entities) {
  let cursor = 0;
  return entities
    .map((e) => {
      let { start, end } = e;
      if (start == null || end == null) {
        start = text.indexOf(e.text, cursor);
        if (start === -1) return null;
        end = start + e.text.length;
      }
      cursor = end;
      const score = e.score <= 1 ? e.score * 100 : e.score;
      return { text: e.text, label: e.label, root: e.root ?? '—', score: Math.round(score * 10) / 10, start, end };
    })
    .filter(Boolean)
    .sort((a, b) => a.start - b.start);
}

/* ---------------- وضع تجريبي فقط (احذفه عند ربط الـ API) ---------------- */
const GAZETTEER = [
  { text: 'جامعة النجاح الوطنية', label: 'ORG', root: 'نجح' },
  { text: 'جامعة بيرزيت', label: 'ORG', root: 'برزت' },
  { text: 'نابلس', label: 'LOC', root: 'نبلس' },
  { text: 'رام الله', label: 'LOC', root: 'رمل' },
  { text: 'القدس', label: 'LOC', root: 'قدس' },
  { text: 'فلسطين', label: 'LOC', root: 'فلسطن' },
  { text: 'غزة', label: 'LOC', root: 'غزز' },
  { text: 'محمود درويش', label: 'PER', root: 'حمد' },
  { text: 'غسان كنفاني', label: 'PER', root: 'غسن' },
];

function mockEntities(text) {
  const found = [];
  for (const g of GAZETTEER) {
    let i = text.indexOf(g.text);
    while (i !== -1) {
      const score = 85 + ((i * 7 + g.text.length * 3) % 14) + 0.5; // قيمة ثابتة لكل موضع
      found.push({ ...g, start: i, end: i + g.text.length, score });
      i = text.indexOf(g.text, i + g.text.length);
    }
  }
  found.sort((a, b) => a.start - b.start || b.end - a.end);
  const out = [];
  for (const f of found) if (!out.length || f.start >= out[out.length - 1].end) out.push(f);
  return out;
}
