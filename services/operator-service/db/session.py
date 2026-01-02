"""Database session factory and connection management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base
from ..config import OperatorConfig


def create_session_factory(config: OperatorConfig) -> sessionmaker:
    """Create a SQLAlchemy session factory.

    Args:
        config: Operator service configuration

    Returns:
        Session factory
    """
    engine = create_engine(
        config.database.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Global session factory (will be initialized in main.py)
SessionLocal: sessionmaker | None = None


def init_db(config: OperatorConfig) -> None:
    """Initialize database connection and session factory.

    Args:
        config: Operator service configuration
    """
    global SessionLocal
    SessionLocal = create_session_factory(config)


def get_db() -> Session:
    """Get database session dependency for FastAPI.

    Yields:
        Database session

    Raises:
        RuntimeError: If database is not initialized
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
