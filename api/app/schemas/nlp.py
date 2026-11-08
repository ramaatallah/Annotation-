from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class WordRootSchema(BaseModel):
    """Schema representing morphological root analysis of a single word."""
    word: str = Field(..., description="Original Arabic word")
    root: Optional[str] = Field(None, description="Extracted trilateral or quadrilateral morphological root (e.g. درس, جمع, برمج)")
    lemma: Optional[str] = Field(None, description="Extracted lemma / lex (اللمة المعجمية)")
    pos: Optional[str] = Field(None, description="Part of speech or morphological category")
    segmentation: Optional[str] = Field(None, description="Morphological segmentation (e.g. ب+ ال+ تعاون)")
    source: str = Field("camel_tools", description="Extraction engine source")
    status: str = Field("analyzed", description="Status: 'analyzed' if root is verified, or 'unresolved'")
    is_trilateral: bool = Field(True, description="True if trilateral (3 letters), False if quadrilateral or unresolved")

    model_config = ConfigDict(from_attributes=True)


class EntitySchema(BaseModel):
    """Schema representing a detected academic or named entity."""
    text: str = Field(..., description="The entity text as found in the sentence")
    category: str = Field(..., description="Entity category: UNIVERSITY, LOCATION, PERSON, DISEASE, TECHNOLOGY, CONCEPT, etc.")
    label_ar: Optional[str] = Field(None, description="Detailed Arabic descriptor (e.g. شجرة حرجية, ظاهرة نباتية)")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    source: str = Field("Hybrid", description="Extraction source: BERT, Groq, Hybrid, or Lexicon")
    start_char: int = Field(0, description="Starting character index in original text")
    end_char: int = Field(0, description="Ending character index in original text")
    roots: List[WordRootSchema] = Field(default_factory=list, description="Roots of constituent content words")

    model_config = ConfigDict(from_attributes=True)


class AnalyzeRequest(BaseModel):
    """Request payload for analyzing highlighted text."""
    text: str = Field(..., min_length=1, description="Highlighted Arabic text to be analyzed")
    url: Optional[str] = Field(None, description="Source web page URL")
    page_title: Optional[str] = Field(None, description="Source web page title")


class AnalyzeResponse(BaseModel):
    """Complete NLP analysis response containing entities and morphological roots."""
    original_text: str
    entities: List[EntitySchema]
    all_roots: List[WordRootSchema] = Field(
        default_factory=list,
        description="Morphological roots for all major words in the input text",
    )
    processing_time_ms: float
    pipeline_status: dict = Field(
        default_factory=dict,
        description="Status indicators for BERT, LLM, and CAMeL Morphological engines",
    )
