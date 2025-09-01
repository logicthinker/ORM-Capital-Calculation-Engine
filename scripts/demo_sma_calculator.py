#!/usr/bin/env python3
"""
Demo script for SMA Calculator Engine

This script demonstrates the complete SMA calculation workflow with sample data.
"""

import sys
import os
from decimal import Decimal
from datetime import date

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from orm_calculator.services.sma_calculator import (
    SMACalculator,
    BusinessIndicatorData,
    LossData,
    RBIBucket
)


def demo_sma_calculation():
    """Demonstrate SMA calculation with sample data"""
    print("=" * 80)
    print("SMA Calculator Engine Demonstration")
    print("=" * 80)
    
    # Initialize calculator
    calculator = SMACalculator(model_version="1.0.0", parameters_version="1.0.0")
    
    # Sample Business Indicator data for 3 years
    print("\n1. Business Indicator Data:")
    print("-" * 40)
    
    bi_data = [
        BusinessIndicatorData(
            period="2023",
            ildc=Decimal('120000000000'),  # ₹12,000 crore
            sc=Decimal('45000000000'),     # ₹4,500 crore
            fc=Decimal('25000000000'),     # ₹2,500 crore
            entity_id="DEMO_BANK",
            calculation_date=date(2023, 12, 31)
        ),
        BusinessIndicatorData(
            period="2022",
            ildc=Decimal('115000000000'),  # ₹11,500 crore
            sc=Decimal('42000000000'),     # ₹4,200 crore
            fc=Decimal('23000000000'),     # ₹2,300 crore
            entity_id="DEMO_BANK",
            calculation_date=date(2022, 12, 31)
        ),
        BusinessIndicatorData(
            period="2021",
            ildc=Decimal('110000000000'),  # ₹11,000 crore
            sc=Decimal('40000000000'),     # ₹4,000 crore
            fc=Decimal('20000000000'),     # ₹2,000 crore
            entity_id="DEMO_BANK",
            calculation_date=date(2021, 12, 31)
        )
    ]
    
    for data in bi_data:
        bi_total = data.ildc + data.sc + data.fc
        print(f"  {data.period}: ILDC=₹{data.ildc/10000000:.0f}cr, SC=₹{data.sc/10000000:.0f}cr, FC=₹{data.fc/10000000:.0f}cr, Total=₹{bi_total/10000000:.0f}cr")
    
    # Sample loss data for 10 years
    print("\n2. Loss Event Data (Sample):")
    print("-" * 40)
    
    loss_data = []
    # Generate sample losses for demonstration
    base_losses = [
        (2023, [150, 80, 120, 200]),   # ₹5.5 crore total
        (2022, [100, 90, 110, 180]),   # ₹4.8 crore total  
        (2021, [120, 70, 95, 160]),    # ₹4.45 crore total
        (2020, [80, 110, 130, 140]),   # ₹4.6 crore total
        (2019, [90, 100, 85, 175]),    # ₹4.5 crore total
        (2018, [75, 95, 105, 165]),    # ₹4.4 crore total
        (2017, [85, 88, 92, 155]),     # ₹4.2 crore total
    ]
    
    for year, quarterly_losses in base_losses:
        year_total = 0
        for quarter, loss_amount in enumerate(quarterly_losses, 1):
            loss_in_paise = loss_amount * 1000000  # Convert crore to paise
            loss_data.append(
                LossData(
                    event_id=f"LOSS_{year}_Q{quarter}",
                    entity_id="DEMO_BANK",
                    accounting_date=date(year, quarter * 3, 15),
                    net_loss=Decimal(str(loss_in_paise))
                )
            )
            year_total += loss_amount
        print(f"  {year}: ₹{year_total:.1f} crore total losses")
    
    # Perform SMA calculation
    print("\n3. SMA Calculation Results:")
    print("-" * 40)
    
    result = calculator.calculate_sma(
        bi_data=bi_data,
        loss_data=loss_data,
        entity_id="DEMO_BANK",
        calculation_date=date(2023, 12, 31),
        run_id="DEMO_RUN_001"
    )
    
    # Display results
    print(f"\nRun ID: {result.run_id}")
    print(f"Entity: {result.entity_id}")
    print(f"Calculation Date: {result.calculation_date}")
    print(f"Model Version: {result.model_version}")
    print(f"Parameters Version: {result.parameters_version}")
    
    print(f"\n📊 Business Indicator Analysis:")
    print(f"  Current BI (2023): ₹{result.bi_current/10000000:,.0f} crore")
    print(f"  3-Year Average BI: ₹{result.bi_three_year_average/10000000:,.0f} crore")
    print(f"  RBI Bucket: {result.bucket.value.upper()}")
    
    print(f"\n💰 Business Indicator Component (BIC):")
    print(f"  BIC Amount: ₹{result.bic/10000000:,.2f} crore")
    print(f"  Marginal Coefficients Applied:")
    for bucket, amount in result.marginal_coefficients_applied.items():
        coefficient = calculator.MARGINAL_COEFFICIENTS[bucket] * 100
        print(f"    {bucket}: ₹{amount/10000000:,.0f} crore @ {coefficient}%")
    
    print(f"\n📉 Loss Component (LC):")
    print(f"  Average Annual Losses: ₹{result.average_annual_losses/10000000:.2f} crore")
    print(f"  Loss Data Years: {result.loss_data_years}")
    print(f"  LC (15 × avg losses): ₹{result.lc/10000000:.2f} crore")
    
    print(f"\n🔢 Internal Loss Multiplier (ILM):")
    print(f"  ILM Value: {result.ilm:.6f}")
    print(f"  ILM Gated: {'Yes' if result.ilm_gated else 'No'}")
    if result.ilm_gated:
        print(f"  Gate Reason: {result.ilm_gate_reason}")
    print(f"  LC/BIC Ratio: {result.lc/result.bic:.6f}")
    
    print(f"\n🎯 Final Capital Requirements:")
    print(f"  Operational Risk Capital (ORC): ₹{result.orc/10000000:,.2f} crore")
    print(f"  Risk Weighted Assets (RWA): ₹{result.rwa/10000000:,.2f} crore")
    print(f"  Capital Ratio (ORC/BI): {(result.orc/result.bi_three_year_average)*100:.2f}%")
    
    print(f"\n⚙️  Calculation Formula Summary:")
    print(f"  BI = ILDC + SC + FC (3-year average)")
    print(f"  BIC = BI × marginal coefficients by bucket")
    print(f"  LC = 15 × average annual losses")
    print(f"  ILM = ln(e - 1 + LC/BIC) {'[GATED]' if result.ilm_gated else ''}")
    print(f"  ORC = BIC × ILM")
    print(f"  RWA = ORC × 12.5")
    
    print("\n" + "=" * 80)
    print("SMA Calculation Complete!")
    print("=" * 80)
    
    return result


def demo_bucket_scenarios():
    """Demonstrate different bucket scenarios"""
    print("\n" + "=" * 80)
    print("RBI Bucket Scenarios Demonstration")
    print("=" * 80)
    
    calculator = SMACalculator()
    
    scenarios = [
        ("Small Bank (Bucket 1)", Decimal('60000000000')),    # ₹6,000 crore
        ("Medium Bank (Bucket 2)", Decimal('150000000000')),  # ₹15,000 crore  
        ("Large Bank (Bucket 3)", Decimal('3000000000000')),  # ₹3,00,000 crore
    ]
    
    for name, bi_amount in scenarios:
        bucket = calculator.assign_bucket(bi_amount)
        bic, coefficients = calculator.calculate_bic(bi_amount, bucket)
        
        print(f"\n{name}:")
        print(f"  BI Amount: ₹{bi_amount/10000000:,.0f} crore")
        print(f"  Bucket: {bucket.value.upper()}")
        print(f"  BIC: ₹{bic/10000000:,.2f} crore")
        print(f"  Effective Rate: {(bic/bi_amount)*100:.2f}%")


if __name__ == "__main__":
    # Run demonstrations
    demo_sma_calculation()
    demo_bucket_scenarios()