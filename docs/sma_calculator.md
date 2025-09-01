# SMA Calculator Engine Documentation

## Overview

The SMA (Standardized Measurement Approach) Calculator Engine implements the RBI Basel III methodology for operational risk capital calculation. This engine provides comprehensive calculation capabilities following the regulatory framework with complete auditability and reproducibility.

## Key Features

- **Complete SMA Implementation**: Full RBI Basel III SMA methodology
- **Business Indicator Calculation**: BI = ILDC + SC + FC with 3-year averaging
- **Bucket Assignment**: Automatic classification based on RBI thresholds
- **BIC Calculation**: Marginal coefficients (12%, 15%, 18%) by bucket
- **Loss Component**: LC = 15 × average annual losses with 10-year horizon
- **ILM Calculation**: Internal Loss Multiplier with gating logic
- **Final Capital**: ORC and RWA calculation with proper rounding
- **Input Validation**: Comprehensive data validation and error handling
- **High Precision**: Decimal arithmetic for financial calculations

## Architecture

### Core Components

1. **SMACalculator**: Main calculation engine
2. **BusinessIndicatorData**: BI data structure
3. **LossData**: Loss event data structure  
4. **SMACalculationResult**: Complete calculation result
5. **RBIBucket**: Bucket classification enumeration

### Calculation Flow

```
Business Indicator Data → BI Calculation → Bucket Assignment
                                              ↓
Loss Event Data → Loss Component ← BIC Calculation
                      ↓
              ILM Calculation → ORC → RWA
```

## Usage Examples

### Basic SMA Calculation

```python
from orm_calculator.services.sma_calculator import (
    SMACalculator, BusinessIndicatorData, LossData
)
from decimal import Decimal
from datetime import date

# Initialize calculator
calculator = SMACalculator()

# Prepare business indicator data
bi_data = [
    BusinessIndicatorData(
        period="2023",
        ildc=Decimal('50000000000'),  # ₹5,000 crore
        sc=Decimal('20000000000'),    # ₹2,000 crore
        fc=Decimal('10000000000'),    # ₹1,000 crore
        entity_id="BANK001",
        calculation_date=date(2023, 12, 31)
    )
]

# Prepare loss data
loss_data = [
    LossData(
        event_id="LOSS001",
        entity_id="BANK001",
        accounting_date=date(2023, 6, 15),
        net_loss=Decimal('50000000')  # ₹5 crore
    )
]

# Perform calculation
result = calculator.calculate_sma(
    bi_data=bi_data,
    loss_data=loss_data,
    entity_id="BANK001",
    calculation_date=date(2023, 12, 31),
    run_id="RUN_001"
)

# Access results
print(f"ORC: ₹{result.orc/10000000:.2f} crore")
print(f"RWA: ₹{result.rwa/10000000:.2f} crore")
print(f"Bucket: {result.bucket.value}")
```

### Individual Component Calculations

```python
# Business Indicator calculation
current_bi, three_year_avg = calculator.calculate_business_indicator(bi_data)

# Bucket assignment
bucket = calculator.assign_bucket(three_year_avg)

# BIC calculation
bic, coefficients = calculator.calculate_bic(three_year_avg, bucket)

# Loss Component calculation
lc, avg_losses, years = calculator.calculate_loss_component(loss_data, date(2023, 12, 31))

# ILM calculation
ilm, gated, reason = calculator.calculate_ilm(lc, bic, bucket, years)
```

## RBI Methodology Implementation

### Business Indicator (BI)

- **Formula**: BI = ILDC + SC + FC
- **Operations**: RBI Max/Min/Abs operations applied
- **Averaging**: 3-year average for BIC calculation
- **Components**:
  - ILDC: Interest, Leases, Dividends, and Commissions
  - SC: Services Component (non-negative)
  - FC: Financial Component

### Bucket Classification

| Bucket | Threshold | Marginal Coefficient |
|--------|-----------|---------------------|
| Bucket 1 | < ₹8,000 crore | 12% |
| Bucket 2 | ₹8,000 - ₹2,40,000 crore | 12% + 15% |
| Bucket 3 | ≥ ₹2,40,000 crore | 12% + 15% + 18% |

### Business Indicator Component (BIC)

Marginal coefficient application:
- **Bucket 1**: 12% on entire amount
- **Bucket 2**: 12% on first ₹8,000 crore + 15% on excess
- **Bucket 3**: 12% on first ₹8,000 crore + 15% on next ₹2,32,000 crore + 18% on excess

### Loss Component (LC)

- **Formula**: LC = 15 × average annual losses
- **Horizon**: 10-year rolling window
- **Threshold**: ₹1,00,000 minimum loss threshold
- **Exclusions**: RBI-approved exclusions supported
- **Data Quality**: Minimum 5 years for ILM calculation

### Internal Loss Multiplier (ILM)

- **Formula**: ILM = ln(e - 1 + LC/BIC)
- **Gating Conditions**:
  - Bucket 1: ILM = 1 (gated)
  - < 5 years data: ILM = 1 (gated)
  - National discretion: ILM = 1 (optional)

### Final Capital Calculation

- **ORC**: Operational Risk Capital = BIC × ILM
- **RWA**: Risk Weighted Assets = ORC × 12.5
- **Precision**: Rounded to 2 decimal places

## Data Validation

The calculator performs comprehensive input validation:

### Business Indicator Validation
- Non-empty data required
- Entity ID and period required
- Reasonable value ranges

### Loss Data Validation
- Non-negative net losses
- Required fields (event_id, entity_id)
- Date consistency
- Exclusion approval validation

### Calculation Validation
- Division by zero protection
- Mathematical domain validation
- Result range validation

## Error Handling

The calculator provides detailed error information:

```python
# Validate inputs before calculation
errors = calculator.validate_inputs(bi_data, loss_data)
if errors:
    for error in errors:
        print(f"Validation Error: {error}")
```

## Testing

Comprehensive test suite covers:

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end calculation testing
- **Edge Cases**: Boundary conditions and error scenarios
- **Precision Tests**: Decimal arithmetic validation
- **Regulatory Tests**: RBI methodology compliance

Run tests:
```bash
python -m pytest tests/test_sma_calculator.py -v
python -m pytest tests/test_sma_integration.py -v
```

## Demo Script

Run the demonstration script to see the calculator in action:

```bash
python scripts/demo_sma_calculator.py
```

This will show:
- Complete SMA calculation with sample data
- Different bucket scenarios
- Detailed calculation breakdown
- Formula explanations

## Performance Characteristics

- **Precision**: Decimal arithmetic for financial accuracy
- **Memory**: Efficient data structures
- **Speed**: Optimized mathematical operations
- **Scalability**: Handles large datasets efficiently

## Compliance Features

- **RBI Basel III**: Full methodology compliance
- **Auditability**: Complete calculation traceability
- **Reproducibility**: Deterministic results
- **Version Control**: Model and parameter versioning
- **Data Lineage**: Input-to-output tracking

## Future Enhancements

The SMA calculator is designed for extensibility:

- **Supervisor Overrides**: Override application logic
- **Parameter Governance**: Maker-checker workflows
- **Advanced Analytics**: Stress testing capabilities
- **Performance Optimization**: Caching and parallelization
- **Additional Methodologies**: BIA and TSA support