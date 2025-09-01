# ORM Capital Calculator Engine - User Guide

## Overview

The ORM Capital Calculator Engine is a comprehensive system for calculating operational risk capital requirements in compliance with RBI's Basel III Standardized Measurement Approach (SMA). This guide provides detailed instructions for using the system effectively.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [Calculation Methods](#calculation-methods)
4. [API Usage Examples](#api-usage-examples)
5. [Data Management](#data-management)
6. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Access to the ORM Capital Calculator API
- Valid authentication credentials

### Quick Start

1. **Health Check**: Verify the system is running
```bash
curl -X GET "http://localhost:8000/api/v1/health"
```

2. **Authentication**: Obtain an access token (see [Authentication](#authentication))

3. **Run a Simple Calculation**: Execute a basic SMA calculation
```bash
curl -X POST "http://localhost:8000/api/v1/calculation-jobs" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "sma",
    "execution_mode": "sync",
    "entity_id": "BANK001",
    "calculation_date": "2024-03-31"
  }'
```

## Authentication

The system uses OAuth 2.0 client credentials flow for authentication.

### Obtaining Access Token

```bash
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using the Token

Include the token in the Authorization header:
```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Calculation Methods

### 1. Standardized Measurement Approach (SMA)

The primary method for operational risk capital calculation under Basel III.

**Key Components:**
- Business Indicator (BI) = ILDC + SC + FC
- Business Indicator Component (BIC) with marginal coefficients
- Loss Component (LC) = 15 × average annual losses
- Internal Loss Multiplier (ILM) = ln(e - 1 + LC/BIC)
- Operational Risk Capital (ORC) = BIC × ILM
- Risk Weighted Assets (RWA) = 12.5 × ORC

### 2. Basic Indicator Approach (BIA)

Legacy method using gross income.

**Formula:** Capital = α × Average Positive Gross Income (3 years)
- Default α = 15%

### 3. Traditional Standardized Approach (TSA)

Legacy method with business line mapping.

**Components:**
- 8 business lines with specific β factors
- Negative offsets within years
- 3-year averaging with floor at zero

## API Usage Examples

### Synchronous SMA Calculation

```bash
curl -X POST "http://localhost:8000/api/v1/calculation-jobs" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "sma",
    "execution_mode": "sync",
    "entity_id": "BANK001",
    "calculation_date": "2024-03-31",
    "parameters": {
      "minimum_loss_threshold": 100000,
      "loss_data_years": 10,
      "bi_averaging_years": 3
    }
  }'
```

**Response:**
```json
{
  "job_id": "job_12345",
  "status": "completed",
  "results": {
    "business_indicator": 50000000000,
    "business_indicator_component": 7500000000,
    "loss_component": 1500000000,
    "internal_loss_multiplier": 1.2,
    "operational_risk_capital": 9000000000,
    "risk_weighted_assets": 112500000000,
    "bucket": 2,
    "methodology": "sma"
  },
  "run_id": "run_67890",
  "calculation_date": "2024-03-31",
  "completed_at": "2024-03-31T10:30:00Z"
}
```

### Asynchronous Calculation with Webhook

```bash
curl -X POST "http://localhost:8000/api/v1/calculation-jobs" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "sma",
    "execution_mode": "async",
    "entity_id": "BANK001",
    "calculation_date": "2024-03-31",
    "callback_url": "https://your-system.com/webhooks/calculation-complete"
  }'
```

**Response:**
```json
{
  "job_id": "job_12346",
  "status": "queued",
  "estimated_completion_time": "2024-03-31T10:35:00Z",
  "callback_url": "https://your-system.com/webhooks/calculation-complete",
  "created_at": "2024-03-31T10:30:00Z"
}
```

### What-If Scenario Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/calculation-jobs" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "what-if",
    "execution_mode": "sync",
    "entity_id": "BANK001",
    "calculation_date": "2024-03-31",
    "parameters": {
      "scenario_name": "stress_test_1",
      "loss_shock": 1.3,
      "bi_shock": 0.8,
      "recovery_haircut": 0.5
    }
  }'
```

### Retrieving Job Status and Results

```bash
curl -X GET "http://localhost:8000/api/v1/calculation-jobs/job_12346" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Data Lineage Tracking

```bash
curl -X GET "http://localhost:8000/api/v1/lineage/run_67890" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "run_id": "run_67890",
  "final_outputs": {
    "orc": 9000000000,
    "rwa": 112500000000
  },
  "intermediates": {
    "bi": 50000000000,
    "bic": 7500000000,
    "lc": 1500000000,
    "ilm": 1.2
  },
  "parameter_versions": [
    {
      "model_name": "sma",
      "version_id": "v1.0.0",
      "effective_date": "2024-01-01"
    }
  ],
  "included_loss_ids": ["loss_001", "loss_002", "loss_003"],
  "environment_hash": "abc123def456",
  "created_at": "2024-03-31T10:30:00Z",
  "reproducible": true
}
```

## Data Management

### Loss Data Ingestion

```bash
curl -X POST "http://localhost:8000/api/v1/loss-data/events" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "event_id": "LOSS_001",
        "entity_id": "BANK001",
        "occurrence_date": "2023-06-15",
        "discovery_date": "2023-06-20",
        "accounting_date": "2023-06-30",
        "gross_loss": 500000,
        "business_line": "retail_banking",
        "event_type": "external_fraud"
      }
    ]
  }'
```

### Business Indicator Data

```bash
curl -X POST "http://localhost:8000/api/v1/loss-data/business-indicators" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "indicators": [
      {
        "entity_id": "BANK001",
        "period": "2023-Q4",
        "calculation_date": "2023-12-31",
        "ildc": 45000000000,
        "sc": 3000000000,
        "fc": 2000000000
      }
    ]
  }'
```

### Parameter Management

#### View Current Parameters
```bash
curl -X GET "http://localhost:8000/api/v1/models/sma/parameters" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Propose Parameter Change
```bash
curl -X POST "http://localhost:8000/api/v1/parameters/proposals" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "sma",
    "parameter_name": "minimum_loss_threshold",
    "current_value": 100000,
    "proposed_value": 150000,
    "change_reason": "Regulatory update",
    "business_justification": "RBI circular dated 2024-03-01"
  }'
```

## Monitoring and Troubleshooting

### System Health Checks

```bash
# Basic health check
curl -X GET "http://localhost:8000/api/v1/health"

# Detailed health check
curl -X GET "http://localhost:8000/api/v1/health/detailed" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Performance Metrics

```bash
curl -X GET "http://localhost:8000/api/v1/performance/metrics" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Error Handling

All API errors follow a standardized format:

```json
{
  "error_code": "VALIDATION_ERROR",
  "error_message": "Request validation failed",
  "details": {
    "validation_errors": [
      {
        "error_code": "VALIDATION_ERROR",
        "error_message": "field required",
        "field": "entity_id",
        "details": {
          "input_value": null,
          "error_type": "missing"
        }
      }
    ]
  }
}
```

### Common Error Codes

- `VALIDATION_ERROR`: Input validation failed
- `AUTHENTICATION_ERROR`: Invalid or missing authentication
- `AUTHORIZATION_ERROR`: Insufficient permissions
- `CALCULATION_ERROR`: Error during calculation execution
- `DATA_NOT_FOUND`: Requested data not found
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_SERVER_ERROR`: Unexpected system error

### Troubleshooting Tips

1. **Authentication Issues**: Ensure token is valid and not expired
2. **Validation Errors**: Check request format against API documentation
3. **Rate Limiting**: Implement exponential backoff for retries
4. **Long-Running Jobs**: Use async mode for calculations > 60 seconds
5. **Data Issues**: Verify data completeness and format before submission

## Best Practices

1. **Use Async Mode**: For calculations expected to take > 60 seconds
2. **Implement Webhooks**: For reliable job completion notifications
3. **Cache Results**: Store calculation results to avoid redundant processing
4. **Monitor Performance**: Use health and metrics endpoints regularly
5. **Handle Errors Gracefully**: Implement proper error handling and retries
6. **Validate Data**: Ensure data quality before submission
7. **Use Correlation IDs**: For request tracing and debugging
8. **Implement Idempotency**: Use idempotency keys for critical operations

## Support

For technical support and questions:
- Email: support@example.com
- Documentation: https://orm-capital-calculator.readthedocs.io
- Issues: https://github.com/example/orm-capital-calculator/issues