import re
from functools import lru_cache

import re
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import nltk
from nltk.stem.isri import ISRIStemmer

# Download basic NLTK data if not already present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Initialize Arabic root stemmer
stemmer = ISRIStemmer()

MODEL_NAME = "hatmimoha/arabic-ner"

# أقل ثقة مقبولة لعرض الكيان (عدّلوها بعد التجربة على نصوصكم)
MIN_SCORE = 0.5

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
def smart_merge_entities(results):
    """
    دمج الكلمات المتتالية والمترابطة لنفس الكيان (مثل: جامعة + النجاح + الوطنية)
    ومنع التقطيع أو ظهور أجزاء مشوهة.
    """
    if not results:
        return []

    merged = []
    current_entity = None

    for entity in results:
        raw_word = entity.get("word", "").strip()
        # إزالة أي آثار متبقية للرموز المشوهة
        clean_word = re.sub(r"^##", "", raw_word).strip()
        
        if not clean_word or clean_word in ["[CLS]", "[SEP]", "[UNK]"]:
            continue

        entity_group = entity.get("entity_group", entity.get("entity", "O"))
        base_type = entity_group.split("-")[-1]
        score = float(entity.get("score", 0.0))

        if current_entity is None:
            current_entity = {
                "text": clean_word,
                "type": base_type,
                "scores": [score]
            }
        else:
            # إذا كان الكيان الحالي والكلمة الجديدة ينتميان لنفس النوع، ندمجهما بمسافة
            if base_type == current_entity["type"]:
                # إذا كانت الكلمة تبدأ بـ ## أصلية ندمجها بدون مسافة، وإلا ندمج بمسافة
                if raw_word.startswith("##"):
                    current_entity["text"] += clean_word
                else:
                    current_entity["text"] += " " + clean_word
                current_entity["scores"].append(score)
            else:
                # إغلاق الكيان السابق وإضافته للقائمة
                avg_score = sum(current_entity["scores"]) / len(current_entity["scores"])
                merged.append({
                    "text": current_entity["text"].strip(),
                    "type": current_entity["type"],
                    "score": avg_score
                })
                # البدء بكيان جديد
                current_entity = {
                    "text": clean_word,
                    "type": base_type,
                    "scores": [score]
                }

    if current_entity:
        avg_score = sum(current_entity["scores"]) / len(current_entity["scores"])
        merged.append({
            "text": current_entity["text"].strip(),
            "type": current_entity["type"],
            "score": avg_score
        })

    return merged


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


def extract_roots_for_text(text, detected_entities=None):
    """
    Extracts triliteral and quadriliteral roots for appropriate words,
    while excluding detected entities (such as names, organizations, and dates).
    """
    if detected_entities is None:
        detected_entities = []

    words = nltk.word_tokenize(text)
    processed_words = []

    for word in words:
        # If the word is a detected entity or punctuation, do not apply stemming
        if word in detected_entities or not word.isalpha():
            processed_words.append(word)
        else:
            processed_words.append(stemmer.stem(word))

    return " ".join(processed_words)


def analyze_text(text):
    """
    يرجّع قائمة كيانات، كل كيان فيه:
    text, start, end (مواقع بالنص الأصلي), type, type_ar,
    subtype, subtype_ar, confidence, source
    """
    if not text or not text.strip():
        return []
    ner = get_ner()
    raw_results = ner(text)

    # تطبيق خوارزمية الدمج الذكية للعبارات المترابطة
    processed_results = smart_merge_entities(raw_results)

    ner = get_ner()
    entities = []
    n = len(text)
    detected_entity_texts = []

    for offset, chunk in split_text(text):
        if not chunk.strip():
    for entity in processed_results:
        original_type = entity["type"]
        entity_text = entity["text"].strip()

        # إزالة الكلمات القصيرة جداً أو الرموز الغريبة
        if len(entity_text) < 2:
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
        detected_entity_texts.append(entity_text)

        subtype, subtype_ar = classify_subtype(
            entity_text,
            original_type,
        )

        entities.append({
            "text": entity_text,
            "type": original_type,
            "type_ar": ENTITY_TYPE_AR.get(
                original_type, "نوع آخر"
            ),
            "subtype": subtype,
            "subtype_ar": subtype_ar,
            "confidence": round(float(entity["score"]), 4),
            "source": "model",
        })

    # Extract roots for the text while excluding detected entities to improve search results
    processed_text_with_roots = extract_roots_for_text(text, detected_entity_texts)

    return {
        "entities": entities,
        "processed_text": processed_text_with_roots
    }
