import type { AuthUser, LibraryItem } from '@/types';
import { supabase, supabaseReady } from '@/lib/supabase';

export const DEMO_ITEMS: LibraryItem[] = [
  { id: 'd1', text: 'جامعة النجاح الوطنية', type: 'ORGANIZATION', root: 'نجح', note: 'مؤسسة أكاديمية في نابلس', source: 'news.palestine.org', created_at: '2026-10-20' },
  { id: 'd2', text: 'نابلس',                type: 'LOCATION',     root: 'نبلس', note: '', source: 'news.palestine.org', created_at: '2026-10-20' },
  { id: 'd3', text: 'وزارة الصحة',          type: 'ORGANIZATION', root: 'صحح',  note: 'جهة رسمية', source: 'health.example.ps', created_at: '2026-10-21' },
  { id: 'd4', text: 'أحمد المنصور',         type: 'PERSON',       root: 'نصر',  note: '', source: 'health.example.ps', created_at: '2026-10-21' },
  { id: 'd5', text: 'الفيروس التاجي كورونا',type: 'DISEASE',      root: 'توج',  note: 'للمراجعة في الأطروحة', source: 'health.example.ps', created_at: '2026-10-22' },
];

const TABLE = 'annotations';

export async function fetchLibrary(user: AuthUser): Promise<LibraryItem[]> {
  if (user?.isDemo) return DEMO_ITEMS;
  if (!supabaseReady || !supabase) throw new Error('إعدادات Supabase غير موجودة');

  try {
    let query = supabase
      .from(TABLE)
      .select(`id, user_id, selected_text, note, url, page_title, created_at,
               detected_entities ( id, text, category, label_ar, confidence,
                 word_roots ( word, root ) )`)
      .order('created_at', { ascending: false });

    if (user?.id) {
      query = query.or(`user_id.eq.${user.id},user_id.is.null`);
    }

    const { data, error } = await query;
    if (error) throw error;

    const items: LibraryItem[] = [];
    (data ?? []).forEach((ann: any) => {
      let hostname = 'مقال ويب';
      try { if (ann.url) hostname = new URL(ann.url).hostname; } catch {}
      const source = ann.page_title || hostname;

      if (ann.detected_entities?.length) {
        ann.detected_entities.forEach((ent: any) => {
          const root = ent.word_roots?.[0]?.root ?? '—';
          items.push({
            id: `ent-${ent.id}`,
            annotationId: ann.id,
            text: ent.text || ann.selected_text,
            type: ent.category ?? 'CONCEPT',
            label_ar: ent.label_ar,
            root,
            note: ann.note ?? '',
            source,
            created_at: ann.created_at,
          });
        });
      } else {
        items.push({
          id: `ann-${ann.id}`,
          annotationId: ann.id,
          text: ann.selected_text,
          type: 'CONCEPT',
          root: '—',
          note: ann.note ?? '',
          source,
          created_at: ann.created_at,
        });
      }
    });

    return items;
  } catch (err: any) {
    throw new Error('تعذّر تحميل المكتبة: ' + err.message);
  }
}

export async function deleteItem(user: AuthUser, id: string): Promise<void> {
  if (user?.isDemo || !supabaseReady || !supabase) return;

  if (id.startsWith('ent-')) {
    const entId = id.replace('ent-', '');
    const { error } = await supabase.from('detected_entities').delete().eq('id', entId);
    if (error) throw new Error('تعذّر الحذف: ' + error.message);
    return;
  }

  const rawId = id.startsWith('ann-') ? id.replace('ann-', '') : id;
  const { error } = await supabase.from(TABLE).delete().eq('id', rawId);
  if (error) throw new Error('تعذّر الحذف: ' + error.message);
}
