"""Main FastAPI Application Entrypoint.

Wahaj / Hashiya Arabic Academic Web Annotation & NLP Engine.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.database import init_db
from app.api.v1 import api_v1_router

# Configure clean logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("wahaj.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database initialization and cleanup."""
    logger.info("Initializing database schema...")
    init_db()
    logger.info("Database initialized successfully.")
    yield
    logger.info("Shutting down Wahaj Backend Engine.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS configuration supporting Chrome Extension and modern frontend apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API V1 routes
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
def root():
    """System information and operational status."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs": "/docs",
        "endpoints": {
            "analyze": f"{settings.API_V1_STR}/analyze",
            "annotations": f"{settings.API_V1_STR}/annotations",
            "search": f"{settings.API_V1_STR}/search",
            "ontology_export": f"{settings.API_V1_STR}/ontology/export",
            "ontology_sparql": f"{settings.API_V1_STR}/ontology/sparql",
        },
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for container and deployment monitors."""
    return {"status": "healthy"}
