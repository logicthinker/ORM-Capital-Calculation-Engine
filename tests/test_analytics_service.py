"""
Tests for Analytics Service

Tests stress testing, sensitivity analysis, back-testing, and scenario analysis
functionality for risk management and model validation.
"""

import pytest
import asyncio
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.orm_calculator.services.analytics_service import (
    AnalyticsService, StressScenario, SensitivityParameter,
    ShockType, AnalysisType
)
from src.orm_calculator.models.pydantic_models import (
    CalculationResult, ModelNameEnum
)


@pytest.fixture
def mock_calculation_service():
    """Mock calculation service"""
    service = AsyncMock()
    
    # Mock base case result
    base_result = CalculationResult(
        run_id="test_run_001",
        entity_id="BANK001",
        calculation_date=date(2024, 6, 30),
        model_name=ModelNameEnum.SMA,
        operational_risk_capital=Decimal('144000000'),
        risk_weighted_assets=Decimal('1800000000'),
        bucket="Bucket 2",
        ilm_gated=False,
        supervisor_override=False,
        created_at=datetime.utcnow()
    )
    
    # Mock stressed result
    stressed_result = CalculationResult(
        run_id="test_run_002",
        entity_id="BANK001",
        calculation_date=date(2024, 6, 30),
        model_name=ModelNameEnum.SMA,
        operational_risk_capital=Decimal('187200000'),  # 30% increase
        risk_weighted_assets=Decimal('2340000000'),
        bucket="Bucket 2",
        ilm_gated=False,
        supervisor_override=False,
        created_at=datetime.utcnow()
    )
    
    service.execute_calculation.side_effect = [base_result, stressed_result]
    return service


@pytest.fixture
def analytics_service(mock_calculation_service):
    """Analytics service with mocked dependencies"""
    service = AnalyticsService()
    service.calculation_service = mock_calculation_service
    return service


class TestAnalyticsService:
    """Test analytics service functionality"""
    
    @pytest.mark.asyncio
    async def test_run_stress_test_single_scenario(self, analytics_service):
        """Test running stress test with single scenario"""
        
        # Create stress scenario
        scenario = StressScenario(
            name="moderate_loss_increase",
            description="30% increase in operational losses",
            shocks=[{"type": "loss_increase", "value": 30}],
            severity="moderate"
        )
        
        # Run stress test
        result = await analytics_service.run_stress_test(
            entity_id="BANK001",
            calculation_date=date(2024, 6, 30),
            scenarios=[scenario],
            model_name=ModelNameEnum.SMA
        )
        
        # Verify result
        assert result.analysis_type == AnalysisType.STRESS_TEST
        assert result.entity_id == "BANK001"
        assert len(result.scenarios) == 1
        assert result.scenarios[0]["scenario_name"] == "moderate_loss_increase"
        assert result.scenarios[0]["status"] == "completed"
        assert "impact" in result.scenarios[0]
        assert result.summary_statistics["successful_scenarios"] == 1
        assert result.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_run_stress_test_multiple_scenarios(self, analytics_service):
        """Test running stress test with multiple scenarios"""
        
        scenarios = [
            StressScenario(
                name="mild_stress",
                description="15% loss increase",
                shocks=[{"type": "loss_increase", "value": 15}],
                severity="mild"
            ),
            StressScenario(
                name="severe_stress",
                description="50% loss increase",
                shocks=[{"type": "loss_increase", "value": 50}],
                severity="severe"
            )
        ]
        
        # Mock multiple calculation results
        analytics_service.calculation_service.execute_calculation.side_effect = [
            # Base case
            CalculationResult(
                run_id="base",
                entity_id="BANK001",
                calculation_date=date(2024, 6, 30),
                model_name=ModelNameEnum.SMA,
                operational_risk_capital=Decimal('144000000'),
                risk_weighted_assets=Decimal('1800000000'),
                bucket="Bucket 2",
                ilm_gated=False,
                supervisor_override=False,
                created_at=datetime.utcnow()
            ),
            # Mild stress result
            CalculationResult(
                run_id="mild",
                entity_id="BANK001",
                calculation_date=date(2024, 6, 30),
                model_name=ModelNameEnum.SMA,
                operational_risk_capital=Decimal('165600000'),  # 15% increase
                risk_weighted_assets=Decimal('2070000000'),
                bucket="Bucket 2",
                ilm_gated=False,
                supervisor_override=False,
                created_at=datetime.utcnow()
            ),
            # Severe stress result
            CalculationResult(
                run_id="severe",
                entity_id="BANK001",
                calculation_date=date(2024, 6, 30),
                model_name=ModelNameEnum.SMA,
                operational_risk_capital=Decimal('216000000'),  # 50% increase
                risk_weighted_assets=Decimal('2700000000'),
                bucket="Bucket 2",
                ilm_gated=False,
                supervisor_override=False,
                created_at=datetime.utcnow()
            )
        ]
        
        # Run stress test
        result = await analytics_service.run_stress_test(
            entity_id="BANK001",
            calculation_date=date(2024, 6, 30),
            scenarios=scenarios,
            model_name=ModelNameEnum.SMA
        )
        
        # Verify result
        assert len(result.scenarios) == 2
        assert result.summary_statistics["successful_scenarios"] == 2
        assert "orc_impact_stats" in result.summary_statistics
        assert "var_95_pct" in result.risk_metrics
    
    @pytest.mark.asyncio
    async def test_run_sensitivity_analysis(self, analytics_service):
        """Test running sensitivity analysis"""
        
        # Create sensitivity parameter
        parameter = SensitivityParameter(
            parameter_name="loss_multiplier",
            base_value=1.0,
            min_value=0.8,
            max_value=1.2,
            step_size=0.1,
            parameter_type="multiplier"
        )
        
        # Mock multiple calculation results for sensitivity
        base_orc = Decimal('144000000')
        results = [
            # Base case
            CalculationResult(
                run_id="base",
                entity_id="BANK001",
                calculation_date=date(2024, 6, 30),
                model_name=ModelNameEnum.SMA,
                operational_risk_capital=base_orc,
                risk_weighted_assets=Decimal('1800000000'),
                bucket="Bucket 2",
                ilm_gated=False,
                supervisor_override=False,
                created_at=datetime.utcnow()
            )
        ]
        
        # Add sensitivity results
        for i, multiplier in enumerate([0.8, 0.9, 1.0, 1.1, 1.2]):
            results.append(
                CalculationResult(
                    run_id=f"sens_{i}",
                    entity_id="BANK001",
                    calculation_date=date(2024, 6, 30),
                    model_name=ModelNameEnum.SMA,
                    operational_risk_capital=base_orc * Decimal(str(multiplier)),
                    risk_weighted_assets=Decimal('1800000000') * Decimal(str(multiplier)),
                    bucket="Bucket 2",
                    ilm_gated=False,
                    supervisor_override=False,
                    created_at=datetime.utcnow()
                )
            )
        
        analytics_service.calculation_service.execute_calculation.side_effect = results
        
        # Run sensitivity analysis
        result = await analytics_service.run_sensitivity_analysis(
            entity_id="BANK001",
            calculation_date=date(2024, 6, 30),
            parameters=[parameter],
            model_name=ModelNameEnum.SMA
        )
        
        # Verify result
        assert result.analysis_type == AnalysisType.SENSITIVITY_ANALYSIS
        assert len(result.scenarios) == 5  # 5 parameter values
        assert "parameter_statistics" in result.summary_statistics
        assert "loss_multiplier" in result.summary_statistics["parameter_statistics"]
        assert "orc_volatility" in result.risk_metrics
    
    @pytest.mark.asyncio
    async def test_run_back_testing(self, analytics_service):
        """Test running back-testing analysis"""
        
        # Mock calculation result
        calc_result = CalculationResult(
            run_id="backtest",
            entity_id="BANK001",
            calculation_date=date(2024, 3, 31),
            model_name=ModelNameEnum.SMA,
            operational_risk_capital=Decimal('144000000'),
            risk_weighted_assets=Decimal('1800000000'),
            bucket="Bucket 2",
            ilm_gated=False,
            supervisor_override=False,
            created_at=datetime.utcnow()
        )
        
        analytics_service.calculation_service.execute_calculation.return_value = calc_result
        
        # Run back-testing
        results = await analytics_service.run_back_testing(
            entity_id="BANK001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            model_name=ModelNameEnum.SMA
        )
        
        # Verify results
        assert len(results) == 1  # One quarter
        assert results[0].period_start == date(2024, 1, 1)
        assert results[0].period_end == date(2024, 3, 31)
        assert results[0].predicted_capital == Decimal('144000000')
        assert results[0].actual_losses == Decimal('50000000')  # Mock value
        assert results[0].coverage_ratio > 0
        assert "coverage_ratio" in results[0].validation_metrics
    
    @pytest.mark.asyncio
    async def test_run_what_if_analysis(self, analytics_service):
        """Test running what-if analysis"""
        
        # Mock base and what-if results
        base_result = CalculationResult(
            run_id="base",
            entity_id="BANK001",
            calculation_date=date(2024, 6, 30),
            model_name=ModelNameEnum.SMA,
            operational_risk_capital=Decimal('144000000'),
            risk_weighted_assets=Decimal('1800000000'),
            bucket="Bucket 2",
            ilm_gated=False,
            supervisor_override=False,
            created_at=datetime.utcnow()
        )
        
        what_if_result = CalculationResult(
            run_id="whatif",
            entity_id="BANK001",
            calculation_date=date(2024, 6, 30),
            model_name=ModelNameEnum.WHAT_IF,
            operational_risk_capital=Decimal('180000000'),  # 25% increase
            risk_weighted_assets=Decimal('2250000000'),
            bucket="Bucket 2",
            ilm_gated=False,
            supervisor_override=False,
            created_at=datetime.utcnow()
        )
        
        analytics_service.calculation_service.execute_calculation.side_effect = [base_result, what_if_result]
        
        # Run what-if analysis
        result = await analytics_service.run_what_if_analysis(
            entity_id="BANK001",
            calculation_date=date(2024, 6, 30),
            what_if_parameters={"loss_multiplier": 1.25},
            model_name=ModelNameEnum.SMA
        )
        
        # Verify result
        assert result.analysis_type == AnalysisType.WHAT_IF_ANALYSIS
        assert len(result.scenarios) == 1
        assert result.scenarios[0]["scenario_name"] == "what_if"
        assert result.scenarios[0]["impact"]["orc_change"] == 36000000.0  # 180M - 144M
        assert result.scenarios[0]["impact"]["orc_change_pct"] == 25.0
    
    def test_get_predefined_scenarios(self, analytics_service):
        """Test getting predefined scenarios"""
        
        scenarios = analytics_service.get_predefined_scenarios()
        
        # Verify scenarios
        assert len(scenarios) > 0
        assert any(s.name == "mild_loss_increase" for s in scenarios)
        assert any(s.name == "severe_loss_increase" for s in scenarios)
        assert any(s.name == "combined_stress_scenario" for s in scenarios)
        
        # Verify scenario structure
        for scenario in scenarios:
            assert hasattr(scenario, 'name')
            assert hasattr(scenario, 'description')
            assert hasattr(scenario, 'shocks')
            assert hasattr(scenario, 'severity')
            assert len(scenario.shocks) > 0
    
    @pytest.mark.asyncio
    async def test_apply_stress_shocks(self, analytics_service):
        """Test applying stress shocks to parameters"""
        
        shocks = [
            {"type": "loss_increase", "value": 30},
            {"type": "bi_decrease", "value": 15},
            {"type": "recovery_haircut", "value": 50}
        ]
        
        modified_params = await analytics_service._apply_stress_shocks(
            shocks, "BANK001", date(2024, 6, 30)
        )
        
        # Verify shock application
        assert "loss_multiplier" in modified_params
        assert modified_params["loss_multiplier"] == 1.3  # 1 + 30%
        assert "bi_multiplier" in modified_params
        assert modified_params["bi_multiplier"] == 0.85  # 1 - 15%
        assert "recovery_haircut" in modified_params
        assert modified_params["recovery_haircut"] == 0.5  # 50%
    
    def test_calculate_stress_summary_statistics(self, analytics_service):
        """Test calculation of stress test summary statistics"""
        
        # Mock base case
        base_case = CalculationResult(
            run_id="base",
            entity_id="BANK001",
            calculation_date=date(2024, 6, 30),
            model_name=ModelNameEnum.SMA,
            operational_risk_capital=Decimal('144000000'),
            risk_weighted_assets=Decimal('1800000000'),
            bucket="Bucket 2",
            ilm_gated=False,
            supervisor_override=False,
            created_at=datetime.utcnow()
        )
        
        # Mock scenario results
        scenario_results = [
            {
                "status": "completed",
                "result": CalculationResult(
                    run_id="s1",
                    entity_id="BANK001",
                    calculation_date=date(2024, 6, 30),
                    model_name=ModelNameEnum.SMA,
                    operational_risk_capital=Decimal('165600000'),
                    risk_weighted_assets=Decimal('2070000000'),
                    bucket="Bucket 2",
                    ilm_gated=False,
                    supervisor_override=False,
                    created_at=datetime.utcnow()
                ),
                "impact": {"orc_change_pct": 15.0}
            },
            {
                "status": "completed",
                "result": CalculationResult(
                    run_id="s2",
                    entity_id="BANK001",
                    calculation_date=date(2024, 6, 30),
                    model_name=ModelNameEnum.SMA,
                    operational_risk_capital=Decimal('187200000'),
                    risk_weighted_assets=Decimal('2340000000'),
                    bucket="Bucket 2",
                    ilm_gated=False,
                    supervisor_override=False,
                    created_at=datetime.utcnow()
                ),
                "impact": {"orc_change_pct": 30.0}
            }
        ]
        
        # Calculate statistics
        stats = analytics_service._calculate_stress_summary_statistics(base_case, scenario_results)
        
        # Verify statistics
        assert stats["base_orc"] == 144000000.0
        assert stats["successful_scenarios"] == 2
        assert stats["orc_impact_stats"]["min_change_pct"] == 15.0
        assert stats["orc_impact_stats"]["max_change_pct"] == 30.0
        assert stats["orc_impact_stats"]["avg_change_pct"] == 22.5
    
    def test_calculate_stress_risk_metrics(self, analytics_service):
        """Test calculation of stress test risk metrics"""
        
        # Mock base case
        base_case = CalculationResult(
            run_id="base",
            entity_id="BANK001",
            calculation_date=date(2024, 6, 30),
            model_name=ModelNameEnum.SMA,
            operational_risk_capital=Decimal('144000000'),
            risk_weighted_assets=Decimal('1800000000'),
            bucket="Bucket 2",
            ilm_gated=False,
            supervisor_override=False,
            created_at=datetime.utcnow()
        )
        
        # Mock scenario results with various impacts
        scenario_results = []
        impact_values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]  # 10 scenarios
        
        for i, impact in enumerate(impact_values):
            scenario_results.append({
                "status": "completed",
                "result": CalculationResult(
                    run_id=f"s{i}",
                    entity_id="BANK001",
                    calculation_date=date(2024, 6, 30),
                    model_name=ModelNameEnum.SMA,
                    operational_risk_capital=Decimal('144000000') * (1 + impact/100),
                    risk_weighted_assets=Decimal('1800000000'),
                    bucket="Bucket 2",
                    ilm_gated=False,
                    supervisor_override=False,
                    created_at=datetime.utcnow()
                ),
                "impact": {"orc_change_pct": float(impact)}
            })
        
        # Calculate risk metrics
        metrics = analytics_service._calculate_stress_risk_metrics(base_case, scenario_results)
        
        # Verify metrics
        assert "var_95_pct" in metrics
        assert "var_99_pct" in metrics
        assert "expected_shortfall_95" in metrics
        assert metrics["worst_case_impact"] == 100.0
        assert metrics["best_case_impact"] == 10.0
        assert metrics["scenarios_with_increase"] == 10
        assert metrics["extreme_scenarios"] >= 5  # Scenarios with >50% impact


@pytest.mark.asyncio
async def test_analytics_service_integration():
    """Integration test for analytics service"""
    
    # This test would require actual database and calculation service
    # For now, we'll test the service initialization
    service = AnalyticsService()
    
    assert service is not None
    assert hasattr(service, 'calculation_service')
    assert hasattr(service, 'predefined_scenarios')
    assert len(service.predefined_scenarios) > 0
    
    # Test predefined scenarios
    scenarios = service.get_predefined_scenarios()
    assert len(scenarios) > 0
    
    # Verify scenario types
    scenario_names = [s.name for s in scenarios]
    assert "mild_loss_increase" in scenario_names
    assert "moderate_loss_increase" in scenario_names
    assert "severe_loss_increase" in scenario_names
    assert "combined_stress_scenario" in scenario_names