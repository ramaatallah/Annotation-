"""Integration tests for RDF/OWL Knowledge Graph and SPARQL query engine."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ontology_export_and_sparql():
    # 1. Seed with an annotation
    seed_payload = {
        "url": "https://ar.wikipedia.org/wiki/Nablus",
        "page_title": "نابلس - ويكيبيديا",
        "selected_text": "جامعة النجاح الوطنية تقع في مدينة نابلس",
        "note": "توثيق أنطولوجي للتجربة",
        "auto_analyze": True,
    }
    create_res = client.post("/v1/annotations", json=seed_payload)
    assert create_res.status_code == 201
    ann_id = create_res.json()["id"]

    # 2. Export Turtle (.ttl)
    export_res = client.get("/v1/ontology/export", params={"format": "turtle"})
    assert export_res.status_code == 200
    export_data = export_res.json()
    assert export_data["format"] == "turtle"
    assert export_data["triples_count"] > 0
    turtle_content = export_data["content"]
    assert "@prefix oa:" in turtle_content or "http://www.w3.org/ns/oa#" in turtle_content
    assert "جامعة النجاح" in turtle_content or "نابلس" in turtle_content

    # 3. Query with SPARQL
    sparql_query = """
    PREFIX oa: <http://www.w3.org/ns/oa#>
    PREFIX wahaj: <http://wahaj.annotation.org/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?annotation ?entityLabel WHERE {
      ?annotation a oa:Annotation ;
                  wahaj:identifiesEntity ?entity .
      ?entity rdfs:label ?entityLabel .
    }
    """
    sparql_res = client.post("/v1/ontology/sparql", json={"query": sparql_query})
    assert sparql_res.status_code == 200
    sparql_data = sparql_res.json()
    assert sparql_data["results_count"] > 0
    assert "entityLabel" in sparql_data["variables"]

    # 4. Clean up seeded annotation
    client.delete(f"/v1/annotations/{ann_id}")
