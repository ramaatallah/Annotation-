// أنواع الكيانات وألوانها (مأخوذة من تصميم وهج). عدّلي المفاتيح لتطابق entityTypes.js في الإضافة.
export const ENTITY_TYPES = {
  PERSON: { label: 'شخص', color: '#6a2bb5', bg: '#e9d9ff' },
  LOCATION: { label: 'مكان', color: '#1d7a3a', bg: '#d8f5e0' },
  ORGANIZATION: { label: 'مؤسسة', color: '#2f4482', bg: '#dbe7ff' },
  UNIVERSITY: { label: 'جامعة', color: '#3730a3', bg: '#c7d2fe' },
  DISEASE: { label: 'مرض / حالة', color: '#a12a2a', bg: '#ffe0e0' },
  MEDICAL_TERM: { label: 'مصطلح طبي', color: '#9d174d', bg: '#fce7f3' },
  TECHNOLOGY: { label: 'تقنية', color: '#0f766e', bg: '#ccfbf1' },
  FIELD: { label: 'تخصص', color: '#0369a1', bg: '#e0f2fe' },
  CONCEPT: { label: 'مفهوم', color: '#92400e', bg: '#fef3c7' },
  DATE: { label: 'تاريخ', color: '#8a5a00', bg: '#ffeccc' },
  EVENT: { label: 'حدث', color: '#15737c', bg: '#d6f3f5' },
  MISC: { label: 'أخرى', color: '#374151', bg: '#f3f4f6' },
};

export const typeInfo = (t) => ENTITY_TYPES[t] ?? { label: t || 'غير مصنّف', color: '#475467', bg: '#eef0f3' };
