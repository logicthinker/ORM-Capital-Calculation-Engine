"""
Synthetic Data Generator for Comprehensive Test Coverage

Generates realistic synthetic data for testing all aspects of the ORM Capital Calculator
including edge cases, boundary conditions, and stress scenarios.
"""

import random
import numpy as np
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from faker import Faker
from dataclasses import dataclass
import json

fake = Faker('en_IN')


@dataclass
class SyntheticBIData:
    """Synthetic Business Indicator data"""
    entity_id: str
    period: str
    ildc: Decimal
    sc: Decimal
    fc: Decimal
    calculation_date: date


@dataclass
class SyntheticLossData:
    """Synthetic Loss Event data"""
    event_id: str
    entity_id: str
    accounting_date: date
    net_loss: Decimal
    is_excluded: bool = False
    exclusion_reason: Optional[str] = None


class SyntheticDataGenerator:
    """Comprehensive synthetic data generator for testing"""
    
    def __init__(self):
        self.rng = np.random.RandomState(42)  # Fixed seed for reproducibility
        self.entity_names = self._generate_entity_names()
        
    def _generate_entity_names(self) -> List[str]:
        """Generate realistic bank entity names"""
        prefixes = ['State Bank', 'National Bank', 'Commercial Bank', 'Regional Bank', 
                   'Urban Bank', 'Cooperative Bank', 'Development Bank']
        suffixes = ['of India', 'of Maharashtra', 'of Gujarat', 'of Karnataka', 
                   'of Tamil Nadu', 'of Punjab', 'Limited', 'Corporation']
        
        entities = []
        for i in range(100):
            if i < 50:
                # Realistic combinations
                prefix = self.rng.choice(prefixes)
                suffix = self.rng.choice(suffixes)
                entities.append(f"{prefix} {suffix}")
            else:
                # Test entities
                entities.append(f"TEST_BANK_{i-49:03d}")
        
        return entities
    
    def generate_bi_test_data(self) -> Dict[str, Any]:
        """Generate Business Indicator test data"""
        entity_id = self.rng.choice(self.entity_names)
        
        # Generate realistic BI components with various scenarios
        scenario = self.rng.choice([
            'normal', 'high_growth', 'declining', 'volatile', 
            'zero_components', 'negative_components', 'boundary_values'
        ])
        
        if scenario == 'normal':
            ildc = Decimal(str(self.rng.uniform(1e10, 1e12)))  # ₹1,000-1,00,000 crore
            sc = Decimal(str(self.rng.uniform(5e9, 5e11)))     # ₹500-50,000 crore
            fc = Decimal(str(self.rng.uniform(2e9, 2e11)))     # ₹200-20,000 crore
        elif scenario == 'high_growth':
            base_ildc = self.rng.uniform(5e10, 2e12)
            ildc = Decimal(str(base_ildc))
            sc = Decimal(str(base_ildc * 0.3))
            fc = Decimal(str(base_ildc * 0.15))
        elif scenario == 'declining':
            base_ildc = self.rng.uniform(1e10, 5e11)
            ildc = Decimal(str(base_ildc))
            sc = Decimal(str(base_ildc * 0.2))
            fc = Decimal(str(base_ildc * 0.1))
        elif scenario == 'volatile':
            ildc = Decimal(str(self.rng.uniform(-1e11, 2e12)))
            sc = Decimal(str(self.rng.uniform(-5e10, 1e12)))
            fc = Decimal(str(self.rng.uniform(-2e10, 5e11)))
        elif scenario == 'zero_components':
            components = [Decimal('0'), Decimal('0'), Decimal('0')]
            self.rng.shuffle(components)
            ildc, sc, fc = components[0], components[1], Decimal(str(self.rng.uniform(1e9, 1e11)))
        elif scenario == 'negative_components':
            ildc = Decimal(str(self.rng.uniform(-1e11, 1e11)))
            sc = Decimal(str(self.rng.uniform(-5e10, 5e10)))
            fc = Decimal(str(self.rng.uniform(-2e10, 2e10)))
        else:  # boundary_values
            boundary_values = [
                Decimal('79999999999'),    # Just below Bucket 1/2 threshold
                Decimal('80000000000'),    # Exactly Bucket 1/2 threshold
                Decimal('80000000001'),    # Just above Bucket 1/2 threshold
                Decimal('2399999999999'),  # Just below Bucket 2/3 threshold
                Decimal('2400000000000'),  # Exactly Bucket 2/3 threshold
                Decimal('2400000000001'),  # Just above Bucket 2/3 threshold
            ]
            total_bi = self.rng.choice(boundary_values)
            ildc = total_bi * Decimal('0.6')
            sc = total_bi * Decimal('0.25')
            fc = total_bi * Decimal('0.15')
        
        return {
            'entity_id': entity_id,
            'period': str(self.rng.randint(2020, 2024)),
            'ildc': ildc,
            'sc': sc,
            'fc': fc,
            'calculation_date': fake.date_between(start_date='-3y', end_date='today'),
            'scenario': scenario
        }
    
    def generate_bic_test_data(self) -> Dict[str, Any]:
        """Generate BIC calculation test data"""
        # Generate BI data for 3 years
        bi_data = []
        entity_id = self.rng.choice(self.entity_names)
        
        for year in range(2021, 2024):
            bi_data.append(self.generate_bi_test_data())
            bi_data[-1]['period'] = str(year)
            bi_data[-1]['entity_id'] = entity_id
        
        return {
            'entity_id': entity_id,
            'bi_data': bi_data,
            'calculation_date': date(2023, 12, 31)
        }
    
    def generate_loss_test_data(self) -> Dict[str, Any]:
        """Generate loss data for testing"""
        entity_id = self.rng.choice(self.entity_names)
        loss_events = []
        
        # Generate 10 years of loss data
        for year in range(2014, 2024):
            num_losses = self.rng.poisson(3)  # Average 3 losses per year
            
            for i in range(num_losses):
                # Loss amount distribution (log-normal for realistic distribution)
                loss_amount = self.rng.lognormal(mean=16, sigma=1.5)  # Mean ~₹8.8 crore
                loss_amount = max(loss_amount, 1000000)  # Minimum ₹10 lakh
                
                # Some losses are excluded
                is_excluded = self.rng.random() < 0.05  # 5% exclusion rate
                
                loss_events.append({
                    'event_id': f"SYNTH_LOSS_{entity_id}_{year}_{i+1:02d}",
                    'entity_id': entity_id,
                    'accounting_date': date(year, self.rng.randint(1, 12), 15),
                    'net_loss': Decimal(str(int(loss_amount))),
                    'is_excluded': is_excluded,
                    'exclusion_reason': 'RBI approved exclusion' if is_excluded else None
                })
        
        return {
            'entity_id': entity_id,
            'loss_events': loss_events,
            'total_losses': len(loss_events),
            'excluded_losses': sum(1 for loss in loss_events if loss['is_excluded'])
        }
    
    def generate_ilm_test_data(self) -> Dict[str, Any]:
        """Generate ILM calculation test data"""
        entity_id = self.rng.choice(self.entity_names)
        
        # Generate BIC and LC data
        bic_data = self.generate_bic_test_data()
        loss_data = self.generate_loss_test_data()
        
        # Generate scenarios for ILM gating
        scenario = self.rng.choice([
            'normal_calculation',
            'bucket_1_gating',
            'insufficient_data_gating',
            'national_discretion',
            'supervisor_override'
        ])
        
        gating_config = {
            'scenario': scenario,
            'bucket_1_gating': scenario == 'bucket_1_gating',
            'insufficient_data': scenario == 'insufficient_data_gating',
            'national_discretion': scenario == 'national_discretion',
            'supervisor_override': scenario == 'supervisor_override'
        }
        
        return {
            'entity_id': entity_id,
            'bic_data': bic_data,
            'loss_data': loss_data,
            'gating_config': gating_config
        }
    
    def generate_edge_case_data(self) -> Dict[str, Any]:
        """Generate edge case test data"""
        edge_cases = [
            'zero_bi_all_years',
            'negative_bi_components',
            'extremely_large_values',
            'extremely_small_values',
            'missing_data_years',
            'all_losses_excluded',
            'no_losses_recorded',
            'single_massive_loss',
            'precision_boundary_values'
        ]
        
        case_type = self.rng.choice(edge_cases)
        entity_id = f"EDGE_CASE_{case_type.upper()}"
        
        if case_type == 'zero_bi_all_years':
            bi_data = []
            for year in range(2021, 2024):
                bi_data.append({
                    'entity_id': entity_id,
                    'period': str(year),
                    'ildc': Decimal('0'),
                    'sc': Decimal('0'),
                    'fc': Decimal('0'),
                    'calculation_date': date(year, 12, 31)
                })
        elif case_type == 'negative_bi_components':
            bi_data = []
            for year in range(2021, 2024):
                bi_data.append({
                    'entity_id': entity_id,
                    'period': str(year),
                    'ildc': Decimal(str(self.rng.uniform(-1e11, -1e10))),
                    'sc': Decimal(str(self.rng.uniform(-5e10, -5e9))),
                    'fc': Decimal(str(self.rng.uniform(-2e10, -2e9))),
                    'calculation_date': date(year, 12, 31)
                })
        elif case_type == 'extremely_large_values':
            bi_data = []
            for year in range(2021, 2024):
                bi_data.append({
                    'entity_id': entity_id,
                    'period': str(year),
                    'ildc': Decimal('1e15'),  # ₹100,00,000 crore
                    'sc': Decimal('5e14'),    # ₹50,00,000 crore
                    'fc': Decimal('2e14'),    # ₹20,00,000 crore
                    'calculation_date': date(year, 12, 31)
                })
        else:
            # Default case
            bi_data = [self.generate_bi_test_data() for _ in range(3)]
        
        return {
            'case_type': case_type,
            'entity_id': entity_id,
            'test_data': bi_data
        }
    
    def generate_boundary_test_data(self) -> Dict[str, Any]:
        """Generate boundary condition test data"""
        boundary_scenarios = [
            'bucket_1_2_threshold_exact',
            'bucket_1_2_threshold_below',
            'bucket_1_2_threshold_above',
            'bucket_2_3_threshold_exact',
            'bucket_2_3_threshold_below',
            'bucket_2_3_threshold_above',
            'minimum_loss_threshold',
            'zero_boundary',
            'negative_boundary'
        ]
        
        scenario = self.rng.choice(boundary_scenarios)
        entity_id = f"BOUNDARY_{scenario.upper()}"
        
        if scenario == 'bucket_1_2_threshold_exact':
            total_bi = Decimal('80000000000')  # Exactly ₹8,000 crore
        elif scenario == 'bucket_1_2_threshold_below':
            total_bi = Decimal('79999999999')  # Just below ₹8,000 crore
        elif scenario == 'bucket_1_2_threshold_above':
            total_bi = Decimal('80000000001')  # Just above ₹8,000 crore
        elif scenario == 'bucket_2_3_threshold_exact':
            total_bi = Decimal('2400000000000')  # Exactly ₹2,40,000 crore
        elif scenario == 'bucket_2_3_threshold_below':
            total_bi = Decimal('2399999999999')  # Just below ₹2,40,000 crore
        elif scenario == 'bucket_2_3_threshold_above':
            total_bi = Decimal('2400000000001')  # Just above ₹2,40,000 crore
        else:
            total_bi = Decimal(str(self.rng.uniform(1e10, 1e12)))
        
        # Distribute total BI across components
        ildc = total_bi * Decimal('0.6')
        sc = total_bi * Decimal('0.25')
        fc = total_bi * Decimal('0.15')
        
        bi_data = []
        for year in range(2021, 2024):
            # Add some variation year over year
            variation = Decimal(str(self.rng.uniform(0.95, 1.05)))
            bi_data.append({
                'entity_id': entity_id,
                'period': str(year),
                'ildc': ildc * variation,
                'sc': sc * variation,
                'fc': fc * variation,
                'calculation_date': date(year, 12, 31)
            })
        
        return {
            'scenario': scenario,
            'entity_id': entity_id,
            'boundary_value': total_bi,
            'bi_data': bi_data
        }
    
    def generate_complete_workflow_data(self) -> Dict[str, Any]:
        """Generate complete workflow test data"""
        entity_id = self.rng.choice(self.entity_names)
        
        # Generate comprehensive data for complete workflow
        bi_data = self.generate_bic_test_data()
        loss_data = self.generate_loss_test_data()
        
        # Add corporate actions
        corporate_actions = []
        if self.rng.random() < 0.3:  # 30% chance of corporate action
            action_type = self.rng.choice(['acquisition', 'divestiture'])
            corporate_actions.append({
                'action_type': action_type,
                'effective_date': fake.date_between(start_date='-2y', end_date='today'),
                'entity_affected': f"ACQUIRED_ENTITY_{self.rng.randint(1, 100)}",
                'rbi_approval': True,
                'disclosure_required': True
            })
        
        # Add supervisor overrides
        supervisor_overrides = []
        if self.rng.random() < 0.1:  # 10% chance of override
            supervisor_overrides.append({
                'override_type': 'ilm_override',
                'override_value': Decimal('1.0'),
                'reason': 'Regulatory discretion applied',
                'approver': 'Chief Risk Officer',
                'approval_date': fake.date_between(start_date='-1y', end_date='today')
            })
        
        return {
            'entity_id': entity_id,
            'bi_data': bi_data,
            'loss_data': loss_data,
            'corporate_actions': corporate_actions,
            'supervisor_overrides': supervisor_overrides,
            'calculation_date': date(2023, 12, 31)
        }
    
    def generate_api_test_data(self) -> Dict[str, Any]:
        """Generate API test data"""
        request_types = [
            'sync_calculation',
            'async_calculation',
            'parameter_update',
            'lineage_query',
            'job_status_query'
        ]
        
        request_type = self.rng.choice(request_types)
        
        if request_type == 'sync_calculation':
            return {
                'request_type': request_type,
                'method': 'POST',
                'endpoint': '/api/v1/calculation-jobs',
                'payload': {
                    'model_name': 'sma',
                    'execution_mode': 'sync',
                    'entity_id': self.rng.choice(self.entity_names),
                    'calculation_date': '2023-12-31',
                    'idempotency_key': fake.uuid4()
                }
            }
        elif request_type == 'async_calculation':
            return {
                'request_type': request_type,
                'method': 'POST',
                'endpoint': '/api/v1/calculation-jobs',
                'payload': {
                    'model_name': 'sma',
                    'execution_mode': 'async',
                    'entity_id': self.rng.choice(self.entity_names),
                    'calculation_date': '2023-12-31',
                    'callback_url': 'https://callback.example.com/webhook',
                    'idempotency_key': fake.uuid4()
                }
            }
        else:
            return {
                'request_type': request_type,
                'method': 'GET',
                'endpoint': f'/api/v1/{request_type.replace("_", "-")}',
                'query_params': {'entity_id': self.rng.choice(self.entity_names)}
            }
    
    def generate_db_test_data(self) -> Dict[str, Any]:
        """Generate database test data"""
        operations = [
            'insert_bi_data',
            'insert_loss_data',
            'update_calculation_result',
            'query_historical_data',
            'bulk_insert_operations'
        ]
        
        operation = self.rng.choice(operations)
        
        if operation == 'insert_bi_data':
            return {
                'operation': operation,
                'table': 'business_indicators',
                'data': self.generate_bi_test_data()
            }
        elif operation == 'insert_loss_data':
            return {
                'operation': operation,
                'table': 'loss_events',
                'data': self.generate_loss_test_data()
            }
        elif operation == 'bulk_insert_operations':
            return {
                'operation': operation,
                'batch_size': self.rng.randint(100, 1000),
                'data_type': self.rng.choice(['bi_data', 'loss_data']),
                'concurrent_operations': self.rng.randint(1, 10)
            }
        else:
            return {
                'operation': operation,
                'entity_id': self.rng.choice(self.entity_names),
                'date_range': {
                    'start_date': '2020-01-01',
                    'end_date': '2023-12-31'
                }
            }
    
    def generate_job_test_data(self) -> Dict[str, Any]:
        """Generate job management test data"""
        job_scenarios = [
            'normal_job_execution',
            'long_running_job',
            'job_failure_recovery',
            'concurrent_job_execution',
            'job_cancellation',
            'webhook_delivery_failure'
        ]
        
        scenario = self.rng.choice(job_scenarios)
        
        return {
            'scenario': scenario,
            'job_id': fake.uuid4(),
            'entity_id': self.rng.choice(self.entity_names),
            'model_name': self.rng.choice(['sma', 'bia', 'tsa']),
            'execution_mode': self.rng.choice(['sync', 'async']),
            'estimated_duration': self.rng.randint(10, 1800),  # 10 seconds to 30 minutes
            'callback_url': 'https://callback.example.com/webhook' if scenario != 'webhook_delivery_failure' else 'https://invalid-callback.example.com/webhook',
            'priority': self.rng.choice(['low', 'normal', 'high']),
            'retry_count': self.rng.randint(0, 3)
        }
    
    def generate_comprehensive_scenario(self) -> Dict[str, Any]:
        """Generate comprehensive synthetic scenario"""
        scenario_types = [
            'multi_entity_calculation',
            'historical_data_analysis',
            'stress_test_scenario',
            'regulatory_reporting_scenario',
            'data_migration_scenario'
        ]
        
        scenario_type = self.rng.choice(scenario_types)
        
        if scenario_type == 'multi_entity_calculation':
            entities = self.rng.choice(self.entity_names, size=self.rng.randint(5, 20), replace=False)
            return {
                'scenario_type': scenario_type,
                'entities': entities.tolist(),
                'calculation_date': '2023-12-31',
                'parallel_execution': True,
                'consolidation_required': True
            }
        elif scenario_type == 'stress_test_scenario':
            return {
                'scenario_type': scenario_type,
                'stress_factors': {
                    'loss_multiplier': self.rng.uniform(1.2, 2.0),
                    'bi_reduction': self.rng.uniform(0.7, 0.9),
                    'recovery_haircut': self.rng.uniform(0.3, 0.7)
                },
                'entities': self.rng.choice(self.entity_names, size=10, replace=False).tolist()
            }
        else:
            return {
                'scenario_type': scenario_type,
                'entity_id': self.rng.choice(self.entity_names),
                'data_volume': self.rng.choice(['small', 'medium', 'large', 'xlarge']),
                'complexity': self.rng.choice(['simple', 'moderate', 'complex'])
            }
    
    def generate_performance_test_dataset(self, size: str = 'medium') -> Dict[str, Any]:
        """Generate performance test datasets of various sizes"""
        size_configs = {
            'small': {'entities': 10, 'years': 3, 'losses_per_year': 5},
            'medium': {'entities': 50, 'years': 5, 'losses_per_year': 10},
            'large': {'entities': 100, 'years': 10, 'losses_per_year': 20},
            'xlarge': {'entities': 500, 'years': 10, 'losses_per_year': 50}
        }
        
        config = size_configs.get(size, size_configs['medium'])
        
        # Generate entities
        entities = [f"PERF_TEST_ENTITY_{i+1:03d}" for i in range(config['entities'])]
        
        # Generate BI data
        bi_data = []
        for entity in entities:
            for year in range(2024 - config['years'], 2024):
                bi_data.append({
                    'entity_id': entity,
                    'period': str(year),
                    'ildc': Decimal(str(self.rng.uniform(1e10, 1e12))),
                    'sc': Decimal(str(self.rng.uniform(5e9, 5e11))),
                    'fc': Decimal(str(self.rng.uniform(2e9, 2e11))),
                    'calculation_date': date(year, 12, 31)
                })
        
        # Generate loss data
        loss_data = []
        for entity in entities:
            for year in range(2024 - config['years'], 2024):
                for i in range(config['losses_per_year']):
                    loss_data.append({
                        'event_id': f"PERF_LOSS_{entity}_{year}_{i+1:02d}",
                        'entity_id': entity,
                        'accounting_date': date(year, self.rng.randint(1, 12), 15),
                        'net_loss': Decimal(str(self.rng.lognormal(16, 1.5))),
                        'is_excluded': False
                    })
        
        return {
            'size': size,
            'config': config,
            'entities': entities,
            'bi_data': bi_data,
            'loss_data': loss_data,
            'total_records': len(bi_data) + len(loss_data)
        }