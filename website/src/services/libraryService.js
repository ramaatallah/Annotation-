import { supabase, supabaseReady } from '../lib/supabase';

// Demo data for guest/demo mode
export const DEMO_ITEMS = [
  { id: 'd1', text: 'جامعة النجاح الوطنية', type: 'ORG', root: 'نجح', note: 'مؤسسة أكاديمية في نابلس', source: 'news.palestine.org', created_at: '2026-10-20' },
  { id: 'd2', text: 'نابلس', type: 'LOC', root: 'نبلس', note: '', source: 'news.palestine.org', created_at: '2026-10-20' },
  { id: 'd3', text: 'وزارة الصحة', type: 'ORG', root: 'صحح', note: 'جهة رسمية', source: 'health.example.ps', created_at: '2026-10-21' },
  { id: 'd4', text: 'أحمد المنصور', type: 'PER', root: 'نصر', note: '', source: 'health.example.ps', created_at: '2026-10-21' },
  { id: 'd5', text: 'الفيروس التاجي كورونا', type: 'DISEASE', root: 'توج', note: 'للمراجعة في الأطروحة', source: 'health.example.ps', created_at: '2026-10-22' },
];

const TABLE = 'annotations';

export async function fetchLibrary(user) {
  if (user?.isDemo) return DEMO_ITEMS;
  if (!supabaseReady) throw new Error('إعدادات Supabase غير موجودة');

  try {
    // 1. Fetch annotations with joined entities and roots
    let query = supabase
      .from(TABLE)
      .select(`
        id,
        user_id,
        selected_text,
        note,
        url,
        page_title,
        color,
        created_at,
        detected_entities (
          id,
          text,
          category,
          confidence,
          word_roots (
            word,
            root,
            lemma
          )
        )
      `)
      .order('created_at', { ascending: false });

    if (user?.id) {
      // Show user's annotations OR unassigned annotations saved locally/during testing
      query = query.or(`user_id.eq.${user.id},user_id.is.null`);
    }

    const { data, error } = await query;
    if (error) {
      console.warn('Joined query error, falling back to simple query:', error);
      const simple = await supabase.from(TABLE).select('*').order('created_at', { ascending: false });
      if (simple.error) throw new Error('تعذّر تحميل المكتبة: ' + simple.error.message);
      return (simple.data || []).map((ann) => ({
        id: ann.id,
        annotationId: ann.id,
        text: ann.selected_text,
        type: 'CONCEPT',
        root: '—',
        note: ann.note || '',
        source: ann.page_title || (ann.url ? new URL(ann.url).hostname : 'مقال ويب'),
        created_at: ann.created_at,
      }));
    }

    // 2. Format items for display
    const items = [];
    (data || []).forEach((ann) => {
      let hostname = 'مقال ويب';
      try {
        if (ann.url) hostname = new URL(ann.url).hostname;
      } catch (e) {}
      const source = ann.page_title || hostname;

      if (ann.detected_entities && ann.detected_entities.length > 0) {
        ann.detected_entities.forEach((ent) => {
          const root = ent.word_roots && ent.word_roots.length > 0 ? ent.word_roots[0].root : '—';
          items.push({
            id: `ent-${ent.id}`,
            annotationId: ann.id,
            text: ent.text || ann.selected_text,
            type: ent.category || 'CONCEPT',
            root: root || '—',
            note: ann.note || '',
            source: source,
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
          note: ann.note || '',
          source: source,
          created_at: ann.created_at,
        });
      }
    });

    return items;
  } catch (err) {
    throw new Error('تعذّر تحميل المكتبة: ' + err.message);
  }
}

export async function deleteItem(user, id) {
  if (user?.isDemo) return;
  if (!supabaseReady) return;

  let rawId = id;
  if (typeof id === 'string') {
    if (id.startsWith('ann-')) {
      rawId = id.replace('ann-', '');
    } else if (id.startsWith('ent-')) {
      // In this case, delete the entity
      const entId = id.replace('ent-', '');
      const { error } = await supabase.from('detected_entities').delete().eq('id', entId);
      if (error) throw new Error('تعذّر الحذف: ' + error.message);
      return;
    }
  }

  const { error } = await supabase.from(TABLE).delete().eq('id', rawId);
  if (error) {
    const fallback = await supabase.from(TABLE).delete().eq('id', id);
    if (fallback.error) throw new Error('تعذّر الحذف: ' + fallback.error.message);
  }
}
