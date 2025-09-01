"""
Lineage API routes for ORM Capital Calculator Engine

Provides endpoints for data lineage tracking and audit trail access.
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from orm_calculator.database.connection import get_db_session
from orm_calculator.services.lineage_service import LineageService
from orm_calculator.models.pydantic_models import CompleteLineage, AuditRecord


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lineage", tags=["lineage"])


@router.get("/{run_id}", response_model=CompleteLineage)
async def get_lineage(
    run_id: str,
    session: AsyncSession = Depends(get_db_session)
) -> CompleteLineage:
    """
    Get complete data lineage for a calculation run
    
    Provides complete traceability including:
    - Final outputs (ORC, RWA)
    - Intermediate results (BI, BIC, LC, ILM)
    - Parameter versions used
    - Model versions used
    - Input data aggregates
    - Included loss event IDs
    - Environment hash for reproducibility
    
    Args:
        run_id: Unique calculation run identifier
        session: Database session
        
    Returns:
        Complete lineage information
        
    Raises:
        HTTPException: If run_id not found or access denied
    """
    try:
        lineage_service = LineageService(session)
        lineage = await lineage_service.get_complete_lineage(run_id)
        
        if not lineage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "LINEAGE_NOT_FOUND",
                    "error_message": f"No lineage found for run_id: {run_id}",
                    "details": {"run_id": run_id}
                }
            )
        
        logger.info(f"Retrieved lineage for run_id: {run_id}")
        return lineage
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving lineage for run_id {run_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "LINEAGE_RETRIEVAL_ERROR",
                "error_message": "Failed to retrieve lineage information",
                "details": {"run_id": run_id, "error": str(e)}
            }
        )


@router.get("/{run_id}/audit", response_model=List[AuditRecord])
async def get_audit_trail(
    run_id: str,
    session: AsyncSession = Depends(get_db_session)
) -> List[AuditRecord]:
    """
    Get complete audit trail for a calculation run
    
    Provides detailed audit records including:
    - All operations performed
    - Input snapshots
    - Parameter versions
    - Results and errors
    - Timestamps and initiators
    - Immutable hashes for integrity verification
    
    Args:
        run_id: Unique calculation run identifier
        session: Database session
        
    Returns:
        List of audit records in chronological order
        
    Raises:
        HTTPException: If run_id not found or access denied
    """
    try:
        lineage_service = LineageService(session)
        audit_records = await lineage_service.get_audit_records(run_id)
        
        if not audit_records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "AUDIT_TRAIL_NOT_FOUND",
                    "error_message": f"No audit trail found for run_id: {run_id}",
                    "details": {"run_id": run_id}
                }
            )
        
        logger.info(f"Retrieved {len(audit_records)} audit records for run_id: {run_id}")
        return audit_records
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving audit trail for run_id {run_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "AUDIT_TRAIL_RETRIEVAL_ERROR",
                "error_message": "Failed to retrieve audit trail",
                "details": {"run_id": run_id, "error": str(e)}
            }
        )


@router.get("/{run_id}/integrity", response_model=Dict[str, Any])
async def verify_data_integrity(
    run_id: str,
    session: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Verify data integrity for a calculation run using SHA-256 hashes
    
    Checks the integrity of all audit records by verifying their
    immutable hashes against recalculated values.
    
    Args:
        run_id: Unique calculation run identifier
        session: Database session
        
    Returns:
        Dictionary with integrity check results
        
    Raises:
        HTTPException: If run_id not found or verification fails
    """
    try:
        lineage_service = LineageService(session)
        integrity_results = await lineage_service.verify_data_integrity(run_id)
        
        if not integrity_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "INTEGRITY_CHECK_NOT_FOUND",
                    "error_message": f"No data found for integrity check of run_id: {run_id}",
                    "details": {"run_id": run_id}
                }
            )
        
        # Calculate overall integrity status
        all_valid = all(integrity_results.values())
        total_records = len(integrity_results)
        valid_records = sum(1 for valid in integrity_results.values() if valid)
        
        result = {
            "run_id": run_id,
            "overall_integrity": all_valid,
            "total_records": total_records,
            "valid_records": valid_records,
            "invalid_records": total_records - valid_records,
            "record_integrity": integrity_results,
            "verification_timestamp": "2024-01-01T00:00:00Z"  # Will be replaced with actual timestamp
        }
        
        # Update with actual timestamp
        from datetime import datetime
        result["verification_timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        logger.info(f"Integrity verification for run_id {run_id}: {valid_records}/{total_records} records valid")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying integrity for run_id {run_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTEGRITY_VERIFICATION_ERROR",
                "error_message": "Failed to verify data integrity",
                "details": {"run_id": run_id, "error": str(e)}
            }
        )


@router.get("/{run_id}/reproducibility", response_model=Dict[str, Any])
async def check_reproducibility(
    run_id: str,
    session: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Check if a calculation run is reproducible
    
    Verifies that all necessary components are available to
    reproduce the calculation exactly:
    - Input data snapshots
    - Parameter versions
    - Model versions
    - Environment information
    
    Args:
        run_id: Unique calculation run identifier
        session: Database session
        
    Returns:
        Dictionary with reproducibility status and details
        
    Raises:
        HTTPException: If run_id not found
    """
    try:
        lineage_service = LineageService(session)
        lineage = await lineage_service.get_complete_lineage(run_id)
        
        if not lineage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "REPRODUCIBILITY_CHECK_NOT_FOUND",
                    "error_message": f"No data found for reproducibility check of run_id: {run_id}",
                    "details": {"run_id": run_id}
                }
            )
        
        # Check reproducibility components
        has_final_outputs = bool(lineage.final_outputs)
        has_intermediates = bool(lineage.intermediates)
        has_parameter_versions = bool(lineage.parameter_versions)
        has_model_versions = bool(lineage.model_versions)
        has_input_aggregates = bool(lineage.input_aggregates)
        has_environment_hash = bool(lineage.environment_hash)
        
        reproducibility_score = sum([
            has_final_outputs,
            has_intermediates,
            has_parameter_versions,
            has_model_versions,
            has_input_aggregates,
            has_environment_hash
        ]) / 6.0
        
        result = {
            "run_id": run_id,
            "reproducible": lineage.reproducible,
            "reproducibility_score": reproducibility_score,
            "components": {
                "final_outputs": has_final_outputs,
                "intermediates": has_intermediates,
                "parameter_versions": has_parameter_versions,
                "model_versions": has_model_versions,
                "input_aggregates": has_input_aggregates,
                "environment_hash": has_environment_hash
            },
            "missing_components": [
                component for component, available in {
                    "final_outputs": has_final_outputs,
                    "intermediates": has_intermediates,
                    "parameter_versions": has_parameter_versions,
                    "model_versions": has_model_versions,
                    "input_aggregates": has_input_aggregates,
                    "environment_hash": has_environment_hash
                }.items() if not available
            ],
            "check_timestamp": "2024-01-01T00:00:00Z"  # Will be replaced with actual timestamp
        }
        
        # Update with actual timestamp
        from datetime import datetime
        result["check_timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        logger.info(f"Reproducibility check for run_id {run_id}: {reproducibility_score:.2%} complete")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking reproducibility for run_id {run_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "REPRODUCIBILITY_CHECK_ERROR",
                "error_message": "Failed to check reproducibility",
                "details": {"run_id": run_id, "error": str(e)}
            }
        )