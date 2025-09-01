"""
API routes for analytics and stress testing

Provides endpoints for stress testing, sensitivity analysis, back-testing,
and scenario analysis capabilities.
"""

import logging
from datetime import date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from pydantic import BaseModel, Field

from orm_calculator.services.analytics_service import (
    AnalyticsService, get_analytics_service,
    StressScenario, SensitivityParameter, AnalysisResult, BackTestResult,
    ShockType, AnalysisType
)
from orm_calculator.models.pydantic_models import ModelNameEnum
from orm_calculator.security.auth import User, get_current_user
from orm_calculator.security.rbac import Permission, require_permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


# Pydantic models for API requests/responses

class StressScenarioRequest(BaseModel):
    """Request model for stress scenario"""
    name: str = Field(..., description="Scenario name")
    description: str = Field(..., description="Scenario description")
    shocks: List[Dict[str, Any]] = Field(..., description="List of shocks to apply")
    severity: str = Field("moderate", description="Scenario severity level")


class SensitivityParameterRequest(BaseModel):
    """Request model for sensitivity parameter"""
    parameter_name: str = Field(..., description="Parameter name to vary")
    base_value: float = Field(..., description="Base parameter value")
    min_value: float = Field(..., description="Minimum parameter value")
    max_value: float = Field(..., description="Maximum parameter value")
    step_size: float = Field(..., description="Step size for parameter variation")
    parameter_type: str = Field("percentage", description="Parameter type")


class StressTestRequest(BaseModel):
    """Request model for stress testing"""
    entity_id: str = Field(..., description="Entity ID to stress test")
    calculation_date: date = Field(..., description="Date for stress testing")
    scenarios: List[StressScenarioRequest] = Field(..., description="Stress scenarios to run")
    model_name: ModelNameEnum = Field(ModelNameEnum.SMA, description="Calculation model")


class SensitivityAnalysisRequest(BaseModel):
    """Request model for sensitivity analysis"""
    entity_id: str = Field(..., description="Entity ID to analyze")
    calculation_date: date = Field(..., description="Date for analysis")
    parameters: List[SensitivityParameterRequest] = Field(..., description="Parameters to vary")
    model_name: ModelNameEnum = Field(ModelNameEnum.SMA, description="Calculation model")


class BackTestingRequest(BaseModel):
    """Request model for back-testing"""
    entity_id: str = Field(..., description="Entity ID to back-test")
    start_date: date = Field(..., description="Start date for back-testing")
    end_date: date = Field(..., description="End date for back-testing")
    model_name: ModelNameEnum = Field(ModelNameEnum.SMA, description="Calculation model")


class WhatIfAnalysisRequest(BaseModel):
    """Request model for what-if analysis"""
    entity_id: str = Field(..., description="Entity ID to analyze")
    calculation_date: date = Field(..., description="Date for analysis")
    what_if_parameters: Dict[str, Any] = Field(..., description="What-if parameters")
    model_name: ModelNameEnum = Field(ModelNameEnum.SMA, description="Calculation model")


class AnalysisResultResponse(BaseModel):
    """Response model for analysis results"""
    analysis_id: str
    analysis_type: str
    entity_id: str
    calculation_date: date
    base_case: Dict[str, Any]
    scenarios: List[Dict[str, Any]]
    summary_statistics: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    execution_time: float
    created_at: str


class BackTestResultResponse(BaseModel):
    """Response model for back-testing results"""
    period_start: date
    period_end: date
    predicted_capital: float
    actual_losses: float
    coverage_ratio: float
    utilization_ratio: float
    breach_count: int
    breach_dates: List[date]
    validation_metrics: Dict[str, float]


# Stress Testing Endpoints

@router.post("/stress-test", response_model=AnalysisResultResponse)
async def run_stress_test(
    request: StressTestRequest,
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(require_permission(Permission.READ_AUDIT))
):
    """
    Run stress testing with multiple scenarios
    
    Requires READ_AUDIT permission (risk analyst level or above).
    """
    try:
        # Convert request scenarios to service scenarios
        scenarios = [
            StressScenario(
                name=s.name,
                description=s.description,
                shocks=s.shocks,
                severity=s.severity
            )
            for s in request.scenarios
        ]
        
        # Run stress test
        result = await analytics_service.run_stress_test(
            entity_id=request.entity_id,
            calculation_date=request.calculation_date,
            scenarios=scenarios,
            model_name=request.model_name
        )
        
        # Convert result to response format
        response = AnalysisResultResponse(
            analysis_id=result.analysis_id,
            analysis_type=result.analysis_type.value,
            entity_id=result.entity_id,
            calculation_date=result.calculation_date,
            base_case={
                "operational_risk_capital": float(result.base_case.operational_risk_capital),
                "risk_weighted_assets": float(result.base_case.risk_weighted_assets),
                "bucket": result.base_case.bucket,
                "ilm_gated": result.base_case.ilm_gated
            },
            scenarios=result.scenarios,
            summary_statistics=result.summary_statistics,
            risk_metrics=result.risk_metrics,
            execution_time=result.execution_time,
            created_at=result.created_at.isoformat()
        )
        
        logger.info(f"Completed stress test {result.analysis_id} for user {current_user.username}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to run stress test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "STRESS_TEST_FAILED",
                "error_message": "Failed to run stress test",
                "details": {"error": str(e)}
            }
        )


@router.post("/sensitivity-analysis", response_model=AnalysisResultResponse)
async def run_sensitivity_analysis(
    request: SensitivityAnalysisRequest,
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(require_permission(Permission.READ_AUDIT))
):
    """
    Run sensitivity analysis over parameter ranges
    
    Requires READ_AUDIT permission (risk analyst level or above).
    """
    try:
        # Convert request parameters to service parameters
        parameters = [
            SensitivityParameter(
                parameter_name=p.parameter_name,
                base_value=p.base_value,
                min_value=p.min_value,
                max_value=p.max_value,
                step_size=p.step_size,
                parameter_type=p.parameter_type
            )
            for p in request.parameters
        ]
        
        # Run sensitivity analysis
        result = await analytics_service.run_sensitivity_analysis(
            entity_id=request.entity_id,
            calculation_date=request.calculation_date,
            parameters=parameters,
            model_name=request.model_name
        )
        
        # Convert result to response format
        response = AnalysisResultResponse(
            analysis_id=result.analysis_id,
            analysis_type=result.analysis_type.value,
            entity_id=result.entity_id,
            calculation_date=result.calculation_date,
            base_case={
                "operational_risk_capital": float(result.base_case.operational_risk_capital),
                "risk_weighted_assets": float(result.base_case.risk_weighted_assets),
                "bucket": result.base_case.bucket,
                "ilm_gated": result.base_case.ilm_gated
            },
            scenarios=result.scenarios,
            summary_statistics=result.summary_statistics,
            risk_metrics=result.risk_metrics,
            execution_time=result.execution_time,
            created_at=result.created_at.isoformat()
        )
        
        logger.info(f"Completed sensitivity analysis {result.analysis_id} for user {current_user.username}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to run sensitivity analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "SENSITIVITY_ANALYSIS_FAILED",
                "error_message": "Failed to run sensitivity analysis",
                "details": {"error": str(e)}
            }
        )


@router.post("/back-testing", response_model=List[BackTestResultResponse])
async def run_back_testing(
    request: BackTestingRequest,
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(require_permission(Permission.READ_AUDIT))
):
    """
    Run back-testing analysis comparing predicted capital vs actual losses
    
    Requires READ_AUDIT permission (risk analyst level or above).
    """
    try:
        # Run back-testing
        results = await analytics_service.run_back_testing(
            entity_id=request.entity_id,
            start_date=request.start_date,
            end_date=request.end_date,
            model_name=request.model_name
        )
        
        # Convert results to response format
        response = [
            BackTestResultResponse(
                period_start=r.period_start,
                period_end=r.period_end,
                predicted_capital=float(r.predicted_capital),
                actual_losses=float(r.actual_losses),
                coverage_ratio=float(r.coverage_ratio),
                utilization_ratio=float(r.utilization_ratio),
                breach_count=r.breach_count,
                breach_dates=r.breach_dates,
                validation_metrics={k: float(v) for k, v in r.validation_metrics.items()}
            )
            for r in results
        ]
        
        logger.info(f"Completed back-testing for entity {request.entity_id} by user {current_user.username}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to run back-testing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "BACK_TESTING_FAILED",
                "error_message": "Failed to run back-testing",
                "details": {"error": str(e)}
            }
        )


@router.post("/what-if-analysis", response_model=AnalysisResultResponse)
async def run_what_if_analysis(
    request: WhatIfAnalysisRequest,
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(require_permission(Permission.READ_AUDIT))
):
    """
    Run what-if scenario analysis with custom parameters
    
    Requires READ_AUDIT permission (risk analyst level or above).
    """
    try:
        # Run what-if analysis
        result = await analytics_service.run_what_if_analysis(
            entity_id=request.entity_id,
            calculation_date=request.calculation_date,
            what_if_parameters=request.what_if_parameters,
            model_name=request.model_name
        )
        
        # Convert result to response format
        response = AnalysisResultResponse(
            analysis_id=result.analysis_id,
            analysis_type=result.analysis_type.value,
            entity_id=result.entity_id,
            calculation_date=result.calculation_date,
            base_case={
                "operational_risk_capital": float(result.base_case.operational_risk_capital),
                "risk_weighted_assets": float(result.base_case.risk_weighted_assets),
                "bucket": result.base_case.bucket,
                "ilm_gated": result.base_case.ilm_gated
            },
            scenarios=result.scenarios,
            summary_statistics=result.summary_statistics,
            risk_metrics=result.risk_metrics,
            execution_time=result.execution_time,
            created_at=result.created_at.isoformat()
        )
        
        logger.info(f"Completed what-if analysis {result.analysis_id} for user {current_user.username}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to run what-if analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "WHAT_IF_ANALYSIS_FAILED",
                "error_message": "Failed to run what-if analysis",
                "details": {"error": str(e)}
            }
        )


# Scenario Management Endpoints

@router.get("/predefined-scenarios")
async def get_predefined_scenarios(
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of predefined stress scenarios
    
    Requires authentication.
    """
    try:
        scenarios = analytics_service.get_predefined_scenarios()
        
        return {
            "scenarios": [
                {
                    "name": s.name,
                    "description": s.description,
                    "shocks": s.shocks,
                    "severity": s.severity
                }
                for s in scenarios
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get predefined scenarios: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "SCENARIOS_RETRIEVAL_FAILED",
                "error_message": "Failed to retrieve predefined scenarios",
                "details": {"error": str(e)}
            }
        )


@router.get("/shock-types")
async def get_shock_types(
    current_user: User = Depends(get_current_user)
):
    """
    Get available shock types for stress testing
    
    Requires authentication.
    """
    return {
        "shock_types": [
            {
                "value": shock_type.value,
                "description": shock_type.value.replace("_", " ").title()
            }
            for shock_type in ShockType
        ]
    }


@router.get("/analysis-types")
async def get_analysis_types(
    current_user: User = Depends(get_current_user)
):
    """
    Get available analysis types
    
    Requires authentication.
    """
    return {
        "analysis_types": [
            {
                "value": analysis_type.value,
                "description": analysis_type.value.replace("_", " ").title()
            }
            for analysis_type in AnalysisType
        ]
    }


# Quick Analysis Endpoints

@router.post("/quick-stress-test")
async def run_quick_stress_test(
    entity_id: str = Body(..., description="Entity ID"),
    calculation_date: date = Body(..., description="Calculation date"),
    loss_shock_pct: float = Body(30, description="Loss increase percentage"),
    model_name: ModelNameEnum = Body(ModelNameEnum.SMA, description="Calculation model"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(require_permission(Permission.READ_AUDIT))
):
    """
    Run a quick stress test with standard loss shock
    
    Requires READ_AUDIT permission.
    """
    try:
        # Create quick stress scenario
        scenario = StressScenario(
            name="quick_stress",
            description=f"Quick stress test with {loss_shock_pct}% loss increase",
            shocks=[{"type": "loss_increase", "value": loss_shock_pct}],
            severity="moderate" if loss_shock_pct <= 30 else "severe"
        )
        
        # Run stress test
        result = await analytics_service.run_stress_test(
            entity_id=entity_id,
            calculation_date=calculation_date,
            scenarios=[scenario],
            model_name=model_name
        )
        
        # Return simplified response
        if result.scenarios and len(result.scenarios) > 0:
            scenario_result = result.scenarios[0]
            return {
                "analysis_id": result.analysis_id,
                "entity_id": entity_id,
                "calculation_date": calculation_date.isoformat(),
                "loss_shock_pct": loss_shock_pct,
                "base_orc": float(result.base_case.operational_risk_capital),
                "stressed_orc": float(scenario_result["result"].operational_risk_capital),
                "orc_impact": scenario_result["impact"]["orc_change"],
                "orc_impact_pct": scenario_result["impact"]["orc_change_pct"],
                "execution_time": result.execution_time
            }
        else:
            raise ValueError("No scenario results available")
        
    except Exception as e:
        logger.error(f"Failed to run quick stress test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "QUICK_STRESS_TEST_FAILED",
                "error_message": "Failed to run quick stress test",
                "details": {"error": str(e)}
            }
        )


@router.post("/parameter-sensitivity")
async def run_parameter_sensitivity(
    entity_id: str = Body(..., description="Entity ID"),
    calculation_date: date = Body(..., description="Calculation date"),
    parameter_name: str = Body(..., description="Parameter name"),
    variation_pct: float = Body(20, description="Variation percentage around base value"),
    steps: int = Body(10, description="Number of steps"),
    model_name: ModelNameEnum = Body(ModelNameEnum.SMA, description="Calculation model"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(require_permission(Permission.READ_AUDIT))
):
    """
    Run parameter sensitivity analysis with automatic range calculation
    
    Requires READ_AUDIT permission.
    """
    try:
        # Assume base value of 1.0 for most parameters
        base_value = 1.0
        variation = base_value * (variation_pct / 100.0)
        
        # Create sensitivity parameter
        parameter = SensitivityParameter(
            parameter_name=parameter_name,
            base_value=base_value,
            min_value=base_value - variation,
            max_value=base_value + variation,
            step_size=(2 * variation) / steps,
            parameter_type="multiplier"
        )
        
        # Run sensitivity analysis
        result = await analytics_service.run_sensitivity_analysis(
            entity_id=entity_id,
            calculation_date=calculation_date,
            parameters=[parameter],
            model_name=model_name
        )
        
        # Extract parameter-specific results
        param_scenarios = [s for s in result.scenarios if s.get("parameter_name") == parameter_name]
        
        return {
            "analysis_id": result.analysis_id,
            "entity_id": entity_id,
            "calculation_date": calculation_date.isoformat(),
            "parameter_name": parameter_name,
            "base_orc": float(result.base_case.operational_risk_capital),
            "scenarios_count": len(param_scenarios),
            "sensitivity_results": [
                {
                    "parameter_value": s["parameter_value"],
                    "orc_value": float(s["result"].operational_risk_capital),
                    "orc_change_pct": s["impact"]["orc_change_pct"]
                }
                for s in param_scenarios if s.get("status") == "completed"
            ],
            "execution_time": result.execution_time
        }
        
    except Exception as e:
        logger.error(f"Failed to run parameter sensitivity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "PARAMETER_SENSITIVITY_FAILED",
                "error_message": "Failed to run parameter sensitivity",
                "details": {"error": str(e)}
            }
        )