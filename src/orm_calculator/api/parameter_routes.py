"""
Parameter Management API Routes for ORM Capital Calculator Engine

Implements parameter governance with Maker-Checker-Approver workflow
and version control for regulatory compliance.
"""

from datetime import date
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db_session
from ..services.parameter_service import ParameterService
from ..models.parameter_models import (
    ParameterChangeProposal, ParameterReview, ParameterApproval,
    ParameterVersionResponse, ParameterSetResponse, ParameterDiff,
    ParameterStatus, ParameterType
)
from ..models.auth_models import User, Permission
from ..services.auth_service import require_permission
from ..models.api_models import ErrorDetail, ErrorResponse


router = APIRouter(prefix="/api/v1/parameters", tags=["Parameter Management"])


def get_parameter_service(db: AsyncSession = Depends(get_db_session)) -> ParameterService:
    """Dependency to get parameter service"""
    return ParameterService(db)


@router.get("/{model_name}", response_model=ParameterSetResponse)
async def get_active_parameters(
    model_name: str,
    parameter_service: ParameterService = Depends(get_parameter_service),
    current_user: User = Depends(require_permission(Permission.READ_PARAMETERS))
):
    """
    Get current active parameter values for a model
    
    Returns the currently active parameter set for the specified model.
    Requires READ_PARAMETERS permission (risk analyst level or above).
    
    Args:
        model_name: Model name (SMA, BIA, TSA)
    
    Returns:
        Active parameter set with version information
    """
    try:
        # Validate model name
        valid_models = ["SMA", "BIA", "TSA"]
        if model_name.upper() not in valid_models:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model name. Must be one of: {', '.join(valid_models)}"
            )
        
        parameters = await parameter_service.get_active_parameters(model_name.upper())
        
        # Get configuration info (simplified for now)
        return ParameterSetResponse(
            model_name=model_name.upper(),
            version_id="current",
            parameters=parameters,
            effective_date=date.today(),
            activated_by="system",
            activated_at=date.today()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve parameters: {str(e)}"
        )


@router.post("/{model_name}/propose", response_model=Dict[str, str])
async def propose_parameter_change(
    model_name: str,
    proposal: ParameterChangeProposal,
    parameter_service: ParameterService = Depends(get_parameter_service),
    current_user: User = Depends(require_permission(Permission.PROPOSE_PARAMETERS))
):
    """
    Propose a parameter change (Maker step)
    
    Initiates the maker-checker-approver workflow for parameter changes.
    Requires PROPOSE_PARAMETERS permission (parameter analyst level or above).
    
    Args:
        model_name: Model name (SMA, BIA, TSA)
        proposal: Parameter change proposal details
    
    Returns:
        Workflow ID for tracking the proposal
    """
    try:
        # Validate model name matches proposal
        if model_name.upper() != proposal.model_name.upper():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Model name in URL must match proposal model name"
            )
        
        # Ensure model name is uppercase
        proposal.model_name = model_name.upper()
        
        workflow_id = await parameter_service.propose_parameter_change(
            proposal, current_user.username
        )
        
        return {
            "workflow_id": workflow_id,
            "status": "proposed",
            "message": f"Parameter change proposed for {proposal.parameter_name}. Workflow ID: {workflow_id}"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to propose parameter change: {str(e)}"
        )


@router.post("/review", response_model=Dict[str, str])
async def review_parameter_change(
    review: ParameterReview,
    parameter_service: ParameterService = Depends(get_parameter_service),
    current_user: User = Depends(require_permission(Permission.REVIEW_PARAMETERS))
):
    """
    Review a parameter change (Checker step)
    
    Reviews a proposed parameter change and either approves it for final approval
    or rejects it. Requires REVIEW_PARAMETERS permission (senior analyst level or above).
    
    Args:
        review: Parameter review details
    
    Returns:
        Review status and next steps
    """
    try:
        await parameter_service.review_parameter_change(review, current_user.username)
        
        action_message = "approved for final approval" if review.action == "approve" else "rejected"
        
        return {
            "workflow_id": review.workflow_id,
            "status": "reviewed",
            "action": review.action,
            "message": f"Parameter change {action_message} by {current_user.username}"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review parameter change: {str(e)}"
        )


@router.post("/approve", response_model=Dict[str, str])
async def approve_parameter_change(
    approval: ParameterApproval,
    parameter_service: ParameterService = Depends(get_parameter_service),
    current_user: User = Depends(require_permission(Permission.APPROVE_PARAMETERS))
):
    """
    Approve a parameter change (Approver step)
    
    Final approval step for parameter changes. Once approved, the parameter
    can be activated. Requires APPROVE_PARAMETERS permission (model risk manager level).
    
    Args:
        approval: Parameter approval details
    
    Returns:
        Approval status and activation instructions
    """
    try:
        await parameter_service.approve_parameter_change(approval, current_user.username)
        
        action_message = "approved and ready for activation" if approval.action == "approve" else "rejected"
        
        return {
            "workflow_id": approval.workflow_id,
            "status": "final_approval_completed",
            "action": approval.action,
            "message": f"Parameter change {action_message} by {current_user.username}",
            "next_step": "activate" if approval.action == "approve" else "workflow_completed"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve parameter change: {str(e)}"
        )


@router.post("/activate/{workflow_id}", response_model=Dict[str, str])
async def activate_parameter_change(
    workflow_id: str,
    parameter_service: ParameterService = Depends(get_parameter_service),
    current_user: User = Depends(require_permission(Permission.ACTIVATE_PARAMETERS))
):
    """
    Activate an approved parameter change
    
    Activates an approved parameter change, making it the current active version.
    Requires ACTIVATE_PARAMETERS permission (system administrator level).
    
    Args:
        workflow_id: Workflow ID of the approved parameter change
    
    Returns:
        Activation status and version information
    """
    try:
        version_id = await parameter_service.activate_parameter_change(
            workflow_id, current_user.username
        )
        
        return {
            "workflow_id": workflow_id,
            "version_id": version_id,
            "status": "activated",
            "message": f"Parameter change activated by {current_user.username}. Version ID: {version_id}",
            "activated_by": current_user.username
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate parameter change: {str(e)}"
        )


@router.get("/{model_name}/history", response_model=List[ParameterVersionResponse])
async def get_parameter_history(
    model_name: str,
    parameter_name: Optional[str] = Query(None, description="Optional specific parameter name"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of versions to return"),
    parameter_service: ParameterService = Depends(get_parameter_service),
    current_user: User = Depends(require_permission(Permission.READ_AUDIT))
):
    """
    Get parameter version history
    
    Returns the version history for parameters in the specified model.
    Requires READ_AUDIT permission (auditor level or above).
    
    Args:
        model_name: Model name (SMA, BIA, TSA)
        parameter_name: Optional specific parameter name filter
        limit: Maximum number of versions to return
    
    Returns:
        List of parameter versions with change history
    """
    try:
        # Validate model name
        valid_models = ["SMA", "BIA", "TSA"]
        if model_name.upper() not in valid_models:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model name. Must be one of: {', '.join(valid_models)}"
            )
        
        history = await parameter_service.get_parameter_history(
            model_name.upper(), parameter_name
        )
        
        # Apply limit
        return history[:limit]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve parameter history: {str(e)}"
        )


@router.get("/version/{version_id}", response_model=ParameterVersionResponse)
async def get_parameter_version(
    version_id: str,
    parameter_service: ParameterService = Depends(get_parameter_service),
    current_user: User = Depends(require_permission(Permission.READ_PARAMETERS))
):
    """
    Get specific parameter version details
    
    Returns detailed information about a specific parameter version.
    Requires READ_PARAMETERS permission (risk analyst level or above).
    
    Args:
        version_id: Parameter version ID
    
    Returns:
        Parameter version details
    """
    try:
        version = await parameter_service.get_parameter_version(version_id)
        
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parameter version {version_id} not found"
            )
        
        return ParameterVersionResponse(
            id=version.id,
            version_id=version.version_id,
            model_name=version.model_name,
            parameter_name=version.parameter_name,
            parameter_type=version.parameter_type,
            parameter_category=version.parameter_category,
            parameter_value=version.parameter_value,
            version_number=version.version_number,
            status=version.status,
            effective_date=version.effective_date,
            created_by=version.created_by,
            change_reason=version.change_reason,
            created_at=version.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve parameter version: {str(e)}"
        )


@router.post("/{model_name}/validate", response_model=Dict[str, Any])
async def validate_parameters(
    model_name: str,
    parameters: Dict[str, Any],
    parameter_service: ParameterService = Depends(get_parameter_service),
    current_user: User = Depends(require_permission(Permission.READ_PARAMETERS))
):
    """
    Validate parameter values
    
    Validates a set of parameters against business rules and regulatory requirements.
    Requires READ_PARAMETERS permission (risk analyst level or above).
    
    Args:
        model_name: Model name (SMA, BIA, TSA)
        parameters: Parameter dictionary to validate
    
    Returns:
        Validation results with errors and warnings
    """
    try:
        # Validate model name
        valid_models = ["SMA", "BIA", "TSA"]
        if model_name.upper() not in valid_models:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model name. Must be one of: {', '.join(valid_models)}"
            )
        
        errors = parameter_service.validate_parameters(model_name.upper(), parameters)
        
        return {
            "model_name": model_name.upper(),
            "is_valid": len(errors) == 0,
            "validation_errors": errors,
            "parameter_count": len(parameters),
            "validated_by": current_user.username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate parameters: {str(e)}"
        )


@router.post("/{model_name}/impact-analysis", response_model=Dict[str, Any])
async def analyze_parameter_impact(
    model_name: str,
    parameter_name: str,
    current_value: Any,
    proposed_value: Any,
    parameter_service: ParameterService = Depends(get_parameter_service),
    current_user: User = Depends(require_permission(Permission.REVIEW_PARAMETERS))
):
    """
    Analyze impact of parameter change
    
    Provides impact analysis for a proposed parameter change including
    validation results and change magnitude assessment.
    Requires REVIEW_PARAMETERS permission (senior analyst level or above).
    
    Args:
        model_name: Model name (SMA, BIA, TSA)
        parameter_name: Parameter name being changed
        current_value: Current parameter value
        proposed_value: Proposed new value
    
    Returns:
        Impact analysis results
    """
    try:
        # Validate model name
        valid_models = ["SMA", "BIA", "TSA"]
        if model_name.upper() not in valid_models:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model name. Must be one of: {', '.join(valid_models)}"
            )
        
        # Get current parameters for context
        current_parameters = await parameter_service.get_active_parameters(model_name.upper())
        
        # Perform impact analysis using validation service
        is_valid, validation_messages = parameter_service.validation_service.validate_parameter_change(
            model_name.upper(),
            parameter_name,
            current_value,
            proposed_value,
            current_parameters
        )
        
        # Categorize messages by severity
        errors = [str(msg) for msg in validation_messages if msg.severity.value == "error"]
        warnings = [str(msg) for msg in validation_messages if msg.severity.value == "warning"]
        info = [str(msg) for msg in validation_messages if msg.severity.value == "info"]
        
        return {
            "model_name": model_name.upper(),
            "parameter_name": parameter_name,
            "current_value": current_value,
            "proposed_value": proposed_value,
            "is_valid": is_valid,
            "impact_assessment": {
                "errors": errors,
                "warnings": warnings,
                "information": info
            },
            "recommendation": "approve" if is_valid and len(warnings) == 0 else "review_required",
            "analyzed_by": current_user.username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze parameter impact: {str(e)}"
        )


@router.post("/rollback/{version_id}", response_model=Dict[str, str])
async def rollback_parameter(
    version_id: str,
    rollback_reason: str,
    parameter_service: ParameterService = Depends(get_parameter_service),
    current_user: User = Depends(require_permission(Permission.ACTIVATE_PARAMETERS))
):
    """
    Rollback to a previous parameter version
    
    Creates a new parameter change proposal to rollback to a previous version.
    This maintains the audit trail while reverting to a known good state.
    Requires ACTIVATE_PARAMETERS permission (system administrator level).
    
    Args:
        version_id: Version ID to rollback to
        rollback_reason: Reason for rollback
    
    Returns:
        Rollback workflow information
    """
    try:
        # Get the target version
        target_version = await parameter_service.get_parameter_version(version_id)
        
        if not target_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parameter version {version_id} not found"
            )
        
        # Get current active parameters
        current_parameters = await parameter_service.get_active_parameters(target_version.model_name)
        current_value = current_parameters.get(target_version.parameter_name)
        
        # Create rollback proposal
        rollback_proposal = ParameterChangeProposal(
            model_name=target_version.model_name,
            parameter_name=target_version.parameter_name,
            parameter_type=target_version.parameter_type,
            parameter_category=target_version.parameter_category,
            current_value=current_value,
            proposed_value=target_version.parameter_value,
            effective_date=date.today(),
            change_reason=f"ROLLBACK: {rollback_reason}",
            business_justification=f"Rollback to version {version_id} due to: {rollback_reason}",
            requires_rbi_approval=target_version.requires_rbi_approval,
            disclosure_required=True  # Rollbacks always require disclosure
        )
        
        workflow_id = await parameter_service.propose_parameter_change(
            rollback_proposal, current_user.username
        )
        
        return {
            "workflow_id": workflow_id,
            "target_version_id": version_id,
            "status": "rollback_proposed",
            "message": f"Rollback to version {version_id} proposed. Workflow ID: {workflow_id}",
            "note": "Rollback proposal created - requires standard approval workflow"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate parameter rollback: {str(e)}"
        )