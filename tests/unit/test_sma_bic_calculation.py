"""
Unit Tests: SMA Business Indicator Component (BIC) Calculation

Test cases SMA-U-006 through SMA-U-014 from the comprehensive test plan.
These tests cover BIC calculation with marginal coefficients across RBI buckets.
"""

import pytest
from decimal import Decimal

from src.orm_calculator.services.sma_calculator import (
    SMACalculator,
    RBIBucket,
)


@pytest.mark.unit
class TestSMABICCalculation:
    """Unit tests for Business Indicator Component (BIC) calculation"""
    
    def test_sma_u_006_happy_path_bucket_1(self, sma_calculator):
        """
        Test Case ID: SMA-U-006
        Description: Happy Path: BI falls squarely into Bucket 1.
        """
        # Arrange
        bi_amount = Decimal('70000000000')  # ₹7,000 crore (< ₹8,000 crore threshold)
        bucket = RBIBucket.BUCKET_1
        
        # Act
        bic, coefficients = sma_calculator.calculate_bic(bi_amount, bucket)
        
        # Assert
        # BIC = 7000 * 0.12 = 840 crore
        expected_bic = Decimal('8400000000')
        assert bic == expected_bic
        
        # Only bucket_1 coefficient should be applied
        assert 'bucket_1' in coefficients
        assert coefficients['bucket_1'] == bi_amount
        assert 'bucket_2' not in coefficients
        assert 'bucket_3' not in coefficients
        
        # Verify bucket assignment
        assigned_bucket = sma_calculator.assign_bucket(bi_amount)
        assert assigned_bucket == RBIBucket.BUCKET_1
    
    def test_sma_u_007_happy_path_bucket_2(self, sma_calculator):
        """
        Test Case ID: SMA-U-007
        Description: Happy Path: BI falls squarely into Bucket 2.
        """
        # Arrange
        bi_amount = Decimal('100000000000')  # ₹10,000 crore (₹8,000 < BI < ₹2,40,000)
        bucket = RBIBucket.BUCKET_2
        
        # Act
        bic, coefficients = sma_calculator.calculate_bic(bi_amount, bucket)
        
        # Assert
        # BIC = (₹8,000 * 12%) + (₹2,000 * 15%) = ₹960 + ₹300 = ₹1,260 crore
        expected_bic = Decimal('12600000000')
        assert bic == expected_bic
        
        # Both bucket_1 and bucket_2 coefficients should be applied
        assert coefficients['bucket_1'] == Decimal('80000000000')  # ₹8,000 crore
        assert coefficients['bucket_2'] == Decimal('20000000000')  # ₹2,000 crore
        assert 'bucket_3' not in coefficients
        
        # Verify bucket assignment
        assigned_bucket = sma_calculator.assign_bucket(bi_amount)
        assert assigned_bucket == RBIBucket.BUCKET_2
    
    def test_sma_u_008_happy_path_bucket_3(self, sma_calculator):
        """
        Test Case ID: SMA-U-008
        Description: Happy Path: BI falls squarely into Bucket 3.
        """
        # Arrange
        bi_amount = Decimal('3000000000000')  # ₹3,00,000 crore (> ₹2,40,000 crore)
        bucket = RBIBucket.BUCKET_3
        
        # Act
        bic, coefficients = sma_calculator.calculate_bic(bi_amount, bucket)
        
        # Assert
        # BIC = (₹8,000 * 12%) + (₹2,32,000 * 15%) + (₹60,000 * 18%)
        # = ₹960 + ₹34,800 + ₹10,800 = ₹46,560 crore
        expected_bic = Decimal('465600000000')
        assert bic == expected_bic
        
        # All three coefficients should be applied
        assert coefficients['bucket_1'] == Decimal('80000000000')    # ₹8,000 crore
        assert coefficients['bucket_2'] == Decimal('2320000000000')  # ₹2,32,000 crore
        assert coefficients['bucket_3'] == Decimal('600000000000')   # ₹60,000 crore
        
        # Verify bucket assignment
        assigned_bucket = sma_calculator.assign_bucket(bi_amount)
        assert assigned_bucket == RBIBucket.BUCKET_3
    
    def test_sma_u_009_boundary_lower_bucket_1_2_threshold(self, sma_calculator):
        """
        Test Case ID: SMA-U-009
        Description: Boundary (Lower): BI is exactly at the threshold between Bucket 1 and 2.
        """
        # Arrange
        bi_amount = Decimal('80000000000')  # Exactly ₹8,000 crore
        
        # Act
        assigned_bucket = sma_calculator.assign_bucket(bi_amount)
        bic, coefficients = sma_calculator.calculate_bic(bi_amount, assigned_bucket)
        
        # Assert
        # At exactly ₹8,000 crore, should be assigned to Bucket 2 (>= threshold)
        assert assigned_bucket == RBIBucket.BUCKET_2
        
        # BIC = (₹8,000 * 12%) + (₹0 * 15%) = ₹960 crore
        expected_bic = Decimal('9600000000')
        assert bic == expected_bic
        
        # Should have bucket_1 coefficient applied, bucket_2 with zero amount
        assert coefficients['bucket_1'] == Decimal('80000000000')
        assert coefficients.get('bucket_2', Decimal('0')) == Decimal('0')
    
    def test_sma_u_010_boundary_upper_bucket_2_3_threshold(self, sma_calculator):
        """
        Test Case ID: SMA-U-010
        Description: Boundary (Upper): BI is exactly at the threshold between Bucket 2 and 3.
        """
        # Arrange
        bi_amount = Decimal('2400000000000')  # Exactly ₹2,40,000 crore
        
        # Act
        assigned_bucket = sma_calculator.assign_bucket(bi_amount)
        bic, coefficients = sma_calculator.calculate_bic(bi_amount, assigned_bucket)
        
        # Assert
        # At exactly ₹2,40,000 crore, should be assigned to Bucket 3 (>= threshold)
        assert assigned_bucket == RBIBucket.BUCKET_3
        
        # BIC = (₹8,000 * 12%) + (₹2,32,000 * 15%) + (₹0 * 18%)
        # = ₹960 + ₹34,800 + ₹0 = ₹35,760 crore
        expected_bic = Decimal('357600000000')
        assert bic == expected_bic
        
        # Should have bucket_1 and bucket_2 coefficients, bucket_3 with zero amount
        assert coefficients['bucket_1'] == Decimal('80000000000')
        assert coefficients['bucket_2'] == Decimal('2320000000000')
        assert coefficients.get('bucket_3', Decimal('0')) == Decimal('0')
    
    def test_sma_u_011_boundary_near_lower_bucket_2(self, sma_calculator):
        """
        Test Case ID: SMA-U-011
        Description: Boundary (Near Lower): BI is just below the Bucket 2 threshold.
        """
        # Arrange
        bi_amount = Decimal('79999999999')  # ₹7,999.99 crore (just below ₹8,000)
        
        # Act
        assigned_bucket = sma_calculator.assign_bucket(bi_amount)
        bic, coefficients = sma_calculator.calculate_bic(bi_amount, assigned_bucket)
        
        # Assert
        # Should be in Bucket 1
        assert assigned_bucket == RBIBucket.BUCKET_1
        
        # BIC = ₹7,999.99 * 12% = ₹959.999 crore
        expected_bic = bi_amount * Decimal('0.12')
        assert bic == expected_bic
        
        # Only bucket_1 coefficient should be applied
        assert coefficients['bucket_1'] == bi_amount
        assert 'bucket_2' not in coefficients
        assert 'bucket_3' not in coefficients
    
    def test_sma_u_012_boundary_near_upper_bucket_2(self, sma_calculator):
        """
        Test Case ID: SMA-U-012
        Description: Boundary (Near Upper): BI is just above the Bucket 2 threshold.
        """
        # Arrange
        bi_amount = Decimal('80000000001')  # ₹8,000.01 crore (just above ₹8,000)
        
        # Act
        assigned_bucket = sma_calculator.assign_bucket(bi_amount)
        bic, coefficients = sma_calculator.calculate_bic(bi_amount, assigned_bucket)
        
        # Assert
        # Should be in Bucket 2
        assert assigned_bucket == RBIBucket.BUCKET_2
        
        # BIC = (₹8,000 * 12%) + (₹0.01 * 15%) = ₹960 + ₹0.0015 = ₹960.0015 crore
        expected_bic = (Decimal('80000000000') * Decimal('0.12') + 
                       Decimal('1') * Decimal('0.15'))
        assert bic == expected_bic
        
        # Should have both coefficients applied
        assert coefficients['bucket_1'] == Decimal('80000000000')
        assert coefficients['bucket_2'] == Decimal('1')
    
    def test_sma_u_013_edge_case_zero_bi(self, sma_calculator):
        """
        Test Case ID: SMA-U-013
        Description: Edge Case: BI is zero.
        """
        # Arrange
        bi_amount = Decimal('0')
        
        # Act
        assigned_bucket = sma_calculator.assign_bucket(bi_amount)
        bic, coefficients = sma_calculator.calculate_bic(bi_amount, assigned_bucket)
        
        # Assert
        # Zero BI should be in Bucket 1
        assert assigned_bucket == RBIBucket.BUCKET_1
        
        # BIC = 0 * 12% = 0
        assert bic == Decimal('0')
        
        # Should have bucket_1 coefficient with zero amount
        assert coefficients['bucket_1'] == Decimal('0')
        assert 'bucket_2' not in coefficients
        assert 'bucket_3' not in coefficients
    
    def test_sma_u_014_negative_case_negative_bi(self, sma_calculator):
        """
        Test Case ID: SMA-U-014
        Description: Negative Case: BI is negative.
        """
        # Arrange
        bi_amount = Decimal('-10000000000')  # Negative ₹1,000 crore
        
        # Act
        assigned_bucket = sma_calculator.assign_bucket(bi_amount)
        bic, coefficients = sma_calculator.calculate_bic(bi_amount, assigned_bucket)
        
        # Assert
        # Negative BI should be treated as Bucket 1 (< threshold)
        assert assigned_bucket == RBIBucket.BUCKET_1
        
        # BIC calculation should handle negative values
        # In practice, negative BI would be floored at 0 in business logic
        expected_bic = bi_amount * Decimal('0.12')  # Negative result
        assert bic == expected_bic
        
        # Should have bucket_1 coefficient with negative amount
        assert coefficients['bucket_1'] == bi_amount
    
    def test_bic_calculation_marginal_coefficients_verification(self, sma_calculator):
        """
        Additional Test: Verify marginal coefficients are correctly defined.
        """
        # Assert
        assert sma_calculator.MARGINAL_COEFFICIENTS['bucket_1'] == Decimal('0.12')  # 12%
        assert sma_calculator.MARGINAL_COEFFICIENTS['bucket_2'] == Decimal('0.15')  # 15%
        assert sma_calculator.MARGINAL_COEFFICIENTS['bucket_3'] == Decimal('0.18')  # 18%
    
    def test_bic_calculation_thresholds_verification(self, sma_calculator):
        """
        Additional Test: Verify RBI thresholds are correctly defined.
        """
        # Assert
        assert sma_calculator.BUCKET_1_THRESHOLD == Decimal('80000000000')    # ₹8,000 crore
        assert sma_calculator.BUCKET_2_THRESHOLD == Decimal('2400000000000')  # ₹2,40,000 crore
    
    def test_bic_calculation_large_bucket_3_amount(self, sma_calculator):
        """
        Additional Test: Test BIC calculation with very large Bucket 3 amount.
        """
        # Arrange
        bi_amount = Decimal('10000000000000')  # ₹10,00,000 crore (very large)
        bucket = RBIBucket.BUCKET_3
        
        # Act
        bic, coefficients = sma_calculator.calculate_bic(bi_amount, bucket)
        
        # Assert
        # BIC = (₹8,000 * 12%) + (₹2,32,000 * 15%) + (₹7,60,000 * 18%)
        # = ₹960 + ₹34,800 + ₹1,36,800 = ₹1,72,560 crore
        expected_bic = (Decimal('80000000000') * Decimal('0.12') +
                       Decimal('2320000000000') * Decimal('0.15') +
                       Decimal('7600000000000') * Decimal('0.18'))
        assert bic == expected_bic
        
        # Verify coefficient breakdown
        assert coefficients['bucket_1'] == Decimal('80000000000')
        assert coefficients['bucket_2'] == Decimal('2320000000000')
        assert coefficients['bucket_3'] == Decimal('7600000000000')
    
    def test_bucket_assignment_comprehensive(self, sma_calculator, boundary_test_cases):
        """
        Additional Test: Comprehensive bucket assignment testing with boundary cases.
        """
        # Test all boundary cases
        test_cases = [
            (boundary_test_cases['bucket_1_upper_boundary'], RBIBucket.BUCKET_1),
            (boundary_test_cases['bucket_1_exact_threshold'], RBIBucket.BUCKET_2),
            (boundary_test_cases['bucket_2_lower_boundary'], RBIBucket.BUCKET_2),
            (boundary_test_cases['bucket_2_upper_boundary'], RBIBucket.BUCKET_2),
            (boundary_test_cases['bucket_2_exact_threshold'], RBIBucket.BUCKET_3),
            (boundary_test_cases['bucket_3_lower_boundary'], RBIBucket.BUCKET_3),
            (boundary_test_cases['zero_bi'], RBIBucket.BUCKET_1),
            (boundary_test_cases['negative_bi'], RBIBucket.BUCKET_1),
        ]
        
        for bi_amount, expected_bucket in test_cases:
            assigned_bucket = sma_calculator.assign_bucket(bi_amount)
            assert assigned_bucket == expected_bucket, f"Failed for BI amount: {bi_amount}"
    
    def test_bic_calculation_precision_handling(self, sma_calculator):
        """
        Additional Test: Test BIC calculation with high precision requirements.
        """
        # Arrange
        bi_amount = Decimal('123456789012.34')  # High precision amount
        bucket = RBIBucket.BUCKET_2
        
        # Act
        bic, coefficients = sma_calculator.calculate_bic(bi_amount, bucket)
        
        # Assert
        # Should maintain precision in calculations
        expected_bucket_1_bic = Decimal('80000000000') * Decimal('0.12')
        expected_bucket_2_bic = (bi_amount - Decimal('80000000000')) * Decimal('0.15')
        expected_total_bic = expected_bucket_1_bic + expected_bucket_2_bic
        
        assert bic == expected_total_bic
        
        # Verify precision is maintained in coefficients
        assert coefficients['bucket_1'] == Decimal('80000000000')
        assert coefficients['bucket_2'] == bi_amount - Decimal('80000000000')
    
    def test_bic_calculation_edge_case_exact_bucket_2_threshold(self, sma_calculator):
        """
        Additional Test: Test exact Bucket 2 threshold calculation edge case.
        """
        # Arrange
        bi_amount = sma_calculator.BUCKET_2_THRESHOLD  # Exactly ₹2,40,000 crore
        
        # Act
        assigned_bucket = sma_calculator.assign_bucket(bi_amount)
        bic, coefficients = sma_calculator.calculate_bic(bi_amount, assigned_bucket)
        
        # Assert
        assert assigned_bucket == RBIBucket.BUCKET_3
        
        # At exact threshold, bucket_3 amount should be 0
        assert coefficients['bucket_1'] == Decimal('80000000000')
        assert coefficients['bucket_2'] == Decimal('2320000000000')
        assert coefficients.get('bucket_3', Decimal('0')) == Decimal('0')
        
        # BIC should be sum of bucket_1 and bucket_2 only
        expected_bic = (Decimal('80000000000') * Decimal('0.12') +
                       Decimal('2320000000000') * Decimal('0.15'))
        assert bic == expected_bic