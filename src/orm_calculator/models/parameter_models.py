"""
Parameter management models for ORM Capital Calculator Engine

Implements parameter governance with Maker-Checker-Approver workflow
and version control for regulatory compliance.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import uuid4
from enum import Enum

from sqlalchemy import (
    Column, String, DateTime, Date, Boolean, Text, ForeignKey, 
    Numeric, Integer, Enum as SQLEnum, Index, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, ConfigDict


# Use the same Base as other models
from .orm_models import Base


class ParameterStatus(str, Enum):
    """Parameter change workflow status"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    REVIEWED = "reviewed"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class ParameterType(str, Enum):
    """Parameter type classification"""
    COEFFICIENT = "coefficient"
    THRESHOLD = "threshold"
    MULTIPLIER = "multiplier"
    FLAG = "flag"
    MAPPING = "mapping"
    FORMULA = "formula"


class ParameterVersion(Base):
    """
    Parameter version management with immutable history
    
    Stores all parameter versions with complete audit trail
    for regulatory compliance and reproducibility.
    """
    __tablename__ = "parameter_versions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    model_name: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # SMA, BIA, TSA
    
    # Parameter identification
    parameter_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    parameter_type: Mapped[ParameterType] = mapped_column(SQLEnum(ParameterType), nullable=False)
    parameter_category: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "marginal_coefficients"
    
    # Parameter value (stored as JSON for flexibility)
    parameter_value: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    previous_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Version control
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_version_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("parameter_versions.version_id"))
    
    # Workflow status
    status: Mapped[ParameterStatus] = mapped_column(SQLEnum(ParameterStatus), nullable=False, default=ParameterStatus.DRAFT)
    
    # Effective dates
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date)
    
    # Governance
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)  # Maker
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100))       # Checker
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))       # Approver
    
    # Change management
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    business_justification: Mapped[str] = mapped_column(Text, nullable=False)
    impact_assessment: Mapped[Optional[str]] = mapped_column(Text)
    
    # Audit trail
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Immutable diff for audit
    immutable_diff: Mapped[Optional[str]] = mapped_column(Text)  # JSON serialized diff
    
    # Regulatory flags
    requires_rbi_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    rbi_approval_reference: Mapped[Optional[str]] = mapped_column(String(100))
    disclosure_required: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    parent_version: Mapped[Optional["ParameterVersion"]] = relationship("ParameterVersion", remote_side=[version_id])
    workflow_history: Mapped[List["ParameterWorkflow"]] = relationship("ParameterWorkflow", back_populates="parameter_version")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_param_model_name', 'model_name', 'parameter_name'),
        Index('idx_param_status', 'status'),
        Index('idx_param_effective', 'effective_date'),
        Index('idx_param_version', 'version_number'),
    )


class ParameterWorkflow(Base):
    """
    Parameter change workflow tracking
    
    Tracks the complete workflow history for parameter changes
    including maker-checker-approver steps.
    """
    __tablename__ = "parameter_workflow"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    parameter_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("parameter_versions.version_id"), nullable=False)
    
    # Workflow step
    step_name: Mapped[str] = mapped_column(String(50), nullable=False)  # create, review, approve, activate
    step_status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending, completed, rejected
    
    # Actor information
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False)  # maker, checker, approver
    
    # Step details
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # create, submit, review, approve, reject
    comments: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    parameter_version: Mapped["ParameterVersion"] = relationship("ParameterVersion", back_populates="workflow_history")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_workflow_id', 'workflow_id'),
        Index('idx_workflow_status', 'step_status'),
        Index('idx_workflow_actor', 'actor'),
    )


class ParameterConfiguration(Base):
    """
    Current active parameter configuration
    
    Maintains the current active parameter set for each model
    with quick lookup for calculations.
    """
    __tablename__ = "parameter_configuration"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    model_name: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # Current active version
    active_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("parameter_versions.version_id"), nullable=False)
    
    # Configuration metadata
    configuration_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Activation details
    activated_by: Mapped[str] = mapped_column(String(100), nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Next scheduled version (for future activation)
    next_version_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("parameter_versions.version_id"))
    next_activation_date: Mapped[Optional[date]] = mapped_column(Date)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    active_version: Mapped["ParameterVersion"] = relationship("ParameterVersion", foreign_keys=[active_version_id])
    next_version: Mapped[Optional["ParameterVersion"]] = relationship("ParameterVersion", foreign_keys=[next_version_id])
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_config_model', 'model_name'),
        Index('idx_config_active', 'active_version_id'),
    )


# Pydantic models for API
class ParameterChangeProposal(BaseModel):
    """Request model for proposing parameter changes"""
    model_config = ConfigDict(from_attributes=True)
    
    model_name: str = Field(..., description="Model name (SMA, BIA, TSA)")
    parameter_name: str = Field(..., description="Parameter name")
    parameter_type: ParameterType = Field(..., description="Parameter type")
    parameter_category: str = Field(..., description="Parameter category")
    
    current_value: Dict[str, Any] = Field(..., description="Current parameter value")
    proposed_value: Dict[str, Any] = Field(..., description="Proposed parameter value")
    
    effective_date: date = Field(..., description="Effective date for change")
    change_reason: str = Field(..., description="Reason for change")
    business_justification: str = Field(..., description="Business justification")
    
    requires_rbi_approval: bool = Field(default=False, description="Requires RBI approval")
    disclosure_required: bool = Field(default=False, description="Requires disclosure")


class ParameterReview(BaseModel):
    """Request model for parameter review"""
    model_config = ConfigDict(from_attributes=True)
    
    workflow_id: str = Field(..., description="Workflow ID")
    action: str = Field(..., description="Review action (approve/reject)")
    comments: Optional[str] = Field(None, description="Review comments")
    impact_assessment: Optional[str] = Field(None, description="Impact assessment")


class ParameterApproval(BaseModel):
    """Request model for parameter approval"""
    model_config = ConfigDict(from_attributes=True)
    
    workflow_id: str = Field(..., description="Workflow ID")
    action: str = Field(..., description="Approval action (approve/reject)")
    comments: Optional[str] = Field(None, description="Approval comments")
    rbi_approval_reference: Optional[str] = Field(None, description="RBI approval reference")


class ParameterVersionResponse(BaseModel):
    """Response model for parameter version"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    version_id: str
    model_name: str
    parameter_name: str
    parameter_type: ParameterType
    parameter_category: str
    parameter_value: Dict[str, Any]
    version_number: int
    status: ParameterStatus
    effective_date: date
    created_by: str
    change_reason: str
    created_at: datetime


class ParameterSetResponse(BaseModel):
    """Response model for complete parameter set"""
    model_config = ConfigDict(from_attributes=True)
    
    model_name: str
    version_id: str
    parameters: Dict[str, Any]
    effective_date: date
    activated_by: str
    activated_at: datetime


class ParameterDiff(BaseModel):
    """Parameter change diff"""
    model_config = ConfigDict(from_attributes=True)
    
    parameter_name: str
    old_value: Any
    new_value: Any
    changed_by: str
    changed_at: datetime
    change_reason: str