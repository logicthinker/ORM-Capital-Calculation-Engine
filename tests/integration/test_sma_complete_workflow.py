"""
Integration Tests: Complete SMA Calculation Workflow

These tests cover end-to-end SMA calculation scenarios integrating all components:
Business Indicator, BIC, Loss Component, ILM, and final capital calculations.
"""

import pytest
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime

from src.orm_calculator.services.sma_calculator import (
    SMACalculator,
    BusinessIndicatorData,
    LossData,
    RBIBucket,
    SMACalculationResult,
)


@pytest.mark.integration
class TestSMACompleteWorkflow:
    """Integration tests for complete SMA calculation workflow"""
    
    def test_complete_sma_bucket_1_calculation(self, sma_calculator, sample_bi_data_bucket_1):
        """
        Integration Test: Complete SMA calculation for Bucket 1 entity.
        Verifies ILM gating for Bucket 1 banks.
        """
        # Arrange
        loss_data = [
            LossData(
                event_id="BUCKET1_LOSS_001",
                entity_id="BUCKET1_BANK",
                accounting_date=date(2023, 6, 15),
                net_loss=Decimal('50000000')  # ₹5 crore
            ),
            LossData(
                event_id="BUCKET1_LOSS_002",
                entity_id="BUCKET1_BANK",
                accounting_date=date(2022, 8, 20),
                net_loss=Decimal('30000000')  # ₹3 crore
            ),
            LossData(
                event_id="BUCKET1_LOSS_003",
                entity_id="BUCKET1_BANK",
                accounting_date=date(2021, 3, 10),
                net_loss=Decimal('20000000')  # ₹2 crore
            ),
            LossData(
                event_id="BUCKET1_LOSS_004",
                entity_id="BUCKET1_BANK",
                accounting_date=date(2020, 11, 5),
                net_loss=Decimal('40000000')  # ₹4 crore
            ),
            LossData(
                event_id="BUCKET1_LOSS_005",
                entity_id="BUCKET1_BANK",
                accounting_date=date(2019, 7, 12),
                net_loss=Decimal('25000000')  # ₹2.5 crore
            )
        ]
        
        # Act
        result = sma_calculator.calculate_sma(
            bi_data=sample_bi_data_bucket_1,
            loss_data=loss_data,
            entity_id="BUCKET1_BANK",
            calculation_date=date(2023, 12, 31),
            run_id="BUCKET1_INTEGRATION_TEST"
        )
        
        # Assert
        assert result.run_id == "BUCKET1_INTEGRATION_TEST"
        assert result.entity_id == "BUCKET1_BANK"
        assert result.calculation_date == date(2023, 12, 31)
        
        # Business Indicator calculations
        # Current BI (2023) = 4000 + 2000 + 1000 = 7000 crore
        assert result.bi_current == Decimal('70000000000')
        
        # Three-year average = (7000 + 7200 + 6200) / 3 = 6800 crore
        expected_bi_avg = Decimal('68000000000')
        assert result.bi_three_year_average == expected_bi_avg
        
        # Bucket assignment - should be Bucket 1 (< ₹8,000 crore)
        assert result.bucket == RBIBucket.BUCKET_1
        
        # BIC calculation - 6800 * 12% = 816 crore
        expected_bic = Decimal('8160000000')
        assert result.bic == expected_bic
        
        # Marginal coefficients - only bucket_1 should be applied
        assert 'bucket_1' in result.marginal_coefficients_applied
        assert result.marginal_coefficients_applied['bucket_1'] == expected_bi_avg
        
        # Loss Component calculation
        assert result.loss_data_years == 5
        # Average annual losses = (5 + 3 + 2 + 4 + 2.5) / 5 = 3.3 crore
        expected_avg_losses = Decimal('33000000')
        assert result.average_annual_losses == expected_avg_losses
        # LC = 15 * 3.3 = 49.5 crore
        expected_lc = Decimal('495000000')
        assert result.lc == expected_lc
        
        # ILM calculation - should be gated for Bucket 1
        assert result.ilm == Decimal('1')
        assert result.ilm_gated == True
        assert "Bucket 1" in result.ilm_gate_reason
        
        # Final capital calculations
        # ORC = BIC * ILM = 816 * 1 = 816 crore
        assert result.orc == expected_bic
        
        # RWA = ORC * 12.5 = 816 * 12.5 = 10,200 crore
        expected_rwa = expected_bic * Decimal('12.5')
        assert result.rwa == expected_rwa
        
        # Metadata
        assert result.model_version == "1.0.0-test"
        assert result.parameters_version == "1.0.0-test"
        assert isinstance(result.calculation_timestamp, datetime)
    
    def test_complete_sma_bucket_2_calculation(self, sma_calculator, sample_bi_data_bucket_2):
        """
        Integration Test: Complete SMA calculation for Bucket 2 entity.
        Verifies ILM calculation without gating.
        """
        # Arrange - Create substantial loss data for 5+ years
        loss_data = []
        for year in range(2019, 2024):  # 5 years of data
            for quarter in [3, 6, 9, 12]:
                loss_data.append(
                    LossData(
                        event_id=f"BUCKET2_LOSS_{year}_Q{quarter//3}",
                        entity_id="BUCKET2_BANK",
                        accounting_date=date(year, quarter, 15),
                        net_loss=Decimal('100000000')  # ₹10 crore each
                    )
                )
        
        # Act
        result = sma_calculator.calculate_sma(
            bi_data=sample_bi_data_bucket_2,
            loss_data=loss_data,
            entity_id="BUCKET2_BANK",
            calculation_date=date(2023, 12, 31),
            run_id="BUCKET2_INTEGRATION_TEST"
        )
        
        # Assert
        assert result.run_id == "BUCKET2_INTEGRATION_TEST"
        assert result.entity_id == "BUCKET2_BANK"
        
        # Business Indicator calculations
        # Current BI (2023) = 8000 + 3000 + 2000 = 13000 crore
        assert result.bi_current == Decimal('130000000000')
        
        # Three-year average = (13000 + 12500 + 12000) / 3 = 12500 crore
        expected_bi_avg = Decimal('125000000000')
        assert result.bi_three_year_average == expected_bi_avg
        
        # Bucket assignment - should be Bucket 2
        assert result.bucket == RBIBucket.BUCKET_2
        
        # BIC calculation for Bucket 2
        # BIC = (8000 * 12%) + (4500 * 15%) = 960 + 675 = 1635 crore
        expected_bic = Decimal('16350000000')
        assert result.bic == expected_bic
        
        # Marginal coefficients
        assert result.marginal_coefficients_applied['bucket_1'] == Decimal('80000000000')
        assert result.marginal_coefficients_applied['bucket_2'] == Decimal('45000000000')
        
        # Loss Component calculation
        assert result.loss_data_years == 5
        # Average annual losses = (20 * 10) / 5 = 40 crore per year (4 losses per year * 10 crore each = 40 crore per year)
        expected_avg_losses = Decimal('400000000')
        assert result.average_annual_losses == expected_avg_losses
        # LC = 15 * 40 = 600 crore
        expected_lc = Decimal('6000000000')
        assert result.lc == expected_lc
        
        # ILM calculation - should NOT be gated (Bucket 2 with sufficient data)
        assert result.ilm_gated == False
        assert result.ilm_gate_reason is None
        assert result.ilm > Decimal('0')
        
        # ILM should be calculated: ln(e - 1 + LC/BIC)
        # LC/BIC = 600/1635 ≈ 0.367
        # ILM = ln(e - 1 + 0.367) = ln(2.085) ≈ 0.735
        assert result.ilm > Decimal('0.7')
        assert result.ilm < Decimal('0.8')
        
        # Final capital calculations
        # ORC = BIC * ILM
        expected_orc = (result.bic * result.ilm).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        assert result.orc == expected_orc
        
        # RWA = ORC * 12.5
        expected_rwa = (result.orc * Decimal('12.5')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        # Allow for small rounding differences
        assert abs(result.rwa - expected_rwa) < Decimal('0.10')
    
    def test_complete_sma_bucket_3_calculation(self, sma_calculator, sample_bi_data_bucket_3):
        """
        Integration Test: Complete SMA calculation for Bucket 3 entity.
        Verifies all marginal coefficients are applied.
        """
        # Arrange - Create large loss data for major bank
        loss_data = []
        for year in range(2014, 2024):  # 10 years of data
            # Generate 2-3 large losses per year
            num_losses = 2 if year % 2 == 0 else 3
            for i in range(num_losses):
                loss_amount = Decimal('500000000') if i == 0 else Decimal('200000000')  # Mix of large and medium losses
                loss_data.append(
                    LossData(
                        event_id=f"BUCKET3_LOSS_{year}_{i+1:02d}",
                        entity_id="BUCKET3_BANK",
                        accounting_date=date(year, (i+1)*3, 15),
                        net_loss=loss_amount
                    )
                )
        
        # Act
        result = sma_calculator.calculate_sma(
            bi_data=sample_bi_data_bucket_3,
            loss_data=loss_data,
            entity_id="BUCKET3_BANK",
            calculation_date=date(2023, 12, 31),
            run_id="BUCKET3_INTEGRATION_TEST"
        )
        
        # Assert
        assert result.run_id == "BUCKET3_INTEGRATION_TEST"
        assert result.entity_id == "BUCKET3_BANK"
        
        # Business Indicator calculations
        # Current BI (2023) = 250000 + 15000 + 10000 = 275000 crore
        assert result.bi_current == Decimal('2750000000000')
        
        # Three-year average calculation
        # 2023: 275000, 2022: 263500, 2021: 252000
        # Average = (275000 + 263500 + 252000) / 3 = 263500 crore
        expected_bi_avg = Decimal('2635000000000')
        assert result.bi_three_year_average == expected_bi_avg
        
        # Bucket assignment - should be Bucket 3
        assert result.bucket == RBIBucket.BUCKET_3
        
        # BIC calculation for Bucket 3
        # BIC = (8000 * 12%) + (232000 * 15%) + (23500 * 18%)
        # = 960 + 34800 + 4230 = 39990 crore
        expected_bic = Decimal('399900000000')
        assert result.bic == expected_bic
        
        # Marginal coefficients - all three should be applied
        assert result.marginal_coefficients_applied['bucket_1'] == Decimal('80000000000')
        assert result.marginal_coefficients_applied['bucket_2'] == Decimal('2320000000000')
        assert result.marginal_coefficients_applied['bucket_3'] == Decimal('235000000000')
        
        # Loss Component calculation
        assert result.loss_data_years == 10
        assert result.average_annual_losses > Decimal('0')
        assert result.lc > Decimal('0')
        
        # ILM calculation - should NOT be gated (Bucket 3 with sufficient data)
        assert result.ilm_gated == False
        assert result.ilm > Decimal('0')
        
        # Final capital calculations should be substantial for large bank
        assert result.orc > Decimal('100000000000')  # > ₹10,000 crore
        assert result.rwa > Decimal('1000000000000')  # > ₹1,00,000 crore
    
    def test_complete_sma_insufficient_loss_data(self, sma_calculator, sample_bi_data_bucket_2, sample_loss_data_insufficient):
        """
        Integration Test: SMA calculation with insufficient loss data (< 5 years).
        Verifies ILM gating due to data quality.
        """
        # Act
        result = sma_calculator.calculate_sma(
            bi_data=sample_bi_data_bucket_2,
            loss_data=sample_loss_data_insufficient,
            entity_id="INSUFFICIENT_DATA_BANK",
            calculation_date=date(2023, 12, 31),
            run_id="INSUFFICIENT_DATA_TEST"
        )
        
        # Assert
        assert result.bucket == RBIBucket.BUCKET_2  # Should still be Bucket 2
        
        # Loss data should be insufficient
        assert result.loss_data_years < 5
        
        # ILM should be gated due to insufficient data
        assert result.ilm_gated == True
        assert result.ilm == Decimal('1')
        assert "years < 5 years" in result.ilm_gate_reason
        
        # ORC should equal BIC (ILM = 1)
        assert result.orc == result.bic
    
    def test_complete_sma_national_discretion(self, sma_calculator, sample_bi_data_bucket_2):
        """
        Integration Test: SMA calculation with national discretion enabled.
        """
        # Arrange
        loss_data = [
            LossData(
                event_id="DISCRETION_LOSS_001",
                entity_id="DISCRETION_BANK",
                accounting_date=date(year, 6, 15),
                net_loss=Decimal('100000000')
            )
            for year in range(2019, 2024)  # 5 years of data
        ]
        
        # Act
        result = sma_calculator.calculate_sma(
            bi_data=sample_bi_data_bucket_2,
            loss_data=loss_data,
            entity_id="DISCRETION_BANK",
            calculation_date=date(2023, 12, 31),
            run_id="DISCRETION_TEST",
            national_discretion_ilm_one=True  # Enable national discretion
        )
        
        # Assert
        assert result.bucket == RBIBucket.BUCKET_2
        assert result.loss_data_years == 5  # Sufficient data
        
        # ILM should be gated due to national discretion
        assert result.ilm_gated == True
        assert result.ilm == Decimal('1')
        assert "National discretion" in result.ilm_gate_reason
        
        # ORC should equal BIC
        assert result.orc == result.bic
    
    def test_complete_sma_boundary_conditions(self, sma_calculator, boundary_test_cases):
        """
        Integration Test: SMA calculation with boundary condition BI amounts.
        """
        # Test exact Bucket 1/2 threshold
        bi_data_threshold = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('60000000000'),   # ₹6,000 crore
                sc=Decimal('15000000000'),     # ₹1,500 crore
                fc=Decimal('5000000000'),      # ₹500 crore
                entity_id="THRESHOLD_BANK",
                calculation_date=date(2023, 12, 31)
            )
        ]
        # Total BI = 8000 crore (exactly at threshold)
        
        loss_data = [
            LossData(
                event_id="THRESHOLD_LOSS",
                entity_id="THRESHOLD_BANK",
                accounting_date=date(2023, 6, 15),
                net_loss=Decimal('50000000')
            )
        ]
        
        # Act
        result = sma_calculator.calculate_sma(
            bi_data=bi_data_threshold,
            loss_data=loss_data,
            entity_id="THRESHOLD_BANK",
            calculation_date=date(2023, 12, 31),
            run_id="THRESHOLD_TEST"
        )
        
        # Assert
        assert result.bi_three_year_average == Decimal('80000000000')  # Exactly ₹8,000 crore
        assert result.bucket == RBIBucket.BUCKET_2  # Should be Bucket 2 (>= threshold)
        
        # BIC should be calculated with Bucket 2 logic
        expected_bic = Decimal('80000000000') * Decimal('0.12')  # Only bucket_1 coefficient
        assert result.bic == expected_bic
    
    def test_complete_sma_zero_losses(self, sma_calculator, sample_bi_data_bucket_2):
        """
        Integration Test: SMA calculation with zero losses.
        """
        # Arrange - No loss data
        loss_data = []
        
        # Act
        result = sma_calculator.calculate_sma(
            bi_data=sample_bi_data_bucket_2,
            loss_data=loss_data,
            entity_id="ZERO_LOSS_BANK",
            calculation_date=date(2023, 12, 31),
            run_id="ZERO_LOSS_TEST"
        )
        
        # Assert
        assert result.bucket == RBIBucket.BUCKET_2
        
        # Loss component should be zero
        assert result.lc == Decimal('0')
        assert result.average_annual_losses == Decimal('0')
        assert result.loss_data_years == 0
        
        # ILM should be gated due to insufficient data
        assert result.ilm_gated == True
        assert result.ilm == Decimal('1')
        
        # ORC should equal BIC
        assert result.orc == result.bic
    
    def test_complete_sma_precision_and_rounding(self, sma_calculator):
        """
        Integration Test: Verify precision handling and rounding in complete calculation.
        """
        # Arrange - Use fractional values
        bi_data = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('33333333333.33'),
                sc=Decimal('16666666666.67'),
                fc=Decimal('10000000000.00'),
                entity_id="PRECISION_BANK",
                calculation_date=date(2023, 12, 31)
            )
        ]
        
        loss_data = [
            LossData(
                event_id="PRECISION_LOSS",
                entity_id="PRECISION_BANK",
                accounting_date=date(year, 6, 15),
                net_loss=Decimal('33333333.33')  # Fractional loss amount
            )
            for year in range(2019, 2024)
        ]
        
        # Act
        result = sma_calculator.calculate_sma(
            bi_data=bi_data,
            loss_data=loss_data,
            entity_id="PRECISION_BANK",
            calculation_date=date(2023, 12, 31),
            run_id="PRECISION_TEST"
        )
        
        # Assert
        # Final results should be properly rounded to 2 decimal places
        assert result.orc.as_tuple().exponent >= -2
        assert result.rwa.as_tuple().exponent >= -2
        
        # Calculations should maintain precision throughout
        assert result.bi_current == Decimal('60000000000.00')
        assert result.orc > Decimal('0')
        assert result.rwa > Decimal('0')
    
    def test_complete_sma_validation_errors(self, sma_calculator):
        """
        Integration Test: Verify validation errors are properly handled.
        """
        # Test with invalid BI data
        invalid_bi_data = [
            BusinessIndicatorData(
                period="",  # Invalid empty period
                ildc=Decimal('-10000000000'),
                sc=Decimal('-5000000000'),
                fc=Decimal('-15000000000'),
                entity_id="",  # Invalid empty entity ID
                calculation_date=date(2023, 12, 31)
            )
        ]
        
        invalid_loss_data = [
            LossData(
                event_id="",  # Invalid empty event ID
                entity_id="",
                accounting_date=date(2023, 6, 15),
                net_loss=Decimal('-1000000')  # Invalid negative loss
            )
        ]
        
        # Act
        errors = sma_calculator.validate_inputs(invalid_bi_data, invalid_loss_data)
        
        # Assert
        assert len(errors) > 0
        assert any("Entity ID is required" in error for error in errors)
        assert any("Period is required" in error for error in errors)
        assert any("Net loss cannot be negative" in error for error in errors)