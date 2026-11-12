"""Entity Knowledge Cache (ذاكرة الكيانات المُكتسبة).

Provides persistent local caching and instant sub-millisecond retrieval of
previously verified and auto-discovered entities, preventing redundant LLM calls
and guaranteeing 100% classification consistency across repeated terms.
"""

import os
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class EntityKnowledgeCache:
    """Manages fast persistent storage and retrieval of learned academic entities."""

    def __init__(self):
        # Resolve SQLite database path
        db_url = settings.DATABASE_URL
        if db_url.startswith("sqlite:///./"):
            api_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            filename = db_url.replace("sqlite:///./", "")
            self.db_path = os.path.join(api_dir, filename).replace("\\", "/")
        elif db_url.startswith("sqlite:///"):
            self.db_path = db_url.replace("sqlite:///", "")
        else:
            self.db_path = "annotations.db"

        self._in_memory_cache: Dict[str, Dict[str, Any]] = {}
        self._init_cache_table()
        self._load_cache_to_memory()
        self._seed_default_knowledge()

    def _get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_cache_table(self):
        """Initializes the entity_knowledge_cache table if not present."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS entity_knowledge_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        text TEXT UNIQUE NOT NULL,
                        category TEXT NOT NULL,
                        label_ar TEXT,
                        confidence REAL DEFAULT 0.98,
                        hit_count INTEGER DEFAULT 1,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_ekc_text ON entity_knowledge_cache(text)")
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not initialize entity_knowledge_cache table: {e}")

    def _load_cache_to_memory(self):
        """Pre-loads known entities into an in-memory dictionary for ultra-fast matching."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT text, category, label_ar, confidence FROM entity_knowledge_cache")
                rows = cursor.fetchall()
                for text, category, label_ar, confidence in rows:
                    self._in_memory_cache[text.strip()] = {
                        "text": text.strip(),
                        "category": category,
                        "label_ar": label_ar,
                        "confidence": float(confidence or 0.98),
                    }
            logger.info(f"Loaded {len(self._in_memory_cache)} cached entities into memory.")
        except Exception as e:
            logger.warning(f"Could not load entity cache into memory: {e}")

    def _seed_default_knowledge(self):
        """Seeds high-precision verified academic entities into the cache."""
        seeds = [
            ("القشرة الأرضية", "GEOLOGY", "طبقة جيولوجية صخرية"),
            ("قشرة الكواكب", "GEOLOGY", "بنية كوكبية صخرية"),
            ("غرف الصهارة", "GEOLOGY", "تراكيب جيولوجية باطنية"),
            ("البراكين", "GEOLOGY", "تضاريس ومعالم بركانية"),
            ("الحمم البركانية", "GEOLOGY", "صخور ومواد بركانية منصهرة"),
            ("الرماد البركاني", "GEOLOGY", "فتات ومقذوفات بركانية"),
            ("التلال المخروطية", "GEOLOGY", "تضاريس ومعالم جيولوجية"),
            ("الجبال البركانية", "GEOLOGY", "معالم وتضاريس جبلية بركانية"),
            ("الأرض", "ASTRONOMY", "كوكب أرضي"),
            ("أمريكا الشمالية", "LOCATION", "قارة وموقع جغرافي"),
            ("متنزه يلوستون الوطني", "LOCATION", "محمية وموقع جغرافي"),
            ("الاحتباس الحراري", "PHENOMENON", "ظاهرة مناخية وبيئية"),
            ("ثنائي أكسيد الكربون", "CHEMICAL", "مركب كيميائي / غاز دفيء"),
            ("الأمم المتحدة", "ORGANIZATION", "منظمة دولية"),
        ]
        to_save = []
        for text, cat, label in seeds:
            if text not in self._in_memory_cache:
                to_save.append({
                    "text": text,
                    "category": cat,
                    "label_ar": label,
                    "confidence": 0.99,
                    "source": "VerifiedKnowledge",
                })
        if to_save:
            self.remember_entities(to_save)

    def lookup_entities(self, text: str) -> List[Dict[str, Any]]:
        """Scans the text against the in-memory entity knowledge base."""
        matched: List[Dict[str, Any]] = []
        if not text:
            return matched

        # Sort cache keys by length descending to match longest phrases first
        sorted_keys = sorted(self._in_memory_cache.keys(), key=len, reverse=True)

        for known_text in sorted_keys:
            idx = 0
            while True:
                found_at = text.find(known_text, idx)
                if found_at == -1:
                    break

                # Boundary check: ensure match is not an internal substring of another word
                is_start_bound = (found_at == 0 or text[found_at - 1] in " \t\n،,.:؟!؛\"'()[]{}«»")
                end_pos = found_at + len(known_text)
                is_end_bound = (end_pos == len(text) or text[end_pos] in " \t\n،,.:؟!؛\"'()[]{}«»")

                if is_start_bound and is_end_bound:
                    cached_info = self._in_memory_cache[known_text]
                    matched.append({
                        "text": known_text,
                        "category": cached_info["category"],
                        "label_ar": cached_info.get("label_ar"),
                        "confidence": cached_info.get("confidence", 0.98),
                        "source": "KnowledgeCache",
                        "start_char": found_at,
                        "end_char": end_pos,
                    })
                idx = found_at + len(known_text)

        return matched

    def remember_entities(self, entities: List[Dict[str, Any]]):
        """Saves newly discovered, high-confidence entities to SQLite and updates in-memory cache."""
        if not entities:
            return

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for ent in entities:
                    text_val = ent.get("text", "").strip()
                    cat = ent.get("category", "").strip().upper()
                    label = ent.get("label_ar")
                    conf = float(ent.get("confidence", 0.90))

                    # Filter out short or unclassified tokens
                    if len(text_val) < 3 or cat in ("MISC", "OTHER", ""):
                        continue

                    self._in_memory_cache[text_val] = {
                        "text": text_val,
                        "category": cat,
                        "label_ar": label,
                        "confidence": conf,
                    }

                    cursor.execute("""
                        INSERT INTO entity_knowledge_cache (text, category, label_ar, confidence, hit_count, updated_at)
                        VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                        ON CONFLICT(text) DO UPDATE SET
                            hit_count = hit_count + 1,
                            category = excluded.category,
                            label_ar = COALESCE(excluded.label_ar, entity_knowledge_cache.label_ar),
                            confidence = MAX(entity_knowledge_cache.confidence, excluded.confidence),
                            updated_at = CURRENT_TIMESTAMP
                    """, (text_val, cat, label, conf))
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not persist entities to entity_knowledge_cache: {e}")


entity_cache = EntityKnowledgeCache()
