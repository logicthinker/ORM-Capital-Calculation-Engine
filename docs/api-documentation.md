# API Documentation

## Overview

The ORM Capital Calculator Engine provides a comprehensive REST API for calculating operational risk capital requirements in compliance with RBI's Basel III Standardized Measurement Approach (SMA). This documentation provides detailed information about all available endpoints, request/response formats, and authentication requirements.

## Base URL

```
Production: https://orm-calculator.your-domain.com/api/v1
Development: http://localhost:8000/api/v1
```

## Authentication

The API uses OAuth 2.0 client credentials flow for authentication. All protected endpoints require a valid Bearer token.

### Obtaining Access Token

**Endpoint:** `POST /auth/token`

**Request:**
```bash
curl -X POST "https://orm-calculator.your-domain.com/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "scope": "read write"
}
```

### Using the Token

Include the token in the Authorization header for all API requests:

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Rate Limiting

API requests are rate-limited to ensure system stability:

- **Calculation endpoints**: 100 requests per minute
- **Data endpoints**: 200 requests per minute  
- **Health/status endpoints**: 1000 requests per minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Error Handling

All errors follow a standardized format:

```json
{
  "error_code": "ERROR_CODE",
  "error_message": "Human readable error message",
  "details": {
    "additional": "context information"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `AUTHENTICATION_ERROR` | 401 | Invalid or missing authentication |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `CALCULATION_ERROR` | 422 | Error during calculation |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected system error |

## API Endpoints

### Health Check Endpoints

#### Basic Health Check

**Endpoint:** `GET /health`

**Description:** Basic health check endpoint (no authentication required)

**Example Request:**
```bash
curl -X GET "https://orm-calculator.your-domain.com/api/v1/health"
```

**Example Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-03-31T10:30:00Z",
  "version": "0.1.0"
}
```

#### Detailed Health Check

**Endpoint:** `GET /health/detailed`

**Description:** Detailed health check with component status (authentication required)

**Example Request:**
```bash
curl -X GET "https://orm-calculator.your-domain.com/api/v1/health/detailed" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-03-31T10:30:00Z",
  "version": "0.1.0",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5,
      "connection_pool": {
        "active": 3,
        "idle": 7,
        "total": 10
      }
    },
    "cache": {
      "status": "healthy",
      "response_time_ms": 2,
      "memory_usage": "45%"
    },
    "external_services": {
      "oauth_provider": {
        "status": "healthy",
        "response_time_ms": 150
      }
    }
  }
}
```

### Calculation Job Endpoints

#### Create Calculation Job

**Endpoint:** `POST /calculation-jobs`

**Description:** Create a new calculation job (sync or async)

**Request Body:**
```json
{
  "model_name": "sma",
  "execution_mode": "sync",
  "entity_id": "BANK001",
  "calculation_date": "2024-03-31",
  "parameters": {
    "minimum_loss_threshold": 100000,
    "loss_data_years": 10,
    "bi_averaging_years": 3
  },
  "callback_url": "https://your-system.com/webhooks/calculation-complete",
  "idempotency_key": "calc_20240331_001",
  "correlation_id": "req_12345"
}
```

**Parameters:**
- `model_name` (required): Calculation method (`sma`, `bia`, `tsa`, `what-if`)
- `execution_mode` (required): Execution mode (`sync`, `async`)
- `entity_id` (required): Entity identifier
- `calculation_date` (required): Calculation date (YYYY-MM-DD)
- `parameters` (optional): Calculation parameters
- `callback_url` (optional): Webhook URL for async jobs
- `idempotency_key` (optional): Unique key for idempotent requests
- `correlation_id` (optional): Request correlation ID

**Example Request:**
```bash
curl -X POST "https://orm-calculator.your-domain.com/api/v1/calculation-jobs" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "sma",
    "execution_mode": "sync",
    "entity_id": "BANK001",
    "calculation_date": "2024-03-31"
  }'
```

**Synchronous Response (execution_mode: sync):**
```json
{
  "job_id": "job_20240331_103000_001234",
  "status": "completed",
  "results": {
    "business_indicator": 50000000000,
    "business_indicator_component": 7500000000,
    "loss_component": 1500000000,
    "internal_loss_multiplier": 1.2,
    "operational_risk_capital": 9000000000,
    "risk_weighted_assets": 112500000000,
    "bucket": 2,
    "methodology": "sma",
    "calculation_metadata": {
      "ilm_gate_applied": false,
      "data_quality_score": 0.95,
      "loss_events_included": 1250
    }
  },
  "run_id": "run_20240331_103000_001234",
  "calculation_date": "2024-03-31",
  "entity_id": "BANK001",
  "created_at": "2024-03-31T10:30:00Z",
  "completed_at": "2024-03-31T10:30:15Z",
  "processing_time_seconds": 15.2
}
```

**Asynchronous Response (execution_mode: async):**
```json
{
  "job_id": "job_20240331_103000_001235",
  "status": "queued",
  "estimated_completion_time": "2024-03-31T10:35:00Z",
  "callback_url": "https://your-system.com/webhooks/calculation-complete",
  "created_at": "2024-03-31T10:30:00Z"
}
```

#### Get Job Status and Results

**Endpoint:** `GET /calculation-jobs/{job_id}`

**Description:** Retrieve job status and results

**Example Request:**
```bash
curl -X GET "https://orm-calculator.your-domain.com/api/v1/calculation-jobs/job_20240331_103000_001234" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**
```json
{
  "job_id": "job_20240331_103000_001234",
  "status": "completed",
  "progress_percentage": 100,
  "started_at": "2024-03-31T10:30:00Z",
  "completed_at": "2024-03-31T10:30:15Z",
  "processing_time_seconds": 15.2,
  "result_available": true,
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
  "run_id": "run_20240331_103000_001234"
}
```

### Loss Data Management Endpoints

#### Ingest Loss Events

**Endpoint:** `POST /loss-data/events`

**Description:** Ingest operational loss event data

**Request Body:**
```json
{
  "events": [
    {
      "event_id": "LOSS_001",
      "entity_id": "BANK001",
      "occurrence_date": "2023-06-15",
      "discovery_date": "2023-06-20",
      "accounting_date": "2023-06-30",
      "gross_loss": 500000,
      "recoveries": 50000,
      "business_line": "retail_banking",
      "event_type": "external_fraud",
      "description": "Credit card fraud incident",
      "is_outsourced": false
    }
  ]
}
```

**Example Request:**
```bash
curl -X POST "https://orm-calculator.your-domain.com/api/v1/loss-data/events" \
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

**Example Response:**
```json
{
  "ingested_count": 1,
  "validation_results": [
    {
      "event_id": "LOSS_001",
      "status": "success",
      "net_loss": 450000,
      "above_threshold": true
    }
  ],
  "summary": {
    "total_events": 1,
    "successful": 1,
    "failed": 0,
    "warnings": 0
  }
}
```

#### Ingest Business Indicator Data

**Endpoint:** `POST /loss-data/business-indicators`

**Description:** Ingest business indicator data

**Request Body:**
```json
{
  "indicators": [
    {
      "entity_id": "BANK001",
      "period": "2023-Q4",
      "calculation_date": "2023-12-31",
      "ildc": 45000000000,
      "sc": 3000000000,
      "fc": 2000000000,
      "source": "GL_SYSTEM"
    }
  ]
}
```

**Example Request:**
```bash
curl -X POST "https://orm-calculator.your-domain.com/api/v1/loss-data/business-indicators" \
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

### Data Lineage Endpoints

#### Get Calculation Lineage

**Endpoint:** `GET /lineage/{run_id}`

**Description:** Retrieve complete data lineage for a calculation run

**Example Request:**
```bash
curl -X GET "https://orm-calculator.your-domain.com/api/v1/lineage/run_20240331_103000_001234" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**
```json
{
  "run_id": "run_20240331_103000_001234",
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
      "effective_date": "2024-01-01",
      "parameters": {
        "minimum_loss_threshold": 100000,
        "bucket_1_threshold": 80000000000,
        "bucket_2_threshold": 2400000000000
      }
    }
  ],
  "model_versions": [
    {
      "model_name": "sma",
      "version": "1.0.0",
      "implementation_hash": "abc123def456"
    }
  ],
  "input_aggregates": [
    {
      "data_type": "business_indicators",
      "record_count": 12,
      "date_range": {
        "start": "2021-01-01",
        "end": "2023-12-31"
      },
      "checksum": "sha256:789abc123def"
    },
    {
      "data_type": "loss_events",
      "record_count": 1250,
      "date_range": {
        "start": "2014-01-01",
        "end": "2023-12-31"
      },
      "checksum": "sha256:def456789abc"
    }
  ],
  "included_loss_ids": ["LOSS_001", "LOSS_002", "LOSS_003"],
  "environment_hash": "env_abc123def456",
  "created_at": "2024-03-31T10:30:00Z",
  "reproducible": true,
  "audit_metadata": {
    "initiator": "user@bank.com",
    "system_version": "0.1.0",
    "database_version": "1.0.0",
    "compliance_flags": ["RBI_COMPLIANT", "CERT_IN_COMPLIANT"]
  }
}
```

### Parameter Management Endpoints

#### Get Model Parameters

**Endpoint:** `GET /models/{model_name}/parameters`

**Description:** Get current parameters for a calculation model

**Example Request:**
```bash
curl -X GET "https://orm-calculator.your-domain.com/api/v1/models/sma/parameters" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**
```json
{
  "model_name": "sma",
  "version_id": "v1.0.0",
  "effective_date": "2024-01-01",
  "parameters": {
    "minimum_loss_threshold": 100000,
    "loss_data_years": 10,
    "bi_averaging_years": 3,
    "bucket_1_threshold": 80000000000,
    "bucket_2_threshold": 2400000000000,
    "marginal_coeff_1": 0.12,
    "marginal_coeff_2": 0.15,
    "marginal_coeff_3": 0.18,
    "loss_multiplier": 15,
    "rwa_multiplier": 12.5
  },
  "created_by": "system",
  "approved_by": "risk_manager",
  "change_reason": "Initial parameter set"
}
```

#### Propose Parameter Change

**Endpoint:** `POST /parameters/proposals`

**Description:** Propose a parameter change (Maker-Checker workflow)

**Request Body:**
```json
{
  "model_name": "sma",
  "parameter_name": "minimum_loss_threshold",
  "current_value": 100000,
  "proposed_value": 150000,
  "change_reason": "Regulatory update",
  "effective_date": "2024-04-01",
  "business_justification": "RBI circular dated 2024-03-01 requires threshold increase"
}
```

**Example Request:**
```bash
curl -X POST "https://orm-calculator.your-domain.com/api/v1/parameters/proposals" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "sma",
    "parameter_name": "minimum_loss_threshold",
    "current_value": 100000,
    "proposed_value": 150000,
    "change_reason": "Regulatory update"
  }'
```

**Example Response:**
```json
{
  "proposal_id": "prop_20240331_001",
  "status": "pending_review",
  "workflow_stage": "checker_review",
  "proposed_by": "user@bank.com",
  "created_at": "2024-03-31T10:30:00Z",
  "estimated_approval_date": "2024-04-02T10:30:00Z"
}
```

### Analytics and Stress Testing Endpoints

#### Run Stress Test

**Endpoint:** `POST /analytics/stress-test`

**Description:** Execute stress testing scenarios

**Request Body:**
```json
{
  "entity_id": "BANK001",
  "calculation_date": "2024-03-31",
  "scenarios": [
    {
      "scenario_name": "adverse_scenario",
      "loss_shock": 1.5,
      "bi_shock": 0.8,
      "recovery_haircut": 0.3
    },
    {
      "scenario_name": "severe_adverse",
      "loss_shock": 2.0,
      "bi_shock": 0.6,
      "recovery_haircut": 0.5
    }
  ]
}
```

**Example Request:**
```bash
curl -X POST "https://orm-calculator.your-domain.com/api/v1/analytics/stress-test" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "BANK001",
    "calculation_date": "2024-03-31",
    "scenarios": [
      {
        "scenario_name": "adverse_scenario",
        "loss_shock": 1.5,
        "bi_shock": 0.8,
        "recovery_haircut": 0.3
      }
    ]
  }'
```

**Example Response:**
```json
{
  "stress_test_id": "stress_20240331_001",
  "base_calculation": {
    "orc": 9000000000,
    "rwa": 112500000000
  },
  "scenario_results": [
    {
      "scenario_name": "adverse_scenario",
      "stressed_orc": 12600000000,
      "stressed_rwa": 157500000000,
      "capital_impact": 3600000000,
      "impact_percentage": 40.0,
      "scenario_parameters": {
        "loss_shock": 1.5,
        "bi_shock": 0.8,
        "recovery_haircut": 0.3
      }
    }
  ],
  "summary": {
    "max_capital_impact": 3600000000,
    "max_impact_percentage": 40.0,
    "worst_case_scenario": "adverse_scenario"
  },
  "run_id": "run_20240331_stress_001",
  "created_at": "2024-03-31T10:30:00Z"
}
```

### Performance Monitoring Endpoints

#### Get Performance Metrics

**Endpoint:** `GET /performance/metrics`

**Description:** Get system performance metrics

**Example Request:**
```bash
curl -X GET "https://orm-calculator.your-domain.com/api/v1/performance/metrics" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**
```json
{
  "timestamp": "2024-03-31T10:30:00Z",
  "system_metrics": {
    "cpu_usage_percent": 45.2,
    "memory_usage_percent": 62.8,
    "disk_usage_percent": 23.1,
    "active_connections": 15
  },
  "application_metrics": {
    "total_requests": 1250,
    "successful_requests": 1235,
    "failed_requests": 15,
    "average_response_time_ms": 245,
    "p95_response_time_ms": 850,
    "p99_response_time_ms": 1200
  },
  "calculation_metrics": {
    "total_calculations": 45,
    "successful_calculations": 44,
    "failed_calculations": 1,
    "average_calculation_time_seconds": 15.2,
    "longest_calculation_time_seconds": 45.8
  },
  "database_metrics": {
    "connection_pool_active": 8,
    "connection_pool_idle": 12,
    "query_count": 2340,
    "average_query_time_ms": 12.5
  }
}
```

## Webhook Notifications

For asynchronous jobs, the system can send webhook notifications when jobs complete.

### Webhook Payload

**HTTP Method:** POST
**Content-Type:** application/json

**Headers:**
```
X-Webhook-Event: calculation.completed
X-Webhook-Signature: sha256=<signature>
X-Correlation-ID: <correlation_id>
```

**Payload:**
```json
{
  "event": "calculation.completed",
  "job_id": "job_20240331_103000_001235",
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
  "run_id": "run_20240331_103000_001235",
  "completed_at": "2024-03-31T10:35:00Z",
  "processing_time_seconds": 285.7
}
```

### Webhook Security

Webhooks are signed using HMAC-SHA256. Verify the signature using the webhook secret:

```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected_signature}", signature)
```

## SDK Examples

### Python SDK Example

```python
import requests
from typing import Dict, Any

class ORMCalculatorClient:
    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
    
    def authenticate(self):
        """Obtain access token"""
        response = requests.post(
            f"{self.base_url}/auth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
        )
        response.raise_for_status()
        self.access_token = response.json()["access_token"]
    
    def calculate_sma(self, entity_id: str, calculation_date: str, 
                     parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Calculate SMA capital"""
        if not self.access_token:
            self.authenticate()
        
        payload = {
            "model_name": "sma",
            "execution_mode": "sync",
            "entity_id": entity_id,
            "calculation_date": calculation_date
        }
        
        if parameters:
            payload["parameters"] = parameters
        
        response = requests.post(
            f"{self.base_url}/calculation-jobs",
            json=payload,
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        response.raise_for_status()
        return response.json()

# Usage example
client = ORMCalculatorClient(
    base_url="https://orm-calculator.your-domain.com/api/v1",
    client_id="your_client_id",
    client_secret="your_client_secret"
)

result = client.calculate_sma(
    entity_id="BANK001",
    calculation_date="2024-03-31",
    parameters={"minimum_loss_threshold": 100000}
)

print(f"Operational Risk Capital: {result['results']['operational_risk_capital']}")
```

### JavaScript SDK Example

```javascript
class ORMCalculatorClient {
    constructor(baseUrl, clientId, clientSecret) {
        this.baseUrl = baseUrl;
        this.clientId = clientId;
        this.clientSecret = clientSecret;
        this.accessToken = null;
    }
    
    async authenticate() {
        const response = await fetch(`${this.baseUrl}/auth/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                grant_type: 'client_credentials',
                client_id: this.clientId,
                client_secret: this.clientSecret
            })
        });
        
        if (!response.ok) {
            throw new Error('Authentication failed');
        }
        
        const data = await response.json();
        this.accessToken = data.access_token;
    }
    
    async calculateSMA(entityId, calculationDate, parameters = {}) {
        if (!this.accessToken) {
            await this.authenticate();
        }
        
        const payload = {
            model_name: 'sma',
            execution_mode: 'sync',
            entity_id: entityId,
            calculation_date: calculationDate,
            parameters: parameters
        };
        
        const response = await fetch(`${this.baseUrl}/calculation-jobs`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.accessToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            throw new Error(`Calculation failed: ${response.statusText}`);
        }
        
        return await response.json();
    }
}

// Usage example
const client = new ORMCalculatorClient(
    'https://orm-calculator.your-domain.com/api/v1',
    'your_client_id',
    'your_client_secret'
);

client.calculateSMA('BANK001', '2024-03-31', {
    minimum_loss_threshold: 100000
}).then(result => {
    console.log('Operational Risk Capital:', result.results.operational_risk_capital);
}).catch(error => {
    console.error('Error:', error);
});
```

## Interactive API Explorer

The API provides interactive documentation through Swagger UI and ReDoc:

- **Swagger UI**: `https://orm-calculator.your-domain.com/docs`
- **ReDoc**: `https://orm-calculator.your-domain.com/redoc`
- **OpenAPI Spec**: `https://orm-calculator.your-domain.com/openapi.json`

These interfaces allow you to:
- Explore all available endpoints
- Test API calls directly from the browser
- View request/response schemas
- Download OpenAPI specifications

## Support and Resources

- **API Status Page**: `https://status.orm-calculator.your-domain.com`
- **Developer Portal**: `https://developers.orm-calculator.your-domain.com`
- **Support Email**: api-support@your-company.com
- **GitHub Repository**: `https://github.com/your-org/orm-capital-calculator`