"""
SQLAlchemy ORM models for ORM Capital Calculator Engine

Core entities for operational risk capital calculations following RBI Basel III SMA.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    Column, String, DateTime, Date, Boolean, Text, ForeignKey, 
    Numeric, Integer, Enum as SQLEnum, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import enum


Base = declarative_base()


class JobStatusEnum(str, enum.Enum):
    """Job execution status enumeration"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ModelNameEnum(str, enum.Enum):
    """Calculation model enumeration"""
    BIA = "bia"
    TSA = "tsa"
    SMA = "sma"
    AMA = "ama"
    WHAT_IF = "what-if"


class ExecutionModeEnum(str, enum.Enum):
    """Execution mode enumeration"""
    SYNC = "sync"
    ASYNC = "async"


class BusinessIndicator(Base):
    """
    Business Indicator data for SMA calculations
    
    Stores ILDC (Interest, Lease, Dividend, Commission), SC (Services Component),
    and FC (Financial Component) data for operational risk capital calculations.
    """
    __tablename__ = "business_indicators"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "2023-Q4"
    
    # Business Indicator Components (using Decimal for financial precision)
    ildc: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    sc: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    fc: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    bi_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    three_year_average: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    # Metadata
    methodology: Mapped[str] = mapped_column(String(10), nullable=False, default="SMA")
    source: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_bi_entity_date', 'entity_id', 'calculation_date'),
        Index('idx_bi_period', 'period'),
    )


class LossEvent(Base):
    """
    Operational loss event data for SMA calculations
    
    Stores loss events with occurrence, discovery, and accounting dates,
    gross amounts, and recovery information for capital calculations.
    """
    __tablename__ = "loss_events"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Key dates for loss events
    occurrence_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    discovery_date: Mapped[date] = mapped_column(Date, nullable=False)
    accounting_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Financial amounts (using Decimal for precision)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # Basel II event type and business line
    basel_event_type: Mapped[Optional[str]] = mapped_column(String(50))
    business_line: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Loss characteristics
    is_outsourced: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    is_timing_loss: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Exclusion handling
    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    exclusion_reason: Mapped[Optional[str]] = mapped_column(Text)
    rbi_approval_reference: Mapped[Optional[str]] = mapped_column(String(100))
    disclosure_required: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationship to recoveries
    recoveries: Mapped[List["Recovery"]] = relationship("Recovery", back_populates="loss_event", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_loss_entity_date', 'entity_id', 'accounting_date'),
        Index('idx_loss_occurrence', 'occurrence_date'),
        Index('idx_loss_discovery', 'discovery_date'),
        Index('idx_loss_amount', 'gross_amount'),
    )


class Recovery(Base):
    """
    Recovery data associated with loss events
    
    Tracks recoveries received against loss events with receipt dates
    for accurate net loss calculations.
    """
    __tablename__ = "recoveries"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    loss_event_id: Mapped[str] = mapped_column(String(36), ForeignKey("loss_events.id"), nullable=False, index=True)
    
    # Recovery details
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    recovery_type: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationship back to loss event
    loss_event: Mapped["LossEvent"] = relationship("LossEvent", back_populates="recoveries")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_recovery_loss_event', 'loss_event_id'),
        Index('idx_recovery_date', 'receipt_date'),
    )


class CapitalCalculation(Base):
    """
    Capital calculation results and intermediate values
    
    Stores complete calculation results including Business Indicator Component (BIC),
    Loss Component (LC), Internal Loss Multiplier (ILM), and final capital amounts.
    """
    __tablename__ = "capital_calculations"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    methodology: Mapped[ModelNameEnum] = mapped_column(SQLEnum(ModelNameEnum), nullable=False)
    
    # SMA Components
    business_indicator: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    business_indicator_component: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    loss_component: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    internal_loss_multiplier: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    
    # Final Results
    operational_risk_capital: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    risk_weighted_assets: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # Bucket and gating information
    bucket: Mapped[int] = mapped_column(Integer, nullable=False)
    ilm_gated: Mapped[bool] = mapped_column(Boolean, default=False)
    ilm_gate_reason: Mapped[Optional[str]] = mapped_column(String(200))
    
    # Parameter versions for reproducibility
    parameter_version: Mapped[Optional[str]] = mapped_column(String(36))
    model_version: Mapped[Optional[str]] = mapped_column(String(36))
    
    # Supervisor overrides
    supervisor_override: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[Optional[str]] = mapped_column(Text)
    override_approver: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_calc_entity_date', 'entity_id', 'calculation_date'),
        Index('idx_calc_methodology', 'methodology'),
        Index('idx_calc_run_id', 'run_id'),
    )


class Job(Base):
    """
    Job execution tracking for async calculations
    
    Tracks job status, execution mode, and results for both synchronous
    and asynchronous calculation requests.
    """
    __tablename__ = "jobs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    
    # Job configuration
    model_name: Mapped[ModelNameEnum] = mapped_column(SQLEnum(ModelNameEnum), nullable=False)
    execution_mode: Mapped[ExecutionModeEnum] = mapped_column(SQLEnum(ExecutionModeEnum), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Job status and timing
    status: Mapped[JobStatusEnum] = mapped_column(SQLEnum(JobStatusEnum), nullable=False, default=JobStatusEnum.QUEUED, index=True)
    progress_percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), default=0.0)
    
    # Timing information
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    estimated_completion_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Request and response data
    request_data: Mapped[Optional[str]] = mapped_column(Text)  # JSON serialized request
    result_data: Mapped[Optional[str]] = mapped_column(Text)   # JSON serialized result
    error_details: Mapped[Optional[str]] = mapped_column(Text) # JSON serialized error
    
    # Webhook configuration
    callback_url: Mapped[Optional[str]] = mapped_column(String(500))
    webhook_delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook_attempts: Mapped[int] = mapped_column(Integer, default=0)
    
    # Request tracking
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    
    # Metadata
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_job_status', 'status'),
        Index('idx_job_entity_date', 'entity_id', 'calculation_date'),
        Index('idx_job_created', 'created_at'),
        Index('idx_job_idempotency', 'idempotency_key'),
    )


class AuditTrail(Base):
    """
    Immutable audit trail for regulatory compliance
    
    Maintains complete audit trail of all calculations with immutable
    records for regulatory compliance and reproducibility.
    """
    __tablename__ = "audit_trail"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    
    # Audit information
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    initiator: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    
    # Data lineage
    input_snapshot: Mapped[Optional[str]] = mapped_column(Text)  # JSON serialized inputs
    parameter_versions: Mapped[Optional[str]] = mapped_column(Text)  # JSON serialized parameter versions
    model_version: Mapped[Optional[str]] = mapped_column(String(36))
    environment_hash: Mapped[Optional[str]] = mapped_column(String(64))  # SHA-256 hash
    
    # Results and errors
    outputs: Mapped[Optional[str]] = mapped_column(Text)  # JSON serialized outputs
    intermediates: Mapped[Optional[str]] = mapped_column(Text)  # JSON serialized intermediate results
    errors: Mapped[Optional[str]] = mapped_column(Text)  # JSON serialized errors
    
    # Regulatory flags
    supervisor_overrides: Mapped[Optional[str]] = mapped_column(Text)  # JSON serialized overrides
    exclusions: Mapped[Optional[str]] = mapped_column(Text)  # JSON serialized exclusions
    corporate_actions: Mapped[Optional[str]] = mapped_column(Text)  # JSON serialized M&A events
    
    # Tamper evidence
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 of record
    
    # Metadata (immutable after creation)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_audit_run_id', 'run_id'),
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_operation', 'operation'),
        Index('idx_audit_initiator', 'initiator'),
    )