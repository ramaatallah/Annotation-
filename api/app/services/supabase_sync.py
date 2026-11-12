"""Supabase Cloud Database Synchronization Service.

Ensures every local annotation, detected entity, and trilateral morphological root
is synchronized to the remote Supabase PostgreSQL database in real-time,
supporting two-way synchronization for updates and deletions.
"""

import logging
import urllib.parse
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
            raw_url = annotation_data.get("url") or ""
            clean_url = urllib.parse.unquote(raw_url).strip()

            ann_payload = {
                "url": clean_url,
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

    def update_annotation(
        self,
        url: str,
        selected_text: str,
        updated_fields: Dict[str, Any],
    ) -> bool:
        """Updates note and/or color of an annotation in Supabase in real-time."""
        if not self.enabled:
            return False

        try:
            raw_url = (url or "").strip()
            decoded_url = urllib.parse.unquote(raw_url)
            encoded_url = urllib.parse.quote(decoded_url, safe=":/#?=&")

            # Update across both decoded and encoded URL variants
            for u in list(dict.fromkeys([decoded_url, encoded_url, raw_url])):
                params = {
                    "url": f"eq.{u}",
                    "selected_text": f"eq.{selected_text}",
                }
                res = requests.patch(
                    f"{self.url}/rest/v1/annotations",
                    params=params,
                    headers=self.headers,
                    json=updated_fields,
                    timeout=5.0,
                )
                if res.ok and res.json():
                    logger.info(f"Successfully updated annotation in Supabase cloud for URL: {u}")
                    return True

            return False
        except Exception as e:
            logger.warning(f"Supabase cloud update skipped or failed: {e}")
            return False

    def delete_annotation(
        self,
        url: str,
        selected_text: str,
        annotation_id: Optional[int] = None,
    ) -> bool:
        """Deletes annotation from Supabase cloud by matching url and selected_text (or ID)."""
        if not self.enabled:
            return False

        try:
            raw_url = (url or "").strip()
            decoded_url = urllib.parse.unquote(raw_url)
            encoded_url = urllib.parse.quote(decoded_url, safe=":/#?=&")

            cloud_ids = []
            for u in list(dict.fromkeys([decoded_url, encoded_url, raw_url])):
                params = {
                    "url": f"eq.{u}",
                    "selected_text": f"eq.{selected_text}",
                    "select": "id",
                }
                res = requests.get(
                    f"{self.url}/rest/v1/annotations",
                    params=params,
                    headers=self.headers,
                    timeout=4.0,
                )
                if res.ok and isinstance(res.json(), list):
                    for item in res.json():
                        if "id" in item and item["id"] not in cloud_ids:
                            cloud_ids.append(item["id"])

            if not cloud_ids and annotation_id:
                cloud_ids = [annotation_id]

            for cid in cloud_ids:
                # Clean up child records (entities and roots)
                try:
                    requests.delete(
                        f"{self.url}/rest/v1/detected_entities?annotation_id=eq.{cid}",
                        headers=self.headers,
                        timeout=3.0,
                    )
                except Exception:
                    pass

                del_res = requests.delete(
                    f"{self.url}/rest/v1/annotations?id=eq.{cid}",
                    headers=self.headers,
                    timeout=5.0,
                )
                if del_res.ok:
                    logger.info(f"Deleted annotation #{cid} from Supabase cloud.")

            return True
        except Exception as e:
            logger.warning(f"Supabase cloud delete failed: {e}")
            return False

    def get_annotations_for_url(self, url: str) -> Optional[List[Dict[str, Any]]]:
        """Fetches active annotations from Supabase for two-way synchronization."""
        if not self.enabled or not url:
            return None

        try:
            raw_url = (url or "").strip()
            decoded_url = urllib.parse.unquote(raw_url)
            encoded_url = urllib.parse.quote(decoded_url, safe=":/#?=&")

            records = []
            seen_texts = set()

            for u in list(dict.fromkeys([decoded_url, encoded_url, raw_url])):
                res = requests.get(
                    f"{self.url}/rest/v1/annotations",
                    params={
                        "url": f"eq.{u}",
                        "select": "id,url,page_title,selected_text,note,color,author_name,visibility,created_at",
                    },
                    headers=self.headers,
                    timeout=5.0,
                )
                if res.ok and isinstance(res.json(), list):
                    for r in res.json():
                        st = r.get("selected_text")
                        if st and st not in seen_texts:
                            seen_texts.add(st)
                            records.append(r)

            return records
        except Exception as e:
            logger.debug(f"Could not fetch annotations from Supabase for sync: {e}")
            return None


supabase_sync = SupabaseSyncService()
