from functools import lru_cache
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

    return pipeline(
        "ner",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple",
        device=-1,
    )


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
    ner = get_ner()
    results = ner(text)

    entities = []
    detected_entity_texts = []

    for entity in results:
        original_type = entity["entity_group"]
        entity_text = entity["word"].strip()

        if not entity_text:
            continue

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
