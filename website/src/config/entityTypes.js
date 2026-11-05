// أنواع الكيانات وألوانها (مأخوذة من تصميم وهج). عدّلي المفاتيح لتطابق entityTypes.js في الإضافة.
export const ENTITY_TYPES = {
  ORG: { label: 'مؤسسة', color: '#6a2bb5', bg: '#efe3ff' },
  LOC: { label: 'مكان', color: '#1d7a3a', bg: '#d8f5e0' },
  PER: { label: 'شخص', color: '#1f5fbf', bg: '#dbeafe' },
  DISEASE: { label: 'مرض / حالة', color: '#b42318', bg: '#fde2e0' },
  DATE: { label: 'تاريخ', color: '#9a5b00', bg: '#ffecc7' },
};

export const typeInfo = (t) => ENTITY_TYPES[t] ?? { label: t || 'غير مصنّف', color: '#475467', bg: '#eef0f3' };
