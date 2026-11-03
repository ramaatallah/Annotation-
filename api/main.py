# -*- coding: utf-8 -*-
"""
FastAPI Server Root Entry Point.
Delegates to the modular app package (app.main:app)
while maintaining backward-compatible endpoints for legacy callers.
"""

import sys
import os

# Ensure api directory and project root are on sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from app.main import app
from app.nlp.ner_local import extract_local_entities
from app.nlp.ner_llm import extract_llm_entities
from app.nlp.fusion import fuse_entities
from pydantic import BaseModel, Field
from typing import Optional


class LegacyAnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    page_url: Optional[str] = None
    title: Optional[str] = None


@app.get("/")
def home():
    return {"status": "ok", "message": "Annotation NER API is running"}


@app.post("/analyze")
async def legacy_analyze(req: LegacyAnalyzeRequest):
    """
    Backward-compatible /analyze endpoint.
    Allows callers to analyze text without strict Bearer token requirement during transition.
    """
    text = (req.text or "").strip()
    if not text:
        return {"entities": []}

    local_ents = extract_local_entities(text)
    llm_ents = await extract_llm_entities(text)
    fused, _ = fuse_entities(text, local_ents, llm_ents)

    # Format in legacy-compatible structure
    legacy_entities = []
    for e in fused:
        primary_root = None
        for w in e.get("words", []):
            if w.get("status") in ("found", "quadrilateral") and w.get("root"):
                primary_root = w.get("root")
                break

        legacy_entities.append({
            "text": e["text"],
            "type": e["type"],
            "type_ar": e.get("type_ar"),
            "subtype_ar": e.get("subtype_ar"),
            "domain": e.get("domain"),
            "root": primary_root,
            "words": e.get("words", []),
            "start": e.get("start"),
            "end": e.get("end"),
            "source": e.get("source"),
            "confidence": e.get("llm_self_confidence") or e.get("bert_score") or 0.95,
        })

    return {"entities": legacy_entities}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
