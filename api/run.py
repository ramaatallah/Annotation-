"""Quick launcher script for the Wahaj Backend Server."""

import uvicorn

if __name__ == "__main__":
    print("=" * 65)
    print("  Starting Wahaj / Hashiya Arabic Annotation & NLP Server")
    print("  Documentation: http://localhost:8000/docs")
    print("  SPARQL / Knowledge Graph: http://localhost:8000/v1/ontology/samples")
    print("=" * 65)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
