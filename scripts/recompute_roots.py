# -*- coding: utf-8 -*-
"""
Database Migration & Recomputation Script.
Re-evaluates all existing entities in kb_entities using the unified RootResolver,
and populates the entity_words table with authenticated word-level roots and statuses.
"""

import os
import sys
import asyncio
import httpx

# Add project root and api to path
_curr = os.path.dirname(os.path.abspath(__file__))
_api_dir = os.path.join(os.path.dirname(_curr), "api")
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from app.config import settings
from app.nlp.roots.resolver import root_resolver


async def recompute_all_roots():
    print("=== Starting Root Recomputation for Existing Entities ===")
    supabase_url = settings.supabase_url.rstrip("/")
    service_key = settings.supabase_service_role_key

    if not supabase_url or not service_key:
        print("[Error] SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not configured in .env")
        return

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Fetch entities
        resp = await client.get(f"{supabase_url}/rest/v1/kb_entities?select=id,entity_text,entity_type", headers=headers)
        if resp.status_code != 200:
            print(f"[Error] Failed to fetch kb_entities: {resp.status_code} {resp.text}")
            return

        entities = resp.json()
        print(f"[Info] Found {len(entities)} entities in knowledge base.")

        updated_count = 0
        for ent in entities:
            ent_id = ent["id"]
            text = ent.get("entity_text", "")
            etype = ent.get("entity_type", "")

            word_roots = root_resolver.resolve_entity_words(text, entity_type=etype)

            # Insert into entity_words
            for idx, wr in enumerate(word_roots):
                row = {
                    "entity_id": ent_id,
                    "position": idx,
                    "word": wr.word,
                    "root": wr.root,
                    "root_len": wr.root_len,
                    "root_status": wr.status,
                    "root_engine": wr.engine,
                    "engine_version": wr.engine_version,
                    "candidates": wr.candidates,
                    "needs_review": wr.needs_review,
                }
                # Upsert row
                upsert_url = f"{supabase_url}/rest/v1/entity_words"
                h_upsert = dict(headers)
                h_upsert["Prefer"] = "resolution=merge-duplicates"
                await client.post(upsert_url, headers=h_upsert, json=row)

            updated_count += 1
            if updated_count % 50 == 0:
                print(f"[Progress] Processed {updated_count}/{len(entities)} entities.")

        print(f"=== Recomputation Finished Successfully! Updated {updated_count} entities. ===")


if __name__ == "__main__":
    asyncio.run(recompute_all_roots())
