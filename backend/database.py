import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.getenv("DATABASE_PATH", os.path.join(DATA_DIR, "hospital.db"))
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine_options = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_options)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if engine.dialect.name != "sqlite":
        return
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
    """Return physical storage metrics supported by the configured database."""
    if engine.dialect.name == "postgresql":
        with engine.connect() as connection:
            size = connection.exec_driver_sql(
                "SELECT pg_database_size(current_database())"
            ).scalar_one()
        return {
            "file_size_bytes": size,
            "page_size": None,
            "page_count": None,
            "freelist_count": None,
        }
    if engine.dialect.name == "mysql":
        with engine.connect() as connection:
            size = connection.exec_driver_sql(
                "SELECT COALESCE(SUM(data_length + index_length), 0) "
                "FROM information_schema.tables WHERE table_schema = DATABASE()"
            ).scalar_one()
        return {
            "file_size_bytes": int(size),
            "page_size": None,
            "page_count": None,
            "freelist_count": None,
        }

    database_path = engine.url.database
    if not database_path or database_path == ":memory:":
        return {
            "file_size_bytes": 0,
            "page_size": 4096,
            "page_count": 0,
            "freelist_count": 0
        }
    
    if not os.path.exists(database_path):
        return {
            "file_size_bytes": 0,
            "page_size": 4096,
            "page_count": 0,
            "freelist_count": 0,
        }
    file_size = os.path.getsize(database_path)
    wal_path = f"{database_path}-wal"
    if os.path.exists(wal_path):
        file_size += os.path.getsize(wal_path)
        
    conn = engine.raw_connection()
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
