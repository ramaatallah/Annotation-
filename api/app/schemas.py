# -*- coding: utf-8 -*-
"""
Pydantic Schemas for API requests and responses.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# Root Extraction Schemas (CAMeL Tools)
# -------------------------------------------------------------
class WordRootSchema(BaseModel):
    word: str
    root: Optional[str] = None
    root_len: Optional[int] = None
    status: str = Field(
        ...,
        description="One of: found, quadrilateral, not_found, unknown",
    )
    engine: Optional[str] = None
    engine_version: Optional[str] = None
    candidates: List[str] = Field(default_factory=list)
    needs_review: bool = False


# -------------------------------------------------------------
# Entity Schemas
# -------------------------------------------------------------
class EntitySchema(BaseModel):
    text: str
    type: str
    type_ar: Optional[str] = None
    subtype_ar: Optional[str] = None
    domain: Optional[str] = None
    start: Optional[int] = None
    end: Optional[int] = None
    occurrences: int = 1
    source: str = Field(default="llm", description="bert, llm, or both")
    bert_score: Optional[float] = None
    llm_self_confidence: Optional[float] = None
    conflict: bool = False
    words: List[WordRootSchema] = Field(default_factory=list)


# -------------------------------------------------------------
# Analyze Endpoint Schemas
# -------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    page_url: Optional[str] = None
    title: Optional[str] = None


class AnalysisMeta(BaseModel):
    text_hash: str
    versions: Dict[str, Any] = Field(default_factory=dict)
    degraded: bool = False
    truncated: bool = False
    rejected_by_span_check: int = 0


class AnalyzeResponse(BaseModel):
    entities: List[EntitySchema]
    meta: AnalysisMeta


# -------------------------------------------------------------
# Annotations Endpoint Schemas
# -------------------------------------------------------------
class SaveAnnotationRequest(BaseModel):
    id: UUID
    url: str
    title: Optional[str] = ""
    text: str = Field(..., min_length=1)
    note: Optional[str] = ""
    contextBefore: Optional[str] = ""
    contextAfter: Optional[str] = ""


class UpdateAnnotationRequest(BaseModel):
    note: Optional[str] = ""


class AnnotationActionResponse(BaseModel):
    success: bool
    annotation_id: UUID
    message: str


# -------------------------------------------------------------
# Feedback & Corrections
# -------------------------------------------------------------
class CorrectionRequest(BaseModel):
    annotation_entity_id: Optional[UUID] = None
    field: str = Field(..., description="type, span, root, or delete")
    old_value: Optional[str] = None
    new_value: Optional[str] = None


class CorrectionResponse(BaseModel):
    id: UUID
    status: str = "pending"
    message: str


# -------------------------------------------------------------
# Health Check Schema
# -------------------------------------------------------------
class HealthCheckResponse(BaseModel):
    status: str
    llm_enabled: bool
    models_loaded: Dict[str, bool]
    versions: Dict[str, Any]
