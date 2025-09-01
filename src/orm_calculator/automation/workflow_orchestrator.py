"""
Automated Development Workflow Orchestrator

Orchestrates continuous development iteration with automated feedback loops.
Implements red-green-refactor cycles and continuous improvement.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from .code_analyzer import CodeAnalyzer
from .test_automation import TestAutomation
from .failure_analyzer import FailureAnalyzer
from .code_generator import CodeGenerator
from .refactoring_engine import RefactoringEngine
from .performance_profiler import PerformanceProfiler
from .metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """Development workflow states"""
    IDLE = "idle"
    ANALYZING = "analyzing"
    TESTING = "testing"
    GENERATING = "generating"
    REFACTORING = "refactoring"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


class IterationPhase(Enum):
    """TDD iteration phases"""
    RED = "red"      # Write failing test
    GREEN = "green"  # Make test pass
    REFACTOR = "refactor"  # Improve code quality


@dataclass
class WorkflowConfig:
    """Configuration for automated workflow"""
    max_iterations: int = 100
    iteration_timeout: timedelta = field(default_factory=lambda: timedelta(minutes=30))
    quality_threshold: float = 0.85
    test_coverage_threshold: float = 0.95
    performance_threshold: float = 1.0  # seconds
    auto_fix_enabled: bool = True
    auto_refactor_enabled: bool = True
    continuous_mode: bool = True
    notification_webhooks: List[str] = field(default_factory=list)


@dataclass
class IterationResult:
    """Result of a development iteration"""
    iteration_id: str
    phase: IterationPhase
    state: WorkflowState
    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = False
    tests_passed: int = 0
    tests_failed: int = 0
    code_quality_score: float = 0.0
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    changes_made: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class WorkflowOrchestrator:
    """
    Orchestrates automated development workflow with continuous iteration
    """
    
    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.state = WorkflowState.IDLE
        self.current_iteration = 0
        self.iteration_history: List[IterationResult] = []
        
        # Initialize automation components
        self.code_analyzer = CodeAnalyzer()
        self.test_automation = TestAutomation()
        self.failure_analyzer = FailureAnalyzer()
        self.code_generator = CodeGenerator()
        self.refactoring_engine = RefactoringEngine()
        self.performance_profiler = PerformanceProfiler()
        self.metrics_collector = MetricsCollector()
        
        # Workflow callbacks
        self.callbacks: Dict[str, List[Callable]] = {
            'iteration_start': [],
            'iteration_complete': [],
            'phase_change': [],
            'error_detected': [],
            'quality_gate_failed': [],
            'workflow_complete': []
        }
    
    async def start_continuous_iteration(self, requirements: List[str]) -> None:
        """
        Start continuous development iteration process
        
        Args:
            requirements: List of requirements to implement
        """
        logger.info("Starting continuous development iteration")
        self.state = WorkflowState.ANALYZING
        
        try:
            while self.current_iteration < self.config.max_iterations:
                iteration_result = await self._execute_iteration(requirements)
                self.iteration_history.append(iteration_result)
                
                # Check completion criteria
                if await self._check_completion_criteria():
                    logger.info("All requirements completed successfully")
                    self.state = WorkflowState.COMPLETED
                    await self._notify_callbacks('workflow_complete', iteration_result)
                    break
                
                # Check if we should continue
                if not self.config.continuous_mode:
                    break
                
                # Brief pause between iterations
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            self.state = WorkflowState.FAILED
            await self._notify_callbacks('error_detected', {'error': str(e)})
    
    async def _execute_iteration(self, requirements: List[str]) -> IterationResult:
        """Execute a single development iteration"""
        iteration_id = f"iter_{self.current_iteration:04d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = IterationResult(
            iteration_id=iteration_id,
            phase=IterationPhase.RED,
            state=self.state,
            start_time=datetime.now()
        )
        
        logger.info(f"Starting iteration {iteration_id}")
        await self._notify_callbacks('iteration_start', result)
        
        try:
            # Phase 1: RED - Write failing tests
            await self._execute_red_phase(result, requirements)
            
            # Phase 2: GREEN - Make tests pass
            await self._execute_green_phase(result, requirements)
            
            # Phase 3: REFACTOR - Improve code quality
            if self.config.auto_refactor_enabled:
                await self._execute_refactor_phase(result)
            
            # Validate iteration results
            await self._validate_iteration(result)
            
            result.success = True
            result.end_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Iteration {iteration_id} failed: {e}")
            result.errors.append(str(e))
            result.success = False
            result.end_time = datetime.now()
            
            # Attempt automated failure recovery
            if self.config.auto_fix_enabled:
                await self._attempt_failure_recovery(result, e)
        
        self.current_iteration += 1
        await self._notify_callbacks('iteration_complete', result)
        return result
    
    async def _execute_red_phase(self, result: IterationResult, requirements: List[str]) -> None:
        """Execute RED phase - write failing tests"""
        result.phase = IterationPhase.RED
        await self._notify_callbacks('phase_change', result)
        
        logger.info("Executing RED phase - generating failing tests")
        
        # Analyze current code state
        code_analysis = await self.code_analyzer.analyze_codebase()
        
        # Generate tests for unimplemented requirements
        missing_tests = await self.test_automation.identify_missing_tests(requirements, code_analysis)
        
        for test_spec in missing_tests:
            test_code = await self.code_generator.generate_test_code(test_spec)
            test_file = await self.test_automation.create_test_file(test_code)
            result.changes_made.append(f"Generated test: {test_file}")
        
        # Run tests to ensure they fail (RED)
        test_results = await self.test_automation.run_tests()
        result.tests_failed = test_results.failed_count
        
        if test_results.failed_count == 0:
            result.recommendations.append("No failing tests generated - may need more specific requirements")
    
    async def _execute_green_phase(self, result: IterationResult, requirements: List[str]) -> None:
        """Execute GREEN phase - make tests pass"""
        result.phase = IterationPhase.GREEN
        await self._notify_callbacks('phase_change', result)
        
        logger.info("Executing GREEN phase - implementing code to pass tests")
        
        # Run tests to identify failures
        test_results = await self.test_automation.run_tests()
        
        # Generate code to make tests pass
        for failure in test_results.failures:
            # Analyze failure and generate fix
            fix_analysis = await self.failure_analyzer.analyze_test_failure(failure)
            
            if fix_analysis.auto_fixable:
                code_fix = await self.code_generator.generate_implementation_code(
                    failure.test_name,
                    failure.error_message,
                    requirements
                )
                
                # Apply the fix
                await self.code_generator.apply_code_changes(code_fix)
                result.changes_made.append(f"Implemented: {code_fix.description}")
        
        # Verify tests now pass
        final_test_results = await self.test_automation.run_tests()
        result.tests_passed = final_test_results.passed_count
        result.tests_failed = final_test_results.failed_count
        
        if final_test_results.failed_count > 0:
            result.recommendations.append("Some tests still failing - may need manual intervention")
    
    async def _execute_refactor_phase(self, result: IterationResult) -> None:
        """Execute REFACTOR phase - improve code quality"""
        result.phase = IterationPhase.REFACTOR
        await self._notify_callbacks('phase_change', result)
        
        logger.info("Executing REFACTOR phase - improving code quality")
        
        # Analyze code quality
        quality_analysis = await self.code_analyzer.analyze_code_quality()
        result.code_quality_score = quality_analysis.overall_score
        
        if quality_analysis.overall_score < self.config.quality_threshold:
            # Apply automated refactoring
            refactoring_suggestions = await self.refactoring_engine.analyze_refactoring_opportunities()
            
            for suggestion in refactoring_suggestions:
                if suggestion.safety_score > 0.8:  # Only apply safe refactorings
                    await self.refactoring_engine.apply_refactoring(suggestion)
                    result.changes_made.append(f"Refactored: {suggestion.description}")
            
            # Re-run tests to ensure refactoring didn't break anything
            test_results = await self.test_automation.run_tests()
            if test_results.failed_count > 0:
                # Rollback refactoring if tests fail
                await self.refactoring_engine.rollback_last_refactoring()
                result.recommendations.append("Refactoring rolled back due to test failures")
    
    async def _validate_iteration(self, result: IterationResult) -> None:
        """Validate iteration meets quality gates"""
        logger.info("Validating iteration against quality gates")
        
        # Check test coverage
        coverage = await self.test_automation.get_test_coverage()
        if coverage < self.config.test_coverage_threshold:
            result.recommendations.append(f"Test coverage {coverage:.2%} below threshold {self.config.test_coverage_threshold:.2%}")
        
        # Check performance
        performance_metrics = await self.performance_profiler.profile_critical_paths()
        result.performance_metrics = performance_metrics
        
        for metric_name, value in performance_metrics.items():
            if value > self.config.performance_threshold:
                result.recommendations.append(f"Performance metric {metric_name} ({value:.2f}s) exceeds threshold")
        
        # Check code quality
        if result.code_quality_score < self.config.quality_threshold:
            await self._notify_callbacks('quality_gate_failed', result)
    
    async def _check_completion_criteria(self) -> bool:
        """Check if all requirements are completed"""
        if not self.iteration_history:
            return False
        
        latest_result = self.iteration_history[-1]
        
        # All tests passing
        if latest_result.tests_failed > 0:
            return False
        
        # Quality threshold met
        if latest_result.code_quality_score < self.config.quality_threshold:
            return False
        
        # Performance threshold met
        for value in latest_result.performance_metrics.values():
            if value > self.config.performance_threshold:
                return False
        
        # No critical recommendations
        critical_recommendations = [r for r in latest_result.recommendations if 'critical' in r.lower()]
        if critical_recommendations:
            return False
        
        return True
    
    async def _attempt_failure_recovery(self, result: IterationResult, error: Exception) -> None:
        """Attempt automated failure recovery"""
        logger.info(f"Attempting automated recovery for error: {error}")
        
        # Analyze the failure
        recovery_plan = await self.failure_analyzer.generate_recovery_plan(error, result)
        
        if recovery_plan.auto_recoverable:
            for action in recovery_plan.recovery_actions:
                try:
                    await self._execute_recovery_action(action)
                    result.changes_made.append(f"Recovery: {action.description}")
                except Exception as recovery_error:
                    logger.error(f"Recovery action failed: {recovery_error}")
                    result.errors.append(f"Recovery failed: {recovery_error}")
    
    async def _execute_recovery_action(self, action) -> None:
        """Execute a specific recovery action"""
        if action.type == "rollback":
            await self.refactoring_engine.rollback_last_changes()
        elif action.type == "fix_syntax":
            await self.code_generator.fix_syntax_errors()
        elif action.type == "update_dependencies":
            await self.dependency_manager.update_dependencies()
        # Add more recovery actions as needed
    
    def register_callback(self, event: str, callback: Callable) -> None:
        """Register callback for workflow events"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    async def _notify_callbacks(self, event: str, data: Any) -> None:
        """Notify registered callbacks"""
        for callback in self.callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")
    
    def get_iteration_metrics(self) -> Dict[str, Any]:
        """Get comprehensive iteration metrics"""
        if not self.iteration_history:
            return {}
        
        total_iterations = len(self.iteration_history)
        successful_iterations = sum(1 for r in self.iteration_history if r.success)
        
        return {
            'total_iterations': total_iterations,
            'successful_iterations': successful_iterations,
            'success_rate': successful_iterations / total_iterations if total_iterations > 0 else 0,
            'average_quality_score': sum(r.code_quality_score for r in self.iteration_history) / total_iterations,
            'total_tests_generated': sum(r.tests_passed + r.tests_failed for r in self.iteration_history),
            'total_changes_made': sum(len(r.changes_made) for r in self.iteration_history),
            'current_state': self.state.value,
            'completion_percentage': self._calculate_completion_percentage()
        }
    
    def _calculate_completion_percentage(self) -> float:
        """Calculate overall completion percentage"""
        if not self.iteration_history:
            return 0.0
        
        latest_result = self.iteration_history[-1]
        
        # Weight different factors
        test_factor = 0.4
        quality_factor = 0.3
        performance_factor = 0.3
        
        test_score = latest_result.tests_passed / max(1, latest_result.tests_passed + latest_result.tests_failed)
        quality_score = latest_result.code_quality_score
        performance_score = 1.0 - min(1.0, max(0.0, sum(latest_result.performance_metrics.values()) / len(latest_result.performance_metrics) if latest_result.performance_metrics else 0))
        
        return (test_factor * test_score + quality_factor * quality_score + performance_factor * performance_score) * 100
    
    async def export_iteration_report(self, output_path: Path) -> None:
        """Export detailed iteration report"""
        report = {
            'workflow_config': {
                'max_iterations': self.config.max_iterations,
                'quality_threshold': self.config.quality_threshold,
                'test_coverage_threshold': self.config.test_coverage_threshold,
                'performance_threshold': self.config.performance_threshold
            },
            'summary': self.get_iteration_metrics(),
            'iterations': [
                {
                    'iteration_id': r.iteration_id,
                    'phase': r.phase.value,
                    'state': r.state.value,
                    'duration': (r.end_time - r.start_time).total_seconds() if r.end_time else None,
                    'success': r.success,
                    'tests_passed': r.tests_passed,
                    'tests_failed': r.tests_failed,
                    'code_quality_score': r.code_quality_score,
                    'performance_metrics': r.performance_metrics,
                    'changes_made': r.changes_made,
                    'errors': r.errors,
                    'recommendations': r.recommendations
                }
                for r in self.iteration_history
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Iteration report exported to {output_path}")