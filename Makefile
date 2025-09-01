# ORM Capital Calculator Engine - Development Makefile

.PHONY: help install dev-install test format lint clean start setup migrate

help: ## Show this help message
	@echo "ORM Capital Calculator Engine - Development Commands"
	@echo "=================================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Set up development environment
	python scripts/setup-dev.py

install: ## Install production dependencies
	pip install -e .

dev-install: ## Install development dependencies
	pip install -e .[dev]

test: ## Run tests with coverage
	python scripts/run-tests.py

format: ## Format code with black and ruff
	python scripts/format-code.py

lint: ## Run linting checks
	python -m ruff check src/ tests/ scripts/
	python -m mypy src/orm_calculator

start: ## Start development server
	python scripts/start-server.py

migrate: ## Run database migrations
	python -m alembic upgrade head

migrate-create: ## Create new migration
	python -m alembic revision --autogenerate -m "$(MSG)"

clean: ## Clean up build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

reset-db: ## Reset database (WARNING: destroys all data)
	rm -f data/orm_calculator.db
	python -m alembic upgrade head

docker-build: ## Build Docker image
	docker build -t orm-capital-calculator .

docker-run: ## Run Docker container
	docker run -p 8000:8000 orm-capital-calculator