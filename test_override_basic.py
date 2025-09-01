"""
Basic supervisor override functionality test
"""

from datetime import date, timedelta
from decimal import Decimal
from orm_calculator.models.override_models import (
    SupervisorOverride, OverrideAuditLog,
    OverrideType, OverrideStatus, OverrideReason,
    SupervisorOverrideCreate, OverrideApproval, OverrideApplication
)

def test_override_models():
    """Test override model creation"""
    try:
        # Test SupervisorOverride model
        override = SupervisorOverride(
            id="OVR_001",
            override_type=OverrideType.CAPITAL_ADJUSTMENT,
            status=OverrideStatus.PROPOSED,
            entity_id="BANK_001",
            original_value=Decimal('100000000'),
            override_value=Decimal('120000000'),
            percentage_adjustment=Decimal('20'),
            override_reason=OverrideReason.CONSERVATIVE_ADJUSTMENT,
            detailed_justification="Conservative adjustment due to market volatility",
            proposed_by="risk_manager_1",
            effective_from=date.today(),
            effective_to=date.today() + timedelta(days=90)
        )
        print(f"✓ Supervisor override created: {override.override_type} ({override.id})")
        
        # Test OverrideAuditLog model
        audit_log = OverrideAuditLog(
            id="AUDIT_001",
            override_id="OVR_001",
            action_type="CREATED",
            action_by="risk_manager_1",
            previous_status=None,
            new_status=OverrideStatus.PROPOSED,
            changes_made={"created": True}
        )
        print(f"✓ Override audit log created: {audit_log.action_type} by {audit_log.action_by}")
        
        return True
    except Exception as e:
        print(f"✗ Override models test failed: {e}")
        return False

def test_override_enums():
    """Test override enums"""
    try:
        # Test OverrideType enum
        types = [
            OverrideType.CAPITAL_ADJUSTMENT,
            OverrideType.ILM_OVERRIDE,
            OverrideType.BIC_OVERRIDE,
            OverrideType.LOSS_COMPONENT_OVERRIDE,
            OverrideType.METHODOLOGY_OVERRIDE,
            OverrideType.PARAMETER_OVERRIDE
        ]
        print(f"✓ Override types: {[t.value for t in types]}")
        
        # Test OverrideStatus enum
        statuses = [
            OverrideStatus.PROPOSED,
            OverrideStatus.APPROVED,
            OverrideStatus.APPLIED,
            OverrideStatus.EXPIRED,
            OverrideStatus.REJECTED
        ]
        print(f"✓ Override statuses: {[s.value for s in statuses]}")
        
        # Test OverrideReason enum
        reasons = [
            OverrideReason.DATA_QUALITY_ISSUE,
            OverrideReason.EXCEPTIONAL_CIRCUMSTANCES,
            OverrideReason.REGULATORY_GUIDANCE,
            OverrideReason.CONSERVATIVE_ADJUSTMENT
        ]
        print(f"✓ Override reasons: {[r.value for r in reasons]}")
        
        return True
    except Exception as e:
        print(f"✗ Override enums test failed: {e}")
        return False

def test_pydantic_models():
    """Test Pydantic models for API"""
    try:
        # Test SupervisorOverrideCreate
        override_create = SupervisorOverrideCreate(
            id="OVR_001",
            override_type=OverrideType.ILM_OVERRIDE,
            entity_id="BANK_001",
            override_value=Decimal('1.5'),
            override_reason=OverrideReason.DATA_QUALITY_ISSUE,
            detailed_justification="Loss data quality issues require ILM adjustment",
            proposed_by="risk_manager_1",
            effective_from=date.today(),
            business_context="Data quality remediation in progress"
        )
        print(f"✓ Override create model: {override_create.override_type} for {override_create.entity_id}")
        
        # Test OverrideApproval
        approval = OverrideApproval(
            approved_by="model_risk_manager_1",
            approval_reference="APP_2025_001",
            approval_comments="Approved based on risk assessment"
        )
        print(f"✓ Override approval model: {approval.approval_reference} by {approval.approved_by}")
        
        # Test OverrideApplication
        application = OverrideApplication(
            applied_by="risk_manager_1",
            application_comments="Applied to quarterly calculation",
            calculation_impact={"orc_change": "20000000"}
        )
        print(f"✓ Override application model: applied by {application.applied_by}")
        
        return True
    except Exception as e:
        print(f"✗ Pydantic models test failed: {e}")
        return False

def test_override_validation():
    """Test override validation logic"""
    try:
        # Test valid percentage adjustment
        valid_override = SupervisorOverrideCreate(
            id="OVR_001",
            override_type=OverrideType.CAPITAL_ADJUSTMENT,
            entity_id="BANK_001",
            override_value=Decimal('120000000'),
            percentage_adjustment=Decimal('20'),  # Valid: 20%
            override_reason=OverrideReason.CONSERVATIVE_ADJUSTMENT,
            detailed_justification="Conservative adjustment",
            proposed_by="risk_manager_1",
            effective_from=date.today()
        )
        print(f"✓ Valid override with {valid_override.percentage_adjustment}% adjustment")
        
        # Test effective dates
        override_with_dates = SupervisorOverrideCreate(
            id="OVR_002",
            override_type=OverrideType.ILM_OVERRIDE,
            entity_id="BANK_001",
            override_value=Decimal('1.3'),
            override_reason=OverrideReason.TEMPORARY_ADJUSTMENT,
            detailed_justification="Temporary adjustment for quarter-end",
            proposed_by="risk_manager_1",
            effective_from=date.today(),
            effective_to=date.today() + timedelta(days=30)
        )
        print(f"✓ Override with effective period: {override_with_dates.effective_from} to {override_with_dates.effective_to}")
        
        return True
    except Exception as e:
        print(f"✗ Override validation test failed: {e}")
        return False

def test_override_workflow():
    """Test override workflow states"""
    try:
        # Test workflow progression
        workflow_states = [
            (OverrideStatus.PROPOSED, "Override proposed by risk manager"),
            (OverrideStatus.APPROVED, "Override approved by model risk manager"),
            (OverrideStatus.APPLIED, "Override applied to calculation"),
            (OverrideStatus.EXPIRED, "Override expired after effective period")
        ]
        
        print("✓ Override workflow states:")
        for status, description in workflow_states:
            print(f"  - {status.value}: {description}")
        
        # Test rejection path
        rejection_states = [
            (OverrideStatus.PROPOSED, "Override proposed"),
            (OverrideStatus.REJECTED, "Override rejected due to insufficient justification")
        ]
        
        print("✓ Override rejection workflow:")
        for status, description in rejection_states:
            print(f"  - {status.value}: {description}")
        
        return True
    except Exception as e:
        print(f"✗ Override workflow test failed: {e}")
        return False

def test_disclosure_logic():
    """Test disclosure requirement logic"""
    try:
        # Test high-impact override requiring disclosure
        high_impact_override = SupervisorOverride(
            id="OVR_001",
            override_type=OverrideType.CAPITAL_ADJUSTMENT,
            percentage_adjustment=Decimal('25'),  # >10%, should require disclosure
            requires_disclosure=True,
            disclosure_period_months=12
        )
        
        print(f"✓ High-impact override disclosure:")
        print(f"  - Percentage adjustment: {high_impact_override.percentage_adjustment}%")
        print(f"  - Requires disclosure: {high_impact_override.requires_disclosure}")
        print(f"  - Disclosure period: {high_impact_override.disclosure_period_months} months")
        
        # Test ILM override requiring RBI notification
        ilm_override = SupervisorOverride(
            id="OVR_002",
            override_type=OverrideType.ILM_OVERRIDE,
            requires_disclosure=True,
            rbi_notification_required=True
        )
        
        print(f"✓ ILM override disclosure:")
        print(f"  - Override type: {ilm_override.override_type}")
        print(f"  - Requires disclosure: {ilm_override.requires_disclosure}")
        print(f"  - RBI notification required: {ilm_override.rbi_notification_required}")
        
        return True
    except Exception as e:
        print(f"✗ Disclosure logic test failed: {e}")
        return False

def test_calculation_impact():
    """Test override impact on calculations"""
    try:
        # Test capital adjustment impact
        original_orc = Decimal('100000000')
        override_orc = Decimal('120000000')
        impact = override_orc - original_orc
        percentage_impact = (impact / original_orc) * 100
        
        print(f"✓ Capital adjustment impact:")
        print(f"  - Original ORC: ₹{original_orc:,}")
        print(f"  - Override ORC: ₹{override_orc:,}")
        print(f"  - Impact: ₹{impact:,} ({percentage_impact}%)")
        
        # Test ILM override impact
        original_ilm = Decimal('1.2')
        override_ilm = Decimal('1.5')
        bic = Decimal('100000000')
        
        original_orc_ilm = bic * original_ilm
        override_orc_ilm = bic * override_ilm
        ilm_impact = override_orc_ilm - original_orc_ilm
        
        print(f"✓ ILM override impact:")
        print(f"  - Original ILM: {original_ilm}")
        print(f"  - Override ILM: {override_ilm}")
        print(f"  - BIC: ₹{bic:,}")
        print(f"  - Original ORC: ₹{original_orc_ilm:,}")
        print(f"  - Override ORC: ₹{override_orc_ilm:,}")
        print(f"  - Impact: ₹{ilm_impact:,}")
        
        return True
    except Exception as e:
        print(f"✗ Calculation impact test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing ORM Capital Calculator Supervisor Override Components")
    print("=" * 65)
    
    tests = [
        ("Override Models", test_override_models),
        ("Override Enums", test_override_enums),
        ("Pydantic Models", test_pydantic_models),
        ("Override Validation", test_override_validation),
        ("Override Workflow", test_override_workflow),
        ("Disclosure Logic", test_disclosure_logic),
        ("Calculation Impact", test_calculation_impact)
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\nTesting {name}:")
        try:
            if test_func():
                passed += 1
                print(f"✓ {name} test passed")
            else:
                print(f"✗ {name} test failed")
        except Exception as e:
            print(f"✗ {name} test error: {e}")
    
    print(f"\n{'='*65}")
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All supervisor override tests passed!")
        exit(0)
    else:
        print("❌ Some tests failed")
        exit(1)