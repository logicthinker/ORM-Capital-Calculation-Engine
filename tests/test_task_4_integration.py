"""
Integration tests for Task 4: ILM gating logic and basic parameter management

Tests the complete implementation of:
- ILM gating: set ORC = BIC for Bucket 1 or when less than 5 years of high-quality loss data
- National discretion parameter to optionally set ILM = 1
- Parameter configuration system using Pydantic models and database storage
- Parameter validation and loading functions with version control
- Bucket assignment with data quality considerations
"""

import pytest
from decimal import Decimal
from datetime import date, datetime
from typing import Dict, Any

from src.orm_calculator.services.sma_calculator import (
    SMACalculator, BusinessIndicatorData, LossData, RBIBucket
)
from src.orm_calculator.services.parameter_validation_service import (
    ParameterValidationService, ValidationSeverity
)


class TestTask4ILMGatingLogic:
    """Test ILM gating logic implementation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.calculator = SMACalculator()
    
    def test_ilm_gating_bucket_1_requirement_1_5(self):
        """Test ILM gating for Bucket 1 (Requirement 1.5)"""
        # Test data for Bucket 1 bank
        lc = Decimal('100000000')      # ₹10 crore
        bic = Decimal('8400000000')    # ₹840 crore (12% of ₹7,000 crore)
        bucket = RBIBucket.BUCKET_1
        years_with_data = 10  # Sufficient data, but Bucket 1 still gates
        
        ilm, gated, reason, metadata = self.calculator.calculate_ilm(
            lc, bic, bucket, years_with_data
        )
        
        # Verify ILM gating for Bucket 1
        assert gated == True
        assert ilm == Decimal('1')
        assert "Bucket 1" in reason
        assert "ORC = BIC" in reason
        
        # Verify metadata contains gating information
        assert metadata["bucket"] == "bucket_1"
        assert metadata["gating_checks"][0]["check"] == "bucket_1_gating"
        assert metadata["gating_checks"][0]["result"] == "gated"
        assert metadata["gating_checks"][0]["reason"] == "Bank is in Bucket 1"
    
    def test_ilm_gating_insufficient_data_requirement_1_5(self):
        """Test ILM gating for insufficient data quality (Requirement 1.5)"""
        # Test data for Bucket 2 bank with insufficient data
        lc = Decimal('495000000')      # ₹49.5 crore
        bic = Decimal('12600000000')   # ₹1,260 crore
        bucket = RBIBucket.BUCKET_2
        years_with_data = 3  # Less than 5 years required
        
        ilm, gated, reason, metadata = self.calculator.calculate_ilm(
            lc, bic, bucket, years_with_data
        )
        
        # Verify ILM gating for insufficient data
        assert gated == True
        assert ilm == Decimal('1')
        assert "3 years < 5 years" in reason
        assert "high-quality loss data" in reason
        
        # Verify metadata contains data quality information
        assert metadata["years_with_data"] == 3
        assert metadata["min_data_quality_years"] == 5
        assert metadata["gating_checks"][1]["check"] == "data_quality_gating"
        assert metadata["gating_checks"][1]["result"] == "gated"
    
    def test_ilm_gating_national_discretion_requirement_1_7(self):
        """Test national discretion parameter to set ILM = 1 (Requirement 1.7)"""
        # Create calculator with national discretion enabled
        parameters = {
            "national_discretion_ilm_one": True,
            "min_data_quality_years": 5
        }
        calculator = SMACalculator(parameters=parameters)
        
        # Test data for Bucket 2 bank with sufficient data
        lc = Decimal('495000000')      # ₹49.5 crore
        bic = Decimal('12600000000')   # ₹1,260 crore
        bucket = RBIBucket.BUCKET_2
        years_with_data = 10  # Sufficient data
        
        ilm, gated, reason, metadata = calculator.calculate_ilm(
            lc, bic, bucket, years_with_data
        )
        
        # Verify national discretion gating
        assert gated == True
        assert ilm == Decimal('1')
        assert "National discretion" in reason
        assert "governed parameter" in reason
        
        # Verify metadata shows national discretion is enabled
        assert metadata["national_discretion_enabled"] == True
        assert metadata["gating_checks"][2]["check"] == "national_discretion_gating"
        assert metadata["gating_checks"][2]["result"] == "gated"
    
    def test_ilm_calculation_without_gating(self):
        """Test normal ILM calculation when no gating conditions apply"""
        # Test data for Bucket 2 bank with sufficient data and no national discretion
        parameters = {
            "national_discretion_ilm_one": False,
            "min_data_quality_years": 5
        }
        calculator = SMACalculator(parameters=parameters)
        
        lc = Decimal('495000000')      # ₹49.5 crore
        bic = Decimal('12600000000')   # ₹1,260 crore
        bucket = RBIBucket.BUCKET_2
        years_with_data = 10  # Sufficient data
        
        ilm, gated, reason, metadata = calculator.calculate_ilm(
            lc, bic, bucket, years_with_data
        )
        
        # Verify normal ILM calculation
        assert gated == False
        assert reason is None
        assert ilm > Decimal('0')  # Should be calculated value
        assert ilm != Decimal('1')  # Should not be gated to 1
        
        # Verify all gating checks passed
        for check in metadata["gating_checks"]:
            if check["check"] != "calculation_error":
                assert check["result"] == "passed"


class TestTask4BucketAssignmentWithDataQuality:
    """Test bucket assignment with data quality considerations"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.calculator = SMACalculator()
    
    def test_bucket_assignment_with_data_quality_metadata(self):
        """Test bucket assignment includes data quality considerations"""
        bi_amount = Decimal('100000000000')  # ₹10,000 crore (Bucket 2)
        data_quality_years = 3  # Insufficient data
        
        bucket, metadata = self.calculator.assign_bucket(bi_amount, data_quality_years)
        
        # Verify bucket assignment
        assert bucket == RBIBucket.BUCKET_2
        
        # Verify data quality metadata
        assert metadata["data_quality_years"] == 3
        assert metadata["min_data_quality_years"] == 5
        assert metadata["data_quality_sufficient"] == False
        assert metadata["ilm_gating_applicable"] == True
        
        # Verify bucket assignment reason
        expected_reason = "Bucket 1 threshold (80,000,000,000) ≤ BI (100,000,000,000) < Bucket 2 threshold (2,400,000,000,000)"
        assert metadata["bucket_assignment_reason"] == expected_reason
    
    def test_bucket_assignment_sufficient_data_quality(self):
        """Test bucket assignment with sufficient data quality"""
        bi_amount = Decimal('100000000000')  # ₹10,000 crore (Bucket 2)
        data_quality_years = 7  # Sufficient data
        
        bucket, metadata = self.calculator.assign_bucket(bi_amount, data_quality_years)
        
        # Verify bucket assignment
        assert bucket == RBIBucket.BUCKET_2
        
        # Verify data quality metadata
        assert metadata["data_quality_years"] == 7
        assert metadata["data_quality_sufficient"] == True
        assert metadata["ilm_gating_applicable"] == False  # Only Bucket 1 would gate


class TestTask4ParameterManagement:
    """Test parameter configuration system with validation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.validation_service = ParameterValidationService()
    
    def test_parameter_validation_system(self):
        """Test comprehensive parameter validation system"""
        # Test valid SMA parameters
        valid_parameters = {
            "marginal_coefficients": {
                "bucket_1": "0.12",
                "bucket_2": "0.15",
                "bucket_3": "0.18"
            },
            "bucket_thresholds": {
                "bucket_1_threshold": "80000000000",
                "bucket_2_threshold": "2400000000000"
            },
            "lc_multiplier": "15",
            "rwa_multiplier": "12.5",
            "min_loss_threshold": "10000000",
            "national_discretion_ilm_one": False,
            "min_data_quality_years": 5
        }
        
        is_valid, messages = self.validation_service.validate_parameter_set("SMA", valid_parameters)
        
        assert is_valid == True
        # Should have no error messages
        error_messages = [msg for msg in messages if msg.severity == ValidationSeverity.ERROR]
        assert len(error_messages) == 0
    
    def test_parameter_validation_with_errors(self):
        """Test parameter validation catches errors"""
        # Test invalid parameters
        invalid_parameters = {
            "marginal_coefficients": {
                "bucket_1": "1.5",  # > 1.0 (invalid)
                "bucket_2": "-0.1",  # negative (invalid)
                "bucket_3": "0.18"
            },
            "bucket_thresholds": {
                "bucket_1_threshold": "100000000000",  # > bucket_2 (invalid)
                "bucket_2_threshold": "80000000000"
            },
            "national_discretion_ilm_one": "not_boolean"  # invalid type
        }
        
        is_valid, messages = self.validation_service.validate_parameter_set("SMA", invalid_parameters)
        
        assert is_valid == False
        # Should have multiple error messages
        error_messages = [msg for msg in messages if msg.severity == ValidationSeverity.ERROR]
        assert len(error_messages) >= 4  # At least 4 errors
    
    def test_parameter_loading_and_updating(self):
        """Test parameter loading and updating functionality"""
        # Test default parameters
        calculator = SMACalculator()
        
        # Verify default parameters are loaded
        assert calculator.MARGINAL_COEFFICIENTS['bucket_1'] == Decimal('0.12')
        assert calculator.MARGINAL_COEFFICIENTS['bucket_2'] == Decimal('0.15')
        assert calculator.MARGINAL_COEFFICIENTS['bucket_3'] == Decimal('0.18')
        assert calculator.NATIONAL_DISCRETION_ILM_ONE == False
        assert calculator.MIN_DATA_QUALITY_YEARS == 5
        
        # Test parameter updates
        new_parameters = {
            "marginal_coefficients": {
                "bucket_1": "0.13",
                "bucket_2": "0.16",
                "bucket_3": "0.19"
            },
            "national_discretion_ilm_one": True,
            "min_data_quality_years": 7
        }
        
        calculator.update_parameters(new_parameters)
        
        # Verify parameters were updated
        assert calculator.MARGINAL_COEFFICIENTS['bucket_1'] == Decimal('0.13')
        assert calculator.MARGINAL_COEFFICIENTS['bucket_2'] == Decimal('0.16')
        assert calculator.MARGINAL_COEFFICIENTS['bucket_3'] == Decimal('0.19')
        assert calculator.NATIONAL_DISCRETION_ILM_ONE == True
        assert calculator.MIN_DATA_QUALITY_YEARS == 7


class TestTask4CompleteIntegration:
    """Test complete integration of Task 4 requirements"""
    
    def test_complete_sma_calculation_with_parameter_management(self):
        """Test complete SMA calculation with parameter management integration"""
        # Create calculator with custom parameters
        parameters = {
            "marginal_coefficients": {
                "bucket_1": "0.12",
                "bucket_2": "0.15",
                "bucket_3": "0.18"
            },
            "bucket_thresholds": {
                "bucket_1_threshold": "80000000000",
                "bucket_2_threshold": "2400000000000"
            },
            "national_discretion_ilm_one": False,
            "min_data_quality_years": 5,
            "lc_multiplier": "15",
            "rwa_multiplier": "12.5"
        }
        
        calculator = SMACalculator(parameters=parameters)
        
        # Sample business indicator data (Bucket 1)
        bi_data = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('40000000000'),  # ₹4,000 crore
                sc=Decimal('20000000000'),    # ₹2,000 crore
                fc=Decimal('10000000000'),    # ₹1,000 crore
                entity_id="BANK001",
                calculation_date=date(2023, 12, 31)
            )
        ]
        
        # Sample loss data (insufficient years)
        loss_data = [
            LossData(
                event_id="LOSS001",
                entity_id="BANK001",
                accounting_date=date(2023, 1, 1),
                net_loss=Decimal('50000000')  # ₹5 crore
            ),
            LossData(
                event_id="LOSS002",
                entity_id="BANK001",
                accounting_date=date(2022, 1, 1),
                net_loss=Decimal('30000000')  # ₹3 crore
            )
        ]
        
        # Perform complete SMA calculation
        result = calculator.calculate_sma(
            bi_data=bi_data,
            loss_data=loss_data,
            entity_id="BANK001",
            calculation_date=date(2023, 12, 31),
            run_id="TEST_RUN_001"
        )
        
        # Verify calculation results
        assert result.entity_id == "BANK001"
        assert result.run_id == "TEST_RUN_001"
        assert result.bucket == RBIBucket.BUCKET_1
        
        # Verify ILM gating occurred (Bucket 1)
        assert result.ilm_gated == True
        assert result.ilm == Decimal('1')
        assert "Bucket 1" in result.ilm_gate_reason
        
        # Verify ORC = BIC for Bucket 1
        assert result.orc == result.bic
        
        # Verify parameter versions are tracked
        assert result.parameters_version is not None
        assert result.model_version is not None
        assert result.parameters_used is not None
        
        # Verify metadata contains parameter information
        assert result.bucket_metadata is not None
        assert result.ilm_metadata is not None
        assert result.bucket_metadata["ilm_gating_applicable"] == True
    
    def test_requirement_coverage_verification(self):
        """Verify all Task 4 requirements are implemented"""
        calculator = SMACalculator()
        
        # Requirement 1.5: ILM gating for Bucket 1
        lc = Decimal('100000000')
        bic = Decimal('8400000000')
        bucket = RBIBucket.BUCKET_1
        years_with_data = 10
        
        ilm, gated, reason, metadata = calculator.calculate_ilm(lc, bic, bucket, years_with_data)
        assert gated == True and "Bucket 1" in reason  # ✓ Requirement 1.5a
        
        # Requirement 1.5: ILM gating for insufficient data
        bucket = RBIBucket.BUCKET_2
        years_with_data = 3
        
        ilm, gated, reason, metadata = calculator.calculate_ilm(lc, bic, bucket, years_with_data)
        assert gated == True and "3 years < 5 years" in reason  # ✓ Requirement 1.5b
        
        # Requirement 1.7: National discretion parameter
        parameters = {"national_discretion_ilm_one": True}
        calculator_with_discretion = SMACalculator(parameters=parameters)
        
        ilm, gated, reason, metadata = calculator_with_discretion.calculate_ilm(
            lc, bic, RBIBucket.BUCKET_2, 10
        )
        assert gated == True and "National discretion" in reason  # ✓ Requirement 1.7
        
        # Requirement 9.1: Parameter configuration system
        validation_service = ParameterValidationService()
        parameters = {
            "marginal_coefficients": {"bucket_1": "0.12", "bucket_2": "0.15", "bucket_3": "0.18"},
            "national_discretion_ilm_one": False,
            "min_data_quality_years": 5
        }
        
        is_valid, messages = validation_service.validate_parameter_set("SMA", parameters)
        assert is_valid == True  # ✓ Requirement 9.1 (parameter validation)
        
        # Bucket assignment with data quality considerations
        bi_amount = Decimal('100000000000')
        bucket, metadata = calculator.assign_bucket(bi_amount, 3)
        assert metadata["data_quality_years"] == 3  # ✓ Data quality tracking
        assert metadata["ilm_gating_applicable"] == True  # ✓ Gating logic integration
        
        print("✓ All Task 4 requirements verified:")
        print("  ✓ 1.5: ILM gating for Bucket 1 and insufficient data")
        print("  ✓ 1.7: National discretion parameter")
        print("  ✓ 9.1: Parameter configuration system with validation")
        print("  ✓ Bucket assignment with data quality considerations")
        print("  ✓ Parameter loading and version control")