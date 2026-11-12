import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Wahaj / Hashiya Arabic Annotation Engine"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "High-performance Academic Arabic NLP Backend for Web Annotation, "
        "Hybrid Entity Recognition, Trilateral Morphological Root Extraction, "
        "and RDF/OWL Knowledge Graph Integration."
    )
    API_V1_STR: str = "/v1"

    # Database Settings
    DATABASE_URL: str = "sqlite:///./annotations.db"

    # Supabase Cloud Sync Settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://tnyvdudzteejdztqmpqa.supabase.co")
    SUPABASE_KEY: str = os.getenv(
        "SUPABASE_KEY",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRueXZkdWR6dGVlamR6dHFtcHFhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTE2NTEwMzMsImV4cCI6MjEwNzIyNzAzM30.ryETzFg4B_8FMGUNkenAjdA0UAW7SZMO-XZ6Ub7Ri7E"
    )
    ENABLE_SUPABASE_SYNC: bool = True

    # LLM Settings (Groq)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_TIMEOUT_SECONDS: float = 12.0

    # Local BERT NER Settings
    LOCAL_NER_MODEL: str = os.getenv("LOCAL_NER_MODEL", "hatmimoha/arabic-ner")
    ENABLE_LOCAL_NER: bool = True

    # CAMeL Tools Settings
    CAMEL_DATA_DIR: str = os.getenv("CAMEL_DATA_DIR", "")
    ENABLE_CAMEL_TOOLS: bool = True

    # CORS Settings (permits Chrome Extension and frontend web clients)
    CORS_ORIGINS: List[str] = [
        "*",
        "chrome-extension://*",
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
