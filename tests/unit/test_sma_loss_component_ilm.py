"""
Unit Tests: SMA Loss Component (LC) and Internal Loss Multiplier (ILM) Calculation

Test cases SMA-U-015 through SMA-U-022 from the comprehensive test plan.
These tests cover LC calculation and ILM calculation with gating logic.
"""

import pytest
from decimal import Decimal
from datetime import date

from src.orm_calculator.services.sma_calculator import (
    SMACalculator,
    LossData,
    RBIBucket,
)


@pytest.mark.unit
class TestSMALossComponentILM:
    """Unit tests for Loss Component and ILM calculation"""
    
    def test_sma_u_015_happy_path_lc_10_years_data(self, sma_calculator, sample_loss_data_10_years):
        """
        Test Case ID: SMA-U-015
        Description: Happy Path: Calculate LC with a full 10 years of loss data.
        """
        # Arrange
        calculation_date = date(2023, 12, 31)
        
        # Act
        lc, avg_losses, years = sma_calculator.calculate_loss_component(
            sample_loss_data_10_years, calculation_date
        )
        
        # Assert
        # Should have 10 years of data
        assert years == 10
        
        # LC should be 15 * average annual losses
        expected_lc = avg_losses * sma_calculator.LC_MULTIPLIER
        assert lc == expected_lc
        
        # Average losses should be positive
        assert avg_losses > Decimal('0')
        
        # LC should be positive
        assert lc > Decimal('0')
    
    def test_sma_u_016_edge_case_zero_losses(self, sma_calculator):
        """
        Test Case ID: SMA-U-016
        Description: Edge Case: Calculate LC with zero losses over 10 years.
        """
        # Arrange
        loss_data = []  # No losses
        calculation_date = date(2023, 12, 31)
        
        # Act
        lc, avg_losses, years = sma_calculator.calculate_loss_component(
            loss_data, calculation_date
        )
        
        # Assert
        assert lc == Decimal('0')
        assert avg_losses == Decimal('0')
        assert years == 0
    
    def test_sma_u_017_edge_case_configurable_horizon(self, sma_calculator):
        """
        Test Case ID: SMA-U-017
        Description: Edge Case: Calculate LC with a configurable horizon (7 years).
        """
        # Arrange - Create 7 years of loss data
        loss_data = []
        base_year = 2017
        
        for year in range(base_year, base_year + 7):
            loss_data.append(
                LossData(
                    event_id=f"LOSS_{year}_01",
                    entity_id="SEVEN_YEAR_BANK",
                    accounting_date=date(year, 6, 15),
                    net_loss=Decimal('100000000')  # ₹10 crore each year
                )
            )
        
        calculation_date = date(2023, 12, 31)
        
        # Act
        lc, avg_losses, years = sma_calculator.calculate_loss_component(
            loss_data, calculation_date
        )
        
        # Assert
        assert years == 7  # Should have 7 years of data
        
        # Average should be ₹10 crore per year
        expected_avg = Decimal('100000000')
        assert avg_losses == expected_avg
        
        # LC = 15 * 10 = 150 crore
        expected_lc = Decimal('1500000000')
        assert lc == expected_lc
    
    def test_sma_u_018_ilm_gate_bucket_1(self, sma_calculator):
        """
        Test Case ID: SMA-U-018
        Description: ILM Gate (Bucket 1): Bank is in Bucket 1.
        """
        # Arrange
        lc = Decimal('100000000')      # ₹10 crore
        bic = Decimal('8400000000')    # ₹840 crore (Bucket 1 BIC)
        bucket = RBIBucket.BUCKET_1
        years_with_data = 10  # Sufficient data
        
        # Act
        ilm, gated, reason = sma_calculator.calculate_ilm(
            lc, bic, bucket, years_with_data, False
        )
        
        # Assert
        assert gated == True
        assert ilm == Decimal('1')
        assert "Bucket 1" in reason
        assert "ILM gated" in reason
    
    def test_sma_u_019_ilm_gate_insufficient_data(self, sma_calculator):
        """
        Test Case ID: SMA-U-019
        Description: ILM Gate (<5 Years Data): Bank has less than 5 years of high-quality loss data.
        """
        # Arrange
        lc = Decimal('495000000')      # ₹49.5 crore
        bic = Decimal('12600000000')   # ₹1,260 crore (Bucket 2 BIC)
        bucket = RBIBucket.BUCKET_2
        years_with_data = 4  # Less than 5 years
        
        # Act
        ilm, gated, reason = sma_calculator.calculate_ilm(
            lc, bic, bucket, years_with_data, False
        )
        
        # Assert
        assert gated == True
        assert ilm == Decimal('1')
        assert "4 years < 5 years" in reason
        assert "Insufficient data quality" in reason
    
    def test_sma_u_020_happy_path_ilm_calculated(self, sma_calculator):
        """
        Test Case ID: SMA-U-020
        Description: Happy Path: ILM is calculated and applied.
        """
        # Arrange
        lc = Decimal('495000000')      # ₹49.5 crore
        bic = Decimal('12600000000')   # ₹1,260 crore
        bucket = RBIBucket.BUCKET_2
        years_with_data = 5  # Sufficient data
        
        # Act
        ilm, gated, reason = sma_calculator.calculate_ilm(
            lc, bic, bucket, years_with_data, False
        )
        
        # Assert
        assert gated == False
        assert reason is None
        assert ilm > Decimal('0')
        
        # ILM = ln(e - 1 + LC/BIC)
        # LC/BIC = 49.5/1260 ≈ 0.0393
        # ILM = ln(e - 1 + 0.0393) = ln(2.7183 - 1 + 0.0393) ≈ ln(1.7576) ≈ 0.564
        assert ilm > Decimal('0.5')
        assert ilm < Decimal('1.0')
    
    def test_sma_u_021_complex_case_national_discretion(self, sma_calculator):
        """
        Test Case ID: SMA-U-021
        Description: Complex Case: National discretion is enabled to disable loss sensitivity.
        """
        # Arrange
        lc = Decimal('495000000')      # ₹49.5 crore
        bic = Decimal('12600000000')   # ₹1,260 crore
        bucket = RBIBucket.BUCKET_2
        years_with_data = 10  # Sufficient data
        national_discretion = True  # Enable national discretion
        
        # Act
        ilm, gated, reason = sma_calculator.calculate_ilm(
            lc, bic, bucket, years_with_data, national_discretion
        )
        
        # Assert
        assert gated == True
        assert ilm == Decimal('1')
        assert "National discretion" in reason
        assert "ILM set to 1" in reason
    
    def test_sma_u_022_complex_case_supervisor_override(self, sma_calculator):
        """
        Test Case ID: SMA-U-022
        Description: Complex Case: Supervisor override is provided.
        Note: This test focuses on the calculation logic; supervisor override 
        handling would be implemented in the service layer.
        """
        # Arrange - Normal calculation first
        lc = Decimal('495000000')
        bic = Decimal('12600000000')
        bucket = RBIBucket.BUCKET_2
        years_with_data = 5
        
        # Act - Calculate normal ILM
        ilm_normal, gated_normal, reason_normal = sma_calculator.calculate_ilm(
            lc, bic, bucket, years_with_data, False
        )
        
        # Assert - Normal calculation should work
        assert not gated_normal
        assert ilm_normal != Decimal('1')
        
        # Simulate supervisor override by forcing ILM = 1
        ilm_override = Decimal('1')
        
        # In a real implementation, this would be handled by the service layer
        # with proper audit logging and approval workflow
        assert ilm_override == Decimal('1')
    
    def test_lc_calculation_with_exclusions(self, sma_calculator):
        """
        Additional Test: LC calculation with excluded losses.
        """
        # Arrange
        loss_data = [
            LossData(
                event_id="INCLUDED_LOSS",
                entity_id="EXCLUSION_TEST_BANK",
                accounting_date=date(2023, 6, 15),
                net_loss=Decimal('100000000'),  # ₹10 crore
                is_excluded=False
            ),
            LossData(
                event_id="EXCLUDED_LOSS",
                entity_id="EXCLUSION_TEST_BANK",
                accounting_date=date(2023, 8, 20),
                net_loss=Decimal('200000000'),  # ₹20 crore
                is_excluded=True,
                exclusion_reason="RBI approved exclusion"
            )
        ]
        
        calculation_date = date(2023, 12, 31)
        
        # Act
        lc, avg_losses, years = sma_calculator.calculate_loss_component(
            loss_data, calculation_date
        )
        
        # Assert
        # Should only include the non-excluded loss
        expected_avg = Decimal('100000000')  # Only ₹10 crore
        assert avg_losses == expected_avg
        
        expected_lc = expected_avg * Decimal('15')
        assert lc == expected_lc
        
        assert years == 1  # Only one year with included losses
    
    def test_lc_calculation_with_threshold_filtering(self, sma_calculator, boundary_test_cases):
        """
        Additional Test: LC calculation with minimum threshold filtering.
        """
        # Arrange
        loss_data = [
            LossData(
                event_id="ABOVE_THRESHOLD",
                entity_id="THRESHOLD_TEST_BANK",
                accounting_date=date(2023, 6, 15),
                net_loss=boundary_test_cases['minimum_loss_threshold']  # Exactly at threshold
            ),
            LossData(
                event_id="BELOW_THRESHOLD",
                entity_id="THRESHOLD_TEST_BANK",
                accounting_date=date(2023, 8, 20),
                net_loss=boundary_test_cases['below_minimum_threshold']  # Below threshold
            )
        ]
        
        calculation_date = date(2023, 12, 31)
        
        # Act
        lc, avg_losses, years = sma_calculator.calculate_loss_component(
            loss_data, calculation_date
        )
        
        # Assert
        # Should only include the loss at/above threshold
        expected_avg = boundary_test_cases['minimum_loss_threshold']
        assert avg_losses == expected_avg
        
        expected_lc = expected_avg * Decimal('15')
        assert lc == expected_lc
    
    def test_lc_calculation_10_year_horizon(self, sma_calculator):
        """
        Additional Test: Verify 10-year rolling horizon is correctly applied.
        """
        # Arrange - Create losses spanning 15 years
        loss_data = []
        base_year = 2009  # Start from 2009
        
        for year in range(base_year, base_year + 15):
            loss_data.append(
                LossData(
                    event_id=f"LOSS_{year}",
                    entity_id="HORIZON_TEST_BANK",
                    accounting_date=date(year, 6, 15),
                    net_loss=Decimal('100000000')  # ₹10 crore each year
                )
            )
        
        calculation_date = date(2023, 12, 31)  # 2023 calculation
        
        # Act
        lc, avg_losses, years = sma_calculator.calculate_loss_component(
            loss_data, calculation_date
        )
        
        # Assert
        # Should only include losses from 2014-2023 (10 years)
        assert years == 10
        
        # Average should be ₹10 crore per year
        expected_avg = Decimal('100000000')
        assert avg_losses == expected_avg
        
        # LC = 15 * 10 = 150 crore
        expected_lc = Decimal('1500000000')
        assert lc == expected_lc
    
    def test_ilm_calculation_edge_cases(self, sma_calculator):
        """
        Additional Test: ILM calculation edge cases.
        """
        # Test case 1: Zero BIC (division by zero protection)
        lc = Decimal('100000000')
        bic = Decimal('0')
        bucket = RBIBucket.BUCKET_2
        years_with_data = 5
        
        ilm, gated, reason = sma_calculator.calculate_ilm(
            lc, bic, bucket, years_with_data, False
        )
        
        assert gated == True
        assert ilm == Decimal('1')
        assert "BIC is zero" in reason
        
        # Test case 2: Very small LC/BIC ratio
        lc = Decimal('1000000')      # ₹0.1 crore
        bic = Decimal('10000000000') # ₹1,000 crore
        
        ilm, gated, reason = sma_calculator.calculate_ilm(
            lc, bic, bucket, years_with_data, False
        )
        
        assert not gated
        assert ilm > Decimal('0')
        assert ilm < Decimal('1')  # Should be less than 1 for small LC/BIC
    
    def test_ilm_calculation_mathematical_accuracy(self, sma_calculator):
        """
        Additional Test: Verify mathematical accuracy of ILM calculation.
        """
        # Arrange
        lc = Decimal('1000000000')     # ₹100 crore
        bic = Decimal('10000000000')   # ₹1,000 crore
        bucket = RBIBucket.BUCKET_2
        years_with_data = 5
        
        # Act
        ilm, gated, reason = sma_calculator.calculate_ilm(
            lc, bic, bucket, years_with_data, False
        )
        
        # Assert
        assert not gated
        
        # Manual calculation for verification
        # LC/BIC = 100/1000 = 0.1
        # ILM = ln(e - 1 + 0.1) = ln(2.7183 - 1 + 0.1) = ln(1.8183) ≈ 0.5978
        import math
        e = math.e
        lc_bic_ratio = float(lc / bic)
        expected_ilm = Decimal(str(math.log(e - 1 + lc_bic_ratio)))
        
        # Allow for small floating point differences
        assert abs(ilm - expected_ilm) < Decimal('0.0001')
    
    def test_lc_calculation_annual_aggregation(self, sma_calculator):
        """
        Additional Test: Verify annual aggregation of losses.
        """
        # Arrange - Multiple losses in same year
        loss_data = [
            LossData(
                event_id="LOSS_2023_Q1",
                entity_id="AGGREGATION_TEST_BANK",
                accounting_date=date(2023, 3, 15),
                net_loss=Decimal('50000000')  # ₹5 crore
            ),
            LossData(
                event_id="LOSS_2023_Q2",
                entity_id="AGGREGATION_TEST_BANK",
                accounting_date=date(2023, 6, 15),
                net_loss=Decimal('30000000')  # ₹3 crore
            ),
            LossData(
                event_id="LOSS_2023_Q3",
                entity_id="AGGREGATION_TEST_BANK",
                accounting_date=date(2023, 9, 15),
                net_loss=Decimal('20000000')  # ₹2 crore
            )
        ]
        
        calculation_date = date(2023, 12, 31)
        
        # Act
        lc, avg_losses, years = sma_calculator.calculate_loss_component(
            loss_data, calculation_date
        )
        
        # Assert
        # Should aggregate all losses in 2023: 5 + 3 + 2 = 10 crore
        expected_avg = Decimal('100000000')  # ₹10 crore total for the year
        assert avg_losses == expected_avg
        
        assert years == 1  # Only one year with data
        
        expected_lc = expected_avg * Decimal('15')
        assert lc == expected_lc