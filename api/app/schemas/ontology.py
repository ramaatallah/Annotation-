from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SparqlQueryRequest(BaseModel):
    """Payload to execute SPARQL against the knowledge graph."""
    query: str = Field(..., description="SPARQL 1.1 Query string (e.g., SELECT ?annotation ?entity WHERE { ... })")


class SparqlQueryResponse(BaseModel):
    query: str
    results_count: int
    variables: List[str]
    bindings: List[Dict[str, Any]]


class OntologyExportResponse(BaseModel):
    format: str = Field(..., description="Export format: turtle, xml, json-ld, nt")
    triples_count: int
    content: str
