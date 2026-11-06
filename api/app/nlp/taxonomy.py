# -*- coding: utf-8 -*-
"""
Single Source of Truth for Entity Taxonomy & Academic Domains.
Defines entity types, Arabic names, descriptions, and few-shot classification examples.
"""

from typing import Dict, Any, List

TAXONOMY: Dict[str, Dict[str, Any]] = {
    "PERSON": {
        "type_ar": "شخص / علم",
        "description": "أشخاص وعلماء ومفكرون وشخصيات تاريخية",
        "examples": ["ابن خلدون", "ماري كوري", "أحمد زويل"],
        "detector": ["bert", "llm"],
        "default_domain": "history",
    },
    "NORP": {
        "type_ar": "قومية / جماعة / مذهب",
        "description": "قبائل وشعوب ومذاهب وأحزاب وجماعات فكرية أو دينية",
        "examples": ["قريش", "الأشاعرة", "الرومان"],
        "detector": ["llm"],
        "default_domain": "social_sciences",
    },
    "ORGANIZATION": {
        "type_ar": "مؤسسة / منظمة",
        "description": "مؤسسات وشركات ووزارات وهيئات غير أكاديمية",
        "examples": ["منظمة الصحة العالمية", "الأمم المتحدة", "شركة أرامكو"],
        "detector": ["bert", "llm"],
        "default_domain": "general",
    },
    "UNIVERSITY": {
        "type_ar": "جامعة / مؤسسة أكاديمية",
        "description": "جامعات وكليات ومعاهد ومراكز بحث أكاديمية",
        "examples": ["جامعة النجاح الوطنية", "جامعة الأزهر", "معهد ماساتشوستس للتكنولوجيا"],
        "detector": ["llm"],
        "default_domain": "education",
    },
    "LOCATION": {
        "type_ar": "موقع جغرافي",
        "description": "دول ومدن وقرى وتضاريس وجبال وأنهار",
        "examples": ["نابلس", "نهر الأردن", "جبال الأطلس"],
        "detector": ["bert", "llm"],
        "default_domain": "geography",
    },
    "FACILITY": {
        "type_ar": "منشأة / معلم",
        "description": "مبانٍ تاريخية ومستشفيات ومساجد ومتاحف وموانئ",
        "examples": ["مسجد قرطبة", "مستشفى رفيديا", "مكتبة الإسكندرية"],
        "detector": ["llm"],
        "default_domain": "general",
    },
    "EVENT": {
        "type_ar": "حدث تاريخي / مؤتمر",
        "description": "أحداث تاريخية ومعارك ومؤتمرات مسمّاة (أحداث بأسمائها وليس أفعالاً)",
        "examples": ["معركة حطين", "مؤتمر مدريد", "الثورة الصناعية"],
        "detector": ["llm"],
        "default_domain": "history",
    },
    "DATE": {
        "type_ar": "تاريخ / حقبة زمنية",
        "description": "تواريخ وسنوات وقرون وفترات زمنية محددة",
        "examples": ["القرن الثامن الهجري", "1948", "15 مايو"],
        "detector": ["bert", "llm"],
        "default_domain": "history",
    },
    "LAW": {
        "type_ar": "قانون / معاهدة",
        "description": "قوانين ودساتير ومعاهدات واتفاقيات وقرارات رسمية",
        "examples": ["اتفاقية أوسلو", "قانون العمل", "إعلان جنيف"],
        "detector": ["llm"],
        "default_domain": "law",
    },
    "WORK": {
        "type_ar": "مصنف / كتاب / مؤلف",
        "description": "كتب وأبحاث ومجلات ونصوص مقدسة وأعمال فنية",
        "examples": ["المقدمة", "مجلة Nature", "صحيح البخاري"],
        "detector": ["llm"],
        "default_domain": "literature",
    },
    "TITLE": {
        "type_ar": "لقب / منصب",
        "description": "مناصب وألقاب ومهن علمية أو سياسية",
        "examples": ["رئيس الجامعة", "وزير الصحة", "الإمام الأكبر"],
        "detector": ["llm"],
        "default_domain": "general",
    },
    "TECHNOLOGY": {
        "type_ar": "تقنية / نظام برمجيات",
        "description": "برمجيات ونماذج ذكاء اصطناعي وأنظمة وأجهزة رقمية",
        "examples": ["الذكاء الاصطناعي", "PyTorch", "شبكات العصبية العميقة"],
        "detector": ["llm"],
        "default_domain": "technology",
    },
    "PRODUCT": {
        "type_ar": "منتج تجاري",
        "description": "منتجات تجارية وصناعية مسمّاة",
        "examples": ["آيفون", "سيارة تسلا"],
        "detector": ["llm"],
        "default_domain": "technology",
    },
    "SUBSTANCE": {
        "type_ar": "مادة / مركب كيميائي / دواء",
        "description": "مركبات ومواد كيميائية وأدوية وجزيئات وفيتامينات",
        "examples": ["الأسبرين", "فيتامين C", "الكولاجين", "حمض الكبريتيك"],
        "detector": ["llm"],
        "default_domain": "medicine",
    },
    "DISEASE": {
        "type_ar": "مرض / حالة صحية",
        "description": "أمراض وأعراض ومتلازمات وحالات سريرية",
        "examples": ["السكري", "التهاب الكبد", "ارتفاع ضغط الدم"],
        "detector": ["llm"],
        "default_domain": "medicine",
    },
    "ANATOMY": {
        "type_ar": "عضو / نسيج حيوي",
        "description": "أعضاء وأنسجة وخلايا وأجهزة حيوية في الجسم",
        "examples": ["البنكرياس", "العصب الوركي", "عضلة القلب"],
        "detector": ["llm"],
        "default_domain": "medicine",
    },
    "ORGANISM": {
        "type_ar": "كائن حي / نبات / سلالة",
        "description": "كائنات حية ونباتات وبكتيريا وفيروسات وسلالات",
        "examples": ["الإشريكية القولونية", "نخيل التمر", "فيروس كورونا"],
        "detector": ["llm"],
        "default_domain": "agriculture",
    },
    "CONCEPT": {
        "type_ar": "مفهوم / نظرية",
        "description": "مفاهيم مجردة ونظريات علمية ومصطلحات تخصصية",
        "examples": ["الاستدامة", "نظرية النسبية", "العدالة الاجتماعية"],
        "detector": ["llm"],
        "default_domain": "general",
    },
    "METHOD": {
        "type_ar": "منهج / أسلوب بحثي",
        "description": "مناهج بحث وأساليب إحصائية وخوارزميات محددة",
        "examples": ["المنهج الوصفي", "تحليل الانحدار", "التحليل الطيفي"],
        "detector": ["llm"],
        "default_domain": "education",
    },
    "FIELD": {
        "type_ar": "حقل علمي / تخصص",
        "description": "علوم وتخصصات وحقول معرفية",
        "examples": ["علم الاجتماع", "أصول الفقه", "البيولوجيا الجزيئية"],
        "detector": ["llm"],
        "default_domain": "education",
    },
    "QUANTITY": {
        "type_ar": "كمية / قياس",
        "description": "قياسات ونسب وأعداد ومقادير مقرونة بوحداتها",
        "examples": ["5 ملغ", "30%", "100 كيلومتر"],
        "detector": ["bert", "llm"],
        "default_domain": "general",
    },
    "LANGUAGE": {
        "type_ar": "لغة / لهجة",
        "description": "لغات ولهجات تاريخية ومعاصرة",
        "examples": ["الآرامية", "السريانية", "العربية الفصحى"],
        "detector": ["llm"],
        "default_domain": "literature",
    },
    "OTHER": {
        "type_ar": "كيان آخر",
        "description": "مرشح أكاديمي لا يطابق أي تصنيف من السابق ويحتاج مراجعة",
        "examples": [],
        "detector": ["llm"],
        "default_domain": "general",
    },
}

# Specialization mappings: when BERT detects broad category, LLM can specialize
ALLOWED_SPECIALIZATIONS = {
    "ORGANIZATION": ["UNIVERSITY", "FACILITY", "ORGANIZATION"],
    "LOCATION": ["FACILITY", "LOCATION"],
}

# Academic Disciplines / Domains
DOMAINS = [
    "medicine",
    "history",
    "law",
    "literature",
    "technology",
    "agriculture",
    "religious_studies",
    "social_sciences",
    "education",
    "geography",
    "general",
]

# Few-shot examples representing multiple domains
FEW_SHOT_EXAMPLES: List[Dict[str, Any]] = [
    {
        "text": "قام ابن خلدون في كتابه المقدمة بتأسيس علم الاجتماع في تونس عام 1377م.",
        "entities": [
            {"text": "ابن خلدون", "type": "PERSON", "type_ar": "شخص / علم", "subtype_ar": "مؤرخ وفيلسوف", "domain": "history"},
            {"text": "المقدمة", "type": "WORK", "type_ar": "مصنف / كتاب / مؤلف", "subtype_ar": "كتاب تاريخ واجتماع", "domain": "history"},
            {"text": "علم الاجتماع", "type": "FIELD", "type_ar": "حقل علمي / تخصص", "subtype_ar": "علم اجتماعي", "domain": "social_sciences"},
            {"text": "تونس", "type": "LOCATION", "type_ar": "موقع جغرافي", "subtype_ar": "دولة / مدينة", "domain": "geography"},
            {"text": "عام 1377م", "type": "DATE", "type_ar": "تاريخ / حقبة زمنية", "subtype_ar": "تاريخ ميلادي", "domain": "history"},
        ],
    },
    {
        "text": "أثبتت دراسات جامعة النجاح الوطنية أن مركب الأسبرين يخفف من مضاعفات السكري بنسبة 15%.",
        "entities": [
            {"text": "جامعة النجاح الوطنية", "type": "UNIVERSITY", "type_ar": "جامعة / مؤسسة أكاديمية", "subtype_ar": "جامعة حكومية", "domain": "education"},
            {"text": "الأسبرين", "type": "SUBSTANCE", "type_ar": "مادة / مركب كيميائي / دواء", "subtype_ar": "دواء مسكن ومضاد للالتهاب", "domain": "medicine"},
            {"text": "السكري", "type": "DISEASE", "type_ar": "مرض / حالة صحية", "subtype_ar": "مرض مزمن", "domain": "medicine"},
            {"text": "15%", "type": "QUANTITY", "type_ar": "كمية / قياس", "subtype_ar": "نسبة مئوية", "domain": "general"},
        ],
    },
    {
        "text": "تستخدم مكتبة PyTorch في تدريب خوارزميات الذكاء الاصطناعي على أنظمة التعلم العميق.",
        "entities": [
            {"text": "PyTorch", "type": "TECHNOLOGY", "type_ar": "تقنية / نظام برمجيات", "subtype_ar": "مكتبة تعلم آلي", "domain": "technology"},
            {"text": "الذكاء الاصطناعي", "type": "TECHNOLOGY", "type_ar": "تقنية / نظام برمجيات", "subtype_ar": "مجال تقني", "domain": "technology"},
            {"text": "التعلم العميق", "type": "CONCEPT", "type_ar": "مفهوم / نظرية", "subtype_ar": "فرع من فروع التعلم الآلي", "domain": "technology"},
        ],
    },
]
