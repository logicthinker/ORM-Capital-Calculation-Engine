"""
SQLAlchemy ORM models for ORM Capital Calculator Engine
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Column, String, DateTime, Date, Numeric, Boolean, Text, 
    ForeignKey, Integer, Enum as SQLEnum
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class JobStatus(enum.Enum):
    """Job execution status"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CalculationMethodology(enum.Enum):
    """Calculation methodology types"""
    SMA = "sma"
    BIA = "bia"
    TSA = "tsa"
    AMA = "ama"


class BusinessIndicator(Base):
    """Business Indicator data model"""
    __tablename__ = "business_indicators"
    
    id = Column(String, primary_key=True)
    entity_id = Column(String, nullable=False, index=True)
    calculation_date = Column(Date, nullable=False, index=True)
    period = Column(String, nullable=False)  # e.g., "2023-Q4"
    
    # Business Indicator components (using Decimal for financial precision)
    ildc = Column(Numeric(precision=15, scale=2), nullable=False)  # Interest, Leases, Dividends, Commissions
    sc = Column(Numeric(precision=15, scale=2), nullable=False)    # Services Component
    fc = Column(Numeric(precision=15, scale=2), nullable=False)    # Financial Component
    bi_total = Column(Numeric(precision=15, scale=2), nullable=False)  # BI = ILDC + SC + FC
    
    # Calculated values
    three_year_average = Column(Numeric(precision=15, scale=2))
    methodology = Column(SQLEnum(CalculationMethodology), nullable=False)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    calculations = relationship("CapitalCalculation", back_populates="business_indicator")


class LossEvent(Base):
    """Loss Event data model"""
    __tablename__ = "loss_events"
    
    id = Column(String, primary_key=True)
    entity_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)  # Basel event type
    business_line = Column(String, nullable=False)  # Basel business line
    
    # Key dates
    occurrence_date = Column(Date, nullable=False, index=True)
    discovery_date = Column(Date, nullable=False)
    accounting_date = Column(Date, nullable=False, index=True)
    
    # Financial amounts (using Decimal for precision)
    gross_amount = Column(Numeric(precision=15, scale=2), nullable=False)
    net_amount = Column(Numeric(precision=15, scale=2), nullable=False)
    
    # Loss characteristics
    is_outsourced = Column(Boolean, default=False)
    is_pending = Column(Boolean, default=False)
    is_timing_loss = Column(Boolean, default=False)
    
    # Exclusion handling
    is_excluded = Column(Boolean, default=False)
    exclusion_reason = Column(Text)
    rbi_approval_reference = Column(String)  # RBI approval for exclusions
    disclosure_required = Column(Boolean, default=False)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    recoveries = relationship("Recovery", back_populates="loss_event", cascade="all, delete-orphan")


class Recovery(Base):
    """Recovery data model"""
    __tablename__ = "recoveries"
    
    id = Column(String, primary_key=True)
    loss_event_id = Column(String, ForeignKey("loss_events.id"), nullable=False)
    
    # Recovery details
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    receipt_date = Column(Date, nullable=False)
    recovery_type = Column(String)  # e.g., "insurance", "legal", "other"
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    loss_event = relationship("LossEvent", back_populates="recoveries")


class CapitalCalculation(Base):
    """Capital Calculation results model"""
    __tablename__ = "capital_calculations"
    
    id = Column(String, primary_key=True)
    run_id = Column(String, nullable=False, unique=True, index=True)
    entity_id = Column(String, nullable=False, index=True)
    calculation_date = Column(Date, nullable=False, index=True)
    methodology = Column(SQLEnum(CalculationMethodology), nullable=False)
    
    # SMA calculation components
    business_indicator = Column(Numeric(precision=15, scale=2), nullable=False)
    business_indicator_component = Column(Numeric(precision=15, scale=2), nullable=False)  # BIC
    loss_component = Column(Numeric(precision=15, scale=2), nullable=False)  # LC
    internal_loss_multiplier = Column(Numeric(precision=15, scale=4), nullable=False)  # ILM
    
    # Final results
    operational_risk_capital = Column(Numeric(precision=15, scale=2), nullable=False)  # ORC
    risk_weighted_assets = Column(Numeric(precision=15, scale=2), nullable=False)  # RWA
    
    # Bucket and gating information
    sma_bucket = Column(Integer)  # 1, 2, or 3
    ilm_gated = Column(Boolean, default=False)  # True if ILM gate applied
    ilm_gate_reason = Column(String)  # Reason for ILM gating
    
    # Parameter versioning
    parameter_version_id = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String)
    
    # Foreign keys
    business_indicator_id = Column(String, ForeignKey("business_indicators.id"))
    
    # Relationships
    business_indicator = relationship("BusinessIndicator", back_populates="calculations")
    job = relationship("Job", back_populates="calculation", uselist=False)


class Job(Base):
    """Job execution tracking model"""
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True)
    run_id = Column(String, nullable=False, index=True)
    job_type = Column(String, nullable=False)  # "calculation", "stress_test", etc.
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.QUEUED)
    
    # Job configuration
    entity_id = Column(String, nullable=False)
    methodology = Column(SQLEnum(CalculationMethodology), nullable=False)
    execution_mode = Column(String, nullable=False)  # "sync" or "async"
    
    # Timing information
    queued_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    estimated_completion = Column(DateTime)
    
    # Progress tracking
    progress_percentage = Column(Numeric(precision=5, scale=2), default=0)
    current_step = Column(String)
    
    # Results and errors
    result_data = Column(Text)  # JSON serialized results
    error_message = Column(Text)
    error_code = Column(String)
    
    # Webhook configuration
    callback_url = Column(String)
    webhook_delivered = Column(Boolean, default=False)
    webhook_delivery_attempts = Column(Integer, default=0)
    
    # Request tracking
    idempotency_key = Column(String, index=True)
    correlation_id = Column(String, index=True)
    created_by = Column(String)
    
    # Foreign keys
    calculation_id = Column(String, ForeignKey("capital_calculations.id"))
    
    # Relationships
    calculation = relationship("CapitalCalculation", back_populates="job")


class AuditTrail(Base):
    """Audit trail for all operations"""
    __tablename__ = "audit_trail"
    
    id = Column(String, primary_key=True)
    run_id = Column(String, nullable=False, index=True)
    operation = Column(String, nullable=False)
    entity_id = Column(String, nullable=False, index=True)
    
    # User and timing
    user_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Operation details
    operation_type = Column(String, nullable=False)  # "calculation", "parameter_change", etc.
    input_data_hash = Column(String, nullable=False)  # SHA-256 hash of inputs
    output_data_hash = Column(String)  # SHA-256 hash of outputs
    
    # Lineage information
    parameter_versions = Column(Text)  # JSON serialized parameter versions
    model_versions = Column(Text)  # JSON serialized model versions
    data_sources = Column(Text)  # JSON serialized data source information
    
    # Reproducibility
    environment_hash = Column(String, nullable=False)
    reproducible = Column(Boolean, default=True)
    
    # Additional metadata
    additional_metadata = Column(Text)  # JSON serialized additional metadata