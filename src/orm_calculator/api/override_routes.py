"""
API routes for supervisor overrides

Provides endpoints for supervisor override management, approval workflows,
and regulatory compliance with proper authentication and validation.
"""

import logging
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from orm_calculator.models.override_models import (
    SupervisorOverride, OverrideAuditLog,
    SupervisorOverrideCreate, SupervisorOverrideResponse,
    OverrideApproval, OverrideApplication, OverrideImpactAnalysis,
    OverrideSearchRequest, OverrideSummary, OverrideValidationResult,
    OverrideType, OverrideStatus, OverrideReason
)
from orm_calculator.services.override_service import OverrideService, get_override_service
from orm_calculator.database.connection import get_db_session as get_database
from orm_calculator.security.auth import User, get_current_user
from orm_calculator.security.rbac import (
    Permission, require_permission, require_any_permission
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/overrides", tags=["supervisor-overrides"])


# Override Management Endpoints

@router.post("/", response_model=SupervisorOverrideResponse)
async def create_supervisor_override(
    override_data: SupervisorOverrideCreate,
    override_service: OverrideService = Depends(get_override_service),
    current_user: User = Depends(require_permission(Permission.CREATE_OVERRIDE))
):
    """
    Create a new supervisor override
    
    Requires CREATE_OVERRIDE permission (risk manager level or above).
    """
    try:
        # Set the proposer to current user
        override_data.proposed_by = current_user.username
        
        # Create override through service
        override = await override_service.create_override(override_data)
        
        logger.info(f"Created supervisor override {override.id} by user {current_user.username}")
        return SupervisorOverrideResponse.model_validate(override)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "OVERRIDE_VALIDATION_FAILED",
                "error_message": str(e),
                "details": {"override_id": override_data.id}
            }
        )
    except Exception as e:
        logger.error(f"Failed to create supervisor override: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "OVERRIDE_CREATION_FAILED",
                "error_message": "Failed to create supervisor override",
                "details": {"error": str(e)}
            }
        )


@router.get("/{override_id}", response_model=SupervisorOverrideResponse)
async def get_supervisor_override(
    override_id: str,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_any_permission([
        Permission.READ_AUDIT, Permission.CREATE_OVERRIDE
    ]))
):
    """
    Get supervisor override by ID
    
    Requires READ_AUDIT or CREATE_OVERRIDE permission.
    """
    override = db.query(SupervisorOverride).filter(
        SupervisorOverride.id == override_id
    ).first()
    
    if not override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "OVERRIDE_NOT_FOUND",
                "error_message": f"Supervisor override {override_id} not found",
                "details": {"override_id": override_id}
            }
        )
    
    return SupervisorOverrideResponse.model_validate(override)


@router.get("/", response_model=List[SupervisorOverrideResponse])
async def search_supervisor_overrides(
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    override_type: Optional[OverrideType] = Query(None, description="Filter by override type"),
    status_filter: Optional[OverrideStatus] = Query(None, description="Filter by status"),
    effective_date_from: Optional[date] = Query(None, description="Filter by effective date from"),
    effective_date_to: Optional[date] = Query(None, description="Filter by effective date to"),
    proposed_by: Optional[str] = Query(None, description="Filter by proposer"),
    approved_by: Optional[str] = Query(None, description="Filter by approver"),
    requires_disclosure: Optional[bool] = Query(None, description="Filter by disclosure requirement"),
    override_service: OverrideService = Depends(get_override_service),
    current_user: User = Depends(require_permission(Permission.READ_AUDIT))
):
    """
    Search supervisor overrides with optional filtering
    
    Requires READ_AUDIT permission.
    """
    search_request = OverrideSearchRequest(
        entity_id=entity_id,
        override_type=override_type,
        status=status_filter,
        effective_date_from=effective_date_from,
        effective_date_to=effective_date_to,
        proposed_by=proposed_by,
        approved_by=approved_by,
        requires_disclosure=requires_disclosure
    )
    
    overrides = await override_service.search_overrides(search_request)
    return [SupervisorOverrideResponse.model_validate(override) for override in overrides]


@router.put("/{override_id}/approve", response_model=SupervisorOverrideResponse)
async def approve_supervisor_override(
    override_id: str,
    approval: OverrideApproval,
    override_service: OverrideService = Depends(get_override_service),
    current_user: User = Depends(require_permission(Permission.APPROVE_OVERRIDE))
):
    """
    Approve a supervisor override
    
    Requires APPROVE_OVERRIDE permission (model risk manager level or above).
    """
    try:
        # Set the approver to current user
        approval.approved_by = current_user.username
        
        # Approve override through service
        override = await override_service.approve_override(override_id, approval)
        
        logger.info(f"Approved supervisor override {override_id} by user {current_user.username}")
        return SupervisorOverrideResponse.model_validate(override)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "OVERRIDE_APPROVAL_FAILED",
                "error_message": str(e),
                "details": {"override_id": override_id}
            }
        )
    except Exception as e:
        logger.error(f"Failed to approve supervisor override: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "APPROVAL_FAILED",
                "error_message": "Failed to approve supervisor override",
                "details": {"error": str(e)}
            }
        )


@router.put("/{override_id}/apply", response_model=SupervisorOverrideResponse)
async def apply_supervisor_override(
    override_id: str,
    application: OverrideApplication,
    override_service: OverrideService = Depends(get_override_service),
    current_user: User = Depends(require_permission(Permission.CREATE_OVERRIDE))
):
    """
    Apply an approved supervisor override
    
    Requires CREATE_OVERRIDE permission.
    """
    try:
        # Set the applicant to current user
        application.applied_by = current_user.username
        
        # Apply override through service
        override = await override_service.apply_override(override_id, application)
        
        logger.info(f"Applied supervisor override {override_id} by user {current_user.username}")
        return SupervisorOverrideResponse.model_validate(override)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "OVERRIDE_APPLICATION_FAILED",
                "error_message": str(e),
                "details": {"override_id": override_id}
            }
        )
    except Exception as e:
        logger.error(f"Failed to apply supervisor override: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "APPLICATION_FAILED",
                "error_message": "Failed to apply supervisor override",
                "details": {"error": str(e)}
            }
        )


@router.put("/{override_id}/reject", response_model=SupervisorOverrideResponse)
async def reject_supervisor_override(
    override_id: str,
    rejection_reason: str,
    override_service: OverrideService = Depends(get_override_service),
    current_user: User = Depends(require_permission(Permission.APPROVE_OVERRIDE))
):
    """
    Reject a supervisor override
    
    Requires APPROVE_OVERRIDE permission.
    """
    try:
        # Reject override through service
        override = await override_service.reject_override(
            override_id, current_user.username, rejection_reason
        )
        
        logger.info(f"Rejected supervisor override {override_id} by user {current_user.username}")
        return SupervisorOverrideResponse.model_validate(override)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "OVERRIDE_REJECTION_FAILED",
                "error_message": str(e),
                "details": {"override_id": override_id}
            }
        )
    except Exception as e:
        logger.error(f"Failed to reject supervisor override: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "REJECTION_FAILED",
                "error_message": "Failed to reject supervisor override",
                "details": {"error": str(e)}
            }
        )


# Override Analysis Endpoints

@router.get("/{override_id}/impact", response_model=OverrideImpactAnalysis)
async def analyze_override_impact(
    override_id: str,
    calculation_date: date = Query(..., description="Date for impact analysis"),
    override_service: OverrideService = Depends(get_override_service),
    current_user: User = Depends(require_permission(Permission.READ_AUDIT))
):
    """
    Analyze the impact of a supervisor override
    
    Requires READ_AUDIT permission.
    """
    try:
        impact_analysis = await override_service.analyze_override_impact(
            override_id, calculation_date
        )
        
        return impact_analysis
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "OVERRIDE_NOT_FOUND",
                "error_message": str(e),
                "details": {"override_id": override_id}
            }
        )
    except Exception as e:
        logger.error(f"Failed to analyze override impact: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "IMPACT_ANALYSIS_FAILED",
                "error_message": "Failed to analyze override impact",
                "details": {"error": str(e)}
            }
        )


@router.get("/entity/{entity_id}/active")
async def get_active_overrides(
    entity_id: str,
    calculation_date: date = Query(default_factory=date.today, description="Date for active overrides"),
    override_service: OverrideService = Depends(get_override_service),
    current_user: User = Depends(require_permission(Permission.READ_AUDIT))
):
    """
    Get active overrides for entity on specific date
    
    Requires READ_AUDIT permission.
    """
    try:
        active_overrides = await override_service.get_active_overrides(entity_id, calculation_date)
        
        return [SupervisorOverrideResponse.model_validate(override) for override in active_overrides]
        
    except Exception as e:
        logger.error(f"Failed to get active overrides: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "ACTIVE_OVERRIDES_FAILED",
                "error_message": "Failed to get active overrides",
                "details": {"error": str(e)}
            }
        )


# Override Statistics and Reporting

@router.get("/summary/statistics", response_model=OverrideSummary)
async def get_override_summary(
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    override_service: OverrideService = Depends(get_override_service),
    current_user: User = Depends(require_permission(Permission.READ_AUDIT))
):
    """
    Get override summary statistics
    
    Requires READ_AUDIT permission.
    """
    try:
        summary = await override_service.get_override_summary(entity_id)
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get override summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "SUMMARY_FAILED",
                "error_message": "Failed to get override summary",
                "details": {"error": str(e)}
            }
        )


@router.get("/{override_id}/audit-trail")
async def get_override_audit_trail(
    override_id: str,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_permission(Permission.READ_AUDIT))
):
    """
    Get audit trail for supervisor override
    
    Requires READ_AUDIT permission.
    """
    # Check if override exists
    override = db.query(SupervisorOverride).filter(
        SupervisorOverride.id == override_id
    ).first()
    
    if not override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "OVERRIDE_NOT_FOUND",
                "error_message": f"Supervisor override {override_id} not found",
                "details": {"override_id": override_id}
            }
        )
    
    # Get audit logs
    audit_logs = db.query(OverrideAuditLog).filter(
        OverrideAuditLog.override_id == override_id
    ).order_by(OverrideAuditLog.action_date.desc()).all()
    
    return {
        "override_id": override_id,
        "audit_trail": [
            {
                "id": log.id,
                "action_type": log.action_type,
                "action_by": log.action_by,
                "action_date": log.action_date,
                "previous_status": log.previous_status,
                "new_status": log.new_status,
                "changes_made": log.changes_made,
                "reason": log.reason,
                "system_context": log.system_context
            }
            for log in audit_logs
        ]
    }


# Administrative Endpoints

@router.post("/expire-overrides")
async def expire_overrides(
    override_service: OverrideService = Depends(get_override_service),
    current_user: User = Depends(require_permission(Permission.MANAGE_SYSTEM))
):
    """
    Expire overrides that have passed their effective_to date
    
    Requires MANAGE_SYSTEM permission (system administrator).
    """
    try:
        expired_ids = await override_service.expire_overrides()
        
        return {
            "expired_count": len(expired_ids),
            "expired_override_ids": expired_ids,
            "processed_by": current_user.username,
            "processed_at": date.today().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to expire overrides: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "EXPIRY_FAILED",
                "error_message": "Failed to expire overrides",
                "details": {"error": str(e)}
            }
        )


# Validation Endpoints

@router.post("/validate", response_model=OverrideValidationResult)
async def validate_override(
    override_data: SupervisorOverrideCreate,
    override_service: OverrideService = Depends(get_override_service),
    current_user: User = Depends(require_permission(Permission.CREATE_OVERRIDE))
):
    """
    Validate supervisor override data without creating it
    
    Requires CREATE_OVERRIDE permission.
    """
    try:
        validation_result = await override_service._validate_override(override_data)
        return validation_result
        
    except Exception as e:
        logger.error(f"Failed to validate override: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "VALIDATION_FAILED",
                "error_message": "Failed to validate override",
                "details": {"error": str(e)}
            }
        )


# Reference Data Endpoints

@router.get("/reference/override-types")
async def get_override_types(
    current_user: User = Depends(get_current_user)
):
    """
    Get available override types
    
    Requires authentication.
    """
    return {
        "override_types": [
            {
                "value": override_type.value,
                "description": override_type.value.replace("_", " ").title()
            }
            for override_type in OverrideType
        ]
    }


@router.get("/reference/override-reasons")
async def get_override_reasons(
    current_user: User = Depends(get_current_user)
):
    """
    Get available override reasons
    
    Requires authentication.
    """
    return {
        "override_reasons": [
            {
                "value": reason.value,
                "description": reason.value.replace("_", " ").title()
            }
            for reason in OverrideReason
        ]
    }


@router.get("/reference/override-statuses")
async def get_override_statuses(
    current_user: User = Depends(get_current_user)
):
    """
    Get available override statuses
    
    Requires authentication.
    """
    return {
        "override_statuses": [
            {
                "value": status_val.value,
                "description": status_val.value.replace("_", " ").title()
            }
            for status_val in OverrideStatus
        ]
    }