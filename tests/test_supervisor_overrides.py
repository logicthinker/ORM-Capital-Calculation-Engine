"""
Tests for supervisor override functionality
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock

from orm_calculator.models.override_models import (
    SupervisorOverride, OverrideAuditLog,
    OverrideType, OverrideStatus, OverrideReason,
    SupervisorOverrideCreate, OverrideApproval, OverrideApplication
)
from orm_calculator.services.override_service import OverrideService
from orm_calculator.api import create_app


@pytest.fixture
def app():
    """Create test application"""
    with patch('orm_calculator.config.get_config') as mock_config:
        from orm_calculator.config import DevelopmentConfig
        mock_config.return_value = DevelopmentConfig()
        return create_app()


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session"""
    return AsyncMock(spec=Session)


@pytest.fixture
def override_service(mock_db):
    """Create override service with mock database"""
    return OverrideService(mock_db)


@pytest.fixture
def sample_override_create():
    """Sample override creation data"""
    return SupervisorOverrideCreate(
        id="OVR_001",
        override_type=OverrideType.CAPITAL_ADJUSTMENT,
        entity_id="BANK_001",
        original_value=Decimal('100000000'),
        override_value=Decimal('120000000'),
        percentage_adjustment=Decimal('20'),
        override_reason=OverrideReason.CONSERVATIVE_ADJUSTMENT,
        detailed_justification="Conservative adjustment due to market volatility",
        proposed_by="risk_manager_1",
        effective_from=date.today(),
        effective_to=date.today() + timedelta(days=90),
        business_context="Market stress conditions require conservative capital buffer"
    )


@pytest.fixture
def sample_override():
    """Sample supervisor override"""
    return SupervisorOverride(
        id="OVR_001",
        override_type=OverrideType.CAPITAL_ADJUSTMENT,
        status=OverrideStatus.PROPOSED,
        entity_id="BANK_001",
        original_value=Decimal('100000000'),
        override_value=Decimal('120000000'),
        percentage_adjustment=Decimal('20'),
        override_reason=OverrideReason.CONSERVATIVE_ADJUSTMENT,
        detailed_justification="Conservative adjustment due to market volatility",
        proposed_by="risk_manager_1",
        effective_from=date.today(),
        effective_to=date.today() + timedelta(days=90),
        requires_disclosure=True,
        disclosure_period_months=12,
        rbi_notification_required=True
    )


class TestOverrideModels:
    """Test override model functionality"""
    
    def test_override_create_validation(self):
        """Test override creation validation"""
        # Valid override
        override_data = SupervisorOverrideCreate(
            id="OVR_001",
            override_type=OverrideType.ILM_OVERRIDE,
            entity_id="BANK_001",
            override_value=Decimal('1.5'),
            override_reason=OverrideReason.DATA_QUALITY_ISSUE,
            detailed_justification="Loss data quality issues require ILM adjustment",
            proposed_by="risk_manager_1",
            effective_from=date.today()
        )
        
        assert override_data.id == "OVR_001"
        assert override_data.override_type == OverrideType.ILM_OVERRIDE
        assert override_data.override_value == Decimal('1.5')
    
    def test_override_percentage_validation(self):
        """Test percentage adjustment validation"""
        with pytest.raises(ValueError, match="Percentage adjustment must be between -100% and 1000%"):
            SupervisorOverrideCreate(
                id="OVR_001",
                override_type=OverrideType.CAPITAL_ADJUSTMENT,
                entity_id="BANK_001",
                override_value=Decimal('100000000'),
                percentage_adjustment=Decimal('1500'),  # Invalid: >1000%
                override_reason=OverrideReason.CONSERVATIVE_ADJUSTMENT,
                detailed_justification="Test",
                proposed_by="test_user",
                effective_from=date.today()
            )
    
    def test_effective_dates_validation(self):
        """Test effective dates validation"""
        with pytest.raises(ValueError, match="Effective to date must be after effective from date"):
            SupervisorOverrideCreate(
                id="OVR_001",
                override_type=OverrideType.CAPITAL_ADJUSTMENT,
                entity_id="BANK_001",
                override_value=Decimal('100000000'),
                override_reason=OverrideReason.CONSERVATIVE_ADJUSTMENT,
                detailed_justification="Test",
                proposed_by="test_user",
                effective_from=date.today(),
                effective_to=date.today() - timedelta(days=1)  # Invalid: before effective_from
            )


class TestOverrideService:
    """Test override service business logic"""
    
    @pytest.mark.asyncio
    async def test_create_override(self, override_service, sample_override_create):
        """Test override creation"""
        # Mock validation
        with patch.object(override_service, '_validate_override') as mock_validate:
            mock_validate.return_value.is_valid = True
            mock_validate.return_value.validation_errors = []
            
            with patch.object(override_service, '_set_disclosure_requirements') as mock_disclosure:
                with patch.object(override_service, '_create_audit_log') as mock_audit:
                    result = await override_service.create_override(sample_override_create)
                    
                    override_service.db.add.assert_called_once()
                    override_service.db.commit.assert_called_once()
                    mock_audit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_approve_override(self, override_service, sample_override):
        """Test override approval"""
        override_service.db.query.return_value.filter.return_value.first.return_value = sample_override
        
        approval = OverrideApproval(
            approved_by="model_risk_manager_1",
            approval_reference="APP_2025_001",
            approval_comments="Approved based on risk assessment"
        )
        
        with patch.object(override_service, '_create_audit_log') as mock_audit:
            result = await override_service.approve_override("OVR_001", approval)
            
            assert result.status == OverrideStatus.APPROVED
            assert result.approved_by == "model_risk_manager_1"
            assert result.approval_reference == "APP_2025_001"
            override_service.db.commit.assert_called_once()
            mock_audit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_apply_override(self, override_service, sample_override):
        """Test override application"""
        # Set override as approved
        sample_override.status = OverrideStatus.APPROVED
        override_service.db.query.return_value.filter.return_value.first.return_value = sample_override
        
        application = OverrideApplication(
            applied_by="risk_manager_1",
            application_comments="Applied to quarterly calculation",
            calculation_impact={"orc_change": "20000000"}
        )
        
        with patch.object(override_service, '_is_override_effective') as mock_effective:
            mock_effective.return_value = True
            
            with patch.object(override_service, '_create_audit_log') as mock_audit:
                result = await override_service.apply_override("OVR_001", application)
                
                assert result.status == OverrideStatus.APPLIED
                assert result.applied_by == "risk_manager_1"
                override_service.db.commit.assert_called_once()
                mock_audit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reject_override(self, override_service, sample_override):
        """Test override rejection"""
        override_service.db.query.return_value.filter.return_value.first.return_value = sample_override
        
        with patch.object(override_service, '_create_audit_log') as mock_audit:
            result = await override_service.reject_override(
                "OVR_001", "model_risk_manager_1", "Insufficient justification"
            )
            
            assert result.status == OverrideStatus.REJECTED
            override_service.db.commit.assert_called_once()
            mock_audit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_active_overrides(self, override_service):
        """Test getting active overrides"""
        active_override = SupervisorOverride(
            id="OVR_001",
            entity_id="BANK_001",
            status=OverrideStatus.APPLIED,
            effective_from=date.today() - timedelta(days=30),
            effective_to=date.today() + timedelta(days=30)
        )
        
        override_service.db.query.return_value.filter.return_value.all.return_value = [active_override]
        
        result = await override_service.get_active_overrides("BANK_001", date.today())
        
        assert len(result) == 1
        assert result[0].id == "OVR_001"
    
    @pytest.mark.asyncio
    async def test_apply_overrides_to_calculation(self, override_service):
        """Test applying overrides to calculation results"""
        # Mock active overrides
        capital_override = SupervisorOverride(
            id="OVR_001",
            override_type=OverrideType.CAPITAL_ADJUSTMENT,
            override_value=Decimal('150000000')
        )
        
        ilm_override = SupervisorOverride(
            id="OVR_002",
            override_type=OverrideType.ILM_OVERRIDE,
            override_value=Decimal('1.5')
        )
        
        with patch.object(override_service, 'get_active_overrides') as mock_active:
            mock_active.return_value = [capital_override, ilm_override]
            
            original_results = {
                "bi": Decimal('1000000000'),
                "bic": Decimal('120000000'),
                "ilm": Decimal('1.2'),
                "orc": Decimal('144000000'),
                "rwa": Decimal('1800000000')
            }
            
            adjusted_results, applied_ids = await override_service.apply_overrides_to_calculation(
                "BANK_001", date.today(), original_results
            )
            
            # Check capital adjustment was applied
            assert adjusted_results["orc"] == Decimal('150000000')
            # Check ILM override was applied and ORC recalculated
            assert adjusted_results["ilm"] == Decimal('1.5')
            assert len(applied_ids) == 2
    
    @pytest.mark.asyncio
    async def test_expire_overrides(self, override_service):
        """Test expiring overrides"""
        expired_override = SupervisorOverride(
            id="OVR_001",
            status=OverrideStatus.APPLIED,
            effective_to=date.today() - timedelta(days=1)
        )
        
        override_service.db.query.return_value.filter.return_value.all.return_value = [expired_override]
        
        with patch.object(override_service, '_create_audit_log') as mock_audit:
            expired_ids = await override_service.expire_overrides()
            
            assert len(expired_ids) == 1
            assert expired_ids[0] == "OVR_001"
            assert expired_override.status == OverrideStatus.EXPIRED
            override_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_override_validation(self, override_service, sample_override_create):
        """Test override validation logic"""
        validation_result = await override_service._validate_override(sample_override_create)
        
        assert validation_result.is_valid is True
        assert len(validation_result.validation_errors) == 0
    
    @pytest.mark.asyncio
    async def test_override_validation_errors(self, override_service):
        """Test override validation with errors"""
        invalid_override = SupervisorOverrideCreate(
            id="OVR_001",
            override_type=OverrideType.CAPITAL_ADJUSTMENT,
            entity_id="BANK_001",
            override_value=Decimal('-100000000'),  # Invalid: negative value
            override_reason=OverrideReason.CONSERVATIVE_ADJUSTMENT,
            detailed_justification="Test",
            proposed_by="test_user",
            effective_from=date.today()
        )
        
        validation_result = await override_service._validate_override(invalid_override)
        
        assert validation_result.is_valid is False
        assert "Override value must be positive" in validation_result.validation_errors
    
    @pytest.mark.asyncio
    async def test_disclosure_requirements_setting(self, override_service):
        """Test automatic disclosure requirements setting"""
        override = SupervisorOverride(
            override_type=OverrideType.ILM_OVERRIDE,
            percentage_adjustment=Decimal('15')  # >10%, should require disclosure
        )
        
        await override_service._set_disclosure_requirements(override)
        
        assert override.requires_disclosure is True
        assert override.rbi_notification_required is True
    
    def test_is_override_effective(self, override_service):
        """Test override effectiveness checking"""
        override = SupervisorOverride(
            effective_from=date.today() - timedelta(days=10),
            effective_to=date.today() + timedelta(days=10)
        )
        
        # Test effective date
        is_effective = override_service._is_override_effective(override, date.today())
        assert is_effective is True
        
        # Test before effective date
        is_effective = override_service._is_override_effective(
            override, date.today() - timedelta(days=20)
        )
        assert is_effective is False
        
        # Test after expiry date
        is_effective = override_service._is_override_effective(
            override, date.today() + timedelta(days=20)
        )
        assert is_effective is False


class TestOverrideAPI:
    """Test override API endpoints"""
    
    def test_create_override_success(self, client):
        """Test successful override creation"""
        override_data = {
            "id": "OVR_TEST_001",
            "override_type": "capital_adjustment",
            "entity_id": "BANK_001",
            "original_value": "100000000",
            "override_value": "120000000",
            "percentage_adjustment": "20",
            "override_reason": "conservative_adjustment",
            "detailed_justification": "Conservative adjustment due to market volatility",
            "proposed_by": "risk_manager_1",
            "effective_from": date.today().isoformat(),
            "business_context": "Market stress conditions"
        }
        
        with patch('orm_calculator.services.override_service.get_override_service') as mock_service:
            mock_override_service = AsyncMock()
            mock_override = SupervisorOverride(**override_data)
            mock_override_service.create_override.return_value = mock_override
            mock_service.return_value = mock_override_service
            
            response = client.post(
                "/api/v1/overrides/",
                json=override_data,
                headers={"X-API-Key": "dev-api-key-12345"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "OVR_TEST_001"
        assert data["override_type"] == "capital_adjustment"
    
    def test_approve_override_success(self, client):
        """Test successful override approval"""
        approval_data = {
            "approved_by": "model_risk_manager_1",
            "approval_reference": "APP_2025_001",
            "approval_comments": "Approved based on risk assessment"
        }
        
        with patch('orm_calculator.services.override_service.get_override_service') as mock_service:
            mock_override_service = AsyncMock()
            mock_override = SupervisorOverride(
                id="OVR_001",
                status=OverrideStatus.APPROVED,
                approved_by="model_risk_manager_1"
            )
            mock_override_service.approve_override.return_value = mock_override
            mock_service.return_value = mock_override_service
            
            response = client.put(
                "/api/v1/overrides/OVR_001/approve",
                json=approval_data,
                headers={"X-API-Key": "dev-api-key-12345"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["approved_by"] == "model_risk_manager_1"
    
    def test_get_override_not_found(self, client):
        """Test getting non-existent override"""
        with patch('orm_calculator.database.connection.get_db_session') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_get_db.return_value = mock_db
            
            response = client.get(
                "/api/v1/overrides/NONEXISTENT",
                headers={"X-API-Key": "dev-api-key-12345"}
            )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "OVERRIDE_NOT_FOUND"
    
    def test_get_override_types(self, client):
        """Test getting available override types"""
        response = client.get(
            "/api/v1/overrides/reference/override-types",
            headers={"X-API-Key": "dev-api-key-12345"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "override_types" in data
        assert len(data["override_types"]) > 0
        
        # Check that capital_adjustment is in the list
        types = [t["value"] for t in data["override_types"]]
        assert "capital_adjustment" in types
    
    def test_get_override_reasons(self, client):
        """Test getting available override reasons"""
        response = client.get(
            "/api/v1/overrides/reference/override-reasons",
            headers={"X-API-Key": "dev-api-key-12345"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "override_reasons" in data
        assert len(data["override_reasons"]) > 0
        
        # Check that conservative_adjustment is in the list
        reasons = [r["value"] for r in data["override_reasons"]]
        assert "conservative_adjustment" in reasons


class TestOverrideCalculationIntegration:
    """Test override integration with calculation engine"""
    
    @pytest.mark.asyncio
    async def test_capital_adjustment_override(self, override_service):
        """Test capital adjustment override application"""
        original_calculation = {
            "orc": Decimal('100000000'),
            "rwa": Decimal('1250000000')
        }
        
        capital_override = SupervisorOverride(
            id="OVR_001",
            override_type=OverrideType.CAPITAL_ADJUSTMENT,
            override_value=Decimal('120000000')
        )
        
        with patch.object(override_service, 'get_active_overrides') as mock_active:
            mock_active.return_value = [capital_override]
            
            adjusted_results, applied_ids = await override_service.apply_overrides_to_calculation(
                "BANK_001", date.today(), original_calculation
            )
            
            assert adjusted_results["orc"] == Decimal('120000000')
            assert "OVR_001" in applied_ids
    
    @pytest.mark.asyncio
    async def test_ilm_override_with_recalculation(self, override_service):
        """Test ILM override with ORC recalculation"""
        original_calculation = {
            "bic": Decimal('100000000'),
            "ilm": Decimal('1.2'),
            "orc": Decimal('120000000')
        }
        
        ilm_override = SupervisorOverride(
            id="OVR_002",
            override_type=OverrideType.ILM_OVERRIDE,
            override_value=Decimal('1.5')
        )
        
        with patch.object(override_service, 'get_active_overrides') as mock_active:
            mock_active.return_value = [ilm_override]
            
            adjusted_results, applied_ids = await override_service.apply_overrides_to_calculation(
                "BANK_001", date.today(), original_calculation
            )
            
            assert adjusted_results["ilm"] == Decimal('1.5')
            assert adjusted_results["orc"] == Decimal('150000000')  # 100M * 1.5
            assert "OVR_002" in applied_ids


if __name__ == "__main__":
    pytest.main([__file__])