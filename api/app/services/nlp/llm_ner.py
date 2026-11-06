"""Intelligent Academic Named Entity Recognition using Groq LLM API.

Specializes in identifying high-level scientific and academic concepts:
- UNIVERSITY (جامعات وكليات)
- CONCEPT (مفاهيم علمية وأكاديمية)
- DISEASE (أمراض ومتلازمات)
- MEDICAL_TERM (مصطلحات طبية ومناعية)
- TECHNOLOGY (تقنيات ونظم برمجية)
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

SYSTEM_PROMPT = """أنت نظام ذكاء اصطناعي أكاديمي فائق الدقة متخصص في معالجة اللغة العربية واستخراج الكيانات المسماة والمفاهيم العلمية (Academic Named Entity Recognition).
مهمتك استخراج جميع الكيانات والمفاهيم المهمة من النص العربي المعطى وتصنيفها بدقة تامة.

الفئات المدعومة (Categories):
- UNIVERSITY: جامعات، كليات، معاهد أكاديمية.
- LOCATION: مدن، دول، معالم جغرافية.
- PERSON: أسماء أشخاص، علماء، باحثين، مؤسسين.
- ORGANIZATION: مؤسسات، وزارات، شركات، مستشفيات، مراكز بحثية.
- DISEASE: أمراض، متلازمات، اعتلالات.
- MEDICAL_TERM: مصطلحات طبية، مناعية، أدوية، أعضاء.
- TECHNOLOGY: تقنيات، أدوات، برمجيات، نظم ذكاء اصطناعي.
- FIELD: مجالات وتخصصات أكاديمية (الكيمياء، الفيزياء، الطب، التربية).
- CONCEPT: درجات علمية (دبلوم، بكالوريوس)، نظريات، ومفاهيم علمية.
- DATE: تواريخ، أزمنة، عصور، سنوات.

شروط الإخراج:
أعد فقط مصفوفة JSON صالحة داخل كائن "entities"، مثل:
{"entities": [{"text": "جامعة النجاح الوطنية", "category": "UNIVERSITY", "confidence": 0.99}, {"text": "مدينة نابلس", "category": "LOCATION", "confidence": 0.98}]}
"""


class GroqLLMNER:
    """Performs deep contextual NER using Groq API with automatic model fallbacks."""

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL or "qwen/qwen3.8-27b"
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extracts deep academic entities from the text via Groq."""
        # Refresh API key from settings or env
        self.api_key = settings.GROQ_API_KEY
        if not self.api_key or self.api_key.strip() == "":
            logger.info("GROQ_API_KEY is not configured. Skipping Groq LLM layer.")
            return []

        prompt = f"استخرج جميع الكيانات والمفاهيم الأكاديمية بدقة من هذا النص:\n\"{text}\""

        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json",
        }

        # Try user model first, then fallback to available models in account
        candidate_models = [
            self.model,
            "qwen/qwen3.8-27b",
            "allam-2-7b",
            "openai/gpt-oss-20b",
        ]
        # Remove duplicates preserving order
        candidate_models = list(dict.fromkeys(candidate_models))

        for model_candidate in candidate_models:
            payload = {
                "model": model_candidate,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 1024,
            }

            try:
                async with httpx.AsyncClient(timeout=settings.GROQ_TIMEOUT_SECONDS) as client:
                    response = await client.post(self.base_url, headers=headers, json=payload)
                    if response.status_code != 200:
                        logger.warning(
                            f"Groq API model {model_candidate} status {response.status_code}: {response.text}"
                        )
                        continue  # Try next candidate model

                    data = response.json()
                    raw_content = data["choices"][0]["message"]["content"].strip()

                    # Extract JSON object even if enclosed in markdown ```json ... ```
                    json_str = self._extract_json_substring(raw_content)
                    if not json_str:
                        continue

                    parsed = json.loads(json_str)

                    # Normalize entities list
                    if isinstance(parsed, list):
                        raw_entities = parsed
                    elif isinstance(parsed, dict):
                        raw_entities = parsed.get("entities", parsed.get("data", []))
                    else:
                        raw_entities = []

                    entities = []
                    for item in raw_entities:
                        if not isinstance(item, dict):
                            continue
                        e_text = item.get("text", item.get("entity", item.get("name", ""))).strip()
                        if not e_text or len(e_text) < 2:
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

                        cat = item.get("category", item.get("type", "CONCEPT")).upper()
                        # Standardize categories
                        if "UNIV" in cat or "COLLEGE" in cat or "INSTITUT" in cat:
                            cat = "UNIVERSITY"
                        elif "LOC" in cat or "CITY" in cat or "PLACE" in cat:
                            cat = "LOCATION"
                        elif "PER" in cat:
                            cat = "PERSON"
                        elif "ORG" in cat:
                            cat = "ORGANIZATION"
                        elif "MED" in cat or "HEALTH" in cat:
                            cat = "MEDICAL_TERM"
                        elif "DATE" in cat or "TIME" in cat or "YEAR" in cat:
                            cat = "DATE"

                        conf = float(item.get("confidence", 0.96))

                        entities.append({
                            "text": e_text,
                            "category": cat,
                            "confidence": round(conf, 4),
                            "source": f"Groq_{model_candidate.split('/')[-1]}",
                            "start_char": start_char,
                            "end_char": end_char,
                        })

                    if entities:
                        logger.info(f"Groq LLM ({model_candidate}) successfully extracted {len(entities)} entities!")
                        return entities

            except Exception as e:
                logger.error(f"Error querying Groq model {model_candidate}: {e}")
                continue

        return []

    def _extract_json_substring(self, content: str) -> str:
        """Finds and extracts valid JSON block from LLM output."""
        # 1. Check for markdown code blocks ```json ... ```
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if match:
            candidate = match.group(1).strip()
            if (candidate.startswith("{") and candidate.endswith("}")) or (candidate.startswith("[") and candidate.endswith("]")):
                return candidate

        # 2. Check for outermost braces { ... }
        start_brace = content.find("{")
        end_brace = content.rfind("}")
        if start_brace != -1 and end_brace > start_brace:
            return content[start_brace:end_brace + 1].strip()

        # 3. Check for outermost brackets [ ... ]
        start_bracket = content.find("[")
        end_bracket = content.rfind("]")
        if start_bracket != -1 and end_bracket > start_bracket:
            return content[start_bracket:end_bracket + 1].strip()

        return ""


groq_llm_ner = GroqLLMNER()
