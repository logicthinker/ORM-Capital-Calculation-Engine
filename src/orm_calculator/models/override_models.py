"""
Supervisor override models for ORM Capital Calculator Engine

Provides models for managing supervisor overrides with structured reasons,
approver tracking, and disclosure requirements for regulatory compliance.
"""

from datetime import date, datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from decimal import Decimal
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Numeric, Date, JSON, Integer
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, field_validator

from orm_calculator.models.orm_models import Base


class OverrideType(str, Enum):
    """Types of supervisor overrides"""
    CAPITAL_ADJUSTMENT = "capital_adjustment"
    ILM_OVERRIDE = "ilm_override"
    BIC_OVERRIDE = "bic_override"
    LOSS_COMPONENT_OVERRIDE = "loss_component_override"
    METHODOLOGY_OVERRIDE = "methodology_override"
    PARAMETER_OVERRIDE = "parameter_override"


class OverrideStatus(str, Enum):
    """Status of supervisor overrides"""
    PROPOSED = "proposed"
    APPROVED = "approved"
    APPLIED = "applied"
    EXPIRED = "expired"
    REJECTED = "rejected"


class OverrideReason(str, Enum):
    """Standardized override reasons"""
    DATA_QUALITY_ISSUE = "data_quality_issue"
    EXCEPTIONAL_CIRCUMSTANCES = "exceptional_circumstances"
    REGULATORY_GUIDANCE = "regulatory_guidance"
    BUSINESS_RESTRUCTURING = "business_restructuring"
    SYSTEM_LIMITATION = "system_limitation"
    CONSERVATIVE_ADJUSTMENT = "conservative_adjustment"
    TEMPORARY_ADJUSTMENT = "temporary_adjustment"
    OTHER = "other"


# SQLAlchemy ORM Models

class SupervisorOverride(Base):
    """Supervisor override model for capital calculation adjustments"""
    __tablename__ = "supervisor_overrides"
    
    id = Column(String, primary_key=True)
    override_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default=OverrideStatus.PROPOSED)
    
    # Target information
    entity_id = Column(String, nullable=False)
    calculation_run_id = Column(String, nullable=True)  # Optional link to specific calculation
    
    # Override details
    original_value = Column(Numeric(precision=15, scale=2), nullable=True)
    override_value = Column(Numeric(precision=15, scale=2), nullable=False)
    percentage_adjustment = Column(Numeric(precision=5, scale=2), nullable=True)
    
    # Justification and approval
    override_reason = Column(String, nullable=False)
    detailed_justification = Column(Text, nullable=False)
    supporting_documentation = Column(JSON, nullable=True)
    
    # Approver information
    proposed_by = Column(String, nullable=False)
    approved_by = Column(String, nullable=True)
    approval_date = Column(Date, nullable=True)
    approval_reference = Column(String, nullable=True)
    
    # Effective period
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    
    # Regulatory and disclosure
    requires_disclosure = Column(Boolean, default=True)
    disclosure_period_months = Column(Integer, default=12)
    rbi_notification_required = Column(Boolean, default=True)
    rbi_notification_date = Column(Date, nullable=True)
    rbi_notification_reference = Column(String, nullable=True)
    
    # Application tracking
    applied_date = Column(Date, nullable=True)
    applied_by = Column(String, nullable=True)
    application_details = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional context
    business_context = Column(Text, nullable=True)
    risk_assessment = Column(Text, nullable=True)
    impact_analysis = Column(JSON, nullable=True)


class OverrideAuditLog(Base):
    """Audit log for supervisor override actions"""
    __tablename__ = "override_audit_logs"
    
    id = Column(String, primary_key=True)
    override_id = Column(String, ForeignKey("supervisor_overrides.id"), nullable=False)
    
    # Action details
    action_type = Column(String, nullable=False)  # created, approved, applied, expired, etc.
    action_by = Column(String, nullable=False)
    action_date = Column(DateTime, default=datetime.utcnow)
    
    # Change tracking
    previous_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    changes_made = Column(JSON, nullable=True)
    
    # Context
    reason = Column(Text, nullable=True)
    system_context = Column(JSON, nullable=True)
    
    # Relationships
    override = relationship("SupervisorOverride", backref="audit_logs")


# Pydantic Models for API

class SupervisorOverrideCreate(BaseModel):
    """Model for creating supervisor overrides"""
    id: str = Field(..., description="Unique override identifier")
    override_type: OverrideType = Field(..., description="Type of override")
    entity_id: str = Field(..., description="Target entity ID")
    calculation_run_id: Optional[str] = Field(None, description="Specific calculation run ID")
    original_value: Optional[Decimal] = Field(None, description="Original calculated value")
    override_value: Decimal = Field(..., description="Override value")
    percentage_adjustment: Optional[Decimal] = Field(None, description="Percentage adjustment")
    override_reason: OverrideReason = Field(..., description="Standardized override reason")
    detailed_justification: str = Field(..., description="Detailed justification")
    supporting_documentation: Optional[Dict[str, Any]] = Field(None, description="Supporting documents")
    proposed_by: str = Field(..., description="User proposing the override")
    effective_from: date = Field(..., description="Effective from date")
    effective_to: Optional[date] = Field(None, description="Effective to date")
    business_context: Optional[str] = Field(None, description="Business context")
    risk_assessment: Optional[str] = Field(None, description="Risk assessment")
    
    @field_validator('percentage_adjustment')
    @classmethod
    def validate_percentage_adjustment(cls, v):
        if v is not None and (v < -100 or v > 1000):
            raise ValueError('Percentage adjustment must be between -100% and 1000%')
        return v
    
    @field_validator('effective_to')
    @classmethod
    def validate_effective_dates(cls, v, info):
        if v is not None and 'effective_from' in info.data:
            if v <= info.data['effective_from']:
                raise ValueError('Effective to date must be after effective from date')
        return v


class SupervisorOverrideResponse(BaseModel):
    """Model for supervisor override API responses"""
    id: str
    override_type: OverrideType
    status: OverrideStatus
    entity_id: str
    calculation_run_id: Optional[str]
    original_value: Optional[Decimal]
    override_value: Decimal
    percentage_adjustment: Optional[Decimal]
    override_reason: OverrideReason
    detailed_justification: str
    supporting_documentation: Optional[Dict[str, Any]]
    proposed_by: str
    approved_by: Optional[str]
    approval_date: Optional[date]
    approval_reference: Optional[str]
    effective_from: date
    effective_to: Optional[date]
    requires_disclosure: bool
    disclosure_period_months: int
    rbi_notification_required: bool
    rbi_notification_date: Optional[date]
    rbi_notification_reference: Optional[str]
    applied_date: Optional[date]
    applied_by: Optional[str]
    business_context: Optional[str]
    risk_assessment: Optional[str]
    impact_analysis: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OverrideApproval(BaseModel):
    """Model for override approval"""
    approved_by: str = Field(..., description="Approver user ID")
    approval_reference: str = Field(..., description="Approval reference number")
    approval_comments: Optional[str] = Field(None, description="Approval comments")
    rbi_notification_reference: Optional[str] = Field(None, description="RBI notification reference")


class OverrideApplication(BaseModel):
    """Model for override application"""
    applied_by: str = Field(..., description="User applying the override")
    application_comments: Optional[str] = Field(None, description="Application comments")
    calculation_impact: Optional[Dict[str, Any]] = Field(None, description="Calculation impact details")


class OverrideImpactAnalysis(BaseModel):
    """Model for override impact analysis"""
    override_id: str
    entity_id: str
    calculation_date: date
    original_calculation: Dict[str, Decimal]
    override_calculation: Dict[str, Decimal]
    impact_summary: Dict[str, Decimal]
    percentage_impact: Dict[str, Decimal]
    disclosure_requirements: List[str]
    regulatory_implications: List[str]


class OverrideSearchRequest(BaseModel):
    """Model for override search requests"""
    entity_id: Optional[str] = Field(None, description="Filter by entity ID")
    override_type: Optional[OverrideType] = Field(None, description="Filter by override type")
    status: Optional[OverrideStatus] = Field(None, description="Filter by status")
    effective_date_from: Optional[date] = Field(None, description="Filter by effective date from")
    effective_date_to: Optional[date] = Field(None, description="Filter by effective date to")
    proposed_by: Optional[str] = Field(None, description="Filter by proposer")
    approved_by: Optional[str] = Field(None, description="Filter by approver")
    requires_disclosure: Optional[bool] = Field(None, description="Filter by disclosure requirement")


class OverrideSummary(BaseModel):
    """Model for override summary statistics"""
    total_overrides: int
    active_overrides: int
    pending_approval: int
    expired_overrides: int
    by_type: Dict[str, int]
    by_entity: Dict[str, int]
    total_impact_amount: Decimal
    average_impact_percentage: Decimal
    disclosure_items: int


class OverrideValidationResult(BaseModel):
    """Model for override validation results"""
    is_valid: bool
    validation_errors: List[str]
    validation_warnings: List[str]
    business_rule_violations: List[str]
    regulatory_concerns: List[str]
    recommended_actions: List[str]