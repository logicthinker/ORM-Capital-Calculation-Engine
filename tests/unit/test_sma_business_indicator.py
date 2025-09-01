"""
Unit Tests: SMA Business Indicator (BI) Calculation

Test cases SMA-U-001 through SMA-U-005 from the comprehensive test plan.
These tests cover the core BI calculation logic with various data scenarios.
"""

import pytest
from decimal import Decimal
from datetime import date

from src.orm_calculator.services.sma_calculator import (
    SMACalculator,
    BusinessIndicatorData,
)


@pytest.mark.unit
class TestSMABusinessIndicator:
    """Unit tests for Business Indicator calculation"""
    
    def test_sma_u_001_happy_path_3_year_bi_calculation(self, sma_calculator):
        """
        Test Case ID: SMA-U-001
        Description: Happy Path: Calculate BI for a standard 3-year period with positive values.
        """
        # Arrange
        bi_data = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('50000000000'),  # ₹5,000 crore
                sc=Decimal('20000000000'),    # ₹2,000 crore
                fc=Decimal('10000000000'),    # ₹1,000 crore
                entity_id="TEST_BANK",
                calculation_date=date(2023, 12, 31)
            ),
            BusinessIndicatorData(
                period="2022",
                ildc=Decimal('48000000000'),  # ₹4,800 crore
                sc=Decimal('22000000000'),    # ₹2,200 crore
                fc=Decimal('12000000000'),    # ₹1,200 crore
                entity_id="TEST_BANK",
                calculation_date=date(2022, 12, 31)
            ),
            BusinessIndicatorData(
                period="2021",
                ildc=Decimal('45000000000'),  # ₹4,500 crore
                sc=Decimal('18000000000'),    # ₹1,800 crore
                fc=Decimal('9000000000'),     # ₹900 crore
                entity_id="TEST_BANK",
                calculation_date=date(2021, 12, 31)
            )
        ]
        
        # Act
        current_bi, three_year_avg = sma_calculator.calculate_business_indicator(bi_data)
        
        # Assert
        # Current BI (2023) = 5000 + 2000 + 1000 = 8000 crore
        expected_current = Decimal('80000000000')
        assert current_bi == expected_current
        
        # Three-year average = (8000 + 8200 + 7200) / 3 = 7800 crore
        expected_avg = Decimal('78000000000')
        assert three_year_avg == expected_avg
    
    def test_sma_u_002_edge_case_zero_components(self, sma_calculator):
        """
        Test Case ID: SMA-U-002
        Description: Edge Case: Calculate BI with zero values for one or more components.
        """
        # Arrange
        bi_data = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('0'),            # Zero ILDC
                sc=Decimal('20000000000'),    # ₹2,000 crore
                fc=Decimal('10000000000'),    # ₹1,000 crore
                entity_id="ZERO_COMPONENT_BANK",
                calculation_date=date(2023, 12, 31)
            ),
            BusinessIndicatorData(
                period="2022",
                ildc=Decimal('48000000000'),  # ₹4,800 crore
                sc=Decimal('0'),              # Zero SC
                fc=Decimal('12000000000'),    # ₹1,200 crore
                entity_id="ZERO_COMPONENT_BANK",
                calculation_date=date(2022, 12, 31)
            ),
            BusinessIndicatorData(
                period="2021",
                ildc=Decimal('45000000000'),  # ₹4,500 crore
                sc=Decimal('18000000000'),    # ₹1,800 crore
                fc=Decimal('0'),              # Zero FC
                entity_id="ZERO_COMPONENT_BANK",
                calculation_date=date(2021, 12, 31)
            )
        ]
        
        # Act
        current_bi, three_year_avg = sma_calculator.calculate_business_indicator(bi_data)
        
        # Assert
        # Current BI (2023) = 0 + 2000 + 1000 = 3000 crore
        expected_current = Decimal('30000000000')
        assert current_bi == expected_current
        
        # Three-year average = (3000 + 6000 + 6300) / 3 = 5100 crore
        expected_avg = Decimal('51000000000')
        assert three_year_avg == expected_avg
    
    def test_sma_u_003_edge_case_entire_year_zero_bi(self, sma_calculator):
        """
        Test Case ID: SMA-U-003
        Description: Edge Case: Calculate BI where one entire year has zero BI.
        """
        # Arrange
        bi_data = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('0'),  # All zero
                sc=Decimal('0'),
                fc=Decimal('0'),
                entity_id="ZERO_YEAR_BANK",
                calculation_date=date(2023, 12, 31)
            ),
            BusinessIndicatorData(
                period="2022",
                ildc=Decimal('48000000000'),  # ₹4,800 crore
                sc=Decimal('22000000000'),    # ₹2,200 crore
                fc=Decimal('12000000000'),    # ₹1,200 crore
                entity_id="ZERO_YEAR_BANK",
                calculation_date=date(2022, 12, 31)
            ),
            BusinessIndicatorData(
                period="2021",
                ildc=Decimal('45000000000'),  # ₹4,500 crore
                sc=Decimal('18000000000'),    # ₹1,800 crore
                fc=Decimal('9000000000'),     # ₹900 crore
                entity_id="ZERO_YEAR_BANK",
                calculation_date=date(2021, 12, 31)
            )
        ]
        
        # Act
        current_bi, three_year_avg = sma_calculator.calculate_business_indicator(bi_data)
        
        # Assert
        # Current BI (2023) = 0 + 0 + 0 = 0 crore
        expected_current = Decimal('0')
        assert current_bi == expected_current
        
        # Three-year average = (0 + 8200 + 7200) / 3 = 5133.33 crore
        expected_avg = Decimal('51333333333.33')
        assert abs(three_year_avg - expected_avg) < Decimal('0.01')
    
    def test_sma_u_004_negative_case_rbi_max_min_abs_operations(self, sma_calculator):
        """
        Test Case ID: SMA-U-004
        Description: Negative Case: Calculate BI with negative values applying RBI Max/Min/Abs operations.
        """
        # Arrange
        bi_data = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('-10000000000'),  # Negative ILDC (should take abs)
                sc=Decimal('-5000000000'),     # Negative SC (should take max with 0)
                fc=Decimal('15000000000'),     # Positive FC
                entity_id="NEGATIVE_VALUES_BANK",
                calculation_date=date(2023, 12, 31)
            ),
            BusinessIndicatorData(
                period="2022",
                ildc=Decimal('48000000000'),   # Positive ILDC
                sc=Decimal('-2000000000'),     # Negative SC
                fc=Decimal('-12000000000'),    # Negative FC (should take abs)
                entity_id="NEGATIVE_VALUES_BANK",
                calculation_date=date(2022, 12, 31)
            ),
            BusinessIndicatorData(
                period="2021",
                ildc=Decimal('-45000000000'),  # Negative ILDC
                sc=Decimal('18000000000'),     # Positive SC
                fc=Decimal('-9000000000'),     # Negative FC
                entity_id="NEGATIVE_VALUES_BANK",
                calculation_date=date(2021, 12, 31)
            )
        ]
        
        # Act
        current_bi, three_year_avg = sma_calculator.calculate_business_indicator(bi_data)
        
        # Assert
        # Current BI (2023) = abs(-1000) + max(-500, 0) + abs(1500) = 1000 + 0 + 1500 = 2500 crore
        expected_current = Decimal('25000000000')
        assert current_bi == expected_current
        
        # 2022: abs(4800) + max(-200, 0) + abs(-1200) = 4800 + 0 + 1200 = 6000 crore
        # 2021: abs(-4500) + max(1800, 0) + abs(-900) = 4500 + 1800 + 900 = 7200 crore
        # Three-year average = (2500 + 6000 + 7200) / 3 = 5233.33 crore
        expected_avg = Decimal('52333333333.33')
        assert abs(three_year_avg - expected_avg) < Decimal('0.01')
    
    def test_sma_u_005_data_validation_missing_data(self, sma_calculator):
        """
        Test Case ID: SMA-U-005
        Description: Data Validation: Attempt to calculate BI with missing data for a year.
        """
        # Arrange - Only 2 years of data instead of 3
        bi_data = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('50000000000'),
                sc=Decimal('20000000000'),
                fc=Decimal('10000000000'),
                entity_id="INSUFFICIENT_DATA_BANK",
                calculation_date=date(2023, 12, 31)
            ),
            BusinessIndicatorData(
                period="2022",
                ildc=Decimal('48000000000'),
                sc=Decimal('22000000000'),
                fc=Decimal('12000000000'),
                entity_id="INSUFFICIENT_DATA_BANK",
                calculation_date=date(2022, 12, 31)
            )
        ]
        
        # Act
        current_bi, three_year_avg = sma_calculator.calculate_business_indicator(bi_data)
        
        # Assert
        # Should still calculate with available data (2-year average)
        expected_current = Decimal('80000000000')  # ₹8,000 crore
        assert current_bi == expected_current
        
        # Two-year average = (8000 + 8200) / 2 = 8100 crore
        expected_avg = Decimal('81000000000')
        assert three_year_avg == expected_avg
    
    def test_sma_u_005_validation_empty_data(self, sma_calculator):
        """
        Test Case ID: SMA-U-005 (Extended)
        Description: Data Validation: Attempt to calculate BI with empty data.
        """
        # Arrange
        bi_data = []
        
        # Act & Assert
        with pytest.raises(ValueError, match="Business Indicator data cannot be empty"):
            sma_calculator.calculate_business_indicator(bi_data)
    
    def test_bi_calculation_single_year_data(self, sma_calculator):
        """
        Additional Test: Calculate BI with only one year of data.
        """
        # Arrange
        bi_data = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('50000000000'),
                sc=Decimal('20000000000'),
                fc=Decimal('10000000000'),
                entity_id="SINGLE_YEAR_BANK",
                calculation_date=date(2023, 12, 31)
            )
        ]
        
        # Act
        current_bi, three_year_avg = sma_calculator.calculate_business_indicator(bi_data)
        
        # Assert
        expected_bi = Decimal('80000000000')  # ₹8,000 crore
        assert current_bi == expected_bi
        assert three_year_avg == expected_bi  # Same as current when only one year
    
    def test_bi_calculation_unsorted_periods(self, sma_calculator):
        """
        Additional Test: Calculate BI with unsorted period data.
        """
        # Arrange - Periods in random order
        bi_data = [
            BusinessIndicatorData(
                period="2021",
                ildc=Decimal('45000000000'),
                sc=Decimal('18000000000'),
                fc=Decimal('9000000000'),
                entity_id="UNSORTED_BANK",
                calculation_date=date(2021, 12, 31)
            ),
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('50000000000'),
                sc=Decimal('20000000000'),
                fc=Decimal('10000000000'),
                entity_id="UNSORTED_BANK",
                calculation_date=date(2023, 12, 31)
            ),
            BusinessIndicatorData(
                period="2022",
                ildc=Decimal('48000000000'),
                sc=Decimal('22000000000'),
                fc=Decimal('12000000000'),
                entity_id="UNSORTED_BANK",
                calculation_date=date(2022, 12, 31)
            )
        ]
        
        # Act
        current_bi, three_year_avg = sma_calculator.calculate_business_indicator(bi_data)
        
        # Assert
        # Should correctly identify 2023 as current year regardless of input order
        expected_current = Decimal('80000000000')  # ₹8,000 crore
        assert current_bi == expected_current
        
        # Three-year average should be calculated correctly
        expected_avg = Decimal('78000000000')  # ₹7,800 crore
        assert three_year_avg == expected_avg
    
    def test_bi_calculation_precision_handling(self, sma_calculator):
        """
        Additional Test: Test precision handling with fractional values.
        """
        # Arrange
        bi_data = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('33333333333.33'),  # ₹3,333.33 crore
                sc=Decimal('16666666666.67'),    # ₹1,666.67 crore
                fc=Decimal('10000000000.00'),    # ₹1,000.00 crore
                entity_id="PRECISION_BANK",
                calculation_date=date(2023, 12, 31)
            )
        ]
        
        # Act
        current_bi, three_year_avg = sma_calculator.calculate_business_indicator(bi_data)
        
        # Assert
        expected_bi = Decimal('60000000000.00')  # ₹6,000.00 crore
        assert current_bi == expected_bi
        assert three_year_avg == expected_bi
    
    def test_bi_validation_comprehensive(self, sma_calculator):
        """
        Additional Test: Comprehensive validation testing.
        """
        # Test with valid data
        valid_bi_data = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('50000000000'),
                sc=Decimal('20000000000'),
                fc=Decimal('10000000000'),
                entity_id="VALID_BANK",
                calculation_date=date(2023, 12, 31)
            )
        ]
        
        valid_loss_data = []
        
        # Act
        errors = sma_calculator.validate_inputs(valid_bi_data, valid_loss_data)
        
        # Assert
        assert len(errors) == 0  # No validation errors
        
        # Test with invalid data
        invalid_bi_data = [
            BusinessIndicatorData(
                period="",  # Empty period
                ildc=Decimal('-10000000000'),
                sc=Decimal('-5000000000'),
                fc=Decimal('-15000000000'),  # All negative
                entity_id="",  # Empty entity ID
                calculation_date=date(2023, 12, 31)
            )
        ]
        
        # Act
        errors = sma_calculator.validate_inputs(invalid_bi_data, valid_loss_data)
        
        # Assert
        assert len(errors) >= 2  # Should have multiple validation errors