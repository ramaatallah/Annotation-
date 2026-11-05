import { supabase, supabaseReady } from '../lib/supabase';

// بيانات تجريبية للزائر (Demo User)
export const DEMO_ITEMS = [
  { id: 'd1', text: 'جامعة النجاح الوطنية', type: 'ORG', root: 'نجح', note: 'مؤسسة أكاديمية في نابلس', source: 'news.palestine.org', created_at: '2026-10-20' },
  { id: 'd2', text: 'نابلس', type: 'LOC', root: 'نبلس', note: '', source: 'news.palestine.org', created_at: '2026-10-20' },
  { id: 'd3', text: 'وزارة الصحة', type: 'ORG', root: 'صحح', note: 'جهة رسمية', source: 'health.example.ps', created_at: '2026-10-21' },
  { id: 'd4', text: 'أحمد المنصور', type: 'PER', root: 'نصر', note: '', source: 'health.example.ps', created_at: '2026-10-21' },
  { id: 'd5', text: 'الفيروس التاجي كورونا', type: 'DISEASE', root: 'توج', note: 'للمراجعة في الأطروحة', source: 'health.example.ps', created_at: '2026-10-22' },
];

/**
 * TODO: عدّلي اسم الجدول والأعمدة ليطابقوا Supabase عندكم
 * (انظري apiService.js في الإضافة لمعرفة الاسم الحقيقي).
 */
const TABLE = 'annotations';

export async function fetchLibrary(user) {
  if (user?.isDemo) return DEMO_ITEMS;
  if (!supabaseReady) throw new Error('إعدادات Supabase غير موجودة');

  const { data, error } = await supabase
    .from(TABLE)
    .select('*')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false });

  if (error) throw new Error('تعذّر تحميل المكتبة: ' + error.message);
  return data ?? [];
}

export async function deleteItem(user, id) {
  if (user?.isDemo) return;
  const { error } = await supabase.from(TABLE).delete().eq('id', id).eq('user_id', user.id);
  if (error) throw new Error('تعذّر الحذف: ' + error.message);
}
