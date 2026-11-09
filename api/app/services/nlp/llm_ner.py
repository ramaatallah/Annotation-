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

SYSTEM_PROMPT = """أنت نظام ذكاء اصطناعي أكاديمي فائق التخصص في الأبحاث واللغة العربية واستخراج الكيانات والمفاهيم العلمية بدقة تامة وبفهم سياقي عميق (Context-Aware Academic Named Entity Recognition).
مهمتك استخراج الكيانات والمصطلحات والظواهر والمفاهيم العلمية الحقيقية من النص وتصنيفها بأدق فئة معتمدة على سياق الجملة، مع إعطائها وصفاً عربياً دقيقاً في حقل "label_ar".

قواعد جوهرية حاسمة:
1. الفهم السياقي الصارم (Contextual Disambiguation):
   - الكلمة لا تصنف بمعزل عن سياقها في الجملة أبداً! الكلمة الواحدة تتغير فئتها جذرياً حسب وظيفتها ودلالتها في النص:
     * السياق المؤسسي مقابل الجغرافي: "واشنطن" في (أعلنت واشنطن) هي ORGANIZATION، وفي (سافرت إلى واشنطن) هي LOCATION.
     * السياق الزمني مقابل الجغرافي: "المغرب" في (صلاة المغرب) هي DATE، وفي (مملكة المغرب) هي LOCATION.
     * السياق الكيميائي مقابل أسماء الأشخاص: "النحاس" في (عنصر النحاس) هي CHEMICAL، وفي (أحمد النحاس) هي PERSON.
     * السياق المجازي: "الذهب الأسود" في سياق الطاقة هو CHEMICAL وليس معدن الذهب.
2. الكيان يجب أن يكون اسماً أو مركباً اسمياً صريحاً فقط (Noun Phrase):
   - يُمنع منعاً باتاً استخراج الأفعال أو الجمل الفعلية (مثل: "لم تحصل"، "تؤدي"، "يبدأ"، "قام"، "كان").
   - يُمنع استخراج أسماء الأعداد والمقادير المبهمة المنفردة (مثل: "بضع"، "عدة"، "بعض"، "قليل").
   - المصطلحات العلمية الطبية تكون أسماء صريحة: استخرج "نقص الكالسيوم" (نعم ككيان)، ولا تستخرج "لم تحصل" (فعل وجملة).
3. الكيان يجب أن يكون كاملاً وغير مجتزأ أبداً (Full Entity Span):
   - استخرج الأسماء المركبة كاملة: "هشاشة العظام" ككيان واحد، "صلاح الدين الأيوبي"، "ثنائيات الفلقة"، "المجموعة الحادية عشرة".
   - استخرج المؤسسات والجامعات كاملة: "جامعة النجاح الوطنية"، "منظمة الصحة العالمية".
4. لا تكرر نفس الكيان أبداً.
5. افصل حرف العطف (الواو) وسوابق الجر عن بداية الكيان: اكتب "القدس" وليس "والقدس"، "الكالسيوم" وليس "بالكالسيوم".

الفئات المدعومة (Categories):
- SPECIES: كائنات حية، نباتات، أشجار، حيوانات، طيور، كائنات دقيقة، فصائل أحيائية (مثل: البلوط، السنديان، الصقر، الإشريكية القولونية).
- PHENOMENON: ظواهر طبيعية، فيزيائية، فلكية، عمليات حيوية وظواهر نادرة (مثل: مارسيسنتية، التمثيل الضوئي، الكسوف، الاحتباس الحراري).
- WORK: كتب، مخطوطات، مؤلفات، أطروحات، معاهدات، دواوين شعرية (مثل: كتاب العبر، مقدمة ابن خلدون، ديوان المتنبي).
- EVENT: أحداث تاريخية، معارك، ثورات، مؤتمرات، أزمات ومفارق تاريخية (مثل: معركة حطين، الثورة الصناعية).
- CHEMICAL: مركبات كيميائية، عناصر، معادن، مواد صلبة أو سائلة (مثل: حمض الكبريتيك، كلوريد الصوديوم، الهيدروجين).
- ANATOMY: أعضاء، أنسجة، أجهزة حيوية، خلايا، تراكيب بيولوجية (مثل: الكلى، الكبد، الشريان الأبهر، غشاء الخلية).
- LAW_RULE: نظريات وقوانين علمية، قواعد فقهية، تشريعات ومبادئ (مثل: نظرية النسبية، قانون نيوتن، الضرورات تبيح المحظورات).
- PERIOD: عصور تاريخية، حقب جيولوجية، دول وحضارات (مثل: العصر العباسي، العصر الطباشيري، الحضارة البابلية).
- ASTRONOMY: أجرام سماوية، كواكب، نجوم، مجرات، سدم (مثل: المشتري، مجرة أندروميدا، سديم الجبار).
- ARTIFACT: آلات، أدوات علمية وتراثية، أسلحة، آثار تاريخية (مثل: الأسطرلاب، المجهر، حجر رشيد).
- UNIVERSITY: جامعات، كليات، مراكز بحثية وأكاديمية.
- LOCATION: مدن، دول، عواصم، معالم جغرافية وتضاريس.
- PERSON: أسماء أشخاص، علماء، باحثين، أطباء، قادة، فلاسفة.
- ORGANIZATION: مؤسسات، وزارات، شركات، مستشفيات، منظمات دولية.
- DISEASE: أمراض، متلازمات، اعتلالات، مشكلات صحية ونفسية.
- MEDICAL_TERM: أدوية، مستحضرات طبية، لقاحات، مصطلحات علاجية.
- TECHNOLOGY: تقنيات، أدوات برمجية، خوارزميات، نظم حاسوبية وذكاء اصطناعي.
- FIELD: مجالات وتخصصات أكاديمية (علم النبات، الفيزياء النظرية، الفلسفة الإسلامية).
- CONCEPT: مفاهيم ونماذج علمية، حالات فسيولوجية، فئات وتصنيفات (مثل: ثنائيات الفلقة، الحمل، كبار السن).
- DATE: تواريخ، أزمنة، فصول سنة، مدد وحقب زمنية.
- OTHER: أي كيان علمي أو معرفي مهم لا ينطبق عليه ما سبق بدقة.

حقل الوصف العربي الدقيق (label_ar):
لكل كيان، اكتب في "label_ar" وصفاً تخصصياً موجزاً ودقيقاً يوضح طبيعة الكيان (مثال: "شجرة حرجية"، "ظاهرة نباتية"، "تصنيف بيولوجي"، "عصر جيولوجي"، "مؤلَّف تراثي"، "مركب كيميائي").

شروط الإخراج:
أعد فقط مصفوفة JSON صالحة داخل كائن "entities"، مثل:
{"entities": [{"text": "البلوط", "category": "SPECIES", "label_ar": "شجرة حرجية", "confidence": 0.99}, {"text": "مارسيسنتية", "category": "PHENOMENON", "label_ar": "ظاهرة نباتية", "confidence": 0.98}, {"text": "ثنائيات الفلقة", "category": "CONCEPT", "label_ar": "تصنيف بيولوجي", "confidence": 0.97}]}
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
                            "label_ar": item.get("label_ar"),
                            "confidence": round(conf, 4),
                            "source": "Groq",
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
        cat_upper = cat_raw.upper().strip()

        # Direct enum matches
        VALID_CATEGORIES = {
            "SPECIES", "PHENOMENON", "CHEMICAL", "PERIOD", "WORK", "EVENT",
            "ANATOMY", "LAW_RULE", "ASTRONOMY", "ARTIFACT", "UNIVERSITY",
            "LOCATION", "PERSON", "ORGANIZATION", "DISEASE", "MEDICAL_TERM",
            "TECHNOLOGY", "FIELD", "CONCEPT", "DATE", "OTHER"
        }
        if cat_upper in VALID_CATEGORIES:
            return cat_upper

        # Semantic mappings
        if any(k in cat_raw for k in ["نبات", "كائن", "شجر", "حيوان", "فصيل", "طائر", "بكتير"]) or any(k in cat_upper for k in ["SPEC", "PLANT", "ANIMAL", "BOTAN"]):
            return "SPECIES"
        if any(k in cat_raw for k in ["ظاهر", "عملية حيوي"]) or "PHENOMEN" in cat_upper:
            return "PHENOMENON"
        if any(k in cat_raw for k in ["كيميا", "مركب", "عنصر", "فلز", "سبيك", "معدن"]) or any(k in cat_upper for k in ["CHEM", "ALLOY", "METAL", "ELEMENT"]):
            return "CHEMICAL"
        if any(k in cat_raw for k in ["عصر", "حقبة", "حضار", "قرن", "إمبراطور"]) or any(k in cat_upper for k in ["PERIOD", "ERA", "EPOCH", "CIVILIZATION"]):
            return "PERIOD"
        if any(k in cat_raw for k in ["كتاب", "مؤلف", "مخطوط", "وثيق", "ديوان", "أطروح", "معاهد"]) or any(k in cat_upper for k in ["WORK", "BOOK", "MANUSCRIPT"]):
            return "WORK"
        if any(k in cat_raw for k in ["حدث", "معرك", "ثور", "مؤتمر", "حرب"]) or any(k in cat_upper for k in ["EVENT", "BATTLE", "WAR"]):
            return "EVENT"
        if any(k in cat_raw for k in ["عضو", "نسيج", "خلايا", "خلية", "شريان", "قلب", "كبد", "كلية"]) or "ANATOM" in cat_upper:
            return "ANATOMY"
        if any(k in cat_raw for k in ["قانون", "نظري", "قاعد", "فقه", "دستور"]) or any(k in cat_upper for k in ["LAW", "RULE", "THEORY"]):
            return "LAW_RULE"
        if any(k in cat_raw for k in ["فلك", "كوكب", "نجم", "مجر", "سديم"]) or any(k in cat_upper for k in ["ASTRON", "PLANET", "STAR", "GALAXY"]):
            return "ASTRONOMY"
        if any(k in cat_raw for k in ["أداة", "آلة", "أثر", "أسطرلاب"]) or any(k in cat_upper for k in ["ARTIFACT", "TOOL"]):
            return "ARTIFACT"
        if any(k in cat_raw for k in ["جامع", "كلي", "معهد", "أكاديم"]) or any(k in cat_upper for k in ["UNIV", "COLLEGE", "INSTITUT"]):
            return "UNIVERSITY"
        if any(k in cat_raw for k in ["شخص", "عالم", "باحث", "مؤسس", "شاعر", "ملك", "رئيس", "طبيب", "أستاذ"]) or "PER" in cat_upper:
            return "PERSON"
        if any(k in cat_raw for k in ["موقع", "مكان", "مدين", "دول", "جغراف", "بلد", "جزير"]) or any(k in cat_upper for k in ["LOC", "CITY", "PLACE", "ISLAND"]):
            return "LOCATION"
        if any(k in cat_raw for k in ["مؤسس", "منظم", "شرك", "وزار", "مستشف", "مركز", "نادي", "جمع"]) or "ORG" in cat_upper:
            return "ORGANIZATION"
        if any(k in cat_raw for k in ["مرض", "متلازم", "اعتلال", "وباء", "عرض", "مشكل"]) or any(k in cat_upper for k in ["DISEASE", "CONDITION", "SYMPTOM", "DISORDER"]):
            return "DISEASE"
        if any(k in cat_raw for k in ["طب", "صيدل", "مناع", "دواء", "علاج", "صحي", "عقار"]) or any(k in cat_upper for k in ["MED", "HEALTH", "DRUG", "PHARMA"]):
            return "MEDICAL_TERM"
        if any(k in cat_raw for k in ["تقني", "برمج", "حاسوب", "ذكاء", "نظام", "خوارزم"]) or "TECH" in cat_upper:
            return "TECHNOLOGY"
        if any(k in cat_raw for k in ["تاريخ", "زمن", "عام", "سنة", "شهر", "أسبوع", "يوم", "فترة", "مدة"]) or any(k in cat_upper for k in ["DATE", "TIME", "YEAR", "WEEK", "MONTH"]):
            return "DATE"
        if any(k in cat_raw for k in ["تخصص", "حقل", "مجال", "علم"]) or "FIELD" in cat_upper:
            return "FIELD"
        return "CONCEPT"


groq_llm_ner = GroqLLMNER()
