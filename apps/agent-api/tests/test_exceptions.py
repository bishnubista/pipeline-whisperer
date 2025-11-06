"""
Test custom exception hierarchy
"""
import pytest
from app.exceptions import (
    PipelineWhispererException,
    ValidationError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    OpenAIServiceError,
)


@pytest.mark.unit
def test_base_exception():
    """Test base exception"""
    exc = PipelineWhispererException("Test error", status_code=500)
    assert exc.message == "Test error"
    assert exc.status_code == 500
    assert exc.details == {}


@pytest.mark.unit
def test_validation_error():
    """Test validation error"""
    exc = ValidationError("Invalid input", details={"field": "email"})
    assert exc.message == "Invalid input"
    assert exc.status_code == 400
    assert exc.details["field"] == "email"


@pytest.mark.unit
def test_authentication_error():
    """Test authentication error"""
    exc = AuthenticationError()
    assert exc.status_code == 401
    assert "Authentication" in exc.message


@pytest.mark.unit
def test_not_found_error():
    """Test not found error"""
    exc = NotFoundError("Resource not found")
    assert exc.status_code == 404
    assert "not found" in exc.message.lower()


@pytest.mark.unit
def test_rate_limit_error():
    """Test rate limit error"""
    exc = RateLimitError()
    assert exc.status_code == 429
    assert "rate limit" in exc.message.lower()


@pytest.mark.unit
def test_external_service_error():
    """Test external service error"""
    exc = OpenAIServiceError("API timeout")
    assert exc.status_code == 503
    assert exc.service_name == "OpenAI"
    assert "OpenAI" in exc.message
    assert exc.details["service"] == "OpenAI"
