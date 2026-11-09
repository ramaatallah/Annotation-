"""Semantic and Morphological Search Endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.annotation import AnnotationSearchResult, AnnotationResponse
from app.services.annotation_service import annotation_service

router = APIRouter(prefix="/search", tags=["Search & Queries"])


@router.get(
    "",
    response_model=AnnotationSearchResult,
    status_code=status.HTTP_200_OK,
    summary="Semantic and Morphological Search",
    description=(
        "Query annotations by Entity Type (e.g. 'Show me all annotations related to universities' via category=UNIVERSITY), "
        "by Trilateral Morphological Root (e.g. root=جمع or root=درس), or free-text search."
    ),
)
def search_annotations(
    query: Optional[str] = Query(None, description="Free text search in highlights and notes"),
    category: Optional[str] = Query(
        None,
        description="Filter by Entity Category (e.g. UNIVERSITY, LOCATION, DISEASE, TECHNOLOGY, CONCEPT, PERSON)",
    ),
    root: Optional[str] = Query(
        None,
        description="Filter by Trilateral Morphological Root (الجذر الثلاثي, e.g. جمع, درس, وطن, مرض)",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    results = annotation_service.search(
        db=db,
        query=query,
        category=category,
        root=root,
        skip=skip,
        limit=limit,
    )

    formatted = [AnnotationResponse.model_validate(r) for r in results]

    return AnnotationSearchResult(
        total_count=len(formatted),
        query=query,
        category_filter=category,
        root_filter=root,
        results=formatted,
    )
