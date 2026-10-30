import re
from functools import lru_cache

import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from nltk.stem.isri import ISRIStemmer

# مستخرج الجذور العربية (ما بحتاج تنزيل بيانات إضافية)
stemmer = ISRIStemmer()

MODEL_NAME = "hatmimoha/arabic-ner"

# أقل ثقة مقبولة لعرض الكيان (عدّلوها بعد التجربة على نصوصكم)
MIN_SCORE = 0.3

# طول الجزء "المملوك" بالحروف. الموديل بياخد الجزء + سياق من كل طرف،
# يعني الطول الفعلي = MAX_CHARS + 2 * OVERLAP (لازم يظل تحت حد 512 توكن)
MAX_CHARS = 700

OVERLAP = 150

ENTITY_TYPE_AR = {
    "PERSON": "شخص",
    "ORGANIZATION": "مؤسسة",
    "LOCATION": "موقع جغرافي",
    "DISEASE": "مرض",
    "DATE": "تاريخ",
    "EVENT": "حدث",
    "PRODUCT": "منتج",
    "COMPETITION": "مسابقة",
    "PRICE": "سعر",
    "TERM": "مصطلح علمي",
}

SENTENCE_END = ".!؟?\n"


@lru_cache(maxsize=1)
def get_ner():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, model_max_length=512)

    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_NAME,
        dtype=torch.float32,
    )

    model.to("cpu")
    model.eval()

    # استخدام استراتيجية التجميع الآلية أولاً لمنع مشكلة ## نهائياً
    return pipeline(
        "ner",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="first",
        device=-1,
    )


def split_text(text, max_chars=MAX_CHARS):
    """
    يقسم النص الطويل لأجزاء، ويفضّل القص عند نهاية جملة أو عند فراغ.
    يرجّع قائمة من (offset, chunk) حتى نرجّع المواقع للنص الأصلي.
    """
    chunks = []
    pos = 0
    n = len(text)

    while pos < n:
        end = min(pos + max_chars, n)

        if end < n:
            window = text[pos:end]
            cut = max(window.rfind(c) for c in SENTENCE_END)

            if cut < max_chars // 2:  # ما في نهاية جملة مناسبة، نقص عند فراغ
                cut = window.rfind(" ")

            if cut > 0:
                end = pos + cut + 1

        chunks.append((pos, text[pos:end]))
        pos = end

    return chunks


def classify_subtype(text, entity_type):
    if entity_type != "ORGANIZATION":
        return None, None

    value = text.strip()

    rules = [
        ("UNIVERSITY", "جامعة", ["جامعة", "الجامعة"]),
        ("COLLEGE", "كلية", ["كلية", "الكليّة"]),
        ("SCHOOL", "مدرسة", ["مدرسة", "المدرسة"]),
        ("INSTITUTE", "معهد", ["معهد", "المعهد", "مركز", "المركز"]),
        (
            "GOVERNMENT_AGENCY",
            "جهة حكومية",
            ["وزارة", "هيئة", "مؤسسة حكومية", "وكالة"],
        ),
        (
            "HEALTHCARE_FACILITY",
            "مؤسسة صحية",
            ["مستشفى", "مركز صحي", "عيادة"],
        ),
        (
            "COMPANY",
            "شركة",
            ["شركة", "شركات", "مؤسسة تجارية", "جريدة", "صحيفة"],
        ),
    ]

    for subtype, label_ar, keywords in rules:
        if any(keyword in value for keyword in keywords):
            return subtype, label_ar

    return None, None


# أنواع ما منستخرج إلها جذر (تواريخ وأسعار مش كلمات لغوية)
NO_ROOT_TYPES = {"DATE", "PRICE"}
ARABIC_WORD = re.compile(r"[\u0621-\u064A]+")


def extract_root(entity_text, entity_type):
    """يرجّع الجذر اللغوي للكيان (لكل كلمة عربية فيه) أو None."""
    if entity_type in NO_ROOT_TYPES:
        return None

    roots = [stemmer.stem(w) for w in ARABIC_WORD.findall(entity_text)]
    roots = [r for r in roots if r]
    return " ".join(roots) if roots else None


# ---------- طبقة قواعد للمصطلحات العلمية (بتكمّل الموديل) ----------
AR = r"[\u0621-\u064A]"
TERM_PATTERNS = [
    # فيتامين ج / فيتامين سي / فيتامين ب12
    rf"فيتامين(?:ات)?\s+{AR}{{1,3}}\d*(?!{AR})",
    # حمض الأسكوربيك
    rf"حمض\s+{AR}+",
    # مضادات الأكسدة / مضاد حيوي
    rf"مضاد(?:ات)?\s+(?:الأكسدة|الاكسدة|حيوي(?:ة)?|الالتهاب(?:ات)?)",
    # معادن وعناصر شائعة
    rf"(?:عنصر|معدن)\s+{AR}{{3,}}",
]
TERM_RE = [re.compile(p) for p in TERM_PATTERNS]


def apply_term_rules(text, entities):
    """يضيف مصطلحات علمية ما لقاها الموديل، بدون ما يتداخل مع كيانات موجودة."""
    taken = [(e["start"], e["end"]) for e in entities]
    for rx in TERM_RE:
        for m in rx.finditer(text):
            start, end = m.start(), m.end()
            if any(start < b and end > a for a, b in taken):
                continue
            taken.append((start, end))
            entities.append({
                "text": text[start:end],
                "start": start,
                "end": end,
                "type": "TERM",
                "type_ar": ENTITY_TYPE_AR["TERM"],
                "subtype": None,
                "subtype_ar": None,
                "root": extract_root(text[start:end], "TERM"),
                "confidence": 0.9,
                "source": "rule",
            })
    entities.sort(key=lambda e: e["start"])
    return entities


def analyze_text(text):
    """
    يرجّع قائمة كيانات، كل كيان فيه:
    text, start, end (مواقع بالنص الأصلي), type, type_ar,
    subtype, subtype_ar, root, confidence, source
    """
    if not text or not text.strip():
        return []

    ner = get_ner()
    entities = []
    n = len(text)

    for offset, chunk in split_text(text):
        if not chunk.strip():
            continue

        own_start = offset
        own_end = offset + len(chunk)

        # الموديل بياخد الجزء + سياق من الطرفين
        ctx_start = max(0, own_start - OVERLAP)
        ctx_end = min(n, own_end + OVERLAP)
        window = text[ctx_start:ctx_end]

        for entity in ner(window):
            score = float(entity["score"])
            if score < MIN_SCORE:
                continue

            # المواقع بالنص الأصلي كامل
            start = int(entity["start"]) + ctx_start
            end = int(entity["end"]) + ctx_start

            # كل جزء "بيملك" الكيانات اللي بتبدأ جواله بس، فما في تكرار
            if not (own_start <= start < own_end):
                continue

            # نأخذ النص من الأصل مش من entity["word"] (أدق للتظليل)
            raw = text[start:end]

            # نشيل الفراغات من الأطراف مع تعديل المواقع
            start += len(raw) - len(raw.lstrip())
            end -= len(raw) - len(raw.rstrip())
            entity_text = text[start:end]

            if len(entity_text) < 2:
                continue

            entity_type = entity["entity_group"]
            subtype, subtype_ar = classify_subtype(entity_text, entity_type)

            entities.append({
                "text": entity_text,
                "start": start,
                "end": end,
                "type": entity_type,
                "type_ar": ENTITY_TYPE_AR.get(entity_type, "نوع آخر"),
                "subtype": subtype,
                "subtype_ar": subtype_ar,
                "root": extract_root(entity_text, entity_type),
                "confidence": round(score, 4),
                "source": "model",
            })

    return apply_term_rules(text, entities)


if __name__ == "__main__":
    import json

    sample = "أعلنت جامعة النجاح الوطنية في نابلس عن مؤتمر حول مرض السكري"
    result = analyze_text(sample)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # اختبار: المواقع لازم تطابق النص الأصلي
    for e in result:
        assert sample[e["start"]:e["end"]] == e["text"], f"موقع غلط: {e}"
    print("OK: كل المواقع صحيحة")
