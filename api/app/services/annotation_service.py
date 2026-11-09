"""Service layer for Annotation lifecycle and Semantic Search."""

import logging
import urllib.parse
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models.annotation import Annotation, DetectedEntity, WordRoot
from app.schemas.annotation import AnnotationCreate, AnnotationUpdate
from app.services.nlp.pipeline import nlp_pipeline
from app.services.supabase_sync import supabase_sync

logger = logging.getLogger(__name__)


def canonicalize_url(u: Optional[str]) -> str:
    """Canonicalizes URLs by unquoting percent-encoded characters, stripping hash fragments and trailing slashes."""
    if not u:
        return ""
    try:
        decoded = urllib.parse.unquote(u).strip()
        if "#" in decoded:
            decoded = decoded.split("#")[0]
        return decoded.rstrip("/")
    except Exception:
        return (u or "").strip()


class AnnotationService:
    """Manages database storage, updates, and semantic search for annotations."""

    async def create_annotation(self, db: Session, payload: AnnotationCreate) -> Annotation:
        """Creates a new annotation and optionally runs the Arabic NLP analysis pipeline."""
        annotation = Annotation(
            url=canonicalize_url(payload.url),
            page_title=payload.page_title,
            selected_text=payload.selected_text,
            note=payload.note,
            color=payload.color or "#FFE082",
            user_id=payload.user_id,
            author_name=payload.author_name or "باحث",
            project_id=payload.project_id,
            visibility=payload.visibility or "private",
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

        # Cloud Sync to Supabase in real-time
        try:
            entities_payload = []
            if payload.auto_analyze and "analysis" in locals():
                entities_payload = analysis.get("entities", [])
            supabase_sync.sync_annotation(
                annotation_data={
                    "url": annotation.url,
                    "page_title": annotation.page_title,
                    "selected_text": annotation.selected_text,
                    "note": annotation.note,
                    "color": annotation.color,
                    "user_id": annotation.user_id,
                    "author_name": annotation.author_name,
                    "project_id": annotation.project_id,
                    "visibility": annotation.visibility,
                },
                entities_data=entities_payload,
            )
        except Exception as se:
            logger.debug(f"Cloud sync notification error: {se}")

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
        """Lists annotations, with automatic two-way reconciliation against Supabase cloud."""
        query = db.query(Annotation)
        if url:
            target_norm = canonicalize_url(url)

            # Two-way synchronization check against Supabase
            if supabase_sync.enabled:
                try:
                    cloud_records = supabase_sync.get_annotations_for_url(target_norm)
                    if cloud_records is not None:
                        # 1. Reconcile deletions from Supabase:
                        # If a record exists locally for this URL but was deleted in Supabase, remove it locally
                        import datetime
                        now = datetime.datetime.utcnow()
                        cloud_texts = {cr.get("selected_text") for cr in cloud_records if cr.get("selected_text")}
                        local_for_url = [a for a in query.all() if canonicalize_url(a.url) == target_norm]
                        for loc in local_for_url:
                            # Grace period: DO NOT delete newly created annotations (< 25s) while cloud sync is completing
                            age_sec = (now - loc.created_at).total_seconds() if loc.created_at else 999
                            if age_sec > 25 and loc.selected_text not in cloud_texts:
                                db.delete(loc)
                            else:
                                # Reconcile notes/color edits made directly in Supabase
                                for cr in cloud_records:
                                    if cr.get("selected_text") == loc.selected_text:
                                        if cr.get("note") != loc.note:
                                            loc.note = cr.get("note")
                                        if cr.get("color") and cr.get("color") != loc.color:
                                            loc.color = cr.get("color")
                                        break
                        db.commit()
                except Exception as se:
                    logger.debug(f"Two-way sync reconciliation skipped: {se}")

            all_records = query.order_by(Annotation.created_at.desc()).all()
            matched = [
                ann for ann in all_records
                if canonicalize_url(ann.url) == target_norm
            ]
            return matched[skip:skip + limit]

        return query.order_by(Annotation.created_at.desc()).offset(skip).limit(limit).all()

    async def update_annotation(
        self,
        db: Session,
        annotation_id: int,
        payload: AnnotationUpdate,
    ) -> Optional[Annotation]:
        """Updates note, color, or text of an annotation with real-time Supabase cloud sync."""
        annotation = self.get_by_id(db, annotation_id)
        if not annotation:
            return None

        updated_fields = {}
        text_changed = False
        if payload.note is not None:
            annotation.note = payload.note
            updated_fields["note"] = payload.note
        if payload.color is not None:
            annotation.color = payload.color
            updated_fields["color"] = payload.color
        if payload.selected_text is not None and payload.selected_text != annotation.selected_text:
            annotation.selected_text = payload.selected_text
            updated_fields["selected_text"] = payload.selected_text
            text_changed = True

        db.commit()

        # If text changed, re-run NLP pipeline to update entities and roots
        if text_changed:
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

        # Real-time Cloud Sync to Supabase for Updates
        try:
            if updated_fields:
                supabase_sync.update_annotation(
                    url=annotation.url,
                    selected_text=annotation.selected_text,
                    updated_fields=updated_fields,
                )
        except Exception as se:
            logger.debug(f"Cloud update sync warning: {se}")

        db.refresh(annotation)
        return annotation

    def delete_annotation(self, db: Session, annotation_id: int) -> bool:
        """Deletes an annotation locally and cascades deletion to Supabase cloud."""
        annotation = self.get_by_id(db, annotation_id)
        if not annotation:
            return False

        url = annotation.url
        selected_text = annotation.selected_text

        db.delete(annotation)
        db.commit()

        try:
            supabase_sync.delete_annotation(
                url=url,
                selected_text=selected_text,
                annotation_id=annotation_id,
            )
        except Exception as se:
            logger.debug(f"Cloud delete sync warning: {se}")

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
