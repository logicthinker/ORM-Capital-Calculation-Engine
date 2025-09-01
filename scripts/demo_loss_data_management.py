#!/usr/bin/env python3
"""
Demo script for Loss Data Management System

Demonstrates the key features of the loss data management system:
- Loss event ingestion with validation
- Recovery processing with net loss recalculation
- Exclusion handling with RBI approval
- Threshold filtering for SMA calculations
"""

import asyncio
import sys
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orm_calculator.models.pydantic_models import (
    LossEventCreate, RecoveryCreate, ValidationResult
)
from orm_calculator.services.loss_data_service import (
    LossDataValidationService, RBIApprovalMetadata
)


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_validation_result(result: ValidationResult, title: str):
    """Print validation result in a formatted way"""
    print(f"\n{title}:")
    print(f"  Success: {result.success}")
    print(f"  Records Processed: {result.records_processed}")
    print(f"  Records Accepted: {result.records_accepted}")
    print(f"  Records Rejected: {result.records_rejected}")
    
    if result.errors:
        print(f"  Errors ({len(result.errors)}):")
        for error in result.errors:
            print(f"    - {error.error_code}: {error.error_message}")
            if error.field:
                print(f"      Field: {error.field}")
    
    if result.warnings:
        print(f"  Warnings ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"    - {warning.error_code}: {warning.error_message}")


def demo_validation_service():
    """Demonstrate the validation service functionality"""
    print_section("Loss Data Validation Service Demo")
    
    validation_service = LossDataValidationService()
    
    # Demo 1: Valid loss event
    print("\n1. Validating a VALID loss event:")
    valid_loss_event = LossEventCreate(
        entity_id="DEMO_BANK_001",
        event_type="operational_loss",
        occurrence_date=date(2023, 6, 15),
        discovery_date=date(2023, 6, 20),
        accounting_date=date(2023, 6, 25),
        gross_amount=Decimal('250000.00'),  # ₹2.5 lakh
        basel_event_type="internal_fraud",
        business_line="retail_banking",
        description="Demo loss event for testing"
    )
    
    errors = validation_service.validate_loss_event(valid_loss_event)
    print(f"   Validation errors: {len(errors)}")
    if errors:
        for error in errors:
            print(f"   - {error.error_code}: {error.error_message}")
    else:
        print("   ✓ Loss event is valid!")
    
    # Demo 2: Loss event below threshold
    print("\n2. Validating loss event BELOW THRESHOLD:")
    below_threshold_dict = {
        "entity_id": "DEMO_BANK_001",
        "event_type": "operational_loss",
        "occurrence_date": date(2023, 6, 15),
        "discovery_date": date(2023, 6, 20),
        "accounting_date": date(2023, 6, 25),
        "gross_amount": Decimal('75000.00')  # Below ₹1,00,000 threshold
    }
    below_threshold_event = type('LossEventCreate', (), below_threshold_dict)()
    
    errors = validation_service.validate_loss_event(below_threshold_event)
    print(f"   Validation errors: {len(errors)}")
    for error in errors:
        print(f"   - {error.error_code}: {error.error_message}")
    
    # Demo 3: Invalid date sequence
    print("\n3. Validating loss event with INVALID DATE SEQUENCE:")
    invalid_dates_dict = {
        "entity_id": "DEMO_BANK_001",
        "event_type": "operational_loss",
        "occurrence_date": date(2023, 6, 20),
        "discovery_date": date(2023, 6, 15),  # Before occurrence
        "accounting_date": date(2023, 6, 25),
        "gross_amount": Decimal('150000.00')
    }
    invalid_dates_event = type('LossEventCreate', (), invalid_dates_dict)()
    
    errors = validation_service.validate_loss_event(invalid_dates_event)
    print(f"   Validation errors: {len(errors)}")
    for error in errors:
        print(f"   - {error.error_code}: {error.error_message}")
    
    # Demo 4: Custom threshold validation
    print("\n4. Validating with CUSTOM THRESHOLD (₹50,000):")
    custom_validation_service = LossDataValidationService(Decimal('50000.00'))
    
    custom_threshold_event = LossEventCreate(
        entity_id="DEMO_BANK_001",
        event_type="operational_loss",
        occurrence_date=date(2023, 6, 15),
        discovery_date=date(2023, 6, 20),
        accounting_date=date(2023, 6, 25),
        gross_amount=Decimal('75000.00')  # Above custom threshold, below default
    )
    
    errors = custom_validation_service.validate_loss_event(custom_threshold_event)
    print(f"   Validation errors with custom threshold: {len(errors)}")
    if errors:
        for error in errors:
            print(f"   - {error.error_code}: {error.error_message}")
    else:
        print("   ✓ Loss event is valid with custom threshold!")


def demo_recovery_validation():
    """Demonstrate recovery validation"""
    print_section("Recovery Validation Demo")
    
    validation_service = LossDataValidationService()
    
    # Create a mock loss event
    from orm_calculator.models.orm_models import LossEvent
    loss_event = LossEvent(
        id="demo-loss-001",
        entity_id="DEMO_BANK_001",
        event_type="operational_loss",
        occurrence_date=date(2023, 6, 15),
        discovery_date=date(2023, 6, 20),
        accounting_date=date(2023, 6, 25),
        gross_amount=Decimal('200000.00'),
        net_amount=Decimal('200000.00')
    )
    
    # Demo 1: Valid recovery
    print("\n1. Validating a VALID recovery:")
    valid_recovery = RecoveryCreate(
        loss_event_id=loss_event.id,
        amount=Decimal('50000.00'),  # ₹50,000 recovery
        receipt_date=date(2023, 8, 15),
        recovery_type="insurance",
        description="Insurance payout for operational loss"
    )
    
    errors = validation_service.validate_recovery(valid_recovery, loss_event)
    print(f"   Validation errors: {len(errors)}")
    if errors:
        for error in errors:
            print(f"   - {error.error_code}: {error.error_message}")
    else:
        print("   ✓ Recovery is valid!")
        print(f"   Original gross loss: ₹{loss_event.gross_amount:,.2f}")
        print(f"   Recovery amount: ₹{valid_recovery.amount:,.2f}")
        print(f"   Net loss after recovery: ₹{loss_event.gross_amount - valid_recovery.amount:,.2f}")
    
    # Demo 2: Recovery exceeding gross amount
    print("\n2. Validating recovery that EXCEEDS GROSS AMOUNT:")
    excessive_recovery = RecoveryCreate(
        loss_event_id=loss_event.id,
        amount=Decimal('250000.00'),  # Exceeds ₹200,000 gross
        receipt_date=date(2023, 8, 15)
    )
    
    errors = validation_service.validate_recovery(excessive_recovery, loss_event)
    print(f"   Validation errors: {len(errors)}")
    for error in errors:
        print(f"   - {error.error_code}: {error.error_message}")
    
    # Demo 3: Recovery before occurrence date
    print("\n3. Validating recovery BEFORE OCCURRENCE DATE:")
    early_recovery = RecoveryCreate(
        loss_event_id=loss_event.id,
        amount=Decimal('30000.00'),
        receipt_date=date(2023, 6, 10)  # Before occurrence date
    )
    
    errors = validation_service.validate_recovery(early_recovery, loss_event)
    print(f"   Validation errors: {len(errors)}")
    for error in errors:
        print(f"   - {error.error_code}: {error.error_message}")


def demo_rbi_approval_validation():
    """Demonstrate RBI approval metadata validation"""
    print_section("RBI Approval Metadata Demo")
    
    validation_service = LossDataValidationService()
    
    # Create a mock loss event
    from orm_calculator.models.orm_models import LossEvent
    loss_event = LossEvent(
        id="demo-loss-002",
        entity_id="DEMO_BANK_001",
        event_type="operational_loss",
        occurrence_date=date(2023, 6, 15),
        discovery_date=date(2023, 6, 20),
        accounting_date=date(2023, 6, 25),
        gross_amount=Decimal('500000.00'),
        net_amount=Decimal('500000.00')
    )
    
    # Demo 1: Valid RBI approval
    print("\n1. Validating VALID RBI approval:")
    valid_approval = RBIApprovalMetadata(
        approval_reference="RBI/DOR/2023/001",
        approval_date=date(2023, 7, 15),
        approving_authority="RBI Department of Regulation",
        approval_reason="Exclusion approved due to external factors beyond bank control"
    )
    
    print(f"   RBI Approval Reference: {valid_approval.approval_reference}")
    print(f"   Approval Date: {valid_approval.approval_date}")
    print(f"   Approving Authority: {valid_approval.approving_authority}")
    print(f"   Approval Reason: {valid_approval.approval_reason}")
    print(f"   Is Valid: {valid_approval.is_valid()}")
    
    errors = validation_service.validate_exclusion(
        loss_event, "External factor exclusion", valid_approval
    )
    print(f"   Exclusion validation errors: {len(errors)}")
    if errors:
        for error in errors:
            print(f"   - {error.error_code}: {error.error_message}")
    else:
        print("   ✓ RBI approval and exclusion are valid!")
    
    # Demo 2: Invalid RBI approval (missing fields)
    print("\n2. Validating INVALID RBI approval (missing reference):")
    invalid_approval = RBIApprovalMetadata(
        approval_reference="",  # Empty reference
        approval_date=date(2023, 7, 15),
        approving_authority="RBI Department of Regulation",
        approval_reason="Exclusion approved"
    )
    
    print(f"   Is Valid: {invalid_approval.is_valid()}")
    
    errors = validation_service.validate_exclusion(
        loss_event, "External factor exclusion", invalid_approval
    )
    print(f"   Exclusion validation errors: {len(errors)}")
    for error in errors:
        print(f"   - {error.error_code}: {error.error_message}")
    
    # Demo 3: No RBI approval provided
    print("\n3. Validating exclusion WITHOUT RBI approval:")
    errors = validation_service.validate_exclusion(
        loss_event, "Attempted exclusion without approval", None
    )
    print(f"   Exclusion validation errors: {len(errors)}")
    for error in errors:
        print(f"   - {error.error_code}: {error.error_message}")


def demo_threshold_scenarios():
    """Demonstrate different threshold scenarios for SMA calculations"""
    print_section("Threshold Scenarios for SMA Calculations")
    
    # Default threshold (₹1,00,000)
    default_service = LossDataValidationService()
    
    # Custom threshold (₹50,000)
    custom_service = LossDataValidationService(Decimal('50000.00'))
    
    test_amounts = [
        Decimal('25000.00'),   # ₹25,000
        Decimal('75000.00'),   # ₹75,000
        Decimal('100000.00'),  # ₹1,00,000 (default threshold)
        Decimal('150000.00'),  # ₹1,50,000
        Decimal('500000.00'),  # ₹5,00,000
    ]
    
    print(f"\n{'Amount':<15} {'Default (₹1L)':<15} {'Custom (₹50K)':<15}")
    print("-" * 45)
    
    for amount in test_amounts:
        # Test with default threshold
        test_event_dict = {
            "entity_id": "DEMO_BANK_001",
            "event_type": "operational_loss",
            "occurrence_date": date(2023, 6, 15),
            "discovery_date": date(2023, 6, 20),
            "accounting_date": date(2023, 6, 25),
            "gross_amount": amount
        }
        test_event = type('LossEventCreate', (), test_event_dict)()
        
        default_errors = default_service.validate_loss_event(test_event)
        custom_errors = custom_service.validate_loss_event(test_event)
        
        default_valid = not any(e.error_code == "BELOW_THRESHOLD" for e in default_errors)
        custom_valid = not any(e.error_code == "BELOW_THRESHOLD" for e in custom_errors)
        
        print(f"₹{amount:>12,.2f} {'✓' if default_valid else '✗':<15} {'✓' if custom_valid else '✗':<15}")
    
    print("\nSummary:")
    print("- Default threshold (₹1,00,000): Only amounts ≥ ₹1,00,000 are included in SMA calculations")
    print("- Custom threshold (₹50,000): Amounts ≥ ₹50,000 are included")
    print("- This flexibility allows banks to adjust thresholds based on their risk profile")


def main():
    """Main demo function"""
    print("🏦 ORM Capital Calculator - Loss Data Management System Demo")
    print("=" * 70)
    print("This demo showcases the key features of the loss data management system")
    print("designed for RBI Basel III SMA compliance.")
    
    try:
        # Run all demos
        demo_validation_service()
        demo_recovery_validation()
        demo_rbi_approval_validation()
        demo_threshold_scenarios()
        
        print_section("Demo Complete")
        print("\n✅ All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("1. ✓ Loss event validation with RBI compliance rules")
        print("2. ✓ Recovery processing with business rule validation")
        print("3. ✓ RBI approval metadata validation for exclusions")
        print("4. ✓ Configurable threshold filtering for SMA calculations")
        print("5. ✓ Comprehensive error reporting and validation feedback")
        
        print("\nNext Steps:")
        print("- Integrate with database for persistent storage")
        print("- Add API endpoints for external system integration")
        print("- Implement audit trail and lineage tracking")
        print("- Add webhook notifications for processing events")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)