#!/bin/bash

# Health Check Script for ORM Capital Calculator Engine
# This script performs comprehensive health checks for deployment validation

set -euo pipefail

# Configuration
DEFAULT_HOST="localhost"
DEFAULT_PORT="8000"
DEFAULT_PROTOCOL="http"
DEFAULT_TIMEOUT="30"

# Parse command line arguments
HOST="${1:-$DEFAULT_HOST}"
PORT="${2:-$DEFAULT_PORT}"
PROTOCOL="${3:-$DEFAULT_PROTOCOL}"
TIMEOUT="${4:-$DEFAULT_TIMEOUT}"

BASE_URL="${PROTOCOL}://${HOST}:${PORT}/api/v1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Health check functions
check_basic_health() {
    log_info "Checking basic health endpoint..."
    
    local response
    local http_code
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" --max-time "$TIMEOUT" "${BASE_URL}/health" || echo "HTTPSTATUS:000")
    http_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    
    if [[ "$http_code" == "200" ]]; then
        log_success "Basic health check passed"
        return 0
    else
        log_error "Basic health check failed (HTTP $http_code)"
        return 1
    fi
}

check_readiness() {
    log_info "Checking readiness endpoint..."
    
    local response
    local http_code
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" --max-time "$TIMEOUT" "${BASE_URL}/health/ready" || echo "HTTPSTATUS:000")
    http_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    
    if [[ "$http_code" == "200" ]]; then
        log_success "Readiness check passed"
        return 0
    elif [[ "$http_code" == "503" ]]; then
        log_warning "Service not ready (HTTP 503)"
        return 1
    else
        log_error "Readiness check failed (HTTP $http_code)"
        return 1
    fi
}

check_liveness() {
    log_info "Checking liveness endpoint..."
    
    local response
    local http_code
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" --max-time "$TIMEOUT" "${BASE_URL}/health/live" || echo "HTTPSTATUS:000")
    http_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    
    if [[ "$http_code" == "200" ]]; then
        log_success "Liveness check passed"
        return 0
    else
        log_error "Liveness check failed (HTTP $http_code)"
        return 1
    fi
}

check_startup() {
    log_info "Checking startup endpoint..."
    
    local response
    local http_code
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" --max-time "$TIMEOUT" "${BASE_URL}/health/startup" || echo "HTTPSTATUS:000")
    http_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    
    if [[ "$http_code" == "200" ]]; then
        log_success "Startup check passed"
        return 0
    elif [[ "$http_code" == "503" ]]; then
        log_warning "Startup in progress (HTTP 503)"
        return 1
    else
        log_error "Startup check failed (HTTP $http_code)"
        return 1
    fi
}

check_metrics() {
    log_info "Checking metrics endpoint..."
    
    local response
    local http_code
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" --max-time "$TIMEOUT" "${BASE_URL}/health/metrics" || echo "HTTPSTATUS:000")
    http_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    
    if [[ "$http_code" == "200" ]]; then
        log_success "Metrics endpoint accessible"
        return 0
    else
        log_warning "Metrics endpoint not accessible (HTTP $http_code)"
        return 1
    fi
}

check_api_endpoints() {
    log_info "Checking core API endpoints..."
    
    # Check OpenAPI docs
    local response
    local http_code
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" --max-time "$TIMEOUT" "${BASE_URL}/../docs" || echo "HTTPSTATUS:000")
    http_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    
    if [[ "$http_code" == "200" ]]; then
        log_success "API documentation accessible"
    else
        log_warning "API documentation not accessible (HTTP $http_code)"
    fi
    
    # Check OpenAPI spec
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" --max-time "$TIMEOUT" "${BASE_URL}/../openapi.json" || echo "HTTPSTATUS:000")
    http_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    
    if [[ "$http_code" == "200" ]]; then
        log_success "OpenAPI specification accessible"
    else
        log_warning "OpenAPI specification not accessible (HTTP $http_code)"
    fi
}

wait_for_startup() {
    log_info "Waiting for application startup..."
    
    local max_attempts=30
    local attempt=1
    local sleep_interval=2
    
    while [[ $attempt -le $max_attempts ]]; do
        log_info "Startup check attempt $attempt/$max_attempts"
        
        if check_startup; then
            log_success "Application startup completed"
            return 0
        fi
        
        if [[ $attempt -lt $max_attempts ]]; then
            log_info "Waiting ${sleep_interval}s before next attempt..."
            sleep $sleep_interval
        fi
        
        ((attempt++))
    done
    
    log_error "Application failed to start within expected time"
    return 1
}

wait_for_readiness() {
    log_info "Waiting for application readiness..."
    
    local max_attempts=15
    local attempt=1
    local sleep_interval=2
    
    while [[ $attempt -le $max_attempts ]]; do
        log_info "Readiness check attempt $attempt/$max_attempts"
        
        if check_readiness; then
            log_success "Application is ready"
            return 0
        fi
        
        if [[ $attempt -lt $max_attempts ]]; then
            log_info "Waiting ${sleep_interval}s before next attempt..."
            sleep $sleep_interval
        fi
        
        ((attempt++))
    done
    
    log_error "Application failed to become ready within expected time"
    return 1
}

perform_comprehensive_check() {
    log_info "Performing comprehensive health check..."
    
    local checks_passed=0
    local total_checks=6
    
    # Basic health check
    if check_basic_health; then
        ((checks_passed++))
    fi
    
    # Liveness check
    if check_liveness; then
        ((checks_passed++))
    fi
    
    # Startup check
    if check_startup; then
        ((checks_passed++))
    fi
    
    # Readiness check
    if check_readiness; then
        ((checks_passed++))
    fi
    
    # Metrics check
    if check_metrics; then
        ((checks_passed++))
    fi
    
    # API endpoints check
    if check_api_endpoints; then
        ((checks_passed++))
    fi
    
    log_info "Health check summary: $checks_passed/$total_checks checks passed"
    
    if [[ $checks_passed -eq $total_checks ]]; then
        log_success "All health checks passed!"
        return 0
    elif [[ $checks_passed -ge $((total_checks - 1)) ]]; then
        log_warning "Most health checks passed, but some warnings detected"
        return 0
    else
        log_error "Multiple health checks failed"
        return 1
    fi
}

show_usage() {
    echo "Usage: $0 [HOST] [PORT] [PROTOCOL] [TIMEOUT]"
    echo ""
    echo "Arguments:"
    echo "  HOST      Target host (default: localhost)"
    echo "  PORT      Target port (default: 8000)"
    echo "  PROTOCOL  Protocol to use (default: http)"
    echo "  TIMEOUT   Request timeout in seconds (default: 30)"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Check localhost:8000"
    echo "  $0 orm-calculator.com 443 https      # Check production"
    echo "  $0 staging.orm-calculator.com 80     # Check staging"
    echo ""
    echo "Commands:"
    echo "  $0 --wait-startup     # Wait for startup completion"
    echo "  $0 --wait-ready       # Wait for readiness"
    echo "  $0 --comprehensive    # Run all checks"
}

# Main execution
main() {
    case "${1:-}" in
        --help|-h)
            show_usage
            exit 0
            ;;
        --wait-startup)
            wait_for_startup
            exit $?
            ;;
        --wait-ready)
            wait_for_readiness
            exit $?
            ;;
        --comprehensive)
            perform_comprehensive_check
            exit $?
            ;;
        *)
            log_info "ORM Capital Calculator Health Check"
            log_info "Target: ${BASE_URL}"
            log_info "Timeout: ${TIMEOUT}s"
            echo ""
            
            perform_comprehensive_check
            exit $?
            ;;
    esac
}

# Check if curl is available
if ! command -v curl &> /dev/null; then
    log_error "curl is required but not installed"
    exit 1
fi

# Run main function
main "$@"