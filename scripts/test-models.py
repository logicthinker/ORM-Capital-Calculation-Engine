#!/usr/bin/env python3
"""
Test script to verify models and repositories work correctly

Creates sample data and tests CRUD operations.
"""

import asyncio
import sys
import os
from datetime import date, datetime
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from orm_calculator.database.connection import init_database, close_database, db_manager
from orm_calculator.database.repositories import RepositoryFactory
from orm_calculator.models.orm_models import (
    BusinessIndicator, LossEvent, Recovery, CapitalCalculation, Job,
    JobStatusEnum, ModelNameEnum, ExecutionModeEnum
)


async def test_business_indicators():
    """Test business indicator operations"""
    print("Testing Business Indicators...")
    
    async with db_manager.get_session() as session:
        repo_factory = RepositoryFactory(session)
        bi_repo = repo_factory.business_indicator_repository()
        
        # Create a business indicator
        bi = BusinessIndicator(
            entity_id="BANK001",
            calculation_date=date(2023, 12, 31),
            period="2023-Q4",
            ildc=Decimal("1000000.00"),
            sc=Decimal("500000.00"),
            fc=Decimal("300000.00"),
            bi_total=Decimal("1800000.00"),
            methodology="SMA"
        )
        
        created_bi = await bi_repo.create(bi)
        await session.commit()
        print(f"Created Business Indicator: {created_bi.id}")
        
        # Find by ID
        found_bi = await bi_repo.find_by_id(created_bi.id)
        assert found_bi is not None
        print(f"Found Business Indicator: {found_bi.entity_id} - {found_bi.bi_total}")
        
        # Find by entity and period
        bis = await bi_repo.find_by_entity_and_period("BANK001", "2023-Q4")
        assert len(bis) == 1
        print(f"Found {len(bis)} business indicators for BANK001 Q4 2023")


async def test_loss_events():
    """Test loss event operations"""
    print("Testing Loss Events...")
    
    async with db_manager.get_session() as session:
        repo_factory = RepositoryFactory(session)
        loss_repo = repo_factory.loss_event_repository()
        recovery_repo = repo_factory.recovery_repository()
        
        # Create a loss event
        loss_event = LossEvent(
            entity_id="BANK001",
            event_type="Operational Loss",
            occurrence_date=date(2023, 6, 15),
            discovery_date=date(2023, 6, 20),
            accounting_date=date(2023, 6, 30),
            gross_amount=Decimal("250000.00"),
            net_amount=Decimal("250000.00"),
            basel_event_type="Internal Fraud",
            business_line="Retail Banking"
        )
        
        created_loss = await loss_repo.create(loss_event)
        await session.commit()
        print(f"Created Loss Event: {created_loss.id}")
        
        # Create a recovery
        recovery = Recovery(
            loss_event_id=created_loss.id,
            amount=Decimal("50000.00"),
            receipt_date=date(2023, 8, 15),
            recovery_type="Insurance"
        )
        
        created_recovery = await recovery_repo.create(recovery)
        await session.commit()
        print(f"Created Recovery: {created_recovery.id}")
        
        # Find loss event with recoveries
        loss_with_recoveries = await loss_repo.find_by_id_with_recoveries(created_loss.id)
        assert loss_with_recoveries is not None
        assert len(loss_with_recoveries.recoveries) == 1
        print(f"Loss event has {len(loss_with_recoveries.recoveries)} recoveries")
        
        # Test threshold query
        above_threshold = await loss_repo.find_above_threshold(Decimal("200000.00"))
        assert len(above_threshold) == 1
        print(f"Found {len(above_threshold)} losses above threshold")


async def test_capital_calculations():
    """Test capital calculation operations"""
    print("Testing Capital Calculations...")
    
    async with db_manager.get_session() as session:
        repo_factory = RepositoryFactory(session)
        calc_repo = repo_factory.capital_calculation_repository()
        
        # Create a capital calculation
        calculation = CapitalCalculation(
            run_id="run_001",
            entity_id="BANK001",
            calculation_date=date(2023, 12, 31),
            methodology=ModelNameEnum.SMA,
            business_indicator=Decimal("1800000.00"),
            business_indicator_component=Decimal("216000.00"),
            loss_component=Decimal("3750000.00"),
            internal_loss_multiplier=Decimal("1.2345"),
            operational_risk_capital=Decimal("266652.00"),
            risk_weighted_assets=Decimal("3333150.00"),
            bucket=2,
            ilm_gated=False
        )
        
        created_calc = await calc_repo.create(calculation)
        await session.commit()
        print(f"Created Capital Calculation: {created_calc.id}")
        
        # Find by run ID
        found_calc = await calc_repo.find_by_run_id("run_001")
        assert found_calc is not None
        print(f"Found calculation by run_id: ORC = {found_calc.operational_risk_capital}")


async def test_jobs():
    """Test job operations"""
    print("Testing Jobs...")
    
    async with db_manager.get_session() as session:
        repo_factory = RepositoryFactory(session)
        job_repo = repo_factory.job_repository()
        
        # Create a job
        job = Job(
            run_id="run_002",
            model_name=ModelNameEnum.SMA,
            execution_mode=ExecutionModeEnum.ASYNC,
            entity_id="BANK001",
            calculation_date=date(2023, 12, 31),
            status=JobStatusEnum.QUEUED,
            idempotency_key="test_key_001"
        )
        
        created_job = await job_repo.create(job)
        await session.commit()
        print(f"Created Job: {created_job.id}")
        
        # Update job status
        updated_job = await job_repo.update_status(
            created_job.id, 
            JobStatusEnum.RUNNING, 
            progress_percentage=Decimal("25.0")
        )
        await session.commit()
        assert updated_job.status == JobStatusEnum.RUNNING
        print(f"Updated job status to: {updated_job.status}")
        
        # Find by idempotency key
        found_job = await job_repo.find_by_idempotency_key("test_key_001")
        assert found_job is not None
        print(f"Found job by idempotency key: {found_job.run_id}")


async def main():
    """Run all tests"""
    try:
        print("Initializing database...")
        await init_database()
        
        print("\nRunning model tests...")
        await test_business_indicators()
        await test_loss_events()
        await test_capital_calculations()
        await test_jobs()
        
        print("\nAll tests passed successfully!")
        return 0
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await close_database()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)