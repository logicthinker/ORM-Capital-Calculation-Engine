"""
Regulatory Compliance Tests: RBI Basel III SMA Requirements

These tests verify compliance with RBI Basel III SMA methodology and regulatory requirements.
Tests cover regulatory formulas, thresholds, data requirements, and compliance scenarios.
"""

import pytest
from decimal import Decimal
from datetime import date

from src.orm_calculator.services.sma_calculator import (
    SMACalculator,
    BusinessIndicatorData,
    LossData,
    RBIBucket,
)


@pytest.mark.regulatory
class TestRBICompliance:
    """Regulatory compliance tests for RBI Basel III SMA requirements"""
    
    def test_rbi_sma_formula_compliance(self, sma_calculator, regulatory_test_parameters):
        """
        Test: Verify SMA formula compliance with RBI Basel III requirements.
        Regulation: RBI Master Direction on Basel III Capital Regulation
        """
        # Arrange - Test data that covers all formula components
        bi_data = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('100000000000'),  # ₹10,000 crore
                sc=Decimal('50000000000'),     # ₹5,000 crore
                fc=Decimal('25000000000'),     # ₹2,500 crore
                entity_id="RBI_COMPLIANCE_BANK",
                calculation_date=date(2023, 12, 31)
            ),
            BusinessIndicatorData(
                period="2022",
                ildc=Decimal('95000000000'),   # ₹9,500 crore
                sc=Decimal('48000000000'),     # ₹4,800 crore
                fc=Decimal('22000000000'),     # ₹2,200 crore
                entity_id="RBI_COMPLIANCE_BANK",
                calculation_date=date(2022, 12, 31)
            ),
            BusinessIndicatorData(
                period="2021",
                ildc=Decimal('90000000000'),   # ₹9,000 crore
                sc=Decimal('45000000000'),     # ₹4,500 crore
                fc=Decimal('20000000000'),     # ₹2,000 crore
                entity_id="RBI_COMPLIANCE_BANK",
                calculation_date=date(2021, 12, 31)
            )
        ]
        
        loss_data = []
        for year in range(2019, 2024):  # 5 years of loss data
            loss_data.append(
                LossData(
                    event_id=f"RBI_LOSS_{year}",
                    entity_id="RBI_COMPLIANCE_BANK",
                    accounting_date=date(year, 6, 15),
                    net_loss=Decimal('200000000')  # ₹20 crore per year
                )
            )
        
        # Act
        result = sma_calculator.calculate_sma(
            bi_data=bi_data,
            loss_data=loss_data,
            entity_id="RBI_COMPLIANCE_BANK",
            calculation_date=date(2023, 12, 31),
            run_id="RBI_COMPLIANCE_TEST"
        )
        
        # Assert - Verify RBI formula compliance
        
        # 1. Business Indicator = ILDC + SC + FC (3-year average)
        # 2023: 10000 + 5000 + 2500 = 17500
        # 2022: 9500 + 4800 + 2200 = 16500  
        # 2021: 9000 + 4500 + 2000 = 15500
        # Average: (17500 + 16500 + 15500) / 3 = 16500 crore
        expected_bi_avg = Decimal('165000000000')
        assert result.bi_three_year_average == expected_bi_avg
        
        # 2. Bucket assignment per RBI thresholds
        assert result.bucket == RBIBucket.BUCKET_2  # ₹8,000 < ₹16,500 < ₹2,40,000
        
        # 3. BIC calculation with marginal coefficients
        # BIC = (₹8,000 * 12%) + (₹8,500 * 15%) = ₹960 + ₹1,275 = ₹2,235 crore
        expected_bic = (regulatory_test_parameters['rbi_thresholds']['bucket_1'] * 
                       regulatory_test_parameters['marginal_coefficients']['bucket_1'] +
                       (expected_bi_avg - regulatory_test_parameters['rbi_thresholds']['bucket_1']) *
                       regulatory_test_parameters['marginal_coefficients']['bucket_2'])
        assert result.bic == expected_bic
        
        # 4. Loss Component = 15 × average annual losses
        # Average annual losses = (20 * 5) / 5 = 20 crore per year
        # LC = 15 * 20 = 300 crore
        expected_lc = Decimal('3000000000')
        assert result.lc == expected_lc
        
        # 5. ILM = ln(e - 1 + LC/BIC) (not gated for Bucket 2 with sufficient data)
        assert not result.ilm_gated
        assert result.ilm > Decimal('0')
        
        # 6. ORC = BIC × ILM
        expected_orc = result.bic * result.ilm
        # Allow for rounding differences
        assert abs(result.orc - expected_orc.quantize(Decimal('0.01'))) < Decimal('0.01')
        
        # 7. RWA = ORC × 12.5
        expected_rwa = result.orc * regulatory_test_parameters['rwa_multiplier']
        # Allow for small rounding differences
        assert abs(result.rwa - expected_rwa) < Decimal('0.10')
    
    def test_rbi_bucket_thresholds_compliance(self, sma_calculator, regulatory_test_parameters):
        """
        Test: Verify RBI bucket thresholds are correctly implemented.
        Regulation: RBI Basel III SMA - Bucket classification thresholds
        """
        # Test cases for each bucket threshold
        test_cases = [
            # Bucket 1 cases
            (Decimal('70000000000'), RBIBucket.BUCKET_1),    # ₹7,000 crore
            (Decimal('79999999999'), RBIBucket.BUCKET_1),    # Just below threshold
            
            # Bucket 2 cases  
            (Decimal('80000000000'), RBIBucket.BUCKET_2),    # Exactly at threshold
            (Decimal('80000000001'), RBIBucket.BUCKET_2),    # Just above threshold
            (Decimal('1000000000000'), RBIBucket.BUCKET_2),  # ₹1,00,000 crore
            (Decimal('2399999999999'), RBIBucket.BUCKET_2),  # Just below upper threshold
            
            # Bucket 3 cases
            (Decimal('2400000000000'), RBIBucket.BUCKET_3),  # Exactly at threshold
            (Decimal('2400000000001'), RBIBucket.BUCKET_3),  # Just above threshold
            (Decimal('5000000000000'), RBIBucket.BUCKET_3),  # ₹5,00,000 crore
        ]
        
        for bi_amount, expected_bucket in test_cases:
            # Act
            assigned_bucket = sma_calculator.assign_bucket(bi_amount)
            
            # Assert
            assert assigned_bucket == expected_bucket, f"BI amount ₹{bi_amount/10000000:.0f} crore should be {expected_bucket.value}"
        
        # Verify threshold constants match RBI requirements
        assert sma_calculator.BUCKET_1_THRESHOLD == regulatory_test_parameters['rbi_thresholds']['bucket_1']
        assert sma_calculator.BUCKET_2_THRESHOLD == regulatory_test_parameters['rbi_thresholds']['bucket_2']
    
    def test_rbi_marginal_coefficients_compliance(self, sma_calculator, regulatory_test_parameters):
        """
        Test: Verify marginal coefficients match RBI Basel III requirements.
        Regulation: RBI Basel III SMA - Marginal coefficient rates
        """
        # Verify coefficient constants
        assert sma_calculator.MARGINAL_COEFFICIENTS['bucket_1'] == regulatory_test_parameters['marginal_coefficients']['bucket_1']
        assert sma_calculator.MARGINAL_COEFFICIENTS['bucket_2'] == regulatory_test_parameters['marginal_coefficients']['bucket_2']
        assert sma_calculator.MARGINAL_COEFFICIENTS['bucket_3'] == regulatory_test_parameters['marginal_coefficients']['bucket_3']
        
        # Test marginal coefficient application for each bucket
        
        # Bucket 1: 12% on entire amount
        bi_bucket_1 = Decimal('70000000000')  # ₹7,000 crore
        bic_1, coeffs_1 = sma_calculator.calculate_bic(bi_bucket_1, RBIBucket.BUCKET_1)
        expected_bic_1 = bi_bucket_1 * Decimal('0.12')
        assert bic_1 == expected_bic_1
        assert coeffs_1['bucket_1'] == bi_bucket_1
        
        # Bucket 2: 12% on first ₹8,000 crore + 15% on excess
        bi_bucket_2 = Decimal('150000000000')  # ₹15,000 crore
        bic_2, coeffs_2 = sma_calculator.calculate_bic(bi_bucket_2, RBIBucket.BUCKET_2)
        expected_bic_2 = (Decimal('80000000000') * Decimal('0.12') + 
                         Decimal('70000000000') * Decimal('0.15'))
        assert bic_2 == expected_bic_2
        assert coeffs_2['bucket_1'] == Decimal('80000000000')
        assert coeffs_2['bucket_2'] == Decimal('70000000000')
        
        # Bucket 3: 12% + 15% + 18% on respective tranches
        bi_bucket_3 = Decimal('3000000000000')  # ₹3,00,000 crore
        bic_3, coeffs_3 = sma_calculator.calculate_bic(bi_bucket_3, RBIBucket.BUCKET_3)
        expected_bic_3 = (Decimal('80000000000') * Decimal('0.12') +     # First ₹8,000 crore
                         Decimal('2320000000000') * Decimal('0.15') +    # Next ₹2,32,000 crore
                         Decimal('600000000000') * Decimal('0.18'))      # Remaining ₹60,000 crore
        assert bic_3 == expected_bic_3
        assert coeffs_3['bucket_1'] == Decimal('80000000000')
        assert coeffs_3['bucket_2'] == Decimal('2320000000000')
        assert coeffs_3['bucket_3'] == Decimal('600000000000')
    
    def test_rbi_loss_component_requirements(self, sma_calculator, regulatory_test_parameters):
        """
        Test: Verify Loss Component calculation meets RBI requirements.
        Regulation: RBI Basel III SMA - Loss Component methodology
        """
        # Test minimum loss threshold compliance
        loss_data_mixed = [
            # Above threshold - should be included
            LossData(
                event_id="ABOVE_THRESHOLD_1",
                entity_id="THRESHOLD_TEST_BANK",
                accounting_date=date(2023, 6, 15),
                net_loss=regulatory_test_parameters['minimum_loss_threshold']  # Exactly ₹1,00,000
            ),
            LossData(
                event_id="ABOVE_THRESHOLD_2", 
                entity_id="THRESHOLD_TEST_BANK",
                accounting_date=date(2023, 8, 20),
                net_loss=Decimal('50000000')  # ₹5 crore (well above threshold)
            ),
            # Below threshold - should be excluded
            LossData(
                event_id="BELOW_THRESHOLD",
                entity_id="THRESHOLD_TEST_BANK", 
                accounting_date=date(2023, 10, 10),
                net_loss=Decimal('9999999')  # Just below ₹1,00,000
            )
        ]
        
        calculation_date = date(2023, 12, 31)
        
        # Act
        lc, avg_losses, years = sma_calculator.calculate_loss_component(
            loss_data_mixed, calculation_date
        )
        
        # Assert
        # Only losses above threshold should be included
        expected_total_losses = regulatory_test_parameters['minimum_loss_threshold'] + Decimal('50000000')
        assert avg_losses == expected_total_losses
        
        # LC should be 15 times average annual losses
        expected_lc = avg_losses * regulatory_test_parameters['loss_component_multiplier']
        assert lc == expected_lc
        
        # Test 10-year rolling horizon
        loss_data_horizon = []
        for year in range(2010, 2025):  # 15 years of data
            loss_data_horizon.append(
                LossData(
                    event_id=f"HORIZON_LOSS_{year}",
                    entity_id="HORIZON_TEST_BANK",
                    accounting_date=date(year, 6, 15),
                    net_loss=Decimal('100000000')  # ₹10 crore each year
                )
            )
        
        lc_horizon, avg_horizon, years_horizon = sma_calculator.calculate_loss_component(
            loss_data_horizon, date(2023, 12, 31)
        )
        
        # Should only include 2014-2023 (10 years)
        assert years_horizon == 10
        assert avg_horizon == Decimal('100000000')  # ₹10 crore per year
        assert lc_horizon == Decimal('1500000000')  # 15 * 10 = ₹150 crore
    
    def test_rbi_ilm_gating_requirements(self, sma_calculator, regulatory_test_parameters):
        """
        Test: Verify ILM gating logic meets RBI requirements.
        Regulation: RBI Basel III SMA - ILM gating conditions
        """
        # Test Case 1: Bucket 1 gating
        lc = Decimal('100000000')
        bic = Decimal('8400000000')  # Bucket 1 BIC
        
        ilm_bucket_1, gated_1, reason_1 = sma_calculator.calculate_ilm(
            lc, bic, RBIBucket.BUCKET_1, 10, False
        )
        
        assert gated_1 == True
        assert ilm_bucket_1 == Decimal('1')
        assert "Bucket 1" in reason_1
        
        # Test Case 2: Insufficient data gating (< 5 years)
        ilm_insufficient, gated_insufficient, reason_insufficient = sma_calculator.calculate_ilm(
            lc, Decimal('12600000000'), RBIBucket.BUCKET_2, 4, False  # Only 4 years
        )
        
        assert gated_insufficient == True
        assert ilm_insufficient == Decimal('1')
        assert "4 years < 5 years" in reason_insufficient
        
        # Test Case 3: Sufficient data, no gating
        ilm_normal, gated_normal, reason_normal = sma_calculator.calculate_ilm(
            lc, Decimal('12600000000'), RBIBucket.BUCKET_2, 5, False  # Exactly 5 years
        )
        
        assert gated_normal == False
        assert reason_normal is None
        assert ilm_normal > Decimal('0')
        
        # Test Case 4: National discretion gating
        ilm_discretion, gated_discretion, reason_discretion = sma_calculator.calculate_ilm(
            lc, Decimal('12600000000'), RBIBucket.BUCKET_2, 10, True  # National discretion enabled
        )
        
        assert gated_discretion == True
        assert ilm_discretion == Decimal('1')
        assert "National discretion" in reason_discretion
    
    def test_rbi_rwa_multiplier_compliance(self, sma_calculator, regulatory_test_parameters):
        """
        Test: Verify RWA multiplier meets RBI Basel III requirements.
        Regulation: RBI Basel III - Risk Weight for Operational Risk
        """
        # Verify RWA multiplier constant
        assert sma_calculator.RWA_MULTIPLIER == regulatory_test_parameters['rwa_multiplier']
        
        # Test RWA calculation
        orc_test_values = [
            Decimal('1000000000'),    # ₹100 crore
            Decimal('10000000000'),   # ₹1,000 crore
            Decimal('100000000000'),  # ₹10,000 crore
        ]
        
        for orc in orc_test_values:
            expected_rwa = orc * regulatory_test_parameters['rwa_multiplier']
            calculated_rwa = orc * sma_calculator.RWA_MULTIPLIER
            assert calculated_rwa == expected_rwa
    
    def test_rbi_data_quality_requirements(self, sma_calculator):
        """
        Test: Verify data quality requirements per RBI guidelines.
        Regulation: RBI Basel III SMA - Data quality and completeness requirements
        """
        # Test minimum data requirements
        insufficient_bi_data = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('50000000000'),
                sc=Decimal('20000000000'),
                fc=Decimal('10000000000'),
                entity_id="DATA_QUALITY_BANK",
                calculation_date=date(2023, 12, 31)
            )
            # Missing 2022 and 2021 data
        ]
        
        # Should still calculate with available data but flag data quality
        current_bi, three_year_avg = sma_calculator.calculate_business_indicator(insufficient_bi_data)
        assert current_bi == Decimal('80000000000')
        assert three_year_avg == Decimal('80000000000')  # Same as current when only 1 year
        
        # Test data validation
        invalid_bi_data = [
            BusinessIndicatorData(
                period="",  # Invalid empty period
                ildc=Decimal('50000000000'),
                sc=Decimal('20000000000'),
                fc=Decimal('10000000000'),
                entity_id="",  # Invalid empty entity ID
                calculation_date=date(2023, 12, 31)
            )
        ]
        
        errors = sma_calculator.validate_inputs(invalid_bi_data, [])
        assert len(errors) > 0
        assert any("Period is required" in error for error in errors)
        assert any("Entity ID is required" in error for error in errors)
    
    def test_rbi_exclusion_requirements(self, sma_calculator):
        """
        Test: Verify loss exclusion handling per RBI requirements.
        Regulation: RBI Basel III SMA - Loss exclusion criteria and approval process
        """
        # Test with RBI-approved exclusions
        loss_data_with_exclusions = [
            # Normal loss - should be included
            LossData(
                event_id="NORMAL_LOSS",
                entity_id="EXCLUSION_TEST_BANK",
                accounting_date=date(2023, 6, 15),
                net_loss=Decimal('100000000'),  # ₹10 crore
                is_excluded=False
            ),
            # RBI-approved exclusion - should be excluded
            LossData(
                event_id="EXCLUDED_LOSS",
                entity_id="EXCLUSION_TEST_BANK",
                accounting_date=date(2023, 8, 20),
                net_loss=Decimal('500000000'),  # ₹50 crore
                is_excluded=True,
                exclusion_reason="RBI approved exclusion - operational disruption due to natural disaster"
            )
        ]
        
        calculation_date = date(2023, 12, 31)
        
        # Act
        lc, avg_losses, years = sma_calculator.calculate_loss_component(
            loss_data_with_exclusions, calculation_date
        )
        
        # Assert
        # Should only include the non-excluded loss
        assert avg_losses == Decimal('100000000')  # Only ₹10 crore
        assert lc == Decimal('1500000000')  # 15 * 10 = ₹150 crore
    
    def test_rbi_calculation_precision_requirements(self, sma_calculator):
        """
        Test: Verify calculation precision meets regulatory requirements.
        Regulation: RBI reporting requirements for precision and rounding
        """
        # Test with high precision inputs
        bi_data_precision = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('123456789012.34'),  # High precision
                sc=Decimal('987654321098.76'),
                fc=Decimal('456789012345.67'),
                entity_id="PRECISION_TEST_BANK",
                calculation_date=date(2023, 12, 31)
            )
        ]
        
        loss_data_precision = [
            LossData(
                event_id="PRECISION_LOSS",
                entity_id="PRECISION_TEST_BANK",
                accounting_date=date(2023, 6, 15),
                net_loss=Decimal('123456789.12')  # High precision loss
            )
        ]
        
        # Act
        result = sma_calculator.calculate_sma(
            bi_data=bi_data_precision,
            loss_data=loss_data_precision,
            entity_id="PRECISION_TEST_BANK",
            calculation_date=date(2023, 12, 31),
            run_id="PRECISION_TEST"
        )
        
        # Assert
        # Final results should be rounded to appropriate precision (2 decimal places for currency)
        assert result.orc.as_tuple().exponent >= -2
        assert result.rwa.as_tuple().exponent >= -2
        
        # Intermediate calculations should maintain precision
        assert result.bi_current > Decimal('0')
        assert result.bic > Decimal('0')
        assert result.lc > Decimal('0')
    
    def test_rbi_comprehensive_compliance_scenario(self, sma_calculator):
        """
        Test: Comprehensive RBI compliance scenario covering all requirements.
        Regulation: Complete RBI Basel III SMA methodology compliance
        """
        # Arrange - Comprehensive test scenario
        bi_data_comprehensive = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('200000000000'),  # ₹20,000 crore
                sc=Decimal('80000000000'),     # ₹8,000 crore  
                fc=Decimal('40000000000'),     # ₹4,000 crore
                entity_id="COMPREHENSIVE_BANK",
                calculation_date=date(2023, 12, 31)
            ),
            BusinessIndicatorData(
                period="2022", 
                ildc=Decimal('190000000000'),  # ₹19,000 crore
                sc=Decimal('75000000000'),     # ₹7,500 crore
                fc=Decimal('35000000000'),     # ₹3,500 crore
                entity_id="COMPREHENSIVE_BANK",
                calculation_date=date(2022, 12, 31)
            ),
            BusinessIndicatorData(
                period="2021",
                ildc=Decimal('180000000000'),  # ₹18,000 crore
                sc=Decimal('70000000000'),     # ₹7,000 crore
                fc=Decimal('30000000000'),     # ₹3,000 crore
                entity_id="COMPREHENSIVE_BANK", 
                calculation_date=date(2021, 12, 31)
            )
        ]
        
        # 10 years of comprehensive loss data
        loss_data_comprehensive = []
        for year in range(2014, 2024):
            # Multiple losses per year with varying amounts
            quarterly_losses = [150, 200, 100, 250]  # ₹ crore amounts
            for quarter, amount in enumerate(quarterly_losses, 1):
                loss_data_comprehensive.append(
                    LossData(
                        event_id=f"COMP_LOSS_{year}_Q{quarter}",
                        entity_id="COMPREHENSIVE_BANK",
                        accounting_date=date(year, quarter * 3, 15),
                        net_loss=Decimal(str(amount * 10000000))  # Convert to paise
                    )
                )
        
        # Act
        result = sma_calculator.calculate_sma(
            bi_data=bi_data_comprehensive,
            loss_data=loss_data_comprehensive,
            entity_id="COMPREHENSIVE_BANK",
            calculation_date=date(2023, 12, 31),
            run_id="COMPREHENSIVE_COMPLIANCE_TEST"
        )
        
        # Assert - Comprehensive compliance verification
        
        # 1. Business Indicator compliance
        # 2023: 32000, 2022: 30000, 2021: 28000
        # Average: 30000 crore
        assert result.bi_three_year_average == Decimal('300000000000')
        
        # 2. Bucket classification compliance (₹30,000 crore is in Bucket 2, not Bucket 3)
        assert result.bucket == RBIBucket.BUCKET_2  # ₹30,000 crore < ₹2,40,000 crore threshold
        
        # 3. BIC calculation compliance with Bucket 2 marginal coefficients
        # BIC = (₹8,000 * 12%) + (₹22,000 * 15%) = ₹960 + ₹3,300 = ₹4,260 crore
        expected_bic = (Decimal('80000000000') * Decimal('0.12') +      # ₹8,000 * 12%
                       Decimal('220000000000') * Decimal('0.15'))       # ₹22,000 * 15%
        assert result.bic == expected_bic
        
        # 4. Loss Component compliance
        assert result.loss_data_years == 10  # Full 10-year horizon
        # Total annual losses = (150+200+100+250) = 700 crore per year
        expected_avg_losses = Decimal('7000000000')
        assert result.average_annual_losses == expected_avg_losses
        expected_lc = expected_avg_losses * Decimal('15')
        assert result.lc == expected_lc
        
        # 5. ILM calculation compliance (not gated for Bucket 3 with sufficient data)
        assert not result.ilm_gated
        assert result.ilm > Decimal('0')
        
        # 6. Final capital calculation compliance
        assert result.orc > Decimal('0')
        # Allow for small rounding differences in RWA calculation
        expected_rwa = result.orc * Decimal('12.5')
        assert abs(result.rwa - expected_rwa) < Decimal('0.10')
        
        # 7. Regulatory metadata compliance
        assert result.model_version is not None
        assert result.parameters_version is not None
        assert result.calculation_timestamp is not None
        
        print(f"Comprehensive RBI compliance test results:")
        print(f"  BI (3-year avg): ₹{result.bi_three_year_average/10000000:,.0f} crore")
        print(f"  Bucket: {result.bucket.value}")
        print(f"  BIC: ₹{result.bic/10000000:,.0f} crore")
        print(f"  LC: ₹{result.lc/10000000:,.0f} crore")
        print(f"  ILM: {result.ilm:.6f} (gated: {result.ilm_gated})")
        print(f"  ORC: ₹{result.orc/10000000:,.0f} crore")
        print(f"  RWA: ₹{result.rwa/10000000:,.0f} crore")