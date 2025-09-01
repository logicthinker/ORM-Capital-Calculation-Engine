"""
Tests for Loss Data Management System

Comprehensive tests for loss data ingestion, validation, recovery processing,
and exclusion handling according to RBI Basel III SMA requirements.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from orm_calculator.models.pydantic_models import (
    LossEventCreate, RecoveryCreate, LossEventExclusion,
    LossDataBatch, ValidationResult
)
from orm_calculator.models.orm_models import LossEvent, Recovery
from orm_calculator.services.loss_data_service import (
    LossDataManagementService, LossDataValidationService,
    RBIApprovalMetadata
)
from orm_calculator.database.repositories import RepositoryFactory


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
        
        loss_event = LossEventCreate(
            entity_id="BANK001",
            event_type="operational_loss",
            occurrence_date=date(2023, 1, 20),
            discovery_date=date(2023, 1, 15),  # Before occurrence
            accounting_date=date(2023, 1, 25),
            gross_amount=Decimal('150000.00')
        )
        
        errors = validation_service.validate_loss_event(loss_event)
        assert len(errors) > 0
        assert any(error.error_code == "INVALID_DATE_SEQUENCE" for error in errors)
    
    def test_validate_recovery_valid(self):
        """Test validation of valid recovery"""
        validation_service = LossDataValidationService()
        
        # Create mock loss event
        loss_event = LossEvent(
            id=str(uuid4()),
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
            id=str(uuid4()),
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
    
    def test_validate_exclusion_valid(self):
        """Test validation of valid exclusion with RBI approval"""
        validation_service = LossDataValidationService()
        
        loss_event = LossEvent(
            id=str(uuid4()),
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
            id=str(uuid4()),
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


@pytest.mark.asyncio
class TestLossDataIngestionService:
    """Test loss data ingestion service"""
    
    async def test_ingest_loss_events_success(self, db_session: AsyncSession):
        """Test successful loss event ingestion"""
        service = LossDataManagementService(db_session)
        
        loss_events = [
            LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 1, 15),
                discovery_date=date(2023, 1, 20),
                accounting_date=date(2023, 1, 25),
                gross_amount=Decimal('150000.00'),
                basel_event_type="internal_fraud",
                business_line="retail_banking"
            ),
            LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 2, 10),
                discovery_date=date(2023, 2, 15),
                accounting_date=date(2023, 2, 20),
                gross_amount=Decimal('250000.00'),
                basel_event_type="external_fraud",
                business_line="commercial_banking"
            )
        ]
        
        result = await service.ingest_loss_events(loss_events)
        
        assert result.success
        assert result.records_processed == 2
        assert result.records_accepted == 2
        assert result.records_rejected == 0
        assert len(result.errors) == 0
    
    async def test_ingest_loss_events_validation_errors(self, db_session: AsyncSession):
        """Test loss event ingestion with validation errors"""
        service = LossDataManagementService(db_session)
        
        loss_events = [
            LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 1, 15),
                discovery_date=date(2023, 1, 20),
                accounting_date=date(2023, 1, 25),
                gross_amount=Decimal('150000.00')  # Valid
            ),
            LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 2, 10),
                discovery_date=date(2023, 2, 15),
                accounting_date=date(2023, 2, 20),
                gross_amount=Decimal('50000.00')  # Below threshold
            )
        ]
        
        result = await service.ingest_loss_events(loss_events)
        
        assert not result.success
        assert result.records_processed == 2
        assert result.records_accepted == 1
        assert result.records_rejected == 1
        assert len(result.errors) > 0
    
    async def test_add_recovery_success(self, db_session: AsyncSession):
        """Test successful recovery addition"""
        service = LossDataManagementService(db_session)
        
        # First create a loss event
        loss_events = [
            LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 1, 15),
                discovery_date=date(2023, 1, 20),
                accounting_date=date(2023, 1, 25),
                gross_amount=Decimal('150000.00')
            )
        ]
        
        ingestion_result = await service.ingest_loss_events(loss_events)
        assert ingestion_result.success
        
        # Get the created loss event
        loss_event = await service.ingestion_service.loss_repo.find_by_entity_and_date_range(
            "BANK001", date(2023, 1, 1), date(2023, 12, 31)
        )
        assert len(loss_event) == 1
        
        # Add recovery
        recovery = RecoveryCreate(
            loss_event_id=loss_event[0].id,
            amount=Decimal('25000.00'),
            receipt_date=date(2023, 3, 15),
            recovery_type="insurance"
        )
        
        recovery_response, errors = await service.add_recovery(recovery)
        
        assert recovery_response is not None
        assert len(errors) == 0
        assert recovery_response.amount == Decimal('25000.00')
        
        # Verify net loss was recalculated
        updated_loss_event = await service.ingestion_service.loss_repo.find_by_id(loss_event[0].id)
        assert updated_loss_event.net_amount == Decimal('125000.00')  # 150000 - 25000
    
    async def test_exclude_loss_event_success(self, db_session: AsyncSession):
        """Test successful loss event exclusion"""
        service = LossDataManagementService(db_session)
        
        # Create loss event
        loss_events = [
            LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 1, 15),
                discovery_date=date(2023, 1, 20),
                accounting_date=date(2023, 1, 25),
                gross_amount=Decimal('150000.00')
            )
        ]
        
        ingestion_result = await service.ingest_loss_events(loss_events)
        assert ingestion_result.success
        
        # Get the created loss event
        loss_event = await service.ingestion_service.loss_repo.find_by_entity_and_date_range(
            "BANK001", date(2023, 1, 1), date(2023, 12, 31)
        )
        assert len(loss_event) == 1
        
        # Create RBI approval
        rbi_approval = RBIApprovalMetadata(
            approval_reference="RBI/2023/001",
            approval_date=date(2023, 2, 1),
            approving_authority="RBI Mumbai",
            approval_reason="Regulatory exclusion approved"
        )
        
        # Exclude loss event
        success, errors = await service.exclude_loss_event(
            loss_event[0].id,
            "Regulatory exclusion",
            rbi_approval
        )
        
        assert success
        assert len(errors) == 0
        
        # Verify exclusion was applied
        updated_loss_event = await service.ingestion_service.loss_repo.find_by_id(loss_event[0].id)
        assert updated_loss_event.is_excluded
        assert updated_loss_event.exclusion_reason == "Regulatory exclusion"
        assert updated_loss_event.rbi_approval_reference == "RBI/2023/001"
        assert updated_loss_event.disclosure_required


@pytest.mark.asyncio
class TestLossDataQueryService:
    """Test loss data query service"""
    
    async def test_get_losses_above_threshold(self, db_session: AsyncSession):
        """Test querying losses above threshold"""
        service = LossDataManagementService(db_session)
        
        # Create test data
        loss_events = [
            LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 1, 15),
                discovery_date=date(2023, 1, 20),
                accounting_date=date(2023, 1, 25),
                gross_amount=Decimal('150000.00')
            ),
            LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 2, 10),
                discovery_date=date(2023, 2, 15),
                accounting_date=date(2023, 2, 20),
                gross_amount=Decimal('250000.00')
            )
        ]
        
        await service.ingest_loss_events(loss_events)
        
        # Query losses above threshold
        losses = await service.query_service.get_losses_above_threshold(
            entity_id="BANK001",
            threshold=Decimal('200000.00'),
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31)
        )
        
        assert len(losses) == 1
        assert losses[0].gross_amount == Decimal('250000.00')
    
    async def test_get_losses_for_calculation(self, db_session: AsyncSession):
        """Test getting losses for SMA calculation"""
        service = LossDataManagementService(db_session)
        
        # Create test data spanning multiple years
        loss_events = []
        for year in range(2020, 2024):
            loss_events.append(
                LossEventCreate(
                    entity_id="BANK001",
                    event_type="operational_loss",
                    occurrence_date=date(year, 6, 15),
                    discovery_date=date(year, 6, 20),
                    accounting_date=date(year, 6, 25),
                    gross_amount=Decimal('150000.00')
                )
            )
        
        await service.ingest_loss_events(loss_events)
        
        # Get losses for calculation (10-year lookback from 2023)
        losses = await service.get_losses_for_calculation(
            entity_id="BANK001",
            calculation_date=date(2023, 12, 31),
            lookback_years=10
        )
        
        # Should include losses from 2014-2023, but we only have 2020-2023
        assert len(losses) == 4
        assert all(loss.entity_id == "BANK001" for loss in losses)
        assert all(loss.gross_amount >= Decimal('100000.00') for loss in losses)
    
    async def test_get_loss_statistics(self, db_session: AsyncSession):
        """Test getting loss statistics"""
        service = LossDataManagementService(db_session)
        
        # Create test data
        loss_events = [
            LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 1, 15),
                discovery_date=date(2023, 1, 20),
                accounting_date=date(2023, 1, 25),
                gross_amount=Decimal('150000.00')
            ),
            LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 2, 10),
                discovery_date=date(2023, 2, 15),
                accounting_date=date(2023, 2, 20),
                gross_amount=Decimal('250000.00')
            )
        ]
        
        await service.ingest_loss_events(loss_events)
        
        # Get statistics
        stats = await service.get_loss_statistics(
            entity_id="BANK001",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31)
        )
        
        assert stats['total_events'] == 2
        assert stats['total_gross_amount'] == Decimal('400000.00')
        assert stats['total_net_amount'] == Decimal('400000.00')
        assert stats['average_gross_amount'] == Decimal('200000.00')
        assert stats['maximum_gross_amount'] == Decimal('250000.00')
        assert stats['minimum_gross_amount'] == Decimal('150000.00')


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


@pytest.mark.asyncio
class TestLossDataIntegration:
    """Integration tests for loss data management"""
    
    async def test_complete_loss_lifecycle(self, db_session: AsyncSession):
        """Test complete loss event lifecycle: create -> add recovery -> exclude"""
        service = LossDataManagementService(db_session)
        
        # 1. Create loss event
        loss_events = [
            LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 1, 15),
                discovery_date=date(2023, 1, 20),
                accounting_date=date(2023, 1, 25),
                gross_amount=Decimal('200000.00'),
                basel_event_type="internal_fraud",
                business_line="retail_banking",
                description="Test loss event"
            )
        ]
        
        ingestion_result = await service.ingest_loss_events(loss_events)
        assert ingestion_result.success
        
        # Get created loss event
        loss_event = await service.ingestion_service.loss_repo.find_by_entity_and_date_range(
            "BANK001", date(2023, 1, 1), date(2023, 12, 31)
        )
        assert len(loss_event) == 1
        loss_event_id = loss_event[0].id
        
        # 2. Add recovery
        recovery = RecoveryCreate(
            loss_event_id=loss_event_id,
            amount=Decimal('50000.00'),
            receipt_date=date(2023, 3, 15),
            recovery_type="insurance",
            description="Insurance recovery"
        )
        
        recovery_response, errors = await service.add_recovery(recovery)
        assert recovery_response is not None
        assert len(errors) == 0
        
        # Verify net loss calculation
        updated_loss_event = await service.ingestion_service.loss_repo.find_by_id(loss_event_id)
        assert updated_loss_event.net_amount == Decimal('150000.00')
        
        # 3. Exclude loss event
        rbi_approval = RBIApprovalMetadata(
            approval_reference="RBI/2023/001",
            approval_date=date(2023, 4, 1),
            approving_authority="RBI Mumbai",
            approval_reason="Regulatory exclusion approved"
        )
        
        success, errors = await service.exclude_loss_event(
            loss_event_id,
            "Regulatory exclusion per RBI guidelines",
            rbi_approval
        )
        
        assert success
        assert len(errors) == 0
        
        # Verify final state
        final_loss_event = await service.ingestion_service.loss_repo.find_by_id(loss_event_id)
        assert final_loss_event.is_excluded
        assert final_loss_event.disclosure_required
        assert final_loss_event.net_amount == Decimal('150000.00')  # Net amount preserved
    
    async def test_threshold_filtering_for_sma(self, db_session: AsyncSession):
        """Test threshold filtering for SMA calculations"""
        service = LossDataManagementService(db_session)
        
        # Create losses with different amounts
        loss_events = [
            LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 1, 15),
                discovery_date=date(2023, 1, 20),
                accounting_date=date(2023, 1, 25),
                gross_amount=Decimal('50000.00')  # Below threshold
            ),
            LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 2, 15),
                discovery_date=date(2023, 2, 20),
                accounting_date=date(2023, 2, 25),
                gross_amount=Decimal('150000.00')  # Above threshold
            ),
            LossEventCreate(
                entity_id="BANK001",
                event_type="operational_loss",
                occurrence_date=date(2023, 3, 15),
                discovery_date=date(2023, 3, 20),
                accounting_date=date(2023, 3, 25),
                gross_amount=Decimal('300000.00')  # Above threshold
            )
        ]
        
        # Ingest with custom threshold to allow the first one
        custom_service = LossDataManagementService(db_session, Decimal('25000.00'))
        result = await custom_service.ingest_loss_events(loss_events)
        
        # All should be accepted with lower threshold
        assert result.success
        assert result.records_accepted == 3
        
        # Query with default threshold (₹1,00,000)
        losses_for_calculation = await service.get_losses_for_calculation(
            entity_id="BANK001",
            calculation_date=date(2023, 12, 31)
        )
        
        # Only 2 should be returned (above ₹1,00,000)
        assert len(losses_for_calculation) == 2
        assert all(loss.gross_amount >= Decimal('100000.00') for loss in losses_for_calculation)