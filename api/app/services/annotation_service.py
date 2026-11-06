"""Service layer for Annotation lifecycle and Semantic Search."""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models.annotation import Annotation, DetectedEntity, WordRoot
from app.schemas.annotation import AnnotationCreate, AnnotationUpdate
from app.services.nlp.pipeline import nlp_pipeline

logger = logging.getLogger(__name__)


class AnnotationService:
    """Manages database storage, updates, and semantic search for annotations."""

    async def create_annotation(self, db: Session, payload: AnnotationCreate) -> Annotation:
        """Creates a new annotation and optionally runs the Arabic NLP analysis pipeline."""
        annotation = Annotation(
            url=payload.url,
            page_title=payload.page_title,
            selected_text=payload.selected_text,
            note=payload.note,
            color=payload.color or "#FFE082",
        )
        db.add(annotation)
        db.commit()
        db.refresh(annotation)

        if payload.auto_analyze:
            try:
                analysis = await nlp_pipeline.analyze_text(payload.selected_text)

                for ent in analysis.get("entities", []):
                    db_entity = DetectedEntity(
                        annotation_id=annotation.id,
                        text=ent["text"],
                        category=ent["category"],
                        confidence=ent["confidence"],
                        source=ent["source"],
                        start_char=ent["start_char"],
                        end_char=ent["end_char"],
                    )
                    db.add(db_entity)
                    db.commit()
                    db.refresh(db_entity)

                    # Store constituent roots
                    for r in ent.get("roots", []):
                        db_root = WordRoot(
                            entity_id=db_entity.id,
                            word=r["word"],
                            root=r.get("root"),
                            lemma=r.get("lemma"),
                            pos=r.get("pos"),
                            segmentation=r.get("segmentation"),
                            source=r.get("source", "camel_tools"),
                            status=r.get("status", "analyzed"),
                            is_trilateral=r.get("is_trilateral", True),
                        )
                        db.add(db_root)

                db.commit()
                db.refresh(annotation)
            except Exception as e:
                logger.error(f"Error auto-analyzing annotation #{annotation.id}: {e}")

        return annotation

    def get_by_id(self, db: Session, annotation_id: int) -> Optional[Annotation]:
        """Fetches a single annotation with eager-loaded entities and roots."""
        return db.query(Annotation).filter(Annotation.id == annotation_id).first()

    def list_annotations(
        self,
        db: Session,
        url: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Annotation]:
        """Lists annotations, optionally filtered by page URL for browser extension restore."""
        query = db.query(Annotation)
        if url:
            query = query.filter(Annotation.url == url)
        return query.order_by(Annotation.created_at.desc()).offset(skip).limit(limit).all()

    async def update_annotation(
        self,
        db: Session,
        annotation_id: int,
        payload: AnnotationUpdate,
    ) -> Optional[Annotation]:
        """Updates note, color, or text of an annotation."""
        annotation = self.get_by_id(db, annotation_id)
        if not annotation:
            return None

        text_changed = False
        if payload.note is not None:
            annotation.note = payload.note
        if payload.color is not None:
            annotation.color = payload.color
        if payload.selected_text is not None and payload.selected_text != annotation.selected_text:
            annotation.selected_text = payload.selected_text
            text_changed = True

        db.commit()

        # If text changed, re-run NLP pipeline to update entities and roots
        if text_changed:
            # Remove old entities
            db.query(DetectedEntity).filter(DetectedEntity.annotation_id == annotation.id).delete()
            db.commit()

            analysis = await nlp_pipeline.analyze_text(annotation.selected_text)
            for ent in analysis.get("entities", []):
                db_entity = DetectedEntity(
                    annotation_id=annotation.id,
                    text=ent["text"],
                    category=ent["category"],
                    confidence=ent["confidence"],
                    source=ent["source"],
                    start_char=ent["start_char"],
                    end_char=ent["end_char"],
                )
                db.add(db_entity)
                db.commit()
                db.refresh(db_entity)

                for r in ent.get("roots", []):
                    db_root = WordRoot(
                        entity_id=db_entity.id,
                        word=r["word"],
                        root=r.get("root"),
                        lemma=r.get("lemma"),
                        pos=r.get("pos"),
                        segmentation=r.get("segmentation"),
                        source=r.get("source", "camel_tools"),
                        status=r.get("status", "analyzed"),
                        is_trilateral=r.get("is_trilateral", True),
                    )
                    db.add(db_root)
            db.commit()

        db.refresh(annotation)
        return annotation

    def delete_annotation(self, db: Session, annotation_id: int) -> bool:
        """Deletes an annotation and cascades to its entities and roots."""
        annotation = self.get_by_id(db, annotation_id)
        if not annotation:
            return False
        db.delete(annotation)
        db.commit()
        return True

    def search(
        self,
        db: Session,
        query: Optional[str] = None,
        category: Optional[str] = None,
        root: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Annotation]:
        """Multi-criteria search supporting text, entity category, and trilateral root queries."""
        q = db.query(Annotation).distinct()

        # Filter by entity category (e.g. UNIVERSITY, DISEASE, LOCATION)
        if category:
            q = q.join(Annotation.entities).filter(
                func.upper(DetectedEntity.category) == category.upper()
            )

        # Filter by morphological trilateral root (e.g. جمع, درس, وطن)
        if root:
            if not category:
                q = q.join(Annotation.entities)
            q = q.join(DetectedEntity.roots).filter(
                WordRoot.root == root.strip()
            )

        # Free text query across selected text, notes, and entity text
        if query and query.strip():
            term = f"%{query.strip()}%"
            q = q.outerjoin(Annotation.entities).filter(
                or_(
                    Annotation.selected_text.ilike(term),
                    Annotation.note.ilike(term),
                    DetectedEntity.text.ilike(term),
                )
            )

        return q.order_by(Annotation.created_at.desc()).offset(skip).limit(limit).all()


annotation_service = AnnotationService()
