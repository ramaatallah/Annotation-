# -*- coding: utf-8 -*-
"""
LLM Academic Entity Classifier.
Extracts and classifies fine-grained academic entities using LLMs (Groq, Allam, Gemini, etc.).
Strict Principle: AI classifies entities ONLY. It is NEVER asked for roots and NEVER returns roots.
"""

import asyncio
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

from app.config import settings
from app.nlp.taxonomy import TAXONOMY, FEW_SHOT_EXAMPLES


def _build_system_prompt() -> str:
    """Constructs academic NER system prompt with definitions, negative constraints, and few-shot examples."""
    types_desc = []
    for k, v in TAXONOMY.items():
        if k == "OTHER":
            continue
        types_desc.append(f"- {k} ({v['type_ar']}): {v['description']}. أمثلة: {', '.join(v['examples'][:2])}")

    taxonomy_block = "\n".join(types_desc)

    few_shots_block = json.dumps(
        {"examples": FEW_SHOT_EXAMPLES},
        ensure_ascii=False,
        indent=2,
    )

    return f"""You are an expert Arabic Academic Named Entity Recognition (NER) and Concept Extractor.
Your sole mission is to classify academic entities in texts across multiple disciplines (medicine, history, literature, law, technology, agriculture, religious studies, education, social sciences).

STRICT ARCHITECTURAL RULE:
You classify entities ONLY. Do NOT extract or invent morphological roots. Never return a 'root' field.

TAXONOMY OF ACADEMIC ENTITIES:
{taxonomy_block}

NEGATIVE RULES (CRITICAL):
1. NEVER extract verbs (e.g. ولد، أسس، اكتشف، قام، أجرى). Verbs are NOT entities.
2. NEVER extract functional words, pronouns, prepositions, or vague generic phrases.
3. The 'text' field MUST be an exact verbatim substring from the input text.
4. For DATE entities, extract the exact temporal phrase.

FEW-SHOT EXAMPLES:
{few_shots_block}

RESPONSE FORMAT:
Return strictly valid JSON with this exact schema (no markdown formatting, no preamble):
{{
  "entities": [
    {{
      "text": "exact entity text from passage",
      "type": "ONE_OF_THE_TAXONOMY_TYPES",
      "type_ar": "التصنيف بالعربية",
      "subtype_ar": "التصنيف الفرعي التوضيحي",
      "domain": "medicine | history | law | literature | technology | agriculture | religious_studies | social_sciences | education | geography | general",
      "confidence": 0.95
    }}
  ]
}}"""


def _call_urllib_sync(url: str, headers: dict, payload: dict, timeout: float) -> Optional[dict]:
    """Fallback synchronous request using standard library urllib."""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as he:
        print(f"[LLM urllib HTTPError] {he.code}: {he.read().decode('utf-8', errors='ignore')}")
    except Exception as exc:
        print(f"[LLM urllib Exception] {exc}")
    return None


async def extract_llm_entities(text: str) -> List[Dict[str, Any]]:
    """
    Calls LLM models in fallback order with total timeout.
    Returns list of extracted entities (without roots).
    """
    if not settings.llm_enabled or not settings.llm_api_key or not text.strip():
        return []

    system_prompt = _build_system_prompt()
    user_prompt = f"حلل هذا النص واستخرج الكيانات الأكاديمية وصنفها بدقة حسب التعليمات:\n{text}"

    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    models = settings.llm_models
    timeout = settings.llm_total_timeout_s

    for model in models:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        try:
            data = None
            if _HTTPX_AVAILABLE:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                    else:
                        print(f"[LLM Error] {model} -> Status {resp.status_code}: {resp.text}")
            else:
                data = await asyncio.to_thread(_call_urllib_sync, url, headers, payload, timeout)

            if data and "choices" in data:
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                raw_entities = parsed.get("entities", [])
                if raw_entities:
                    for ent in raw_entities:
                        ent["source"] = "llm"
                        ent["llm_self_confidence"] = ent.get("confidence", 0.9)
                    return raw_entities
        except Exception as exc:
            print(f"[LLM Exception] {model} failed: {exc}")
            continue

    return []
