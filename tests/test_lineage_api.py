"""
Tests for Lineage API endpoints

Tests the REST API endpoints for data lineage tracking and audit trail access.
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from orm_calculator.api import create_app
from orm_calculator.services.lineage_service import LineageService
from orm_calculator.models.pydantic_models import CalculationRequest, CalculationResult, ModelNameEnum, ExecutionModeEnum
from orm_calculator.database.connection import db_manager


@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
async def setup_test_lineage():
    """Setup test lineage data"""
    run_id = f"test_run_{uuid4().hex[:8]}"
    
    request = CalculationRequest(
        model_name=ModelNameEnum.SMA,
        execution_mode=ExecutionModeEnum.SYNC,
        entity_id="TEST_ENTITY_001",
        calculation_date=date(2024, 1, 1),
        parameters={"test_param": "test_value"}
    )
    
    result = CalculationResult(
        run_id=run_id,
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
    
    # Create complete lineage
    async with db_manager.get_session() as session:
        lineage_service = LineageService(session)
        
        # Create initial record
        await lineage_service.create_lineage_record(run_id, request, "test_user")
        
        # Add data inputs
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
        
        # Add parameter versions
        await lineage_service.record_parameter_versions(run_id, ["param_v1.0.0"], "model_v1.0.0")
        
        # Add results
        intermediates = {
            "business_indicator": 1800000000,
            "business_indicator_component": 216000000,
            "loss_component": 1125000000,
            "internal_loss_multiplier": 1.5
        }
        
        await lineage_service.store_calculation_results(run_id, result, intermediates)
    
    return run_id


class TestLineageAPI:
    """Test cases for Lineage API endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_lineage_success(self, client, setup_test_lineage):
        """Test successful lineage retrieval"""
        run_id = await setup_test_lineage
        
        response = client.get(f"/api/v1/lineage/{run_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == run_id
        assert "final_outputs" in data
        assert "intermediates" in data
        assert "parameter_versions" in data
        assert "model_versions" in data
        assert "input_aggregates" in data
        assert "included_loss_ids" in data
        assert "environment_hash" in data
        assert data["reproducible"] is True
        
        # Verify final outputs
        assert "operational_risk_capital" in data["final_outputs"]
        assert "risk_weighted_assets" in data["final_outputs"]
        
        # Verify intermediates
        assert "business_indicator" in data["intermediates"]
        assert "business_indicator_component" in data["intermediates"]
        assert "loss_component" in data["intermediates"]
        assert "internal_loss_multiplier" in data["intermediates"]
        
        # Verify parameter versions
        assert data["parameter_versions"] == ["param_v1.0.0"]
        assert data["model_versions"] == ["model_v1.0.0"]
        
        # Verify included loss IDs
        assert data["included_loss_ids"] == ["loss_test_001"]
    
    def test_get_lineage_not_found(self, client):
        """Test lineage retrieval for non-existent run_id"""
        non_existent_run_id = "non_existent_run"
        
        response = client.get(f"/api/v1/lineage/{non_existent_run_id}")
        
        assert response.status_code == 404
        data = response.json()
        
        assert data["error_code"] == "LINEAGE_NOT_FOUND"
        assert non_existent_run_id in data["error_message"]
        assert data["details"]["run_id"] == non_existent_run_id
    
    @pytest.mark.asyncio
    async def test_get_audit_trail_success(self, client, setup_test_lineage):
        """Test successful audit trail retrieval"""
        run_id = await setup_test_lineage
        
        response = client.get(f"/api/v1/lineage/{run_id}/audit")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 2  # At least start and completion records
        
        # Verify audit record structure
        for record in data:
            assert "id" in record
            assert "run_id" in record
            assert record["run_id"] == run_id
            assert "operation" in record
            assert "initiator" in record
            assert "timestamp" in record
            assert "immutable_hash" in record
            assert "created_at" in record
        
        # Verify we have start and completion operations
        operations = [record["operation"] for record in data]
        assert "calculation_started" in operations
        assert "calculation_completed" in operations
    
    def test_get_audit_trail_not_found(self, client):
        """Test audit trail retrieval for non-existent run_id"""
        non_existent_run_id = "non_existent_run"
        
        response = client.get(f"/api/v1/lineage/{non_existent_run_id}/audit")
        
        assert response.status_code == 404
        data = response.json()
        
        assert data["error_code"] == "AUDIT_TRAIL_NOT_FOUND"
        assert non_existent_run_id in data["error_message"]
    
    @pytest.mark.asyncio
    async def test_verify_data_integrity_success(self, client, setup_test_lineage):
        """Test successful data integrity verification"""
        run_id = await setup_test_lineage
        
        response = client.get(f"/api/v1/lineage/{run_id}/integrity")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == run_id
        assert data["overall_integrity"] is True
        assert data["total_records"] >= 2
        assert data["valid_records"] == data["total_records"]
        assert data["invalid_records"] == 0
        assert "record_integrity" in data
        assert "verification_timestamp" in data
        
        # Verify all records are valid
        for record_id, is_valid in data["record_integrity"].items():
            assert is_valid is True
    
    def test_verify_data_integrity_not_found(self, client):
        """Test data integrity verification for non-existent run_id"""
        non_existent_run_id = "non_existent_run"
        
        response = client.get(f"/api/v1/lineage/{non_existent_run_id}/integrity")
        
        assert response.status_code == 404
        data = response.json()
        
        assert data["error_code"] == "INTEGRITY_CHECK_NOT_FOUND"
        assert non_existent_run_id in data["error_message"]
    
    @pytest.mark.asyncio
    async def test_check_reproducibility_success(self, client, setup_test_lineage):
        """Test successful reproducibility check"""
        run_id = await setup_test_lineage
        
        response = client.get(f"/api/v1/lineage/{run_id}/reproducibility")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == run_id
        assert data["reproducible"] is True
        assert data["reproducibility_score"] == 1.0  # 100% complete
        assert "components" in data
        assert "missing_components" in data
        assert "check_timestamp" in data
        
        # Verify all components are present
        components = data["components"]
        assert components["final_outputs"] is True
        assert components["intermediates"] is True
        assert components["parameter_versions"] is True
        assert components["model_versions"] is True
        assert components["input_aggregates"] is True
        assert components["environment_hash"] is True
        
        # No missing components
        assert len(data["missing_components"]) == 0
    
    def test_check_reproducibility_not_found(self, client):
        """Test reproducibility check for non-existent run_id"""
        non_existent_run_id = "non_existent_run"
        
        response = client.get(f"/api/v1/lineage/{non_existent_run_id}/reproducibility")
        
        assert response.status_code == 404
        data = response.json()
        
        assert data["error_code"] == "REPRODUCIBILITY_CHECK_NOT_FOUND"
        assert non_existent_run_id in data["error_message"]
    
    def test_invalid_run_id_format(self, client):
        """Test handling of invalid run_id format"""
        invalid_run_id = ""
        
        response = client.get(f"/api/v1/lineage/{invalid_run_id}")
        
        # Should return 404 for empty run_id
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_lineage_api_error_handling(self, client):
        """Test API error handling for various scenarios"""
        # Test with special characters in run_id
        special_run_id = "run@#$%"
        
        response = client.get(f"/api/v1/lineage/{special_run_id}")
        assert response.status_code == 404
        
        # Test with very long run_id
        long_run_id = "a" * 1000
        
        response = client.get(f"/api/v1/lineage/{long_run_id}")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_lineage_api_response_format(self, client, setup_test_lineage):
        """Test that API responses follow the expected format"""
        run_id = await setup_test_lineage
        
        # Test lineage endpoint
        response = client.get(f"/api/v1/lineage/{run_id}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        # Test audit endpoint
        response = client.get(f"/api/v1/lineage/{run_id}/audit")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        # Test integrity endpoint
        response = client.get(f"/api/v1/lineage/{run_id}/integrity")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        # Test reproducibility endpoint
        response = client.get(f"/api/v1/lineage/{run_id}/reproducibility")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_lineage_api_integration():
    """Integration test for lineage API with actual calculation"""
    from orm_calculator.services.calculation_service import CalculationService
    
    app = create_app()
    client = TestClient(app)
    
    calculation_service = CalculationService()
    
    request = CalculationRequest(
        model_name=ModelNameEnum.SMA,
        execution_mode=ExecutionModeEnum.SYNC,
        entity_id="API_INTEGRATION_TEST_001",
        calculation_date=date(2024, 1, 1)
    )
    
    run_id = f"api_integration_test_{uuid4().hex[:8]}"
    
    # Execute calculation with lineage tracking
    result = await calculation_service.execute_calculation(request, run_id, "api_integration_test")
    
    # Test lineage API endpoints
    response = client.get(f"/api/v1/lineage/{run_id}")
    assert response.status_code == 200
    
    lineage_data = response.json()
    assert lineage_data["run_id"] == run_id
    assert lineage_data["reproducible"] is True
    
    # Test audit trail
    response = client.get(f"/api/v1/lineage/{run_id}/audit")
    assert response.status_code == 200
    
    audit_data = response.json()
    assert len(audit_data) >= 2
    
    # Test integrity verification
    response = client.get(f"/api/v1/lineage/{run_id}/integrity")
    assert response.status_code == 200
    
    integrity_data = response.json()
    assert integrity_data["overall_integrity"] is True
    
    # Test reproducibility check
    response = client.get(f"/api/v1/lineage/{run_id}/reproducibility")
    assert response.status_code == 200
    
    reproducibility_data = response.json()
    assert reproducibility_data["reproducible"] is True
    assert reproducibility_data["reproducibility_score"] == 1.0