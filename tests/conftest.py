"""
Pytest configuration and fixtures for ORM Capital Calculator Engine

This module provides comprehensive test fixtures and configuration for TDD approach
covering unit, integration, performance, regulatory, and security testing.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Generator
from unittest.mock import Mock, AsyncMock
import sqlite3
import os

# Test data generators
from faker import Faker
import numpy as np

# Application imports
from src.orm_calculator.services.sma_calculator import (
    SMACalculator,
    BusinessIndicatorData,
    LossData,
    RBIBucket,
    SMACalculationResult
)

fake = Faker('en_IN')  # Indian locale for realistic test data


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def temp_db_dir():
    """Create temporary directory for test databases"""
    temp_dir = tempfile.mkdtemp(prefix="orm_test_")
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_db_path(temp_db_dir):
    """Create unique test database path for each test"""
    db_path = Path(temp_db_dir) / f"test_{fake.uuid4()}.db"
    yield str(db_path)
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def sma_calculator():
    """Create SMA calculator instance for testing"""
    return SMACalculator(model_version="1.0.0-test", parameters_version="1.0.0-test")


# Test data fixtures
@pytest.fixture
def sample_bi_data_bucket_1():
    """Sample Business Indicator data for Bucket 1 (< ₹8,000 crore)"""
    return [
        BusinessIndicatorData(
            period="2023",
            ildc=Decimal('40000000000'),  # ₹4,000 crore
            sc=Decimal('20000000000'),    # ₹2,000 crore
            fc=Decimal('10000000000'),    # ₹1,000 crore
            entity_id="BUCKET1_BANK",
            calculation_date=date(2023, 12, 31)
        ),
        BusinessIndicatorData(
            period="2022",
            ildc=Decimal('38000000000'),  # ₹3,800 crore
            sc=Decimal('22000000000'),    # ₹2,200 crore
            fc=Decimal('12000000000'),    # ₹1,200 crore
            entity_id="BUCKET1_BANK",
            calculation_date=date(2022, 12, 31)
        ),
        BusinessIndicatorData(
            period="2021",
            ildc=Decimal('35000000000'),  # ₹3,500 crore
            sc=Decimal('18000000000'),    # ₹1,800 crore
            fc=Decimal('9000000000'),     # ₹900 crore
            entity_id="BUCKET1_BANK",
            calculation_date=date(2021, 12, 31)
        )
    ]


@pytest.fixture
def sample_bi_data_bucket_2():
    """Sample Business Indicator data for Bucket 2 (₹8,000 - ₹2,40,000 crore)"""
    return [
        BusinessIndicatorData(
            period="2023",
            ildc=Decimal('80000000000'),   # ₹8,000 crore
            sc=Decimal('30000000000'),     # ₹3,000 crore
            fc=Decimal('20000000000'),     # ₹2,000 crore
            entity_id="BUCKET2_BANK",
            calculation_date=date(2023, 12, 31)
        ),
        BusinessIndicatorData(
            period="2022",
            ildc=Decimal('75000000000'),   # ₹7,500 crore
            sc=Decimal('32000000000'),     # ₹3,200 crore
            fc=Decimal('18000000000'),     # ₹1,800 crore
            entity_id="BUCKET2_BANK",
            calculation_date=date(2022, 12, 31)
        ),
        BusinessIndicatorData(
            period="2021",
            ildc=Decimal('70000000000'),   # ₹7,000 crore
            sc=Decimal('28000000000'),     # ₹2,800 crore
            fc=Decimal('22000000000'),     # ₹2,200 crore
            entity_id="BUCKET2_BANK",
            calculation_date=date(2021, 12, 31)
        )
    ]


@pytest.fixture
def sample_bi_data_bucket_3():
    """Sample Business Indicator data for Bucket 3 (≥ ₹2,40,000 crore)"""
    return [
        BusinessIndicatorData(
            period="2023",
            ildc=Decimal('2500000000000'),  # ₹2,50,000 crore
            sc=Decimal('150000000000'),     # ₹15,000 crore
            fc=Decimal('100000000000'),     # ₹10,000 crore
            entity_id="BUCKET3_BANK",
            calculation_date=date(2023, 12, 31)
        ),
        BusinessIndicatorData(
            period="2022",
            ildc=Decimal('2400000000000'),  # ₹2,40,000 crore
            sc=Decimal('140000000000'),     # ₹14,000 crore
            fc=Decimal('95000000000'),      # ₹9,500 crore
            entity_id="BUCKET3_BANK",
            calculation_date=date(2022, 12, 31)
        ),
        BusinessIndicatorData(
            period="2021",
            ildc=Decimal('2300000000000'),  # ₹2,30,000 crore
            sc=Decimal('130000000000'),     # ₹13,000 crore
            fc=Decimal('90000000000'),      # ₹9,000 crore
            entity_id="BUCKET3_BANK",
            calculation_date=date(2021, 12, 31)
        )
    ]


@pytest.fixture
def sample_loss_data_10_years():
    """Sample loss data for 10 years with realistic distribution"""
    loss_data = []
    base_year = 2014
    
    for year in range(base_year, base_year + 10):
        # Generate 2-4 losses per year with varying amounts
        num_losses = fake.random_int(min=2, max=4)
        
        for i in range(num_losses):
            # Generate loss amounts following realistic distribution
            # Most losses are small, few are large
            if fake.random.random() < 0.8:  # 80% small losses
                loss_amount = fake.random_int(min=10000000, max=100000000)  # ₹1-10 crore
            elif fake.random.random() < 0.95:  # 15% medium losses
                loss_amount = fake.random_int(min=100000000, max=500000000)  # ₹10-50 crore
            else:  # 5% large losses
                loss_amount = fake.random_int(min=500000000, max=2000000000)  # ₹50-200 crore
            
            loss_data.append(
                LossData(
                    event_id=f"LOSS_{year}_{i+1:02d}",
                    entity_id="TEST_BANK",
                    accounting_date=date(year, fake.random_int(min=1, max=12), 15),
                    net_loss=Decimal(str(loss_amount))
                )
            )
    
    return loss_data


@pytest.fixture
def sample_loss_data_insufficient():
    """Sample loss data with insufficient years (< 5 years)"""
    loss_data = []
    base_year = 2020
    
    for year in range(base_year, base_year + 3):  # Only 3 years
        loss_data.append(
            LossData(
                event_id=f"LOSS_{year}_01",
                entity_id="INSUFFICIENT_DATA_BANK",
                accounting_date=date(year, 6, 15),
                net_loss=Decimal('50000000')  # ₹5 crore
            )
        )
    
    return loss_data


@pytest.fixture
def boundary_test_cases():
    """Test cases for boundary conditions"""
    return {
        'bucket_1_upper_boundary': Decimal('79999999999'),  # Just below ₹8,000 crore
        'bucket_1_exact_threshold': Decimal('80000000000'),  # Exactly ₹8,000 crore
        'bucket_2_lower_boundary': Decimal('80000000001'),   # Just above ₹8,000 crore
        'bucket_2_upper_boundary': Decimal('2399999999999'), # Just below ₹2,40,000 crore
        'bucket_2_exact_threshold': Decimal('2400000000000'), # Exactly ₹2,40,000 crore
        'bucket_3_lower_boundary': Decimal('2400000000001'),  # Just above ₹2,40,000 crore
        'zero_bi': Decimal('0'),
        'negative_bi': Decimal('-1000000000'),  # Negative ₹100 crore
        'minimum_loss_threshold': Decimal('10000000'),  # ₹1,00,000
        'below_minimum_threshold': Decimal('9999999'),   # Just below threshold
    }


@pytest.fixture
def stress_test_scenarios():
    """Stress test scenarios for analytics testing"""
    return {
        'high_loss_scenario': {
            'loss_multiplier': 1.3,  # +30% losses
            'description': 'High loss stress scenario'
        },
        'low_income_scenario': {
            'bi_multiplier': 0.8,  # -20% fee-based BI
            'description': 'Low income stress scenario'
        },
        'recovery_haircut_scenario': {
            'recovery_multiplier': 0.5,  # 50% recovery haircut
            'description': 'Recovery haircut scenario'
        },
        'combined_stress_scenario': {
            'loss_multiplier': 1.3,
            'bi_multiplier': 0.8,
            'recovery_multiplier': 0.5,
            'description': 'Combined stress scenario'
        }
    }


@pytest.fixture
def performance_test_data():
    """Large dataset for performance testing"""
    def generate_large_dataset(num_entities=100, years=10):
        bi_data = []
        loss_data = []
        
        for entity_id in range(1, num_entities + 1):
            entity_name = f"PERF_TEST_BANK_{entity_id:03d}"
            
            # Generate BI data for each entity
            for year in range(2014, 2014 + years):
                bi_data.append(
                    BusinessIndicatorData(
                        period=str(year),
                        ildc=Decimal(str(fake.random_int(min=10000000000, max=100000000000))),
                        sc=Decimal(str(fake.random_int(min=5000000000, max=50000000000))),
                        fc=Decimal(str(fake.random_int(min=2000000000, max=20000000000))),
                        entity_id=entity_name,
                        calculation_date=date(year, 12, 31)
                    )
                )
            
            # Generate loss data for each entity
            for year in range(2014, 2014 + years):
                num_losses = fake.random_int(min=1, max=5)
                for i in range(num_losses):
                    loss_data.append(
                        LossData(
                            event_id=f"PERF_LOSS_{entity_id}_{year}_{i+1}",
                            entity_id=entity_name,
                            accounting_date=date(year, fake.random_int(min=1, max=12), 15),
                            net_loss=Decimal(str(fake.random_int(min=10000000, max=500000000)))
                        )
                    )
        
        return bi_data, loss_data
    
    return generate_large_dataset


@pytest.fixture
def mock_database():
    """Mock database for testing without actual database"""
    mock_db = Mock()
    mock_db.execute = AsyncMock()
    mock_db.fetch_all = AsyncMock()
    mock_db.fetch_one = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    return mock_db


@pytest.fixture
def mock_webhook_service():
    """Mock webhook service for testing callbacks"""
    mock_service = Mock()
    mock_service.deliver_webhook = AsyncMock()
    mock_service.retry_delivery = AsyncMock()
    mock_service.get_delivery_status = AsyncMock()
    return mock_service


@pytest.fixture
def regulatory_test_parameters():
    """RBI regulatory parameters for compliance testing"""
    return {
        'rbi_thresholds': {
            'bucket_1': Decimal('80000000000'),    # ₹8,000 crore
            'bucket_2': Decimal('2400000000000'),  # ₹2,40,000 crore
        },
        'marginal_coefficients': {
            'bucket_1': Decimal('0.12'),  # 12%
            'bucket_2': Decimal('0.15'),  # 15%
            'bucket_3': Decimal('0.18'),  # 18%
        },
        'loss_component_multiplier': Decimal('15'),
        'rwa_multiplier': Decimal('12.5'),
        'minimum_loss_threshold': Decimal('10000000'),  # ₹1,00,000
        'minimum_data_years': 5,
        'loss_horizon_years': 10,
    }


@pytest.fixture
def security_test_config():
    """Security testing configuration"""
    return {
        'valid_tokens': [
            'valid_token_read_only',
            'valid_token_read_write',
            'valid_token_admin'
        ],
        'invalid_tokens': [
            'expired_token',
            'malformed_token',
            'revoked_token'
        ],
        'rbac_scopes': {
            'read_only': ['read:calculations', 'read:parameters'],
            'read_write': ['read:calculations', 'read:parameters', 'write:calculations'],
            'admin': ['read:calculations', 'read:parameters', 'write:calculations', 'write:parameters', 'admin:all']
        }
    }


@pytest.fixture
def audit_test_data():
    """Test data for audit and lineage testing"""
    return {
        'run_id': 'TEST_RUN_001',
        'initiator': 'test_user@bank.com',
        'calculation_timestamp': datetime.now(),
        'input_hash': 'sha256_input_hash',
        'parameter_version': '1.0.0',
        'model_version': '1.0.0',
        'environment_hash': 'sha256_environment_hash'
    }


# Test utilities
class TestDataGenerator:
    """Utility class for generating test data"""
    
    @staticmethod
    def generate_bi_data_with_negatives():
        """Generate BI data with negative values for RBI Max/Min/Abs testing"""
        return [
            BusinessIndicatorData(
                period="2023",
                ildc=Decimal('-10000000000'),  # Negative ILDC
                sc=Decimal('-5000000000'),     # Negative SC
                fc=Decimal('15000000000'),     # Positive FC
                entity_id="NEGATIVE_TEST_BANK",
                calculation_date=date(2023, 12, 31)
            )
        ]
    
    @staticmethod
    def generate_loss_data_with_exclusions():
        """Generate loss data with RBI exclusions"""
        return [
            LossData(
                event_id="EXCLUDED_LOSS_001",
                entity_id="EXCLUSION_TEST_BANK",
                accounting_date=date(2023, 6, 15),
                net_loss=Decimal('100000000'),  # ₹10 crore
                is_excluded=True,
                exclusion_reason="RBI approved exclusion - operational disruption"
            ),
            LossData(
                event_id="INCLUDED_LOSS_001",
                entity_id="EXCLUSION_TEST_BANK",
                accounting_date=date(2023, 8, 20),
                net_loss=Decimal('50000000'),   # ₹5 crore
                is_excluded=False
            )
        ]
    
    @staticmethod
    def generate_recovery_data():
        """Generate recovery data for net loss calculation testing"""
        return [
            LossData(
                event_id="RECOVERY_TEST_001",
                entity_id="RECOVERY_TEST_BANK",
                accounting_date=date(2023, 6, 15),
                net_loss=Decimal('80000000')  # ₹8 crore (₹10 crore gross - ₹2 crore recovery)
            )
        ]


# Performance testing utilities
@pytest.fixture
def performance_monitor():
    """Performance monitoring fixture"""
    import time
    import psutil
    import threading
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.memory_usage = []
            self.cpu_usage = []
            self.monitoring = False
            self.monitor_thread = None
        
        def start_monitoring(self):
            self.start_time = time.time()
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_resources)
            self.monitor_thread.start()
        
        def stop_monitoring(self):
            self.end_time = time.time()
            self.monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join()
        
        def _monitor_resources(self):
            while self.monitoring:
                self.memory_usage.append(psutil.virtual_memory().percent)
                self.cpu_usage.append(psutil.cpu_percent())
                time.sleep(0.1)
        
        def get_metrics(self):
            return {
                'execution_time': self.end_time - self.start_time if self.end_time else None,
                'avg_memory_usage': sum(self.memory_usage) / len(self.memory_usage) if self.memory_usage else 0,
                'max_memory_usage': max(self.memory_usage) if self.memory_usage else 0,
                'avg_cpu_usage': sum(self.cpu_usage) / len(self.cpu_usage) if self.cpu_usage else 0,
                'max_cpu_usage': max(self.cpu_usage) if self.cpu_usage else 0
            }
    
    return PerformanceMonitor()


# Database testing utilities
@pytest.fixture
def test_database_setup():
    """Set up test database with schema"""
    def setup_db(db_path: str):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create test tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS business_indicators (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                period TEXT NOT NULL,
                ildc REAL NOT NULL,
                sc REAL NOT NULL,
                fc REAL NOT NULL,
                calculation_date DATE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loss_events (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                accounting_date DATE NOT NULL,
                net_loss REAL NOT NULL,
                is_excluded BOOLEAN DEFAULT FALSE,
                exclusion_reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS capital_calculations (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL UNIQUE,
                entity_id TEXT NOT NULL,
                calculation_date DATE NOT NULL,
                methodology TEXT NOT NULL,
                business_indicator REAL NOT NULL,
                business_indicator_component REAL NOT NULL,
                loss_component REAL NOT NULL,
                internal_loss_multiplier REAL NOT NULL,
                operational_risk_capital REAL NOT NULL,
                risk_weighted_assets REAL NOT NULL,
                bucket TEXT NOT NULL,
                ilm_gated BOOLEAN DEFAULT FALSE,
                ilm_gate_reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    return setup_db


# Pytest markers for test categorization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.performance = pytest.mark.performance
pytest.mark.regulatory = pytest.mark.regulatory
pytest.mark.security = pytest.mark.security
pytest.mark.slow = pytest.mark.slow