from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ner import analyze_text

app = FastAPI(title="Annotation NER API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)


@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "Annotation NER API is running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    text = request.text.strip()

    if not text:
        raise HTTPException(
            status_code=422,
            detail="النص فارغ",
        )

    try:
        entities = analyze_text(text)
        return {"entities": entities}
    except Exception as error:
        print(f"Analysis error: {error}")
        raise HTTPException(
            status_code=500,
            detail="فشل تحليل النص",
        ) from error
