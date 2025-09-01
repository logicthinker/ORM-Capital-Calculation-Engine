"""
Unit tests for Unified Calculator

Tests the unified calculation interface supporting SMA, BIA, and TSA.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime

from src.orm_calculator.services.unified_calculator import (
    UnifiedCalculator,
    CalculationMethod,
    UnifiedCalculationResult
)


class TestUnifiedCalculator:
    """Test suite for Unified Calculator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.calculator = UnifiedCalculator()
        self.entity_id = "TEST_BANK_001"
        self.calculation_date = date(2024, 3, 31)
        self.run_id = "test_run_001"
    
    def test_unified_calculator_initialization(self):
        """Test unified calculator initialization"""
        assert self.calculator.model_version == "1.0.0"
        assert self.calculator.parameters_version == "1.0.0"
        assert hasattr(self.calculator, 'sma_calculator')
        assert hasattr(self.calculator, 'bia_calculator')
        assert hasattr(self.calculator, 'tsa_calculator')
    
    def test_unified_calculator_custom_parameters(self):
        """Test unified calculator with custom parameters"""
        custom_params = {
            "sma": {
                "marginal_coefficients": {
                    "bucket_1": Decimal('0.10')
                }
            },
            "bia": {
                "alpha_coefficient": Decimal('0.18')
            },
            "tsa": {
                "beta_factors": {
                    "retail_banking": Decimal('0.10')
                }
            }
        }
        
        calculator = UnifiedCalculator(parameters=custom_params)
        
        # Check that parameters were passed to individual calculators
        assert calculator.sma_calculator.MARGINAL_COEFFICIENTS['bucket_1'] == Decimal('0.10')
        assert calculator.bia_calculator.ALPHA_COEFFICIENT == Decimal('0.18')
        assert calculator.tsa_calculator.BETA_FACTORS['retail_banking'] == Decimal('0.10')
    
    def test_unified_calculator_sma_calculation(self):
        """Test SMA calculation through unified interface"""
        data = {
            "business_indicator_data": [
                {
                    "period": "2023-Q4",
                    "ildc": "1000000000",
                    "sc": "500000000",
                    "fc": "300000000"
                },
                {
                    "period": "2022-Q4",
                    "ildc": "950000000",
                    "sc": "480000000",
                    "fc": "290000000"
                }
            ],
            "loss_data": [
                {
                    "event_id": "LOSS_001",
                    "accounting_date": "2023-06-15",
                    "net_loss": "50000000",
                    "is_excluded": False
                }
            ]
        }
        
        result = self.calculator.calculate(
            method=CalculationMethod.SMA,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id,
            data=data
        )
        
        assert isinstance(result, UnifiedCalculationResult)
        assert result.method == CalculationMethod.SMA
        assert result.run_id == self.run_id
        assert result.entity_id == self.entity_id
        assert result.operational_risk_capital > 0
        assert result.risk_weighted_assets > 0
        
        # Check that we can get the SMA-specific result
        sma_result = result.get_method_specific_result()
        assert sma_result is not None
    
    def test_unified_calculator_bia_calculation(self):
        """Test BIA calculation through unified interface"""
        data = {
            "gross_income_data": [
                {
                    "period": "2023",
                    "gross_income": "2000000000",
                    "excluded_items": "50000000"
                },
                {
                    "period": "2022",
                    "gross_income": "1900000000",
                    "excluded_items": "45000000"
                },
                {
                    "period": "2021",
                    "gross_income": "1800000000",
                    "excluded_items": "40000000"
                }
            ]
        }
        
        result = self.calculator.calculate(
            method=CalculationMethod.BIA,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id,
            data=data
        )
        
        assert isinstance(result, UnifiedCalculationResult)
        assert result.method == CalculationMethod.BIA
        assert result.run_id == self.run_id
        assert result.entity_id == self.entity_id
        assert result.operational_risk_capital > 0
        assert result.risk_weighted_assets > 0
        
        # Check that we can get the BIA-specific result
        bia_result = result.get_method_specific_result()
        assert bia_result is not None
    
    def test_unified_calculator_tsa_calculation(self):
        """Test TSA calculation through unified interface"""
        data = {
            "business_line_data": [
                {
                    "period": "2023",
                    "business_line": "retail_banking",
                    "gross_income": "1000000000",
                    "excluded_items": "50000000"
                },
                {
                    "period": "2023",
                    "business_line": "commercial_banking",
                    "gross_income": "800000000",
                    "excluded_items": "40000000"
                },
                {
                    "period": "2022",
                    "business_line": "retail_banking",
                    "gross_income": "950000000",
                    "excluded_items": "45000000"
                }
            ]
        }
        
        result = self.calculator.calculate(
            method=CalculationMethod.TSA,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id,
            data=data
        )
        
        assert isinstance(result, UnifiedCalculationResult)
        assert result.method == CalculationMethod.TSA
        assert result.run_id == self.run_id
        assert result.entity_id == self.entity_id
        assert result.operational_risk_capital > 0
        assert result.risk_weighted_assets > 0
        
        # Check that we can get the TSA-specific result
        tsa_result = result.get_method_specific_result()
        assert tsa_result is not None
    
    def test_unified_calculator_unsupported_method(self):
        """Test unified calculator with unsupported method"""
        with pytest.raises(ValueError, match="Unsupported calculation method"):
            self.calculator.calculate(
                method="INVALID_METHOD",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                run_id=self.run_id,
                data={}
            )
    
    def test_unified_calculator_input_validation(self):
        """Test unified calculator input validation"""
        # Test SMA validation
        sma_errors = self.calculator.validate_inputs(CalculationMethod.SMA, {})
        assert "Business indicator data is required for SMA" in sma_errors
        assert "Loss data is required for SMA" in sma_errors
        
        # Test BIA validation
        bia_errors = self.calculator.validate_inputs(CalculationMethod.BIA, {})
        assert "Gross income data is required for BIA" in bia_errors
        
        # Test TSA validation
        tsa_errors = self.calculator.validate_inputs(CalculationMethod.TSA, {})
        assert "Business line data is required for TSA" in tsa_errors
        
        # Test valid data
        valid_sma_data = {
            "business_indicator_data": [],
            "loss_data": []
        }
        sma_errors = self.calculator.validate_inputs(CalculationMethod.SMA, valid_sma_data)
        assert len(sma_errors) == 0
    
    def test_unified_calculator_supported_methods(self):
        """Test getting supported calculation methods"""
        methods = self.calculator.get_supported_methods()
        
        assert "sma" in methods
        assert "bia" in methods
        assert "tsa" in methods
        assert len(methods) == 3
    
    def test_unified_calculator_method_metadata(self):
        """Test getting method-specific metadata"""
        # Test SMA metadata
        sma_metadata = self.calculator.get_method_metadata(CalculationMethod.SMA)
        assert "marginal_coefficients" in sma_metadata
        
        # Test BIA metadata
        bia_metadata = self.calculator.get_method_metadata(CalculationMethod.BIA)
        assert bia_metadata["method"] == "BIA"
        assert "alpha_coefficient" in bia_metadata
        
        # Test TSA metadata
        tsa_metadata = self.calculator.get_method_metadata(CalculationMethod.TSA)
        assert tsa_metadata["method"] == "TSA"
        assert "beta_factors" in tsa_metadata
    
    def test_unified_calculator_parameter_update(self):
        """Test parameter updates for all calculators"""
        new_params = {
            "sma": {
                "marginal_coefficients": {
                    "bucket_1": Decimal('0.13')
                }
            },
            "bia": {
                "alpha_coefficient": Decimal('0.20')
            },
            "tsa": {
                "beta_factors": {
                    "retail_banking": Decimal('0.14')
                }
            }
        }
        
        self.calculator.update_parameters(new_params)
        
        # Check that parameters were updated
        assert self.calculator.sma_calculator.MARGINAL_COEFFICIENTS['bucket_1'] == Decimal('0.13')
        assert self.calculator.bia_calculator.ALPHA_COEFFICIENT == Decimal('0.20')
        assert self.calculator.tsa_calculator.BETA_FACTORS['retail_banking'] == Decimal('0.14')
    
    def test_unified_calculator_multiple_methods(self):
        """Test calculating with multiple methods for comparison"""
        # Prepare data for all methods
        data = {
            "business_indicator_data": [
                {
                    "period": "2023-Q4",
                    "ildc": "1000000000",
                    "sc": "500000000",
                    "fc": "300000000"
                }
            ],
            "loss_data": [
                {
                    "event_id": "LOSS_001",
                    "accounting_date": "2023-06-15",
                    "net_loss": "50000000",
                    "is_excluded": False
                }
            ],
            "gross_income_data": [
                {
                    "period": "2023",
                    "gross_income": "2000000000",
                    "excluded_items": "50000000"
                }
            ],
            "business_line_data": [
                {
                    "period": "2023",
                    "business_line": "retail_banking",
                    "gross_income": "1000000000",
                    "excluded_items": "50000000"
                }
            ]
        }
        
        methods = [CalculationMethod.SMA, CalculationMethod.BIA, CalculationMethod.TSA]
        results = self.calculator.calculate_multiple_methods(
            methods=methods,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id,
            data=data
        )
        
        assert len(results) == 3
        assert "sma" in results
        assert "bia" in results
        assert "tsa" in results
        
        # Check that each result is valid
        for method_name, result in results.items():
            if isinstance(result, dict) and "error" in result:
                # Skip error results for this test
                continue
            assert isinstance(result, UnifiedCalculationResult)
            assert result.operational_risk_capital > 0


class TestUnifiedCalculationResult:
    """Test suite for Unified Calculation Result"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.entity_id = "TEST_BANK_001"
        self.calculation_date = date(2024, 3, 31)
        self.run_id = "test_run_001"
    
    def test_unified_result_to_dict_sma(self):
        """Test converting SMA result to dictionary"""
        # Create a mock SMA result
        from src.orm_calculator.services.sma_calculator import SMACalculationResult, RBIBucket
        
        sma_result = SMACalculationResult(
            run_id=self.run_id,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            bi_current=Decimal('1000000000'),
            bi_three_year_average=Decimal('950000000'),
            bic=Decimal('114000000'),
            bucket=RBIBucket.BUCKET_1,
            marginal_coefficients_applied={"bucket_1": Decimal('950000000')},
            lc=Decimal('750000000'),
            average_annual_losses=Decimal('50000000'),
            loss_data_years=3,
            ilm=Decimal('1.0'),
            ilm_gated=True,
            orc=Decimal('114000000'),
            rwa=Decimal('1425000000'),
            calculation_timestamp=datetime.now(),
            parameters_version="1.0.0",
            model_version="1.0.0",
            ilm_gate_reason="Bucket 1 gating"
        )
        
        unified_result = UnifiedCalculationResult(CalculationMethod.SMA, sma_result)
        result_dict = unified_result.to_dict()
        
        assert result_dict["method"] == "sma"
        assert result_dict["run_id"] == self.run_id
        assert result_dict["entity_id"] == self.entity_id
        assert "business_indicator" in result_dict
        assert "business_indicator_component" in result_dict
        assert "loss_component" in result_dict
        assert "internal_loss_multiplier" in result_dict
        assert "bucket" in result_dict
        assert "ilm_gated" in result_dict
        assert "ilm_gate_reason" in result_dict
    
    def test_unified_result_to_dict_bia(self):
        """Test converting BIA result to dictionary"""
        # Create a mock BIA result
        from src.orm_calculator.services.bia_calculator import BIACalculationResult
        
        bia_result = BIACalculationResult(
            run_id=self.run_id,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            gi_years=[],
            positive_gi_years=[],
            average_gross_income=Decimal('1900000000'),
            alpha_coefficient=Decimal('0.15'),
            operational_risk_capital=Decimal('285000000'),
            risk_weighted_assets=Decimal('3562500000'),
            calculation_timestamp=datetime.now(),
            parameters_version="1.0.0",
            model_version="1.0.0",
            years_used=3,
            excluded_years=[]
        )
        
        unified_result = UnifiedCalculationResult(CalculationMethod.BIA, bia_result)
        result_dict = unified_result.to_dict()
        
        assert result_dict["method"] == "bia"
        assert result_dict["run_id"] == self.run_id
        assert result_dict["entity_id"] == self.entity_id
        assert "average_gross_income" in result_dict
        assert "alpha_coefficient" in result_dict
        assert "years_used" in result_dict
        assert "excluded_years" in result_dict
        assert "positive_gi_years" in result_dict
    
    def test_unified_result_to_dict_tsa(self):
        """Test converting TSA result to dictionary"""
        # Create a mock TSA result
        from src.orm_calculator.services.tsa_calculator import TSACalculationResult
        
        tsa_result = TSACalculationResult(
            run_id=self.run_id,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            business_line_data={},
            annual_calculations=[],
            three_year_average_capital=Decimal('200000000'),
            operational_risk_capital=Decimal('200000000'),
            risk_weighted_assets=Decimal('2500000000'),
            beta_factors={"retail_banking": Decimal('0.12')},
            calculation_timestamp=datetime.now(),
            parameters_version="1.0.0",
            model_version="1.0.0",
            years_used=3
        )
        
        unified_result = UnifiedCalculationResult(CalculationMethod.TSA, tsa_result)
        result_dict = unified_result.to_dict()
        
        assert result_dict["method"] == "tsa"
        assert result_dict["run_id"] == self.run_id
        assert result_dict["entity_id"] == self.entity_id
        assert "three_year_average_capital" in result_dict
        assert "beta_factors" in result_dict
        assert "years_used" in result_dict
        assert "annual_calculations" in result_dict