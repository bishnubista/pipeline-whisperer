"""SQLAlchemy base model and database setup with connection pooling"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Determine if using SQLite or PostgreSQL
is_sqlite = settings.database_url.startswith("sqlite")

# Create engine with appropriate pooling
engine_kwargs = {
    "echo": settings.log_level == "DEBUG",
    "future": True,
}

if is_sqlite:
    # SQLite doesn't support connection pooling the same way
    # Use NullPool for SQLite to avoid threading issues
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    logger.info("Using SQLite database (no connection pooling)")
else:
    # PostgreSQL with connection pooling
    engine_kwargs["poolclass"] = QueuePool
    engine_kwargs["pool_size"] = settings.db_pool_size
    engine_kwargs["max_overflow"] = settings.db_max_overflow
    engine_kwargs["pool_timeout"] = settings.db_pool_timeout
    engine_kwargs["pool_recycle"] = settings.db_pool_recycle
    engine_kwargs["pool_pre_ping"] = True  # Verify connections before using
    logger.info(
        f"Using PostgreSQL with connection pool "
        f"(size={settings.db_pool_size}, max_overflow={settings.db_max_overflow})"
    )

engine = create_engine(settings.database_url, **engine_kwargs)


# Add connection pool logging for debugging
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    logger.debug("Database connection opened")


@event.listens_for(engine, "close")
def receive_close(dbapi_conn, connection_record):
    logger.debug("Database connection closed")


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_pool_status() -> dict:
    """Get database connection pool status"""
    if is_sqlite:
        return {
            "type": "sqlite",
            "pooling": False,
            "message": "SQLite does not use connection pooling",
        }

    try:
        pool = engine.pool
        return {
            "type": "postgresql",
            "pooling": True,
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "max_overflow": settings.db_max_overflow,
        }
    except Exception as e:
        logger.warning(f"Failed to get pool status: {e}")
        return {
            "type": "postgresql",
            "pooling": True,
            "error": str(e),
        }
