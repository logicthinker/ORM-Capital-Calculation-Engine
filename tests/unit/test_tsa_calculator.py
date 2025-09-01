"""
Unit tests for TSA Calculator

Tests the Traditional Standardized Approach calculation engine.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime

from src.orm_calculator.services.tsa_calculator import (
    TSACalculator,
    BusinessLineData,
    BusinessLine,
    TSACalculationResult
)


class TestTSACalculator:
    """Test suite for TSA Calculator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.calculator = TSACalculator()
        self.entity_id = "TEST_BANK_001"
        self.calculation_date = date(2024, 3, 31)
        self.run_id = "test_run_001"
    
    def test_tsa_calculator_initialization(self):
        """Test TSA calculator initialization with default parameters"""
        assert self.calculator.model_version == "1.0.0"
        assert self.calculator.parameters_version == "1.0.0"
        assert self.calculator.RWA_MULTIPLIER == Decimal('12.5')
        assert self.calculator.LOOKBACK_YEARS == 3
        assert self.calculator.ALLOW_NEGATIVE_OFFSET == True
        assert self.calculator.FLOOR_ANNUAL_AT_ZERO == True
        
        # Check beta factors
        assert self.calculator.BETA_FACTORS["retail_banking"] == Decimal('0.12')
        assert self.calculator.BETA_FACTORS["commercial_banking"] == Decimal('0.15')
        assert self.calculator.BETA_FACTORS["trading_sales"] == Decimal('0.18')
    
    def test_tsa_calculator_custom_parameters(self):
        """Test TSA calculator with custom parameters"""
        custom_params = {
            "beta_factors": {
                "retail_banking": Decimal('0.10'),
                "commercial_banking": Decimal('0.13')
            },
            "rwa_multiplier": Decimal('10.0'),
            "lookback_years": 5,
            "floor_annual_at_zero": False
        }
        
        calculator = TSACalculator(parameters=custom_params)
        
        assert calculator.BETA_FACTORS["retail_banking"] == Decimal('0.10')
        assert calculator.BETA_FACTORS["commercial_banking"] == Decimal('0.13')
        assert calculator.RWA_MULTIPLIER == Decimal('10.0')
        assert calculator.LOOKBACK_YEARS == 5
        assert calculator.FLOOR_ANNUAL_AT_ZERO == False
    
    def test_tsa_calculation_basic(self):
        """Test basic TSA calculation with multiple business lines"""
        bl_data = [
            # 2023 data
            BusinessLineData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.RETAIL_BANKING,
                gross_income=Decimal('1000000000'),  # ₹100 crore
                excluded_items=Decimal('50000000')   # ₹5 crore
            ),
            BusinessLineData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.COMMERCIAL_BANKING,
                gross_income=Decimal('800000000'),   # ₹80 crore
                excluded_items=Decimal('40000000')   # ₹4 crore
            ),
            # 2022 data
            BusinessLineData(
                period="2022",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.RETAIL_BANKING,
                gross_income=Decimal('950000000'),   # ₹95 crore
                excluded_items=Decimal('45000000')   # ₹4.5 crore
            ),
            BusinessLineData(
                period="2022",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.COMMERCIAL_BANKING,
                gross_income=Decimal('750000000'),   # ₹75 crore
                excluded_items=Decimal('35000000')   # ₹3.5 crore
            ),
            # 2021 data
            BusinessLineData(
                period="2021",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.RETAIL_BANKING,
                gross_income=Decimal('900000000'),   # ₹90 crore
                excluded_items=Decimal('40000000')   # ₹4 crore
            ),
            BusinessLineData(
                period="2021",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.COMMERCIAL_BANKING,
                gross_income=Decimal('700000000'),   # ₹70 crore
                excluded_items=Decimal('30000000')   # ₹3 crore
            )
        ]
        
        result = self.calculator.calculate_tsa(
            bl_data=bl_data,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id
        )
        
        # Check basic result structure
        assert result.years_used == 3
        assert len(result.annual_calculations) == 3
        
        # Check 2023 calculation
        # Retail: (1000-50) * 0.12 = 950 * 0.12 = 114 crore
        # Commercial: (800-40) * 0.15 = 760 * 0.15 = 114 crore
        # Total 2023: 114 + 114 = 228 crore
        calc_2023 = next(calc for calc in result.annual_calculations if calc["period"] == "2023")
        expected_retail_2023 = float(Decimal('950000000') * Decimal('0.12'))
        expected_commercial_2023 = float(Decimal('760000000') * Decimal('0.15'))
        
        assert calc_2023["business_line_charges"]["retail_banking"] == expected_retail_2023
        assert calc_2023["business_line_charges"]["commercial_banking"] == expected_commercial_2023
        
        # Check that ORC and RWA are calculated
        assert result.operational_risk_capital > 0
        assert result.risk_weighted_assets == result.operational_risk_capital * Decimal('12.5')
    
    def test_tsa_calculation_negative_offset(self):
        """Test TSA calculation with negative business line income"""
        bl_data = [
            # 2023 data with one negative business line
            BusinessLineData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.RETAIL_BANKING,
                gross_income=Decimal('1000000000'),  # ₹100 crore
                excluded_items=Decimal('0')
            ),
            BusinessLineData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.TRADING_SALES,
                gross_income=Decimal('200000000'),   # ₹20 crore
                excluded_items=Decimal('300000000')  # ₹30 crore (negative result)
            )
        ]
        
        result = self.calculator.calculate_tsa(
            bl_data=bl_data,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id
        )
        
        # Check that negative offset is applied within the year
        calc_2023 = result.annual_calculations[0]
        retail_charge = Decimal('1000000000') * Decimal('0.12')  # 120 crore
        trading_charge = Decimal('-100000000') * Decimal('0.18')  # -18 crore
        expected_total = retail_charge + trading_charge  # 102 crore
        
        assert calc_2023["business_line_charges"]["retail_banking"] == float(retail_charge)
        assert calc_2023["business_line_charges"]["trading_sales"] == float(trading_charge)
        assert calc_2023["total_before_floor"] == float(expected_total)
    
    def test_tsa_calculation_annual_floor(self):
        """Test TSA calculation with annual floor at zero"""
        bl_data = [
            # 2023 data with overall negative result
            BusinessLineData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.RETAIL_BANKING,
                gross_income=Decimal('100000000'),   # ₹10 crore
                excluded_items=Decimal('0')
            ),
            BusinessLineData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.TRADING_SALES,
                gross_income=Decimal('200000000'),   # ₹20 crore
                excluded_items=Decimal('800000000')  # ₹80 crore (very negative)
            )
        ]
        
        result = self.calculator.calculate_tsa(
            bl_data=bl_data,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id
        )
        
        # Check that annual floor is applied
        calc_2023 = result.annual_calculations[0]
        assert calc_2023["total_before_floor"] < 0
        assert calc_2023["total_after_floor"] == 0.0
        assert calc_2023["floor_applied"] == True
    
    def test_tsa_calculation_no_floor(self):
        """Test TSA calculation without annual floor"""
        # Create calculator without floor
        calculator = TSACalculator(parameters={"floor_annual_at_zero": False})
        
        bl_data = [
            BusinessLineData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.RETAIL_BANKING,
                gross_income=Decimal('100000000'),
                excluded_items=Decimal('0')
            ),
            BusinessLineData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.TRADING_SALES,
                gross_income=Decimal('200000000'),
                excluded_items=Decimal('800000000')  # Very negative
            )
        ]
        
        result = calculator.calculate_tsa(
            bl_data=bl_data,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id
        )
        
        # Check that floor is not applied
        calc_2023 = result.annual_calculations[0]
        assert calc_2023["total_before_floor"] < 0
        assert calc_2023["total_after_floor"] == calc_2023["total_before_floor"]
        assert calc_2023["floor_applied"] == False
    
    def test_tsa_calculation_empty_data(self):
        """Test TSA calculation fails with empty data"""
        with pytest.raises(ValueError, match="Business line data cannot be empty"):
            self.calculator.calculate_tsa(
                bl_data=[],
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                run_id=self.run_id
            )
    
    def test_tsa_business_line_mapping(self):
        """Test TSA business line mapping"""
        mapping = self.calculator.get_business_line_mapping()
        
        assert len(mapping) == 8  # Should have 8 business lines
        assert "retail_banking" in mapping
        assert "commercial_banking" in mapping
        assert "trading_sales" in mapping
        assert "corporate_finance" in mapping
        assert "payment_settlement" in mapping
        assert "agency_services" in mapping
        assert "asset_management" in mapping
        assert "retail_brokerage" in mapping
        
        # Check descriptions
        assert mapping["retail_banking"] == "Retail Banking"
        assert mapping["trading_sales"] == "Trading & Sales"
    
    def test_tsa_input_validation(self):
        """Test TSA input validation"""
        # Test empty data
        errors = self.calculator.validate_inputs([])
        assert "Business line data cannot be empty" in errors
        
        # Test invalid data
        invalid_data = [
            BusinessLineData(
                period="",  # Empty period
                entity_id="",  # Empty entity ID
                calculation_date=self.calculation_date,
                business_line=BusinessLine.RETAIL_BANKING,
                gross_income=Decimal('1000000000'),
                excluded_items=Decimal('-50000000')  # Negative exclusions
            )
        ]
        
        errors = self.calculator.validate_inputs(invalid_data)
        assert len(errors) >= 3  # Should have multiple validation errors
        assert any("Entity ID is required" in error for error in errors)
        assert any("Period is required" in error for error in errors)
        assert any("Excluded items cannot be negative" in error for error in errors)
    
    def test_tsa_parameter_update(self):
        """Test TSA parameter updates"""
        new_params = {
            "beta_factors": {
                "retail_banking": Decimal('0.10')
            },
            "rwa_multiplier": Decimal('15.0')
        }
        
        self.calculator.update_parameters(new_params)
        
        assert self.calculator.BETA_FACTORS["retail_banking"] == Decimal('0.10')
        assert self.calculator.RWA_MULTIPLIER == Decimal('15.0')
    
    def test_tsa_calculation_metadata(self):
        """Test TSA calculation metadata"""
        metadata = self.calculator.get_calculation_metadata()
        
        assert metadata["method"] == "TSA"
        assert metadata["model_version"] == "1.0.0"
        assert metadata["rwa_multiplier"] == 12.5
        assert metadata["lookback_years"] == 3
        assert metadata["allow_negative_offset"] == True
        assert metadata["floor_annual_at_zero"] == True
        assert "beta_factors" in metadata
        assert len(metadata["beta_factors"]) == 8
    
    def test_tsa_calculation_result_structure(self):
        """Test TSA calculation result structure"""
        bl_data = [
            BusinessLineData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.RETAIL_BANKING,
                gross_income=Decimal('1000000000'),
                excluded_items=Decimal('50000000')
            )
        ]
        
        result = self.calculator.calculate_tsa(
            bl_data=bl_data,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id
        )
        
        # Check result structure
        assert isinstance(result, TSACalculationResult)
        assert result.run_id == self.run_id
        assert result.entity_id == self.entity_id
        assert result.calculation_date == self.calculation_date
        assert isinstance(result.business_line_data, dict)
        assert isinstance(result.annual_calculations, list)
        assert isinstance(result.three_year_average_capital, Decimal)
        assert isinstance(result.operational_risk_capital, Decimal)
        assert isinstance(result.risk_weighted_assets, Decimal)
        assert isinstance(result.beta_factors, dict)
        assert isinstance(result.calculation_timestamp, datetime)
        assert result.parameters_version == "1.0.0"
        assert result.model_version == "1.0.0"
        assert isinstance(result.years_used, int)
        assert result.parameters_used is not None
    
    def test_tsa_calculation_precision(self):
        """Test TSA calculation precision and rounding"""
        bl_data = [
            BusinessLineData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.RETAIL_BANKING,
                gross_income=Decimal('1000000000.33'),  # Test decimal precision
                excluded_items=Decimal('0')
            )
        ]
        
        result = self.calculator.calculate_tsa(
            bl_data=bl_data,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id
        )
        
        # Check that results are properly rounded to 2 decimal places
        assert result.operational_risk_capital.as_tuple().exponent >= -2
        assert result.risk_weighted_assets.as_tuple().exponent >= -2
    
    def test_tsa_multiple_entries_same_business_line(self):
        """Test TSA calculation with multiple entries for same business line in same period"""
        bl_data = [
            # Two entries for retail banking in 2023
            BusinessLineData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.RETAIL_BANKING,
                gross_income=Decimal('500000000'),
                excluded_items=Decimal('25000000')
            ),
            BusinessLineData(
                period="2023",
                entity_id=self.entity_id,
                calculation_date=self.calculation_date,
                business_line=BusinessLine.RETAIL_BANKING,
                gross_income=Decimal('600000000'),
                excluded_items=Decimal('30000000')
            )
        ]
        
        result = self.calculator.calculate_tsa(
            bl_data=bl_data,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id
        )
        
        # Should aggregate both entries: (500-25) + (600-30) = 1045 crore
        # Capital charge: 1045 * 0.12 = 125.4 crore
        calc_2023 = result.annual_calculations[0]
        expected_charge = float(Decimal('1045000000') * Decimal('0.12'))
        assert calc_2023["business_line_charges"]["retail_banking"] == expected_charge
    
    def test_tsa_lookback_years_limit(self):
        """Test TSA respects lookback years limit"""
        # Create 5 years of data but calculator should only use 3
        bl_data = []
        for year in range(2019, 2024):  # 2019-2023 (5 years)
            bl_data.append(
                BusinessLineData(
                    period=str(year),
                    entity_id=self.entity_id,
                    calculation_date=self.calculation_date,
                    business_line=BusinessLine.RETAIL_BANKING,
                    gross_income=Decimal('1000000000'),
                    excluded_items=Decimal('0')
                )
            )
        
        result = self.calculator.calculate_tsa(
            bl_data=bl_data,
            entity_id=self.entity_id,
            calculation_date=self.calculation_date,
            run_id=self.run_id
        )
        
        # Should only use 3 most recent years (2021, 2022, 2023)
        assert len(result.annual_calculations) == 3
        assert result.years_used == 3
        periods_used = [calc["period"] for calc in result.annual_calculations]
        assert "2023" in periods_used
        assert "2022" in periods_used
        assert "2021" in periods_used
        assert "2020" not in periods_used
        assert "2019" not in periods_used