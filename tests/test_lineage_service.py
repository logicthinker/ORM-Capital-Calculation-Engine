"""
Tests for Lineage Service

Tests data lineage tracking, audit trail functionality, and data integrity verification.
"""

import pytest
import pytest_asyncio
import json
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from orm_calculator.services.lineage_service import LineageService
from orm_calculator.models.pydantic_models import CalculationRequest, CalculationResult, ModelNameEnum, ExecutionModeEnum
from orm_calculator.models.orm_models import AuditTrail
from orm_calculator.database.connection import db_manager


@pytest_asyncio.fixture
async def lineage_service():
    """Create lineage service with database session"""
    # Initialize database first
    await db_manager.initialize()
    
    async with db_manager.get_session() as session:
        yield LineageService(session)


@pytest.fixture
def sample_calculation_request():
    """Sample calculation request for testing"""
    return CalculationRequest(
        model_name=ModelNameEnum.SMA,
        execution_mode=ExecutionModeEnum.SYNC,
        entity_id="TEST_ENTITY_001",
        calculation_date=date(2024, 1, 1),
        parameters={"test_param": "test_value"},
        correlation_id="test_correlation_001"
    )


@pytest.fixture
def sample_calculation_result():
    """Sample calculation result for testing"""
    return CalculationResult(
        run_id="test_run_001",
        entity_id="TEST_ENTITY_001",
        calculation_date=date(2024, 1, 1),
        methodology=ModelNameEnum.SMA,
        business_indicator=Decimal('1800000000'),
        business_indicator_component=Decimal('216000000'),
        loss_component=Decimal('1125000000'),
        internal_loss_multiplier=Decimal('1.5'),
        operational_risk_capital=Decimal('324000000'),
        risk_weighted_assets=Decimal('4050000000'),
        bucket=2,
        ilm_gated=False,
        parameter_version="1.0.0",
        model_version="1.0.0",
        supervisor_override=False,
        created_at=datetime.utcnow()
    )


class TestLineageService:
    """Test cases for LineageService"""
    
    @pytest.mark.asyncio
    async def test_create_lineage_record(self, lineage_service, sample_calculation_request):
        """Test creating initial lineage record"""
        run_id = f"test_run_{uuid4().hex[:8]}"
        
        audit_id = await lineage_service.create_lineage_record(
            run_id, 
            sample_calculation_request, 
            "test_user"
        )
        
        assert audit_id is not None
        assert len(audit_id) > 0
        
        # Verify record was created
        audit_records = await lineage_service.get_audit_records(run_id)
        assert len(audit_records) == 1
        assert audit_records[0].run_id == run_id
        assert audit_records[0].operation == "calculation_started"
        assert audit_records[0].initiator == "test_user"
    
    @pytest.mark.asyncio
    async def test_track_data_inputs(self, lineage_service, sample_calculation_request):
        """Test tracking data inputs"""
        run_id = f"test_run_{uuid4().hex[:8]}"
        
        # Create initial record
        await lineage_service.create_lineage_record(run_id, sample_calculation_request)
        
        # Track data inputs
        bi_data = [
            {
                "id": "bi_test_001",
                "entity_id": "TEST_ENTITY_001",
                "period": "2023-Q4",
                "ildc": 1000000000,
                "sc": 500000000,
                "fc": 300000000,
                "calculation_date": "2024-01-01"
            }
        ]
        
        loss_data = [
            {
                "id": "loss_test_001",
                "entity_id": "TEST_ENTITY_001",
                "accounting_date": "2023-06-15",
                "net_loss": 50000000,
                "is_excluded": False
            }
        ]
        
        await lineage_service.track_data_inputs(run_id, bi_data, loss_data)
        
        # Verify data was tracked
        audit_records = await lineage_service.get_audit_records(run_id)
        assert len(audit_records) == 1
        
        input_snapshot = audit_records[0].input_snapshot
        assert input_snapshot is not None
        assert "data_inputs" in input_snapshot
        assert input_snapshot["data_inputs"]["input_count"]["bi_records"] == 1
        assert input_snapshot["data_inputs"]["input_count"]["loss_records"] == 1
    
    @pytest.mark.asyncio
    async def test_record_parameter_versions(self, lineage_service, sample_calculation_request):
        """Test recording parameter versions"""
        run_id = f"test_run_{uuid4().hex[:8]}"
        
        # Create initial record
        await lineage_service.create_lineage_record(run_id, sample_calculation_request)
        
        # Record parameter versions
        parameter_versions = ["param_v1.0.0", "param_v1.1.0"]
        model_version = "model_v1.0.0"
        
        await lineage_service.record_parameter_versions(run_id, parameter_versions, model_version)
        
        # Verify versions were recorded
        audit_records = await lineage_service.get_audit_records(run_id)
        assert len(audit_records) == 1
        assert audit_records[0].parameter_versions == parameter_versions
        assert audit_records[0].model_version == model_version
    
    @pytest.mark.asyncio
    async def test_store_calculation_results(self, lineage_service, sample_calculation_request, sample_calculation_result):
        """Test storing calculation results"""
        run_id = sample_calculation_result.run_id
        
        # Create initial record
        await lineage_service.create_lineage_record(run_id, sample_calculation_request)
        
        # Store results
        intermediates = {
            "business_indicator": 1800000000,
            "business_indicator_component": 216000000,
            "loss_component": 1125000000,
            "internal_loss_multiplier": 1.5
        }
        
        await lineage_service.store_calculation_results(run_id, sample_calculation_result, intermediates)
        
        # Verify results were stored
        audit_records = await lineage_service.get_audit_records(run_id)
        assert len(audit_records) == 2  # Initial + completion record
        
        completion_record = next(r for r in audit_records if r.operation == "calculation_completed")
        assert completion_record.outputs is not None
        assert completion_record.intermediates is not None
        assert completion_record.outputs["operational_risk_capital"] == float(sample_calculation_result.operational_risk_capital)
    
    @pytest.mark.asyncio
    async def test_store_calculation_error(self, lineage_service, sample_calculation_request):
        """Test storing calculation errors"""
        run_id = f"test_run_{uuid4().hex[:8]}"
        
        # Create initial record
        await lineage_service.create_lineage_record(run_id, sample_calculation_request)
        
        # Store error
        error_details = {
            "error_type": "ValueError",
            "error_message": "Invalid input data",
            "calculation_method": "SMA"
        }
        
        await lineage_service.store_calculation_error(run_id, error_details)
        
        # Verify error was stored
        audit_records = await lineage_service.get_audit_records(run_id)
        assert len(audit_records) == 2  # Initial + error record
        
        error_record = next(r for r in audit_records if r.operation == "calculation_failed")
        assert error_record.errors is not None
        assert error_record.errors[0]["error_type"] == "ValueError"
    
    @pytest.mark.asyncio
    async def test_get_complete_lineage(self, lineage_service, sample_calculation_request, sample_calculation_result):
        """Test retrieving complete lineage"""
        run_id = sample_calculation_result.run_id
        
        # Create complete lineage
        await lineage_service.create_lineage_record(run_id, sample_calculation_request)
        
        # Add data inputs
        bi_data = [{"id": "bi_001", "entity_id": "TEST_ENTITY_001"}]
        loss_data = [{"id": "loss_001", "entity_id": "TEST_ENTITY_001"}]
        await lineage_service.track_data_inputs(run_id, bi_data, loss_data)
        
        # Add parameter versions
        await lineage_service.record_parameter_versions(run_id, ["param_v1.0.0"], "model_v1.0.0")
        
        # Add results
        intermediates = {"business_indicator": 1800000000}
        await lineage_service.store_calculation_results(run_id, sample_calculation_result, intermediates)
        
        # Get complete lineage
        lineage = await lineage_service.get_complete_lineage(run_id)
        
        assert lineage is not None
        assert lineage.run_id == run_id
        assert lineage.final_outputs is not None
        assert lineage.intermediates is not None
        assert lineage.parameter_versions == ["param_v1.0.0"]
        assert lineage.model_versions == ["model_v1.0.0"]
        assert lineage.included_loss_ids == ["loss_001"]
        assert lineage.reproducible is True
    
    @pytest.mark.asyncio
    async def test_verify_data_integrity(self, lineage_service, sample_calculation_request):
        """Test data integrity verification"""
        run_id = f"test_run_{uuid4().hex[:8]}"
        
        # Create lineage record
        await lineage_service.create_lineage_record(run_id, sample_calculation_request)
        
        # Verify integrity
        integrity_results = await lineage_service.verify_data_integrity(run_id)
        
        assert len(integrity_results) == 1
        assert all(integrity_results.values())  # All records should be valid
    
    @pytest.mark.asyncio
    async def test_data_hash_generation(self, lineage_service):
        """Test data hash generation for consistency"""
        data1 = [{"id": "1", "value": "test"}, {"id": "2", "value": "test2"}]
        data2 = [{"id": "2", "value": "test2"}, {"id": "1", "value": "test"}]  # Different order
        
        hash1 = lineage_service._generate_data_hash(data1)
        hash2 = lineage_service._generate_data_hash(data2)
        
        # Hashes should be the same regardless of order
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64-character hex string
    
    @pytest.mark.asyncio
    async def test_environment_hash_generation(self, lineage_service):
        """Test environment hash generation"""
        run_id = f"test_run_{uuid4().hex[:8]}"
        
        env_hash = await lineage_service._generate_environment_hash(run_id)
        
        assert env_hash is not None
        assert len(env_hash) == 64  # SHA-256 produces 64-character hex string
    
    @pytest.mark.asyncio
    async def test_lineage_not_found(self, lineage_service):
        """Test handling of non-existent lineage"""
        non_existent_run_id = "non_existent_run"
        
        lineage = await lineage_service.get_complete_lineage(non_existent_run_id)
        assert lineage is None
        
        audit_records = await lineage_service.get_audit_records(non_existent_run_id)
        assert len(audit_records) == 0
        
        integrity_results = await lineage_service.verify_data_integrity(non_existent_run_id)
        assert len(integrity_results) == 0


@pytest.mark.asyncio
async def test_lineage_integration_with_calculation():
    """Integration test for lineage tracking with actual calculation"""
    from orm_calculator.services.calculation_service import CalculationService
    
    # Initialize database first
    await db_manager.initialize()
    
    calculation_service = CalculationService()
    
    request = CalculationRequest(
        model_name=ModelNameEnum.SMA,
        execution_mode=ExecutionModeEnum.SYNC,
        entity_id="INTEGRATION_TEST_001",
        calculation_date=date(2024, 1, 1)
    )
    
    run_id = f"integration_test_{uuid4().hex[:8]}"
    
    # Execute calculation with lineage tracking
    result = await calculation_service.execute_calculation(request, run_id, "integration_test")
    
    # Verify lineage was created
    async with db_manager.get_session() as session:
        lineage_service = LineageService(session)
        lineage = await lineage_service.get_complete_lineage(run_id)
        
        assert lineage is not None
        assert lineage.run_id == run_id
        assert lineage.final_outputs is not None
        assert lineage.intermediates is not None
        assert lineage.reproducible is True
        
        # Verify audit records
        audit_records = await lineage_service.get_audit_records(run_id)
        assert len(audit_records) >= 2  # At least start and completion records
        
        # Verify data integrity
        integrity_results = await lineage_service.verify_data_integrity(run_id)
        assert all(integrity_results.values())  # All records should be valid