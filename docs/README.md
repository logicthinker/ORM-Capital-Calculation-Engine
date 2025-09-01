# ORM Capital Calculator Engine - Documentation

## Overview

The ORM Capital Calculator Engine is a comprehensive system for calculating operational risk capital requirements in compliance with RBI's Basel III Standardized Measurement Approach (SMA). This documentation provides complete information for deploying, configuring, and using the system.

## Documentation Structure

### User Guides
- **[User Guide](user-guide.md)** - Complete guide for using the API and system features
- **[Calculation Methods Guide](calculation-methods.md)** - Detailed explanation of SMA, BIA, TSA methodologies
- **[API Documentation](api-documentation.md)** - Comprehensive API reference with examples

### Deployment Guides
- **[Deployment Guide](deployment-guide.md)** - Step-by-step deployment instructions for all environments
- **[Deployment Checklist](deployment-checklist.md)** - Production deployment checklist and sign-off
- **[Health Check Scripts](../deployment/scripts/)** - Automated health check and validation scripts

### Technical Documentation
- **[OpenAPI Specification](openapi.json)** - Machine-readable API specification
- **[API Endpoints Summary](api-endpoints.md)** - Quick reference of all endpoints
- **[Architecture Overview](../README.md#architecture)** - System architecture and design principles

### Configuration Templates
- **[Environment Templates](../deployment/templates/)** - Configuration templates for different environments
- **[Kubernetes Manifests](../deployment/kubernetes/)** - Container orchestration configurations
- **[Docker Compose](../docker-compose.yml)** - Container deployment configurations

### Monitoring and Logging
- **[Prometheus Configuration](../deployment/monitoring/prometheus.yml)** - Metrics collection setup
- **[Grafana Dashboards](../deployment/monitoring/grafana/)** - Pre-built monitoring dashboards
- **[Alert Rules](../deployment/monitoring/alert_rules.yml)** - Production alerting configuration
- **[Logging Configuration](../deployment/logging/)** - Structured logging and compliance setup

## Quick Start

### Local Development
```bash
# Clone repository
git clone https://github.com/your-org/orm-capital-calculator.git
cd orm-capital-calculator

# Set up environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .[dev,test]

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
python scripts/init-database.py
alembic upgrade head

# Start development server
python scripts/start-server.py
```

### Docker Development
```bash
# Start development environment
docker-compose up orm-calculator-dev

# View logs
docker-compose logs -f orm-calculator-dev

# Access API documentation
# Open browser to: http://localhost:8000/docs
```

### Production Deployment
```bash
# Build production image
docker build --target production -t orm-calculator:prod .

# Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Or deploy to Kubernetes
kubectl apply -f deployment/kubernetes/
```

## API Quick Reference

### Authentication
```bash
# Obtain access token
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"
```

### Health Check
```bash
# Basic health check
curl http://localhost:8000/api/v1/health

# Detailed health check (requires auth)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/health/detailed
```

### SMA Calculation
```bash
# Synchronous calculation
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

### Data Lineage
```bash
# Get calculation lineage
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/lineage/run_12345
```

## Key Features

### Calculation Methods
- **SMA (Standardized Measurement Approach)** - Primary Basel III method
- **BIA (Basic Indicator Approach)** - Legacy method using gross income
- **TSA (Traditional Standardized Approach)** - Legacy method with business lines
- **What-If Scenarios** - Stress testing and sensitivity analysis

### Compliance Features
- **RBI Basel III Compliance** - Full SMA implementation per RBI guidelines
- **CERT-In Security Controls** - Indian cybersecurity compliance
- **Data Residency** - India-only data processing and storage
- **Audit Trail** - Complete lineage and reproducibility
- **Parameter Governance** - Maker-checker-approver workflow

### Technical Features
- **Job-Based API** - Synchronous and asynchronous execution
- **Webhook Notifications** - Real-time job completion callbacks
- **Database Abstraction** - SQLite (dev) to PostgreSQL (prod) migration
- **Container Ready** - Docker and Kubernetes deployment
- **Comprehensive Monitoring** - Prometheus metrics and Grafana dashboards

## System Requirements

### Development Environment
- Python 3.9+
- SQLite (included with Python)
- 4GB RAM minimum
- 10GB disk space

### Production Environment
- Linux server (Ubuntu 20.04+ recommended)
- PostgreSQL 13+ or compatible database
- Redis 6+ for caching
- 8GB RAM minimum
- 100GB disk space minimum
- SSL certificates for HTTPS

### Container Environment
- Docker 20.10+
- Docker Compose 2.0+
- Kubernetes 1.20+ (for K8s deployment)
- 4GB RAM per container
- Persistent storage for data

## Security Considerations

### Authentication & Authorization
- OAuth 2.0 client credentials flow
- JWT token-based authentication
- Role-based access control (RBAC)
- API key fallback for development

### Data Protection
- AES-256 encryption at rest
- TLS 1.3+ encryption in transit
- Sensitive data masking in logs
- PII data handling procedures

### Compliance
- CERT-In security controls implementation
- RBI data residency requirements
- 180+ day audit log retention
- Tamper-evident audit trails

## Performance Targets

### SLA Requirements
- **Quarterly Full Run**: ≤ 30 minutes
- **Ad-hoc What-if**: ≤ 60 seconds
- **Concurrent Users**: ≥ 50 users without degradation
- **API Response Time**: 95th percentile < 5 seconds

### Scalability
- Horizontal scaling with load balancers
- Database connection pooling
- Redis caching for performance
- Asynchronous job processing

## Monitoring and Alerting

### Health Checks
- **Liveness**: Basic application responsiveness
- **Readiness**: Service ready to handle traffic
- **Startup**: Application initialization complete

### Metrics Collection
- Application performance metrics
- Business logic metrics (calculations, jobs)
- System resource metrics
- Security event metrics

### Alerting
- Critical: Service down, database failures
- Warning: High response times, resource usage
- Info: Unusual patterns, capacity planning

## Support and Maintenance

### Documentation
- **Interactive API Docs**: `/docs` endpoint (Swagger UI)
- **API Specification**: `/openapi.json` endpoint
- **User Guides**: Complete usage documentation
- **Deployment Guides**: Environment-specific instructions

### Troubleshooting
- **Health Check Scripts**: Automated validation tools
- **Log Analysis**: Structured logging with correlation IDs
- **Performance Profiling**: Built-in performance monitoring
- **Error Tracking**: Standardized error handling

### Maintenance
- **Automated Backups**: Database and configuration backups
- **Log Rotation**: Compliance-aware log retention
- **Security Updates**: Regular dependency updates
- **Performance Optimization**: Continuous monitoring and tuning

## Getting Help

### Resources
- **API Documentation**: [Interactive Docs](http://localhost:8000/docs)
- **GitHub Repository**: [Source Code and Issues](https://github.com/your-org/orm-capital-calculator)
- **User Guide**: [Complete Usage Guide](user-guide.md)
- **Deployment Guide**: [Deployment Instructions](deployment-guide.md)

### Support Channels
- **Technical Support**: support@your-company.com
- **Security Issues**: security@your-company.com
- **Emergency Hotline**: +91-XXX-XXX-XXXX
- **Documentation Issues**: docs@your-company.com

### Contributing
- **Bug Reports**: Use GitHub Issues
- **Feature Requests**: Use GitHub Discussions
- **Code Contributions**: Submit Pull Requests
- **Documentation**: Help improve guides and examples

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## Compliance Statement

This system is designed to comply with:
- RBI Basel III Operational Risk Capital Requirements
- CERT-In Cybersecurity Guidelines for Banking Sector
- Indian Data Protection and Residency Requirements
- Basel Committee on Banking Supervision Standards

For compliance questions, contact: compliance@your-company.com