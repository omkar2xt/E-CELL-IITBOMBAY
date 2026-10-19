# StorePulse AI — Database Connection & Engine
# Developer: Omkar Gurav
# Environment-driven PostgreSQL (Neon) & SQLite configuration with connection pooling

import os
import sqlite3
from typing import Dict, Any, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, NullPool

def normalize_database_url(url: str) -> str:
    """Normalize SQLAlchemy dialect URLs (e.g. postgres:// -> postgresql://)."""
    if not url:
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

# Base directory for local SQLite database fallback
DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "storepulse.db")

# Read environment variables
RAW_DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
RAW_DIRECT_URL = os.getenv("DIRECT_URL", "").strip()

# Determine active URLs
DATABASE_URL = normalize_database_url(RAW_DATABASE_URL) if RAW_DATABASE_URL else f"sqlite:///{DB_PATH}"
DIRECT_URL = normalize_database_url(RAW_DIRECT_URL) if RAW_DIRECT_URL else DATABASE_URL

IS_POSTGRES = DATABASE_URL.startswith("postgresql")
IS_SERVERLESS = os.getenv("VERCEL") == "1" or os.getenv("SERVERLESS", "0") == "1"

def create_app_engine(db_url: str, is_direct: bool = False) -> Engine:
    """
    Create SQLAlchemy engine with appropriate pooling strategy.
    - PostgreSQL / Neon: Serverless connection pooling with QueuePool, pre-ping, and recycling.
    - SQLite: Multi-threaded connection settings with WAL pragma hooks.
    """
    if db_url.startswith("postgresql"):
        # Serverless PostgreSQL / Neon configuration
        # For serverless functions or poolers, use sensible limits to prevent connection exhaustion
        pool_size = int(os.getenv("DB_POOL_SIZE", "5" if not IS_SERVERLESS else "2"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10" if not IS_SERVERLESS else "3"))
        pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "300"))  # Recycle every 5 mins to prevent stale sockets

        # If direct migration connection or single-operation mode requested
        if is_direct and os.getenv("DB_USE_NULLPOOL", "0") == "1":
            return create_engine(
                db_url,
                poolclass=NullPool,
                echo=os.getenv("DB_ECHO", "0") == "1"
            )

        return create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,  # Check connection liveness before checkout
            echo=os.getenv("DB_ECHO", "0") == "1"
        )
    else:
        # SQLite fallback configuration
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False, "timeout": 30.0},
            echo=os.getenv("DB_ECHO", "0") == "1"
        )

# Primary application engine (uses pooled connection string for Neon)
engine = create_app_engine(DATABASE_URL)

# Enable WAL mode and foreign keys for SQLite connections
@event.listens_for(Engine, "connect")
def configure_sqlite_connection(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        cursor.close()

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_migration_engine() -> Engine:
    """
    Return engine for schema migrations (Alembic / DDL).
    Uses DIRECT_URL (unpooled Neon connection) if provided to bypass transaction poolers.
    """
    return create_app_engine(DIRECT_URL, is_direct=True)

def get_db():
    """FastAPI Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    """Context manager for background threads, workers, and migration scripts."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
