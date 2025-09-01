#!/usr/bin/env python3
"""
Test script to verify Pydantic models work correctly

Tests data validation and serialization.
"""

import sys
import os
from datetime import date, datetime
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from orm_calculator.models.pydantic_models import (
    BusinessIndicatorCreate, BusinessIndicatorResponse,
    LossEventCreate, LossEventResponse,
    RecoveryCreate, RecoveryResponse,
    CalculationRequest, CalculationResult,
    JobResponse, JobStatus,
    ModelNameEnum, ExecutionModeEnum, JobStatusEnum
)


def test_business_indicator_models():
    """Test business indicator Pydantic models"""
    print("Testing Business Indicator Pydantic models...")
    
    # Test creation model
    bi_create = BusinessIndicatorCreate(
        entity_id="BANK001",
        calculation_date=date(2023, 12, 31),
        period="2023-Q4",
        ildc=Decimal("1000000.00"),
        sc=Decimal("500000.00"),
        fc=Decimal("300000.00"),
        methodology="SMA"
    )
    
    print(f"Created BI model: {bi_create.entity_id} - {bi_create.period}")
    
    # Test response model
    bi_response = BusinessIndicatorResponse(
        id="test-id",
        entity_id="BANK001",
        calculation_date=date(2023, 12, 31),
        period="2023-Q4",
        ildc=Decimal("1000000.00"),
        sc=Decimal("500000.00"),
        fc=Decimal("300000.00"),
        bi_total=Decimal("1800000.00"),
        methodology="SMA",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    print(f"Created BI response: {bi_response.bi_total}")


def test_loss_event_models():
    """Test loss event Pydantic models"""
    print("Testing Loss Event Pydantic models...")
    
    # Test creation model
    loss_create = LossEventCreate(
        entity_id="BANK001",
        event_type="Operational Loss",
        occurrence_date=date(2023, 6, 15),
        discovery_date=date(2023, 6, 20),
        accounting_date=date(2023, 6, 30),
        gross_amount=Decimal("250000.00"),
        basel_event_type="Internal Fraud",
        business_line="Retail Banking"
    )
    
    print(f"Created Loss Event: {loss_create.event_type} - {loss_create.gross_amount}")
    
    # Test validation - discovery date should be after occurrence date
    try:
        invalid_loss = LossEventCreate(
            entity_id="BANK001",
            event_type="Operational Loss",
            occurrence_date=date(2023, 6, 20),
            discovery_date=date(2023, 6, 15),  # Before occurrence date
            accounting_date=date(2023, 6, 30),
            gross_amount=Decimal("250000.00")
        )
        print("ERROR: Validation should have failed!")
    except ValueError as e:
        print(f"Validation correctly failed: {e}")


def test_calculation_models():
    """Test calculation request/response models"""
    print("Testing Calculation Pydantic models...")
    
    # Test calculation request
    calc_request = CalculationRequest(
        model_name=ModelNameEnum.SMA,
        execution_mode=ExecutionModeEnum.SYNC,
        entity_id="BANK001",
        calculation_date=date(2023, 12, 31),
        idempotency_key="test_key_001"
    )
    
    print(f"Created calculation request: {calc_request.model_name} - {calc_request.entity_id}")
    
    # Test calculation result
    calc_result = CalculationResult(
        run_id="run_001",
        entity_id="BANK001",
        calculation_date=date(2023, 12, 31),
        methodology=ModelNameEnum.SMA,
        business_indicator=Decimal("1800000.00"),
        business_indicator_component=Decimal("216000.00"),
        loss_component=Decimal("3750000.00"),
        internal_loss_multiplier=Decimal("1.2345"),
        operational_risk_capital=Decimal("266652.00"),
        risk_weighted_assets=Decimal("3333150.00"),
        bucket=2,
        ilm_gated=False,
        created_at=datetime.now()
    )
    
    print(f"Created calculation result: ORC = {calc_result.operational_risk_capital}")


def test_job_models():
    """Test job management models"""
    print("Testing Job Pydantic models...")
    
    # Test job response
    job_response = JobResponse(
        job_id="job_001",
        run_id="run_001",
        status=JobStatusEnum.QUEUED,
        created_at=datetime.now()
    )
    
    print(f"Created job response: {job_response.job_id} - {job_response.status}")
    
    # Test job status
    job_status = JobStatus(
        job_id="job_001",
        run_id="run_001",
        status=JobStatusEnum.RUNNING,
        progress_percentage=Decimal("25.0"),
        result_available=False
    )
    
    print(f"Created job status: {job_status.progress_percentage}% complete")


def test_json_serialization():
    """Test JSON serialization/deserialization"""
    print("Testing JSON serialization...")
    
    # Create a model
    calc_request = CalculationRequest(
        model_name=ModelNameEnum.SMA,
        execution_mode=ExecutionModeEnum.ASYNC,
        entity_id="BANK001",
        calculation_date=date(2023, 12, 31),
        callback_url="https://example.com/webhook"
    )
    
    # Serialize to JSON
    json_data = calc_request.model_dump_json()
    print(f"Serialized to JSON: {json_data}")
    
    # Deserialize from JSON
    parsed_request = CalculationRequest.model_validate_json(json_data)
    print(f"Parsed from JSON: {parsed_request.model_name} - {parsed_request.callback_url}")


def main():
    """Run all tests"""
    try:
        print("Testing Pydantic models...\n")
        
        test_business_indicator_models()
        print()
        
        test_loss_event_models()
        print()
        
        test_calculation_models()
        print()
        
        test_job_models()
        print()
        
        test_json_serialization()
        print()
        
        print("All Pydantic model tests passed successfully!")
        return 0
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)