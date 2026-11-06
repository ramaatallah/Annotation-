from fastapi import APIRouter
from app.api.v1.analyze import router as analyze_router
from app.api.v1.annotations import router as annotations_router
from app.api.v1.search import router as search_router
from app.api.v1.ontology import router as ontology_router

api_v1_router = APIRouter()
api_v1_router.include_router(analyze_router)
api_v1_router.include_router(annotations_router)
api_v1_router.include_router(search_router)
api_v1_router.include_router(ontology_router)
