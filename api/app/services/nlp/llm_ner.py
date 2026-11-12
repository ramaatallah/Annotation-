"""Intelligent Academic Named Entity Recognition using Groq LLM API.

Specializes in identifying high-level scientific and academic concepts across all domains:
- UNIVERSITY (Universities, colleges, and research institutions)
- CONCEPT (Scientific and philosophical concepts, theoretical models)
- DISEASE (Diseases, syndromes, and clinical disorders)
- MEDICAL_TERM (Medications, pharmaceutical terms, anatomy)
- TECHNOLOGY (Technologies, software systems, and engineering frameworks)
- FIELD (Academic fields and scientific disciplines)
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
2. السياق الدلالي الدقيق وقواعد الفصل الصارم:
   - الكلمة لا تصنف بمعزل عن سياقها في الجملة أبداً:
     * السياق الجيولوجي مقابل التشريحي: تراكيب الأرض وبنى الكواكب (مثل "القشرة الأرضية"، "قشرة الكواكب"، "غرف الصهارة"، "الوشاح"، "النواة الأرضية") تصنف حصراً GEOLOGY (تضاريس / علوم الأرض) ويُمنع منعاً باتاً تصنيفها ANATOMY؛ فئة ANATOMY مخصصة حصراً للكائنات الحية وأعضاء الإنسان والحيوان.
     * التضاريس والظواهر الطبيعية مقابل الآثار: "البراكين"، "الزلازل"، "التلال"، "الجبال"، "الكهوف" تصنف GEOLOGY أو PHENOMENON، ويُمنع منعاً باتاً تصنيفها ARTIFACT؛ فئة ARTIFACT مخصصة فقط للأدوات والآلات والمصنوعات البشرية التاريخية والتراثية.
     * السياق المؤسسي مقابل الجغرافي: "واشنطن" في (أعلنت واشنطن) هي ORGANIZATION، وفي (سافرت إلى واشنطن) هي LOCATION.
     * السياق الزمني مقابل الجغرافي: "المغرب" في (صلاة المغرب) هي DATE، وفي (مملكة المغرب) هي LOCATION.
     * السياق الكيميائي مقابل أسماء الأشخاص: "النحاس" في (عنصر النحاس) هي CHEMICAL، وفي (أحمد النحاس) هي PERSON.
     * السياق المجازي: "الذهب الأسود" في سياق الطاقة هو CHEMICAL وليس معدن الذهب.
3. الكيان يجب أن يكون اسماً أو مركباً اسمياً صريحاً فقط (Noun Phrase):
   - يُمنع منعاً باتاً استخراج الأفعال أو الجمل الفعلية (مثل: "لم تحصل"، "تؤدي"، "يبدأ"، "قام"، "كان").
   - يُمنع استخراج أسماء الأعداد والمقادير المبهمة المنفردة (مثل: "بضع"، "عدة"، "بعض"، "قليل").
   - المصطلحات العلمية الطبية تكون أسماء صريحة: استخرج "نقص الكالسيوم" (نعم ككيان)، ولا تستخرج "لم تحصل" (فعل وجملة).
4. الكيان يجب أن يكون كاملاً وغير مجتزأ أبداً ومكتمل الحروف (Full Word & Entity Span):
   - يُمنع منعاً باتاً بتر الحروف الأخيرة من الكلمة (مثل اقتطاع التاء المربوطة أو الياء؛ لا تكتب 'الطّاق' بل 'الطاقة'، ولا تكتب 'غاز الطبي' بل 'الغاز الطبيعي').
   - استخرج الأسماء المركبة كاملة: "هشاشة العظام" ككيان واحد، "صلاح الدين الأيوبي"، "ثنائيات الفلقة"، "المجموعة الحادية عشرة"، "ثنائي أكسيد الكربون".
   - استخرج المؤسسات والجامعات كاملة: "جامعة النجاح الوطنية"، "منظمة الصحة العالمية".
5. قاعدة التخصيص الدلالي الصارم (Specific-First Hierarchy):
   - تجنب تماماً حشر كل شيء تحت مفهوم علمي CONCEPT؛ هذه الفئة محجوزة فقط للمفاهيم المجردة والنظريات العامة.
   - أي معلم جيولوجي، بنية كوكبية أو صخرية، صهارة، طبقة أرضية، صفائح تكتونية، براكين، تلال، جبال بركانية يصنف إلزامياً GEOLOGY (🌋 تضاريس / علوم الأرض).
   - أي مركب كيميائي، عنصر، غاز، فلز، سبيكة، أو وقود هيدروكربوني (مثل: ثنائي أكسيد الكربون، الميثان، النحاس، الكالسيوم، البترول، الفحم) يصنف إلزامياً CHEMICAL (🧪 مركب كيميائي).
   - أي عملية فيزيائية أو حركة طبيعية أو مناخية أو دورة بيئية (مثل: الاحتباس الحراري، المد والجزر، حركة الأمواج، الرياح، التمثيل الضوئي) تصنف إلزامياً PHENOMENON (🔬 ظاهرة علمية).
   - أي جرم سماوي، كوكب، نجم، شمس، قمر يصنف إلزامياً ASTRONOMY (🌌 جرم فلكي).
   - أي دولة، مدينة، إقليم، أو تجمع جيوسياسي (مثل: جزيرة قبرص، دول العالم، الشرق الأوسط) يصنف إلزامياً LOCATION (📍 موقع جغرافي).
6. افصل سوابق الجر وحروف العطف عن بداية الكيان: اكتب "أمريكا الشمالية" وليس "بأمريكا الشمالية"، "القدس" وليس "والقدس"، "الكالسيوم" وليس "بالكالسيوم"، "فرنسا" وليس "كفرنسا".
7. لا تكرر نفس الكيان أبداً.

الفئات المدعومة (Categories):
- GEOLOGY: معالم وتضاريس جيولوجية، براكين، فوهات، حِمم وصهارة، طبقات وبنى كوكبية وصخرية، تلال، جبال بركانية، صفائح تكتونية، صدوع ورواسب (مثل: البراكين، القشرة الأرضية، قشرة الكواكب، غرف الصهارة، الصهارة، الحمم البركانية، التلال المخروطية، الجبال البركانية، الوشاح، الصفيحة العربية).
- SPECIES: كائنات حية، نباتات، أشجار، حيوانات، طيور، كائنات دقيقة، فصائل أحيائية (مثل: البلوط، السنديان، الصقر، الإشريكية القولونية).
- PHENOMENON: ظواهر طبيعية، فيزيائية، فلكية، مناخية، عمليات حيوية وحركات طاقية (مثل: الاحتباس الحراري، التمثيل الضوئي، الكسوف، المد والجزر، حركة الأمواج، الرياح، الزلازل).
- WORK: كتب، مخطوطات، مؤلفات، أطروحات، معاهدات، دواوين شعرية (مثل: كتاب العبر، مقدمة ابن خلدون، ديوان المتنبي).
- EVENT: أحداث تاريخية، معارك، ثورات، مؤتمرات، أزمات ومفارق تاريخية (مثل: معركة حطين، الثورة الصناعية).
- CHEMICAL: مركبات كيميائية، عناصر، معادن، غازات، سبائك، وقود أحفوري، مواد طبيعية وصلبة وسائلة (مثل: ثنائي أكسيد الكربون، النحاس، القصدير، البرونز، الكالسيوم، البترول، الفحم، حمض الكبريتيك، الهيدروجين).
- ANATOMY: أعضاء، أنسجة، أجهزة حيوية، خلايا، تراكيب بيولوجية لدى الكائنات الحية فقط (مثل: العظام، الكلى، الكبد، الشريان الأبهر، غشاء الخلية). يُمنع منعاً باتاً استخدامها لتراكيب الأرض أو الكواكب أو الجماد.
- LAW_RULE: نظريات وقوانين علمية، قواعد فقهية، تشريعات ومبادئ (مثل: نظرية النسبية، قانون نيوتن، الضرورات تبيح المحظورات).
- PERIOD: عصور تاريخية، حقب جيولوجية، دول وحضارات (مثل: العصر النحاسي، العصر البرونزي، العصر العباسي، الحضارة البابلية).
- ASTRONOMY: أجرام سماوية، كواكب، نجوم، شمس، قمر، مجرات، سدم (مثل: الشمس، المشتري، مجرة أندروميدا).
- ARTIFACT: آلات، أدوات علمية وتراثية، أسلحة، مصنوعات ومكتشفات أثرية بشرية (مثل: الأسطرلاب، المجهر، حجر رشيد). يُمنع منعاً باتاً استخدامها للتضاريس الطبيعية والبراكين.
- UNIVERSITY: جامعات، كليات، مراكز بحثية وأكاديمية.
- LOCATION: مدن، دول، عواصم، معالم جغرافية ومحميات وحدائق وطنية، أقاليم وتجمعات دول (مثل: القدس، متنزه يلوستون الوطني، أمريكا الشمالية).
- PERSON: أسماء أشخاص، علماء، باحثين، أطباء، قادة، فلاسفة.
- ORGANIZATION: مؤسسات، وزارات، شركات، مستشفيات، منظمات وهيئات دولية (مثل: الأمم المتحدة، الاتحاد الأوروبي).
- DISEASE: أمراض، متلازمات، اعتلالات، مشكلات صحية ونفسية (مثل: هشاشة العظام، السكري).
- MEDICAL_TERM: أدوية، مستحضرات طبية، لقاحات، مصطلحات علاجية.
- TECHNOLOGY: تقنيات، أدوات برمجية، خوارزميات، نظم حاسوبية وذكاء اصطناعي.
- FIELD: مجالات وتخصصات أكاديمية (علم النبات، الفيزياء النظرية، علم طبقات الأرض).
- CONCEPT: مفاهيم ونماذج علمية مجردة، فئات وتصنيفات، حالات فسيولوجية (مثل: ثنائيات الفلقة، الطاقة المتجددة، الموارد الطبيعية، سن البلوغ).
- DATE: تواريخ، أزمنة، فصول سنة، مدد وحقب زمنية (مثل: 5000 إلى 4000 سنة قبل الميلاد).
- OTHER: أي كيان علمي أو معرفي مهم لا ينطبق عليه ما سبق بدقة.

حقل الوصف العربي الدقيق (label_ar):
لكل كيان، اكتب في "label_ar" وصفاً تخصصياً موجزاً ودقيقاً يوضح طبيعة الكيان (مثال: "طبقة صخرية باطنية"، "تضاريس بركانية"، "مركب كيميائي"، "غاز دفيء"، "وقود أحفوري"، "ظاهرة بيئية"، "تجمع دولي"، "حقبة تاريخية").

شروط الإخراج:
أعد فقط مصفوفة JSON صالحة داخل كائن "entities"، مثل:
{"entities": [{"text": "القشرة الأرضية", "category": "GEOLOGY", "label_ar": "طبقة جيولوجية صخرية", "confidence": 0.99}, {"text": "البراكين", "category": "GEOLOGY", "label_ar": "تضاريس ومعالم بركانية", "confidence": 0.99}, {"text": "متنزه يلوستون الوطني", "category": "LOCATION", "label_ar": "محمية وموقع جغرافي", "confidence": 0.98}]}
"""


class GroqLLMNER:
    """Performs deep contextual NER using Groq API with automatic model fallbacks and robust parsing."""

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL or "llama-3.3-70b-versatile"
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

        # Model priority: User specified / llama-3.3-70b -> qwen -> allam -> fallback models
        candidate_models = [
            self.model,
            "llama-3.3-70b-versatile",
            "qwen/qwen3.8-27b",
            "allam-2-7b",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
        ]
        candidate_models = list(dict.fromkeys(candidate_models))

        for model_candidate in candidate_models:
            # Qwen has an enforced OTPM limit of 1000 on Groq free/on-demand tier, so cap at 800
            tok_limit = 800 if "qwen" in model_candidate else 1400
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
            r'\{\s*"text"\s*:\s*"([^"]+)"\s*,\s*"category"\s*:\s*"([^"]+)"(?:\s*,\s*"confidence"\s*:\s*([0-9.]+))?(?:\s*,\s*"label_ar"\s*:\s*"([^"]+)")?\s*\}'
        )
        for match in entity_regex.finditer(raw_content):
            salvaged.append({
                "text": match.group(1).strip(),
                "category": match.group(2).strip(),
                "confidence": float(match.group(3)) if match.group(3) else 0.95,
                "label_ar": match.group(4) if match.group(4) else None,
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
        if any(k in cat_raw for k in ["ظاهر", "عملية حيوي", "مناخ", "احتباس", "أمواج", "رياح", "مد وجزر", "فيزياء", "طاق"]) or any(k in cat_upper for k in ["PHENOMEN", "CLIMATE", "WAVE"]):
            return "PHENOMENON"
        if any(k in cat_raw for k in ["كيميا", "مركب", "عنصر", "فلز", "سبيك", "معدن", "غاز", "وقود", "بترول", "نفط", "فحم", "أكسيد"]) or any(k in cat_upper for k in ["CHEM", "ALLOY", "METAL", "ELEMENT", "GAS", "FUEL", "MINERAL"]):
            return "CHEMICAL"
        if any(k in cat_raw for k in ["عصر", "حقبة", "حضار", "قرن", "إمبراطور"]) or any(k in cat_upper for k in ["PERIOD", "ERA", "EPOCH", "CIVILIZATION"]):
            return "PERIOD"
        if any(k in cat_raw for k in ["كتاب", "مؤلف", "مخطوط", "وثيق", "ديوان", "أطروح", "معاهد"]) or any(k in cat_upper for k in ["WORK", "BOOK", "MANUSCRIPT"]):
            return "WORK"
        if any(k in cat_raw for k in ["حدث", "معرك", "ثور", "مؤتمر", "حرب"]) or any(k in cat_upper for k in ["EVENT", "BATTLE", "WAR"]):
            return "EVENT"
        if any(k in cat_raw for k in ["عضو", "نسيج", "خلايا", "خلية", "شريان", "قلب", "كبد", "كلية", "عظام"]) or "ANATOM" in cat_upper:
            return "ANATOMY"
        if any(k in cat_raw for k in ["قانون", "نظري", "قاعد", "فقه", "دستور"]) or any(k in cat_upper for k in ["LAW", "RULE", "THEORY"]):
            return "LAW_RULE"
        if any(k in cat_raw for k in ["فلك", "كوكب", "نجم", "مجر", "سديم", "شمس", "قمر"]) or any(k in cat_upper for k in ["ASTRON", "PLANET", "STAR", "GALAXY"]):
            return "ASTRONOMY"
        if any(k in cat_raw for k in ["أداة", "آلة", "أثر", "أسطرلاب"]) or any(k in cat_upper for k in ["ARTIFACT", "TOOL"]):
            return "ARTIFACT"
        if any(k in cat_raw for k in ["جامع", "كلي", "معهد", "أكاديم"]) or any(k in cat_upper for k in ["UNIV", "COLLEGE", "INSTITUT"]):
            return "UNIVERSITY"
        if any(k in cat_raw for k in ["شخص", "عالم", "باحث", "مؤسس", "شاعر", "ملك", "رئيس", "طبيب", "أستاذ"]) or "PER" in cat_upper:
            return "PERSON"
        if any(k in cat_raw for k in ["موقع", "مكان", "مدين", "دول", "جغراف", "بلد", "جزير", "إقليم", "عالم"]) or any(k in cat_upper for k in ["LOC", "CITY", "PLACE", "ISLAND", "GEO", "COUNTRY", "WORLD"]):
            return "LOCATION"
        if any(k in cat_raw for k in ["مؤسس", "منظم", "شرك", "وزار", "مستشف", "مركز", "نادي", "جمع", "اتحاد", "أمم"]) or "ORG" in cat_upper:
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
