# -*- coding: utf-8 -*-
"""
Arabic Academic NER & Concept Extraction Engine


# ──────────────────────────────────────────────────────────────
# Environment variable loader (api/.env or root .env)
# ──────────────────────────────────────────────────────────────
def _load_env_file(filepath):
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


_current_dir = os.path.dirname(os.path.abspath(__file__))
_load_env_file(os.path.join(_current_dir, ".env"))
_load_env_file(os.path.join(os.path.dirname(_current_dir), ".env"))


# ──────────────────────────────────────────────────────────────
# Text cleaning & strict root validation
# Academic constraint: Arabic roots must be EXACTLY 3 letters
# ──────────────────────────────────────────────────────────────

# Regex: exactly 3 Arabic letters (Unicode range U+0621–U+064A)
_TRILATERAL_RE = re.compile(r"^[\u0621-\u064A]{3}$")

# Functional/stop words that carry no entity semantic value
STOP_WORDS = {
    "في", "من", "إلى", "الى", "على", "عن", "مع", "بين", "حول", "لدى", "عند",
    "هذا", "هذه", "هذان", "هاتان", "هؤلاء", "ذلك", "تلك", "أولئك",
    "الذي", "التي", "الذين", "اللواتي", "اللاتي",
    "هو", "هي", "هم", "هن", "نحن", "أنا", "أنت", "أنتم",
    "ما", "من", "لا", "ماذا", "لماذا", "كيف", "متى", "أين",
    "كل", "بعض", "غير", "سوى", "فقط", "أيضا", "أيضاً", "جداً", "جدا",
    "تم", "تمت", "كان", "كانت", "يكون", "تكون", "ليس", "ليست",
    # Relational connectors in personal and academic names
    "بن", "ابن", "بنت", "ابنة", "آل", "أبو", "أبي", "أبا", "أم", "ذو", "ذا", "ذي",
}

# Thread lock for non-thread-safe stemmers
_tasha_lock = threading.Lock()


def clean_arabic_word(word: str) -> str:
    """Remove diacritics (tashkeel), tatweel, and extraneous characters."""
    if not word:
        return ""
    w = str(word).strip().replace("\u0640", "").replace("#", "")
    w = re.sub(r"[\u064B-\u065F\u0670]", "", w)
    return w


def _valid(root: str):
    """
    Validate that a root is strictly trilateral: exactly 3 Arabic consonants.
    Academic morphological rule: No original Alif (ا) exists in Arabic roots!
    """
    if not root:
        return None
    r = clean_arabic_word(root)
    r = re.sub(r"\s+", "", r)
    if not _TRILATERAL_RE.fullmatch(r):
        return None
    if "ا" in r:
        return None
    return r


# Rigid words that have NO morphological root (أفعال جامدة، حروف، أسماء مبنية)
RIGID_WORDS = {
    "عسى", "ليس", "نعم", "بئس", "حبذا", "خلا", "عدا", "حاشا", "كاد", "طفق", "هيهات", "شتان",
    "هذا", "هذه", "هذان", "هاتان", "هؤلاء", "ذلك", "تلك", "أولئك",
    "الذي", "التي", "الذين", "اللواتي", "اللاتي",
    "أنا", "أنت", "هو", "هي", "نحن", "أنتم", "أنتن", "هما", "هم", "هن",
    "في", "من", "إلى", "الى", "على", "عن", "مع", "بين", "حتى", "ثم", "أو", "أم", "بل", "لكن",
}

# Common hollow verb pairs where middle radical inverts to Yaa (ياء)
YAA_HOLLOW_PAIRS = {
    "بع", "سر", "طر", "زد", "ضع", "طب", "مل", "نل", "عش", "صد", "خط", "كل", "عب", "هب", "غب", "دن", "حن", "شب"
}

SENTENCE_END = ".!؟?\n"


def normalize_root_radicals(r: str):
    """
    Classical Morphological Radicals Normalizer:
    Resolves inverted weak letters according to classical Arabic morphology:
      1. Trailing Hamza (ء) -> Waw (و)
      2. Trailing Alif Maqsoora (ى) -> Yaa (ي)
      3. Trailing Alif (ا) in 3-letter verbs -> Waw (و) (e.g. دعا -> دعو)
      4. Middle Alif (ا) in hollow verbs -> Waw or Yaa (e.g. قال -> قول, باع -> بيع)
    """
    if not r or len(r) != 3:
        return None

    res = list(r)
    if res[2] == "\u0621":
        res[2] = "و"
    if res[2] == "ى":
        res[2] = "ي"
    if res[2] == "ا":
        res[2] = "و"
    if res[1] == "ا":
        pair = res[0] + res[2]
        res[1] = "ي" if pair in YAA_HOLLOW_PAIRS else "و"

    final_r = "".join(res)
    return _valid(final_r)


def _strip_affixes(word: str) -> str:
    """
    Generalized Arabic Affix & Clitic Stripper.
    Strips proclitic prefixes and enclitic suffixes without any word-specific hardcoding.
    """
    w = clean_arabic_word(word)
    if not w or len(w) < 2:
        return w
    if w in RIGID_WORDS:
        return None

    # 1. Proclitic Prefixes
    if any(w.startswith(p) for p in ("وبال", "وفال", "وكال")) and len(w) > 6:
        w = w[4:]
    elif any(w.startswith(p) for p in ("وال", "فال", "بال", "كال")) and len(w) > 5:
        w = w[3:]
    elif w.startswith("لل") and len(w) > 4:
        w = w[2:]
    elif w.startswith("ال") and len(w) > 4:
        w = w[2:]

    # 2. Present tense verbs with prefix + plural suffix (e.g. يتكاتبون -> تكاتب)
    if len(w) >= 7 and (w.endswith("ون") or w.endswith("ين")):
        if w.startswith("يت") or w.startswith("تت") or w.startswith("نت"):
            w = w[1:-2]
        elif w.startswith("يست") or w.startswith("تست"):
            w = w[1:-2]
            if not w.startswith("ا"):
                w = "ا" + w

    # 3. Verbal Noun exceptions (NOT plural suffixes):
    if w.startswith("ت") and w.endswith("ية") and len(w) == 5:
        return w
    if w.startswith("ت") and len(w) == 5 and w[3] == "ي":
        return w
    if w.startswith("م") and len(w) == 5 and w[3] == "و":
        return w

    # 4. Feminine Plural + Attached Pronoun (ات + ضمير)
    fem_plural_pronouns = ("اتهما", "اتهم", "اتهن", "اتها", "اتنا", "اتكم", "اتكن")
    for fpp in fem_plural_pronouns:
        if w.endswith(fpp) and len(w) > len(fpp) + 2:
            return w[:-len(fpp)]

    # 5. Feminine Singular + Attached Pronoun (ت + ضمير)
    fem_pronouns = ("تهما", "تهم", "تهن", "تها", "تنا", "تكم", "تكن", "ته")
    for fp in fem_pronouns:
        if w.endswith(fp) and len(w) > len(fp) + 2:
            return w[:-len(fp)]

    # 6. Regular Attached Pronouns (هـ, ها, هم, هن, هما, نا, كم)
    masc_pronouns = ("هما", "هم", "هن", "ها", "نا", "كم", "كن", "ه")
    for mp in masc_pronouns:
        if w.endswith(mp) and len(w) > len(mp) + 2:
            w = w[:-len(mp)]
            break

    # 7. Inflectional Suffixes
    if w.endswith("ية") and len(w) > 4:
        w = w[:-2]
    elif w.endswith("ات") and len(w) > 4:
        w = w[:-2]
    elif w.endswith("ي") and len(w) > 3:
        w = w[:-1]
    elif w.endswith("ة") and len(w) > 3:
        w = w[:-1]

    # 8. Sound Masculine Plural (ون, ين)
    if (w.endswith("ون") or w.endswith("ين")) and len(w) >= 6:
        if w[0] == "م" or w[1] == "ا":
            w = w[:-2]

    return w


def _extract_root_by_pattern(w: str):
    """
    Extract trilateral roots using classical Arabic morphological weights and rules.
    """
    if not w:
        return None
    n = len(w)

    # 2-letter Geminates (مدّ -> مدد, رد -> ردد)
    if n == 2:
        return normalize_root_radicals(w[0] + w[1] + w[1])

    # 3-letter nouns with deleted initial Waw (صفة -> وصف, سمة -> وسم, صلة -> وصل, هبة -> وهب)
    if n == 3 and w[2] == "ة":
        return normalize_root_radicals("و" + w[0] + w[1])

    # Present tense geminate verb (يمد -> مدد, يمر -> مرر, يعد -> عدد)
    if n == 3 and w[0] in "يتنأ" and w[1] != "ا":
        return normalize_root_radicals(w[1] + w[2] + w[2])

    # Geminate Istif'al (استقل -> قلل, استقر -> قرر, استمر -> مرر)
    if w.startswith("است") and n == 5:
        return normalize_root_radicals(w[3] + w[4] + w[4])

    # تَفَاعَل (تكاتب -> كتب, تفاعل -> فعل)
    if n == 5 and w[0] == "ت" and w[2] == "ا":
        return normalize_root_radicals(w[1] + w[3] + w[4])

    # تَفْعِلَة (تنمية -> نمو)
    if w.startswith("ت") and w.endswith("ية") and len(w) == 5:
        return normalize_root_radicals(w[1] + w[2] + "و")

    # تَفْعِيل (تكوين -> كون, تمكين -> مكن, تنظيم -> نظم)
    if n == 5 and w[0] == "ت" and w[3] == "ي":
        return normalize_root_radicals(w[1] + w[2] + w[4])

    # مَفْعُول (مكتوب -> كتب, مخزون -> خزن, مسجون -> سجن)
    if n == 5 and w[0] == "م" and w[3] == "و":
        return normalize_root_radicals(w[1] + w[2] + w[4])

    # Ifti'al with assimilated initial waw (اتصال -> وصل)
    if w.startswith("ات") and n == 5 and w[3] == "ا":
        return normalize_root_radicals("و" + w[2] + w[4])
    # Ifti'al after zaa (ازدهار -> زهر)
    if w.startswith("ازد") and n == 6 and w[4] == "ا":
        return normalize_root_radicals(w[1] + w[3] + w[5])
    # Ifti'al after emphatics (اصطناع -> صنع)
    if (w.startswith("اصط") or w.startswith("اضط")) and n == 6 and w[4] == "ا":
        return normalize_root_radicals(w[1] + w[3] + w[5])

    # Hollow verb masdars (استقامة -> قوم, إدارة -> دور)
    if w.startswith("است") and n == 6 and w[4] == "ا":
        return normalize_root_radicals(w[3] + "و" + w[5])
    if w[0] in "إاأ" and n == 4 and w[2] == "ا":
        return normalize_root_radicals(w[1] + "و" + w[3])

    # استفعال / مستفعل (المستشفى -> شفي, استخدام -> خدم)
    if w.startswith("است") and n >= 6:
        if n == 7 and w[5] == "ا":
            return normalize_root_radicals(w[3] + w[4] + w[6])
        if n == 6:
            return normalize_root_radicals(w[3] + w[4] + w[5])
    if w.startswith("مست") and n == 6:
        last_ch = "ي" if w[5] == "ى" else w[5]
        return normalize_root_radicals(w[3] + w[4] + last_ch)

    # إفعال
    if w[0] in "إاأ" and n == 5 and w[3] == "ا":
        return normalize_root_radicals(w[1] + w[2] + w[4])

    # افتعال
    if w[0] in "اإ" and n == 6 and w[2] == "ت" and w[4] == "ا":
        return normalize_root_radicals(w[1] + w[3] + w[5])

    # انفعال
    if w.startswith("ان") and n == 6 and w[4] == "ا":
        return normalize_root_radicals(w[2] + w[3] + w[5])

    # متفاعل
    if n == 6 and w[:2] == "مت" and w[3] == "ا":
        return normalize_root_radicals(w[2] + w[4] + w[5])

    # مفاعيل
    if n == 6 and w[0] == "م" and w[2] == "ا" and w[4] == "ي":
        return normalize_root_radicals(w[1] + w[3] + w[5])

    # مفاعل
    if n == 5 and w[0] == "م" and w[2] == "ا":
        return normalize_root_radicals(w[1] + w[3] + w[4])

    # تفعل
    if n == 4 and w[0] == "ت":
        return normalize_root_radicals(w[1] + w[2] + w[3])

    # متفعل
    if n == 5 and w[:2] == "مت":
        return normalize_root_radicals(w[2] + w[3] + w[4])

    # فعول
    if n == 4 and w[2] == "و":
        return normalize_root_radicals(w[0] + w[1] + w[3])

    # فعال
    if n == 4 and w[2] == "ا":
        return normalize_root_radicals(w[0] + w[1] + w[3])

    # فاعل
    if n == 4 and w[1] == "ا":
        return normalize_root_radicals(w[0] + w[2] + w[3])

    # فعيل
    if n == 4 and w[2] == "ي":
        return normalize_root_radicals(w[0] + w[1] + w[3])

    # فعلال
    if n == 5 and w[2] == "ا" and w[3] == "ا":
        return normalize_root_radicals(w[0] + w[1] + w[4])

    # مفعل (مكتب -> كتب, مصنع -> صنع)
    if n == 4 and w[0] == "م":
        return normalize_root_radicals(w[1] + w[2] + w[3])

    # ثلاثي مجرد (رد الألف المنقلبة إلى واو أو ياء)
    if n == 3:
        return normalize_root_radicals(w)

    return None


def _pattern_root_extractor(word: str):
    """
    Generalized Arabic trilateral root extractor using morphological patterns.

    Strategy:
      1. Clean and strip the definite article.
      2. Strip derivational suffixes (nisba, feminine, sound plural).
         ون/ين are only stripped when the base starts with a morphological
         prefix initial — this naturally rejects most loanwords without
         needing any hardcoded word list.
      3. Match against Arabic morphological patterns (catalogue above).
      4. Normalize trailing ء → و (defective/hollow verb roots).
      5. Validate: exactly 3 Arabic consonants.

    Loanwords (فيتامين، بروتين، باريس…) naturally return None because:
      - They don't start with Arabic morphological prefix initials, so
        ين/ون is not stripped (preventing accidental pattern matches).
      - Their consonant structure doesn't fit any Arabic wazn.
    """
    w = clean_arabic_word(word)
    if not w or len(w) < 3:
        return None

    # Reject words containing non-Arabic characters (Latin script, digits)
    if re.search(r"[A-Za-z0-9]", w):
        return None

    # Step 1 & 2: Strip proclitic prefixes, definite article, attached pronouns, and inflectional suffixes
    w = _strip_affixes(w)
    if not w or len(w) < 3:
        return None

    # Step 3: Match patterns and extract root consonants
    candidate = _extract_root_by_pattern(w)
    if not candidate:
        return None

    # Step 4: Normalize trailing hamza (ء → و) for hollow/defective roots
    candidate = _normalize_final_hamza(candidate)

    # Step 5: Strict validation (must be 3 Arabic consonants)
    return _valid(candidate)


def _normalize_final_hamza(root: str):
    """Normalizes trailing weak letter if needed, preserving genuine hamza."""
    if not root:
        return None
    if root.endswith("ى"):
        return root[:-1] + "ي"
    return root


# ──────────────────────────────────────────────────────────────
# Root Lookup — unified entry point with lexicon-first priority
# ──────────────────────────────────────────────────────────────
_LEXICON_ENGINES = []
try:
    from app.nlp.roots.camel_engine import CamelRootEngine
    _camel = CamelRootEngine()
    if _camel.is_available():
        _LEXICON_ENGINES.append(("camel", lambda w: (_camel.extract_root(w) or None) and _camel.extract_root(w).root))
except Exception:
    _LEXICON_ENGINES = []

ROOT_ENGINES = (
    [name for name, _ in _LEXICON_ENGINES] + ["pattern_rules"]
)


@lru_cache(maxsize=50_000)
def get_root(word: str):
    """
    Retrieve the trilateral root for a single Arabic word using CAMeL Tools.
    """
    try:
        from app.nlp.roots.camel_engine import CamelRootEngine
        _camel = CamelRootEngine()
        res = _camel.extract_root(word)
        if res and res.status in ("found", "quadrilateral") and res.root:
            return res.root, res.engine or "camel"
    except Exception:
        pass
    return None, None


# ──────────────────────────────────────────────────────────────
# Entity-level root extraction
# ──────────────────────────────────────────────────────────────

def extract_entity_roots(entity_text: str) -> list:
    """
    Extract trilateral roots for each meaningful word in a (possibly
    multi-word) entity, skipping functional/stop words and loanwords.

    Returns a list of dicts: [{"word": <original>, "root": <3-letter root>}]

    Examples:
      "الإنتاج الزراعي"  → [{"word": "الإنتاج", "root": "نتج"},
                              {"word": "الزراعي", "root": "زرع"}]
      "فيتامين C"        → []   (loanword + Latin letter → both skipped)
      "جامعة النجاح"     → [{"word": "جامعة", "root": "جمع"},
                              {"word": "النجاح", "root": "نجح"}]
    """
    if not entity_text:
        return []

    cleaned_input = clean_arabic_word(entity_text)
    # Extract Arabic tokens only
    words = re.findall(r"[\u0621-\u064A]+", cleaned_input)
    word_roots = []
    seen = set()

    for w in words:
        clean = clean_arabic_word(w)
        if len(clean) < 2 or clean in seen:
            continue
        seen.add(clean)

        # Skip functional words
        if clean in STOP_WORDS:
            continue
        clean_no_al = clean[2:] if clean.startswith("ال") and len(clean) > 4 else clean
        if clean_no_al in STOP_WORDS:
            continue

        r, _ = get_root(clean)
        if r:
            word_roots.append({"word": w, "root": r})

    return word_roots


def populate_entity_roots(entities: list) -> list:
    """
    Populates deterministic word-level roots and root_status for entities
    using CAMeL Tools.
    """
    try:
        from app.nlp.roots.camel_engine import CamelRootEngine
        camel_eng = CamelRootEngine()
        for e in entities:
            text = e.get("text", "")
            ent_type = (e.get("type") or "").upper()

            if ent_type == "DATE" or not text:
                e["root"] = None
                e["root_status"] = "not_applicable"
                e["words"] = []
                e["word_roots"] = []
                continue

            words = text.split()
            word_roots = camel_eng.extract_roots_batch(words)
            words_dicts = [wr.to_dict() for wr in word_roots if wr is not None]
            e["words"] = words_dicts
            e["word_roots"] = [
                {"word": w["word"], "root": w["root"]}
                for w in words_dicts if w["root"]
            ]

            # Primary root is the first valid root found in entity tokens
            primary_root = None
            primary_status = "unknown"
            for wr in word_roots:
                if wr and wr.status in ("found", "quadrilateral") and wr.root:
                    primary_root = wr.root
                    primary_status = wr.status
                    break
            if not primary_root and words_dicts:
                primary_status = words_dicts[0]["status"]

            e["root"] = primary_root
            e["root_status"] = primary_status
    except Exception as exc:
        print(f"[Roots Error] {exc}")
    return entities

    return entities
# ──────────────────────────────────────────────────────────────
# LLM Classifier  (entity classification only — NOT roots)
# ──────────────────────────────────────────────────────────────

def _call_llm_classifier(text: str):
    """
    Call the configured LLM (Groq / any OpenAI-compatible endpoint) for
    entity detection and classification. The model is instructed to:
      - Identify and classify entities across all academic disciplines.
      - Output roots as a HINT only (the local engine overrides them).
      - Return null for loanwords/foreign terms (critical signal).

    Supported entity types:
      PERSON, LOCATION, ORGANIZATION, UNIVERSITY, TECHNOLOGY,
      EVENT, PRODUCT, ANATOMY, CONCEPT, DISEASE, DATE
    """
    api_key = os.environ.get("ANNOTATION_AI_API_KEY", "").strip()
    base_url = os.environ.get(
        "ANNOTATION_AI_BASE_URL",
        "https://api.groq.com/openai/v1"
    ).strip()
    configured_model = os.environ.get(
        "ANNOTATION_AI_MODEL", "llama-3.3-70b-versatile"
    ).strip()

    if not api_key:
        return None

    system_prompt = (
        "You are an expert Arabic academic NER system serving all disciplines "
        "(medicine, history, literature, law, technology, agriculture, etc.).\n"
        "Your ONLY job is entity detection and classification.\n\n"
        "CLASSIFICATION RULES:\n"
        "1. Extract multi-word expressions as a single unit "
        "(e.g., 'جامعة النجاح الوطنية', 'فيتامين C', 'الذكاء الاصطناعي').\n"
        "2. Entity types:\n"
        "   PERSON       — people, scholars, historical figures\n"
        "   LOCATION     — countries, cities, geographical features\n"
        "   ORGANIZATION — companies, ministries, institutions (non-university)\n"
        "   UNIVERSITY   — universities, colleges, higher-education bodies\n"
        "   TECHNOLOGY   — technical systems, software, AI, devices\n"
        "   EVENT        — verbs or actions (ولد، أسس، اكتشف، يحمي…)\n"
        "   PRODUCT      — drugs, compounds, biological molecules\n"
        "   ANATOMY      — organs, tissues, body systems\n"
        "   CONCEPT      — scientific phenomena, abstract ideas\n"
        "   DISEASE      — diseases, symptoms, medical conditions\n"
        "   DATE         — dates, time periods, years\n\n"
        "Respond with ONLY a valid JSON object (no markdown, no preamble):\n"
        "{\n"
        '  "entities": [\n'
        "    {\n"
        '      "text": "entity text as it appears",\n'
        '      "type": "PERSON|LOCATION|ORGANIZATION|UNIVERSITY|TECHNOLOGY|EVENT|PRODUCT|ANATOMY|CONCEPT|DISEASE|DATE",\n'
        '      "type_ar": "التصنيف بالعربية",\n'
        '      "subtype_ar": "تصنيف فرعي توضيحي",\n'
        '      "occurrences": 1,\n'
        '      "confidence": 0.95\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    # Build model fallback list
    models_to_try = [configured_model]
    if "groq.com" in base_url:
        for m in ("allam-2-7b", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"):
            if m not in models_to_try:
                models_to_try.append(m)
    else:
        for m in ("gemini-3.5-flash-lite", "gemini-3.5-flash"):
            if m not in models_to_try:
                models_to_try.append(m)

    chat_url = f"{base_url.rstrip('/')}/chat/completions"

    for model_name in models_to_try:
        try:
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            "Respond with valid JSON only. "
                            "Analyze and extract entities from this Arabic text:\n"
                            + text[:1500]
                        ),
                    },
                ],
                "temperature": 0.1,
                "max_tokens": 1200,
                "response_format": {"type": "json_object"},
            }
            req = urllib.request.Request(
                chat_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36"
                    ),
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                content = body["choices"][0]["message"]["content"].strip()

                # Strip markdown fences if present
                if "```json" in content:
                    content = content.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in content:
                    content = content.split("```", 1)[1].split("```", 1)[0].strip()

                # Extract the outermost JSON object
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1:
                    content = content[start : end + 1]

                parsed = json.loads(content)
                entities = parsed.get("entities", [])
                if entities:
                    for e in entities:
                        e["source"] = f"llm_{model_name}"
                    print(
                        f"[AI] Classification successful via {model_name}: "
                        f"{len(entities)} entities found."
                    )
                    return entities

        except urllib.error.HTTPError as http_err:
            err_body = ""
            try:
                err_body = http_err.read().decode("utf-8")[:200]
            except Exception:
                pass
            print(f"[AI] {model_name} HTTP {http_err.code}: {err_body}")
            continue
        except Exception as ex:
            print(f"[AI] {model_name} error: {ex}")
            continue

    print("[AI] All LLM models failed or rate-limited. Falling back to local NLP pipeline.")
    return None


# ──────────────────────────────────────────────────────────────
# Local offline fallback (no internet / no API key)
# ──────────────────────────────────────────────────────────────

# Human-readable Arabic labels for entity types
ENTITY_TYPE_AR = {
    "PERSON":       "شخص",
    "ORGANIZATION": "مؤسسة",
    "LOCATION":     "موقع جغرافي",
    "UNIVERSITY":   "جامعة / مؤسسة تعليمية",
    "TECHNOLOGY":   "تقنية / نظام",
    "DISEASE":      "مرض / حالة طبية",
    "DATE":         "تاريخ / فترة زمنية",
    "EVENT":        "حدث / فعل",
    "PRODUCT":      "مركب / دواء / منتج",
    "ANATOMY":      "عضو / نسيج / جهاز",
    "CONCEPT":      "مفهوم علمي",
    "UNKNOWN":      "نوع آخر",
}

_ner_pipeline = None
_ner_load_failed = False


def get_ner():
    """Load the local HuggingFace Arabic NER model (offline zero-shot model)."""
    global _ner_pipeline, _ner_load_failed
    if _ner_pipeline is not None:
        return _ner_pipeline
    if _ner_load_failed:
        return None
    try:
        import torch
        from transformers import (
            AutoModelForTokenClassification,
            AutoTokenizer,
            pipeline,
        )

        model_name = "hatmimoha/arabic-ner"
        tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
        model = AutoModelForTokenClassification.from_pretrained(
            model_name, local_files_only=True, torch_dtype=torch.float32
        )
        model.to("cpu")
        model.eval()

        _ner_pipeline = pipeline(
            "ner",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy="simple",
            device=-1,
        )
        return _ner_pipeline
    except Exception as e:
        _ner_load_failed = True
        print(f"Local NER model not available: {e}")
        return None


def _extract_bert_entities(text: str) -> list:
    """
    Run local fine-tuned BERT model (hatmimoha/arabic-ner) to detect
    grounded core named entities (PERSON, LOCATION, ORGANIZATION) with exact token spans.
    """
    raw_results = []
    try:
        ner_model = get_ner()
        if ner_model:
            raw_results = ner_model(text)
    except Exception as e:
        print(f"[Local BERT NER] Warning: {e}")

    entities = []
    seen = set()

    for item in raw_results:
        raw = str(item.get("word", "")).strip()
        if raw.startswith("##"):
            continue
        word = raw.replace("##", "").strip()
        if len(word) < 2 or word in seen or not re.search(r"[\u0621-\u064A\w]", word):
            continue
        seen.add(word)
        orig_type = item["entity_group"]
        entities.append({
            "text": word,
            "type": orig_type,
            "type_ar": ENTITY_TYPE_AR.get(orig_type, "نوع آخر"),
            "subtype_ar": None,
            "occurrences": 1,
            "confidence": round(float(item["score"]), 4),
            "source": "bert_local",
        })

    return entities


def _merge_hybrid_entities(bert_ents: list, llm_ents: list) -> list:
    """
    Hybrid Ensemble Fusion Algorithm:
    Combines Local BERT (exact token boundaries) with LLM (rich academic taxonomy).

    Complementary Integration:
      1. Cross-Validation: When both BERT and LLM detect the same entity,
         boost confidence to 0.99 and mark source as 'hybrid_ensemble' (BERT + AI).
      2. Semantic Specialization: If BERT tagged 'ORGANIZATION' and LLM specialized
         it to 'UNIVERSITY', adopt the specialized academic type 'UNIVERSITY'.
      3. Academic Gap-Filling: LLM provides classes that BERT cannot detect
         (TECHNOLOGY, CONCEPT, DISEASE, PRODUCT, DATE, ANATOMY).
      4. Deduplication: Merges overlapping multi-word phrases cleanly.
    """
    merged = []
    llm_map = {}

    for le in llm_ents:
        norm = clean_arabic_word(le.get("text", "")).lower()
        if norm:
            llm_map[norm] = le

    seen_norms = set()

    # 1. Process local BERT entities (grounded base)
    for be in bert_ents:
        b_text = be.get("text", "")
        b_norm = clean_arabic_word(b_text).lower()
        if not b_norm or b_norm in seen_norms:
            continue
        seen_norms.add(b_norm)

        # Check for exact or substring match in LLM entities
        matched_llm = llm_map.get(b_norm)
        if not matched_llm:
            for l_norm, le in llm_map.items():
                if b_norm in l_norm or l_norm in b_norm:
                    matched_llm = le
                    seen_norms.add(l_norm)
                    break

        if matched_llm:
            # Cross-validated by both BERT and LLM!
            l_type = (matched_llm.get("type") or "").upper()
            b_type = (be.get("type") or "").upper()

            # Specialize generic ORGANIZATION to UNIVERSITY if LLM recognized it
            final_type = l_type if l_type == "UNIVERSITY" and b_type == "ORGANIZATION" else (l_type or b_type)
            final_text = matched_llm.get("text") if len(matched_llm.get("text", "")) >= len(b_text) else b_text

            merged.append({
                "text": final_text,
                "type": final_type,
                "type_ar": matched_llm.get("type_ar") or be.get("type_ar"),
                "subtype_ar": matched_llm.get("subtype_ar"),
                "occurrences": 1,
                "confidence": 0.99,  # High confidence: verified by two independent models
                "source": "hybrid_ensemble",
            })
        else:
            merged.append(be)

    # 2. Add domain-specific entities from LLM (TECHNOLOGY, CONCEPT, DISEASE, PRODUCT, DATE)
    for l_norm, le in llm_map.items():
        if l_norm not in seen_norms:
            seen_norms.add(l_norm)
            merged.append({
                **le,
                "source": le.get("source") or "ai_academic_llm",
            })

    return merged


# ──────────────────────────────────────────────────────────────
# Analysis cache + main entry point (Hybrid Ensemble)
# ──────────────────────────────────────────────────────────────

_ANALYSIS_CACHE: dict = {}


def analyze_text(text: str) -> list:
    """
    Main entry point for Arabic academic text analysis.

    Hybrid Pipeline:
      1. Cache lookup → instant return for repeated inputs.
      2. Local BERT NER (hatmimoha/arabic-ner) → extracts grounded core entities (PER, LOC, ORG).
      3. Academic LLM Classifier → extracts rich academic & specialized entities (UNIVERSITY, TECH, CONCEPT, DISEASE, DATE).
      4. Hybrid Fusion → merges and cross-validates results from both models.
      5. Local Morphological Engine → deterministically computes trilateral roots for all entities.
    """
    cleaned = text.strip()
    if not cleaned:
        return []

    cache_key = cleaned[:300]
    if cache_key in _ANALYSIS_CACHE:
        return _ANALYSIS_CACHE[cache_key]

    # Step 1: Run local BERT model
    bert_entities = []
    try:
        bert_entities = _extract_bert_entities(cleaned)
    except Exception as e:
        print(f"[BERT NER] Info: {e}")

    # Step 2: Run Academic LLM classifier
    llm_entities = []
    try:
        llm_entities = _call_llm_classifier(cleaned) or []
    except Exception as e:
        print(f"[LLM NER] Info: {e}")

    # Step 3: Hybrid Fusion (both models complement each other)
    if bert_entities and llm_entities:
        print(f"[NER] Hybrid Ensemble active: {len(bert_entities)} BERT + {len(llm_entities)} LLM entities merged.")
        merged_entities = _merge_hybrid_entities(bert_entities, llm_entities)
    elif llm_entities:
        merged_entities = llm_entities
    elif bert_entities:
        merged_entities = bert_entities
    else:
        merged_entities = []

    # Step 4: Extract trilateral roots deterministically using the local morphological engine
    result = populate_entity_roots(merged_entities)
    _ANALYSIS_CACHE[cache_key] = result
    return result
