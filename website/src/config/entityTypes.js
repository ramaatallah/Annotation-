// أنواع الكيانات وألوانها (مأخوذة من تصميم وهج). عدّلي المفاتيح لتطابق entityTypes.js في الإضافة.
// أنواع الكيانات وألوانها المعتمدة في وهج عبر مختلف التخصصات الأكاديمية
export const ENTITY_TYPES = {
  SPECIES: { label: 'كائن حي / نبات', color: '#15803d', bg: '#dcfce7' },
  PHENOMENON: { label: 'ظاهرة علمية', color: '#0284c7', bg: '#e0f2fe' },
  WORK: { label: 'مؤلَّف / وثيقة', color: '#b45309', bg: '#fef3c7' },
  EVENT: { label: 'حدث تاريخي', color: '#b91c1c', bg: '#fee2e2' },
  CHEMICAL: { label: 'مركب كيميائي', color: '#7c3aed', bg: '#ede9fe' },
  ANATOMY: { label: 'عضو / تشريح', color: '#be123c', bg: '#ffe4e6' },
  LAW_RULE: { label: 'قاعدة / نظرية', color: '#4338ca', bg: '#e0e7ff' },
  PERIOD: { label: 'عصر / حقبة', color: '#c2410c', bg: '#ffedd5' },
  ASTRONOMY: { label: 'جرم فلكي', color: '#1e40af', bg: '#dbeafe' },
  ARTIFACT: { label: 'أداة / أثر', color: '#854d0e', bg: '#fef9c3' },
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
  OTHER: { label: 'كيان علمي', color: '#374151', bg: '#f3f4f6' },
  MISC: { label: 'أخرى', color: '#374151', bg: '#f3f4f6' },
};

export const typeInfo = (t) => ENTITY_TYPES[t] ?? { label: t || 'غير مصنّف', color: '#475467', bg: '#eef0f3' };
