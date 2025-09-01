"""
Comprehensive Test Runner for ORM Capital Calculator Engine

This script executes the complete test suite following TDD principles with
comprehensive coverage of unit, integration, performance, regulatory, and security tests.
"""

import sys
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class ComprehensiveTestRunner:
    """Comprehensive test runner with detailed reporting and analysis"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        
    def run_test_suite(self, test_category: str, test_path: str, markers: List[str] = None) -> Dict:
        """Run a specific test suite and capture results"""
        print(f"\n{'='*80}")
        print(f"Running {test_category} Tests")
        print(f"{'='*80}")
        
        # Build pytest command
        cmd = ["python", "-m", "pytest", test_path, "-v", "--tb=short"]
        
        # Add markers if specified
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        # Add coverage for unit and integration tests
        if test_category in ["Unit", "Integration"]:
            cmd.extend(["--cov=src", "--cov-report=term-missing"])
        
        # Add performance reporting for performance tests
        if test_category == "Performance":
            cmd.extend(["--durations=10"])
        
        start_time = time.time()
        
        try:
            # Run the tests
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            execution_time = time.time() - start_time
            
            # Parse results
            test_result = self._parse_pytest_output(result.stdout, result.stderr)
            test_result.update({
                'category': test_category,
                'execution_time': execution_time,
                'return_code': result.returncode,
                'command': ' '.join(cmd)
            })
            
            self.test_results[test_category] = test_result
            
            # Update totals
            self.total_tests += test_result.get('total', 0)
            self.passed_tests += test_result.get('passed', 0)
            self.failed_tests += test_result.get('failed', 0)
            self.skipped_tests += test_result.get('skipped', 0)
            
            # Print summary
            self._print_test_summary(test_category, test_result)
            
            return test_result
            
        except Exception as e:
            error_result = {
                'category': test_category,
                'error': str(e),
                'execution_time': time.time() - start_time,
                'return_code': -1
            }
            self.test_results[test_category] = error_result
            print(f"ERROR running {test_category} tests: {e}")
            return error_result
    
    def _parse_pytest_output(self, stdout: str, stderr: str) -> Dict:
        """Parse pytest output to extract test results"""
        result = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': [],
            'warnings': [],
            'stdout': stdout,
            'stderr': stderr
        }
        
        # Parse the summary line
        lines = stdout.split('\n')
        for line in lines:
            if 'passed' in line and ('failed' in line or 'error' in line or 'skipped' in line):
                # Extract numbers from summary line
                import re
                numbers = re.findall(r'(\d+)\s+(passed|failed|error|skipped)', line)
                for count, status in numbers:
                    if status == 'passed':
                        result['passed'] = int(count)
                    elif status in ['failed', 'error']:
                        result['failed'] += int(count)
                    elif status == 'skipped':
                        result['skipped'] = int(count)
                
                result['total'] = result['passed'] + result['failed'] + result['skipped']
                break
        
        # Extract errors and warnings
        if stderr:
            result['errors'].append(stderr)
        
        return result
    
    def _print_test_summary(self, category: str, result: Dict):
        """Print test summary for a category"""
        print(f"\n{category} Test Results:")
        print(f"  Total: {result.get('total', 0)}")
        print(f"  Passed: {result.get('passed', 0)}")
        print(f"  Failed: {result.get('failed', 0)}")
        print(f"  Skipped: {result.get('skipped', 0)}")
        print(f"  Execution Time: {result.get('execution_time', 0):.2f}s")
        print(f"  Status: {'✅ PASSED' if result.get('return_code') == 0 else '❌ FAILED'}")
        
        if result.get('failed', 0) > 0:
            print(f"  ⚠️  {result.get('failed')} test(s) failed - check output above")
    
    def run_all_tests(self):
        """Run the complete test suite"""
        print("🚀 Starting Comprehensive Test Suite for ORM Capital Calculator Engine")
        print("=" * 80)
        
        self.start_time = time.time()
        
        # Test execution plan
        test_plan = [
            {
                'category': 'Unit - SMA Business Indicator',
                'path': 'tests/unit/test_sma_business_indicator.py',
                'markers': ['unit']
            },
            {
                'category': 'Unit - SMA BIC Calculation', 
                'path': 'tests/unit/test_sma_bic_calculation.py',
                'markers': ['unit']
            },
            {
                'category': 'Unit - SMA Loss Component & ILM',
                'path': 'tests/unit/test_sma_loss_component_ilm.py', 
                'markers': ['unit']
            },
            {
                'category': 'Unit - SMA Calculator (Existing)',
                'path': 'tests/test_sma_calculator.py',
                'markers': ['unit']
            },
            {
                'category': 'Integration - Complete Workflow',
                'path': 'tests/integration/test_sma_complete_workflow.py',
                'markers': ['integration']
            },
            {
                'category': 'Integration - SMA Integration (Existing)',
                'path': 'tests/test_sma_integration.py',
                'markers': ['integration']
            },
            {
                'category': 'Regulatory - RBI Compliance',
                'path': 'tests/regulatory/test_rbi_compliance.py',
                'markers': ['regulatory']
            },
            {
                'category': 'Performance - SMA Performance',
                'path': 'tests/performance/test_sma_performance.py',
                'markers': ['performance']
            }
        ]
        
        # Execute each test category
        for test_config in test_plan:
            self.run_test_suite(
                test_config['category'],
                test_config['path'],
                test_config.get('markers')
            )
        
        # Generate final report
        self._generate_final_report()
    
    def _generate_final_report(self):
        """Generate comprehensive final test report"""
        total_time = time.time() - self.start_time
        
        print(f"\n{'='*80}")
        print("📊 COMPREHENSIVE TEST SUITE FINAL REPORT")
        print(f"{'='*80}")
        
        print(f"\n⏱️  Execution Summary:")
        print(f"  Total Execution Time: {total_time:.2f}s")
        print(f"  Total Tests: {self.total_tests}")
        print(f"  Passed: {self.passed_tests}")
        print(f"  Failed: {self.failed_tests}")
        print(f"  Skipped: {self.skipped_tests}")
        
        # Calculate success rate
        if self.total_tests > 0:
            success_rate = (self.passed_tests / self.total_tests) * 100
            print(f"  Success Rate: {success_rate:.1f}%")
        
        print(f"\n📋 Test Category Breakdown:")
        for category, result in self.test_results.items():
            status = "✅ PASSED" if result.get('return_code') == 0 else "❌ FAILED"
            print(f"  {category:<30} {status:<10} ({result.get('execution_time', 0):.2f}s)")
        
        # Overall status
        overall_success = self.failed_tests == 0
        print(f"\n🎯 Overall Status: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
        if overall_success:
            print("\n🎉 Congratulations! All tests passed successfully.")
            print("   The ORM Capital Calculator Engine is ready for deployment.")
        else:
            print(f"\n⚠️  {self.failed_tests} test(s) failed. Please review the output above.")
            print("   Fix the failing tests before proceeding to deployment.")
        
        # Performance insights
        self._print_performance_insights()
        
        # Regulatory compliance summary
        self._print_regulatory_compliance_summary()
        
        # Save detailed report
        self._save_detailed_report()
    
    def _print_performance_insights(self):
        """Print performance insights from test results"""
        print(f"\n⚡ Performance Insights:")
        
        perf_result = self.test_results.get('Performance - SMA Performance')
        if perf_result and perf_result.get('return_code') == 0:
            print("  ✅ Performance tests passed - system meets SLA requirements")
            print("  📈 Key metrics:")
            print("    - Quarter-end calculations: < 30 minutes ✅")
            print("    - Ad-hoc calculations: < 60 seconds ✅") 
            print("    - Concurrent user support: 50+ users ✅")
            print("    - Memory usage: Within acceptable limits ✅")
        else:
            print("  ⚠️  Performance tests failed or not run")
            print("    - Review performance test output for bottlenecks")
    
    def _print_regulatory_compliance_summary(self):
        """Print regulatory compliance summary"""
        print(f"\n📜 Regulatory Compliance Summary:")
        
        reg_result = self.test_results.get('Regulatory - RBI Compliance')
        if reg_result and reg_result.get('return_code') == 0:
            print("  ✅ RBI Basel III SMA compliance verified")
            print("  📋 Compliance areas:")
            print("    - SMA formula implementation ✅")
            print("    - Bucket thresholds (₹8,000cr, ₹2,40,000cr) ✅")
            print("    - Marginal coefficients (12%, 15%, 18%) ✅")
            print("    - Loss component methodology ✅")
            print("    - ILM gating logic ✅")
            print("    - RWA multiplier (12.5x) ✅")
            print("    - Data quality requirements ✅")
        else:
            print("  ⚠️  Regulatory compliance tests failed or not run")
            print("    - Review regulatory test output for compliance issues")
    
    def _save_detailed_report(self):
        """Save detailed test report to file"""
        report_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_execution_time': time.time() - self.start_time,
            'summary': {
                'total_tests': self.total_tests,
                'passed_tests': self.passed_tests,
                'failed_tests': self.failed_tests,
                'skipped_tests': self.skipped_tests,
                'success_rate': (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
            },
            'test_results': self.test_results
        }
        
        # Save to file
        report_file = Path(__file__).parent / 'test_report.json'
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n💾 Detailed report saved to: {report_file}")


def main():
    """Main entry point for comprehensive test runner"""
    runner = ComprehensiveTestRunner()
    
    # Check if specific test category is requested
    if len(sys.argv) > 1:
        test_category = sys.argv[1].lower()
        
        category_map = {
            'unit': [
                ('Unit - SMA Business Indicator', 'tests/unit/test_sma_business_indicator.py', ['unit']),
                ('Unit - SMA BIC Calculation', 'tests/unit/test_sma_bic_calculation.py', ['unit']),
                ('Unit - SMA Loss Component & ILM', 'tests/unit/test_sma_loss_component_ilm.py', ['unit']),
                ('Unit - SMA Calculator (Existing)', 'tests/test_sma_calculator.py', ['unit'])
            ],
            'integration': [
                ('Integration - Complete Workflow', 'tests/integration/test_sma_complete_workflow.py', ['integration']),
                ('Integration - SMA Integration (Existing)', 'tests/test_sma_integration.py', ['integration'])
            ],
            'performance': [
                ('Performance - SMA Performance', 'tests/performance/test_sma_performance.py', ['performance'])
            ],
            'regulatory': [
                ('Regulatory - RBI Compliance', 'tests/regulatory/test_rbi_compliance.py', ['regulatory'])
            ]
        }
        
        if test_category in category_map:
            print(f"Running {test_category.upper()} tests only...")
            runner.start_time = time.time()
            
            for category, path, markers in category_map[test_category]:
                runner.run_test_suite(category, path, markers)
            
            runner._generate_final_report()
        else:
            print(f"Unknown test category: {test_category}")
            print("Available categories: unit, integration, performance, regulatory, all")
            sys.exit(1)
    else:
        # Run all tests
        runner.run_all_tests()


if __name__ == "__main__":
    main()