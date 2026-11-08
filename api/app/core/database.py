import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Engine configuration (handling SQLite multi-threading and absolute path resolution)
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///./"):
    api_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    filename = db_url.replace("sqlite:///./", "")
    abs_path = os.path.join(api_dir, filename).replace("\\", "/")
    db_url = f"sqlite:///{abs_path}"

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency generator that provides a SQLAlchemy session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Creates database tables and applies lightweight schema updates."""
    import app.models.annotation  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Automatic non-destructive schema migration for SQLite
    if settings.DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                # Migrate word_roots
                res = conn.execute(text("PRAGMA table_info(word_roots)"))
                existing_cols = [r[1] for r in res.fetchall()]
                new_cols = [
                    ("lemma", "VARCHAR(128)"),
                    ("segmentation", "VARCHAR(128)"),
                    ("source", "VARCHAR(64) DEFAULT 'camel_tools'"),
                    ("status", "VARCHAR(32) DEFAULT 'analyzed'"),
                ]
                for col_name, col_type in new_cols:
                    if col_name not in existing_cols:
                        conn.execute(text(f"ALTER TABLE word_roots ADD COLUMN {col_name} {col_type}"))

                # Migrate annotations
                res_ann = conn.execute(text("PRAGMA table_info(annotations)"))
                existing_ann_cols = [r[1] for r in res_ann.fetchall()]
                new_ann_cols = [
                    ("user_id", "VARCHAR(64)"),
                    ("author_name", "VARCHAR(255) DEFAULT 'باحث'"),
                    ("project_id", "INTEGER"),
                    ("visibility", "VARCHAR(32) DEFAULT 'private'"),
                ]
                for col_name, col_type in new_ann_cols:
                    if col_name not in existing_ann_cols:
                        conn.execute(text(f"ALTER TABLE annotations ADD COLUMN {col_name} {col_type}"))

                conn.commit()
        except Exception:
            pass


# Auto-create tables on load
init_db()
