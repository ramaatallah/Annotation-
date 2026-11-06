// خدمة التواصل مع الـ API: تحليل النص (كيانات + دقة + جذر)
//
// الباك إند (api/main.py) بيرد على POST {VITE_API_URL}/analyze بـ:
//   { "entities": [ { "text", "start", "end", "type": "PERSON|ORGANIZATION|LOCATION|...", "confidence": 0.96, ... } ] }
// هالملف بيقبل كمان الشكل البديل: label بدل type، و score بدل confidence، و root.
// إذا ما في VITE_API_URL في ملف .env بيشتغل وضع تجريبي (mock) عشان تجرب الواجهة فوراً.

// نشيل أي "/" بالنهاية عشان ما يصير //analyze
const API_URL = (import.meta.env?.VITE_API_URL ?? '').trim().replace(/\/+$/, '');

// أسماء مختصرة -> الأسماء اللي بيرجّعها الباك إند
const LABEL_ALIAS = { PER: 'PERSON', LOC: 'LOCATION', ORG: 'ORGANIZATION' };

export async function analyzeText(text) {
  if (!API_URL) {
    await new Promise((r) => setTimeout(r, 400)); // محاكاة زمن الشبكة
    return { entities: mockEntities(text), mock: true };
  }

  let res;
  try {
    res = await fetch(`${API_URL}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
  } catch {
    throw new Error('تعذّر الاتصال بالسيرفر. تأكد أنه شغّال وأن VITE_API_URL صحيح.');
  }
  if (!res.ok) throw new Error(`فشل الطلب (${res.status})`);

  const data = await res.json();
  const list = Array.isArray(data) ? data : data.entities ?? [];
  return { entities: normalize(text, list), mock: false };
}

// توحيد الرد: label/score/root موحّدة، وحساب start/end إذا ناقصة، وحذف التداخل
function normalize(text, entities) {
  let cursor = 0;
  const out = [];
  for (const e of entities) {
    let { start, end } = e;
    if (start == null || end == null) {
      start = text.indexOf(e.text, cursor);
      if (start === -1) continue;
      end = start + e.text.length;
    }
    if (start < 0 || end > text.length || end <= start) continue;
    cursor = end;

    const rawLabel = e.label ?? e.type ?? 'OTHER';
    const rawScore = Number(e.score ?? e.confidence ?? 0);
    const score = rawScore <= 1 ? rawScore * 100 : rawScore;
    out.push({
      text: text.slice(start, end),
      label: LABEL_ALIAS[rawLabel] ?? rawLabel,
      root: e.root ?? '—',
      score: Math.round(score * 10) / 10,
      start,
      end,
    });
  }
  out.sort((a, b) => a.start - b.start || b.end - a.end);
  // نمنع التداخل (وإلا التظليل بيتخربط)
  return out.filter((e, i) => i === 0 || e.start >= out[i - 1].end);
}

/* ---------------- وضع تجريبي فقط (احذفه عند ربط الـ API) ----------------
   قبل: كان بيعرف 9 أسماء ثابتة بس، فأي نص تاني يطلع "ما في كيانات".
   هلأ: قاموس أكبر + قواعد بسيطة (جامعة X، مدينة X، الشاعر X ...) + تعامل مع
   التشكيل وأشكال الألف والسوابق (و/ب/ل/ف/ك) والـ "ال". */

const GAZETTEER = [
  // مؤسسات
  ['جامعة النجاح الوطنية', 'ORGANIZATION', 'نجح'], ['جامعة بيرزيت', 'ORGANIZATION', 'برزت'],
  ['جامعة القدس', 'ORGANIZATION', 'قدس'], ['جامعة الخليل', 'ORGANIZATION', 'خلل'],
  ['الأمم المتحدة', 'ORGANIZATION', 'أمم'], ['منظمة الصحة العالمية', 'ORGANIZATION', 'صحح'],
  ['الجامعة العربية', 'ORGANIZATION', 'عرب'], ['الهلال الأحمر', 'ORGANIZATION', 'هلل'],
  // أماكن
  ['نابلس', 'LOCATION', 'نبلس'], ['رام الله', 'LOCATION', 'رمل'], ['القدس', 'LOCATION', 'قدس'],
  ['فلسطين', 'LOCATION', 'فلسطن'], ['غزة', 'LOCATION', 'غزز'], ['الخليل', 'LOCATION', 'خلل'],
  ['بيت لحم', 'LOCATION', 'بيت'], ['جنين', 'LOCATION', 'جنن'], ['طولكرم', 'LOCATION', 'طلكرم'],
  ['قلقيلية', 'LOCATION', 'قلقل'], ['أريحا', 'LOCATION', 'ريح'], ['سلفيت', 'LOCATION', 'سلفت'],
  ['طوباس', 'LOCATION', 'طبس'], ['يافا', 'LOCATION', 'يفو'], ['حيفا', 'LOCATION', 'حيف'],
  ['عكا', 'LOCATION', 'عكك'], ['الناصرة', 'LOCATION', 'نصر'], ['الأردن', 'LOCATION', 'ردن'],
  ['عمان', 'LOCATION', 'عمن'], ['لبنان', 'LOCATION', 'لبن'], ['بيروت', 'LOCATION', 'برت'],
  ['سوريا', 'LOCATION', 'سور'], ['دمشق', 'LOCATION', 'دمشق'], ['مصر', 'LOCATION', 'مصر'],
  ['القاهرة', 'LOCATION', 'قهر'], ['العراق', 'LOCATION', 'عرق'], ['بغداد', 'LOCATION', 'بغد'],
  ['السعودية', 'LOCATION', 'سعد'], ['الرياض', 'LOCATION', 'ريض'], ['قطر', 'LOCATION', 'قطر'],
  ['الدوحة', 'LOCATION', 'دوح'], ['الكويت', 'LOCATION', 'كوت'], ['الإمارات', 'LOCATION', 'أمر'],
  ['تونس', 'LOCATION', 'تنس'], ['الجزائر', 'LOCATION', 'جزر'], ['المغرب', 'LOCATION', 'غرب'],
  ['ليبيا', 'LOCATION', 'ليب'], ['السودان', 'LOCATION', 'سود'], ['اليمن', 'LOCATION', 'يمن'],
  ['تركيا', 'LOCATION', 'ترك'], ['أمريكا', 'LOCATION', 'أمرك'], ['أوروبا', 'LOCATION', 'أرب'],
  ['لندن', 'LOCATION', 'لند'], ['باريس', 'LOCATION', 'برس'], ['واشنطن', 'LOCATION', 'وشن'],
  // أشخاص
  ['محمود درويش', 'PERSON', 'حمد'], ['غسان كنفاني', 'PERSON', 'غسن'], ['إدوارد سعيد', 'PERSON', 'سعد'],
  ['فدوى طوقان', 'PERSON', 'فدي'], ['سميح القاسم', 'PERSON', 'سمح'], ['ناجي العلي', 'PERSON', 'نجو'],
  ['إبراهيم طوقان', 'PERSON', 'برهم'], ['جبرا إبراهيم جبرا', 'PERSON', 'جبر'],
  ['نزار قباني', 'PERSON', 'نزر'], ['أم كلثوم', 'PERSON', 'كلثم'], ['ياسر عرفات', 'PERSON', 'يسر'],
];

/* eslint-disable no-misleading-character-class -- نقصد حروف التشكيل المركّبة عن قصد */
const AR_WORD = /[\u0621-\u064A\u064B-\u0652\u0670]+/g;
const norm = (s) =>
  s.replace(/[\u064B-\u0652\u0670\u0640]/g, '').replace(/[\u0623\u0625\u0622\u0671]/g, 'ا').replace(/\u0649/g, 'ي').replace(/\u0629/g, 'ه');
/* eslint-enable no-misleading-character-class */
const hasAl = (n) => n.startsWith('ال') && n.length > 3;
const stripAl = (n) => (hasAl(n) ? n.slice(2) : n);
const wordsOf = (s) => norm(s).split(/\s+/).map((w) => ({ core: stripAl(w), al: hasAl(w) }));

const ENTRIES = GAZETTEER.map(([t, label, root]) => ({ label, root, words: wordsOf(t) })).sort(
  (a, b) => b.words.length - a.words.length
);

const ORG_TRIG = new Set(['جامعة', 'كلية', 'وزارة', 'شركة', 'مستشفى', 'مدرسة', 'بلدية', 'مركز', 'معهد', 'هيئة', 'نادي', 'منظمة', 'مؤسسة', 'اتحاد', 'نقابة', 'صحيفة', 'جريدة'].map(norm));
const LOC_TRIG = new Set(['مدينة', 'قرية', 'محافظة', 'مخيم', 'دولة', 'بلدة', 'منطقة'].map(norm));
const PER_TRIG = new Set(['شاعر', 'كاتب', 'روائي', 'دكتور', 'دكتورة', 'استاذ', 'استاذة', 'رئيس', 'وزير', 'مهندس', 'مهندسة', 'سيد', 'سيدة', 'فنان', 'اديب', 'باحث', 'شيخ', 'ملك', 'امير', 'شهيد', 'مناضل', 'قائد', 'صحفي', 'شاعرة', 'كاتبة', 'نائب', 'محامي', 'قاضي'].map(norm));
const COMPOUND = new Set(['بيت', 'عين', 'دير', 'خربه', 'كفر', 'ام', 'ابو', 'راس', 'جبل', 'وادي', 'عبد', 'ابن', 'بن'].map(norm));
const STOP = new Set(['في', 'من', 'على', 'الي', 'عن', 'مع', 'و', 'ثم', 'حول', 'بعد', 'قبل', 'عند', 'هذا', 'هذه', 'ان', 'انه', 'التي', 'الذي', 'قد', 'لقد', 'كان', 'كانت', 'او', 'لكن', 'قال', 'قالت'].map(norm));

// احتمالات الكلمة: بدون سابقة، أو مع سابقة (و/ب/ل/ف/ك)، أو "لل"، أو "ول"/"وب"...
function variants(tok, n = tok.n, shift = 0) {
  const out = [{ core: stripAl(n), shift, al: hasAl(n), pref: shift > 0 }];
  if (n.length > 3) {
    if ('وبلفك'.includes(n[0])) {
      out.push(...variants(tok, n.slice(1), shift + 1));
      if (n.startsWith('لل')) out.push({ core: n.slice(2), shift, al: true, pref: true });
    }
  }
  return out;
}
const matchTok = (tok, w, allowPrefix) =>
  variants(tok).find((v) => (allowPrefix || !v.pref) && v.core === w.core && (!w.al || v.al));

const adjacent = (text, a, b) => text.slice(a.end, b.start).trim() === '';

function mockEntities(text) {
  const toks = [...text.matchAll(AR_WORD)].map((m) => ({
    start: m.index, end: m.index + m[0].length, n: norm(m[0]),
  }));
  const found = [];
  const taken = new Set();
  const add = (i, j, shift, label, root) => {
    const start = toks[i].start + shift;
    const end = toks[j].end;
    const score = 82 + ((start * 7 + (end - start) * 3) % 15) + 0.5; // قيمة ثابتة لكل موضع
    found.push({ text: text.slice(start, end), label, root, start, end, score });
    for (let k = i; k <= j; k++) taken.add(k);
  };

  // 1) القاموس
  for (let i = 0; i < toks.length; i++) {
    if (taken.has(i)) continue;
    for (const en of ENTRIES) {
      const last = i + en.words.length - 1;
      if (last >= toks.length) continue;
      const first = matchTok(toks[i], en.words[0], true);
      if (!first) continue;
      let ok = true;
      for (let k = 1; k < en.words.length && ok; k++) {
        ok = adjacent(text, toks[i + k - 1], toks[i + k]) && !!matchTok(toks[i + k], en.words[k], false);
      }
      if (ok) { add(i, last, first.shift, en.label, en.root); i = last; break; }
    }
  }

  // 2) قواعد بسيطة: جامعة X / مدينة X / الشاعر X
  const nextOk = (i) => i < toks.length && !taken.has(i) && adjacent(text, toks[i - 1], toks[i]) && !STOP.has(toks[i].n);
  for (let i = 0; i < toks.length; i++) {
    if (taken.has(i)) continue;
    const v = variants(toks[i]).find((x) => ORG_TRIG.has(x.core) || LOC_TRIG.has(x.core) || PER_TRIG.has(x.core));
    if (!v) continue;

    if (ORG_TRIG.has(v.core)) {
      if (!nextOk(i + 1) || (v.al && !hasAl(toks[i + 1].n))) continue;
      let j = i + 1;
      while (j + 1 < toks.length && j - i < 3 && nextOk(j + 1) && /^(وال|ال)/.test(toks[j + 1].n)) j++;
      add(i, j, v.shift, 'ORGANIZATION', '—');
      i = j;
    } else if (LOC_TRIG.has(v.core)) {
      if (v.al || !nextOk(i + 1)) continue;
      const j = COMPOUND.has(stripAl(toks[i + 1].n)) && nextOk(i + 2) ? i + 2 : i + 1;
      add(i + 1, j, 0, 'LOCATION', '—');
      i = j;
    } else {
      if (!nextOk(i + 1)) continue;
      const j = COMPOUND.has(toks[i + 1].n) && nextOk(i + 2) ? i + 2 : i + 1;
      add(i + 1, j, 0, 'PERSON', '—');
      i = j;
    }
  }

  return found.sort((a, b) => a.start - b.start);
}
