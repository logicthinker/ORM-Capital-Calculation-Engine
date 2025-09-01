"""
Unit tests for BIA Calculator

Tests the Basic Indicator Approach calculation engine.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime

from src.orm_calculator.services.bia_calculator import (
    BIACalculator,
    GrossIncomeData,
    BIACalculationResult
)


class TestBIACalculator:
    """Test suite for BIA Calculator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.calculator = BIACalculator()
        self.entity_id = "TEST_BANK_001"
        self.calculation_date = date(2024, 3, 31)
        self.run_id = "test_run_001"
    
    def test_bia_calculator_initialization(self):
        """Test BIA calculator initialization with default parameters"""
        assert self.calculator.model_version == "1.0.0"
        assert self.calculator.parameters_version == "1.0.0"
        assert self.calculator.ALPHA_COEFFICIENT == Decimal('0.15')
        assert self.calculator.RWA_MULTIPLIER == Decimal('12.5')
        assert self.calculator.LOOKBACK_YEARS == 3
    
    def test_bia_calculator_custom_parameters(self):
        """Test BIA calculator with custom parameters"""
        custom_params = {
            "alpha_coefficient": Decimal('0.18'),
            "rwa_multiplier": Decimal('10.0'),
            "lookback_years": 5
        }
        
        calculator = BIACalculator(parameters=custom_params)
        
        assert calculator.ALPHA_COEFFICIENT == Decimal('0.18')
        assert calculator.RWA_MULTIPLIER == Decimal('10.0')
        assert calculator.LOOKBACK_YEARS == 5
    
    def test_bia_calculation_positive_years_only(self):
        """Test BIA calculation uses only positive GI years"""
        gi_data = [
            GrossIncomeData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                gross_income=Decimal('2000000000'),  # ₹200 crore
                excluded_items=Decimal('50000000')   # ₹5 crore
            ),
            GrossIncomeData(
                period="2022",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                gross_income=Decimal('1000000000'),  # ₹100 crore
                excluded_items=Decimal('1200000000') # ₹120 crore (results in negative)
            ),
            GrossIncomeData(
                period="2021",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                gross_income=Decimal('1800000000'),  # ₹180 crore
                excluded_items=Decimal('40000000')   # ₹4 crore
            )
        ]
        
        result = self.calculator.calculate_bia(
            gi_data=gi_data,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id
        )
        
        # Should only use 2023 and 2021 (positive years)
        assert result.years_used == 2
        assert "2022" in result.excluded_years
        assert len(result.positive_gi_years) == 2
        
        # Check calculation: (1950 + 1760) / 2 = 1855 crore
        expected_avg = (Decimal('1950000000') + Decimal('1760000000')) / Decimal('2')
        assert result.average_gross_income == expected_avg
        
        # Check ORC: 1855 * 0.15 = 278.25 crore
        expected_orc = expected_avg * Decimal('0.15')
        assert result.operational_risk_capital == expected_orc.quantize(Decimal('0.01'))
        
        # Check RWA: 278.25 * 12.5 = 3478.125 crore
        expected_rwa = expected_orc * Decimal('12.5')
        assert result.risk_weighted_assets == expected_rwa.quantize(Decimal('0.01'))
    
    def test_bia_calculation_all_positive_years(self):
        """Test BIA calculation with all positive GI years"""
        gi_data = [
            GrossIncomeData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                gross_income=Decimal('2000000000'),
                excluded_items=Decimal('50000000')
            ),
            GrossIncomeData(
                period="2022",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                gross_income=Decimal('1900000000'),
                excluded_items=Decimal('45000000')
            ),
            GrossIncomeData(
                period="2021",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                gross_income=Decimal('1800000000'),
                excluded_items=Decimal('40000000')
            )
        ]
        
        result = self.calculator.calculate_bia(
            gi_data=gi_data,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id
        )
        
        # Should use all 3 years
        assert result.years_used == 3
        assert len(result.excluded_years) == 0
        assert len(result.positive_gi_years) == 3
        
        # Check calculation: (1950 + 1855 + 1760) / 3 = 1855 crore
        expected_avg = (Decimal('1950000000') + Decimal('1855000000') + Decimal('1760000000')) / Decimal('3')
        assert result.average_gross_income == expected_avg
    
    def test_bia_calculation_no_positive_years(self):
        """Test BIA calculation fails with no positive GI years"""
        gi_data = [
            GrossIncomeData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                gross_income=Decimal('1000000000'),
                excluded_items=Decimal('1200000000')  # Negative result
            ),
            GrossIncomeData(
                period="2022",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                gross_income=Decimal('800000000'),
                excluded_items=Decimal('900000000')   # Negative result
            )
        ]
        
        with pytest.raises(ValueError, match="No positive Gross Income years available"):
            self.calculator.calculate_bia(
                gi_data=gi_data,
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                run_id=self.run_id
            )
    
    def test_bia_calculation_empty_data(self):
        """Test BIA calculation fails with empty data"""
        with pytest.raises(ValueError, match="Gross Income data cannot be empty"):
            self.calculator.calculate_bia(
                gi_data=[],
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                run_id=self.run_id
            )
    
    def test_bia_calculation_prescribed_exclusions(self):
        """Test BIA calculation properly handles prescribed exclusions"""
        gi_data = [
            GrossIncomeData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                gross_income=Decimal('2000000000'),
                excluded_items=Decimal('100000000')  # ₹10 crore exclusions
            )
        ]
        
        result = self.calculator.calculate_bia(
            gi_data=gi_data,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id
        )
        
        # Net GI should be 2000 - 100 = 1900 crore
        assert result.positive_gi_years[0]["net_gross_income"] == 1900000000.0
        assert result.average_gross_income == Decimal('1900000000')
    
    def test_bia_parameter_update(self):
        """Test BIA parameter updates"""
        new_params = {
            "alpha_coefficient": Decimal('0.20'),
            "rwa_multiplier": Decimal('15.0')
        }
        
        self.calculator.update_parameters(new_params)
        
        assert self.calculator.ALPHA_COEFFICIENT == Decimal('0.20')
        assert self.calculator.RWA_MULTIPLIER == Decimal('15.0')
    
    def test_bia_input_validation(self):
        """Test BIA input validation"""
        # Test empty data
        errors = self.calculator.validate_inputs([])
        assert "Gross Income data cannot be empty" in errors
        
        # Test invalid data
        invalid_data = [
            GrossIncomeData(
                period="",  # Empty period
                entity_id="",  # Empty entity ID
                calculation_date=self.calculation_date,
                gross_income=Decimal('1000000000'),
                excluded_items=Decimal('-50000000')  # Negative exclusions
            )
        ]
        
        errors = self.calculator.validate_inputs(invalid_data)
        assert len(errors) >= 3  # Should have multiple validation errors
        assert any("Entity ID is required" in error for error in errors)
        assert any("Period is required" in error for error in errors)
        assert any("Excluded items cannot be negative" in error for error in errors)
    
    def test_bia_calculation_metadata(self):
        """Test BIA calculation metadata"""
        metadata = self.calculator.get_calculation_metadata()
        
        assert metadata["method"] == "BIA"
        assert metadata["model_version"] == "1.0.0"
        assert metadata["alpha_coefficient"] == 0.15
        assert metadata["rwa_multiplier"] == 12.5
        assert metadata["lookback_years"] == 3
        assert "prescribed_exclusions" in metadata
    
    def test_bia_calculation_result_structure(self):
        """Test BIA calculation result structure"""
        gi_data = [
            GrossIncomeData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                gross_income=Decimal('2000000000'),
                excluded_items=Decimal('50000000')
            )
        ]
        
        result = self.calculator.calculate_bia(
            gi_data=gi_data,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id
        )
        
        # Check result structure
        assert isinstance(result, BIACalculationResult)
        assert result.run_id == self.run_id
        assert result.entity_id == self.entity_id
        assert result.calculation_date == self.calculation_date
        assert isinstance(result.gi_years, list)
        assert isinstance(result.positive_gi_years, list)
        assert isinstance(result.average_gross_income, Decimal)
        assert isinstance(result.alpha_coefficient, Decimal)
        assert isinstance(result.operational_risk_capital, Decimal)
        assert isinstance(result.risk_weighted_assets, Decimal)
        assert isinstance(result.calculation_timestamp, datetime)
        assert result.parameters_version == "1.0.0"
        assert result.model_version == "1.0.0"
        assert isinstance(result.years_used, int)
        assert isinstance(result.excluded_years, list)
        assert result.parameters_used is not None
    
    def test_bia_calculation_precision(self):
        """Test BIA calculation precision and rounding"""
        gi_data = [
            GrossIncomeData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                gross_income=Decimal('1000000000.33'),  # Test decimal precision
                excluded_items=Decimal('0')
            )
        ]
        
        result = self.calculator.calculate_bia(
            gi_data=gi_data,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id
        )
        
        # Check that results are properly rounded to 2 decimal places
        assert result.operational_risk_capital.as_tuple().exponent >= -2
        assert result.risk_weighted_assets.as_tuple().exponent >= -2
    
    def test_bia_lookback_years_limit(self):
        """Test BIA respects lookback years limit"""
        # Create 5 years of data but calculator should only use 3
        gi_data = []
        for year in range(2019, 2024):  # 2019-2023 (5 years)
            gi_data.append(
                GrossIncomeData(
                    period=str(year),
                    entity_id=self.entity_id,
                    calculation_date=self.calculation_date,
                    gross_income=Decimal('1000000000'),
                    excluded_items=Decimal('0')
                )
            )
        
        result = self.calculator.calculate_bia(
            gi_data=gi_data,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id
        )
        
        # Should only use 3 most recent years (2021, 2022, 2023)
        assert len(result.gi_years) == 3
        assert result.years_used == 3
        periods_used = [year["period"] for year in result.gi_years]
        assert "2023" in periods_used
        assert "2022" in periods_used
        assert "2021" in periods_used
        assert "2020" not in periods_used
        assert "2019" not in periods_used