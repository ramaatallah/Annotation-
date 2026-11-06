# -*- coding: utf-8 -*-
"""
Annotation Backend API - FastAPI Application Entry Point.
Production-grade endpoints for Arabic Academic Entity Recognition.
"""

import time
from contextlib import asynccontextmanager
from typing import List, Optional
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalysisMeta,
    EntitySchema,
    WordRootSchema,
    SaveAnnotationRequest,
    UpdateAnnotationRequest,
    AnnotationActionResponse,
    CorrectionRequest,
    CorrectionResponse,
    HealthCheckResponse,
)
from app.deps import parse_jwt_user_id, rate_limiter
from app.nlp.normalize import compute_sha256
from app.nlp.chunking import split_into_chunks
from app.nlp.ner_local import init_local_ner, extract_local_entities, is_local_ner_available
from app.nlp.ner_llm import extract_llm_entities
from app.nlp.fusion import fuse_entities
from app.nlp.roots.camel_engine import CamelRootEngine
from app.db.repo import repo


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize local models and analyzers
    init_local_ner()
    yield
    # Shutdown logic if needed


app = FastAPI(
    title="Arabic Academic Annotation & NER API",
    version="1.0.0",
    description="Backend service for Academic Entity Classification.",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health readiness check returning model and engine availability."""
    camel_eng = CamelRootEngine()
    return HealthCheckResponse(
        status="ready",
        llm_enabled=settings.llm_enabled and bool(settings.llm_api_key),
        models_loaded={
            "ner_local_bert": is_local_ner_available(),
            "camel_roots": camel_eng.is_available(),
        },
        versions={
            "api": "1.0.0",
            "prompt_version": settings.prompt_version,
            "models": settings.llm_models,
        },
    )


@app.get("/v1/roots", response_model=WordRootSchema)
async def get_word_root(
    word: str = Query(..., min_length=1, description="Word to analyze"),
):
    """Direct query for single-word morphological root analysis via CAMeL Tools."""
    camel_eng = CamelRootEngine()
    res = camel_eng.extract_root(word)
    if not res:
        return WordRootSchema(word=word, status="not_found", engine="camel")
    return WordRootSchema(**res.to_dict())


@app.post("/v1/analyze", response_model=AnalyzeResponse)
async def analyze_text(
    payload: AnalyzeRequest,
    user_id: UUID = Depends(parse_jwt_user_id),
):
    """
    Analyzes Arabic text, extracts academic entities, and performs span verification.
    """
    rate_limiter(user_id)
    raw_text = payload.text.strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="Empty text provided.")
    if len(raw_text) > settings.max_text_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Text exceeds maximum allowed length of {settings.max_text_chars} characters.",
        )

    start_time = time.time()
    text_hash = compute_sha256(raw_text)

    # Chunking long documents at sentence boundaries to prevent silent truncation
    chunks = split_into_chunks(raw_text, max_chunk_size=1200, overlap=100)
    all_local_entities = []
    all_llm_entities = []
    degraded = False

    try:
        # Extract local BERT entities across chunks
        for chunk_text, chunk_offset in chunks:
            local_ents = extract_local_entities(chunk_text)
            for le in local_ents:
                if le.get("start") is not None and le.get("end") is not None:
                    le["start"] += chunk_offset
                    le["end"] += chunk_offset
                all_local_entities.append(le)
    except Exception as exc:
        print(f"[BERT Extraction Error] {exc}")
        degraded = True

    try:
        # Extract LLM entities across chunks
        for chunk_text, chunk_offset in chunks:
            llm_ents = await extract_llm_entities(chunk_text)
            all_llm_entities.extend(llm_ents)
    except Exception as exc:
        print(f"[LLM Extraction Error] {exc}")
        degraded = True

    # If both failed, return 503 instead of false empty
    if not all_local_entities and not all_llm_entities and degraded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="All entity recognition engines are temporarily unavailable.",
        )

    # Fusion and Span Verification
    fused_entities, rejected_count = fuse_entities(
        original_text=raw_text,
        local_entities=all_local_entities,
        llm_entities=all_llm_entities,
    )

    latency_ms = int((time.time() - start_time) * 1000)

    # Record analysis run asynchronously
    versions = {
        "llm_models": settings.llm_models,
        "prompt_version": settings.prompt_version,
    }
    await repo.record_analysis_run(
        user_id=user_id,
        text_hash=text_hash,
        versions=versions,
        latency_ms=latency_ms,
        degraded=degraded,
    )

    entities_schemas = [EntitySchema(**e) for e in fused_entities]
    meta = AnalysisMeta(
        text_hash=text_hash,
        versions=versions,
        degraded=degraded,
        truncated=False,
        rejected_by_span_check=rejected_count,
    )

    return AnalyzeResponse(entities=entities_schemas, meta=meta)


@app.post("/v1/annotations", response_model=AnnotationActionResponse)
async def save_annotation(
    payload: SaveAnnotationRequest,
    user_id: UUID = Depends(parse_jwt_user_id),
):
    """
    Atomic annotation save.
    Re-analyzes text server-side, extracts entities,
    and invokes the save_annotation_with_entities PostgreSQL RPC.
    """
    try:
        rate_limiter(user_id)
        raw_text = payload.text.strip()
        if not raw_text:
            raise HTTPException(status_code=400, detail="Empty text provided.")

        # 1. Resolve or create page
        page_id = await repo.get_or_create_page(
            user_id=user_id,
            url=payload.url,
            title=payload.title or "",
        )
        if not page_id:
            raise HTTPException(status_code=500, detail="Failed to initialize page record in Supabase.")

        # 2. Server-side authoritative analysis (never trust client-supplied entities)
        local_ents = extract_local_entities(raw_text)
        llm_ents = await extract_llm_entities(raw_text)
        fused_ents, _ = fuse_entities(raw_text, local_ents, llm_ents)

        # 3. Atomic RPC commit
        success = await repo.save_annotation_atomic(
            user_id=user_id,
            annotation_id=payload.id,
            page_id=page_id,
            selected_text=raw_text,
            note=payload.note or "",
            context_before=payload.contextBefore or "",
            context_after=payload.contextAfter or "",
            entities=fused_ents,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save annotation atomically.")

        return AnnotationActionResponse(
            success=True,
            annotation_id=payload.id,
            message="Annotation and entities saved successfully.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Annotation save error: {exc}")


@app.put("/v1/annotations/{annotation_id}", response_model=AnnotationActionResponse)
async def update_annotation_note(
    annotation_id: UUID,
    payload: UpdateAnnotationRequest,
    user_id: UUID = Depends(parse_jwt_user_id),
):
    """Updates user-owned annotation note atomically."""
    rate_limiter(user_id)
    success = await repo.update_annotation_note(
        user_id=user_id,
        annotation_id=annotation_id,
        note=payload.note or "",
    )
    if not success:
        raise HTTPException(status_code=404, detail="Annotation not found or not owned by user.")

    return AnnotationActionResponse(
        success=True,
        annotation_id=annotation_id,
        message="Annotation note updated successfully.",
    )


@app.delete("/v1/annotations/{annotation_id}", response_model=AnnotationActionResponse)
async def delete_annotation(
    annotation_id: UUID,
    user_id: UUID = Depends(parse_jwt_user_id),
):
    """Deletes user-owned annotation and cascades related links."""
    rate_limiter(user_id)
    success = await repo.delete_annotation(user_id=user_id, annotation_id=annotation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Annotation not found or not owned by user.")

    return AnnotationActionResponse(
        success=True,
        annotation_id=annotation_id,
        message="Annotation deleted successfully.",
    )


@app.post("/v1/corrections", response_model=CorrectionResponse)
async def submit_correction(
    payload: CorrectionRequest,
    user_id: UUID = Depends(parse_jwt_user_id),
):
    """Submits a researcher feedback correction for gold dataset curation."""
    rate_limiter(user_id)
    corr_id = await repo.add_correction(
        user_id=user_id,
        annotation_entity_id=payload.annotation_entity_id,
        field=payload.field,
        old_value=payload.old_value,
        new_value=payload.new_value,
    )
    if not corr_id:
        raise HTTPException(status_code=500, detail="Failed to record correction.")

    return CorrectionResponse(
        id=UUID(corr_id),
        status="pending",
        message="Correction submitted successfully for review.",
    )
