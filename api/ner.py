from functools import lru_cache
import re
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

MODEL_NAME = "hatmimoha/arabic-ner"

ENTITY_TYPE_AR = {
    "PERSON": "شخص",
    "ORGANIZATION": "مؤسسة",
    "LOCATION": "موقع جغرافي",
    "DISEASE": "مرض",
    "DATE": "تاريخ",
    "TIME": "وقت",
    "EVENT": "حدث",
    "PRODUCT": "منتج",
    "TECHNOLOGY": "تقنية",
    "UNKNOWN": "غير معروف",
}


@lru_cache(maxsize=1)
def get_ner():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float32,
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


def analyze_text(text):
    ner = get_ner()
    raw_results = ner(text)

    # تطبيق خوارزمية الدمج الذكية للعبارات المترابطة
    processed_results = smart_merge_entities(raw_results)

    entities = []

    for entity in processed_results:
        original_type = entity["type"]
        entity_text = entity["text"].strip()

        # إزالة الكلمات القصيرة جداً أو الرموز الغريبة
        if len(entity_text) < 2:
            continue

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

    return entities
