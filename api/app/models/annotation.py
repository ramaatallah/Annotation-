import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Annotation(Base):
    """Represents a user-highlighted annotation and associated notes."""
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(64), nullable=True, index=True)
    author_name = Column(String(255), default="باحث", nullable=True)
    project_id = Column(Integer, nullable=True, index=True)
    url = Column(String(2048), nullable=False, index=True)
    page_title = Column(String(512), nullable=True)
    selected_text = Column(Text, nullable=False)
    note = Column(Text, nullable=True)
    color = Column(String(32), default="#FFE082")  # Warm amber highlight default
    visibility = Column(String(32), default="private")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )

    entities = relationship(
        "DetectedEntity",
        back_populates="annotation",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class DetectedEntity(Base):
    """Represents a named or conceptual entity recognized inside an annotation."""
    __tablename__ = "detected_entities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    annotation_id = Column(Integer, ForeignKey("annotations.id", ondelete="CASCADE"), nullable=True)
    text = Column(String(512), nullable=False, index=True)
    category = Column(String(128), nullable=False, index=True)
    label_ar = Column(String(256), nullable=True)
    confidence = Column(Float, default=1.0)
    source = Column(String(64), default="Hybrid")
    start_char = Column(Integer, default=0)
    end_char = Column(Integer, default=0)

    annotation = relationship("Annotation", back_populates="entities")
    roots = relationship(
        "WordRoot",
        back_populates="entity",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class WordRoot(Base):
    """Represents the morphological analysis and root of a word."""
    __tablename__ = "word_roots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey("detected_entities.id", ondelete="CASCADE"), nullable=False)
    word = Column(String(128), nullable=False)
    root = Column(String(64), nullable=True, index=True)
    lemma = Column(String(128), nullable=True)
    pos = Column(String(64), nullable=True)
    segmentation = Column(String(128), nullable=True)
    source = Column(String(64), default="camel_tools")
    status = Column(String(32), default="analyzed")
    is_trilateral = Column(Boolean, default=True)

    entity = relationship("DetectedEntity", back_populates="roots")
