"""
Concurrent processing utilities for ORM Capital Calculator Engine

Provides asyncio-based concurrent processing for independent calculations,
task groups, and parallel execution with proper error handling and resource management.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Callable, Awaitable, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import functools

from orm_calculator.core.performance import get_performance_monitor


T = TypeVar('T')
R = TypeVar('R')


class ExecutionMode(str, Enum):
    """Execution modes for concurrent processing"""
    ASYNC = "async"
    THREAD = "thread"
    PROCESS = "process"


@dataclass
class TaskResult(Generic[T]):
    """Result of a concurrent task execution"""
    task_id: str
    result: Optional[T] = None
    error: Optional[Exception] = None
    duration: float = 0.0
    success: bool = False


@dataclass
class ConcurrentConfig:
    """Configuration for concurrent processing"""
    max_concurrent_tasks: int = 10
    max_thread_workers: int = 4
    max_process_workers: int = 2
    timeout_seconds: Optional[float] = None
    retry_attempts: int = 0
    retry_delay: float = 1.0


class TaskGroup:
    """Manages a group of concurrent tasks with proper resource management"""
    
    def __init__(self, config: Optional[ConcurrentConfig] = None):
        self.config = config or ConcurrentConfig()
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)
        self.thread_executor = ThreadPoolExecutor(max_workers=self.config.max_thread_workers)
        self.process_executor = ProcessPoolExecutor(max_workers=self.config.max_process_workers)
        self.performance_monitor = get_performance_monitor()
        self._tasks: List[asyncio.Task] = []
        self._results: Dict[str, TaskResult] = {}
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup"""
        await self.cleanup()
    
    async def add_async_task(self, task_id: str, coro: Awaitable[T]) -> None:
        """Add an async task to the group"""
        task = asyncio.create_task(self._execute_async_task(task_id, coro))
        self._tasks.append(task)
    
    async def add_sync_task(self, task_id: str, func: Callable[[], T], 
                          execution_mode: ExecutionMode = ExecutionMode.THREAD) -> None:
        """Add a synchronous task to the group"""
        if execution_mode == ExecutionMode.THREAD:
            task = asyncio.create_task(self._execute_thread_task(task_id, func))
        elif execution_mode == ExecutionMode.PROCESS:
            task = asyncio.create_task(self._execute_process_task(task_id, func))
        else:
            # Convert to async
            async def async_wrapper():
                return func()
            task = asyncio.create_task(self._execute_async_task(task_id, async_wrapper()))
        
        self._tasks.append(task)
    
    async def add_calculation_task(self, task_id: str, calculation_func: Callable[[], T],
                                 entity_id: str, model_name: str) -> None:
        """Add a calculation task with performance monitoring"""
        async def monitored_calculation():
            start_time = time.perf_counter()
            try:
                if asyncio.iscoroutinefunction(calculation_func):
                    result = await calculation_func()
                else:
                    result = calculation_func()
                
                duration = time.perf_counter() - start_time
                self.performance_monitor.record_calculation(model_name, entity_id, duration, True)
                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                self.performance_monitor.record_calculation(model_name, entity_id, duration, False)
                raise
        
        await self.add_async_task(task_id, monitored_calculation())
    
    async def wait_all(self, return_when: str = "ALL_COMPLETED") -> Dict[str, TaskResult[T]]:
        """Wait for all tasks to complete"""
        if not self._tasks:
            return self._results
        
        try:
            if self.config.timeout_seconds:
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks, return_exceptions=True),
                    timeout=self.config.timeout_seconds
                )
            else:
                await asyncio.gather(*self._tasks, return_exceptions=True)
        except asyncio.TimeoutError:
            # Cancel remaining tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for cancellation to complete
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        return self._results
    
    async def wait_first_completed(self) -> Optional[TaskResult[T]]:
        """Wait for the first task to complete"""
        if not self._tasks:
            return None
        
        done, pending = await asyncio.wait(self._tasks, return_when=asyncio.FIRST_COMPLETED)
        
        # Get result from first completed task
        for task in done:
            task_id = getattr(task, '_task_id', 'unknown')
            if task_id in self._results:
                return self._results[task_id]
        
        return None
    
    async def get_completed_results(self) -> Dict[str, TaskResult[T]]:
        """Get results from completed tasks without waiting"""
        completed_results = {}
        
        for task in self._tasks:
            if task.done():
                task_id = getattr(task, '_task_id', 'unknown')
                if task_id in self._results:
                    completed_results[task_id] = self._results[task_id]
        
        return completed_results
    
    async def cancel_all(self) -> None:
        """Cancel all pending tasks"""
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Wait for cancellation to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        await self.cancel_all()
        
        if self.thread_executor:
            self.thread_executor.shutdown(wait=True)
        
        if self.process_executor:
            self.process_executor.shutdown(wait=True)
    
    async def _execute_async_task(self, task_id: str, coro: Awaitable[T]) -> None:
        """Execute an async task with error handling and monitoring"""
        async with self.semaphore:
            start_time = time.perf_counter()
            
            try:
                result = await self._retry_task(coro)
                duration = time.perf_counter() - start_time
                
                self._results[task_id] = TaskResult(
                    task_id=task_id,
                    result=result,
                    duration=duration,
                    success=True
                )
            except Exception as e:
                duration = time.perf_counter() - start_time
                
                self._results[task_id] = TaskResult(
                    task_id=task_id,
                    error=e,
                    duration=duration,
                    success=False
                )
    
    async def _execute_thread_task(self, task_id: str, func: Callable[[], T]) -> None:
        """Execute a task in a thread pool"""
        async with self.semaphore:
            start_time = time.perf_counter()
            
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(self.thread_executor, func)
                duration = time.perf_counter() - start_time
                
                self._results[task_id] = TaskResult(
                    task_id=task_id,
                    result=result,
                    duration=duration,
                    success=True
                )
            except Exception as e:
                duration = time.perf_counter() - start_time
                
                self._results[task_id] = TaskResult(
                    task_id=task_id,
                    error=e,
                    duration=duration,
                    success=False
                )
    
    async def _execute_process_task(self, task_id: str, func: Callable[[], T]) -> None:
        """Execute a task in a process pool"""
        async with self.semaphore:
            start_time = time.perf_counter()
            
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(self.process_executor, func)
                duration = time.perf_counter() - start_time
                
                self._results[task_id] = TaskResult(
                    task_id=task_id,
                    result=result,
                    duration=duration,
                    success=True
                )
            except Exception as e:
                duration = time.perf_counter() - start_time
                
                self._results[task_id] = TaskResult(
                    task_id=task_id,
                    error=e,
                    duration=duration,
                    success=False
                )
    
    async def _retry_task(self, coro: Awaitable[T]) -> T:
        """Retry a task with exponential backoff"""
        last_exception = None
        
        for attempt in range(self.config.retry_attempts + 1):
            try:
                return await coro
            except Exception as e:
                last_exception = e
                
                if attempt < self.config.retry_attempts:
                    delay = self.config.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    raise last_exception
        
        raise last_exception


class CalculationBatch:
    """Manages batch processing of calculations with load balancing"""
    
    def __init__(self, config: Optional[ConcurrentConfig] = None):
        self.config = config or ConcurrentConfig()
        self.performance_monitor = get_performance_monitor()
    
    async def process_entity_calculations(self, entities: List[str], 
                                        calculation_func: Callable[[str], Awaitable[T]],
                                        model_name: str) -> Dict[str, TaskResult[T]]:
        """Process calculations for multiple entities concurrently"""
        async with TaskGroup(self.config) as task_group:
            for entity_id in entities:
                task_id = f"{model_name}_{entity_id}"
                
                # Create calculation wrapper
                async def entity_calculation(eid=entity_id):
                    return await calculation_func(eid)
                
                await task_group.add_calculation_task(
                    task_id, entity_calculation, entity_id, model_name
                )
            
            return await task_group.wait_all()
    
    async def process_date_range_calculations(self, entity_id: str, dates: List[str],
                                            calculation_func: Callable[[str, str], Awaitable[T]],
                                            model_name: str) -> Dict[str, TaskResult[T]]:
        """Process calculations for multiple dates concurrently"""
        async with TaskGroup(self.config) as task_group:
            for calc_date in dates:
                task_id = f"{model_name}_{entity_id}_{calc_date}"
                
                # Create calculation wrapper
                async def date_calculation(date=calc_date):
                    return await calculation_func(entity_id, date)
                
                await task_group.add_calculation_task(
                    task_id, date_calculation, entity_id, model_name
                )
            
            return await task_group.wait_all()
    
    async def process_model_comparisons(self, entity_id: str, calculation_date: str,
                                      model_calculations: Dict[str, Callable[[], Awaitable[T]]]) -> Dict[str, TaskResult[T]]:
        """Process multiple model calculations concurrently for comparison"""
        async with TaskGroup(self.config) as task_group:
            for model_name, calc_func in model_calculations.items():
                task_id = f"{model_name}_{entity_id}_{calculation_date}"
                
                await task_group.add_calculation_task(
                    task_id, calc_func, entity_id, model_name
                )
            
            return await task_group.wait_all()


class ParallelDataProcessor:
    """Processes large datasets in parallel chunks"""
    
    def __init__(self, chunk_size: int = 1000, max_concurrent: int = 5):
        self.chunk_size = chunk_size
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_data_chunks(self, data: List[T], 
                                processor_func: Callable[[List[T]], Awaitable[R]]) -> List[R]:
        """Process data in parallel chunks"""
        chunks = [data[i:i + self.chunk_size] for i in range(0, len(data), self.chunk_size)]
        
        async def process_chunk(chunk: List[T]) -> R:
            async with self.semaphore:
                return await processor_func(chunk)
        
        tasks = [process_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return successful results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        return successful_results
    
    async def process_with_progress(self, data: List[T], 
                                  processor_func: Callable[[List[T]], Awaitable[R]],
                                  progress_callback: Optional[Callable[[int, int], None]] = None) -> List[R]:
        """Process data with progress tracking"""
        chunks = [data[i:i + self.chunk_size] for i in range(0, len(data), self.chunk_size)]
        results = []
        completed = 0
        
        async def process_chunk_with_progress(chunk: List[T]) -> R:
            nonlocal completed
            async with self.semaphore:
                result = await processor_func(chunk)
                completed += 1
                
                if progress_callback:
                    progress_callback(completed, len(chunks))
                
                return result
        
        # Process chunks in batches to avoid overwhelming the system
        for i in range(0, len(chunks), self.max_concurrent):
            batch_chunks = chunks[i:i + self.max_concurrent]
            batch_tasks = [process_chunk_with_progress(chunk) for chunk in batch_chunks]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Add successful results
            successful_batch_results = [r for r in batch_results if not isinstance(r, Exception)]
            results.extend(successful_batch_results)
        
        return results


# Utility functions for common concurrent operations

async def run_calculations_concurrently(calculations: Dict[str, Callable[[], Awaitable[T]]],
                                      max_concurrent: int = 10) -> Dict[str, TaskResult[T]]:
    """Run multiple calculations concurrently"""
    config = ConcurrentConfig(max_concurrent_tasks=max_concurrent)
    
    async with TaskGroup(config) as task_group:
        for calc_id, calc_func in calculations.items():
            await task_group.add_async_task(calc_id, calc_func())
        
        return await task_group.wait_all()


async def run_with_timeout(coro: Awaitable[T], timeout_seconds: float) -> T:
    """Run a coroutine with timeout"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")


def concurrent_calculation(max_concurrent: int = 10, timeout: Optional[float] = None):
    """Decorator for making calculations concurrent"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if timeout:
                return await run_with_timeout(func(*args, **kwargs), timeout)
            else:
                return await func(*args, **kwargs)
        return wrapper
    return decorator


# Global instances
_calculation_batch: Optional[CalculationBatch] = None
_data_processor: Optional[ParallelDataProcessor] = None


def get_calculation_batch(config: Optional[ConcurrentConfig] = None) -> CalculationBatch:
    """Get calculation batch processor instance"""
    global _calculation_batch
    if _calculation_batch is None:
        _calculation_batch = CalculationBatch(config)
    return _calculation_batch


def get_data_processor(chunk_size: int = 1000, max_concurrent: int = 5) -> ParallelDataProcessor:
    """Get parallel data processor instance"""
    global _data_processor
    if _data_processor is None:
        _data_processor = ParallelDataProcessor(chunk_size, max_concurrent)
    return _data_processor