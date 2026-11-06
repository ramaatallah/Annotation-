"""Local Arabic Named Entity and Academic Concept Recognition Engine.

Combines HuggingFace Transformers (when available) with a comprehensive,
high-precision Academic Semantic Pattern Analyzer designed specifically
for Arabic scientific, educational, medical, and encyclopedic texts.
"""

import re
import logging
from typing import List, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

# Standard Arabic Academic and Entity Lexicons
ACADEMIC_PREFIXES = r"(?:جامعة|كلية|معهد|أكاديمية|مدرسة|مركز|مستشفى|مجمع)"
DEGREE_TERMS = [
    "بكالوريوس", "ماجستير", "دكتوراه", "دبلوم", "دبلوم عالي", "الدرجة الجامعية",
    "الدرجة المتوسطة", "التعليم العالي", "إعداد المعلمين", "شهادة",
]

KNOWN_CITIES_REGIONS = [
    "نابلس", "طولكرم", "القدس", "رام الله", "غزة", "الخليل", "جنين", "بيت لحم",
    "أريحا", "قلقيلية", "سلفيت", "طوباس", "يافا", "حيفا", "عكا", "صفد", "الناصرة",
    "فلسطين", "الأردن", "عمان", "مصر", "القاهرة", "سوريا", "دمشق", "لبنان", "بيروت",
    "العراق", "بغداد", "السعودية", "الرياض",
]

ACADEMIC_FIELDS = [
    "الكيمياء", "الفيزياء", "الرياضيات", "أصول الدين", "الشريعة", "الطب",
    "الهندسة", "علوم الحاسوب", "اللغويات", "التربية", "علم النفس", "علم الاجتماع",
    "القانون", "العلوم الإدارية", "الاقتصاد", "علم المناعة", "الأحياء", "الصيدلة",
    "التمريض", "تكنولوجيا المعلومات", "الذكاء الاصطناعي",
]


class LocalBertNER:
    """Enterprise Arabic Entity Recognition engine with deep academic heuristics."""

    def __init__(self, model_name: str = settings.LOCAL_NER_MODEL):
        self.model_name = model_name
        self.pipeline = None
        self._is_loaded = False
        self._load_attempted = False

    def _load_model(self):
        """Loads Hugging Face pipeline gracefully if dependencies exist."""
        if self._load_attempted:
            return
        self._load_attempted = True

        if not settings.ENABLE_LOCAL_NER:
            return

        try:
            from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
            logger.info(f"Loading local Arabic NER model: {self.model_name}...")
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            model = AutoModelForTokenClassification.from_pretrained(self.model_name)
            self.pipeline = pipeline(
                "token-classification",
                model=model,
                tokenizer=tokenizer,
                aggregation_strategy="simple",
            )
            self._is_loaded = True
            logger.info("Local Arabic NER model loaded successfully.")
        except Exception as e:
            logger.info(f"Transformer model offline/fallback active: {e}")
            self._is_loaded = False

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extracts all academic, conceptual, and named entities from Arabic text."""
        entities = []

        # 1. Try Transformer model if loaded
        self._load_model()
        if self._is_loaded and self.pipeline:
            try:
                raw_results = self.pipeline(text)
                for item in raw_results:
                    label = item.get("entity_group", item.get("entity", "MISC"))
                    label = label.replace("B-", "").replace("I-", "").upper()
                    category_map = {"PER": "PERSON", "LOC": "LOCATION", "ORG": "ORGANIZATION", "DATE": "DATE"}
                    category = category_map.get(label, label)
                    entity_text = item.get("word", "").strip()
                    start_char = item.get("start", text.find(entity_text))
                    end_char = item.get("end", start_char + len(entity_text))

                    if entity_text and len(entity_text) > 1:
                        entities.append({
                            "text": entity_text,
                            "category": category,
                            "confidence": round(float(item.get("score", 0.95)), 4),
                            "source": "BERT",
                            "start_char": max(0, start_char),
                            "end_char": min(len(text), end_char),
                        })
            except Exception as e:
                logger.warning(f"Transformer inference warning: {e}")

        # 2. Comprehensive Academic Semantic Extractor (Always active to ensure deep coverage)
        heuristic_entities = self._deep_academic_extract(text)
        entities.extend(heuristic_entities)

        return entities

    def _deep_academic_extract(self, text: str) -> List[Dict[str, Any]]:
        """Extracts universities, academic degrees, fields, historical dates, persons, and locations."""
        entities = []

        # 1. Universities, Colleges, and Educational Institutions
        # Matches: جامعة النجاح الوطنية, مدرسة النجاح الوطنية, كلية النجاح, جامعة بيرزيت, etc.
        edu_pattern = rf"\b{ACADEMIC_PREFIXES}\s+[\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+){{0,4}}"
        for match in re.finditer(edu_pattern, text):
            matched_str = match.group().strip()
            # Stop before verbs or prepositions
            matched_str = re.split(r"\s+(?:تقع|تعد|تأسست|بدأت|لعبت|في|من|على|إلى|عام)\b", matched_str)[0].strip()
            if len(matched_str.split()) >= 2:
                cat = "UNIVERSITY" if any(k in matched_str for k in ["جامعة", "كلية", "معهد", "أكاديمية"]) else "ORGANIZATION"
                entities.append({
                    "text": matched_str,
                    "category": cat,
                    "confidence": 0.96,
                    "source": "AcademicEngine",
                    "start_char": match.start(),
                    "end_char": match.start() + len(matched_str),
                })

        # 2. Locations (Cities, Towns, Regions)
        for city in KNOWN_CITIES_REGIONS:
            city_pattern = rf"(?:مدينة\s+)?{re.escape(city)}"
            for match in re.finditer(city_pattern, text):
                clean_text = match.group().strip()
                entities.append({
                    "text": clean_text,
                    "category": "LOCATION",
                    "confidence": 0.95,
                    "source": "AcademicEngine",
                    "start_char": match.start(),
                    "end_char": match.end(),
                })

        # 3. Dates, Years, and Eras (e.g. عام 1918, عام 1965, عام 1977, سنة 1948)
        date_pattern = r"(?:عام|سنة|تاريخ|شهر)\s+\d{3,4}(?:\s*م)?|(?:\d{1,2}\s+(?:يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)(?:\s+\d{4})?)"
        for match in re.finditer(date_pattern, text):
            entities.append({
                "text": match.group().strip(),
                "category": "DATE",
                "confidence": 0.98,
                "source": "AcademicEngine",
                "start_char": match.start(),
                "end_char": match.end(),
            })

        # 4. Academic Degrees and Programs (e.g. درجات البكالوريوس، الماجستير، الدبلوم، التعليم العالي)
        for deg in DEGREE_TERMS:
            pattern = rf"(?:درجة\s+|درجات\s+)?{re.escape(deg)}"
            for match in re.finditer(pattern, text):
                entities.append({
                    "text": match.group().strip(),
                    "category": "CONCEPT",
                    "confidence": 0.93,
                    "source": "AcademicEngine",
                    "start_char": match.start(),
                    "end_char": match.end(),
                })

        # 5. Academic Fields and Disciplines (e.g. الكيمياء، الفيزياء، أصول الدين، الطب، علم المناعة)
        for field in ACADEMIC_FIELDS:
            pattern = rf"\b{re.escape(field)}\b"
            for match in re.finditer(pattern, text):
                cat = "MEDICAL_TERM" if any(m in field for m in ["الطب", "المناعة", "الصيدلة", "التمريض"]) else "FIELD"
                entities.append({
                    "text": match.group().strip(),
                    "category": cat,
                    "confidence": 0.94,
                    "source": "AcademicEngine",
                    "start_char": match.start(),
                    "end_char": match.end(),
                })

        # 6. Prominent Figures & Political/Academic Roles (e.g. السياسي الفلسطيني حسن شاكر حماد)
        person_patterns = [
            r"(?:السياسي(?:\s+الفلسطيني)?|الدكتور|الأستاذ|الشيخ|المؤسس)\s+([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+){1,3})",
            r"(?:على\s+يد\s+)([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+){1,3})",
        ]
        for p_pat in person_patterns:
            for match in re.finditer(p_pat, text):
                person_name = match.group(1).strip()
                # Stop if it hit punctuation or dates
                person_name = re.split(r"[\s،,\.\-\(\)\[\]]", person_name)[0] if len(person_name.split()) > 4 else person_name
                if len(person_name.split()) >= 2 and not any(city in person_name for city in KNOWN_CITIES_REGIONS):
                    entities.append({
                        "text": person_name,
                        "category": "PERSON",
                        "confidence": 0.91,
                        "source": "AcademicEngine",
                        "start_char": match.start(1),
                        "end_char": match.start(1) + len(person_name),
                    })

        return entities


local_bert_ner = LocalBertNER()
