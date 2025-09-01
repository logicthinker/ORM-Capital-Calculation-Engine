# Calculation Methods Guide

## Overview

This document provides detailed information about the calculation methods supported by the ORM Capital Calculator Engine, including mathematical formulas, implementation details, and regulatory compliance requirements.

## Standardized Measurement Approach (SMA)

### Overview

The Standardized Measurement Approach (SMA) is the primary method for calculating operational risk capital under Basel III framework as implemented by RBI.

### Mathematical Framework

#### 1. Business Indicator (BI) Calculation

```
BI = ILDC + SC + FC
```

Where:
- **ILDC**: Interest, Lease and Dividend Component
- **SC**: Services Component  
- **FC**: Financial Component

**RBI Operations Applied:**
- Max/Min/Abs operations as per RBI guidelines
- 3-year averaging: `BI_avg = (BI_year1 + BI_year2 + BI_year3) / 3`

#### 2. Business Indicator Component (BIC) Calculation

BIC is calculated using marginal coefficients across RBI-defined thresholds:

```
BIC = α₁ × min(BI, T₁) + α₂ × min(max(BI - T₁, 0), T₂ - T₁) + α₃ × max(BI - T₂, 0)
```

**Parameters:**
- T₁ = ₹8,000 crore (Bucket 1 threshold)
- T₂ = ₹2,40,000 crore (Bucket 2 threshold)
- α₁ = 12% (Bucket 1 coefficient)
- α₂ = 15% (Bucket 2 coefficient)
- α₃ = 18% (Bucket 3 coefficient)

**Bucket Assignment:**
- Bucket 1: BI ≤ ₹8,000 crore
- Bucket 2: ₹8,000 crore < BI ≤ ₹2,40,000 crore
- Bucket 3: BI > ₹2,40,000 crore

#### 3. Loss Component (LC) Calculation

```
LC = 15 × Average Annual Operational Losses
```

**Implementation Details:**
- Default lookback period: 10 years
- Minimum threshold: ₹1,00,000 (configurable)
- Uses accounting date for loss recognition
- Includes net losses (gross - recoveries)

#### 4. Internal Loss Multiplier (ILM) Calculation

```
ILM = ln(e - 1 + LC/BIC)
```

**Special Cases:**
- If LC/BIC ≤ 0: ILM = 1
- If bank has < 5 years of high-quality loss data: ILM = 1 (ILM Gate)
- If bank is in Bucket 1: ILM = 1 (ILM Gate)

#### 5. Final Capital Calculation

```
ORC = BIC × ILM
RWA = 12.5 × ORC
```

**ILM Gating Logic:**
```python
if bucket == 1 or loss_data_years < 5:
    ORC = BIC  # ILM gate applied
else:
    ORC = BIC * ILM
```

### Implementation Example

```python
def calculate_sma(bi_data: List[float], loss_data: List[float]) -> SMAResult:
    # 1. Calculate 3-year average BI
    bi_avg = sum(bi_data[-3:]) / 3
    
    # 2. Calculate BIC with marginal coefficients
    T1, T2 = 80_000_000_000, 2_400_000_000_000  # ₹8,000 cr, ₹2,40,000 cr
    alpha1, alpha2, alpha3 = 0.12, 0.15, 0.18
    
    bic = (alpha1 * min(bi_avg, T1) + 
           alpha2 * min(max(bi_avg - T1, 0), T2 - T1) + 
           alpha3 * max(bi_avg - T2, 0))
    
    # 3. Calculate LC
    annual_losses = [sum(losses_in_year) for losses_in_year in group_by_year(loss_data)]
    lc = 15 * (sum(annual_losses) / len(annual_losses))
    
    # 4. Calculate ILM
    if bic > 0:
        ilm = math.log(math.e - 1 + lc / bic)
    else:
        ilm = 1
    
    # 5. Apply ILM gating
    bucket = get_bucket(bi_avg)
    if bucket == 1 or len(annual_losses) < 5:
        orc = bic  # ILM gate
    else:
        orc = bic * ilm
    
    # 6. Calculate RWA
    rwa = 12.5 * orc
    
    return SMAResult(
        business_indicator=bi_avg,
        business_indicator_component=bic,
        loss_component=lc,
        internal_loss_multiplier=ilm,
        operational_risk_capital=orc,
        risk_weighted_assets=rwa,
        bucket=bucket
    )
```

## Basic Indicator Approach (BIA)

### Overview

Legacy method using gross income as the primary risk indicator.

### Mathematical Framework

```
Capital = α × Average Positive Gross Income (3 years)
```

**Parameters:**
- α = 15% (default, configurable)
- Only positive GI years included in average
- Excludes prescribed items per RBI guidelines

### Implementation Details

```python
def calculate_bia(gross_income_data: List[float], alpha: float = 0.15) -> BIAResult:
    # Filter positive GI years only
    positive_gi = [gi for gi in gross_income_data if gi > 0]
    
    # Calculate 3-year average
    if len(positive_gi) >= 3:
        avg_gi = sum(positive_gi[-3:]) / 3
    else:
        avg_gi = sum(positive_gi) / len(positive_gi) if positive_gi else 0
    
    # Calculate capital
    capital = alpha * avg_gi
    rwa = 12.5 * capital
    
    return BIAResult(
        average_gross_income=avg_gi,
        alpha_coefficient=alpha,
        operational_risk_capital=capital,
        risk_weighted_assets=rwa,
        years_used=len(positive_gi)
    )
```

## Traditional Standardized Approach (TSA)

### Overview

Legacy method with business line mapping and specific beta factors.

### Business Line Mapping

| Business Line | Beta Factor |
|---------------|-------------|
| Corporate Finance | 18% |
| Trading & Sales | 18% |
| Retail Banking | 12% |
| Commercial Banking | 15% |
| Payment & Settlement | 18% |
| Agency Services | 15% |
| Asset Management | 12% |
| Retail Brokerage | 12% |

### Mathematical Framework

```
Capital = Σ(βᵢ × GIᵢ) / 3 years
```

**Rules:**
- Negative GI in any business line offset against positive GI in other lines within the same year
- Annual sum floored at zero before averaging
- 3-year average of annual sums

### Implementation Example

```python
def calculate_tsa(business_line_data: Dict[str, List[float]]) -> TSAResult:
    beta_factors = {
        'corporate_finance': 0.18,
        'trading_sales': 0.18,
        'retail_banking': 0.12,
        'commercial_banking': 0.15,
        'payment_settlement': 0.18,
        'agency_services': 0.15,
        'asset_management': 0.12,
        'retail_brokerage': 0.12
    }
    
    annual_capitals = []
    
    for year in range(3):  # Last 3 years
        year_capital = 0
        for business_line, gi_values in business_line_data.items():
            if year < len(gi_values):
                beta = beta_factors.get(business_line, 0.15)
                year_capital += beta * gi_values[-(year+1)]
        
        # Floor at zero
        annual_capitals.append(max(year_capital, 0))
    
    # 3-year average
    capital = sum(annual_capitals) / 3
    rwa = 12.5 * capital
    
    return TSAResult(
        annual_capitals=annual_capitals,
        operational_risk_capital=capital,
        risk_weighted_assets=rwa,
        business_line_breakdown=calculate_breakdown(business_line_data, beta_factors)
    )
```

## What-If Scenario Analysis

### Overview

Stress testing and sensitivity analysis capabilities for risk management.

### Supported Scenarios

#### 1. Loss Shock Scenarios
```python
# Apply shock to historical losses
shocked_losses = [loss * shock_factor for loss in historical_losses]
```

#### 2. Business Indicator Shocks
```python
# Apply shock to BI components
shocked_bi = {
    'ildc': original_bi['ildc'] * bi_shock,
    'sc': original_bi['sc'] * bi_shock,
    'fc': original_bi['fc'] * bi_shock
}
```

#### 3. Recovery Haircuts
```python
# Apply haircut to recoveries
adjusted_recoveries = [recovery * (1 - haircut) for recovery in recoveries]
```

### Example Stress Test

```python
def stress_test_scenario(base_data: CalculationData, scenario: StressScenario) -> StressTestResult:
    # Apply shocks
    stressed_losses = apply_loss_shock(base_data.losses, scenario.loss_shock)
    stressed_bi = apply_bi_shock(base_data.business_indicators, scenario.bi_shock)
    adjusted_recoveries = apply_recovery_haircut(base_data.recoveries, scenario.recovery_haircut)
    
    # Recalculate with stressed inputs
    stressed_result = calculate_sma(stressed_bi, stressed_losses, adjusted_recoveries)
    base_result = calculate_sma(base_data.business_indicators, base_data.losses, base_data.recoveries)
    
    return StressTestResult(
        scenario_name=scenario.name,
        base_capital=base_result.operational_risk_capital,
        stressed_capital=stressed_result.operational_risk_capital,
        capital_impact=stressed_result.operational_risk_capital - base_result.operational_risk_capital,
        impact_percentage=(stressed_result.operational_risk_capital / base_result.operational_risk_capital - 1) * 100
    )
```

## Supervisor Override Handling

### Overview

Mechanism for regulatory supervisor overrides with proper audit trail.

### Implementation

```python
def apply_supervisor_override(calculation_result: CalculationResult, override: SupervisorOverride) -> CalculationResult:
    # Store original values
    original_values = {
        'orc': calculation_result.operational_risk_capital,
        'rwa': calculation_result.risk_weighted_assets
    }
    
    # Apply override
    if override.override_type == 'orc_absolute':
        calculation_result.operational_risk_capital = override.override_value
        calculation_result.risk_weighted_assets = 12.5 * override.override_value
    elif override.override_type == 'orc_multiplier':
        calculation_result.operational_risk_capital *= override.override_value
        calculation_result.risk_weighted_assets = 12.5 * calculation_result.operational_risk_capital
    
    # Mark for disclosure
    calculation_result.supervisor_override = SupervisorOverrideRecord(
        override_id=override.override_id,
        override_type=override.override_type,
        override_value=override.override_value,
        reason=override.reason,
        approver=override.approver,
        applied_at=datetime.utcnow(),
        original_values=original_values,
        disclosure_required=True
    )
    
    return calculation_result
```

## Data Quality Requirements

### Loss Data Quality

1. **Completeness**: All required fields must be present
2. **Accuracy**: Amounts must be positive, dates must be valid
3. **Consistency**: Recoveries cannot exceed gross losses
4. **Timeliness**: Data must be current and up-to-date

### Business Indicator Data Quality

1. **Consistency**: Components must sum to total BI
2. **Accuracy**: Values must be reasonable and validated
3. **Completeness**: All three components (ILDC, SC, FC) required

### Validation Rules

```python
def validate_loss_event(event: LossEvent) -> ValidationResult:
    errors = []
    
    # Required fields
    if not event.gross_loss or event.gross_loss <= 0:
        errors.append("Gross loss must be positive")
    
    # Recovery validation
    if event.recoveries and event.recoveries > event.gross_loss:
        errors.append("Recoveries cannot exceed gross loss")
    
    # Date validation
    if event.discovery_date < event.occurrence_date:
        errors.append("Discovery date cannot be before occurrence date")
    
    # Threshold validation
    if event.net_loss < MINIMUM_THRESHOLD:
        errors.append(f"Net loss below minimum threshold of {MINIMUM_THRESHOLD}")
    
    return ValidationResult(valid=len(errors) == 0, errors=errors)
```

## Regulatory Compliance

### RBI Requirements

1. **Data Retention**: 10+ years for loss data, 3+ years for BI data
2. **Audit Trail**: Complete lineage for all calculations
3. **Disclosure**: Supervisor overrides and exclusions
4. **Validation**: Comprehensive data quality checks

### Basel III Compliance

1. **Methodology**: Strict adherence to Basel III SMA framework
2. **Calibration**: Use of prescribed coefficients and thresholds
3. **Reporting**: Standardized output formats
4. **Documentation**: Complete methodology documentation

## Performance Considerations

### Optimization Strategies

1. **Caching**: Cache frequently accessed parameters and intermediate results
2. **Indexing**: Proper database indexing for time-series data
3. **Parallel Processing**: Concurrent calculation of independent components
4. **Memory Management**: Efficient handling of large datasets

### SLA Targets

- **Quarterly Full Run**: ≤ 30 minutes
- **Ad-hoc What-if**: ≤ 60 seconds
- **Concurrent Users**: ≥ 50 users without degradation

## Error Handling

### Common Calculation Errors

1. **Insufficient Data**: Less than required years of data
2. **Data Quality Issues**: Invalid or inconsistent data
3. **Parameter Errors**: Missing or invalid parameters
4. **Mathematical Errors**: Division by zero, invalid logarithms

### Error Recovery

```python
def safe_calculate_ilm(lc: float, bic: float) -> float:
    try:
        if bic <= 0:
            return 1.0  # Default ILM when BIC is zero or negative
        
        ratio = lc / bic
        if ratio <= 0:
            return 1.0  # Default ILM when ratio is non-positive
        
        return math.log(math.e - 1 + ratio)
    except (ValueError, ZeroDivisionError, OverflowError):
        return 1.0  # Safe fallback
```