from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

DB_PATH = Path("data/scheduled_deletions.db")
DB_PATH.parent.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///./{DB_PATH}"
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Erstellt alle Tabellen in der Datenbank"""
    Base.metadata.create_all(bind=engine)