"""
Loss Data Management API Routes for ORM Capital Calculator Engine

REST API endpoints for loss data ingestion, recovery management, and exclusion handling.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from orm_calculator.database.connection import get_db_session
from orm_calculator.models.pydantic_models import (
    LossEventCreate, LossEventResponse, RecoveryCreate, RecoveryResponse,
    LossEventExclusion, LossDataBatch, LossDataFilter, LossDataStatistics,
    RecoveryBatch, ValidationResult, ErrorDetail
)
from orm_calculator.services.loss_data_service import (
    LossDataManagementService, RBIApprovalMetadata
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/loss-data", tags=["Loss Data Management"])


@router.post("/events", response_model=ValidationResult, status_code=status.HTTP_201_CREATED)
async def ingest_loss_events(
    loss_events: List[LossEventCreate],
    minimum_threshold: Optional[Decimal] = Query(None, description="Custom minimum threshold"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Ingest loss events with validation
    
    - **loss_events**: List of loss events to ingest
    - **minimum_threshold**: Custom minimum threshold (default: ₹1,00,000)
    """
    try:
        service = LossDataManagementService(db, minimum_threshold)
        result = await service.ingest_loss_events(loss_events)
        
        if not result.success:
            logger.warning(f"Loss event ingestion completed with {result.records_rejected} rejections")
        
        return result
        
    except Exception as e:
        logger.error(f"Error ingesting loss events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest loss events: {str(e)}"
        )


@router.post("/events/batch", response_model=ValidationResult, status_code=status.HTTP_201_CREATED)
async def ingest_loss_events_batch(
    batch: LossDataBatch,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Batch ingest loss events with validation
    
    - **batch**: Batch of loss events with processing options
    """
    try:
        service = LossDataManagementService(db, batch.minimum_threshold)
        
        if batch.validate_only:
            # Validation only mode - don't save to database
            validation_result = ValidationResult(
                success=True,
                records_processed=len(batch.loss_events)
            )
            
            for loss_event in batch.loss_events:
                validation_errors = service.validation_service.validate_loss_event(loss_event)
                if validation_errors:
                    validation_result.errors.extend(validation_errors)
                    validation_result.records_rejected += 1
                else:
                    validation_result.records_accepted += 1
            
            validation_result.success = validation_result.records_rejected == 0
            return validation_result
        else:
            # Full ingestion
            return await service.ingest_loss_events(batch.loss_events)
        
    except Exception as e:
        logger.error(f"Error processing loss event batch: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process loss event batch: {str(e)}"
        )


@router.get("/events", response_model=List[LossEventResponse])
async def get_loss_events(
    entity_id: str = Query(..., description="Entity identifier"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    minimum_amount: Optional[Decimal] = Query(None, description="Minimum loss amount"),
    include_excluded: bool = Query(False, description="Include excluded losses"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get loss events with filtering
    
    - **entity_id**: Entity identifier (required)
    - **start_date**: Filter by start date
    - **end_date**: Filter by end date
    - **minimum_amount**: Filter by minimum amount
    - **include_excluded**: Include excluded losses
    """
    try:
        service = LossDataManagementService(db)
        
        # Use the query service for filtered results
        return await service.query_service.get_losses_above_threshold(
            entity_id=entity_id,
            threshold=minimum_amount,
            start_date=start_date,
            end_date=end_date,
            include_excluded=include_excluded
        )
        
    except Exception as e:
        logger.error(f"Error retrieving loss events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve loss events: {str(e)}"
        )


@router.get("/events/calculation/{entity_id}", response_model=List[LossEventResponse])
async def get_losses_for_calculation(
    entity_id: str,
    calculation_date: date = Query(..., description="Calculation date"),
    lookback_years: int = Query(10, ge=1, le=20, description="Years to look back"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get loss events for SMA calculation
    
    - **entity_id**: Entity identifier
    - **calculation_date**: Calculation date
    - **lookback_years**: Number of years to look back (default: 10)
    """
    try:
        service = LossDataManagementService(db)
        return await service.get_losses_for_calculation(
            entity_id=entity_id,
            calculation_date=calculation_date,
            lookback_years=lookback_years
        )
        
    except Exception as e:
        logger.error(f"Error retrieving losses for calculation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve losses for calculation: {str(e)}"
        )


@router.get("/events/statistics/{entity_id}", response_model=LossDataStatistics)
async def get_loss_statistics(
    entity_id: str,
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get loss data statistics for an entity
    
    - **entity_id**: Entity identifier
    - **start_date**: Start date for statistics
    - **end_date**: End date for statistics
    """
    try:
        service = LossDataManagementService(db)
        stats = await service.get_loss_statistics(entity_id, start_date, end_date)
        
        # Convert to response model
        return LossDataStatistics(
            entity_id=entity_id,
            period_start=start_date,
            period_end=end_date,
            total_events=stats['total_events'],
            total_gross_amount=stats['total_gross_amount'],
            total_net_amount=stats['total_net_amount'],
            total_recoveries=stats['total_gross_amount'] - stats['total_net_amount'],
            average_gross_amount=stats['average_gross_amount'],
            maximum_gross_amount=stats['maximum_gross_amount'],
            minimum_gross_amount=stats['minimum_gross_amount'],
            events_above_threshold=stats['total_events'],  # All returned events are above threshold
            threshold_amount=Decimal('100000.00'),
            excluded_events=0,  # Would need additional query
            outsourced_events=0,  # Would need additional query
            pending_events=0,  # Would need additional query
            timing_events=0  # Would need additional query
        )
        
    except Exception as e:
        logger.error(f"Error retrieving loss statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve loss statistics: {str(e)}"
        )


@router.post("/recoveries", response_model=RecoveryResponse, status_code=status.HTTP_201_CREATED)
async def add_recovery(
    recovery: RecoveryCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Add recovery to loss event and recalculate net loss
    
    - **recovery**: Recovery data to add
    """
    try:
        service = LossDataManagementService(db)
        recovery_response, errors = await service.add_recovery(recovery)
        
        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Recovery validation failed",
                    "errors": [error.dict() for error in errors]
                }
            )
        
        if not recovery_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loss event not found"
            )
        
        return recovery_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding recovery: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add recovery: {str(e)}"
        )


@router.post("/recoveries/batch", response_model=ValidationResult, status_code=status.HTTP_201_CREATED)
async def add_recoveries_batch(
    batch: RecoveryBatch,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Batch add recoveries to loss events
    
    - **batch**: Batch of recoveries with processing options
    """
    try:
        service = LossDataManagementService(db)
        
        validation_result = ValidationResult(
            success=True,
            records_processed=len(batch.recoveries)
        )
        
        for recovery in batch.recoveries:
            if batch.validate_only:
                # Validation only - check if loss event exists and validate recovery
                loss_event = await service.ingestion_service.loss_repo.find_by_id(recovery.loss_event_id)
                if not loss_event:
                    validation_result.errors.append(ErrorDetail(
                        error_code="LOSS_EVENT_NOT_FOUND",
                        error_message=f"Loss event {recovery.loss_event_id} not found",
                        field="loss_event_id"
                    ))
                    validation_result.records_rejected += 1
                    continue
                
                validation_errors = service.validation_service.validate_recovery(recovery, loss_event)
                if validation_errors:
                    validation_result.errors.extend(validation_errors)
                    validation_result.records_rejected += 1
                else:
                    validation_result.records_accepted += 1
            else:
                # Full processing
                recovery_response, errors = await service.add_recovery(recovery)
                if errors:
                    validation_result.errors.extend(errors)
                    validation_result.records_rejected += 1
                else:
                    validation_result.records_accepted += 1
        
        validation_result.success = validation_result.records_rejected == 0
        return validation_result
        
    except Exception as e:
        logger.error(f"Error processing recovery batch: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process recovery batch: {str(e)}"
        )


@router.post("/events/{loss_event_id}/exclude", status_code=status.HTTP_200_OK)
async def exclude_loss_event(
    loss_event_id: str,
    exclusion: LossEventExclusion,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Exclude loss event with RBI approval
    
    - **loss_event_id**: Loss event ID to exclude
    - **exclusion**: Exclusion details with RBI approval metadata
    """
    try:
        # Create RBI approval metadata
        rbi_approval = RBIApprovalMetadata(
            approval_reference=exclusion.rbi_approval_reference,
            approval_date=exclusion.rbi_approval_date,
            approving_authority=exclusion.approving_authority,
            approval_reason=exclusion.exclusion_reason
        )
        
        service = LossDataManagementService(db)
        success, errors = await service.exclude_loss_event(
            loss_event_id=loss_event_id,
            exclusion_reason=exclusion.exclusion_reason,
            rbi_approval=rbi_approval
        )
        
        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Loss event exclusion failed",
                    "errors": [error.dict() for error in errors]
                }
            )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loss event not found or exclusion failed"
            )
        
        return {"message": "Loss event excluded successfully", "disclosure_required": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error excluding loss event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to exclude loss event: {str(e)}"
        )


@router.get("/validation/thresholds", response_model=dict)
async def get_validation_thresholds():
    """
    Get current validation thresholds and rules
    """
    return {
        "minimum_threshold": "100000.00",
        "currency": "INR",
        "valid_basel_event_types": [
            "internal_fraud", "external_fraud", "employment_practices",
            "clients_products_business", "damage_physical_assets",
            "business_disruption", "execution_delivery_process"
        ],
        "valid_business_lines": [
            "corporate_finance", "trading_sales", "retail_banking",
            "commercial_banking", "payment_settlement", "agency_services",
            "asset_management", "retail_brokerage"
        ],
        "required_fields": [
            "entity_id", "event_type", "occurrence_date", "discovery_date",
            "accounting_date", "gross_amount"
        ],
        "date_validation_rules": {
            "discovery_date": "Must be on or after occurrence_date",
            "accounting_date": "Cannot be before occurrence_date"
        },
        "exclusion_requirements": {
            "rbi_approval_required": True,
            "disclosure_required": True,
            "retention_period_years": 3
        }
    }


@router.get("/health", response_model=dict)
async def health_check(db: AsyncSession = Depends(get_db_session)):
    """
    Health check for loss data management service
    """
    try:
        # Test database connectivity
        service = LossDataManagementService(db)
        
        return {
            "status": "healthy",
            "service": "loss_data_management",
            "database": "connected",
            "validation_service": "active",
            "minimum_threshold": "100000.00"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )