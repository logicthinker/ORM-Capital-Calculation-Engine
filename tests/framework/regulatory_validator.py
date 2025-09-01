"""
Regulatory Compliance Validator for Automated Testing Framework

Validates compliance with RBI Basel III SMA requirements and other regulatory standards.
"""

from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import date, datetime
import json
import logging


@dataclass
class ComplianceRule:
    """Regulatory compliance rule definition"""
    rule_id: str
    category: str
    description: str
    requirement: str
    validation_function: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    regulatory_reference: str


@dataclass
class ComplianceResult:
    """Compliance validation result"""
    rule_id: str
    status: str  # 'compliant', 'non_compliant', 'warning', 'not_applicable'
    message: str
    details: Optional[Dict] = None
    evidence: Optional[List[str]] = None


class RegulatoryComplianceValidator:
    """Comprehensive regulatory compliance validator"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rbi_rules = self._initialize_rbi_rules()
        self.basel_rules = self._initialize_basel_rules()
        self.data_quality_rules = self._initialize_data_quality_rules()
        
    def _initialize_rbi_rules(self) -> List[ComplianceRule]:
        """Initialize RBI SMA compliance rules"""
        return [
            ComplianceRule(
                rule_id='RBI_SMA_001',
                category='sma_calculation',
                description='Business Indicator calculation using RBI Max/Min/Abs operations',
                requirement='BI = ILDC + SC + FC with 3-year averaging using RBI operations',
                validation_function='validate_bi_calculation',
                severity='critical',
                regulatory_reference='RBI Master Direction on Basel III Capital Regulations, Annex 13'
            ),
            ComplianceRule(
                rule_id='RBI_SMA_002',
                category='bucket_thresholds',
                description='Correct bucket thresholds for Indian banks',
                requirement='Bucket 1: < ₹8,000 crore, Bucket 2: ₹8,000-₹2,40,000 crore, Bucket 3: ≥ ₹2,40,000 crore',
                validation_function='validate_bucket_thresholds',
                severity='critical',
                regulatory_reference='RBI Master Direction on Basel III Capital Regulations, Para 13.2.3'
            ),
            ComplianceRule(
                rule_id='RBI_SMA_003',
                category='marginal_coefficients',
                description='Correct marginal coefficients for BIC calculation',
                requirement='Bucket 1: 12%, Bucket 2: 15%, Bucket 3: 18%',
                validation_function='validate_marginal_coefficients',
                severity='critical',
                regulatory_reference='RBI Master Direction on Basel III Capital Regulations, Para 13.2.4'
            ),
            ComplianceRule(
                rule_id='RBI_SMA_004',
                category='loss_component',
                description='Loss Component calculation methodology',
                requirement='LC = 15 × average annual losses over 10-year period',
                validation_function='validate_loss_component',
                severity='critical',
                regulatory_reference='RBI Master Direction on Basel III Capital Regulations, Para 13.2.5'
            ),
            ComplianceRule(
                rule_id='RBI_SMA_005',
                category='ilm_calculation',
                description='Internal Loss Multiplier calculation',
                requirement='ILM = ln(e - 1 + LC/BIC) with appropriate gating',
                validation_function='validate_ilm_calculation',
                severity='critical',
                regulatory_reference='RBI Master Direction on Basel III Capital Regulations, Para 13.2.6'
            ),
            ComplianceRule(
                rule_id='RBI_SMA_006',
                category='ilm_gating',
                description='ILM gating for Bucket 1 and insufficient data',
                requirement='Set ORC = BIC for Bucket 1 or < 5 years high-quality data',
                validation_function='validate_ilm_gating',
                severity='critical',
                regulatory_reference='RBI Master Direction on Basel III Capital Regulations, Para 13.2.7'
            ),
            ComplianceRule(
                rule_id='RBI_SMA_007',
                category='rwa_calculation',
                description='Risk Weighted Assets calculation',
                requirement='RWA = 12.5 × ORC',
                validation_function='validate_rwa_calculation',
                severity='critical',
                regulatory_reference='RBI Master Direction on Basel III Capital Regulations, Para 13.2.8'
            ),
            ComplianceRule(
                rule_id='RBI_SMA_008',
                category='loss_threshold',
                description='Minimum loss threshold for inclusion',
                requirement='Include losses ≥ ₹1,00,000 (or bank-specific threshold)',
                validation_function='validate_loss_threshold',
                severity='high',
                regulatory_reference='RBI Master Direction on Basel III Capital Regulations, Para 13.3.2'
            ),
            ComplianceRule(
                rule_id='RBI_SMA_009',
                category='data_quality',
                description='Minimum data quality requirements',
                requirement='At least 5 years of high-quality loss data for ILM calculation',
                validation_function='validate_data_quality',
                severity='high',
                regulatory_reference='RBI Master Direction on Basel III Capital Regulations, Para 13.3.3'
            ),
            ComplianceRule(
                rule_id='RBI_SMA_010',
                category='exclusions',
                description='Loss exclusion approval requirements',
                requirement='Exclusions require RBI approval with proper documentation',
                validation_function='validate_exclusions',
                severity='high',
                regulatory_reference='RBI Master Direction on Basel III Capital Regulations, Para 13.3.4'
            )
        ]
    
    def _initialize_basel_rules(self) -> List[ComplianceRule]:
        """Initialize Basel III compliance rules"""
        return [
            ComplianceRule(
                rule_id='BASEL_SMA_001',
                category='sma_methodology',
                description='SMA methodology implementation',
                requirement='Implement SMA as per Basel Committee guidelines',
                validation_function='validate_basel_sma_methodology',
                severity='critical',
                regulatory_reference='Basel Committee on Banking Supervision, Basel III: Finalising post-crisis reforms'
            ),
            ComplianceRule(
                rule_id='BASEL_SMA_002',
                category='business_indicator',
                description='Business Indicator components definition',
                requirement='BI components must include ILDC, SC, FC as defined by Basel',
                validation_function='validate_basel_bi_components',
                severity='critical',
                regulatory_reference='Basel III Framework, Operational Risk, Para 7.3'
            ),
            ComplianceRule(
                rule_id='BASEL_SMA_003',
                category='loss_data_standards',
                description='Operational loss data standards',
                requirement='Loss data must meet Basel operational risk data standards',
                validation_function='validate_basel_loss_standards',
                severity='high',
                regulatory_reference='Basel III Framework, Operational Risk, Para 7.4'
            )
        ]
    
    def _initialize_data_quality_rules(self) -> List[ComplianceRule]:
        """Initialize data quality rules"""
        return [
            ComplianceRule(
                rule_id='DQ_001',
                category='completeness',
                description='Data completeness requirements',
                requirement='All required fields must be populated',
                validation_function='validate_data_completeness',
                severity='high',
                regulatory_reference='Internal Data Quality Standards'
            ),
            ComplianceRule(
                rule_id='DQ_002',
                category='accuracy',
                description='Data accuracy requirements',
                requirement='Data values must be within expected ranges',
                validation_function='validate_data_accuracy',
                severity='high',
                regulatory_reference='Internal Data Quality Standards'
            ),
            ComplianceRule(
                rule_id='DQ_003',
                category='consistency',
                description='Data consistency requirements',
                requirement='Data must be consistent across related fields',
                validation_function='validate_data_consistency',
                severity='medium',
                regulatory_reference='Internal Data Quality Standards'
            ),
            ComplianceRule(
                rule_id='DQ_004',
                category='timeliness',
                description='Data timeliness requirements',
                requirement='Data must be current and updated within required timeframes',
                validation_function='validate_data_timeliness',
                severity='medium',
                regulatory_reference='Internal Data Quality Standards'
            )
        ]
    
    def generate_sma_rule(self) -> Dict[str, Any]:
        """Generate SMA compliance rule for testing"""
        import random
        
        rule = random.choice(self.rbi_rules)
        
        # Generate test scenario based on rule
        if rule.rule_id == 'RBI_SMA_001':
            return {
                'rule': rule,
                'test_scenario': {
                    'bi_components': {
                        'ildc': Decimal(str(random.uniform(1e10, 1e12))),
                        'sc': Decimal(str(random.uniform(5e9, 5e11))),
                        'fc': Decimal(str(random.uniform(2e9, 2e11)))
                    },
                    'years': [2021, 2022, 2023],
                    'expected_operation': 'rbi_max_min_abs'
                }
            }
        elif rule.rule_id == 'RBI_SMA_002':
            return {
                'rule': rule,
                'test_scenario': {
                    'bi_value': Decimal(str(random.uniform(1e10, 3e12))),
                    'expected_thresholds': [
                        Decimal('80000000000'),    # ₹8,000 crore
                        Decimal('2400000000000')   # ₹2,40,000 crore
                    ]
                }
            }
        elif rule.rule_id == 'RBI_SMA_003':
            return {
                'rule': rule,
                'test_scenario': {
                    'bucket': random.randint(1, 3),
                    'expected_coefficients': [
                        Decimal('0.12'),  # 12%
                        Decimal('0.15'),  # 15%
                        Decimal('0.18')   # 18%
                    ]
                }
            }
        else:
            return {
                'rule': rule,
                'test_scenario': {
                    'generic_test': True,
                    'validation_required': True
                }
            }
    
    def generate_basel_rule(self) -> Dict[str, Any]:
        """Generate Basel III compliance rule for testing"""
        import random
        
        rule = random.choice(self.basel_rules)
        
        return {
            'rule': rule,
            'test_scenario': {
                'methodology': 'sma',
                'compliance_check': rule.validation_function,
                'severity': rule.severity
            }
        }
    
    def generate_quality_rule(self) -> Dict[str, Any]:
        """Generate data quality rule for testing"""
        import random
        
        rule = random.choice(self.data_quality_rules)
        
        return {
            'rule': rule,
            'test_scenario': {
                'data_quality_dimension': rule.category,
                'validation_function': rule.validation_function,
                'expected_quality_level': 'high'
            }
        }
    
    def validate_sma_compliance(self, calculation_data: Dict[str, Any]) -> List[ComplianceResult]:
        """Validate SMA calculation compliance"""
        results = []
        
        for rule in self.rbi_rules:
            try:
                if rule.validation_function == 'validate_bi_calculation':
                    result = self._validate_bi_calculation(rule, calculation_data)
                elif rule.validation_function == 'validate_bucket_thresholds':
                    result = self._validate_bucket_thresholds(rule, calculation_data)
                elif rule.validation_function == 'validate_marginal_coefficients':
                    result = self._validate_marginal_coefficients(rule, calculation_data)
                elif rule.validation_function == 'validate_loss_component':
                    result = self._validate_loss_component(rule, calculation_data)
                elif rule.validation_function == 'validate_ilm_calculation':
                    result = self._validate_ilm_calculation(rule, calculation_data)
                elif rule.validation_function == 'validate_ilm_gating':
                    result = self._validate_ilm_gating(rule, calculation_data)
                elif rule.validation_function == 'validate_rwa_calculation':
                    result = self._validate_rwa_calculation(rule, calculation_data)
                else:
                    result = ComplianceResult(
                        rule_id=rule.rule_id,
                        status='not_applicable',
                        message=f'Validation function {rule.validation_function} not implemented'
                    )
                
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Error validating rule {rule.rule_id}: {e}")
                results.append(ComplianceResult(
                    rule_id=rule.rule_id,
                    status='non_compliant',
                    message=f'Validation error: {str(e)}'
                ))
        
        return results
    
    def _validate_bi_calculation(self, rule: ComplianceRule, data: Dict[str, Any]) -> ComplianceResult:
        """Validate Business Indicator calculation"""
        try:
            bi_data = data.get('bi_data', [])
            if not bi_data:
                return ComplianceResult(
                    rule_id=rule.rule_id,
                    status='non_compliant',
                    message='No BI data provided for validation'
                )
            
            # Check if BI calculation follows RBI methodology
            for bi_record in bi_data:
                ildc = bi_record.get('ildc', Decimal('0'))
                sc = bi_record.get('sc', Decimal('0'))
                fc = bi_record.get('fc', Decimal('0'))
                calculated_bi = bi_record.get('bi_total', Decimal('0'))
                
                # RBI Max/Min/Abs operations
                expected_bi = abs(max(min(ildc, Decimal('1e15')), Decimal('-1e15'))) + \
                             abs(max(min(sc, Decimal('1e15')), Decimal('-1e15'))) + \
                             abs(max(min(fc, Decimal('1e15')), Decimal('-1e15')))
                
                if abs(calculated_bi - expected_bi) > Decimal('0.01'):
                    return ComplianceResult(
                        rule_id=rule.rule_id,
                        status='non_compliant',
                        message=f'BI calculation incorrect: {calculated_bi} != {expected_bi}',
                        details={'expected': str(expected_bi), 'actual': str(calculated_bi)}
                    )
            
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='compliant',
                message='BI calculation follows RBI methodology'
            )
            
        except Exception as e:
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='non_compliant',
                message=f'BI validation error: {str(e)}'
            )
    
    def _validate_bucket_thresholds(self, rule: ComplianceRule, data: Dict[str, Any]) -> ComplianceResult:
        """Validate bucket threshold compliance"""
        try:
            bucket_config = data.get('bucket_config', {})
            thresholds = bucket_config.get('thresholds', [])
            
            expected_thresholds = [Decimal('80000000000'), Decimal('2400000000000')]
            
            if len(thresholds) != 2:
                return ComplianceResult(
                    rule_id=rule.rule_id,
                    status='non_compliant',
                    message=f'Expected 2 thresholds, got {len(thresholds)}'
                )
            
            for i, threshold in enumerate(thresholds):
                if abs(Decimal(str(threshold)) - expected_thresholds[i]) > Decimal('1'):
                    return ComplianceResult(
                        rule_id=rule.rule_id,
                        status='non_compliant',
                        message=f'Threshold {i+1} incorrect: {threshold} != {expected_thresholds[i]}',
                        details={'expected_thresholds': [str(t) for t in expected_thresholds]}
                    )
            
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='compliant',
                message='Bucket thresholds comply with RBI requirements'
            )
            
        except Exception as e:
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='non_compliant',
                message=f'Bucket threshold validation error: {str(e)}'
            )
    
    def _validate_marginal_coefficients(self, rule: ComplianceRule, data: Dict[str, Any]) -> ComplianceResult:
        """Validate marginal coefficients compliance"""
        try:
            coefficients = data.get('marginal_coefficients', [])
            expected_coefficients = [Decimal('0.12'), Decimal('0.15'), Decimal('0.18')]
            
            if len(coefficients) != 3:
                return ComplianceResult(
                    rule_id=rule.rule_id,
                    status='non_compliant',
                    message=f'Expected 3 coefficients, got {len(coefficients)}'
                )
            
            for i, coeff in enumerate(coefficients):
                if abs(Decimal(str(coeff)) - expected_coefficients[i]) > Decimal('0.001'):
                    return ComplianceResult(
                        rule_id=rule.rule_id,
                        status='non_compliant',
                        message=f'Coefficient {i+1} incorrect: {coeff} != {expected_coefficients[i]}',
                        details={'expected_coefficients': [str(c) for c in expected_coefficients]}
                    )
            
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='compliant',
                message='Marginal coefficients comply with RBI requirements'
            )
            
        except Exception as e:
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='non_compliant',
                message=f'Marginal coefficient validation error: {str(e)}'
            )
    
    def _validate_loss_component(self, rule: ComplianceRule, data: Dict[str, Any]) -> ComplianceResult:
        """Validate Loss Component calculation"""
        try:
            loss_data = data.get('loss_data', {})
            lc_value = loss_data.get('lc', Decimal('0'))
            average_losses = loss_data.get('average_annual_losses', Decimal('0'))
            
            expected_lc = average_losses * Decimal('15')
            
            if abs(lc_value - expected_lc) > Decimal('0.01'):
                return ComplianceResult(
                    rule_id=rule.rule_id,
                    status='non_compliant',
                    message=f'LC calculation incorrect: {lc_value} != {expected_lc}',
                    details={'expected_lc': str(expected_lc), 'actual_lc': str(lc_value)}
                )
            
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='compliant',
                message='Loss Component calculation complies with RBI methodology'
            )
            
        except Exception as e:
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='non_compliant',
                message=f'LC validation error: {str(e)}'
            )
    
    def _validate_ilm_calculation(self, rule: ComplianceRule, data: Dict[str, Any]) -> ComplianceResult:
        """Validate ILM calculation"""
        try:
            ilm_data = data.get('ilm_data', {})
            ilm_value = ilm_data.get('ilm', Decimal('1'))
            bic = ilm_data.get('bic', Decimal('0'))
            lc = ilm_data.get('lc', Decimal('0'))
            
            if bic == 0:
                expected_ilm = Decimal('1')  # ILM gating
            else:
                import math
                ratio = lc / bic
                expected_ilm = Decimal(str(math.log(math.e - 1 + float(ratio))))
                expected_ilm = max(expected_ilm, Decimal('1'))  # Floor of 1
            
            if abs(ilm_value - expected_ilm) > Decimal('0.001'):
                return ComplianceResult(
                    rule_id=rule.rule_id,
                    status='non_compliant',
                    message=f'ILM calculation incorrect: {ilm_value} != {expected_ilm}',
                    details={'expected_ilm': str(expected_ilm), 'actual_ilm': str(ilm_value)}
                )
            
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='compliant',
                message='ILM calculation complies with RBI methodology'
            )
            
        except Exception as e:
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='non_compliant',
                message=f'ILM validation error: {str(e)}'
            )
    
    def _validate_ilm_gating(self, rule: ComplianceRule, data: Dict[str, Any]) -> ComplianceResult:
        """Validate ILM gating logic"""
        try:
            gating_data = data.get('gating_data', {})
            bucket = gating_data.get('bucket', 1)
            data_years = gating_data.get('data_years', 0)
            high_quality_data = gating_data.get('high_quality_data', False)
            ilm_gated = gating_data.get('ilm_gated', False)
            
            should_gate = (bucket == 1) or (data_years < 5) or (not high_quality_data)
            
            if should_gate and not ilm_gated:
                return ComplianceResult(
                    rule_id=rule.rule_id,
                    status='non_compliant',
                    message='ILM gating should be applied but was not',
                    details={
                        'bucket': bucket,
                        'data_years': data_years,
                        'high_quality_data': high_quality_data,
                        'should_gate': should_gate,
                        'actually_gated': ilm_gated
                    }
                )
            elif not should_gate and ilm_gated:
                return ComplianceResult(
                    rule_id=rule.rule_id,
                    status='warning',
                    message='ILM gating applied when not required',
                    details={
                        'bucket': bucket,
                        'data_years': data_years,
                        'high_quality_data': high_quality_data,
                        'should_gate': should_gate,
                        'actually_gated': ilm_gated
                    }
                )
            
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='compliant',
                message='ILM gating logic complies with RBI requirements'
            )
            
        except Exception as e:
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='non_compliant',
                message=f'ILM gating validation error: {str(e)}'
            )
    
    def _validate_rwa_calculation(self, rule: ComplianceRule, data: Dict[str, Any]) -> ComplianceResult:
        """Validate RWA calculation"""
        try:
            rwa_data = data.get('rwa_data', {})
            rwa_value = rwa_data.get('rwa', Decimal('0'))
            orc = rwa_data.get('orc', Decimal('0'))
            
            expected_rwa = orc * Decimal('12.5')
            
            if abs(rwa_value - expected_rwa) > Decimal('0.01'):
                return ComplianceResult(
                    rule_id=rule.rule_id,
                    status='non_compliant',
                    message=f'RWA calculation incorrect: {rwa_value} != {expected_rwa}',
                    details={'expected_rwa': str(expected_rwa), 'actual_rwa': str(rwa_value)}
                )
            
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='compliant',
                message='RWA calculation complies with RBI requirements'
            )
            
        except Exception as e:
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='non_compliant',
                message=f'RWA validation error: {str(e)}'
            )
    
    def validate_data_quality(self, data: Dict[str, Any]) -> List[ComplianceResult]:
        """Validate data quality compliance"""
        results = []
        
        for rule in self.data_quality_rules:
            try:
                if rule.validation_function == 'validate_data_completeness':
                    result = self._validate_data_completeness(rule, data)
                elif rule.validation_function == 'validate_data_accuracy':
                    result = self._validate_data_accuracy(rule, data)
                elif rule.validation_function == 'validate_data_consistency':
                    result = self._validate_data_consistency(rule, data)
                elif rule.validation_function == 'validate_data_timeliness':
                    result = self._validate_data_timeliness(rule, data)
                else:
                    result = ComplianceResult(
                        rule_id=rule.rule_id,
                        status='not_applicable',
                        message=f'Validation function {rule.validation_function} not implemented'
                    )
                
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Error validating data quality rule {rule.rule_id}: {e}")
                results.append(ComplianceResult(
                    rule_id=rule.rule_id,
                    status='non_compliant',
                    message=f'Data quality validation error: {str(e)}'
                ))
        
        return results
    
    def _validate_data_completeness(self, rule: ComplianceRule, data: Dict[str, Any]) -> ComplianceResult:
        """Validate data completeness"""
        required_fields = ['entity_id', 'calculation_date', 'bi_data', 'loss_data']
        missing_fields = []
        
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='non_compliant',
                message=f'Missing required fields: {", ".join(missing_fields)}',
                details={'missing_fields': missing_fields}
            )
        
        return ComplianceResult(
            rule_id=rule.rule_id,
            status='compliant',
            message='All required fields are present'
        )
    
    def _validate_data_accuracy(self, rule: ComplianceRule, data: Dict[str, Any]) -> ComplianceResult:
        """Validate data accuracy"""
        accuracy_issues = []
        
        # Check BI data accuracy
        bi_data = data.get('bi_data', [])
        for bi_record in bi_data:
            ildc = bi_record.get('ildc', Decimal('0'))
            sc = bi_record.get('sc', Decimal('0'))
            fc = bi_record.get('fc', Decimal('0'))
            
            # Check for unrealistic values
            if ildc < 0 or sc < 0 or fc < 0:
                accuracy_issues.append('Negative BI components detected')
            
            if ildc > Decimal('1e15') or sc > Decimal('1e15') or fc > Decimal('1e15'):
                accuracy_issues.append('Unrealistically large BI components detected')
        
        # Check loss data accuracy
        loss_data = data.get('loss_data', {})
        loss_events = loss_data.get('loss_events', [])
        for loss_event in loss_events:
            net_loss = loss_event.get('net_loss', Decimal('0'))
            
            if net_loss < 0:
                accuracy_issues.append('Negative loss amounts detected')
            
            if net_loss > Decimal('1e12'):  # > ₹1,00,000 crore
                accuracy_issues.append('Unrealistically large loss amounts detected')
        
        if accuracy_issues:
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='non_compliant',
                message=f'Data accuracy issues: {"; ".join(accuracy_issues)}',
                details={'accuracy_issues': accuracy_issues}
            )
        
        return ComplianceResult(
            rule_id=rule.rule_id,
            status='compliant',
            message='Data accuracy checks passed'
        )
    
    def _validate_data_consistency(self, rule: ComplianceRule, data: Dict[str, Any]) -> ComplianceResult:
        """Validate data consistency"""
        consistency_issues = []
        
        # Check entity_id consistency
        entity_id = data.get('entity_id')
        bi_data = data.get('bi_data', [])
        loss_data = data.get('loss_data', {})
        
        for bi_record in bi_data:
            if bi_record.get('entity_id') != entity_id:
                consistency_issues.append('Entity ID mismatch in BI data')
                break
        
        loss_events = loss_data.get('loss_events', [])
        for loss_event in loss_events:
            if loss_event.get('entity_id') != entity_id:
                consistency_issues.append('Entity ID mismatch in loss data')
                break
        
        if consistency_issues:
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='non_compliant',
                message=f'Data consistency issues: {"; ".join(consistency_issues)}',
                details={'consistency_issues': consistency_issues}
            )
        
        return ComplianceResult(
            rule_id=rule.rule_id,
            status='compliant',
            message='Data consistency checks passed'
        )
    
    def _validate_data_timeliness(self, rule: ComplianceRule, data: Dict[str, Any]) -> ComplianceResult:
        """Validate data timeliness"""
        calculation_date = data.get('calculation_date')
        if not calculation_date:
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='non_compliant',
                message='No calculation date provided'
            )
        
        # Check if calculation date is reasonable (not too far in future or past)
        if isinstance(calculation_date, str):
            try:
                calc_date = datetime.strptime(calculation_date, '%Y-%m-%d').date()
            except ValueError:
                return ComplianceResult(
                    rule_id=rule.rule_id,
                    status='non_compliant',
                    message='Invalid calculation date format'
                )
        else:
            calc_date = calculation_date
        
        today = date.today()
        if calc_date > today:
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='warning',
                message='Calculation date is in the future',
                details={'calculation_date': str(calc_date), 'today': str(today)}
            )
        
        # Check if data is too old (more than 5 years)
        years_old = (today - calc_date).days / 365.25
        if years_old > 5:
            return ComplianceResult(
                rule_id=rule.rule_id,
                status='warning',
                message=f'Calculation date is {years_old:.1f} years old',
                details={'calculation_date': str(calc_date), 'years_old': years_old}
            )
        
        return ComplianceResult(
            rule_id=rule.rule_id,
            status='compliant',
            message='Data timeliness checks passed'
        )
    
    def generate_compliance_report(self, compliance_results: List[ComplianceResult]) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        if not compliance_results:
            return {'error': 'No compliance results provided'}
        
        # Categorize results
        compliant = [r for r in compliance_results if r.status == 'compliant']
        non_compliant = [r for r in compliance_results if r.status == 'non_compliant']
        warnings = [r for r in compliance_results if r.status == 'warning']
        not_applicable = [r for r in compliance_results if r.status == 'not_applicable']
        
        # Calculate compliance rate
        total_applicable = len(compliance_results) - len(not_applicable)
        compliance_rate = (len(compliant) / total_applicable * 100) if total_applicable > 0 else 0
        
        # Categorize by severity
        critical_issues = []
        high_issues = []
        medium_issues = []
        low_issues = []
        
        for result in non_compliant + warnings:
            # Find the rule to get severity
            rule = None
            for rule_list in [self.rbi_rules, self.basel_rules, self.data_quality_rules]:
                rule = next((r for r in rule_list if r.rule_id == result.rule_id), None)
                if rule:
                    break
            
            if rule:
                if rule.severity == 'critical':
                    critical_issues.append(result)
                elif rule.severity == 'high':
                    high_issues.append(result)
                elif rule.severity == 'medium':
                    medium_issues.append(result)
                else:
                    low_issues.append(result)
        
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'summary': {
                'total_rules_checked': len(compliance_results),
                'compliant': len(compliant),
                'non_compliant': len(non_compliant),
                'warnings': len(warnings),
                'not_applicable': len(not_applicable),
                'compliance_rate_percent': round(compliance_rate, 2),
                'overall_status': 'compliant' if len(non_compliant) == 0 else 'non_compliant'
            },
            'issues_by_severity': {
                'critical': len(critical_issues),
                'high': len(high_issues),
                'medium': len(medium_issues),
                'low': len(low_issues)
            },
            'detailed_results': [
                {
                    'rule_id': r.rule_id,
                    'status': r.status,
                    'message': r.message,
                    'details': r.details,
                    'evidence': r.evidence
                }
                for r in compliance_results
            ],
            'critical_issues': [
                {
                    'rule_id': r.rule_id,
                    'message': r.message,
                    'details': r.details
                }
                for r in critical_issues
            ],
            'recommendations': self._generate_compliance_recommendations(non_compliant, warnings)
        }
        
        return report
    
    def _generate_compliance_recommendations(self, non_compliant: List[ComplianceResult], 
                                           warnings: List[ComplianceResult]) -> List[Dict[str, str]]:
        """Generate compliance recommendations"""
        recommendations = []
        
        for result in non_compliant:
            if 'BI calculation' in result.message:
                recommendations.append({
                    'rule_id': result.rule_id,
                    'priority': 'critical',
                    'recommendation': 'Review and correct Business Indicator calculation methodology to comply with RBI Max/Min/Abs operations'
                })
            elif 'threshold' in result.message.lower():
                recommendations.append({
                    'rule_id': result.rule_id,
                    'priority': 'critical',
                    'recommendation': 'Update bucket thresholds to match RBI requirements (₹8,000 crore and ₹2,40,000 crore)'
                })
            elif 'coefficient' in result.message.lower():
                recommendations.append({
                    'rule_id': result.rule_id,
                    'priority': 'critical',
                    'recommendation': 'Correct marginal coefficients to RBI specified values (12%, 15%, 18%)'
                })
            elif 'ILM' in result.message:
                recommendations.append({
                    'rule_id': result.rule_id,
                    'priority': 'critical',
                    'recommendation': 'Review ILM calculation and gating logic to ensure compliance with RBI methodology'
                })
            else:
                recommendations.append({
                    'rule_id': result.rule_id,
                    'priority': 'high',
                    'recommendation': f'Address compliance issue: {result.message}'
                })
        
        for result in warnings:
            recommendations.append({
                'rule_id': result.rule_id,
                'priority': 'medium',
                'recommendation': f'Review warning: {result.message}'
            })
        
        return recommendations