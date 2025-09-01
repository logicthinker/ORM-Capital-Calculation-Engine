"""
Tests for consolidation and corporate actions functionality
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock

from orm_calculator.models.entity_models import (
    Entity, CorporateAction, ConsolidationMapping,
    ConsolidationLevel, CorporateActionType, CorporateActionStatus,
    EntityCreate, CorporateActionCreate, ConsolidationRequest
)
from orm_calculator.services.consolidation_service import ConsolidationService
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
def consolidation_service(mock_db):
    """Create consolidation service with mock database"""
    return ConsolidationService(mock_db)


@pytest.fixture
def sample_entities():
    """Sample entities for testing"""
    return [
        Entity(
            id="BANK_001",
            name="Main Bank",
            entity_type="bank",
            consolidation_level=ConsolidationLevel.CONSOLIDATED,
            is_active=True
        ),
        Entity(
            id="SUB_001",
            name="Subsidiary 1",
            entity_type="subsidiary",
            parent_entity_id="BANK_001",
            consolidation_level=ConsolidationLevel.SUB_CONSOLIDATED,
            is_active=True
        ),
        Entity(
            id="SUB_002",
            name="Subsidiary 2",
            entity_type="subsidiary",
            parent_entity_id="BANK_001",
            consolidation_level=ConsolidationLevel.SUBSIDIARY,
            is_active=True
        )
    ]


@pytest.fixture
def sample_corporate_action():
    """Sample corporate action for testing"""
    return CorporateAction(
        id="CA_001",
        action_type=CorporateActionType.ACQUISITION,
        status=CorporateActionStatus.PROPOSED,
        target_entity_id="SUB_003",
        acquirer_entity_id="BANK_001",
        transaction_value=Decimal('1000000000'),
        ownership_percentage=Decimal('100'),
        announcement_date=date.today() - timedelta(days=30),
        effective_date=date.today(),
        requires_pillar3_disclosure=True,
        prior_bi_inclusion_required=True
    )


class TestEntityManagement:
    """Test entity management functionality"""
    
    def test_create_entity_success(self, client):
        """Test successful entity creation"""
        entity_data = {
            "id": "TEST_001",
            "name": "Test Entity",
            "entity_type": "subsidiary",
            "consolidation_level": "subsidiary",
            "rbi_entity_code": "RBI001"
        }
        
        with patch('orm_calculator.database.connection.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_get_db.return_value = mock_db
            
            response = client.post(
                "/api/v1/consolidation/entities",
                json=entity_data,
                headers={"X-API-Key": "dev-api-key-12345"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "TEST_001"
        assert data["name"] == "Test Entity"
        assert data["entity_type"] == "subsidiary"
    
    def test_create_entity_duplicate_id(self, client):
        """Test entity creation with duplicate ID"""
        entity_data = {
            "id": "EXISTING_001",
            "name": "Test Entity",
            "entity_type": "subsidiary",
            "consolidation_level": "subsidiary"
        }
        
        with patch('orm_calculator.database.connection.get_database') as mock_get_db:
            mock_db = AsyncMock()
            # Mock existing entity
            existing_entity = Entity(id="EXISTING_001", name="Existing")
            mock_db.query.return_value.filter.return_value.first.return_value = existing_entity
            mock_get_db.return_value = mock_db
            
            response = client.post(
                "/api/v1/consolidation/entities",
                json=entity_data,
                headers={"X-API-Key": "dev-api-key-12345"}
            )
        
        assert response.status_code == 409
        data = response.json()
        assert data["error_code"] == "ENTITY_EXISTS"
    
    def test_get_entity_hierarchy(self, client):
        """Test getting entity hierarchy"""
        with patch('orm_calculator.services.consolidation_service.get_consolidation_service') as mock_service:
            mock_consolidation_service = AsyncMock()
            mock_hierarchy = {
                "entity": {
                    "id": "BANK_001",
                    "name": "Main Bank",
                    "entity_type": "bank",
                    "consolidation_level": "consolidated",
                    "is_active": True
                },
                "children": [],
                "consolidation_mappings": []
            }
            mock_consolidation_service.get_entity_hierarchy.return_value = mock_hierarchy
            mock_service.return_value = mock_consolidation_service
            
            response = client.get(
                "/api/v1/consolidation/entities/BANK_001/hierarchy",
                headers={"X-API-Key": "dev-api-key-12345"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["entity"]["id"] == "BANK_001"


class TestCorporateActions:
    """Test corporate actions functionality"""
    
    def test_create_corporate_action(self, client):
        """Test creating corporate action"""
        action_data = {
            "id": "CA_TEST_001",
            "action_type": "acquisition",
            "target_entity_id": "SUB_001",
            "acquirer_entity_id": "BANK_001",
            "transaction_value": "1000000000",
            "ownership_percentage": "100",
            "announcement_date": "2025-08-01",
            "effective_date": "2025-08-29",
            "description": "Test acquisition"
        }
        
        with patch('orm_calculator.services.consolidation_service.get_consolidation_service') as mock_service:
            mock_consolidation_service = AsyncMock()
            mock_action = CorporateAction(**action_data)
            mock_consolidation_service.register_corporate_action.return_value = mock_action
            mock_service.return_value = mock_consolidation_service
            
            response = client.post(
                "/api/v1/consolidation/corporate-actions",
                json=action_data,
                headers={"X-API-Key": "dev-api-key-12345"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "CA_TEST_001"
        assert data["action_type"] == "acquisition"
    
    def test_approve_corporate_action(self, client):
        """Test approving corporate action"""
        with patch('orm_calculator.services.consolidation_service.get_consolidation_service') as mock_service:
            mock_consolidation_service = AsyncMock()
            mock_action = CorporateAction(
                id="CA_001",
                action_type=CorporateActionType.ACQUISITION,
                status=CorporateActionStatus.RBI_APPROVED,
                rbi_approval_reference="RBI/2025/001"
            )
            mock_consolidation_service.approve_corporate_action.return_value = mock_action
            mock_service.return_value = mock_consolidation_service
            
            response = client.put(
                "/api/v1/consolidation/corporate-actions/CA_001/approve"
                "?rbi_approval_reference=RBI/2025/001"
                "&approval_date=2025-08-29",
                headers={"X-API-Key": "dev-api-key-12345"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rbi_approved"
        assert data["rbi_approval_reference"] == "RBI/2025/001"


class TestConsolidationService:
    """Test consolidation service business logic"""
    
    @pytest.mark.asyncio
    async def test_calculate_consolidated_capital(self, consolidation_service, sample_entities):
        """Test consolidated capital calculation"""
        # Mock database queries
        consolidation_service.db.query.return_value.filter.return_value.first.return_value = sample_entities[0]
        
        request = ConsolidationRequest(
            parent_entity_id="BANK_001",
            consolidation_level=ConsolidationLevel.CONSOLIDATED,
            calculation_date=date.today(),
            include_subsidiaries=True,
            include_corporate_actions=True
        )
        
        # Mock the hierarchy building
        with patch.object(consolidation_service, 'get_entity_hierarchy') as mock_hierarchy:
            mock_hierarchy.return_value = {
                "entity": sample_entities[0],
                "children": sample_entities[1:],
                "consolidation_mappings": []
            }
            
            with patch.object(consolidation_service, '_determine_consolidation_scope') as mock_scope:
                mock_scope.return_value = (sample_entities, [])
                
                with patch.object(consolidation_service, '_apply_corporate_actions') as mock_actions:
                    mock_actions.return_value = []
                    
                    with patch.object(consolidation_service, '_calculate_consolidated_bi') as mock_bi:
                        mock_bi.return_value = Decimal('1000000000')
                        
                        with patch.object(consolidation_service, '_calculate_consolidated_losses') as mock_losses:
                            mock_losses.return_value = Decimal('50000000')
                            
                            with patch.object(consolidation_service, '_get_entity_contributions') as mock_contrib:
                                mock_contrib.return_value = {}
                                
                                with patch.object(consolidation_service, '_identify_disclosure_items') as mock_disclosure:
                                    mock_disclosure.return_value = []
                                    
                                    result = await consolidation_service.calculate_consolidated_capital(request)
        
        assert result.parent_entity_id == "BANK_001"
        assert result.consolidation_level == ConsolidationLevel.CONSOLIDATED
        assert result.consolidated_bi == Decimal('1000000000')
        assert result.consolidated_losses == Decimal('50000000')
    
    @pytest.mark.asyncio
    async def test_register_corporate_action_acquisition(self, consolidation_service, sample_corporate_action):
        """Test registering acquisition corporate action"""
        result = await consolidation_service.register_corporate_action(sample_corporate_action)
        
        assert result.prior_bi_inclusion_required is True
        assert result.bi_exclusion_required is False
        consolidation_service.db.add.assert_called_once()
        consolidation_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_corporate_action_divestiture(self, consolidation_service):
        """Test registering divestiture corporate action"""
        divestiture_action = CorporateAction(
            id="CA_002",
            action_type=CorporateActionType.DIVESTITURE,
            status=CorporateActionStatus.PROPOSED,
            target_entity_id="SUB_001",
            ownership_percentage=Decimal('50'),
            announcement_date=date.today(),
            effective_date=date.today()
        )
        
        result = await consolidation_service.register_corporate_action(divestiture_action)
        
        assert result.prior_bi_inclusion_required is False
        assert result.bi_exclusion_required is True
    
    @pytest.mark.asyncio
    async def test_approve_corporate_action(self, consolidation_service, sample_corporate_action):
        """Test approving corporate action"""
        consolidation_service.db.query.return_value.filter.return_value.first.return_value = sample_corporate_action
        
        result = await consolidation_service.approve_corporate_action(
            "CA_001", "RBI/2025/001", date.today()
        )
        
        assert result.status == CorporateActionStatus.RBI_APPROVED
        assert result.rbi_approval_reference == "RBI/2025/001"
        consolidation_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_corporate_action(self, consolidation_service, sample_corporate_action):
        """Test completing corporate action"""
        # Set action as approved first
        sample_corporate_action.status = CorporateActionStatus.RBI_APPROVED
        consolidation_service.db.query.return_value.filter.return_value.first.return_value = sample_corporate_action
        
        result = await consolidation_service.complete_corporate_action("CA_001", date.today())
        
        assert result.status == CorporateActionStatus.COMPLETED
        assert result.completion_date == date.today()
        consolidation_service.db.commit.assert_called_once()
    
    def test_should_include_entity_consolidated(self, consolidation_service, sample_entities):
        """Test entity inclusion logic for consolidated level"""
        entity = sample_entities[0]  # Main bank
        
        should_include = consolidation_service._should_include_entity(
            entity, ConsolidationLevel.CONSOLIDATED, date.today(), 0
        )
        
        assert should_include is True
    
    def test_should_include_entity_subsidiary_only(self, consolidation_service, sample_entities):
        """Test entity inclusion logic for subsidiary level"""
        entity = sample_entities[1]  # Subsidiary
        
        # Should include only at hierarchy level 0 (root)
        should_include_root = consolidation_service._should_include_entity(
            entity, ConsolidationLevel.SUBSIDIARY, date.today(), 0
        )
        should_include_child = consolidation_service._should_include_entity(
            entity, ConsolidationLevel.SUBSIDIARY, date.today(), 1
        )
        
        assert should_include_root is True
        assert should_include_child is False
    
    def test_should_exclude_inactive_entity(self, consolidation_service, sample_entities):
        """Test that inactive entities are excluded"""
        entity = sample_entities[0]
        entity.is_active = False
        
        should_include = consolidation_service._should_include_entity(
            entity, ConsolidationLevel.CONSOLIDATED, date.today(), 0
        )
        
        assert should_include is False


class TestConsolidationCalculations:
    """Test consolidation calculation logic"""
    
    @pytest.mark.asyncio
    async def test_bi_calculation_with_corporate_actions(self, consolidation_service):
        """Test BI calculation with corporate action adjustments"""
        base_bi = Decimal('500000000')
        entity_id = "SUB_001"
        
        # Mock acquisition action
        acquisition_action = CorporateAction(
            id="CA_001",
            action_type=CorporateActionType.ACQUISITION,
            target_entity_id=entity_id,
            prior_bi_inclusion_required=True,
            effective_date=date.today() - timedelta(days=30)
        )
        
        with patch.object(consolidation_service, '_get_prior_bi_for_acquisition') as mock_prior_bi:
            mock_prior_bi.return_value = Decimal('100000000')
            
            adjusted_bi = await consolidation_service._apply_corporate_action_adjustments(
                base_bi, entity_id, [acquisition_action], date.today()
            )
        
        assert adjusted_bi == Decimal('600000000')  # 500M + 100M
    
    @pytest.mark.asyncio
    async def test_bi_calculation_with_divestiture(self, consolidation_service):
        """Test BI calculation with divestiture adjustment"""
        base_bi = Decimal('500000000')
        entity_id = "SUB_001"
        
        # Mock divestiture action
        divestiture_action = CorporateAction(
            id="CA_002",
            action_type=CorporateActionType.DIVESTITURE,
            target_entity_id=entity_id,
            bi_exclusion_required=True,
            effective_date=date.today() - timedelta(days=30),
            ownership_percentage=Decimal('20')  # 20% divestiture
        )
        
        with patch.object(consolidation_service, '_get_divested_bi') as mock_divested_bi:
            mock_divested_bi.return_value = Decimal('100000000')  # 20% of 500M
            
            adjusted_bi = await consolidation_service._apply_corporate_action_adjustments(
                base_bi, entity_id, [divestiture_action], date.today()
            )
        
        assert adjusted_bi == Decimal('400000000')  # 500M - 100M
    
    @pytest.mark.asyncio
    async def test_disclosure_items_identification(self, consolidation_service):
        """Test identification of disclosure items"""
        # Mock corporate action requiring disclosure
        action = CorporateAction(
            id="CA_001",
            action_type=CorporateActionType.ACQUISITION,
            target_entity_id="SUB_001",
            requires_pillar3_disclosure=True,
            disclosure_period_months=36,
            effective_date=date.today() - timedelta(days=365)  # 1 year ago
        )
        
        disclosure_items = await consolidation_service._identify_disclosure_items(
            [action], date.today()
        )
        
        assert len(disclosure_items) == 1
        assert "acquisition_CA_001_SUB_001" in disclosure_items[0]
    
    @pytest.mark.asyncio
    async def test_disclosure_items_expired(self, consolidation_service):
        """Test that expired disclosure items are not included"""
        # Mock corporate action with expired disclosure period
        action = CorporateAction(
            id="CA_001",
            action_type=CorporateActionType.ACQUISITION,
            target_entity_id="SUB_001",
            requires_pillar3_disclosure=True,
            disclosure_period_months=36,
            effective_date=date.today() - timedelta(days=365 * 4)  # 4 years ago
        )
        
        disclosure_items = await consolidation_service._identify_disclosure_items(
            [action], date.today()
        )
        
        assert len(disclosure_items) == 0


if __name__ == "__main__":
    pytest.main([__file__])