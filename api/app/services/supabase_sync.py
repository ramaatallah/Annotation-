"""Supabase Cloud Database Synchronization Service.

Ensures every local annotation, detected entity, and trilateral morphological root
is synchronized to the remote Supabase PostgreSQL database in real-time.
"""

import logging
from typing import Optional, Dict, Any, List
import requests
from app.config import settings

logger = logging.getLogger("wahaj.supabase_sync")


class SupabaseSyncService:
    """Manages cloud synchronization of academic annotations and NLP entities to Supabase."""

    def __init__(self):
        self.url = (settings.SUPABASE_URL or "").rstrip("/")
        self.key = settings.SUPABASE_KEY or ""
        self.enabled = bool(settings.ENABLE_SUPABASE_SYNC and self.url and self.key)

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def sync_annotation(
        self,
        annotation_data: Dict[str, Any],
        entities_data: List[Dict[str, Any]],
    ) -> Optional[int]:
        """
        Saves annotation and all its detected entities & trilateral roots to Supabase.
        Returns the created Supabase annotation ID, or None if sync failed.
        """
        if not self.enabled:
            return None

        try:
            # 1. Insert Annotation
            ann_payload = {
                "url": annotation_data.get("url"),
                "page_title": annotation_data.get("page_title"),
                "selected_text": annotation_data.get("selected_text"),
                "note": annotation_data.get("note"),
                "color": annotation_data.get("color", "#FFE082"),
                "author_name": annotation_data.get("author_name", "باحث"),
                "visibility": annotation_data.get("visibility", "private"),
            }
            if annotation_data.get("user_id"):
                ann_payload["user_id"] = annotation_data["user_id"]
            if annotation_data.get("project_id"):
                ann_payload["project_id"] = annotation_data["project_id"]

            res = requests.post(
                f"{self.url}/rest/v1/annotations",
                headers=self.headers,
                json=ann_payload,
                timeout=6.0,
            )

            if not res.ok:
                logger.warning(f"Supabase annotation insert returned {res.status_code}: {res.text}")
                return None

            inserted_ann = res.json()
            if not inserted_ann or not isinstance(inserted_ann, list):
                return None

            cloud_ann_id = inserted_ann[0].get("id")

            # 2. Insert Entities and Roots
            for ent in entities_data:
                ent_payload = {
                    "annotation_id": cloud_ann_id,
                    "text": ent.get("text"),
                    "category": ent.get("category", "CONCEPT"),
                    "confidence": float(ent.get("confidence", 1.0)),
                    "source": ent.get("source", "Hybrid"),
                    "start_char": int(ent.get("start_char", 0)),
                    "end_char": int(ent.get("end_char", 0)),
                }

                ent_res = requests.post(
                    f"{self.url}/rest/v1/detected_entities",
                    headers=self.headers,
                    json=ent_payload,
                    timeout=5.0,
                )

                if ent_res.ok:
                    inserted_ent = ent_res.json()
                    if inserted_ent and isinstance(inserted_ent, list):
                        cloud_ent_id = inserted_ent[0].get("id")

                        # Insert word roots for this entity
                        for root in ent.get("roots", []):
                            root_payload = {
                                "entity_id": cloud_ent_id,
                                "word": root.get("word"),
                                "root": root.get("root"),
                                "lemma": root.get("lemma"),
                                "pos": root.get("pos"),
                                "segmentation": root.get("segmentation"),
                                "source": root.get("source", "camel_tools"),
                                "status": root.get("status", "analyzed"),
                                "is_trilateral": root.get("is_trilateral", True),
                            }
                            try:
                                requests.post(
                                    f"{self.url}/rest/v1/word_roots",
                                    headers=self.headers,
                                    json=root_payload,
                                    timeout=4.0,
                                )
                            except Exception as re:
                                logger.debug(f"Root sync warning: {re}")

            logger.info(f"Successfully synced annotation #{cloud_ann_id} to Supabase cloud.")
            return cloud_ann_id

        except Exception as e:
            logger.warning(f"Supabase cloud sync skipped or failed (local SQLite is safe): {e}")
            return None

    def delete_annotation(self, annotation_id: int):
        """Deletes annotation from Supabase cloud (cascading deletes entities and roots)."""
        if not self.enabled:
            return
        try:
            requests.delete(
                f"{self.url}/rest/v1/annotations?id=eq.{annotation_id}",
                headers=self.headers,
                timeout=5.0,
            )
        except Exception as e:
            logger.debug(f"Cloud delete error: {e}")


supabase_sync = SupabaseSyncService()
