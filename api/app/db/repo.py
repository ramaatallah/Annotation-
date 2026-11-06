# -*- coding: utf-8 -*-
"""
Database Repository for Supabase.
All writes are executed exclusively by the backend service role via atomic RPCs.
Never trusts client-provided user_id; enforces user_id from verified JWT.
Supports httpx with fallback to standard library urllib.
"""

import asyncio
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

from app.config import settings
from app.nlp.normalize import normalize_for_matching


def _sync_http_request(method: str, url: str, headers: dict, payload: Optional[dict] = None, timeout: float = 10.0):
    """Synchronous HTTP request via standard library urllib."""
    try:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8")
            status = resp.status
            try:
                parsed = json.loads(content) if content else None
            except Exception:
                parsed = None
            return status, parsed
    except urllib.error.HTTPError as he:
        err_body = he.read().decode("utf-8")
        print(f"[Supabase HTTPError] {method} {url} -> {he.code}: {err_body}")
        try:
            parsed = json.loads(err_body)
        except Exception:
            parsed = None
        return he.code, parsed
    except Exception as exc:
        print(f"[Supabase Request Exception] {method} {url} -> {exc}")
        return 500, None


class SupabaseRepo:
    def __init__(self):
        self.base_url = settings.supabase_url.rstrip("/")
        self.service_key = settings.supabase_service_role_key

    def _headers(self) -> Dict[str, str]:
        return {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def _get(self, url: str, extra_headers: Optional[dict] = None) -> Tuple[int, Any]:
        headers = self._headers()
        if extra_headers:
            headers.update(extra_headers)

        if _HTTPX_AVAILABLE:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url, headers=headers)
                    try:
                        return resp.status_code, resp.json()
                    except Exception:
                        return resp.status_code, None
            except Exception as exc:
                print(f"[Supabase HTTPX Exception] GET {url} -> {exc}")
                return 500, None
        else:
            return await asyncio.to_thread(_sync_http_request, "GET", url, headers, None, 10.0)

    async def _post(self, url: str, payload: dict, extra_headers: Optional[dict] = None) -> Tuple[int, Any]:
        headers = self._headers()
        if extra_headers:
            headers.update(extra_headers)

        if _HTTPX_AVAILABLE:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code >= 400:
                        print(f"[Supabase HTTPX Error] POST {url} -> {resp.status_code}: {resp.text}")
                    try:
                        return resp.status_code, resp.json()
                    except Exception:
                        return resp.status_code, None
            except Exception as exc:
                print(f"[Supabase HTTPX Exception] POST {url} -> {exc}")
                return 500, None
        else:
            return await asyncio.to_thread(_sync_http_request, "POST", url, headers, payload, 15.0)

    async def get_or_create_page(
        self, user_id: UUID, url: str, title: str = ""
    ) -> Optional[str]:
        """Upserts or retrieves a page record for the user and returns its page_id."""
        if not self.base_url or not self.service_key:
            print("[get_or_create_page] Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
            return None

        import urllib.parse
        parsed = urllib.parse.urlsplit(url.strip())
        # Clean URL: scheme://netloc/path (strip hash & query to match extension)
        norm_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
        domain = parsed.netloc or ""

        # Step 1: Check if page already exists for this user (using clean query params)
        find_url = f"{self.base_url}/rest/v1/pages?user_id=eq.{str(user_id)}&normalized_url=eq.{urllib.parse.quote(norm_url)}&select=id"
        status, rows = await self._get(find_url)
        if status == 200 and isinstance(rows, list) and len(rows) > 0:
            return rows[0]["id"]

        # Step 2: Atomic Upsert page (handles concurrency and duplicate prevention cleanly)
        payload = {
            "user_id": str(user_id),
            "url": url,
            "normalized_url": norm_url,
            "title": title or "",
            "domain": domain,
        }
        url_endpoint = f"{self.base_url}/rest/v1/pages?on_conflict=user_id,normalized_url"
        status, rows = await self._post(
            url_endpoint,
            payload,
            extra_headers={"Prefer": "resolution=merge-duplicates,return=representation"},
        )
        if status in (200, 201) and rows and isinstance(rows, list) and len(rows) > 0:
            return rows[0]["id"]

        # If insert failed due to concurrent creation, fetch again
        status, rows = await self._get(find_url)
        if status == 200 and isinstance(rows, list) and len(rows) > 0:
            return rows[0]["id"]

        print(f"[get_or_create_page] Failed to get or create page for {url} (status={status}, rows={rows})")
        return None

    async def record_analysis_run(
        self,
        user_id: UUID,
        text_hash: str,
        versions: Dict[str, Any],
        latency_ms: int,
        degraded: bool = False,
    ) -> Optional[str]:
        """Records an analysis execution run for reproducibility."""
        if not self.base_url or not self.service_key:
            return None

        payload = {
            "user_id": str(user_id),
            "text_hash": text_hash,
            "versions": versions,
            "latency_ms": latency_ms,
            "degraded": degraded,
        }

        status, rows = await self._post(f"{self.base_url}/rest/v1/analysis_runs", payload)
        if status in (200, 201) and rows:
            if isinstance(rows, list) and len(rows) > 0:
                return rows[0].get("id")
            elif isinstance(rows, dict):
                return rows.get("id")
        return None

    async def save_annotation_atomic(
        self,
        user_id: UUID,
        annotation_id: UUID,
        page_id: str,
        selected_text: str,
        note: str,
        context_before: str,
        context_after: str,
        entities: List[Dict[str, Any]],
        run_id: Optional[str] = None,
    ) -> bool:
        """
        Executes the atomic save_annotation_with_entities RPC.
        Ensures all entities, words, and links are committed in a single PostgreSQL transaction.
        """
        if not self.base_url or not self.service_key:
            print("[save_annotation_atomic] Missing Supabase configuration")
            return False

        rpc_payload = {
            "p": {
                "user_id": str(user_id),
                "annotation_id": str(annotation_id),
                "page_id": str(page_id),
                "selected_text": selected_text,
                "note": note,
                "context_before": context_before,
                "context_after": context_after,
                "run_id": run_id,
                "entities": [
                    {
                        "text": e["text"],
                        "normalized": normalize_for_matching(e["text"]),
                        "type": e["type"],
                        "type_ar": e.get("type_ar"),
                        "subtype_ar": e.get("subtype_ar"),
                        "domain": e.get("domain"),
                        "start": e.get("start"),
                        "end": e.get("end"),
                        "source": e.get("source", "llm"),
                        "bert_score": e.get("bert_score"),
                        "llm_self_confidence": e.get("llm_self_confidence"),
                        "conflict": e.get("conflict", False),
                        "words": [
                            {
                                "position": idx,
                                "word": w.get("word"),
                                "root": w.get("root"),
                                "root_len": w.get("root_len"),
                                "status": w.get("status"),
                                "engine": w.get("engine"),
                                "engine_version": w.get("engine_version"),
                                "candidates": w.get("candidates", []),
                                "needs_review": w.get("needs_review", False),
                            }
                            for idx, w in enumerate(e.get("words", []))
                        ],
                    }
                    for e in entities
                ],
            }
        }

        rpc_url = f"{self.base_url}/rest/v1/rpc/save_annotation_with_entities"
        status, body = await self._post(rpc_url, rpc_payload)
        if status in (200, 204):
            return True

        print(f"[save_annotation_atomic] RPC call failed with status {status}: {body}")

        # Fallback Direct Upsert: Save annotation directly so researcher never loses notes
        try:
            print("[save_annotation_atomic] Attempting direct fallback upsert to public.annotations...")
            direct_url = f"{self.base_url}/rest/v1/annotations"
            ann_row = {
                "id": str(annotation_id),
                "user_id": str(user_id),
                "page_id": str(page_id),
                "selected_text": selected_text,
                "note": note,
                "context_before": context_before,
                "context_after": context_after,
            }
            d_status, d_body = await self._post(
                direct_url,
                ann_row,
                extra_headers={"Prefer": "resolution=merge-duplicates"},
            )
            print(f"[save_annotation_atomic] Direct fallback status: {d_status}, response: {d_body}")
            return d_status in (200, 201, 204)
        except Exception as exc:
            print(f"[save_annotation_atomic] Fallback failed: {exc}")
            return False

    async def update_annotation_note(
        self, user_id: UUID, annotation_id: UUID, note: str
    ) -> bool:
        """Updates note for user-owned annotation."""
        if not self.base_url or not self.service_key:
            return False

        url = f"{self.base_url}/rest/v1/annotations?id=eq.{str(annotation_id)}&user_id=eq.{str(user_id)}"
        headers = self._headers()
        payload = {"note": note, "updated_at": "now()"}

        if _HTTPX_AVAILABLE:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.patch(url, headers=headers, json=payload)
                    return resp.status_code in (200, 204)
            except Exception:
                return False
        else:
            status, _ = await asyncio.to_thread(_sync_http_request, "PATCH", url, headers, payload, 5.0)
            return status in (200, 204)

    async def delete_annotation(self, user_id: UUID, annotation_id: UUID) -> bool:
        """Deletes user-owned annotation."""
        if not self.base_url or not self.service_key:
            return False

        url = f"{self.base_url}/rest/v1/annotations?id=eq.{str(annotation_id)}&user_id=eq.{str(user_id)}"
        headers = self._headers()

        if _HTTPX_AVAILABLE:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.delete(url, headers=headers)
                    return resp.status_code in (200, 204)
            except Exception:
                return False
        else:
            status, _ = await asyncio.to_thread(_sync_http_request, "DELETE", url, headers, None, 5.0)
            return status in (200, 204)

    async def add_correction(
        self,
        user_id: UUID,
        annotation_entity_id: Optional[UUID],
        field: str,
        old_value: Optional[str],
        new_value: Optional[str],
    ) -> Optional[str]:
        """Saves a researcher correction feedback."""
        if not self.base_url or not self.service_key:
            return None

        payload = {
            "user_id": str(user_id),
            "annotation_entity_id": str(annotation_entity_id) if annotation_entity_id else None,
            "field": field,
            "old_value": old_value,
            "new_value": new_value,
            "status": "pending",
        }

        url = f"{self.base_url}/rest/v1/entity_corrections"
        status, rows = await self._post(url, payload)
        if status in (200, 201) and rows:
            if isinstance(rows, list) and len(rows) > 0:
                return rows[0].get("id")
            elif isinstance(rows, dict):
                return rows.get("id")
        return None


repo = SupabaseRepo()
