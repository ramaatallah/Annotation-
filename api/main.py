from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# يشتغل سواء شغّلتوا من جذر المشروع (uvicorn api.main:app)
# أو من جوا مجلد api (uvicorn main:app)
try:
    from .ner import analyze_text, get_ner
except ImportError:
    from ner import analyze_text, get_ner


@asynccontextmanager
async def lifespan(app: FastAPI):
    # تحميل الموديل أول ما يشتغل السيرفر، مش عند أول طلب
    get_ner()
    yield


app = FastAPI(title="Annotation NER API", lifespan=lifespan)
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
    return {"status": "ok", "message": "Annotation NER API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    # مهم: ما نعمل strip للنص اللي بنحلله، لأن start/end لازم
    # يطابقوا النص الأصلي اللي بعتته الإضافة بالضبط
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="النص فارغ")

    try:
        entities = analyze_text(request.text)
        return {"entities": entities}
    except Exception as error:
        print(f"Analysis error: {error}")
        raise HTTPException(status_code=500, detail="فشل تحليل النص") from error
