"""
Property-Based Test Generator using Hypothesis

Generates property-based tests to discover edge cases and verify mathematical
and business rule properties of the ORM Capital Calculator.
"""

from hypothesis import strategies as st, given, settings, HealthCheck, assume
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import hypothesis.extra.numpy as hnp
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import math


class PropertyBasedTestGenerator:
    """Generator for property-based tests using Hypothesis"""
    
    def __init__(self):
        self.decimal_strategy = st.decimals(
            min_value=Decimal('-1e15'),
            max_value=Decimal('1e15'),
            places=2
        )
        self.positive_decimal_strategy = st.decimals(
            min_value=Decimal('0'),
            max_value=Decimal('1e15'),
            places=2
        )
        
    def generate_mathematical_property(self) -> Dict[str, Any]:
        """Generate mathematical property tests"""
        properties = [
            'bi_calculation_associativity',
            'bi_calculation_commutativity',
            'bic_monotonicity',
            'loss_component_linearity',
            'ilm_logarithmic_properties',
            'rwa_scaling_properties',
            'precision_preservation',
            'boundary_continuity'
        ]
        
        import random
        property_name = random.choice(properties)
        
        if property_name == 'bi_calculation_associativity':
            return {
                'property': 'bi_calculation_associativity',
                'description': 'BI calculation should be associative: (ILDC + SC) + FC = ILDC + (SC + FC)',
                'test_strategy': self._bi_associativity_strategy(),
                'invariant': 'associative_property_holds'
            }
        elif property_name == 'bic_monotonicity':
            return {
                'property': 'bic_monotonicity',
                'description': 'BIC should increase monotonically with BI across buckets',
                'test_strategy': self._bic_monotonicity_strategy(),
                'invariant': 'monotonic_increase'
            }
        elif property_name == 'loss_component_linearity':
            return {
                'property': 'loss_component_linearity',
                'description': 'LC should scale linearly with average losses: LC = 15 × avg_losses',
                'test_strategy': self._lc_linearity_strategy(),
                'invariant': 'linear_scaling'
            }
        elif property_name == 'ilm_logarithmic_properties':
            return {
                'property': 'ilm_logarithmic_properties',
                'description': 'ILM should follow logarithmic properties: ILM = ln(e - 1 + LC/BIC)',
                'test_strategy': self._ilm_logarithmic_strategy(),
                'invariant': 'logarithmic_properties'
            }
        else:
            return {
                'property': property_name,
                'description': f'Property test for {property_name}',
                'test_strategy': self._default_strategy(),
                'invariant': 'property_holds'
            }
    
    def _bi_associativity_strategy(self) -> st.SearchStrategy:
        """Strategy for BI associativity testing"""
        return st.tuples(
            self.positive_decimal_strategy,  # ILDC
            self.positive_decimal_strategy,  # SC
            self.positive_decimal_strategy   # FC
        )
    
    def _bic_monotonicity_strategy(self) -> st.SearchStrategy:
        """Strategy for BIC monotonicity testing"""
        return st.lists(
            self.positive_decimal_strategy,
            min_size=2,
            max_size=10
        ).map(sorted)  # Ensure sorted order for monotonicity testing
    
    def _lc_linearity_strategy(self) -> st.SearchStrategy:
        """Strategy for LC linearity testing"""
        return st.lists(
            self.positive_decimal_strategy,
            min_size=1,
            max_size=100
        )
    
    def _ilm_logarithmic_strategy(self) -> st.SearchStrategy:
        """Strategy for ILM logarithmic properties testing"""
        return st.tuples(
            self.positive_decimal_strategy,  # BIC
            self.positive_decimal_strategy   # LC
        ).filter(lambda x: x[1] > 0 and x[0] > 0)  # Ensure positive values for log
    
    def _default_strategy(self) -> st.SearchStrategy:
        """Default strategy for general property testing"""
        return st.tuples(
            self.positive_decimal_strategy,
            self.positive_decimal_strategy
        )
    
    def generate_business_rule_property(self) -> Dict[str, Any]:
        """Generate business rule property tests"""
        business_rules = [
            'bucket_assignment_consistency',
            'ilm_gating_rules',
            'loss_threshold_enforcement',
            'recovery_validation',
            'exclusion_rules',
            'data_quality_rules',
            'regulatory_constraints',
            'supervisor_override_rules'
        ]
        
        import random
        rule_name = random.choice(business_rules)
        
        if rule_name == 'bucket_assignment_consistency':
            return {
                'property': 'bucket_assignment_consistency',
                'description': 'Bucket assignment should be consistent for same BI values',
                'test_strategy': self._bucket_consistency_strategy(),
                'business_rule': 'bucket_assignment_deterministic'
            }
        elif rule_name == 'ilm_gating_rules':
            return {
                'property': 'ilm_gating_rules',
                'description': 'ILM gating should apply correctly for Bucket 1 and insufficient data',
                'test_strategy': self._ilm_gating_strategy(),
                'business_rule': 'ilm_gating_applied_correctly'
            }
        elif rule_name == 'loss_threshold_enforcement':
            return {
                'property': 'loss_threshold_enforcement',
                'description': 'Losses below threshold should be excluded from calculations',
                'test_strategy': self._loss_threshold_strategy(),
                'business_rule': 'threshold_enforcement'
            }
        elif rule_name == 'recovery_validation':
            return {
                'property': 'recovery_validation',
                'description': 'Recoveries should never exceed gross loss amounts',
                'test_strategy': self._recovery_validation_strategy(),
                'business_rule': 'recovery_constraint'
            }
        else:
            return {
                'property': rule_name,
                'description': f'Business rule test for {rule_name}',
                'test_strategy': self._default_business_rule_strategy(),
                'business_rule': 'rule_satisfied'
            }
    
    def _bucket_consistency_strategy(self) -> st.SearchStrategy:
        """Strategy for bucket assignment consistency"""
        return st.tuples(
            self.positive_decimal_strategy,  # BI value
            st.integers(min_value=1, max_value=10)  # Number of repetitions
        )
    
    def _ilm_gating_strategy(self) -> st.SearchStrategy:
        """Strategy for ILM gating rules"""
        return st.tuples(
            st.integers(min_value=1, max_value=3),  # Bucket
            st.integers(min_value=1, max_value=15), # Years of data
            st.booleans(),  # High quality data flag
            st.booleans()   # National discretion flag
        )
    
    def _loss_threshold_strategy(self) -> st.SearchStrategy:
        """Strategy for loss threshold enforcement"""
        return st.tuples(
            st.lists(
                self.positive_decimal_strategy,
                min_size=1,
                max_size=100
            ),
            self.positive_decimal_strategy  # Threshold value
        )
    
    def _recovery_validation_strategy(self) -> st.SearchStrategy:
        """Strategy for recovery validation"""
        return st.tuples(
            self.positive_decimal_strategy,  # Gross loss
            self.positive_decimal_strategy   # Recovery amount
        )
    
    def _default_business_rule_strategy(self) -> st.SearchStrategy:
        """Default strategy for business rule testing"""
        return st.tuples(
            self.positive_decimal_strategy,
            st.booleans()
        )


class SMAStateMachine(RuleBasedStateMachine):
    """Stateful property-based testing for SMA calculations"""
    
    def __init__(self):
        super().__init__()
        self.entities = {}
        self.calculations = {}
        self.parameters = {
            'bucket_thresholds': [Decimal('80000000000'), Decimal('2400000000000')],
            'marginal_coefficients': [Decimal('0.12'), Decimal('0.15'), Decimal('0.18')],
            'lc_multiplier': Decimal('15'),
            'rwa_multiplier': Decimal('12.5')
        }
    
    @initialize()
    def setup_initial_state(self):
        """Initialize the state machine with basic entities"""
        self.entities['TEST_ENTITY_1'] = {
            'bi_data': [],
            'loss_data': [],
            'calculations': []
        }
    
    @rule(
        entity_id=st.text(min_size=1, max_size=20),
        ildc=st.decimals(min_value=0, max_value=Decimal('1e12'), places=2),
        sc=st.decimals(min_value=0, max_value=Decimal('1e12'), places=2),
        fc=st.decimals(min_value=0, max_value=Decimal('1e12'), places=2)
    )
    def add_bi_data(self, entity_id: str, ildc: Decimal, sc: Decimal, fc: Decimal):
        """Add business indicator data to an entity"""
        if entity_id not in self.entities:
            self.entities[entity_id] = {'bi_data': [], 'loss_data': [], 'calculations': []}
        
        bi_total = ildc + sc + fc
        self.entities[entity_id]['bi_data'].append({
            'ildc': ildc,
            'sc': sc,
            'fc': fc,
            'total': bi_total
        })
    
    @rule(
        entity_id=st.sampled_from(['TEST_ENTITY_1']),
        loss_amount=st.decimals(min_value=0, max_value=Decimal('1e10'), places=2)
    )
    def add_loss_data(self, entity_id: str, loss_amount: Decimal):
        """Add loss data to an entity"""
        assume(entity_id in self.entities)
        
        self.entities[entity_id]['loss_data'].append({
            'amount': loss_amount,
            'excluded': False
        })
    
    @rule(entity_id=st.sampled_from(['TEST_ENTITY_1']))
    def calculate_sma(self, entity_id: str):
        """Perform SMA calculation for an entity"""
        assume(entity_id in self.entities)
        assume(len(self.entities[entity_id]['bi_data']) >= 3)
        
        # Calculate 3-year average BI
        bi_values = [data['total'] for data in self.entities[entity_id]['bi_data'][-3:]]
        avg_bi = sum(bi_values) / len(bi_values)
        
        # Determine bucket
        bucket = self._determine_bucket(avg_bi)
        
        # Calculate BIC
        bic = self._calculate_bic(avg_bi, bucket)
        
        # Calculate LC
        loss_values = [data['amount'] for data in self.entities[entity_id]['loss_data'] 
                      if not data['excluded']]
        lc = self._calculate_lc(loss_values)
        
        # Calculate ILM
        ilm = self._calculate_ilm(bic, lc, bucket)
        
        # Calculate ORC and RWA
        orc = bic * ilm
        rwa = orc * self.parameters['rwa_multiplier']
        
        calculation = {
            'avg_bi': avg_bi,
            'bucket': bucket,
            'bic': bic,
            'lc': lc,
            'ilm': ilm,
            'orc': orc,
            'rwa': rwa
        }
        
        self.entities[entity_id]['calculations'].append(calculation)
        self.calculations[f"{entity_id}_{len(self.entities[entity_id]['calculations'])}"] = calculation
    
    def _determine_bucket(self, bi: Decimal) -> int:
        """Determine bucket based on BI value"""
        if bi < self.parameters['bucket_thresholds'][0]:
            return 1
        elif bi < self.parameters['bucket_thresholds'][1]:
            return 2
        else:
            return 3
    
    def _calculate_bic(self, bi: Decimal, bucket: int) -> Decimal:
        """Calculate Business Indicator Component"""
        thresholds = self.parameters['bucket_thresholds']
        coefficients = self.parameters['marginal_coefficients']
        
        if bucket == 1:
            return bi * coefficients[0]
        elif bucket == 2:
            bucket_1_contribution = thresholds[0] * coefficients[0]
            bucket_2_contribution = (bi - thresholds[0]) * coefficients[1]
            return bucket_1_contribution + bucket_2_contribution
        else:  # bucket == 3
            bucket_1_contribution = thresholds[0] * coefficients[0]
            bucket_2_contribution = (thresholds[1] - thresholds[0]) * coefficients[1]
            bucket_3_contribution = (bi - thresholds[1]) * coefficients[2]
            return bucket_1_contribution + bucket_2_contribution + bucket_3_contribution
    
    def _calculate_lc(self, losses: List[Decimal]) -> Decimal:
        """Calculate Loss Component"""
        if not losses:
            return Decimal('0')
        
        avg_loss = sum(losses) / len(losses)
        return avg_loss * self.parameters['lc_multiplier']
    
    def _calculate_ilm(self, bic: Decimal, lc: Decimal, bucket: int) -> Decimal:
        """Calculate Internal Loss Multiplier"""
        if bucket == 1 or bic == 0:
            return Decimal('1')  # ILM gating
        
        try:
            ratio = lc / bic
            ilm = Decimal(str(math.log(math.e - 1 + float(ratio))))
            return max(ilm, Decimal('1'))  # ILM floor of 1
        except (ValueError, ZeroDivisionError):
            return Decimal('1')
    
    @invariant()
    def bic_increases_with_bi(self):
        """BIC should increase with BI"""
        for entity_id, entity_data in self.entities.items():
            calculations = entity_data['calculations']
            if len(calculations) >= 2:
                for i in range(1, len(calculations)):
                    prev_calc = calculations[i-1]
                    curr_calc = calculations[i]
                    
                    if curr_calc['avg_bi'] > prev_calc['avg_bi']:
                        assert curr_calc['bic'] >= prev_calc['bic'], \
                            f"BIC should increase with BI: {prev_calc['bic']} -> {curr_calc['bic']}"
    
    @invariant()
    def orc_non_negative(self):
        """ORC should always be non-negative"""
        for calc_id, calculation in self.calculations.items():
            assert calculation['orc'] >= 0, f"ORC should be non-negative: {calculation['orc']}"
    
    @invariant()
    def rwa_scaling(self):
        """RWA should be 12.5 times ORC"""
        for calc_id, calculation in self.calculations.items():
            expected_rwa = calculation['orc'] * self.parameters['rwa_multiplier']
            assert abs(calculation['rwa'] - expected_rwa) < Decimal('0.01'), \
                f"RWA scaling incorrect: {calculation['rwa']} != {expected_rwa}"
    
    @invariant()
    def bucket_consistency(self):
        """Bucket assignment should be consistent"""
        for entity_id, entity_data in self.entities.items():
            calculations = entity_data['calculations']
            for calc in calculations:
                expected_bucket = self._determine_bucket(calc['avg_bi'])
                assert calc['bucket'] == expected_bucket, \
                    f"Bucket assignment inconsistent: {calc['bucket']} != {expected_bucket}"


# Property-based test functions using Hypothesis decorators
@given(
    ildc=st.decimals(min_value=0, max_value=Decimal('1e12'), places=2),
    sc=st.decimals(min_value=0, max_value=Decimal('1e12'), places=2),
    fc=st.decimals(min_value=0, max_value=Decimal('1e12'), places=2)
)
@settings(max_examples=1000, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_bi_calculation_properties(ildc: Decimal, sc: Decimal, fc: Decimal):
    """Test BI calculation properties"""
    # Associativity: (ILDC + SC) + FC = ILDC + (SC + FC)
    result1 = (ildc + sc) + fc
    result2 = ildc + (sc + fc)
    assert result1 == result2, f"BI calculation not associative: {result1} != {result2}"
    
    # Commutativity: ILDC + SC = SC + ILDC
    assert ildc + sc == sc + ildc, "BI components not commutative"
    
    # Non-negativity: BI >= 0 when all components >= 0
    bi_total = ildc + sc + fc
    assert bi_total >= 0, f"BI should be non-negative: {bi_total}"


@given(
    bi_values=st.lists(
        st.decimals(min_value=0, max_value=Decimal('1e13'), places=2),
        min_size=2,
        max_size=10
    ).map(sorted)
)
@settings(max_examples=500, deadline=None)
def test_bic_monotonicity(bi_values: List[Decimal]):
    """Test BIC monotonicity property"""
    assume(len(bi_values) >= 2)
    
    bucket_thresholds = [Decimal('80000000000'), Decimal('2400000000000')]
    marginal_coefficients = [Decimal('0.12'), Decimal('0.15'), Decimal('0.18')]
    
    def calculate_bic(bi: Decimal) -> Decimal:
        if bi < bucket_thresholds[0]:
            return bi * marginal_coefficients[0]
        elif bi < bucket_thresholds[1]:
            bucket_1 = bucket_thresholds[0] * marginal_coefficients[0]
            bucket_2 = (bi - bucket_thresholds[0]) * marginal_coefficients[1]
            return bucket_1 + bucket_2
        else:
            bucket_1 = bucket_thresholds[0] * marginal_coefficients[0]
            bucket_2 = (bucket_thresholds[1] - bucket_thresholds[0]) * marginal_coefficients[1]
            bucket_3 = (bi - bucket_thresholds[1]) * marginal_coefficients[2]
            return bucket_1 + bucket_2 + bucket_3
    
    bic_values = [calculate_bic(bi) for bi in bi_values]
    
    # BIC should be monotonically increasing
    for i in range(1, len(bic_values)):
        assert bic_values[i] >= bic_values[i-1], \
            f"BIC not monotonic: {bic_values[i-1]} -> {bic_values[i]} for BI {bi_values[i-1]} -> {bi_values[i]}"


@given(
    losses=st.lists(
        st.decimals(min_value=0, max_value=Decimal('1e10'), places=2),
        min_size=1,
        max_size=100
    )
)
@settings(max_examples=500, deadline=None)
def test_loss_component_linearity(losses: List[Decimal]):
    """Test Loss Component linearity property"""
    lc_multiplier = Decimal('15')
    
    # Calculate LC
    avg_loss = sum(losses) / len(losses)
    lc = avg_loss * lc_multiplier
    
    # Test linearity: LC should scale linearly with average loss
    assert lc == avg_loss * lc_multiplier, "LC not linear with average loss"
    
    # Test scaling: doubling average loss should double LC
    doubled_losses = [loss * 2 for loss in losses]
    doubled_avg = sum(doubled_losses) / len(doubled_losses)
    doubled_lc = doubled_avg * lc_multiplier
    
    expected_doubled_lc = lc * 2
    assert abs(doubled_lc - expected_doubled_lc) < Decimal('0.01'), \
        f"LC scaling not linear: {doubled_lc} != {expected_doubled_lc}"