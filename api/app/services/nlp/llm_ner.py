"""Intelligent Academic Named Entity Recognition using Groq LLM API.

Specializes in identifying high-level scientific and academic concepts across all domains:
- UNIVERSITY (جامعات وكليات ومراكز بحثية)
- CONCEPT (مفاهيم علمية وفلسفية وحالات فسيولوجية)
- DISEASE (أمراض، متلازمات، واعتلالات)
- MEDICAL_TERM (أدوية، مستحضرات، مصطلحات طبية، أعضاء)
- TECHNOLOGY (تقنيات ونظم برمجية وحاسوبية)
- FIELD (حقول وتخصصات علمية)
- Standard entities (PERSON, ORGANIZATION, LOCATION, DATE)
"""

import json
import logging
import re
from typing import List, Dict, Any
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """أنت نظام ذكاء اصطناعي فائق الدقة متخصص في الأبحاث العلمية ومعالجة اللغة العربية واستخراج الكيانات المسماة كاملة دون تقطيع (Academic & Scientific Named Entity Recognition).
مهمتك استخراج جميع الكيانات والمفاهيم والمصطلحات العلمية والطبية والأكاديمية المهمة من النص العربي المعطى وتصنيفها بدقة تامة.

قواعد جوهرية وحاسمة:
1. الكيان يجب أن يكون كاملاً وغير مجتزأ أبداً (Full Entity Span):
   - استخرج الأسماء المركبة كاملة: "صلاح الدين الأيوبي" ككيان واحد، "جمال عبد الناصر"، "محمود درويش".
   - استخرج المؤسسات والجامعات كاملة: "جامعة النجاح الوطنية"، "الجامعة الأمريكية في بيروت"، "منظمة الصحة العالمية".
   - استخرج الأماكن المركبة كاملة: "رام الله"، "بيت لحم"، "شرم الشيخ"، "كفر الشيخ".
   - استخرج المصطلحات الطبية والأمراض كاملة: "مرض السكري"، "نقص السائل الأمنيوسي"، "اضطراب كلى الجنين"، "الأدوية المميعة للدم".
2. لا تكرر نفس الكيان أبداً، ولا تدخل في حلقات تكرار.
3. افصل حرف العطف (الواو) وسوابق الجر عن بداية الكيان: اكتب "القدس" وليس "والقدس"، "دمشق" وليس "بدمشق".

الفئات المدعومة (Categories):
- UNIVERSITY: جامعات، كليات، معاهد أكاديمية وبحثية.
- LOCATION: مدن، دول، معالم جغرافية.
- PERSON: أسماء أشخاص، علماء، باحثين، أطباء، قادة.
- ORGANIZATION: مؤسسات، وزارات، شركات، مستشفيات، منظمات دولية.
- DISEASE: أمراض، متلازمات، اعتلالات، مشكلات صحية (مثل: الربو، أمراض القلب، الجفاف، جدري الماء).
- MEDICAL_TERM: أدوية (ألترافين، الإيبوبروفين)، مستحضرات، أعضاء حيوية (الكلى، الكبد)، سوائل ومصطلحات طبية.
- TECHNOLOGY: تقنيات، أدوات، برمجيات، نظم ذكاء اصطناعي.
- FIELD: مجالات وتخصصات أكاديمية (الكيمياء، الطب، الصيدلة، الفيزياء).
- CONCEPT: حالات فسيولوجية (الحمل، الرضاعة)، مفاهيم علمية وإحصائية، فئات (كبار السن، الأطفال).
- DATE: تواريخ، أزمنة، مدد وفترات زمنية (الأسبوع 20، الثلث الأخير، 3 أشهر، عام 1965).

شروط الإخراج:
أعد فقط مصفوفة JSON صالحة داخل كائن "entities"، مثل:
{"entities": [{"text": "ألترافين", "category": "MEDICAL_TERM", "confidence": 0.99}, {"text": "الربو", "category": "DISEASE", "confidence": 0.98}]}
"""


class GroqLLMNER:
    """Performs deep contextual NER using Groq API with automatic model fallbacks and robust parsing."""

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL or "qwen/qwen3.8-27b"
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extracts deep academic and scientific entities from the text via Groq."""
        self.api_key = settings.GROQ_API_KEY
        if not self.api_key or self.api_key.strip() == "":
            logger.info("GROQ_API_KEY is not configured. Skipping Groq LLM layer.")
            return []

        prompt = f"استخرج جميع الكيانات والمفاهيم والمصطلحات كاملة دون أي تقطيع وبدون تكرار من هذا النص العربي:\n\"{text}\""

        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json",
        }

        # Model priority: Qwen (highest accuracy and no looping) -> allam -> gpt-oss-120b -> 20b
        candidate_models = [
            self.model,
            "qwen/qwen3.8-27b",
            "allam-2-7b",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
        ]
        candidate_models = list(dict.fromkeys(candidate_models))

        for model_candidate in candidate_models:
            # Qwen has an enforced OTPM limit of 1000 on Groq free/on-demand tier, so cap at 800
            tok_limit = 800 if "qwen" in model_candidate else 1200
            payload = {
                "model": model_candidate,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": tok_limit,
            }

            try:
                async with httpx.AsyncClient(timeout=settings.GROQ_TIMEOUT_SECONDS) as client:
                    response = await client.post(self.base_url, headers=headers, json=payload)
                    if response.status_code != 200:
                        logger.warning(
                            f"Groq API model {model_candidate} status {response.status_code}: {response.text}"
                        )
                        continue

                    data = response.json()
                    raw_content = data["choices"][0]["message"]["content"].strip()

                    raw_entities = self._robust_parse_entities(raw_content)
                    if not raw_entities:
                        continue

                    entities = []
                    seen_spans = set()

                    for item in raw_entities:
                        if not isinstance(item, dict):
                            continue
                        e_text = item.get("text", item.get("entity", item.get("name", ""))).strip()
                        if not e_text or len(e_text) < 2:
                            continue

                        # Avoid duplicates
                        if e_text in seen_spans:
                            continue

                        # Locate character offsets in original text
                        pattern = re.escape(e_text)
                        match = re.search(pattern, text)
                        if match:
                            start_char = match.start()
                            end_char = match.end()
                        else:
                            start_char = text.find(e_text)
                            if start_char == -1:
                                first_w = e_text.split()[0]
                                start_char = max(0, text.find(first_w))
                            end_char = start_char + len(e_text)

                        cat_raw = str(item.get("category", item.get("type", "CONCEPT"))).strip()
                        cat = self._standardize_category(cat_raw)

                        conf = float(item.get("confidence", 0.96))

                        entities.append({
                            "text": e_text,
                            "category": cat,
                            "confidence": round(conf, 4),
                            "source": f"Groq_{model_candidate.split('/')[-1]}",
                            "start_char": start_char,
                            "end_char": end_char,
                        })
                        seen_spans.add(e_text)

                    if entities:
                        logger.info(f"Groq LLM ({model_candidate}) successfully extracted {len(entities)} entities!")
                        return entities

            except Exception as e:
                logger.error(f"Error querying Groq model {model_candidate}: {e}")
                continue

        return []

    def _robust_parse_entities(self, raw_content: str) -> List[Dict[str, Any]]:
        """Parses entity list with multi-stage auto-repair for truncated or unclosed JSON."""
        # Stage 1: Try direct JSON parse of extracted block
        json_str = self._extract_json_substring(raw_content)
        if json_str:
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, dict):
                    return parsed.get("entities", parsed.get("data", []))
            except json.JSONDecodeError:
                pass

        # Stage 2: Auto-repair unclosed JSON array (truncated by token limit)
        # Find the last occurrence of complete object `}`
        last_obj_end = raw_content.rfind("}")
        first_array_start = raw_content.find("[")
        if first_array_start != -1 and last_obj_end > first_array_start:
            repaired_json = raw_content[first_array_start:last_obj_end + 1] + "]"
            try:
                parsed = json.loads(repaired_json)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

        # Stage 3: Regex salvage fallback - extract all valid {"text": ..., "category": ...} items
        salvaged = []
        entity_regex = re.compile(
            r'\{\s*"text"\s*:\s*"([^"]+)"\s*,\s*"category"\s*:\s*"([^"]+)"(?:\s*,\s*"confidence"\s*:\s*([0-9.]+))?\s*\}'
        )
        for match in entity_regex.finditer(raw_content):
            salvaged.append({
                "text": match.group(1).strip(),
                "category": match.group(2).strip(),
                "confidence": float(match.group(3)) if match.group(3) else 0.95
            })

        return salvaged

    def _extract_json_substring(self, content: str) -> str:
        """Finds and extracts valid JSON block from LLM output."""
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if match:
            candidate = match.group(1).strip()
            if (candidate.startswith("{") and candidate.endswith("}")) or (candidate.startswith("[") and candidate.endswith("]")):
                return candidate

        start_brace = content.find("{")
        end_brace = content.rfind("}")
        if start_brace != -1 and end_brace > start_brace:
            return content[start_brace:end_brace + 1].strip()

        start_bracket = content.find("[")
        end_bracket = content.rfind("]")
        if start_bracket != -1 and end_bracket > start_bracket:
            return content[start_bracket:end_bracket + 1].strip()

        return ""

    def _standardize_category(self, cat_raw: str) -> str:
        """Normalizes and standardizes Arabic/English raw category labels."""
        cat_upper = cat_raw.upper()

        if any(k in cat_raw for k in ["جامع", "كلي", "معهد", "أكاديم"]) or any(k in cat_upper for k in ["UNIV", "COLLEGE", "INSTITUT"]):
            return "UNIVERSITY"
        if any(k in cat_raw for k in ["شخص", "عالم", "باحث", "مؤسس", "شاعر", "ملك", "رئيس", "طبيب", "أستاذ"]) or "PER" in cat_upper:
            return "PERSON"
        if any(k in cat_raw for k in ["موقع", "مكان", "مدين", "دول", "جغراف", "بلد"]) or any(k in cat_upper for k in ["LOC", "CITY", "PLACE"]):
            return "LOCATION"
        if any(k in cat_raw for k in ["مؤسس", "منظم", "شرك", "وزار", "مستشف", "مركز", "نادي", "جمع"]) or "ORG" in cat_upper:
            return "ORGANIZATION"
        if any(k in cat_raw for k in ["مرض", "متلازم", "اعتلال", "وباء", "عرض", "مشكل"]) or any(k in cat_upper for k in ["DISEASE", "CONDITION", "SYMPTOM", "DISORDER"]):
            return "DISEASE"
        if any(k in cat_raw for k in ["طب", "صيدل", "مناع", "دواء", "علاج", "صحي", "عقار", "عضو", "جنين", "سائل"]) or any(k in cat_upper for k in ["MED", "HEALTH", "DRUG", "PHARMA", "ANATOMY"]):
            return "MEDICAL_TERM"
        if any(k in cat_raw for k in ["تقني", "برمج", "حاسوب", "ذكاء", "نظام", "أداة"]) or "TECH" in cat_upper:
            return "TECHNOLOGY"
        if any(k in cat_raw for k in ["تاريخ", "زمن", "عام", "سنة", "عصر", "شهر", "أسبوع", "يوم", "فترة", "مدة"]) or any(k in cat_upper for k in ["DATE", "TIME", "YEAR", "WEEK", "MONTH"]):
            return "DATE"
        if any(k in cat_raw for k in ["تخصص", "حقل", "مجال", "علم"]) or "FIELD" in cat_upper:
            return "FIELD"
        return "CONCEPT"


groq_llm_ner = GroqLLMNER()
