"""
API routes for consolidation and corporate actions

Provides endpoints for entity hierarchy management, consolidation calculations,
and corporate action processing with proper authentication and validation.
"""

import logging
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from orm_calculator.models.entity_models import (
    Entity, CorporateAction, ConsolidationMapping,
    EntityCreate, EntityResponse, CorporateActionCreate, CorporateActionResponse,
    ConsolidationMappingCreate, ConsolidationMappingResponse,
    EntityHierarchy, ConsolidationRequest, ConsolidationResult,
    CorporateActionStatus
)
from orm_calculator.services.consolidation_service import ConsolidationService, get_consolidation_service
from orm_calculator.database.connection import get_db_session as get_database
from orm_calculator.security.auth import User, get_current_user
from orm_calculator.security.rbac import (
    Permission, require_permission, require_any_permission
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/consolidation", tags=["consolidation"])


# Entity Management Endpoints

@router.post("/entities", response_model=EntityResponse)
async def create_entity(
    entity_data: EntityCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_permission(Permission.WRITE_BI_DATA))
):
    """
    Create a new entity in the organizational hierarchy
    
    Requires WRITE_BI_DATA permission for corporate finance analysts.
    """
    try:
        # Check if entity already exists
        existing_entity = db.query(Entity).filter(Entity.id == entity_data.id).first()
        if existing_entity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_code": "ENTITY_EXISTS",
                    "error_message": f"Entity with ID {entity_data.id} already exists",
                    "details": {"entity_id": entity_data.id}
                }
            )
        
        # Validate parent entity exists if specified
        if entity_data.parent_entity_id:
            parent_entity = db.query(Entity).filter(
                Entity.id == entity_data.parent_entity_id
            ).first()
            if not parent_entity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "PARENT_ENTITY_NOT_FOUND",
                        "error_message": f"Parent entity {entity_data.parent_entity_id} not found",
                        "details": {"parent_entity_id": entity_data.parent_entity_id}
                    }
                )
        
        # Create entity
        entity = Entity(**entity_data.model_dump())
        db.add(entity)
        db.commit()
        db.refresh(entity)
        
        logger.info(f"Created entity {entity.id} by user {current_user.username}")
        return EntityResponse.model_validate(entity)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create entity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "ENTITY_CREATION_FAILED",
                "error_message": "Failed to create entity",
                "details": {"error": str(e)}
            }
        )


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: str,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_permission(Permission.READ_BI_DATA))
):
    """
    Get entity by ID
    
    Requires READ_BI_DATA permission.
    """
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "ENTITY_NOT_FOUND",
                "error_message": f"Entity {entity_id} not found",
                "details": {"entity_id": entity_id}
            }
        )
    
    return EntityResponse.model_validate(entity)


@router.get("/entities", response_model=List[EntityResponse])
async def list_entities(
    active_only: bool = Query(True, description="Return only active entities"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_permission(Permission.READ_BI_DATA))
):
    """
    List entities with optional filtering
    
    Requires READ_BI_DATA permission.
    """
    query = db.query(Entity)
    
    if active_only:
        query = query.filter(Entity.is_active == True)
    
    if entity_type:
        query = query.filter(Entity.entity_type == entity_type)
    
    entities = query.all()
    return [EntityResponse.model_validate(entity) for entity in entities]


@router.get("/entities/{entity_id}/hierarchy", response_model=EntityHierarchy)
async def get_entity_hierarchy(
    entity_id: str,
    consolidation_service: ConsolidationService = Depends(get_consolidation_service),
    current_user: User = Depends(require_permission(Permission.READ_BI_DATA))
):
    """
    Get complete entity hierarchy starting from specified entity
    
    Requires READ_BI_DATA permission.
    """
    hierarchy = await consolidation_service.get_entity_hierarchy(entity_id)
    if not hierarchy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "ENTITY_NOT_FOUND",
                "error_message": f"Entity {entity_id} not found",
                "details": {"entity_id": entity_id}
            }
        )
    
    return hierarchy


# Corporate Action Endpoints

@router.post("/corporate-actions", response_model=CorporateActionResponse)
async def create_corporate_action(
    action_data: CorporateActionCreate,
    consolidation_service: ConsolidationService = Depends(get_consolidation_service),
    current_user: User = Depends(require_permission(Permission.WRITE_BI_DATA))
):
    """
    Register a new corporate action
    
    Requires WRITE_BI_DATA permission for corporate finance analysts.
    """
    try:
        # Create corporate action entity
        action = CorporateAction(**action_data.model_dump())
        
        # Register through service (applies business rules)
        registered_action = await consolidation_service.register_corporate_action(action)
        
        logger.info(f"Created corporate action {action.id} by user {current_user.username}")
        return CorporateActionResponse.model_validate(registered_action)
        
    except Exception as e:
        logger.error(f"Failed to create corporate action: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "CORPORATE_ACTION_CREATION_FAILED",
                "error_message": "Failed to create corporate action",
                "details": {"error": str(e)}
            }
        )


@router.get("/corporate-actions/{action_id}", response_model=CorporateActionResponse)
async def get_corporate_action(
    action_id: str,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_permission(Permission.READ_BI_DATA))
):
    """
    Get corporate action by ID
    
    Requires READ_BI_DATA permission.
    """
    action = db.query(CorporateAction).filter(CorporateAction.id == action_id).first()
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "CORPORATE_ACTION_NOT_FOUND",
                "error_message": f"Corporate action {action_id} not found",
                "details": {"action_id": action_id}
            }
        )
    
    return CorporateActionResponse.model_validate(action)


@router.get("/corporate-actions", response_model=List[CorporateActionResponse])
async def list_corporate_actions(
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    status_filter: Optional[CorporateActionStatus] = Query(None, description="Filter by status"),
    effective_date_from: Optional[date] = Query(None, description="Filter by effective date from"),
    effective_date_to: Optional[date] = Query(None, description="Filter by effective date to"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_permission(Permission.READ_BI_DATA))
):
    """
    List corporate actions with optional filtering
    
    Requires READ_BI_DATA permission.
    """
    query = db.query(CorporateAction)
    
    if entity_id:
        query = query.filter(
            (CorporateAction.target_entity_id == entity_id) |
            (CorporateAction.acquirer_entity_id == entity_id)
        )
    
    if status_filter:
        query = query.filter(CorporateAction.status == status_filter)
    
    if effective_date_from:
        query = query.filter(CorporateAction.effective_date >= effective_date_from)
    
    if effective_date_to:
        query = query.filter(CorporateAction.effective_date <= effective_date_to)
    
    actions = query.order_by(CorporateAction.effective_date.desc()).all()
    return [CorporateActionResponse.model_validate(action) for action in actions]


@router.put("/corporate-actions/{action_id}/approve")
async def approve_corporate_action(
    action_id: str,
    rbi_approval_reference: str,
    approval_date: date,
    consolidation_service: ConsolidationService = Depends(get_consolidation_service),
    current_user: User = Depends(require_permission(Permission.APPROVE_PARAMETERS))
):
    """
    Approve corporate action with RBI reference
    
    Requires APPROVE_PARAMETERS permission (model risk manager level).
    """
    try:
        approved_action = await consolidation_service.approve_corporate_action(
            action_id, rbi_approval_reference, approval_date
        )
        
        logger.info(f"Approved corporate action {action_id} by user {current_user.username}")
        return CorporateActionResponse.model_validate(approved_action)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "CORPORATE_ACTION_NOT_FOUND",
                "error_message": str(e),
                "details": {"action_id": action_id}
            }
        )
    except Exception as e:
        logger.error(f"Failed to approve corporate action: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "APPROVAL_FAILED",
                "error_message": "Failed to approve corporate action",
                "details": {"error": str(e)}
            }
        )


@router.put("/corporate-actions/{action_id}/complete")
async def complete_corporate_action(
    action_id: str,
    completion_date: date,
    consolidation_service: ConsolidationService = Depends(get_consolidation_service),
    current_user: User = Depends(require_permission(Permission.WRITE_BI_DATA))
):
    """
    Mark corporate action as completed
    
    Requires WRITE_BI_DATA permission.
    """
    try:
        completed_action = await consolidation_service.complete_corporate_action(
            action_id, completion_date
        )
        
        logger.info(f"Completed corporate action {action_id} by user {current_user.username}")
        return CorporateActionResponse.model_validate(completed_action)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_ACTION_STATUS",
                "error_message": str(e),
                "details": {"action_id": action_id}
            }
        )
    except Exception as e:
        logger.error(f"Failed to complete corporate action: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "COMPLETION_FAILED",
                "error_message": "Failed to complete corporate action",
                "details": {"error": str(e)}
            }
        )


# Consolidation Calculation Endpoints

@router.post("/calculate", response_model=ConsolidationResult)
async def calculate_consolidated_capital(
    request: ConsolidationRequest,
    consolidation_service: ConsolidationService = Depends(get_consolidation_service),
    current_user: User = Depends(require_any_permission([
        Permission.CALCULATE_SMA,
        Permission.CALCULATE_BIA,
        Permission.CALCULATE_TSA
    ]))
):
    """
    Calculate consolidated capital at specified level
    
    Requires calculation permissions (risk analyst level or above).
    """
    try:
        result = await consolidation_service.calculate_consolidated_capital(request)
        
        logger.info(
            f"Calculated consolidated capital for entity {request.parent_entity_id} "
            f"at {request.consolidation_level} level by user {current_user.username}"
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_CONSOLIDATION_REQUEST",
                "error_message": str(e),
                "details": {"request": request.model_dump()}
            }
        )
    except Exception as e:
        logger.error(f"Failed to calculate consolidated capital: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "CONSOLIDATION_CALCULATION_FAILED",
                "error_message": "Failed to calculate consolidated capital",
                "details": {"error": str(e)}
            }
        )


# Consolidation Mapping Endpoints

@router.post("/mappings", response_model=ConsolidationMappingResponse)
async def create_consolidation_mapping(
    mapping_data: ConsolidationMappingCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(require_permission(Permission.WRITE_BI_DATA))
):
    """
    Create consolidation mapping between entities
    
    Requires WRITE_BI_DATA permission.
    """
    try:
        # Validate entities exist
        parent_entity = db.query(Entity).filter(Entity.id == mapping_data.parent_entity_id).first()
        child_entity = db.query(Entity).filter(Entity.id == mapping_data.child_entity_id).first()
        
        if not parent_entity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "PARENT_ENTITY_NOT_FOUND",
                    "error_message": f"Parent entity {mapping_data.parent_entity_id} not found",
                    "details": {"parent_entity_id": mapping_data.parent_entity_id}
                }
            )
        
        if not child_entity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "CHILD_ENTITY_NOT_FOUND",
                    "error_message": f"Child entity {mapping_data.child_entity_id} not found",
                    "details": {"child_entity_id": mapping_data.child_entity_id}
                }
            )
        
        # Create mapping
        mapping = ConsolidationMapping(**mapping_data.model_dump())
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        
        logger.info(f"Created consolidation mapping {mapping.id} by user {current_user.username}")
        return ConsolidationMappingResponse.model_validate(mapping)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create consolidation mapping: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "MAPPING_CREATION_FAILED",
                "error_message": "Failed to create consolidation mapping",
                "details": {"error": str(e)}
            }
        )


@router.get("/mappings", response_model=List[ConsolidationMappingResponse])
async def list_consolidation_mappings(
    parent_entity_id: Optional[str] = Query(None, description="Filter by parent entity"),
    child_entity_id: Optional[str] = Query(None, description="Filter by child entity"),
    active_only: bool = Query(True, description="Return only active mappings"),
    db: Session = Depends(get_database),
    current_user: User = Depends(require_permission(Permission.READ_BI_DATA))
):
    """
    List consolidation mappings with optional filtering
    
    Requires READ_BI_DATA permission.
    """
    query = db.query(ConsolidationMapping)
    
    if parent_entity_id:
        query = query.filter(ConsolidationMapping.parent_entity_id == parent_entity_id)
    
    if child_entity_id:
        query = query.filter(ConsolidationMapping.child_entity_id == child_entity_id)
    
    if active_only:
        query = query.filter(
            (ConsolidationMapping.effective_to.is_(None)) |
            (ConsolidationMapping.effective_to >= date.today())
        )
    
    mappings = query.all()
    return [ConsolidationMappingResponse.model_validate(mapping) for mapping in mappings]