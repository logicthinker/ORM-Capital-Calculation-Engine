"""
Integration tests for SMA Calculator with existing models

Tests the integration between SMA calculator and the ORM/Pydantic models.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime

from src.orm_calculator.services.sma_calculator import (
    SMACalculator,
    BusinessIndicatorData,
    LossData,
    RBIBucket
)


class TestSMAIntegration:
    """Integration tests for SMA Calculator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.calculator = SMACalculator()
    
    def test_sma_calculator_import(self):
        """Test that SMA calculator can be imported correctly"""
        assert self.calculator is not None
        assert self.calculator.model_version == "1.0.0"
        assert self.calculator.parameters_version == "1.0.0"
    
    def test_data_classes_creation(self):
        """Test that data classes can be created correctly"""
        # Test BusinessIndicatorData creation
        bi_data = BusinessIndicatorData(
            period="2023",
            ildc=Decimal('50000000000'),
            sc=Decimal('20000000000'),
            fc=Decimal('10000000000'),
            entity_id="TEST_BANK",
            calculation_date=date(2023, 12, 31)
        )
        
        assert bi_data.period == "2023"
        assert bi_data.ildc == Decimal('50000000000')
        assert bi_data.entity_id == "TEST_BANK"
        
        # Test LossData creation
        loss_data = LossData(
            event_id="LOSS001",
            entity_id="TEST_BANK",
            accounting_date=date(2023, 6, 15),
            net_loss=Decimal('50000000')
        )
        
        assert loss_data.event_id == "LOSS001"
        assert loss_data.net_loss == Decimal('50000000')
        assert not loss_data.is_excluded
    
    def test_rbi_bucket_enum(self):
        """Test RBI bucket enumeration"""
        assert RBIBucket.BUCKET_1.value == "bucket_1"
        assert RBIBucket.BUCKET_2.value == "bucket_2"
        assert RBIBucket.BUCKET_3.value == "bucket_3"
    
    def test_calculator_constants(self):
        """Test that calculator constants are set correctly"""
        # Test thresholds
        assert self.calculator.BUCKET_1_THRESHOLD == Decimal('80000000000')
        assert self.calculator.BUCKET_2_THRESHOLD == Decimal('2400000000000')
        
        # Test coefficients
        assert self.calculator.MARGINAL_COEFFICIENTS['bucket_1'] == Decimal('0.12')
        assert self.calculator.MARGINAL_COEFFICIENTS['bucket_2'] == Decimal('0.15')
        assert self.calculator.MARGINAL_COEFFICIENTS['bucket_3'] == Decimal('0.18')
        
        # Test multipliers
        assert self.calculator.LC_MULTIPLIER == Decimal('15')
        assert self.calculator.RWA_MULTIPLIER == Decimal('12.5')
    
    def test_end_to_end_calculation(self):
        """Test complete end-to-end SMA calculation"""
        # Create sample data
        bi_data = [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('50000000000'),
                sc=Decimal('20000000000'),
                fc=Decimal('10000000000'),
                entity_id="INTEGRATION_TEST",
                calculation_date=date(2023, 12, 31)
            )
        ]
        
        loss_data = [
            LossData(
                event_id="INTEGRATION_LOSS",
                entity_id="INTEGRATION_TEST",
                accounting_date=date(2023, 6, 15),
                net_loss=Decimal('50000000')
            )
        ]
        
        # Perform calculation
        result = self.calculator.calculate_sma(
            bi_data=bi_data,
            loss_data=loss_data,
            entity_id="INTEGRATION_TEST",
            calculation_date=date(2023, 12, 31),
            run_id="INTEGRATION_TEST_001"
        )
        
        # Verify result structure
        assert result.run_id == "INTEGRATION_TEST_001"
        assert result.entity_id == "INTEGRATION_TEST"
        assert isinstance(result.calculation_timestamp, datetime)
        assert result.bucket == RBIBucket.BUCKET_2  # ₹8,000 crore (exactly at threshold)
        assert result.orc > Decimal('0')
        assert result.rwa > Decimal('0')
        assert result.rwa == result.orc * Decimal('12.5')


if __name__ == "__main__":
    pytest.main([__file__])