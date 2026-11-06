import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.nlp import EntitySchema


class AnnotationBase(BaseModel):
    url: str = Field(..., description="Target webpage URL")
    page_title: Optional[str] = Field(None, description="Webpage title")
    selected_text: str = Field(..., min_length=1, description="Highlighted text")
    note: Optional[str] = Field(None, description="User note attached to highlight")
    color: Optional[str] = Field("#FFE082", description="Highlight hex color code")


class AnnotationCreate(AnnotationBase):
    """Payload to create an annotation. Can optionally trigger immediate NLP analysis."""
    auto_analyze: bool = Field(True, description="Automatically trigger Hybrid NER & Root extraction upon saving")


class AnnotationUpdate(BaseModel):
    """Payload to update an existing annotation."""
    note: Optional[str] = Field(None, description="Updated user note")
    color: Optional[str] = Field(None, description="Updated highlight color")
    selected_text: Optional[str] = Field(None, description="Updated selected text")


class AnnotationResponse(AnnotationBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    entities: List[EntitySchema] = []

    model_config = ConfigDict(from_attributes=True)


class AnnotationSearchResult(BaseModel):
    total_count: int
    query: Optional[str] = None
    category_filter: Optional[str] = None
    root_filter: Optional[str] = None
    results: List[AnnotationResponse]
