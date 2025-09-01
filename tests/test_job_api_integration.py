"""
Integration tests for job management API

Tests the complete job management flow through the API endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import date

from orm_calculator.api import create_app
from orm_calculator.database.connection import init_database, close_database


@pytest_asyncio.fixture
async def app():
    """Create FastAPI app with database initialization"""
    # Initialize database
    await init_database()
    
    # Create app
    app = create_app()
    
    yield app
    
    # Cleanup
    await close_database()


@pytest_asyncio.fixture
async def client(app):
    """Create async HTTP client"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test health check endpoint"""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "orm-capital-calculator"


@pytest.mark.asyncio
async def test_queue_statistics(client):
    """Test queue statistics endpoint"""
    response = await client.get("/api/v1/calculation-jobs/queue/statistics")
    assert response.status_code == 200
    data = response.json()
    
    # Verify expected fields
    assert "total_jobs" in data
    assert "queued_jobs" in data
    assert "running_jobs" in data
    assert "status_breakdown" in data
    assert "max_concurrent_jobs" in data
    assert "sync_execution_threshold" in data
    assert "processor_running" in data


@pytest.mark.asyncio
async def test_create_sync_job(client):
    """Test creating a synchronous job"""
    job_request = {
        "model_name": "sma",
        "execution_mode": "sync",
        "entity_id": "TEST_ENTITY_001",
        "calculation_date": "2024-01-01"
    }
    
    response = await client.post("/api/v1/calculation-jobs", json=job_request)
    assert response.status_code == 201
    
    data = response.json()
    assert data["job_id"].startswith("sync_")
    assert data["run_id"].startswith("run_")
    assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_create_async_job(client):
    """Test creating an asynchronous job"""
    job_request = {
        "model_name": "sma",
        "execution_mode": "async",
        "entity_id": "TEST_ENTITY_002",
        "calculation_date": "2024-01-01",
        "callback_url": "https://example.com/webhook"
    }
    
    response = await client.post("/api/v1/calculation-jobs", json=job_request)
    assert response.status_code == 201
    
    data = response.json()
    assert data["job_id"].startswith("job_")
    assert data["run_id"].startswith("run_")
    assert data["status"] == "queued"
    assert data["callback_url"] == "https://example.com/webhook"


@pytest.mark.asyncio
async def test_get_job_status(client):
    """Test getting job status"""
    # Create a job first
    job_request = {
        "model_name": "sma",
        "execution_mode": "async",
        "entity_id": "TEST_ENTITY_003",
        "calculation_date": "2024-01-01"
    }
    
    create_response = await client.post("/api/v1/calculation-jobs", json=job_request)
    assert create_response.status_code == 201
    job_data = create_response.json()
    job_id = job_data["job_id"]
    
    # Get job status
    status_response = await client.get(f"/api/v1/calculation-jobs/{job_id}/status")
    assert status_response.status_code == 200
    
    status_data = status_response.json()
    assert status_data["job_id"] == job_id
    assert status_data["status"] == "queued"
    assert "progress_percentage" in status_data
    assert "result_available" in status_data


@pytest.mark.asyncio
async def test_get_job_result(client):
    """Test getting job result"""
    # Create a job first
    job_request = {
        "model_name": "sma",
        "execution_mode": "async",
        "entity_id": "TEST_ENTITY_004",
        "calculation_date": "2024-01-01"
    }
    
    create_response = await client.post("/api/v1/calculation-jobs", json=job_request)
    assert create_response.status_code == 201
    job_data = create_response.json()
    job_id = job_data["job_id"]
    
    # Get job result
    result_response = await client.get(f"/api/v1/calculation-jobs/{job_id}")
    assert result_response.status_code == 200
    
    result_data = result_response.json()
    assert result_data["job_id"] == job_id
    assert result_data["status"] == "queued"  # Job hasn't been processed yet


@pytest.mark.asyncio
async def test_cancel_job(client):
    """Test cancelling a job"""
    # Create a job first
    job_request = {
        "model_name": "sma",
        "execution_mode": "async",
        "entity_id": "TEST_ENTITY_005",
        "calculation_date": "2024-01-01"
    }
    
    create_response = await client.post("/api/v1/calculation-jobs", json=job_request)
    assert create_response.status_code == 201
    job_data = create_response.json()
    job_id = job_data["job_id"]
    
    # Cancel the job
    cancel_response = await client.delete(f"/api/v1/calculation-jobs/{job_id}")
    assert cancel_response.status_code == 204
    
    # Verify job is cancelled
    status_response = await client.get(f"/api/v1/calculation-jobs/{job_id}/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["status"] == "failed"


@pytest.mark.asyncio
async def test_cleanup_jobs(client):
    """Test job cleanup endpoint"""
    response = await client.post("/api/v1/calculation-jobs/cleanup?max_age_hours=1")
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "jobs_cleaned" in data
    assert "max_age_hours" in data
    assert data["max_age_hours"] == 1


@pytest.mark.asyncio
async def test_invalid_job_request(client):
    """Test invalid job request"""
    invalid_request = {
        "model_name": "invalid_model",
        "execution_mode": "sync",
        "entity_id": "",  # Empty entity ID
        "calculation_date": "invalid-date"
    }
    
    response = await client.post("/api/v1/calculation-jobs", json=invalid_request)
    assert response.status_code == 400
    
    data = response.json()
    assert data["error_code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_job_not_found(client):
    """Test getting non-existent job"""
    response = await client.get("/api/v1/calculation-jobs/job_nonexistent")
    assert response.status_code == 404
    
    data = response.json()
    assert data["error_code"] == "JOB_NOT_FOUND"


if __name__ == "__main__":
    pytest.main([__file__])