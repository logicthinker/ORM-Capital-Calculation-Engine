# ORM Capital Calculator Engine

A comprehensive system for calculating operational risk capital requirements in compliance with RBI's Basel III Standardized Measurement Approach (SMA) framework.

## Features

- **SMA Calculation Engine**: Full implementation of RBI Basel III SMA methodology
- **Legacy Methods Support**: BIA and TSA calculations for transition period
- **Job-Based APIs**: Asynchronous execution with webhook callbacks
- **Complete Auditability**: Immutable audit trails and data lineage tracking
- **Database Abstraction**: SQLite for development, PostgreSQL for production
- **Security Compliance**: CERT-In controls and RBI data residency requirements

## Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package installer)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd orm-capital-calculator
   ```

2. **Set up development environment**
   ```bash
   python scripts/setup-dev.py
   ```

3. **Start the development server**
   ```bash
   python scripts/start-server.py
   ```

4. **Visit the API documentation**
   - Swagger UI: http://127.0.0.1:8000/docs
   - ReDoc: http://127.0.0.1:8000/redoc

### Using Make Commands

```bash
make setup          # Set up development environment
make start           # Start development server
make test            # Run tests with coverage
make format          # Format code
make lint            # Run linting checks
make migrate         # Run database migrations
```

## Project Structure

```
orm-capital-calculator/
├── src/orm_calculator/          # Main application code
│   ├── api/                     # FastAPI routes and endpoints
│   ├── database/                # Database models and connections
│   ├── models/                  # Pydantic models
│   └── services/                # Business logic services
├── tests/                       # Test suite
├── scripts/                     # Development scripts
├── migrations/                  # Database migrations
├── data/                        # SQLite database files (development)
└── docs/                        # Documentation
```

## Development

### Running Tests

```bash
# Run all tests with coverage
make test

# Run specific test file
python -m pytest tests/test_api.py -v

# Run tests with coverage report
python -m pytest --cov=src/orm_calculator --cov-report=html
```

### Code Formatting

```bash
# Format all code
make format

# Check code style
make lint
```

### Database Management

```bash
# Run migrations
make migrate

# Create new migration
make migrate-create MSG="Description of changes"

# Reset database (WARNING: destroys all data)
make reset-db
```

## API Documentation

The API follows REST principles with OpenAPI 3.0 specification:

- **Base URL**: `http://localhost:8000/api/v1`
- **Health Check**: `GET /api/v1/health`
- **Interactive Docs**: `http://localhost:8000/docs`

## Configuration

Configuration is managed through environment variables. Copy `.env.example` to `.env` and modify as needed:

```bash
cp .env.example .env
```

Key configuration options:
- `DATABASE_URL`: Database connection string
- `ENVIRONMENT`: development/production
- `LOG_LEVEL`: Logging level
- `SECRET_KEY`: Application secret key

## Requirements Compliance

This system implements the following regulatory requirements:

- **RBI Basel III SMA**: Complete implementation of Standardized Measurement Approach
- **CERT-In Security Controls**: Security compliance for Indian banking systems
- **Data Residency**: All data processing within India
- **Audit Requirements**: Complete audit trails and reproducibility

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and formatting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For support and questions, please contact the development team.