import type { AnalysisResult, Entity, Root } from '@/types';

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? '').trim().replace(/\/+$/, '');
const LABEL_ALIAS: Record<string, string> = {
  PER: 'PERSON', LOC: 'LOCATION', ORG: 'ORGANIZATION',
};

export async function analyzeText(text: string): Promise<AnalysisResult> {
  if (!API_URL) {
    await new Promise((r) => setTimeout(r, 400));
    return { text, entities: mockEntities(text), allRoots: [], mock: true };
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
  } catch {
    throw new Error('تعذّر الاتصال بالسيرفر. تأكد أنه شغّال وأن NEXT_PUBLIC_API_URL صحيح.');
  }
  if (!res.ok) throw new Error(`فشل الطلب (${res.status})`);

  const data = await res.json();
  const entities = normalize(text, data.entities ?? []);
  const allRoots: Root[] = data.all_roots ?? [];

  return { text, entities, allRoots, mock: false };
}

function normalize(text: string, entities: any[]): Entity[] {
  let cursor = 0;
  const out: Entity[] = [];

  for (const e of entities) {
    let start: number = e.start_char ?? e.start;
    let end: number   = e.end_char   ?? e.end;
    if (start == null || end == null) {
      start = text.indexOf(e.text, cursor);
      if (start === -1) continue;
      end = start + e.text.length;
    }
    if (start < 0 || end > text.length || end <= start) continue;
    cursor = end;

    const rawLabel = e.category ?? e.label ?? e.type ?? 'OTHER';
    const rawScore = Number(e.confidence ?? e.score ?? 0);
    const score    = rawScore <= 1 ? rawScore * 100 : rawScore;
    const roots: Root[] = (e.roots ?? []).filter((r: Root) => r.root);

    out.push({
      text:  text.slice(start, end),
      label: LABEL_ALIAS[rawLabel] ?? rawLabel,
      roots,
      score: Math.round(score * 10) / 10,
      start,
      end,
    });
  }

  out.sort((a, b) => a.start - b.start || b.end - a.end);
  return out.filter((e, i) => i === 0 || e.start >= out[i - 1].end);
}

// ─── Mock / Offline gazetteer (same logic as original JS) ───────────────────

const GAZETTEER: [string, string, string][] = [
  ['جامعة النجاح الوطنية','UNIVERSITY','نجح'],['جامعة بيرزيت','UNIVERSITY','برزت'],
  ['الأمم المتحدة','ORGANIZATION','أمم'],['نابلس','LOCATION','نبلس'],
  ['رام الله','LOCATION','رمل'],['القدس','LOCATION','قدس'],
  ['فلسطين','LOCATION','فلسطن'],['غزة','LOCATION','غزز'],
  ['محمود درويش','PERSON','حمد'],['غسان كنفاني','PERSON','غسن'],
];

const AR_WORD = /[\u0621-\u064A\u064B-\u0652\u0670]+/g;
const norm = (s: string) =>
  s.replace(/[\u064B-\u0652\u0670\u0640]/g, '')
   .replace(/[\u0623\u0625\u0622\u0671]/g, 'ا')
   .replace(/\u0649/g, 'ي')
   .replace(/\u0629/g, 'ه');

function mockEntities(text: string): Entity[] {
  const toks = [...text.matchAll(AR_WORD)].map((m) => ({
    start: m.index!, end: m.index! + m[0].length, n: norm(m[0]),
  }));
  const found: Entity[] = [];
  const taken = new Set<number>();

  for (const [phrase, label, root] of GAZETTEER) {
    const words = phrase.split(' ').map(norm);
    for (let i = 0; i <= toks.length - words.length; i++) {
      if (taken.has(i)) continue;
      if (words.every((w, k) => toks[i + k]?.n === w)) {
        const start = toks[i].start;
        const end   = toks[i + words.length - 1].end;
        found.push({
          text: text.slice(start, end),
          label,
          roots: root ? [{ word: text.slice(start, end), root }] : [],
          score: 88,
          start,
          end,
        });
        for (let k = i; k < i + words.length; k++) taken.add(k);
        break;
      }
    }
  }

  return found.sort((a, b) => a.start - b.start);
}
