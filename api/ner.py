import re
from functools import lru_cache

import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

MODEL_NAME = "hatmimoha/arabic-ner"

# أقل ثقة مقبولة لعرض الكيان (عدّلوها بعد التجربة على نصوصكم)
MIN_SCORE = 0.5

# طول الجزء "المملوك" بالحروف. الموديل بياخد الجزء + سياق من كل طرف،
# يعني الطول الفعلي = MAX_CHARS + 2 * OVERLAP (لازم يظل تحت حد 512 توكن)
MAX_CHARS = 700

# سياق إضافي من كل طرف عشان الكيان اللي على الحد يوصل كامل للموديل
# (لازم يكون أكبر من أطول كيان متوقع عندكم)
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

    return pipeline(
        "ner",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple",
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
        (
            "GOVERNMENT_AGENCY",
            "جهة حكومية",
            ["وزارة", "هيئة حكومية", "مؤسسة حكومية"],
        ),
        (
            "HEALTHCARE_FACILITY",
            "مؤسسة صحية",
            ["مستشفى", "مركز صحي", "عيادة"],
        ),
    ]

    for subtype, label_ar, keywords in rules:
        if any(keyword in value for keyword in keywords):
            return subtype, label_ar

    return None, None


def analyze_text(text):
    """
    يرجّع قائمة كيانات، كل كيان فيه:
    text, start, end (مواقع بالنص الأصلي), type, type_ar,
    subtype, subtype_ar, confidence, source
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

            if not entity_text:
                continue

            original_type = entity["entity_group"]
            subtype, subtype_ar = classify_subtype(entity_text, original_type)

            entities.append({
                "text": entity_text,
                "start": start,
                "end": end,
                "type": original_type,
                "type_ar": ENTITY_TYPE_AR.get(original_type, "نوع آخر"),
                "subtype": subtype,
                "subtype_ar": subtype_ar,
                "confidence": round(score, 4),
                "source": "model",
            })

    return entities


if __name__ == "__main__":
    import json

    sample = "أعلنت جامعة النجاح الوطنية في نابلس عن مؤتمر حول مرض السكري"
    result = analyze_text(sample)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # اختبار: المواقع لازم تطابق النص الأصلي
    for e in result:
        assert sample[e["start"]:e["end"]] == e["text"], f"موقع غلط: {e}"
    print("OK: كل المواقع صحيحة")