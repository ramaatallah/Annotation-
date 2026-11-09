"""API Endpoint for Live Text Analysis (BERT + Groq LLM + Trilateral Roots)."""

import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.nlp import AnalyzeRequest, AnalyzeResponse
from app.services.nlp.pipeline import nlp_pipeline

router = APIRouter(prefix="/analyze", tags=["NLP Analysis"])
logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Highlighted Arabic Text",
    description=(
        "Executes concurrent Hybrid NER (BERT + Groq LLM) to detect academic "
        "and named entities, and applies morphological analysis to extract trilateral roots."
    ),
)
async def analyze_text_endpoint(payload: AnalyzeRequest):
    text = payload.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input text cannot be empty.",
        )

    try:
        result = await nlp_pipeline.analyze_text(text)
        return result
    except Exception as e:
        logger.error(f"Error during text analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"NLP analysis encountered an error: {str(e)}",
        )
