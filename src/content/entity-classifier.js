
const ENTITY_RULES = [
  {
    subtype: "UNIVERSITY",
    patterns: [
      /جامعة/u,
      /الجامعة/u,
    ],
  },
  {
    subtype: "COLLEGE",
    patterns: [
      /كلية/u,
      /الكليّة/u,
    ],
  },
  {
    subtype: "SCHOOL",
    patterns: [
      /مدرسة/u,
      /المدرسة/u,
    ],
  },
  {
    subtype: "GOVERNMENT_AGENCY",
    patterns: [
      /وزارة/u,
      /هيئة حكومية/u,
      /مؤسسة حكومية/u,
    ],
  },
  {
    subtype: "HEALTHCARE_FACILITY",
    patterns: [
      /مستشفى/u,
      /مركز صحي/u,
      /عيادة/u,
    ],
  },
];

export function classifyEntity(entity) {
  const text = entity.text?.trim() || "";
  const type = entity.type?.toUpperCase() || "UNKNOWN";

  // لا نصنّف الكيانات غير المؤسسية بهذه القواعد.
  if (!text || type !== "ORGANIZATION") {
    return {
      ...entity,
      type,
      subtype: null,
      classificationSource: "model",
    };
  }

  const rule = ENTITY_RULES.find(({ patterns }) =>
    patterns.some((pattern) => pattern.test(text))
  );

  return {
    ...entity,
    type,
    subtype: rule?.subtype || null,
    classificationSource: rule ? "rule" : "model",
  };
}


