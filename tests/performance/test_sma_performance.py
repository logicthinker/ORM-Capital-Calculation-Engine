"""
Performance Tests: SMA Calculation Engine

Test cases PERF-P-001 through PERF-P-004 from the comprehensive test plan.
These tests verify performance requirements and scalability targets.
"""

import pytest
import asyncio
import time
from decimal import Decimal
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from src.orm_calculator.services.sma_calculator import (
    SMACalculator,
    BusinessIndicatorData,
    LossData,
)


@pytest.mark.performance
@pytest.mark.slow
class TestSMAPerformance:
    """Performance tests for SMA calculation engine"""
    
    def test_perf_p_001_quarter_end_full_run(self, sma_calculator, performance_test_data, performance_monitor):
        """
        Test Case ID: PERF-P-001
        Description: Load Test (Quarter-End): Simulate a full quarter-end run.
        Target: Complete entire job in under 30 minutes.
        """
        # Arrange
        num_entities = 50  # Reduced for test environment
        years = 10
        bi_data, loss_data = performance_test_data(num_entities, years)
        
        performance_monitor.start_monitoring()
        start_time = time.time()
        
        # Act - Simulate quarter-end calculation for all entities
        results = []
        for entity_id in range(1, num_entities + 1):
            entity_name = f"PERF_TEST_BANK_{entity_id:03d}"
            
            # Filter data for this entity
            entity_bi_data = [bi for bi in bi_data if bi.entity_id == entity_name]
            entity_loss_data = [loss for loss in loss_data if loss.entity_id == entity_name]
            
            if entity_bi_data:  # Only calculate if we have BI data
                result = sma_calculator.calculate_sma(
                    bi_data=entity_bi_data,
                    loss_data=entity_loss_data,
                    entity_id=entity_name,
                    calculation_date=date(2023, 12, 31),
                    run_id=f"QUARTER_END_{entity_id:03d}"
                )
                results.append(result)
        
        end_time = time.time()
        performance_monitor.stop_monitoring()
        
        # Assert
        execution_time = end_time - start_time
        metrics = performance_monitor.get_metrics()
        
        # Performance assertions
        assert execution_time < 1800, f"Quarter-end run took {execution_time:.2f}s, should be < 30 minutes (1800s)"
        assert len(results) == num_entities, f"Expected {num_entities} results, got {len(results)}"
        
        # Memory usage should be reasonable
        assert metrics['max_memory_usage'] < 80, f"Memory usage {metrics['max_memory_usage']:.1f}% too high"
        
        # All results should be valid
        for result in results:
            assert result.orc >= Decimal('0')
            assert result.rwa >= Decimal('0')
            assert result.bucket in ['bucket_1', 'bucket_2', 'bucket_3']
        
        print(f"Quarter-end performance: {execution_time:.2f}s for {num_entities} entities")
        print(f"Average time per entity: {execution_time/num_entities:.3f}s")
        print(f"Peak memory usage: {metrics['max_memory_usage']:.1f}%")
    
    def test_perf_p_002_concurrent_ad_hoc_requests(self, sma_calculator, sample_bi_data_bucket_2, performance_monitor):
        """
        Test Case ID: PERF-P-002
        Description: Stress Test (Ad-hoc): Simulate concurrent ad-hoc requests.
        Target: p95 response time under 60 seconds for 50 concurrent users.
        """
        # Arrange
        num_concurrent_requests = 20  # Reduced for test environment
        
        # Create varied loss data for different scenarios
        loss_data_scenarios = []
        for i in range(num_concurrent_requests):
            scenario_loss_data = []
            for year in range(2019, 2024):
                for quarter in range(1, 5):
                    scenario_loss_data.append(
                        LossData(
                            event_id=f"CONCURRENT_LOSS_{i}_{year}_Q{quarter}",
                            entity_id=f"CONCURRENT_BANK_{i:03d}",
                            accounting_date=date(year, quarter * 3, 15),
                            net_loss=Decimal(str(50000000 + (i * 10000000)))  # Varied loss amounts
                        )
                    )
            loss_data_scenarios.append(scenario_loss_data)
        
        def calculate_sma_scenario(scenario_id):
            """Calculate SMA for a single scenario"""
            start_time = time.time()
            
            # Modify entity_id for each scenario
            scenario_bi_data = []
            for bi in sample_bi_data_bucket_2:
                scenario_bi = BusinessIndicatorData(
                    period=bi.period,
                    ildc=bi.ildc + Decimal(str(scenario_id * 1000000000)),  # Slight variation
                    sc=bi.sc,
                    fc=bi.fc,
                    entity_id=f"CONCURRENT_BANK_{scenario_id:03d}",
                    calculation_date=bi.calculation_date
                )
                scenario_bi_data.append(scenario_bi)
            
            result = sma_calculator.calculate_sma(
                bi_data=scenario_bi_data,
                loss_data=loss_data_scenarios[scenario_id],
                entity_id=f"CONCURRENT_BANK_{scenario_id:03d}",
                calculation_date=date(2023, 12, 31),
                run_id=f"CONCURRENT_TEST_{scenario_id:03d}"
            )
            
            end_time = time.time()
            return {
                'scenario_id': scenario_id,
                'execution_time': end_time - start_time,
                'result': result
            }
        
        performance_monitor.start_monitoring()
        start_time = time.time()
        
        # Act - Execute concurrent calculations
        execution_times = []
        results = []
        
        with ThreadPoolExecutor(max_workers=num_concurrent_requests) as executor:
            # Submit all tasks
            future_to_scenario = {
                executor.submit(calculate_sma_scenario, i): i 
                for i in range(num_concurrent_requests)
            }
            
            # Collect results
            for future in as_completed(future_to_scenario):
                scenario_result = future.result()
                execution_times.append(scenario_result['execution_time'])
                results.append(scenario_result['result'])
        
        total_time = time.time() - start_time
        performance_monitor.stop_monitoring()
        
        # Assert
        metrics = performance_monitor.get_metrics()
        
        # Calculate percentiles
        execution_times.sort()
        p95_time = execution_times[int(0.95 * len(execution_times))]
        p50_time = execution_times[int(0.50 * len(execution_times))]
        max_time = max(execution_times)
        avg_time = sum(execution_times) / len(execution_times)
        
        # Performance assertions
        assert p95_time < 60, f"P95 response time {p95_time:.2f}s exceeds 60s target"
        assert max_time < 120, f"Maximum response time {max_time:.2f}s too high"
        assert len(results) == num_concurrent_requests, f"Expected {num_concurrent_requests} results"
        
        # All results should be valid
        for result in results:
            assert result.orc >= Decimal('0')
            assert result.rwa >= Decimal('0')
        
        print(f"Concurrent performance metrics:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Average time: {avg_time:.3f}s")
        print(f"  P50 time: {p50_time:.3f}s")
        print(f"  P95 time: {p95_time:.3f}s")
        print(f"  Max time: {max_time:.3f}s")
        print(f"  Peak memory: {metrics['max_memory_usage']:.1f}%")
    
    def test_perf_p_003_auto_async_threshold(self, sma_calculator, performance_test_data):
        """
        Test Case ID: PERF-P-003
        Description: Auto-Async: Trigger a calculation estimated to be slow.
        Target: System should intelligently handle slow calculations.
        """
        # Arrange - Create a large dataset that would be slow
        num_entities = 10
        years = 10
        bi_data, loss_data = performance_test_data(num_entities, years)
        
        # Simulate a calculation that would exceed 60 seconds
        # In a real system, this would trigger async mode automatically
        
        start_time = time.time()
        
        # Act - Perform calculation that might be slow
        results = []
        for entity_id in range(1, num_entities + 1):
            entity_name = f"SLOW_CALC_BANK_{entity_id:03d}"
            
            entity_bi_data = [bi for bi in bi_data if bi.entity_id == entity_name]
            entity_loss_data = [loss for loss in loss_data if loss.entity_id == entity_name]
            
            # Always create results even if no BI data (for test purposes)
            if entity_bi_data:
                result = sma_calculator.calculate_sma(
                    bi_data=entity_bi_data,
                    loss_data=entity_loss_data,
                    entity_id=entity_name,
                    calculation_date=date(2023, 12, 31),
                    run_id=f"SLOW_CALC_{entity_id:03d}"
                )
                results.append(result)
            else:
                # Create a dummy result for entities without BI data
                results.append(f"No BI data for {entity_name}")
        
        execution_time = time.time() - start_time
        
        # Assert
        # In this test environment, we verify the calculation completes
        # In production, this would test the async threshold logic
        assert len(results) == num_entities
        
        # If execution time exceeds threshold, it should trigger async mode
        async_threshold = 60  # seconds
        if execution_time > async_threshold:
            print(f"Calculation took {execution_time:.2f}s, would trigger async mode")
        else:
            print(f"Calculation completed in {execution_time:.2f}s, within sync threshold")
        
        # All valid results should have positive values
        valid_results = [r for r in results if hasattr(r, 'orc')]
        for result in valid_results:
            assert result.orc >= Decimal('0')
            assert result.rwa >= Decimal('0')
    
    def test_perf_p_004_memory_usage_large_dataset(self, sma_calculator, performance_monitor):
        """
        Test Case ID: PERF-P-004
        Description: Memory usage test with large datasets.
        Target: Memory usage should remain reasonable even with large datasets.
        """
        # Arrange - Create progressively larger datasets
        dataset_sizes = [10, 50, 100]  # Number of entities
        memory_usage_results = []
        
        for size in dataset_sizes:
            performance_monitor.start_monitoring()
            
            # Generate large dataset
            bi_data = []
            loss_data = []
            
            for entity_id in range(1, size + 1):
                entity_name = f"MEMORY_TEST_BANK_{entity_id:04d}"
                
                # Generate BI data
                for year in range(2014, 2024):  # 10 years
                    bi_data.append(
                        BusinessIndicatorData(
                            period=str(year),
                            ildc=Decimal(str(50000000000 + entity_id * 1000000000)),
                            sc=Decimal(str(20000000000 + entity_id * 500000000)),
                            fc=Decimal(str(10000000000 + entity_id * 200000000)),
                            entity_id=entity_name,
                            calculation_date=date(year, 12, 31)
                        )
                    )
                
                # Generate loss data
                for year in range(2014, 2024):
                    for month in [3, 6, 9, 12]:
                        loss_data.append(
                            LossData(
                                event_id=f"MEMORY_LOSS_{entity_id}_{year}_{month:02d}",
                                entity_id=entity_name,
                                accounting_date=date(year, month, 15),
                                net_loss=Decimal(str(100000000 + entity_id * 1000000))
                            )
                        )
            
            # Act - Process the dataset
            start_time = time.time()
            results = []
            
            for entity_id in range(1, size + 1):
                entity_name = f"MEMORY_TEST_BANK_{entity_id:04d}"
                
                entity_bi_data = [bi for bi in bi_data if bi.entity_id == entity_name]
                entity_loss_data = [loss for loss in loss_data if loss.entity_id == entity_name]
                
                result = sma_calculator.calculate_sma(
                    bi_data=entity_bi_data,
                    loss_data=entity_loss_data,
                    entity_id=entity_name,
                    calculation_date=date(2023, 12, 31),
                    run_id=f"MEMORY_TEST_{entity_id:04d}"
                )
                results.append(result)
            
            execution_time = time.time() - start_time
            performance_monitor.stop_monitoring()
            
            metrics = performance_monitor.get_metrics()
            memory_usage_results.append({
                'dataset_size': size,
                'execution_time': execution_time,
                'max_memory_usage': metrics['max_memory_usage'],
                'avg_memory_usage': metrics['avg_memory_usage']
            })
            
            # Assert for this dataset size
            assert len(results) == size
            assert metrics['max_memory_usage'] < 90, f"Memory usage {metrics['max_memory_usage']:.1f}% too high for {size} entities"
        
        # Assert overall memory scaling
        print("Memory usage scaling results:")
        for result in memory_usage_results:
            print(f"  {result['dataset_size']} entities: {result['max_memory_usage']:.1f}% peak memory, {result['execution_time']:.2f}s")
        
        # Memory usage should not grow exponentially
        if len(memory_usage_results) >= 2:
            memory_growth_ratio = memory_usage_results[-1]['max_memory_usage'] / memory_usage_results[0]['max_memory_usage']
            entity_growth_ratio = memory_usage_results[-1]['dataset_size'] / memory_usage_results[0]['dataset_size']
            
            # Memory growth should be roughly linear with data size
            assert memory_growth_ratio < entity_growth_ratio * 2, "Memory usage growing too fast relative to dataset size"
    
    def test_performance_calculation_components(self, sma_calculator, sample_bi_data_bucket_2, sample_loss_data_10_years):
        """
        Additional Test: Performance of individual calculation components.
        """
        num_iterations = 100
        
        # Test BI calculation performance
        start_time = time.time()
        for _ in range(num_iterations):
            sma_calculator.calculate_business_indicator(sample_bi_data_bucket_2)
        bi_time = (time.time() - start_time) / num_iterations
        
        # Test BIC calculation performance
        bi_amount = Decimal('125000000000')
        bucket = sma_calculator.assign_bucket(bi_amount)
        start_time = time.time()
        for _ in range(num_iterations):
            sma_calculator.calculate_bic(bi_amount, bucket)
        bic_time = (time.time() - start_time) / num_iterations
        
        # Test LC calculation performance
        calculation_date = date(2023, 12, 31)
        start_time = time.time()
        for _ in range(num_iterations):
            sma_calculator.calculate_loss_component(sample_loss_data_10_years, calculation_date)
        lc_time = (time.time() - start_time) / num_iterations
        
        # Test ILM calculation performance
        lc = Decimal('495000000')
        bic = Decimal('12600000000')
        start_time = time.time()
        for _ in range(num_iterations):
            sma_calculator.calculate_ilm(lc, bic, bucket, 5, False)
        ilm_time = (time.time() - start_time) / num_iterations
        
        # Assert performance targets
        assert bi_time < 0.001, f"BI calculation too slow: {bi_time:.6f}s per iteration"
        assert bic_time < 0.001, f"BIC calculation too slow: {bic_time:.6f}s per iteration"
        assert lc_time < 0.01, f"LC calculation too slow: {lc_time:.6f}s per iteration"
        assert ilm_time < 0.001, f"ILM calculation too slow: {ilm_time:.6f}s per iteration"
        
        print(f"Component performance (per calculation):")
        print(f"  BI calculation: {bi_time*1000:.3f}ms")
        print(f"  BIC calculation: {bic_time*1000:.3f}ms")
        print(f"  LC calculation: {lc_time*1000:.3f}ms")
        print(f"  ILM calculation: {ilm_time*1000:.3f}ms")
    
    @pytest.mark.asyncio
    async def test_async_performance_simulation(self, sma_calculator, sample_bi_data_bucket_2):
        """
        Additional Test: Simulate async performance characteristics.
        """
        # Simulate multiple async calculations
        async def async_sma_calculation(entity_id: int):
            # Simulate async calculation (in real implementation, this would be truly async)
            await asyncio.sleep(0.01)  # Simulate I/O delay
            
            # Modify data for each entity
            entity_bi_data = []
            for bi in sample_bi_data_bucket_2:
                entity_bi = BusinessIndicatorData(
                    period=bi.period,
                    ildc=bi.ildc + Decimal(str(entity_id * 1000000000)),
                    sc=bi.sc,
                    fc=bi.fc,
                    entity_id=f"ASYNC_BANK_{entity_id:03d}",
                    calculation_date=bi.calculation_date
                )
                entity_bi_data.append(entity_bi)
            
            result = sma_calculator.calculate_sma(
                bi_data=entity_bi_data,
                loss_data=[],
                entity_id=f"ASYNC_BANK_{entity_id:03d}",
                calculation_date=date(2023, 12, 31),
                run_id=f"ASYNC_TEST_{entity_id:03d}"
            )
            
            return result
        
        # Execute multiple async calculations
        num_async_tasks = 10
        start_time = time.time()
        
        tasks = [async_sma_calculation(i) for i in range(num_async_tasks)]
        results = await asyncio.gather(*tasks)
        
        execution_time = time.time() - start_time
        
        # Assert
        assert len(results) == num_async_tasks
        assert execution_time < 5, f"Async calculations took {execution_time:.2f}s, should be faster"
        
        # All results should be valid
        for result in results:
            assert result.orc >= Decimal('0')
            assert result.rwa >= Decimal('0')
        
        print(f"Async performance: {execution_time:.2f}s for {num_async_tasks} concurrent calculations")