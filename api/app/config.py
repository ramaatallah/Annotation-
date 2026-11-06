# -*- coding: utf-8 -*-
"""
Configuration settings for the Annotation Backend API.
Loads environment variables safely with defaults and fallback support,
without requiring external pydantic-settings package.
"""

import os
from typing import List


def _load_env_file(filepath: str):
    """Safely loads key-value pairs from a .env file into os.environ if not already present."""
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


# Load nearest .env files (api/.env and root .env)
_curr = os.path.dirname(os.path.abspath(__file__))
_load_env_file(os.path.join(_curr, "..", ".env"))
_load_env_file(os.path.join(_curr, "..", "..", ".env"))
_load_env_file(os.path.join(os.getcwd(), "api", ".env"))
_load_env_file(os.path.join(os.getcwd(), ".env"))


class Settings:
    """Application settings backed by os.environ."""

    @property
    def supabase_url(self) -> str:
        return os.environ.get("SUPABASE_URL", "")

    @property
    def supabase_service_role_key(self) -> str:
        return os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    @property
    def supabase_jwt_secret(self) -> str:
        return os.environ.get("SUPABASE_JWT_SECRET", "")

    @property
    def llm_enabled(self) -> bool:
        val = os.environ.get("LLM_ENABLED", "true").lower()
        return val in ("true", "1", "yes", "t")

    @property
    def llm_api_key(self) -> str:
        return (
            os.environ.get("LLM_API_KEY")
            or os.environ.get("ANNOTATION_AI_API_KEY", "")
        )

    @property
    def llm_base_url(self) -> str:
        return (
            os.environ.get("LLM_BASE_URL")
            or os.environ.get("ANNOTATION_AI_BASE_URL", "https://api.groq.com/openai/v1")
        )

    @property
    def llm_models_raw(self) -> str:
        return (
            os.environ.get("LLM_MODELS")
            or os.environ.get("ANNOTATION_AI_MODEL", "llama-3.3-70b-versatile,qwen/qwen3.8-27b,allam-2-7b")
        )

    @property
    def llm_models(self) -> List[str]:
        raw = self.llm_models_raw
        if not raw:
            return ["llama-3.3-70b-versatile", "qwen/qwen3.8-27b", "allam-2-7b"]
        return [m.strip() for m in raw.split(",") if m.strip()]

    @property
    def llm_total_timeout_s(self) -> float:
        try:
            return float(os.environ.get("LLM_TOTAL_TIMEOUT_S", "10.0"))
        except ValueError:
            return 10.0

    @property
    def allowed_origins(self) -> str:
        return os.environ.get(
            "ALLOWED_ORIGINS",
            "chrome-extension://*,http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
        )

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def max_text_chars(self) -> int:
        try:
            return int(os.environ.get("MAX_TEXT_CHARS", "5000"))
        except ValueError:
            return 5000

    @property
    def rate_limit_per_min(self) -> int:
        try:
            return int(os.environ.get("RATE_LIMIT_PER_MIN", "30"))
        except ValueError:
            return 30

    @property
    def prompt_version(self) -> str:
        return os.environ.get("PROMPT_VERSION", "v3")


settings = Settings()
