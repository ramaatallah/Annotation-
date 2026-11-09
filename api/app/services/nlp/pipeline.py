"""Integrated Hybrid Arabic NLP Pipeline.

Orchestrates concurrent execution of:
1. Local BERT NER (hatmimoha/arabic-ner).
2. Groq LLM NER (llama-3.3-70b-versatile).
3. Fusion & Conflict Resolution Engine.
4. Trilateral Morphological Root Extraction (CAMeL Tools + Rules).
"""

import time
import asyncio
import logging
from typing import Dict, Any
from app.services.nlp.local_ner import local_bert_ner
from app.services.nlp.llm_ner import groq_llm_ner
from app.services.nlp.fusion import fusion_engine
from app.services.nlp.root_engine import root_engine

logger = logging.getLogger(__name__)


class ArabicNLPPipeline:
    """End-to-End Orchestrator for Academic Arabic NER and Morphology."""

    async def analyze_text(self, text: str) -> Dict[str, Any]:
        """Executes the hybrid pipeline concurrently and returns normalized results."""
        start_time = time.perf_counter()

        # Run Local BERT and Groq LLM concurrently
        loop = asyncio.get_event_loop()

        # Wrap synchronous BERT call in executor so it does not block the async event loop
        bert_future = loop.run_in_executor(None, local_bert_ner.extract_entities, text)
        groq_future = groq_llm_ner.extract_entities(text)

        bert_entities, groq_entities = await asyncio.gather(
            bert_future,
            groq_future,
            return_exceptions=False,
        )

        # Merge candidate entities and resolve overlapping spans
        merged_entities = fusion_engine.merge_entities(text, bert_entities, groq_entities)

        # Extract morphological trilateral roots for all content words in the sentence
        # Only include resolved roots (word + root), skip unresolved for cleaner output
        raw_roots = root_engine.extract_phrase_roots(text)
        all_roots = [
            {"word": r["word"], "root": r["root"]}
            for r in raw_roots
            if r.get("root") and r.get("status") == "analyzed"
        ]

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        logger.info(
            f"Hybrid Fusion: hatmimoha={len(bert_entities)} ents | Groq={len(groq_entities)} ents -> Merged={len(merged_entities)} final ents | Roots={len(all_roots)} in {elapsed_ms}ms"
        )

        return {
            "original_text": text,
            "entities": merged_entities,
            "all_roots": all_roots,
            "processing_time_ms": elapsed_ms,
            "pipeline_status": {
                "bert_entities_count": len(bert_entities),
                "groq_entities_count": len(groq_entities),
                "merged_entities_count": len(merged_entities),
                "roots_extracted_count": len(all_roots),
            },
        }


nlp_pipeline = ArabicNLPPipeline()
