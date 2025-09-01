"""
Entity hierarchy and corporate action models for ORM Capital Calculator Engine

Provides models for managing entity hierarchies, consolidation levels,
and corporate actions (acquisitions, divestitures) with disclosure tracking.
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Numeric, Date, JSON, Integer
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, field_validator

from orm_calculator.models.orm_models import Base


class ConsolidationLevel(str, Enum):
    """Consolidation levels for capital calculations"""
    CONSOLIDATED = "consolidated"
    SUB_CONSOLIDATED = "sub_consolidated"
    SUBSIDIARY = "subsidiary"


class CorporateActionType(str, Enum):
    """Types of corporate actions"""
    ACQUISITION = "acquisition"
    DIVESTITURE = "divestiture"
    MERGER = "merger"
    SPIN_OFF = "spin_off"
    RESTRUCTURING = "restructuring"


class CorporateActionStatus(str, Enum):
    """Status of corporate actions"""
    PROPOSED = "proposed"
    RBI_APPROVED = "rbi_approved"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# SQLAlchemy ORM Models

class Entity(Base):
    """Entity model for organizational hierarchy"""
    __tablename__ = "entities"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)  # bank, subsidiary, branch
    parent_entity_id = Column(String, ForeignKey("entities.id"), nullable=True)
    consolidation_level = Column(String, nullable=False, default=ConsolidationLevel.SUBSIDIARY)
    
    # Regulatory identifiers
    rbi_entity_code = Column(String, nullable=True)
    lei_code = Column(String, nullable=True)  # Legal Entity Identifier
    
    # Status and dates
    is_active = Column(Boolean, default=True)
    incorporation_date = Column(Date, nullable=True)
    regulatory_approval_date = Column(Date, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent_entity = relationship("Entity", remote_side=[id], back_populates="child_entities")
    child_entities = relationship("Entity", back_populates="parent_entity")
    corporate_actions_as_target = relationship("CorporateAction", foreign_keys="CorporateAction.target_entity_id", overlaps="target_entity")
    corporate_actions_as_acquirer = relationship("CorporateAction", foreign_keys="CorporateAction.acquirer_entity_id", overlaps="acquirer_entity")


class CorporateAction(Base):
    """Corporate action model for M&A events"""
    __tablename__ = "corporate_actions"
    
    id = Column(String, primary_key=True)
    action_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default=CorporateActionStatus.PROPOSED)
    
    # Entities involved
    target_entity_id = Column(String, ForeignKey("entities.id"), nullable=False)
    acquirer_entity_id = Column(String, ForeignKey("entities.id"), nullable=True)
    
    # Action details
    transaction_value = Column(Numeric(precision=15, scale=2), nullable=True)
    ownership_percentage = Column(Numeric(precision=5, scale=2), nullable=True)
    
    # Dates
    announcement_date = Column(Date, nullable=False)
    rbi_approval_date = Column(Date, nullable=True)
    completion_date = Column(Date, nullable=True)
    effective_date = Column(Date, nullable=False)  # For capital calculation purposes
    
    # Regulatory and disclosure
    rbi_approval_reference = Column(String, nullable=True)
    requires_pillar3_disclosure = Column(Boolean, default=True)
    disclosure_period_months = Column(Integer, default=36)  # 3 years
    
    # Business impact
    prior_bi_inclusion_required = Column(Boolean, default=False)
    bi_exclusion_required = Column(Boolean, default=False)
    
    # Metadata
    description = Column(Text, nullable=True)
    additional_details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    target_entity = relationship("Entity", foreign_keys=[target_entity_id], overlaps="corporate_actions_as_target")
    acquirer_entity = relationship("Entity", foreign_keys=[acquirer_entity_id], overlaps="corporate_actions_as_acquirer")


class ConsolidationMapping(Base):
    """Mapping for entity consolidation relationships"""
    __tablename__ = "consolidation_mappings"
    
    id = Column(String, primary_key=True)
    parent_entity_id = Column(String, ForeignKey("entities.id"), nullable=False)
    child_entity_id = Column(String, ForeignKey("entities.id"), nullable=False)
    consolidation_level = Column(String, nullable=False)
    
    # Consolidation parameters
    ownership_percentage = Column(Numeric(precision=5, scale=2), nullable=False)
    voting_control_percentage = Column(Numeric(precision=5, scale=2), nullable=True)
    consolidation_method = Column(String, nullable=False)  # full, proportional, equity
    
    # Effective periods
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent_entity = relationship("Entity", foreign_keys=[parent_entity_id])
    child_entity = relationship("Entity", foreign_keys=[child_entity_id])


# Pydantic Models for API

class EntityCreate(BaseModel):
    """Model for creating new entities"""
    id: str = Field(..., description="Unique entity identifier")
    name: str = Field(..., description="Entity name")
    entity_type: str = Field(..., description="Type of entity (bank, subsidiary, branch)")
    parent_entity_id: Optional[str] = Field(None, description="Parent entity ID for hierarchy")
    consolidation_level: ConsolidationLevel = Field(ConsolidationLevel.SUBSIDIARY, description="Consolidation level")
    rbi_entity_code: Optional[str] = Field(None, description="RBI entity code")
    lei_code: Optional[str] = Field(None, description="Legal Entity Identifier")
    incorporation_date: Optional[date] = Field(None, description="Date of incorporation")
    regulatory_approval_date: Optional[date] = Field(None, description="RBI approval date")


class EntityResponse(BaseModel):
    """Model for entity API responses"""
    id: str
    name: str
    entity_type: str
    parent_entity_id: Optional[str]
    consolidation_level: ConsolidationLevel
    rbi_entity_code: Optional[str]
    lei_code: Optional[str]
    is_active: bool
    incorporation_date: Optional[date]
    regulatory_approval_date: Optional[date]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CorporateActionCreate(BaseModel):
    """Model for creating corporate actions"""
    id: str = Field(..., description="Unique corporate action identifier")
    action_type: CorporateActionType = Field(..., description="Type of corporate action")
    target_entity_id: str = Field(..., description="Target entity ID")
    acquirer_entity_id: Optional[str] = Field(None, description="Acquirer entity ID")
    transaction_value: Optional[Decimal] = Field(None, description="Transaction value")
    ownership_percentage: Optional[Decimal] = Field(None, description="Ownership percentage")
    announcement_date: date = Field(..., description="Announcement date")
    effective_date: date = Field(..., description="Effective date for calculations")
    rbi_approval_reference: Optional[str] = Field(None, description="RBI approval reference")
    description: Optional[str] = Field(None, description="Action description")
    
    @field_validator('ownership_percentage')
    @classmethod
    def validate_ownership_percentage(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Ownership percentage must be between 0 and 100')
        return v


class CorporateActionResponse(BaseModel):
    """Model for corporate action API responses"""
    id: str
    action_type: CorporateActionType
    status: CorporateActionStatus
    target_entity_id: str
    acquirer_entity_id: Optional[str]
    transaction_value: Optional[Decimal]
    ownership_percentage: Optional[Decimal]
    announcement_date: date
    rbi_approval_date: Optional[date]
    completion_date: Optional[date]
    effective_date: date
    rbi_approval_reference: Optional[str]
    requires_pillar3_disclosure: bool
    disclosure_period_months: int
    prior_bi_inclusion_required: bool
    bi_exclusion_required: bool
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConsolidationMappingCreate(BaseModel):
    """Model for creating consolidation mappings"""
    id: str = Field(..., description="Unique mapping identifier")
    parent_entity_id: str = Field(..., description="Parent entity ID")
    child_entity_id: str = Field(..., description="Child entity ID")
    consolidation_level: ConsolidationLevel = Field(..., description="Consolidation level")
    ownership_percentage: Decimal = Field(..., description="Ownership percentage")
    voting_control_percentage: Optional[Decimal] = Field(None, description="Voting control percentage")
    consolidation_method: str = Field(..., description="Consolidation method")
    effective_from: date = Field(..., description="Effective from date")
    effective_to: Optional[date] = Field(None, description="Effective to date")
    
    @field_validator('ownership_percentage', 'voting_control_percentage')
    @classmethod
    def validate_percentages(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Percentage must be between 0 and 100')
        return v


class ConsolidationMappingResponse(BaseModel):
    """Model for consolidation mapping API responses"""
    id: str
    parent_entity_id: str
    child_entity_id: str
    consolidation_level: ConsolidationLevel
    ownership_percentage: Decimal
    voting_control_percentage: Optional[Decimal]
    consolidation_method: str
    effective_from: date
    effective_to: Optional[date]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EntityHierarchy(BaseModel):
    """Model for entity hierarchy representation"""
    entity: EntityResponse
    children: List['EntityHierarchy'] = []
    consolidation_mappings: List[ConsolidationMappingResponse] = []


class ConsolidationRequest(BaseModel):
    """Model for consolidation calculation requests"""
    parent_entity_id: str = Field(..., description="Parent entity for consolidation")
    consolidation_level: ConsolidationLevel = Field(..., description="Level of consolidation")
    calculation_date: date = Field(..., description="Date for calculation")
    include_subsidiaries: bool = Field(True, description="Include subsidiary entities")
    include_corporate_actions: bool = Field(True, description="Apply corporate action adjustments")


class ConsolidationResult(BaseModel):
    """Model for consolidation calculation results"""
    parent_entity_id: str
    consolidation_level: ConsolidationLevel
    calculation_date: date
    included_entities: List[str]
    excluded_entities: List[str]
    corporate_actions_applied: List[str]
    consolidated_bi: Decimal
    consolidated_losses: Decimal
    entity_contributions: Dict[str, Dict[str, Decimal]]
    disclosure_items: List[str]


# Update EntityHierarchy to handle forward references
EntityHierarchy.model_rebuild()