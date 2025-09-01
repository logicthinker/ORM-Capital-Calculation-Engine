"""
Calculation API routes for ORM Capital Calculator Engine

Implements job-based REST API endpoints for synchronous and asynchronous SMA calculations.
"""

import asyncio
import uuid
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from orm_calculator.models.pydantic_models import (
    CalculationRequest,
    CalculationResult,
    JobResponse,
    JobStatus,
    JobResult,
    JobStatusEnum,
    ModelNameEnum,
    ExecutionModeEnum,
    ErrorDetail,
    ValidationResult
)
from orm_calculator.services.sma_calculator import (
    SMACalculator,
    BusinessIndicatorData,
    LossData,
    SMACalculationResult
)
from orm_calculator.services.calculation_service import CalculationService
from orm_calculator.services.job_service import JobService
from orm_calculator.database.repositories import (
    BusinessIndicatorRepository,
    LossEventRepository,
    CalculationRepository,
    JobRepository
)

router = APIRouter(prefix="/calculation-jobs", tags=["calculations"])

# Global job service instance
job_service_instance = None

async def get_job_service_instance() -> JobService:
    """Get or create job service instance"""
    global job_service_instance
    if job_service_instance is None:
        job_service_instance = JobService()
        await job_service_instance.start_job_processor()
    return job_service_instance


class CalculationError(Exception):
    """Custom exception for calculation errors"""
    def __init__(self, message: str, error_code: str = "CALCULATION_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


def get_calculation_service() -> CalculationService:
    """Dependency to get calculation service instance"""
    return CalculationService()


async def get_job_service() -> JobService:
    """Dependency to get job service instance"""
    return await get_job_service_instance()


async def validate_calculation_request(request: CalculationRequest) -> List[ErrorDetail]:
    """
    Validate calculation request parameters
    
    Args:
        request: Calculation request to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Validate entity_id
    if not request.entity_id or len(request.entity_id.strip()) == 0:
        errors.append(ErrorDetail(
            error_code="INVALID_ENTITY_ID",
            error_message="Entity ID cannot be empty",
            field="entity_id"
        ))
    
    # Validate calculation_date
    if request.calculation_date > date.today():
        errors.append(ErrorDetail(
            error_code="INVALID_CALCULATION_DATE",
            error_message="Calculation date cannot be in the future",
            field="calculation_date"
        ))
    
    # Validate model-specific parameters
    if request.model_name == ModelNameEnum.SMA:
        # SMA-specific validations can be added here
        pass
    elif request.model_name in [ModelNameEnum.BIA, ModelNameEnum.TSA]:
        # Legacy method validations
        pass
    elif request.model_name == ModelNameEnum.WHAT_IF:
        # What-if scenario validations
        if not request.parameters:
            errors.append(ErrorDetail(
                error_code="MISSING_WHAT_IF_PARAMETERS",
                error_message="What-if scenarios require parameters",
                field="parameters"
            ))
    
    # Validate callback URL for async requests
    if request.execution_mode == ExecutionModeEnum.ASYNC and request.callback_url:
        if not request.callback_url.startswith(('http://', 'https://')):
            errors.append(ErrorDetail(
                error_code="INVALID_CALLBACK_URL",
                error_message="Callback URL must be a valid HTTP/HTTPS URL",
                field="callback_url"
            ))
    
    return errors


async def perform_sma_calculation(
    entity_id: str,
    calculation_date: date,
    run_id: str,
    parameters: Optional[Dict[str, Any]] = None
) -> CalculationResult:
    """
    Perform SMA calculation for given entity and date
    
    Args:
        entity_id: Entity identifier
        calculation_date: Date for calculation
        run_id: Unique run identifier
        parameters: Optional custom parameters
        
    Returns:
        Calculation result
        
    Raises:
        CalculationError: If calculation fails
    """
    try:
        # Initialize SMA calculator with parameters
        calculator = SMACalculator(
            model_version="1.0.0",
            parameters_version="1.0.0",
            parameters=parameters
        )
        
        # Mock business indicator data (replace with actual data retrieval)
        bi_data = [
            BusinessIndicatorData(
                period="2023-Q4",
                ildc=Decimal('1000000000'),  # ₹100 crore
                sc=Decimal('500000000'),     # ₹50 crore
                fc=Decimal('300000000'),     # ₹30 crore
                entity_id=entity_id,
                calculation_date=calculation_date
            ),
            BusinessIndicatorData(
                period="2022-Q4",
                ildc=Decimal('950000000'),
                sc=Decimal('480000000'),
                fc=Decimal('290000000'),
                entity_id=entity_id,
                calculation_date=calculation_date
            ),
            BusinessIndicatorData(
                period="2021-Q4",
                ildc=Decimal('900000000'),
                sc=Decimal('460000000'),
                fc=Decimal('280000000'),
                entity_id=entity_id,
                calculation_date=calculation_date
            )
        ]
        
        # Mock loss data (replace with actual data retrieval)
        loss_data = [
            LossData(
                event_id="LOSS_001",
                entity_id=entity_id,
                accounting_date=date(2023, 6, 15),
                net_loss=Decimal('50000000'),  # ₹5 crore
                is_excluded=False
            ),
            LossData(
                event_id="LOSS_002",
                entity_id=entity_id,
                accounting_date=date(2022, 8, 20),
                net_loss=Decimal('75000000'),  # ₹7.5 crore
                is_excluded=False
            )
        ]
        
        # Validate inputs
        validation_errors = calculator.validate_inputs(bi_data, loss_data)
        if validation_errors:
            raise CalculationError(
                message=f"Input validation failed: {'; '.join(validation_errors)}",
                error_code="VALIDATION_ERROR",
                details={"validation_errors": validation_errors}
            )
        
        # Perform SMA calculation
        sma_result = calculator.calculate_sma(
            bi_data=bi_data,
            loss_data=loss_data,
            entity_id=entity_id,
            calculation_date=calculation_date,
            run_id=run_id
        )
        
        # Convert to API response format
        result = CalculationResult(
            run_id=run_id,
            entity_id=entity_id,
            calculation_date=calculation_date,
            methodology=ModelNameEnum.SMA,
            business_indicator=sma_result.bi_three_year_average,
            business_indicator_component=sma_result.bic,
            loss_component=sma_result.lc,
            internal_loss_multiplier=sma_result.ilm,
            operational_risk_capital=sma_result.orc,
            risk_weighted_assets=sma_result.rwa,
            bucket=sma_result.bucket.value.split('_')[1],  # Extract bucket number
            ilm_gated=sma_result.ilm_gated,
            ilm_gate_reason=sma_result.ilm_gate_reason,
            parameter_version=sma_result.parameters_version,
            model_version=sma_result.model_version,
            supervisor_override=False,
            created_at=sma_result.calculation_timestamp
        )
        
        return result
        
    except Exception as e:
        if isinstance(e, CalculationError):
            raise
        else:
            raise CalculationError(
                message=f"Unexpected error during calculation: {str(e)}",
                error_code="INTERNAL_ERROR",
                details={"original_error": str(e)}
            )


# Remove the old execute_calculation_job function as it's now handled by JobService


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create calculation job",
    description="Create a new calculation job for SMA, BIA, TSA, or what-if scenarios"
)
async def create_calculation_job(
    request: CalculationRequest,
    background_tasks: BackgroundTasks,
    job_service: JobService = Depends(get_job_service)
) -> JobResponse:
    """
    Create a new calculation job
    
    - **Synchronous execution**: Returns results immediately for fast calculations (≤60 seconds)
    - **Asynchronous execution**: Returns job_id for long-running calculations with webhook callbacks
    - **Idempotency**: Use idempotency_key to prevent duplicate calculations
    - **Correlation**: Use correlation_id for request tracing
    """
    try:
        # Validate request
        validation_errors = await validate_calculation_request(request)
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "VALIDATION_ERROR",
                    "error_message": "Request validation failed",
                    "details": {"validation_errors": [error.dict() for error in validation_errors]}
                }
            )
        
        # Handle synchronous execution
        if request.execution_mode == ExecutionModeEnum.SYNC:
            try:
                # Execute synchronously using job service
                result = await job_service.execute_sync_job(request)
                
                # Return immediate response with completed status
                return JobResponse(
                    job_id=f"sync_{uuid.uuid4().hex[:8]}",
                    run_id=result.run_id,
                    status=JobStatusEnum.COMPLETED,
                    callback_url=request.callback_url,
                    created_at=result.created_at
                )
                
            except Exception as e:
                error_code = getattr(e, 'error_code', 'EXECUTION_ERROR')
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": error_code,
                        "error_message": str(e),
                        "details": getattr(e, 'details', {})
                    }
                )
        
        # Handle asynchronous execution
        else:
            # Create job using job service
            return await job_service.create_job(request)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_message": "An unexpected error occurred",
                "details": {"original_error": str(e)}
            }
        )


@router.get(
    "/{job_id}",
    response_model=JobResult,
    summary="Get calculation job result",
    description="Retrieve calculation job status and results by job ID"
)
async def get_calculation_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service)
) -> JobResult:
    """
    Get calculation job status and results
    
    - **job_id**: Unique job identifier returned from job creation
    - Returns job status, progress, and results when available
    - For failed jobs, includes detailed error information
    """
    try:
        job_result = await job_service.get_job_result(job_id)
        
        if not job_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "JOB_NOT_FOUND",
                    "error_message": f"Job with ID {job_id} not found",
                    "details": {"job_id": job_id}
                }
            )
        
        return job_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_message": "An unexpected error occurred while retrieving job",
                "details": {"original_error": str(e)}
            }
        )


@router.get(
    "/{job_id}/status",
    response_model=JobStatus,
    summary="Get calculation job status",
    description="Get detailed status information for a calculation job"
)
async def get_job_status(
    job_id: str,
    job_service: JobService = Depends(get_job_service)
) -> JobStatus:
    """
    Get detailed job status information
    
    - **job_id**: Unique job identifier
    - Returns current status, progress percentage, and timing information
    - Useful for polling job progress in async scenarios
    """
    try:
        job_status = await job_service.get_job_status(job_id)
        
        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "JOB_NOT_FOUND",
                    "error_message": f"Job with ID {job_id} not found",
                    "details": {"job_id": job_id}
                }
            )
        
        return job_status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_message": "An unexpected error occurred while retrieving job status",
                "details": {"original_error": str(e)}
            }
        )


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel calculation job",
    description="Cancel a queued or running calculation job"
)
async def cancel_calculation_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service)
) -> None:
    """
    Cancel a calculation job
    
    - **job_id**: Unique job identifier
    - Only queued or running jobs can be cancelled
    - Completed or failed jobs cannot be cancelled
    """
    try:
        cancelled = await job_service.cancel_job(job_id)
        
        if not cancelled:
            # Check if job exists to provide appropriate error
            job_status = await job_service.get_job_status(job_id)
            
            if not job_status:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error_code": "JOB_NOT_FOUND",
                        "error_message": f"Job with ID {job_id} not found",
                        "details": {"job_id": job_id}
                    }
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "JOB_NOT_CANCELLABLE",
                        "error_message": f"Job with status {job_status.status} cannot be cancelled",
                        "details": {"job_id": job_id, "current_status": job_status.status}
                    }
                )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_message": "An unexpected error occurred while cancelling job",
                "details": {"original_error": str(e)}
            }
        )


@router.get(
    "/queue/statistics",
    summary="Get job queue statistics",
    description="Get statistics about the job queue and processing status"
)
async def get_queue_statistics(
    job_service: JobService = Depends(get_job_service)
) -> Dict[str, Any]:
    """
    Get job queue statistics
    
    Returns information about:
    - Total jobs in system
    - Jobs by status (queued, running, completed, failed)
    - Queue size and processing capacity
    - System configuration
    """
    try:
        return await job_service.get_queue_statistics()
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_message": "An unexpected error occurred while retrieving queue statistics",
                "details": {"original_error": str(e)}
            }
        )


@router.post(
    "/cleanup",
    summary="Clean up old completed jobs",
    description="Remove old completed and failed jobs from the system"
)
async def cleanup_old_jobs(
    max_age_hours: int = 24,
    job_service: JobService = Depends(get_job_service)
) -> Dict[str, Any]:
    """
    Clean up old completed jobs
    
    - **max_age_hours**: Maximum age in hours for jobs to keep (default: 24)
    - Removes completed and failed jobs older than the specified age
    - Returns count of jobs cleaned up
    """
    try:
        if max_age_hours < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_MAX_AGE",
                    "error_message": "max_age_hours must be at least 1",
                    "details": {"provided_value": max_age_hours}
                }
            )
        
        cleaned_count = await job_service.cleanup_completed_jobs(max_age_hours)
        
        return {
            "message": f"Cleaned up {cleaned_count} old jobs",
            "jobs_cleaned": cleaned_count,
            "max_age_hours": max_age_hours
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_message": "An unexpected error occurred during cleanup",
                "details": {"original_error": str(e)}
            }
        )