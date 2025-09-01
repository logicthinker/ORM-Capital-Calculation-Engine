# Security Implementation Guide

## Overview

The ORM Capital Calculator Engine implements comprehensive security controls to meet CERT-In compliance requirements and RBI data residency mandates. This document outlines the security architecture, configuration, and usage.

## Security Architecture

### Authentication & Authorization

#### OAuth 2.0 Client Credentials Flow
- **Production**: OAuth 2.0 with JWT tokens
- **Development**: API key fallback for testing
- **Token Expiration**: Configurable (default: 30 minutes)
- **Scopes**: `read`, `write`, `admin`, `audit`

#### Role-Based Access Control (RBAC)
- **Granular Permissions**: 25+ specific permissions
- **Predefined Roles**: 10 business roles (Risk Analyst, Risk Manager, etc.)
- **Permission Groups**: Common operation groupings
- **Dynamic Authorization**: Runtime permission checking

### Security Middleware Stack

1. **Request Logging Middleware** (innermost)
   - Correlation ID tracking
   - Security event logging
   - Performance monitoring

2. **Authentication Middleware**
   - JWT token validation
   - API key authentication (dev)
   - User context injection

3. **Rate Limiting Middleware**
   - Per-endpoint rate limits
   - Client-based tracking
   - Exponential backoff

4. **Security Headers Middleware**
   - CERT-In compliant headers
   - CSP, HSTS, X-Frame-Options
   - Data residency indicators

5. **CORS Middleware** (outermost)
   - Environment-specific origins
   - Credential handling
   - Method restrictions

### Security Headers

#### CERT-In Compliance Headers
```http
X-Security-Framework: CERT-In-Compliant
X-Data-Residency: IN
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

#### Rate Limiting Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1640995200
```

## Configuration

### Environment-Based Security

#### Development Configuration
```python
# Relaxed security for development
security = SecurityConfig(
    use_https=False,
    cors_origins=["http://localhost:3000"],
    api_keys=["dev-api-key-12345"],
    enable_security_headers=True
)
```

#### Production Configuration
```python
# Strict security for production
security = SecurityConfig(
    use_https=True,
    cors_origins=[],  # Must be explicitly set
    oauth2_token_url="https://auth.example.com/token",
    enable_security_headers=True,
    hsts_max_age=31536000
)
```

### Rate Limiting Configuration

```python
rate_limit = RateLimitConfig(
    default_rate_limit=100,        # requests/minute
    calculation_rate_limit=50,     # for heavy operations
    health_rate_limit=1000,        # for monitoring
    rate_limit_storage="memory"    # or "redis" for production
)
```

## Usage Examples

### API Authentication

#### Using API Key (Development)
```bash
curl -H "X-API-Key: dev-api-key-12345" \
     http://localhost:8000/api/v1/health/
```

#### Using JWT Token (Production)
```bash
# Get token from OAuth provider
TOKEN=$(curl -X POST https://auth.example.com/token \
  -d "grant_type=client_credentials" \
  -d "client_id=your_client_id" \
  -d "client_secret=your_secret" \
  -d "scope=read write" | jq -r .access_token)

# Use token in API calls
curl -H "Authorization: Bearer $TOKEN" \
     https://api.example.com/api/v1/calculation-jobs
```

### Permission-Based Endpoints

```python
from orm_calculator.security.rbac import require_permission, Permission

@router.post("/calculation-jobs")
async def create_calculation(
    request: CalculationRequest,
    user: User = Depends(require_permission(Permission.CREATE_JOBS))
):
    # Only users with CREATE_JOBS permission can access
    pass
```

### Role-Based Access

```python
from orm_calculator.security.rbac import require_role, Role

@router.get("/admin/metrics")
async def get_metrics(
    user: User = Depends(require_role(Role.SYSTEM_ADMINISTRATOR))
):
    # Only system administrators can access
    pass
```

## Security Monitoring

### Health Check Endpoints

#### Basic Health (Public)
```bash
GET /api/v1/health/
```

#### Detailed Health (Admin Only)
```bash
GET /api/v1/health/detailed
Authorization: Bearer <admin_token>
```

#### Security Events (Audit Access)
```bash
GET /api/v1/health/security-events
Authorization: Bearer <audit_token>
```

### Security Event Types

- `AUTHENTICATION_FAILED`: Invalid credentials
- `AUTHORIZATION_FAILED`: Insufficient permissions
- `RATE_LIMIT_EXCEEDED`: Rate limit violations
- `SERVER_ERROR`: System errors
- `REQUEST_EXCEPTION`: Unhandled exceptions

## Compliance Features

### CERT-In Compliance
- ✅ Security headers implementation
- ✅ Incident reporting capability
- ✅ 180+ day audit log retention
- ✅ Security event monitoring
- ✅ Data encryption (TLS 1.3+)

### RBI Data Residency
- ✅ India region enforcement
- ✅ Data residency headers
- ✅ Audit trail locality
- ✅ NTP synchronization (NIC/NPL)

### Basel III Security Requirements
- ✅ Immutable audit trails
- ✅ Calculation reproducibility
- ✅ Parameter governance
- ✅ Supervisor override controls

## Security Testing

### Automated Security Tests
```bash
# Run security test suite
python -m pytest tests/test_security.py -v

# Test specific security components
python -m pytest tests/test_security.py::TestAuthentication -v
python -m pytest tests/test_security.py::TestRBAC -v
```

### Manual Security Testing
```bash
# Test rate limiting
for i in {1..10}; do
  curl -w "%{http_code}\n" http://localhost:8000/api/v1/health/
done

# Test security headers
curl -I http://localhost:8000/api/v1/health/

# Test authentication
curl -H "Authorization: Bearer invalid_token" \
     http://localhost:8000/api/v1/calculation-jobs
```

## Production Deployment

### Environment Variables
```bash
# Security configuration
SECURITY_SECRET_KEY=your-production-secret-key
SECURITY_USE_HTTPS=true
SECURITY_OAUTH2_TOKEN_URL=https://your-oauth-provider/token
SECURITY_OAUTH2_CLIENT_ID=your-client-id
SECURITY_OAUTH2_CLIENT_SECRET=your-client-secret

# CORS configuration
SECURITY_CORS_ORIGINS=["https://your-frontend.com"]
SECURITY_TRUSTED_HOSTS=["your-api-domain.com"]

# Rate limiting
RATE_LIMIT_RATE_LIMIT_STORAGE=redis
RATE_LIMIT_REDIS_URL=redis://your-redis-server:6379

# Compliance
COMPLIANCE_ENFORCE_DATA_RESIDENCY=true
COMPLIANCE_CERT_IN_COMPLIANCE=true
```

### SSL/TLS Configuration
```bash
# Certificate files
SECURITY_SSL_CERT_FILE=/path/to/cert.pem
SECURITY_SSL_KEY_FILE=/path/to/key.pem
SECURITY_SSL_CA_FILE=/path/to/ca.pem
```

### Monitoring Integration
```bash
# SOC integration
LOG_SOC_ENDPOINT=https://your-soc.com/events
LOG_SOC_API_KEY=your-soc-api-key

# Security logging
LOG_SECURITY_LOG_FILE=/var/log/orm-calculator/security.log
LOG_AUDIT_LOG_FILE=/var/log/orm-calculator/audit.log
```

## Troubleshooting

### Common Issues

#### Authentication Failures
```bash
# Check token validity
python -c "
from orm_calculator.security.auth import verify_token
try:
    result = verify_token('your_token_here')
    print('Token valid:', result.username)
except Exception as e:
    print('Token invalid:', e)
"
```

#### Rate Limiting Issues
```bash
# Check rate limit status
curl -I http://localhost:8000/api/v1/health/ | grep -i ratelimit
```

#### Permission Errors
```bash
# Check user permissions
python -c "
from orm_calculator.security.rbac import get_user_permissions
from orm_calculator.security.auth import User
user = User(username='test', scopes=['read'])
print('Permissions:', list(get_user_permissions(user)))
"
```

### Security Logs
```bash
# View security events
tail -f /var/log/orm-calculator/security.log | grep SECURITY_EVENT

# Monitor authentication failures
grep "AUTHENTICATION_FAILED" /var/log/orm-calculator/security.log
```

## Best Practices

### Development
1. Use API keys only in development
2. Never commit secrets to version control
3. Test with realistic rate limits
4. Validate security headers in tests

### Production
1. Use OAuth 2.0 with short-lived tokens
2. Implement token refresh mechanisms
3. Monitor security events continuously
4. Regular security audits and penetration testing
5. Keep dependencies updated
6. Use environment-specific configurations

### Compliance
1. Regular CERT-In compliance audits
2. Data residency validation
3. Audit log integrity checks
4. Security incident response procedures
5. Regular security training for developers