"""
Pytest fixtures and configuration
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, get_db
from main import app


# Test database
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with overridden database dependency"""
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_lead_data():
    """Sample lead data for testing"""
    return {
        "company_name": "Test Corp",
        "industry": "technology",
        "employee_count": 100,
        "revenue": 10000000,
        "website": "testcorp.com",
        "contact_email": "contact@testcorp.com",
    }


@pytest.fixture
def sample_experiment_data():
    """Sample experiment data for testing"""
    return {
        "name": "Test Experiment",
        "variant_type": "subject_line",
        "description": "Test experiment description",
        "alpha": 1.0,
        "beta": 1.0,
    }
