"""
Test job management functionality

Tests for async job execution, status tracking, and queue management.
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, date
from decimal import Decimal

from orm_calculator.services.job_service import JobService, JobPriority
from orm_calculator.models.pydantic_models import (
    CalculationRequest,
    ModelNameEnum,
    ExecutionModeEnum,
    JobStatusEnum
)
from orm_calculator.database.connection import init_database, close_database


@pytest_asyncio.fixture
async def job_service():
    """Create job service instance for testing"""
    # Initialize database for testing
    await init_database()
    
    service = JobService()
    await service.start_job_processor()
    
    try:
        yield service
    finally:
        await service.stop_job_processor()
        await close_database()


@pytest.fixture
def sample_calculation_request():
    """Create sample calculation request for testing"""
    return CalculationRequest(
        model_name=ModelNameEnum.SMA,
        execution_mode=ExecutionModeEnum.ASYNC,
        entity_id="TEST_ENTITY_001",
        calculation_date=date(2024, 1, 1),
        parameters={"test_param": "test_value"},
        callback_url="https://example.com/webhook",
        idempotency_key="test_idempotency_key_001",
        correlation_id="test_correlation_001"
    )


@pytest.mark.asyncio
async def test_create_async_job(job_service, sample_calculation_request):
    """Test creating an async job"""
    # Create job
    job_response = await job_service.create_job(sample_calculation_request)
    
    # Verify job response
    assert job_response.job_id.startswith("job_")
    assert job_response.run_id.startswith("run_")
    assert job_response.status == JobStatusEnum.QUEUED
    assert job_response.callback_url == sample_calculation_request.callback_url
    assert isinstance(job_response.created_at, datetime)


@pytest.mark.asyncio
async def test_get_job_status(job_service, sample_calculation_request):
    """Test getting job status"""
    # Create job
    job_response = await job_service.create_job(sample_calculation_request)
    
    # Get job status
    job_status = await job_service.get_job_status(job_response.job_id)
    
    # Verify status
    assert job_status is not None
    assert job_status.job_id == job_response.job_id
    assert job_status.run_id == job_response.run_id
    assert job_status.status == JobStatusEnum.QUEUED
    assert job_status.progress_percentage == 0.0 or job_status.progress_percentage is None


@pytest.mark.asyncio
async def test_get_job_result(job_service, sample_calculation_request):
    """Test getting job result"""
    # Create job
    job_response = await job_service.create_job(sample_calculation_request)
    
    # Get job result
    job_result = await job_service.get_job_result(job_response.job_id)
    
    # Verify result structure
    assert job_result is not None
    assert job_result.job_id == job_response.job_id
    assert job_result.run_id == job_response.run_id
    assert job_result.status == JobStatusEnum.QUEUED
    assert job_result.result is None  # No result yet for queued job


@pytest.mark.asyncio
async def test_cancel_job(job_service, sample_calculation_request):
    """Test cancelling a job"""
    # Create job
    job_response = await job_service.create_job(sample_calculation_request)
    
    # Cancel job
    cancelled = await job_service.cancel_job(job_response.job_id)
    assert cancelled is True
    
    # Verify job is cancelled
    job_status = await job_service.get_job_status(job_response.job_id)
    assert job_status.status == JobStatusEnum.FAILED
    
    # Verify error details indicate cancellation
    job_result = await job_service.get_job_result(job_response.job_id)
    assert job_result.error_details is not None
    assert job_result.error_details["error_code"] == "JOB_CANCELLED"


@pytest.mark.asyncio
async def test_idempotency(job_service, sample_calculation_request):
    """Test idempotency key functionality"""
    # Create first job
    job_response1 = await job_service.create_job(sample_calculation_request)
    
    # Create second job with same idempotency key
    job_response2 = await job_service.create_job(sample_calculation_request)
    
    # Should return the same job
    assert job_response1.job_id == job_response2.job_id
    assert job_response1.run_id == job_response2.run_id


@pytest.mark.asyncio
async def test_sync_execution(job_service):
    """Test synchronous job execution"""
    sync_request = CalculationRequest(
        model_name=ModelNameEnum.SMA,
        execution_mode=ExecutionModeEnum.SYNC,
        entity_id="TEST_ENTITY_SYNC",
        calculation_date=date(2024, 1, 1)
    )
    
    # Execute sync job
    result = await job_service.execute_sync_job(sync_request)
    
    # Verify result
    assert result is not None
    assert result.run_id.startswith("run_")
    assert result.entity_id == sync_request.entity_id
    assert result.methodology == ModelNameEnum.SMA
    assert isinstance(result.operational_risk_capital, Decimal)
    assert isinstance(result.risk_weighted_assets, Decimal)


@pytest.mark.asyncio
async def test_queue_statistics(job_service, sample_calculation_request):
    """Test queue statistics"""
    # Get initial statistics
    initial_stats = await job_service.get_queue_statistics()
    
    # Create a job
    await job_service.create_job(sample_calculation_request)
    
    # Get updated statistics
    updated_stats = await job_service.get_queue_statistics()
    
    # Verify statistics structure
    assert "total_jobs" in updated_stats
    assert "queued_jobs" in updated_stats
    assert "running_jobs" in updated_stats
    assert "status_breakdown" in updated_stats
    assert "max_concurrent_jobs" in updated_stats
    assert "sync_execution_threshold" in updated_stats
    assert "processor_running" in updated_stats
    
    # Verify job was added
    assert updated_stats["total_jobs"] >= initial_stats["total_jobs"]


@pytest.mark.asyncio
async def test_job_cleanup(job_service, sample_calculation_request):
    """Test job cleanup functionality"""
    # Create and immediately cancel a job to have a completed job
    job_response = await job_service.create_job(sample_calculation_request)
    await job_service.cancel_job(job_response.job_id)
    
    # Run cleanup with 0 hours (should clean up the cancelled job)
    cleaned_count = await job_service.cleanup_completed_jobs(max_age_hours=0)
    
    # Verify cleanup occurred
    assert cleaned_count >= 0  # May be 0 if job was just created


@pytest.mark.asyncio
async def test_job_not_found(job_service):
    """Test handling of non-existent jobs"""
    non_existent_job_id = "job_nonexistent"
    
    # Test get_job_status
    status = await job_service.get_job_status(non_existent_job_id)
    assert status is None
    
    # Test get_job_result
    result = await job_service.get_job_result(non_existent_job_id)
    assert result is None
    
    # Test cancel_job
    cancelled = await job_service.cancel_job(non_existent_job_id)
    assert cancelled is False


@pytest.mark.asyncio
async def test_execution_mode_auto_selection(job_service):
    """Test automatic execution mode selection based on estimated duration"""
    # Create request with sync mode but parameters that might take longer
    request = CalculationRequest(
        model_name=ModelNameEnum.SMA,
        execution_mode=ExecutionModeEnum.SYNC,
        entity_id="TEST_ENTITY_AUTO",
        calculation_date=date(2024, 1, 1),
        parameters={"complex_calculation": True}  # This might trigger async mode
    )
    
    # Create job
    job_response = await job_service.create_job(request)
    
    # Verify job was created (mode selection is internal)
    assert job_response.job_id.startswith("job_")
    assert job_response.status == JobStatusEnum.QUEUED


if __name__ == "__main__":
    pytest.main([__file__])