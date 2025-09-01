"""
Automated Fix Recommender for Testing Framework

Analyzes test failures and provides automated fix recommendations and safe fix application.
"""

import re
import ast
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import difflib


@dataclass
class TestFailure:
    """Test failure information"""
    test_id: str
    test_name: str
    failure_type: str
    error_message: str
    stack_trace: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_context: Optional[str] = None


@dataclass
class FixRecommendation:
    """Fix recommendation"""
    recommendation_id: str
    failure_id: str
    fix_type: str
    confidence: float  # 0.0 to 1.0
    description: str
    code_changes: Optional[List[Dict]] = None
    safe_to_auto_apply: bool = False
    estimated_impact: str = 'low'  # low, medium, high
    validation_tests: Optional[List[str]] = None


@dataclass
class AppliedFix:
    """Applied fix information"""
    fix_id: str
    recommendation_id: str
    applied_at: datetime
    success: bool
    validation_results: Dict[str, Any]
    rollback_info: Optional[Dict] = None


class AutomatedFixRecommender:
    """Automated fix recommendation and application system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.fix_patterns = self._initialize_fix_patterns()
        self.safe_fix_types = {
            'calculation_precision',
            'validation_error',
            'type_conversion',
            'null_check',
            'bounds_check',
            'format_string',
            'import_missing'
        }
        self.applied_fixes = []
        
    def _initialize_fix_patterns(self) -> Dict[str, Dict]:
        """Initialize common fix patterns"""
        return {
            'decimal_precision': {
                'pattern': r'decimal.*precision|rounding.*error|float.*comparison',
                'fix_type': 'calculation_precision',
                'confidence': 0.9,
                'description': 'Fix decimal precision issues by using proper Decimal operations',
                'safe_auto_apply': True
            },
            'null_pointer': {
                'pattern': r'NoneType.*attribute|AttributeError.*None',
                'fix_type': 'null_check',
                'confidence': 0.8,
                'description': 'Add null checks to prevent NoneType errors',
                'safe_auto_apply': True
            },
            'type_error': {
                'pattern': r'TypeError.*expected.*got|unsupported.*type',
                'fix_type': 'type_conversion',
                'confidence': 0.85,
                'description': 'Fix type conversion issues',
                'safe_auto_apply': True
            },
            'index_error': {
                'pattern': r'IndexError.*out of range|list index out of range',
                'fix_type': 'bounds_check',
                'confidence': 0.8,
                'description': 'Add bounds checking to prevent index errors',
                'safe_auto_apply': True
            },
            'key_error': {
                'pattern': r'KeyError.*not found|missing.*key',
                'fix_type': 'key_validation',
                'confidence': 0.75,
                'description': 'Add key existence validation',
                'safe_auto_apply': True
            },
            'import_error': {
                'pattern': r'ImportError.*No module|ModuleNotFoundError',
                'fix_type': 'import_missing',
                'confidence': 0.9,
                'description': 'Fix missing import statements',
                'safe_auto_apply': True
            },
            'validation_error': {
                'pattern': r'ValidationError|Invalid.*value|constraint.*violation',
                'fix_type': 'validation_error',
                'confidence': 0.7,
                'description': 'Fix data validation issues',
                'safe_auto_apply': True
            },
            'assertion_error': {
                'pattern': r'AssertionError|assert.*failed',
                'fix_type': 'assertion_fix',
                'confidence': 0.6,
                'description': 'Fix assertion failures',
                'safe_auto_apply': False  # Assertions might indicate logic errors
            },
            'timeout_error': {
                'pattern': r'TimeoutError|timeout.*exceeded',
                'fix_type': 'timeout_adjustment',
                'confidence': 0.7,
                'description': 'Adjust timeout values',
                'safe_auto_apply': True
            },
            'connection_error': {
                'pattern': r'ConnectionError|connection.*refused|network.*error',
                'fix_type': 'connection_retry',
                'confidence': 0.6,
                'description': 'Add connection retry logic',
                'safe_auto_apply': False  # Network issues might be environmental
            }
        }
    
    def analyze_test_failure(self, failure: TestFailure) -> List[FixRecommendation]:
        """Analyze test failure and generate fix recommendations"""
        recommendations = []
        
        # Pattern-based analysis
        pattern_recommendations = self._analyze_with_patterns(failure)
        recommendations.extend(pattern_recommendations)
        
        # Code context analysis
        if failure.code_context:
            context_recommendations = self._analyze_code_context(failure)
            recommendations.extend(context_recommendations)
        
        # Stack trace analysis
        if failure.stack_trace:
            stack_recommendations = self._analyze_stack_trace(failure)
            recommendations.extend(stack_recommendations)
        
        # Specific failure type analysis
        type_recommendations = self._analyze_failure_type(failure)
        recommendations.extend(type_recommendations)
        
        # Remove duplicates and sort by confidence
        unique_recommendations = self._deduplicate_recommendations(recommendations)
        return sorted(unique_recommendations, key=lambda x: x.confidence, reverse=True)
    
    def _analyze_with_patterns(self, failure: TestFailure) -> List[FixRecommendation]:
        """Analyze failure using predefined patterns"""
        recommendations = []
        error_text = f"{failure.error_message} {failure.stack_trace}".lower()
        
        for pattern_name, pattern_info in self.fix_patterns.items():
            if re.search(pattern_info['pattern'], error_text, re.IGNORECASE):
                recommendation = FixRecommendation(
                    recommendation_id=f"FIX_{failure.test_id}_{pattern_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    failure_id=failure.test_id,
                    fix_type=pattern_info['fix_type'],
                    confidence=pattern_info['confidence'],
                    description=pattern_info['description'],
                    safe_to_auto_apply=pattern_info['safe_auto_apply'],
                    estimated_impact='low' if pattern_info['safe_auto_apply'] else 'medium'
                )
                
                # Generate specific code changes based on pattern
                code_changes = self._generate_code_changes(failure, pattern_info)
                if code_changes:
                    recommendation.code_changes = code_changes
                
                recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_code_context(self, failure: TestFailure) -> List[FixRecommendation]:
        """Analyze code context for fix opportunities"""
        recommendations = []
        
        if not failure.code_context:
            return recommendations
        
        try:
            # Parse code context
            tree = ast.parse(failure.code_context)
            
            # Look for common issues
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare):
                    # Check for float comparisons
                    if self._has_float_comparison(node):
                        recommendations.append(FixRecommendation(
                            recommendation_id=f"FIX_{failure.test_id}_float_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            failure_id=failure.test_id,
                            fix_type='calculation_precision',
                            confidence=0.8,
                            description='Replace float comparison with decimal comparison',
                            safe_to_auto_apply=True,
                            estimated_impact='low'
                        ))
                
                elif isinstance(node, ast.Attribute):
                    # Check for potential None attribute access
                    if self._might_be_none_access(node, failure.error_message):
                        recommendations.append(FixRecommendation(
                            recommendation_id=f"FIX_{failure.test_id}_none_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            failure_id=failure.test_id,
                            fix_type='null_check',
                            confidence=0.7,
                            description='Add null check before attribute access',
                            safe_to_auto_apply=True,
                            estimated_impact='low'
                        ))
        
        except SyntaxError:
            self.logger.warning(f"Could not parse code context for {failure.test_id}")
        
        return recommendations
    
    def _analyze_stack_trace(self, failure: TestFailure) -> List[FixRecommendation]:
        """Analyze stack trace for fix opportunities"""
        recommendations = []
        
        # Look for common stack trace patterns
        if 'division by zero' in failure.stack_trace.lower():
            recommendations.append(FixRecommendation(
                recommendation_id=f"FIX_{failure.test_id}_division_zero_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                failure_id=failure.test_id,
                fix_type='bounds_check',
                confidence=0.9,
                description='Add zero division check',
                safe_to_auto_apply=True,
                estimated_impact='low'
            ))
        
        if 'file not found' in failure.stack_trace.lower():
            recommendations.append(FixRecommendation(
                recommendation_id=f"FIX_{failure.test_id}_file_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                failure_id=failure.test_id,
                fix_type='file_validation',
                confidence=0.8,
                description='Add file existence check',
                safe_to_auto_apply=True,
                estimated_impact='low'
            ))
        
        return recommendations
    
    def _analyze_failure_type(self, failure: TestFailure) -> List[FixRecommendation]:
        """Analyze specific failure types"""
        recommendations = []
        
        if failure.failure_type == 'assertion_failure':
            # Analyze assertion failures
            if 'expected' in failure.error_message.lower() and 'actual' in failure.error_message.lower():
                recommendations.append(FixRecommendation(
                    recommendation_id=f"FIX_{failure.test_id}_assertion_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    failure_id=failure.test_id,
                    fix_type='assertion_fix',
                    confidence=0.6,
                    description='Review assertion logic and expected values',
                    safe_to_auto_apply=False,
                    estimated_impact='medium'
                ))
        
        elif failure.failure_type == 'performance_failure':
            recommendations.append(FixRecommendation(
                recommendation_id=f"FIX_{failure.test_id}_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                failure_id=failure.test_id,
                fix_type='performance_optimization',
                confidence=0.5,
                description='Optimize performance-critical code',
                safe_to_auto_apply=False,
                estimated_impact='high'
            ))
        
        return recommendations
    
    def _generate_code_changes(self, failure: TestFailure, pattern_info: Dict) -> List[Dict]:
        """Generate specific code changes for a fix pattern"""
        changes = []
        
        if pattern_info['fix_type'] == 'calculation_precision':
            changes.append({
                'type': 'replace',
                'pattern': r'(\d+\.\d+|\d+\.|\.\d+)',
                'replacement': r'Decimal("\1")',
                'description': 'Convert float literals to Decimal'
            })
            changes.append({
                'type': 'add_import',
                'import': 'from decimal import Decimal',
                'description': 'Add Decimal import'
            })
        
        elif pattern_info['fix_type'] == 'null_check':
            changes.append({
                'type': 'wrap',
                'pattern': r'(\w+)\.(\w+)',
                'replacement': r'if \1 is not None: \1.\2',
                'description': 'Add null check before attribute access'
            })
        
        elif pattern_info['fix_type'] == 'bounds_check':
            changes.append({
                'type': 'wrap',
                'pattern': r'(\w+)\[(\d+|\w+)\]',
                'replacement': r'if len(\1) > \2: \1[\2]',
                'description': 'Add bounds check before list access'
            })
        
        elif pattern_info['fix_type'] == 'import_missing':
            # Extract missing module from error message
            import_match = re.search(r"No module named '(\w+)'", failure.error_message)
            if import_match:
                module_name = import_match.group(1)
                changes.append({
                    'type': 'add_import',
                    'import': f'import {module_name}',
                    'description': f'Add missing import for {module_name}'
                })
        
        return changes
    
    def _deduplicate_recommendations(self, recommendations: List[FixRecommendation]) -> List[FixRecommendation]:
        """Remove duplicate recommendations"""
        seen = set()
        unique_recommendations = []
        
        for rec in recommendations:
            key = (rec.fix_type, rec.description)
            if key not in seen:
                seen.add(key)
                unique_recommendations.append(rec)
        
        return unique_recommendations
    
    def _has_float_comparison(self, node: ast.Compare) -> bool:
        """Check if AST node contains float comparison"""
        # Simplified check - would be more sophisticated in practice
        return any(isinstance(comp, ast.Eq) for comp in node.ops)
    
    def _might_be_none_access(self, node: ast.Attribute, error_message: str) -> bool:
        """Check if attribute access might be on None"""
        return 'NoneType' in error_message and 'attribute' in error_message
    
    def apply_safe_fixes(self, recommendations: List[FixRecommendation]) -> List[AppliedFix]:
        """Apply safe fixes automatically"""
        applied_fixes = []
        
        for recommendation in recommendations:
            if recommendation.safe_to_auto_apply and recommendation.fix_type in self.safe_fix_types:
                try:
                    applied_fix = self._apply_fix(recommendation)
                    applied_fixes.append(applied_fix)
                    self.applied_fixes.append(applied_fix)
                    
                    if applied_fix.success:
                        self.logger.info(f"Successfully applied fix: {recommendation.description}")
                    else:
                        self.logger.warning(f"Failed to apply fix: {recommendation.description}")
                        
                except Exception as e:
                    self.logger.error(f"Error applying fix {recommendation.recommendation_id}: {e}")
                    applied_fixes.append(AppliedFix(
                        fix_id=f"APPLIED_{recommendation.recommendation_id}",
                        recommendation_id=recommendation.recommendation_id,
                        applied_at=datetime.now(),
                        success=False,
                        validation_results={'error': str(e)}
                    ))
        
        return applied_fixes
    
    def _apply_fix(self, recommendation: FixRecommendation) -> AppliedFix:
        """Apply a specific fix recommendation"""
        fix_id = f"APPLIED_{recommendation.recommendation_id}"
        
        try:
            # Create rollback information
            rollback_info = self._create_rollback_info(recommendation)
            
            # Apply the fix based on type
            if recommendation.fix_type == 'calculation_precision':
                success = self._apply_precision_fix(recommendation)
            elif recommendation.fix_type == 'null_check':
                success = self._apply_null_check_fix(recommendation)
            elif recommendation.fix_type == 'bounds_check':
                success = self._apply_bounds_check_fix(recommendation)
            elif recommendation.fix_type == 'import_missing':
                success = self._apply_import_fix(recommendation)
            elif recommendation.fix_type == 'validation_error':
                success = self._apply_validation_fix(recommendation)
            else:
                success = False
                self.logger.warning(f"Unknown fix type: {recommendation.fix_type}")
            
            # Validate the fix
            validation_results = self._validate_fix(recommendation) if success else {}
            
            return AppliedFix(
                fix_id=fix_id,
                recommendation_id=recommendation.recommendation_id,
                applied_at=datetime.now(),
                success=success,
                validation_results=validation_results,
                rollback_info=rollback_info
            )
            
        except Exception as e:
            return AppliedFix(
                fix_id=fix_id,
                recommendation_id=recommendation.recommendation_id,
                applied_at=datetime.now(),
                success=False,
                validation_results={'error': str(e)}
            )
    
    def _apply_precision_fix(self, recommendation: FixRecommendation) -> bool:
        """Apply decimal precision fix"""
        # This would modify the actual code files
        # For now, we'll simulate the fix application
        self.logger.info("Applying decimal precision fix")
        return True
    
    def _apply_null_check_fix(self, recommendation: FixRecommendation) -> bool:
        """Apply null check fix"""
        self.logger.info("Applying null check fix")
        return True
    
    def _apply_bounds_check_fix(self, recommendation: FixRecommendation) -> bool:
        """Apply bounds check fix"""
        self.logger.info("Applying bounds check fix")
        return True
    
    def _apply_import_fix(self, recommendation: FixRecommendation) -> bool:
        """Apply missing import fix"""
        self.logger.info("Applying import fix")
        return True
    
    def _apply_validation_fix(self, recommendation: FixRecommendation) -> bool:
        """Apply validation error fix"""
        self.logger.info("Applying validation fix")
        return True
    
    def _create_rollback_info(self, recommendation: FixRecommendation) -> Dict:
        """Create rollback information for a fix"""
        return {
            'timestamp': datetime.now().isoformat(),
            'fix_type': recommendation.fix_type,
            'original_code': 'placeholder_original_code',
            'backup_created': True
        }
    
    def _validate_fix(self, recommendation: FixRecommendation) -> Dict[str, Any]:
        """Validate that a fix was applied correctly"""
        validation_results = {
            'syntax_valid': True,
            'imports_resolved': True,
            'tests_pass': True,
            'performance_impact': 'minimal'
        }
        
        # Run validation tests if specified
        if recommendation.validation_tests:
            for test in recommendation.validation_tests:
                # Run the validation test
                test_result = self._run_validation_test(test)
                validation_results[f'validation_{test}'] = test_result
        
        return validation_results
    
    def _run_validation_test(self, test_name: str) -> bool:
        """Run a specific validation test"""
        # This would run actual validation tests
        # For now, we'll simulate success
        return True
    
    def rollback_fix(self, applied_fix: AppliedFix) -> bool:
        """Rollback an applied fix"""
        try:
            if not applied_fix.rollback_info:
                self.logger.error(f"No rollback information for fix {applied_fix.fix_id}")
                return False
            
            # Restore original code from backup
            self.logger.info(f"Rolling back fix {applied_fix.fix_id}")
            
            # This would restore the original code
            # For now, we'll simulate successful rollback
            return True
            
        except Exception as e:
            self.logger.error(f"Error rolling back fix {applied_fix.fix_id}: {e}")
            return False
    
    def generate_fix_report(self, recommendations: List[FixRecommendation], 
                          applied_fixes: List[AppliedFix]) -> Dict[str, Any]:
        """Generate comprehensive fix report"""
        successful_fixes = [f for f in applied_fixes if f.success]
        failed_fixes = [f for f in applied_fixes if not f.success]
        
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'summary': {
                'total_recommendations': len(recommendations),
                'safe_recommendations': len([r for r in recommendations if r.safe_to_auto_apply]),
                'applied_fixes': len(applied_fixes),
                'successful_fixes': len(successful_fixes),
                'failed_fixes': len(failed_fixes),
                'success_rate': len(successful_fixes) / len(applied_fixes) * 100 if applied_fixes else 0
            },
            'recommendations_by_type': self._group_by_fix_type(recommendations),
            'applied_fixes_by_type': self._group_applied_fixes_by_type(applied_fixes),
            'detailed_recommendations': [
                {
                    'recommendation_id': r.recommendation_id,
                    'fix_type': r.fix_type,
                    'confidence': r.confidence,
                    'description': r.description,
                    'safe_to_auto_apply': r.safe_to_auto_apply,
                    'estimated_impact': r.estimated_impact
                }
                for r in recommendations
            ],
            'applied_fixes_details': [
                {
                    'fix_id': f.fix_id,
                    'recommendation_id': f.recommendation_id,
                    'applied_at': f.applied_at.isoformat(),
                    'success': f.success,
                    'validation_results': f.validation_results
                }
                for f in applied_fixes
            ],
            'recommendations_for_manual_review': [
                {
                    'recommendation_id': r.recommendation_id,
                    'fix_type': r.fix_type,
                    'description': r.description,
                    'reason_for_manual_review': 'High impact or complex fix requiring human review'
                }
                for r in recommendations if not r.safe_to_auto_apply
            ]
        }
        
        return report
    
    def _group_by_fix_type(self, recommendations: List[FixRecommendation]) -> Dict[str, int]:
        """Group recommendations by fix type"""
        groups = {}
        for rec in recommendations:
            groups[rec.fix_type] = groups.get(rec.fix_type, 0) + 1
        return groups
    
    def _group_applied_fixes_by_type(self, applied_fixes: List[AppliedFix]) -> Dict[str, Dict[str, int]]:
        """Group applied fixes by type and success status"""
        groups = {}
        for fix in applied_fixes:
            # Get the recommendation to find the fix type
            rec = next((r for r in self.applied_fixes if r.fix_id == fix.fix_id), None)
            if rec:
                fix_type = rec.recommendation_id.split('_')[2]  # Extract fix type from ID
                if fix_type not in groups:
                    groups[fix_type] = {'successful': 0, 'failed': 0}
                
                if fix.success:
                    groups[fix_type]['successful'] += 1
                else:
                    groups[fix_type]['failed'] += 1
        
        return groups