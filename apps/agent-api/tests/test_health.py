"""
Test health check endpoints
"""
import pytest
from fastapi import status


@pytest.mark.unit
def test_liveness_check(client):
    """Test liveness probe"""
    response = client.get("/health/liveness")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data
    assert "uptime_seconds" in data


@pytest.mark.unit
def test_readiness_check(client):
    """Test readiness probe"""
    response = client.get("/health/readiness")
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "database" in data["checks"]


@pytest.mark.unit
def test_startup_check(client):
    """Test startup probe"""
    response = client.get("/health/startup")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert data["status"] in ["starting", "started"]


@pytest.mark.unit
def test_detailed_health(client):
    """Test detailed health endpoint"""
    response = client.get("/health/detailed")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "system" in data
    assert "database" in data["checks"]
    assert "kafka" in data["checks"]
    assert "openai" in data["checks"]
    assert "lightfield" in data["checks"]
