"""Main API Server Entrypoint.

Wahaj / Hashiya Arabic Academic NLP & Knowledge Engine.
Exposes modern v1 modular routes and provides backward compatibility for website callers.
"""

import sys
import os
from typing import Optional
from pydantic import BaseModel, Field

# Ensure api directory is on sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from app.main import app
from app.services.nlp.pipeline import nlp_pipeline


class WebsiteAnalyzeRequest(BaseModel):
    text: str = Field(min_length=1)
    url: Optional[str] = None
    page_title: Optional[str] = None


@app.post("/analyze", tags=["Website Compatibility"])
async def website_analyze_endpoint(req: WebsiteAnalyzeRequest):
    """
    Backward-compatible /analyze endpoint for website client.
    Normalizes response structure so website TryIt and Live Analysis work instantly.
    """
    text = (req.text or "").strip()
    if not text:
        return {"entities": []}

    result = await nlp_pipeline.analyze_text(text)

    # Normalize entities for website frontend expectations
    normalized_entities = []
    for ent in result.get("entities", []):
        # Extract primary root from words if available
        primary_root = "—"
        for r in ent.get("roots", []):
            if r.get("root"):
                primary_root = r["root"]
                break

        category = ent.get("category", "OTHER")
        confidence = float(ent.get("confidence", 0.95))
        label_ar = ent.get("label_ar")

        normalized_entities.append({
            "text": ent.get("text"),
            "type": category,
            "label": label_ar or category,
            "label_ar": label_ar,
            "confidence": confidence,
            "score": round(confidence * 100, 1) if confidence <= 1.0 else round(confidence, 1),
            "start": ent.get("start_char", 0),
            "end": ent.get("end_char", len(ent.get("text", ""))),
            "root": primary_root,
            "roots": ent.get("roots", []),
            "source": ent.get("source", "Hybrid"),
        })

    return {
        "entities": normalized_entities,
        "all_roots": result.get("all_roots", []),
        "original_text": text,
        "processing_time_ms": result.get("processing_time_ms", 0),
    }


if __name__ == "__main__":
    import uvicorn
    print("=" * 65)
    print(" Starting Wahaj / Hashiya Arabic Annotation & NLP Server")
    print(" Documentation: http://localhost:8000/docs")
    print(" Legacy endpoint: http://localhost:8000/analyze")
    print(" V1 endpoints: http://localhost:8000/v1/analyze")
    print("=" * 65)
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
