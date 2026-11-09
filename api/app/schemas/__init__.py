from app.schemas.nlp import (
    WordRootSchema,
    EntitySchema,
    AnalyzeRequest,
    AnalyzeResponse,
)
from app.schemas.annotation import (
    AnnotationBase,
    AnnotationCreate,
    AnnotationUpdate,
    AnnotationResponse,
    AnnotationSearchResult,
)
from app.schemas.ontology import (
    SparqlQueryRequest,
    SparqlQueryResponse,
    OntologyExportResponse,
)

__all__ = [
    "WordRootSchema",
    "EntitySchema",
    "AnalyzeRequest",
    "AnalyzeResponse",
    "AnnotationBase",
    "AnnotationCreate",
    "AnnotationUpdate",
    "AnnotationResponse",
    "AnnotationSearchResult",
    "SparqlQueryRequest",
    "SparqlQueryResponse",
    "OntologyExportResponse",
]
