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
                        # Strip proclitic conjunction 'و' if attached by BERT (e.g. 'والقدس' -> 'القدس', 'وصلاح' -> 'صلاح')
                        clean_start = max(0, start_char)
                        clean_end = min(len(text), end_char)
                        if (
                            entity_text.startswith("و")
                            and len(entity_text) > 3
                            and entity_text not in {"واشنطن", "وادي", "ورقلة", "ويلز", "ولايات"}
                            and not text[clean_start:clean_start + 1].isalnum() == False
                        ):
                            entity_text = entity_text[1:]
                            clean_start = clean_start + 1

                        entities.append({
                            "text": entity_text,
                            "category": category,
                            "confidence": round(float(item.get("score", 0.95)), 4),
                            "source": "BERT",
                            "start_char": clean_start,
                            "end_char": clean_end,
                        })

                # Repair BERT sub-token splits where tokens are contiguous without space (e.g. "والقد" + "س" -> "والقدس")
                repaired = []
                for e in entities:
                    if repaired and repaired[-1]["end_char"] == e["start_char"] and repaired[-1]["category"] == e["category"]:
                        repaired[-1]["end_char"] = e["end_char"]
                        repaired[-1]["text"] = text[repaired[-1]["start_char"]:e["end_char"]]
                    else:
                        repaired.append(e)
                entities = repaired
            except Exception as e:
                logger.warning(f"Transformer inference warning: {e}")

        # 2. Comprehensive Academic Semantic Extractor (Always active to ensure deep coverage)
        heuristic_entities = self._deep_academic_extract(text)
        entities.extend(heuristic_entities)

        logger.info(f"Local BERT (hatmimoha/arabic-ner) extracted {len(entities)} candidate entities.")
        return entities

    def _deep_academic_extract(self, text: str) -> List[Dict[str, Any]]:
        """Extracts universities, academic degrees, fields, historical dates, persons, and locations."""
        entities = []

        # 1. Universities, Colleges, and Educational Institutions
        # Matches: جامعة النجاح الوطنية, مدرسة النجاح الوطنية, كلية النجاح, جامعة بيرزيت, etc.
        edu_pattern = rf"\b{ACADEMIC_PREFIXES}\s+[\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+){{0,2}}"
        for match in re.finditer(edu_pattern, text):
            matched_str = match.group().strip()
            # Stop before verbs, prepositions, or connectives
            matched_str = re.split(r"\s+(?:عن|في|من|على|إلى|مع|لـ|بـ|تقديم|تعلن|تنظم|تواصل|تضم|تحتفل|تقع|تعد|تأسست|بدأت|لعبت|عام)\b", matched_str)[0].strip()
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

        # 2. Locations (Cities, Towns, Regions) with strict word boundaries
        for city in KNOWN_CITIES_REGIONS:
            city_pattern = rf"\b(?:مدينة\s+)?{re.escape(city)}\b"
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

        # 3. Dates, Years, Weeks, and Eras (e.g. عام 1965, سنة 1948, الأسبوع 20, 3 أشهر, الثلث الأخير)
        date_pattern = (
            r"(?:عام|سنة|تاريخ|شهر|الأسبوع|أسبوع|يوم)\s+\d+(?:\s*م)?"
            r"|(?:\d{1,2}\s+(?:يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)(?:\s+\d{4})?)"
            r"|(?:\d+\s+(?:أشهر|شهور|سنوات|أعوام|أسابيع|أيام|ساعات|دقائق))"
            r"|(?:الثلث\s+(?:الأول|الثاني|الأخير))"
            r"|(?:الربع\s+(?:الأول|الثاني|الثالث|الأخير))"
        )
        for match in re.finditer(date_pattern, text):
            entities.append({
                "text": match.group().strip(),
                "category": "DATE",
                "confidence": 0.98,
                "source": "AcademicEngine",
                "start_char": match.start(),
                "end_char": match.end(),
            })

        # 4. Universal Scientific & Clinical Conditions (e.g. أمراض القلب, مرض السكري, اضطراب كلى الجنين)
        ARABIC_WORD = r"[\u0621-\u064A\u0671-\u06D3]+"
        clinical_pattern = rf"\b(?:أمراض|مرض|متلازمة|اضطراب|نقص)\s+{ARABIC_WORD}(?:\s+{ARABIC_WORD}){{0,2}}"
        for match in re.finditer(clinical_pattern, text):
            matched_str = match.group().strip()
            # Stop before connectives, verbs, or punctuation
            matched_str = re.split(r"[\s،,.:؟!؛]+(?:عن|في|من|على|إلى|مع|لـ|بـ|لدى|دون|أو|و|ونقص|قد|تسبب|يسبب|تعد|تظهر)\b", matched_str)[0].strip()
            matched_str = matched_str.strip(" ،,.:؟!؛")
            if len(matched_str.split()) >= 2:
                entities.append({
                    "text": matched_str,
                    "category": "DISEASE",
                    "confidence": 0.95,
                    "source": "AcademicEngine",
                    "start_char": match.start(),
                    "end_char": match.start() + len(matched_str),
                })

        # 5. Universal Research & Scientific Methodology Concepts
        research_terms = [
            "المجموعة الضابطة", "العينة الضابطة", "الفرضية الصفرية", "التحليل الإحصائي",
            "التجارب السريرية", "المنهج الوصفي", "معامل الارتباط", "الانحدار الخطي",
            "الدراسة الاستقصائية", "المراجعة المنهجية", "التحليل البعدي", "عينة البحث",
        ]
        for term in research_terms:
            pattern = rf"\b{re.escape(term)}\b"
            for match in re.finditer(pattern, text):
                entities.append({
                    "text": match.group().strip(),
                    "category": "CONCEPT",
                    "confidence": 0.96,
                    "source": "AcademicEngine",
                    "start_char": match.start(),
                    "end_char": match.end(),
                })

        # 6. Academic Degrees and Programs (e.g. درجات البكالوريوس، الماجستير، الدبلوم، التعليم العالي)
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

        # 7. Academic Fields and Disciplines (e.g. الكيمياء، الفيزياء، أصول الدين، الطب، علم المناعة)
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

        return entities


local_bert_ner = LocalBertNER()
