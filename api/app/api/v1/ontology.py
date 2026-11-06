"""Ontology, RDF/OWL Representation, and SPARQL Endpoints."""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.ontology import (
    SparqlQueryRequest,
    SparqlQueryResponse,
    OntologyExportResponse,
)
from app.services.ontology_service import ontology_service

router = APIRouter(prefix="/ontology", tags=["Ontology & SPARQL"])
logger = logging.getLogger(__name__)


@router.get(
    "/export",
    response_model=OntologyExportResponse,
    status_code=status.HTTP_200_OK,
    summary="Export Knowledge Graph (RDF/OWL)",
    description="Exports all annotations, entities, and trilateral roots into Turtle, RDF/XML, or JSON-LD.",
)
def export_ontology(
    format: str = Query("turtle", description="Format: turtle, xml, json-ld, nt"),
    db: Session = Depends(get_db),
):
    try:
        result = ontology_service.export_knowledge_graph(db, format_type=format)
        return OntologyExportResponse(
            format=result["format"],
            triples_count=result["triples_count"],
            content=result["content"],
        )
    except Exception as e:
        logger.error(f"Error exporting RDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export ontology: {str(e)}",
        )


@router.get(
    "/download",
    summary="Direct File Download of Knowledge Graph",
    description="Downloads the Turtle (.ttl) knowledge graph file directly for Protégé or Apache Jena.",
)
def download_ontology(
    format: str = Query("turtle", description="Format: turtle or xml"),
    db: Session = Depends(get_db),
):
    result = ontology_service.export_knowledge_graph(db, format_type=format)
    media_type = "text/turtle" if result["format"] == "turtle" else "application/rdf+xml"
    filename = f"wahaj_knowledge_graph.{ 'ttl' if result['format'] == 'turtle' else 'rdf' }"

    return Response(
        content=result["content"],
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post(
    "/sparql",
    response_model=SparqlQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute SPARQL 1.1 Query",
    description="Runs a SPARQL query against the active RDF Knowledge Graph.",
)
def query_sparql(
    payload: SparqlQueryRequest,
    db: Session = Depends(get_db),
):
    try:
        result = ontology_service.execute_sparql_query(db, payload.query)
        return SparqlQueryResponse(
            query=result["query"],
            results_count=result["results_count"],
            variables=result["variables"],
            bindings=result["bindings"],
        )
    except Exception as e:
        logger.error(f"SPARQL execution error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SPARQL query failed: {str(e)}",
        )


@router.get(
    "/samples",
    summary="Get Sample SPARQL Queries",
    description="Returns pre-crafted SPARQL queries for university annotations, medical entities, and trilateral roots.",
)
def get_sample_sparql_queries() -> List[Dict[str, str]]:
    return [
        {
            "title": "Find all annotations related to Universities (جامعات)",
            "description": "Selects web annotations that contain University entities, including the web URL and highlighted text.",
            "sparql": (
                "PREFIX oa: <http://www.w3.org/ns/oa#>\n"
                "PREFIX schema: <http://schema.org/>\n"
                "PREFIX wahaj: <http://wahaj.annotation.org/ontology#>\n\n"
                "SELECT ?annotation ?universityName ?targetUrl ?highlightedText WHERE {\n"
                "  ?annotation a oa:Annotation ;\n"
                "              wahaj:identifiesEntity ?entity ;\n"
                "              oa:hasTarget ?target .\n"
                "  ?target oa:hasSource ?targetUrl ;\n"
                "          oa:hasSelector ?selector .\n"
                "  ?selector oa:exact ?highlightedText .\n"
                "  ?entity a schema:CollegeOrUniversity ;\n"
                "          rdfs:label ?universityName .\n"
                "}"
            ),
        },
        {
            "title": "Find Trilateral Roots of all Entities (الجذور الثلاثية)",
            "description": "Queries words within detected entities and their extracted 3-letter roots.",
            "sparql": (
                "PREFIX wahaj: <http://wahaj.annotation.org/ontology#>\n"
                "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n\n"
                "SELECT ?entityLabel ?word ?root WHERE {\n"
                "  ?entity rdfs:label ?entityLabel ;\n"
                "          wahaj:hasMorphologicalWord ?mWord .\n"
                "  ?mWord wahaj:wordSurface ?word ;\n"
                "         wahaj:trilateralRoot ?root ;\n"
                "         wahaj:isTrilateral true .\n"
                "}"
            ),
        },
        {
            "title": "List all Entities with high confidence (> 0.90)",
            "description": "Extracts entity names, categories, and confidence scores.",
            "sparql": (
                "PREFIX wahaj: <http://wahaj.annotation.org/ontology#>\n"
                "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n\n"
                "SELECT ?entityLabel ?category ?confidence WHERE {\n"
                "  ?entity rdfs:label ?entityLabel ;\n"
                "          wahaj:category ?category ;\n"
                "          wahaj:confidence ?confidence .\n"
                "  FILTER (?confidence >= 0.90)\n"
                "} ORDER BY DESC(?confidence)"
            ),
        },
    ]
