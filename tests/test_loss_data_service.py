"""
Tests for Loss Data Management Service

Focused tests for loss data validation, ingestion, and processing functionality.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

from orm_calculator.models.pydantic_models import (
    LossEventCreate, RecoveryCreate, ValidationResult
)
from orm_calculator.models.orm_models import LossEvent, Recovery
from orm_calculator.services.loss_data_service import (
    LossDataValidationService, RBIApprovalMetadata
)


class TestLossDataValidationService:
    """Test loss data validation service"""
    
    def test_validate_loss_event_valid(self):
        """Test validation of valid loss event"""
        validation_service = LossDataValidationService()
        
        loss_event = LossEventCreate(
            entity_id="BANK001",
            event_type="operational_loss",
            occurrence_date=date(2023, 1, 15),
            discovery_date=date(2023, 1, 20),
            accounting_date=date(2023, 1, 25),
            gross_amount=Decimal('150000.00'),
            basel_event_type="internal_fraud",
            business_line="retail_banking"
        )
        
        errors = validation_service.validate_loss_event(loss_event)
        assert len(errors) == 0
    
    def test_validate_loss_event_below_threshold(self):
        """Test validation fails for amount below threshold"""
        validation_service = LossDataValidationService()
        
        loss_event = LossEventCreate(
            entity_id="BANK001",
            event_type="operational_loss",
            occurrence_date=date(2023, 1, 15),
            discovery_date=date(2023, 1, 20),
            accounting_date=date(2023, 1, 25),
            gross_amount=Decimal('50000.00')  # Below ₹1,00,000 threshold
        )
        
        errors = validation_service.validate_loss_event(loss_event)
        assert len(errors) > 0
        assert any(error.error_code == "BELOW_THRESHOLD" for error in errors)
    
    def test_validate_loss_event_invalid_dates(self):
        """Test validation fails for invalid date sequence"""
        validation_service = LossDataValidationService()
        
        # Create loss event with invalid date sequence using dict to bypass Pydantic validation
        loss_event_dict = {
            "entity_id": "BANK001",
            "event_type": "operational_loss",
            "occurrence_date": date(2023, 1, 20),
            "discovery_date": date(2023, 1, 15),  # Before occurrence
            "accounting_date": date(2023, 1, 25),
            "gross_amount": Decimal('150000.00')
        }
        
        # Create object directly to bypass Pydantic validation
        loss_event = type('LossEventCreate', (), loss_event_dict)()
        
        errors = validation_service.validate_loss_event(loss_event)
        assert len(errors) > 0
        assert any(error.error_code == "INVALID_DATE_SEQUENCE" for error in errors)
    
    def test_validate_loss_event_missing_required_fields(self):
        """Test validation fails for missing required fields"""
        validation_service = LossDataValidationService()
        
        # Create loss event with missing entity_id
        loss_event_dict = {
            "entity_id": "",  # Empty required field
            "event_type": "operational_loss",
            "occurrence_date": date(2023, 1, 15),
            "discovery_date": date(2023, 1, 20),
            "accounting_date": date(2023, 1, 25),
            "gross_amount": Decimal('150000.00')
        }
        
        loss_event = type('LossEventCreate', (), loss_event_dict)()
        
        errors = validation_service.validate_loss_event(loss_event)
        assert len(errors) > 0
        assert any(error.error_code == "MISSING_REQUIRED_FIELD" for error in errors)
    
    def test_validate_loss_event_invalid_basel_event_type(self):
        """Test validation fails for invalid Basel event type"""
        validation_service = LossDataValidationService()
        
        # Create loss event with invalid Basel event type using dict to bypass Pydantic validation
        loss_event_dict = {
            "entity_id": "BANK001",
            "event_type": "operational_loss",
            "occurrence_date": date(2023, 1, 15),
            "discovery_date": date(2023, 1, 20),
            "accounting_date": date(2023, 1, 25),
            "gross_amount": Decimal('150000.00'),
            "basel_event_type": "invalid_event_type"  # Invalid type
        }
        
        loss_event = type('LossEventCreate', (), loss_event_dict)()
        
        errors = validation_service.validate_loss_event(loss_event)
        assert len(errors) > 0
        assert any(error.error_code == "INVALID_BASEL_EVENT_TYPE" for error in errors)
    
    def test_validate_recovery_valid(self):
        """Test validation of valid recovery"""
        validation_service = LossDataValidationService()
        
        # Create mock loss event
        loss_event = LossEvent(
            id="test-loss-id",
            entity_id="BANK001",
            event_type="operational_loss",
            occurrence_date=date(2023, 1, 15),
            discovery_date=date(2023, 1, 20),
            accounting_date=date(2023, 1, 25),
            gross_amount=Decimal('150000.00'),
            net_amount=Decimal('150000.00')
        )
        
        recovery = RecoveryCreate(
            loss_event_id=loss_event.id,
            amount=Decimal('25000.00'),
            receipt_date=date(2023, 3, 15)
        )
        
        errors = validation_service.validate_recovery(recovery, loss_event)
        assert len(errors) == 0
    
    def test_validate_recovery_exceeds_gross(self):
        """Test validation fails when recovery exceeds gross amount"""
        validation_service = LossDataValidationService()
        
        loss_event = LossEvent(
            id="test-loss-id",
            entity_id="BANK001",
            event_type="operational_loss",
            occurrence_date=date(2023, 1, 15),
            discovery_date=date(2023, 1, 20),
            accounting_date=date(2023, 1, 25),
            gross_amount=Decimal('150000.00'),
            net_amount=Decimal('150000.00')
        )
        
        recovery = RecoveryCreate(
            loss_event_id=loss_event.id,
            amount=Decimal('200000.00'),  # Exceeds gross amount
            receipt_date=date(2023, 3, 15)
        )
        
        errors = validation_service.validate_recovery(recovery, loss_event)
        assert len(errors) > 0
        assert any(error.error_code == "RECOVERY_EXCEEDS_GROSS" for error in errors)
    
    def test_validate_recovery_before_occurrence(self):
        """Test validation fails when recovery is before occurrence date"""
        validation_service = LossDataValidationService()
        
        loss_event = LossEvent(
            id="test-loss-id",
            entity_id="BANK001",
            event_type="operational_loss",
            occurrence_date=date(2023, 1, 15),
            discovery_date=date(2023, 1, 20),
            accounting_date=date(2023, 1, 25),
            gross_amount=Decimal('150000.00'),
            net_amount=Decimal('150000.00')
        )
        
        recovery = RecoveryCreate(
            loss_event_id=loss_event.id,
            amount=Decimal('25000.00'),
            receipt_date=date(2023, 1, 10)  # Before occurrence date
        )
        
        errors = validation_service.validate_recovery(recovery, loss_event)
        assert len(errors) > 0
        assert any(error.error_code == "RECOVERY_BEFORE_OCCURRENCE" for error in errors)
    
    def test_validate_exclusion_valid(self):
        """Test validation of valid exclusion with RBI approval"""
        validation_service = LossDataValidationService()
        
        loss_event = LossEvent(
            id="test-loss-id",
            entity_id="BANK001",
            event_type="operational_loss",
            occurrence_date=date(2023, 1, 15),
            discovery_date=date(2023, 1, 20),
            accounting_date=date(2023, 1, 25),
            gross_amount=Decimal('150000.00'),
            net_amount=Decimal('150000.00')
        )
        
        rbi_approval = RBIApprovalMetadata(
            approval_reference="RBI/2023/001",
            approval_date=date(2023, 2, 1),
            approving_authority="RBI Mumbai",
            approval_reason="Regulatory exclusion approved"
        )
        
        errors = validation_service.validate_exclusion(
            loss_event, "Regulatory exclusion", rbi_approval
        )
        assert len(errors) == 0
    
    def test_validate_exclusion_missing_approval(self):
        """Test validation fails without RBI approval"""
        validation_service = LossDataValidationService()
        
        loss_event = LossEvent(
            id="test-loss-id",
            entity_id="BANK001",
            event_type="operational_loss",
            occurrence_date=date(2023, 1, 15),
            discovery_date=date(2023, 1, 20),
            accounting_date=date(2023, 1, 25),
            gross_amount=Decimal('150000.00'),
            net_amount=Decimal('150000.00')
        )
        
        errors = validation_service.validate_exclusion(
            loss_event, "Regulatory exclusion", None
        )
        assert len(errors) > 0
        assert any(error.error_code == "MISSING_RBI_APPROVAL" for error in errors)
    
    def test_validate_exclusion_missing_reason(self):
        """Test validation fails without exclusion reason"""
        validation_service = LossDataValidationService()
        
        loss_event = LossEvent(
            id="test-loss-id",
            entity_id="BANK001",
            event_type="operational_loss",
            occurrence_date=date(2023, 1, 15),
            discovery_date=date(2023, 1, 20),
            accounting_date=date(2023, 1, 25),
            gross_amount=Decimal('150000.00'),
            net_amount=Decimal('150000.00')
        )
        
        rbi_approval = RBIApprovalMetadata(
            approval_reference="RBI/2023/001",
            approval_date=date(2023, 2, 1),
            approving_authority="RBI Mumbai",
            approval_reason="Regulatory exclusion approved"
        )
        
        errors = validation_service.validate_exclusion(
            loss_event, "", rbi_approval  # Empty reason
        )
        assert len(errors) > 0
        assert any(error.error_code == "MISSING_EXCLUSION_REASON" for error in errors)


class TestRBIApprovalMetadata:
    """Test RBI approval metadata"""
    
    def test_valid_approval_metadata(self):
        """Test valid RBI approval metadata"""
        approval = RBIApprovalMetadata(
            approval_reference="RBI/2023/001",
            approval_date=date(2023, 2, 1),
            approving_authority="RBI Mumbai",
            approval_reason="Regulatory exclusion approved"
        )
        
        assert approval.is_valid()
    
    def test_invalid_approval_metadata_missing_fields(self):
        """Test invalid RBI approval metadata with missing fields"""
        approval = RBIApprovalMetadata(
            approval_reference="",  # Empty
            approval_date=date(2023, 2, 1),
            approving_authority="RBI Mumbai",
            approval_reason="Regulatory exclusion approved"
        )
        
        assert not approval.is_valid()
    
    def test_invalid_approval_metadata_future_date(self):
        """Test invalid RBI approval metadata with future date"""
        from datetime import date, timedelta
        
        approval = RBIApprovalMetadata(
            approval_reference="RBI/2023/001",
            approval_date=date.today() + timedelta(days=1),  # Future date
            approving_authority="RBI Mumbai",
            approval_reason="Regulatory exclusion approved"
        )
        
        assert not approval.is_valid()
    
    def test_invalid_approval_metadata_missing_authority(self):
        """Test invalid RBI approval metadata with missing authority"""
        approval = RBIApprovalMetadata(
            approval_reference="RBI/2023/001",
            approval_date=date(2023, 2, 1),
            approving_authority="",  # Empty
            approval_reason="Regulatory exclusion approved"
        )
        
        assert not approval.is_valid()
    
    def test_invalid_approval_metadata_missing_reason(self):
        """Test invalid RBI approval metadata with missing reason"""
        approval = RBIApprovalMetadata(
            approval_reference="RBI/2023/001",
            approval_date=date(2023, 2, 1),
            approving_authority="RBI Mumbai",
            approval_reason=""  # Empty
        )
        
        assert not approval.is_valid()


class TestLossDataValidationServiceThresholds:
    """Test loss data validation service with different thresholds"""
    
    def test_custom_minimum_threshold(self):
        """Test validation with custom minimum threshold"""
        custom_threshold = Decimal('50000.00')  # ₹50,000
        validation_service = LossDataValidationService(custom_threshold)
        
        # This should pass with custom threshold
        loss_event = LossEventCreate(
            entity_id="BANK001",
            event_type="operational_loss",
            occurrence_date=date(2023, 1, 15),
            discovery_date=date(2023, 1, 20),
            accounting_date=date(2023, 1, 25),
            gross_amount=Decimal('75000.00')  # Above custom threshold, below default
        )
        
        errors = validation_service.validate_loss_event(loss_event)
        # Should have no threshold errors with custom threshold
        threshold_errors = [e for e in errors if e.error_code == "BELOW_THRESHOLD"]
        assert len(threshold_errors) == 0
    
    def test_default_threshold_enforcement(self):
        """Test that default threshold is properly enforced"""
        validation_service = LossDataValidationService()  # Default threshold
        
        # Test amount just below default threshold
        loss_event = LossEventCreate(
            entity_id="BANK001",
            event_type="operational_loss",
            occurrence_date=date(2023, 1, 15),
            discovery_date=date(2023, 1, 20),
            accounting_date=date(2023, 1, 25),
            gross_amount=Decimal('99999.99')  # Just below ₹1,00,000
        )
        
        errors = validation_service.validate_loss_event(loss_event)
        assert any(error.error_code == "BELOW_THRESHOLD" for error in errors)
        
        # Test amount at threshold
        loss_event_at_threshold = LossEventCreate(
            entity_id="BANK001",
            event_type="operational_loss",
            occurrence_date=date(2023, 1, 15),
            discovery_date=date(2023, 1, 20),
            accounting_date=date(2023, 1, 25),
            gross_amount=Decimal('100000.00')  # Exactly ₹1,00,000
        )
        
        errors_at_threshold = validation_service.validate_loss_event(loss_event_at_threshold)
        threshold_errors = [e for e in errors_at_threshold if e.error_code == "BELOW_THRESHOLD"]
        assert len(threshold_errors) == 0


class TestLossDataValidationServiceBusinessRules:
    """Test business rule validation"""
    
    def test_valid_basel_event_types(self):
        """Test all valid Basel event types"""
        validation_service = LossDataValidationService()
        
        valid_types = [
            'internal_fraud', 'external_fraud', 'employment_practices',
            'clients_products_business', 'damage_physical_assets',
            'business_disruption', 'execution_delivery_process'
        ]
        
        for event_type in valid_types:
            loss_event = LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 1, 15),
                discovery_date=date(2023, 1, 20),
                accounting_date=date(2023, 1, 25),
                gross_amount=Decimal('150000.00'),
                basel_event_type=event_type
            )
            
            errors = validation_service.validate_loss_event(loss_event)
            basel_errors = [e for e in errors if e.error_code == "INVALID_BASEL_EVENT_TYPE"]
            assert len(basel_errors) == 0, f"Valid Basel event type {event_type} should not generate errors"
    
    def test_valid_business_lines(self):
        """Test all valid business lines"""
        validation_service = LossDataValidationService()
        
        valid_lines = [
            'corporate_finance', 'trading_sales', 'retail_banking',
            'commercial_banking', 'payment_settlement', 'agency_services',
            'asset_management', 'retail_brokerage'
        ]
        
        for business_line in valid_lines:
            loss_event = LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 1, 15),
                discovery_date=date(2023, 1, 20),
                accounting_date=date(2023, 1, 25),
                gross_amount=Decimal('150000.00'),
                business_line=business_line
            )
            
            errors = validation_service.validate_loss_event(loss_event)
            business_line_errors = [e for e in errors if e.error_code == "INVALID_BUSINESS_LINE"]
            assert len(business_line_errors) == 0, f"Valid business line {business_line} should not generate errors"
    
    def test_negative_amounts_validation(self):
        """Test validation of negative amounts"""
        validation_service = LossDataValidationService()
        
        # Test negative gross amount (should be caught by Pydantic first, but test service validation)
        loss_event_dict = {
            "entity_id": "BANK001",
            "event_type": "operational_loss",
            "occurrence_date": date(2023, 1, 15),
            "discovery_date": date(2023, 1, 20),
            "accounting_date": date(2023, 1, 25),
            "gross_amount": Decimal('-150000.00')  # Negative amount
        }
        
        loss_event = type('LossEventCreate', (), loss_event_dict)()
        
        errors = validation_service.validate_loss_event(loss_event)
        assert any(error.error_code == "NEGATIVE_AMOUNT" for error in errors)
    
    def test_optional_fields_validation(self):
        """Test that optional fields don't cause validation errors when None"""
        validation_service = LossDataValidationService()
        
        loss_event = LossEventCreate(
            entity_id="BANK001",
            event_type="operational_loss",
            occurrence_date=date(2023, 1, 15),
            discovery_date=date(2023, 1, 20),
            accounting_date=date(2023, 1, 25),
            gross_amount=Decimal('150000.00'),
            basel_event_type=None,  # Optional field
            business_line=None,     # Optional field
            description=None        # Optional field
        )
        
        errors = validation_service.validate_loss_event(loss_event)
        # Should only have no errors for optional fields being None
        optional_field_errors = [
            e for e in errors 
            if e.error_code in ["INVALID_BASEL_EVENT_TYPE", "INVALID_BUSINESS_LINE"]
        ]
        assert len(optional_field_errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])