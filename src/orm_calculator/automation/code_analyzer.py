"""
Automated Code Analysis with Quality Gates and Improvement Suggestions

Provides comprehensive code analysis including:
- Static code analysis
- Code quality metrics
- Security vulnerability detection
- Best practices enforcement
- Improvement suggestions
"""

import ast
import logging
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import json
import re

logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IssueCategory(Enum):
    """Code issue categories"""
    STYLE = "style"
    COMPLEXITY = "complexity"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    RELIABILITY = "reliability"
    DOCUMENTATION = "documentation"


@dataclass
class CodeIssue:
    """Represents a code issue found during analysis"""
    file_path: str
    line_number: int
    column: int
    severity: SeverityLevel
    category: IssueCategory
    rule_id: str
    message: str
    suggestion: Optional[str] = None
    auto_fixable: bool = False


@dataclass
class QualityMetrics:
    """Code quality metrics"""
    cyclomatic_complexity: float
    maintainability_index: float
    lines_of_code: int
    test_coverage: float
    code_duplication: float
    technical_debt_ratio: float
    security_score: float
    documentation_coverage: float


@dataclass
class CodeAnalysisResult:
    """Complete code analysis result"""
    overall_score: float
    quality_metrics: QualityMetrics
    issues: List[CodeIssue]
    suggestions: List[str]
    files_analyzed: int
    analysis_duration: float
    timestamp: str


class CodeAnalyzer:
    """
    Comprehensive code analyzer with quality gates and improvement suggestions
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.src_path = self.project_root / "src"
        self.test_path = self.project_root / "tests"
        
        # Quality thresholds
        self.quality_thresholds = {
            'cyclomatic_complexity': 10,
            'maintainability_index': 70,
            'test_coverage': 95,
            'code_duplication': 5,
            'technical_debt_ratio': 10,
            'security_score': 80,
            'documentation_coverage': 80
        }
    
    async def analyze_codebase(self) -> CodeAnalysisResult:
        """
        Perform comprehensive codebase analysis
        
        Returns:
            Complete analysis result with metrics and issues
        """
        logger.info("Starting comprehensive codebase analysis")
        
        start_time = time.time()
        issues = []
        files_analyzed = 0
        
        # Analyze Python files
        python_files = list(self.src_path.rglob("*.py"))
        for file_path in python_files:
            file_issues = await self._analyze_python_file(file_path)
            issues.extend(file_issues)
            files_analyzed += 1
        
        # Calculate quality metrics
        quality_metrics = await self._calculate_quality_metrics()
        
        # Generate overall score
        overall_score = self._calculate_overall_score(quality_metrics, issues)
        
        # Generate improvement suggestions
        suggestions = self._generate_improvement_suggestions(quality_metrics, issues)
        
        analysis_duration = time.time() - start_time
        
        result = CodeAnalysisResult(
            overall_score=overall_score,
            quality_metrics=quality_metrics,
            issues=issues,
            suggestions=suggestions,
            files_analyzed=files_analyzed,
            analysis_duration=analysis_duration,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Code analysis completed: {overall_score:.2f} score, {len(issues)} issues found")
        return result
    
    async def _analyze_python_file(self, file_path: Path) -> List[CodeIssue]:
        """Analyze a single Python file"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content, filename=str(file_path))
            
            # Run various analyzers
            issues.extend(self._check_complexity(file_path, tree))
            issues.extend(self._check_style(file_path, content))
            issues.extend(self._check_security(file_path, tree, content))
            issues.extend(self._check_performance(file_path, tree))
            issues.extend(self._check_maintainability(file_path, tree))
            issues.extend(self._check_documentation(file_path, tree, content))
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            issues.append(CodeIssue(
                file_path=str(file_path),
                line_number=1,
                column=1,
                severity=SeverityLevel.ERROR,
                category=IssueCategory.RELIABILITY,
                rule_id="PARSE_ERROR",
                message=f"Failed to parse file: {e}",
                auto_fixable=False
            ))
        
        return issues
    
    def _check_complexity(self, file_path: Path, tree: ast.AST) -> List[CodeIssue]:
        """Check cyclomatic complexity"""
        issues = []
        
        class ComplexityVisitor(ast.NodeVisitor):
            def __init__(self):
                self.complexity_issues = []
            
            def visit_FunctionDef(self, node):
                complexity = self._calculate_function_complexity(node)
                if complexity > 10:  # Threshold for high complexity
                    self.complexity_issues.append(CodeIssue(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        column=node.col_offset,
                        severity=SeverityLevel.WARNING if complexity <= 15 else SeverityLevel.ERROR,
                        category=IssueCategory.COMPLEXITY,
                        rule_id="HIGH_COMPLEXITY",
                        message=f"Function '{node.name}' has high cyclomatic complexity: {complexity}",
                        suggestion="Consider breaking this function into smaller functions",
                        auto_fixable=False
                    ))
                self.generic_visit(node)
            
            def _calculate_function_complexity(self, node):
                # Simplified complexity calculation
                complexity = 1  # Base complexity
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1
                return complexity
        
        visitor = ComplexityVisitor()
        visitor.visit(tree)
        issues.extend(visitor.complexity_issues)
        
        return issues
    
    def _check_style(self, file_path: Path, content: str) -> List[CodeIssue]:
        """Check code style issues"""
        issues = []
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 88:  # Black's default line length
                issues.append(CodeIssue(
                    file_path=str(file_path),
                    line_number=i,
                    column=89,
                    severity=SeverityLevel.WARNING,
                    category=IssueCategory.STYLE,
                    rule_id="LINE_TOO_LONG",
                    message=f"Line too long ({len(line)} > 88 characters)",
                    suggestion="Break long lines using parentheses or backslashes",
                    auto_fixable=True
                ))
            
            # Check trailing whitespace
            if line.rstrip() != line:
                issues.append(CodeIssue(
                    file_path=str(file_path),
                    line_number=i,
                    column=len(line.rstrip()) + 1,
                    severity=SeverityLevel.INFO,
                    category=IssueCategory.STYLE,
                    rule_id="TRAILING_WHITESPACE",
                    message="Trailing whitespace",
                    suggestion="Remove trailing whitespace",
                    auto_fixable=True
                ))
        
        return issues
    
    def _check_security(self, file_path: Path, tree: ast.AST, content: str) -> List[CodeIssue]:
        """Check security vulnerabilities"""
        issues = []
        
        # Check for hardcoded secrets
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password detected"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key detected"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret detected"),
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, message in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(CodeIssue(
                        file_path=str(file_path),
                        line_number=i,
                        column=1,
                        severity=SeverityLevel.CRITICAL,
                        category=IssueCategory.SECURITY,
                        rule_id="HARDCODED_SECRET",
                        message=message,
                        suggestion="Use environment variables or secure configuration",
                        auto_fixable=False
                    ))
        
        # Check for dangerous imports
        class SecurityVisitor(ast.NodeVisitor):
            def __init__(self):
                self.security_issues = []
            
            def visit_Import(self, node):
                for alias in node.names:
                    if alias.name in ['pickle', 'cPickle']:
                        self.security_issues.append(CodeIssue(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            column=node.col_offset,
                            severity=SeverityLevel.WARNING,
                            category=IssueCategory.SECURITY,
                            rule_id="UNSAFE_IMPORT",
                            message=f"Potentially unsafe import: {alias.name}",
                            suggestion="Consider using safer alternatives like json",
                            auto_fixable=False
                        ))
        
        visitor = SecurityVisitor()
        visitor.visit(tree)
        issues.extend(visitor.security_issues)
        
        return issues
    
    def _check_performance(self, file_path: Path, tree: ast.AST) -> List[CodeIssue]:
        """Check performance issues"""
        issues = []
        
        class PerformanceVisitor(ast.NodeVisitor):
            def __init__(self):
                self.performance_issues = []
            
            def visit_ListComp(self, node):
                # Check for nested list comprehensions
                for child in ast.walk(node):
                    if isinstance(child, ast.ListComp) and child != node:
                        self.performance_issues.append(CodeIssue(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            column=node.col_offset,
                            severity=SeverityLevel.WARNING,
                            category=IssueCategory.PERFORMANCE,
                            rule_id="NESTED_LIST_COMP",
                            message="Nested list comprehension may impact performance",
                            suggestion="Consider using generator expressions or breaking into separate operations",
                            auto_fixable=False
                        ))
                self.generic_visit(node)
        
        visitor = PerformanceVisitor()
        visitor.visit(tree)
        issues.extend(visitor.performance_issues)
        
        return issues
    
    def _check_maintainability(self, file_path: Path, tree: ast.AST) -> List[CodeIssue]:
        """Check maintainability issues"""
        issues = []
        
        class MaintainabilityVisitor(ast.NodeVisitor):
            def __init__(self):
                self.maintainability_issues = []
            
            def visit_FunctionDef(self, node):
                # Check function length
                function_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
                if function_lines > 50:
                    self.maintainability_issues.append(CodeIssue(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        column=node.col_offset,
                        severity=SeverityLevel.WARNING,
                        category=IssueCategory.MAINTAINABILITY,
                        rule_id="LONG_FUNCTION",
                        message=f"Function '{node.name}' is too long ({function_lines} lines)",
                        suggestion="Consider breaking this function into smaller functions",
                        auto_fixable=False
                    ))
                
                # Check parameter count
                param_count = len(node.args.args)
                if param_count > 5:
                    self.maintainability_issues.append(CodeIssue(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        column=node.col_offset,
                        severity=SeverityLevel.WARNING,
                        category=IssueCategory.MAINTAINABILITY,
                        rule_id="TOO_MANY_PARAMS",
                        message=f"Function '{node.name}' has too many parameters ({param_count})",
                        suggestion="Consider using a configuration object or dataclass",
                        auto_fixable=False
                    ))
                
                self.generic_visit(node)
        
        visitor = MaintainabilityVisitor()
        visitor.visit(tree)
        issues.extend(visitor.maintainability_issues)
        
        return issues
    
    def _check_documentation(self, file_path: Path, tree: ast.AST, content: str) -> List[CodeIssue]:
        """Check documentation coverage"""
        issues = []
        
        class DocumentationVisitor(ast.NodeVisitor):
            def __init__(self):
                self.doc_issues = []
            
            def visit_FunctionDef(self, node):
                # Check if function has docstring
                if not ast.get_docstring(node):
                    self.doc_issues.append(CodeIssue(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        column=node.col_offset,
                        severity=SeverityLevel.INFO,
                        category=IssueCategory.DOCUMENTATION,
                        rule_id="MISSING_DOCSTRING",
                        message=f"Function '{node.name}' is missing docstring",
                        suggestion="Add docstring describing function purpose, parameters, and return value",
                        auto_fixable=True
                    ))
                self.generic_visit(node)
            
            def visit_ClassDef(self, node):
                # Check if class has docstring
                if not ast.get_docstring(node):
                    self.doc_issues.append(CodeIssue(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        column=node.col_offset,
                        severity=SeverityLevel.INFO,
                        category=IssueCategory.DOCUMENTATION,
                        rule_id="MISSING_CLASS_DOCSTRING",
                        message=f"Class '{node.name}' is missing docstring",
                        suggestion="Add docstring describing class purpose and usage",
                        auto_fixable=True
                    ))
                self.generic_visit(node)
        
        visitor = DocumentationVisitor()
        visitor.visit(tree)
        issues.extend(visitor.doc_issues)
        
        return issues
    
    async def _calculate_quality_metrics(self) -> QualityMetrics:
        """Calculate comprehensive quality metrics"""
        
        # Run external tools for more accurate metrics
        try:
            # Calculate test coverage
            coverage_result = await self._run_coverage_analysis()
            test_coverage = coverage_result.get('coverage', 0.0)
            
            # Calculate other metrics
            complexity_metrics = await self._calculate_complexity_metrics()
            duplication_metrics = await self._calculate_duplication_metrics()
            
            return QualityMetrics(
                cyclomatic_complexity=complexity_metrics.get('average_complexity', 0.0),
                maintainability_index=complexity_metrics.get('maintainability_index', 0.0),
                lines_of_code=complexity_metrics.get('lines_of_code', 0),
                test_coverage=test_coverage,
                code_duplication=duplication_metrics.get('duplication_percentage', 0.0),
                technical_debt_ratio=self._calculate_technical_debt_ratio(),
                security_score=await self._calculate_security_score(),
                documentation_coverage=await self._calculate_documentation_coverage()
            )
            
        except Exception as e:
            logger.error(f"Error calculating quality metrics: {e}")
            return QualityMetrics(
                cyclomatic_complexity=0.0,
                maintainability_index=0.0,
                lines_of_code=0,
                test_coverage=0.0,
                code_duplication=0.0,
                technical_debt_ratio=0.0,
                security_score=0.0,
                documentation_coverage=0.0
            )
    
    async def _run_coverage_analysis(self) -> Dict[str, Any]:
        """Run test coverage analysis"""
        try:
            result = subprocess.run(
                ['python', '-m', 'pytest', '--cov=src', '--cov-report=json'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                # Parse coverage report
                coverage_file = self.project_root / 'coverage.json'
                if coverage_file.exists():
                    with open(coverage_file) as f:
                        coverage_data = json.load(f)
                    return {'coverage': coverage_data.get('totals', {}).get('percent_covered', 0.0)}
            
        except Exception as e:
            logger.error(f"Coverage analysis failed: {e}")
        
        return {'coverage': 0.0}
    
    async def _calculate_complexity_metrics(self) -> Dict[str, Any]:
        """Calculate complexity metrics"""
        total_complexity = 0
        total_functions = 0
        total_lines = 0
        
        python_files = list(self.src_path.rglob("*.py"))
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    total_lines += len(content.split('\n'))
                
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        complexity = self._calculate_function_complexity_detailed(node)
                        total_complexity += complexity
                        total_functions += 1
                        
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")
        
        average_complexity = total_complexity / max(1, total_functions)
        maintainability_index = max(0, 171 - 5.2 * math.log(total_lines) - 0.23 * average_complexity)
        
        return {
            'average_complexity': average_complexity,
            'maintainability_index': maintainability_index,
            'lines_of_code': total_lines
        }
    
    def _calculate_function_complexity_detailed(self, node: ast.FunctionDef) -> int:
        """Calculate detailed cyclomatic complexity for a function"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
        
        return complexity
    
    async def _calculate_duplication_metrics(self) -> Dict[str, Any]:
        """Calculate code duplication metrics"""
        # Simplified duplication detection
        # In a real implementation, you might use tools like jscpd or similar
        
        file_hashes = {}
        duplicate_lines = 0
        total_lines = 0
        
        python_files = list(self.src_path.rglob("*.py"))
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    total_lines += len(lines)
                    
                    # Check for duplicate lines (simplified)
                    for line in lines:
                        line_hash = hash(line.strip())
                        if line_hash in file_hashes:
                            duplicate_lines += 1
                        else:
                            file_hashes[line_hash] = file_path
                            
            except Exception as e:
                logger.error(f"Error analyzing duplication in {file_path}: {e}")
        
        duplication_percentage = (duplicate_lines / max(1, total_lines)) * 100
        
        return {'duplication_percentage': duplication_percentage}
    
    def _calculate_technical_debt_ratio(self) -> float:
        """Calculate technical debt ratio"""
        # Simplified calculation based on code issues
        # In practice, this would be more sophisticated
        return 5.0  # Placeholder
    
    async def _calculate_security_score(self) -> float:
        """Calculate security score"""
        # Run security analysis
        try:
            result = subprocess.run(
                ['python', '-m', 'bandit', '-r', 'src', '-f', 'json'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                security_data = json.loads(result.stdout)
                total_issues = len(security_data.get('results', []))
                high_severity = sum(1 for issue in security_data.get('results', []) 
                                  if issue.get('issue_severity') == 'HIGH')
                
                # Calculate score based on issues found
                if total_issues == 0:
                    return 100.0
                else:
                    penalty = (high_severity * 20) + ((total_issues - high_severity) * 5)
                    return max(0.0, 100.0 - penalty)
            
        except Exception as e:
            logger.error(f"Security analysis failed: {e}")
        
        return 80.0  # Default score
    
    async def _calculate_documentation_coverage(self) -> float:
        """Calculate documentation coverage"""
        total_functions = 0
        documented_functions = 0
        total_classes = 0
        documented_classes = 0
        
        python_files = list(self.src_path.rglob("*.py"))
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        total_functions += 1
                        if ast.get_docstring(node):
                            documented_functions += 1
                    elif isinstance(node, ast.ClassDef):
                        total_classes += 1
                        if ast.get_docstring(node):
                            documented_classes += 1
                            
            except Exception as e:
                logger.error(f"Error analyzing documentation in {file_path}: {e}")
        
        total_items = total_functions + total_classes
        documented_items = documented_functions + documented_classes
        
        if total_items == 0:
            return 100.0
        
        return (documented_items / total_items) * 100
    
    def _calculate_overall_score(self, metrics: QualityMetrics, issues: List[CodeIssue]) -> float:
        """Calculate overall quality score"""
        
        # Weight different factors
        weights = {
            'complexity': 0.15,
            'maintainability': 0.20,
            'test_coverage': 0.25,
            'duplication': 0.10,
            'security': 0.20,
            'documentation': 0.10
        }
        
        # Normalize metrics to 0-100 scale
        complexity_score = max(0, 100 - (metrics.cyclomatic_complexity * 5))
        maintainability_score = metrics.maintainability_index
        coverage_score = metrics.test_coverage
        duplication_score = max(0, 100 - (metrics.code_duplication * 2))
        security_score = metrics.security_score
        documentation_score = metrics.documentation_coverage
        
        # Calculate weighted score
        weighted_score = (
            weights['complexity'] * complexity_score +
            weights['maintainability'] * maintainability_score +
            weights['test_coverage'] * coverage_score +
            weights['duplication'] * duplication_score +
            weights['security'] * security_score +
            weights['documentation'] * documentation_score
        )
        
        # Apply penalty for critical issues
        critical_issues = sum(1 for issue in issues if issue.severity == SeverityLevel.CRITICAL)
        error_issues = sum(1 for issue in issues if issue.severity == SeverityLevel.ERROR)
        
        penalty = (critical_issues * 10) + (error_issues * 5)
        
        return max(0.0, min(100.0, weighted_score - penalty))
    
    def _generate_improvement_suggestions(self, metrics: QualityMetrics, issues: List[CodeIssue]) -> List[str]:
        """Generate improvement suggestions based on analysis"""
        suggestions = []
        
        # Coverage suggestions
        if metrics.test_coverage < self.quality_thresholds['test_coverage']:
            suggestions.append(f"Increase test coverage from {metrics.test_coverage:.1f}% to {self.quality_thresholds['test_coverage']}%")
        
        # Complexity suggestions
        if metrics.cyclomatic_complexity > self.quality_thresholds['cyclomatic_complexity']:
            suggestions.append("Reduce cyclomatic complexity by breaking down complex functions")
        
        # Security suggestions
        security_issues = [i for i in issues if i.category == IssueCategory.SECURITY]
        if security_issues:
            suggestions.append(f"Address {len(security_issues)} security issues found")
        
        # Documentation suggestions
        if metrics.documentation_coverage < self.quality_thresholds['documentation_coverage']:
            suggestions.append("Improve documentation coverage by adding docstrings to functions and classes")
        
        # Performance suggestions
        performance_issues = [i for i in issues if i.category == IssueCategory.PERFORMANCE]
        if performance_issues:
            suggestions.append(f"Optimize {len(performance_issues)} performance issues")
        
        return suggestions
    
    async def analyze_code_quality(self) -> CodeAnalysisResult:
        """Convenience method for quality-focused analysis"""
        return await self.analyze_codebase()
    
    def get_auto_fixable_issues(self, issues: List[CodeIssue]) -> List[CodeIssue]:
        """Get list of issues that can be automatically fixed"""
        return [issue for issue in issues if issue.auto_fixable]