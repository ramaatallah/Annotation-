"""Ontology & Knowledge Graph Service.

Integrates W3C Open Annotation Ontology (OA), Schema.org, and custom Wahaj
ontology to represent annotations, entities, and trilateral roots as RDF/OWL triples.
Supports export to Turtle/RDF-XML/JSON-LD and execution of SPARQL 1.1 queries.
"""

import logging
from typing import Dict, Any, List
from rdflib import Graph, URIRef, Literal, Namespace, RDF, RDFS, OWL, XSD
from sqlalchemy.orm import Session
from app.models.annotation import Annotation, DetectedEntity, WordRoot

logger = logging.getLogger(__name__)

# Standard and Custom Namespaces
OA = Namespace("http://www.w3.org/ns/oa#")
SCHEMA = Namespace("http://schema.org/")
WAHAJ = Namespace("http://wahaj.annotation.org/ontology#")
DC = Namespace("http://purl.org/dc/elements/1.1/")


class OntologyService:
    """Manages RDF Knowledge Graph generation, serialization, and SPARQL queries."""

    def build_graph_for_annotations(self, annotations: List[Annotation]) -> Graph:
        """Constructs an in-memory RDF Graph representing the provided annotations."""
        g = Graph()

        # Bind common prefixes for elegant Turtle output
        g.bind("oa", OA)
        g.bind("schema", SCHEMA)
        g.bind("wahaj", WAHAJ)
        g.bind("rdfs", RDFS)
        g.bind("owl", OWL)
        g.bind("xsd", XSD)
        g.bind("dc", DC)

        for ann in annotations:
            ann_uri = URIRef(f"http://wahaj.annotation.org/annotation/{ann.id}")
            g.add((ann_uri, RDF.type, OA.Annotation))
            g.add((ann_uri, SCHEMA.dateCreated, Literal(ann.created_at.isoformat(), datatype=XSD.dateTime)))

            # Web page target
            target_uri = URIRef(f"http://wahaj.annotation.org/target/{ann.id}")
            g.add((target_uri, RDF.type, OA.SpecificResource))
            g.add((target_uri, OA.hasSource, URIRef(ann.url)))
            g.add((ann_uri, OA.hasTarget, target_uri))

            # Selected text selector
            selector_uri = URIRef(f"http://wahaj.annotation.org/selector/{ann.id}")
            g.add((selector_uri, RDF.type, OA.TextQuoteSelector))
            g.add((selector_uri, OA.exact, Literal(ann.selected_text, lang="ar")))
            g.add((target_uri, OA.hasSelector, selector_uri))

            # User Note body
            if ann.note:
                body_uri = URIRef(f"http://wahaj.annotation.org/body/{ann.id}")
                g.add((body_uri, RDF.type, OA.TextualBody))
                g.add((body_uri, RDF.value, Literal(ann.note, lang="ar")))
                g.add((body_uri, DC["format"], Literal("text/plain")))
                g.add((ann_uri, OA.hasBody, body_uri))

            # Detected Entities
            for ent in ann.entities:
                ent_uri = URIRef(f"http://wahaj.annotation.org/entity/{ent.id}")
                g.add((ann_uri, WAHAJ.identifiesEntity, ent_uri))
                g.add((ent_uri, RDF.type, WAHAJ.NamedEntity))
                g.add((ent_uri, RDFS.label, Literal(ent.text, lang="ar")))
                g.add((ent_uri, WAHAJ.confidence, Literal(ent.confidence, datatype=XSD.float)))
                g.add((ent_uri, WAHAJ.category, Literal(ent.category)))
                if hasattr(ent, "label_ar") and ent.label_ar:
                    g.add((ent_uri, RDFS.comment, Literal(ent.label_ar, lang="ar")))

                # Map categories to schema.org or ontology classes
                cat = ent.category.upper()
                if cat == "UNIVERSITY":
                    g.add((ent_uri, RDF.type, SCHEMA.CollegeOrUniversity))
                elif cat == "LOCATION":
                    g.add((ent_uri, RDF.type, SCHEMA.Place))
                elif cat == "GEOLOGY":
                    g.add((ent_uri, RDF.type, SCHEMA.Landform))
                elif cat == "PERSON":
                    g.add((ent_uri, RDF.type, SCHEMA.Person))
                elif cat == "ORGANIZATION":
                    g.add((ent_uri, RDF.type, SCHEMA.Organization))
                elif cat == "DISEASE":
                    g.add((ent_uri, RDF.type, SCHEMA.MedicalCondition))
                elif cat == "TECHNOLOGY":
                    g.add((ent_uri, RDF.type, WAHAJ.Technology))
                else:
                    g.add((ent_uri, RDF.type, WAHAJ.AcademicConcept))

                # Morphological Trilateral Roots
                for root_obj in ent.roots:
                    root_uri = URIRef(f"http://wahaj.annotation.org/root/{root_obj.id}")
                    g.add((ent_uri, WAHAJ.hasMorphologicalWord, root_uri))
                    g.add((root_uri, RDF.type, WAHAJ.WordMorphology))
                    g.add((root_uri, WAHAJ.wordSurface, Literal(root_obj.word, lang="ar")))
                    g.add((root_uri, WAHAJ.trilateralRoot, Literal(root_obj.root, lang="ar")))
                    g.add((root_uri, WAHAJ.isTrilateral, Literal(root_obj.is_trilateral, datatype=XSD.boolean)))

        return g

    def export_knowledge_graph(self, db: Session, format_type: str = "turtle") -> Dict[str, Any]:
        """Serializes all stored annotations into RDF Turtle, XML, JSON-LD, or NT."""
        annotations = db.query(Annotation).all()
        graph = self.build_graph_for_annotations(annotations)

        # rdflib standard format strings
        rdf_format_map = {
            "turtle": "turtle",
            "ttl": "turtle",
            "xml": "xml",
            "rdf": "xml",
            "json-ld": "json-ld",
            "nt": "nt",
        }
        fmt = rdf_format_map.get(format_type.lower(), "turtle")
        serialized = graph.serialize(format=fmt)

        return {
            "format": fmt,
            "triples_count": len(graph),
            "content": serialized if isinstance(serialized, str) else serialized.decode("utf-8"),
        }

    def execute_sparql_query(self, db: Session, sparql_str: str) -> Dict[str, Any]:
        """Executes an arbitrary SPARQL 1.1 query over the knowledge graph."""
        annotations = db.query(Annotation).all()
        graph = self.build_graph_for_annotations(annotations)

        qres = graph.query(sparql_str)
        variables = [str(var) for var in qres.vars] if qres.vars else []
        bindings = []

        for row in qres:
            row_dict = {}
            for var in variables:
                val = row[var]
                row_dict[var] = str(val) if val is not None else None
            bindings.append(row_dict)

        return {
            "query": sparql_str,
            "results_count": len(bindings),
            "variables": variables,
            "bindings": bindings,
        }


ontology_service = OntologyService()
