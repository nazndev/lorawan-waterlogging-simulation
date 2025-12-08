"""
Database connection and session management using SQLAlchemy.
Handles PostgreSQL connection and provides session factory.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from core.config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

# Create SQLAlchemy Base for declarative models
Base = declarative_base()

# Create engine with connection pooling
try:
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        echo=False,  # Set to True for SQL query logging
        connect_args={"connect_timeout": 10}
    )
    logger.info(f"Database engine created for: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency function to get database session.
    Use with context manager: with get_db() as db: ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    Should be called on application startup.
    Only logs if tables are actually created (not if they already exist).
    """
    try:
        # Check which tables already exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        
        # Create all tables (idempotent - only creates missing tables)
        Base.metadata.create_all(bind=engine)
        
        # Check which tables exist now
        inspector = inspect(engine)
        current_tables = set(inspector.get_table_names())
        
        # Only log if new tables were created
        new_tables = current_tables - existing_tables
        if new_tables:
            logger.info(f"Database tables created successfully: {', '.join(new_tables)}")
        # Otherwise, tables already exist, no need to log
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def check_db_connection():
    """
    Check if database connection is available.
    Returns True if connection is successful, False otherwise.
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

