"""CRUD API Endpoints for Web Annotations and Notes."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.annotation import (
    AnnotationCreate,
    AnnotationUpdate,
    AnnotationResponse,
)
from app.services.annotation_service import annotation_service

router = APIRouter(prefix="/annotations", tags=["Annotations"])
logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Web Highlight & Note",
    description="Saves a user highlight, attaches optional notes, and executes NLP pipeline.",
)
async def create_annotation(
    payload: AnnotationCreate,
    db: Session = Depends(get_db),
):
    try:
        annotation = await annotation_service.create_annotation(db, payload)
        return annotation
    except Exception as e:
        logger.error(f"Error creating annotation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create annotation: {str(e)}",
        )


@router.get(
    "",
    response_model=List[AnnotationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Annotations",
    description="Retrieves annotations, optionally filtered by page URL for browser persistent highlights.",
)
def list_annotations(
    url: Optional[str] = Query(None, description="Filter annotations by page URL"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return annotation_service.list_annotations(db, url=url, skip=skip, limit=limit)


@router.get(
    "/{annotation_id}",
    response_model=AnnotationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Annotation by ID",
)
def get_annotation(
    annotation_id: int,
    db: Session = Depends(get_db),
):
    annotation = annotation_service.get_by_id(db, annotation_id)
    if not annotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Annotation #{annotation_id} not found.",
        )
    return annotation


@router.put(
    "/{annotation_id}",
    response_model=AnnotationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Annotation Note or Text",
    description="Updates user note, highlight color, or text (re-running NLP if text changed).",
)
async def update_annotation(
    annotation_id: int,
    payload: AnnotationUpdate,
    db: Session = Depends(get_db),
):
    updated = await annotation_service.update_annotation(db, annotation_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Annotation #{annotation_id} not found.",
        )
    return updated


@router.delete(
    "/{annotation_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Annotation",
)
def delete_annotation(
    annotation_id: int,
    db: Session = Depends(get_db),
):
    success = annotation_service.delete_annotation(db, annotation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Annotation #{annotation_id} not found.",
        )
    return {"message": f"Annotation #{annotation_id} deleted successfully."}
