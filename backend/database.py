import os
import sqlite3
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.getenv("DATABASE_PATH", os.path.join(DATA_DIR, "hospital.db"))
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_file_metrics():
    """Return raw file and page metrics from SQLite."""
    if not os.path.exists(DB_PATH):
        return {
            "file_size_bytes": 0,
            "page_size": 4096,
            "page_count": 0,
            "freelist_count": 0
        }
    
    file_size = os.path.getsize(DB_PATH)
    wal_path = f"{DB_PATH}-wal"
    if os.path.exists(wal_path):
        file_size += os.path.getsize(wal_path)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA page_size")
    page_size = cursor.fetchone()[0]
    cursor.execute("PRAGMA page_count")
    page_count = cursor.fetchone()[0]
    cursor.execute("PRAGMA freelist_count")
    freelist_count = cursor.fetchone()[0]
    conn.close()
    
    return {
        "file_size_bytes": file_size,
        "page_size": page_size,
        "page_count": page_count,
        "freelist_count": freelist_count
    }
