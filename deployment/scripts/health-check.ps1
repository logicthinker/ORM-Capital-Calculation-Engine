# Health Check Script for ORM Capital Calculator Engine (PowerShell)
# This script performs comprehensive health checks for deployment validation

param(
    [string]$Host = "localhost",
    [int]$Port = 8000,
    [string]$Protocol = "http",
    [int]$Timeout = 30,
    [switch]$WaitStartup,
    [switch]$WaitReady,
    [switch]$Comprehensive,
    [switch]$Help
)

# Configuration
$BaseUrl = "${Protocol}://${Host}:${Port}/api/v1"

# Logging functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Health check functions
function Test-BasicHealth {
    Write-Info "Checking basic health endpoint..."
    
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -TimeoutSec $Timeout -ErrorAction Stop
        Write-Success "Basic health check passed"
        return $true
    }
    catch {
        Write-Error "Basic health check failed: $($_.Exception.Message)"
        return $false
    }
}

function Test-Readiness {
    Write-Info "Checking readiness endpoint..."
    
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/health/ready" -Method Get -TimeoutSec $Timeout -ErrorAction Stop
        Write-Success "Readiness check passed"
        return $true
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq 503) {
            Write-Warning "Service not ready (HTTP 503)"
        }
        else {
            Write-Error "Readiness check failed: $($_.Exception.Message)"
        }
        return $false
    }
}

function Test-Liveness {
    Write-Info "Checking liveness endpoint..."
    
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/health/live" -Method Get -TimeoutSec $Timeout -ErrorAction Stop
        Write-Success "Liveness check passed"
        return $true
    }
    catch {
        Write-Error "Liveness check failed: $($_.Exception.Message)"
        return $false
    }
}

function Test-Startup {
    Write-Info "Checking startup endpoint..."
    
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/health/startup" -Method Get -TimeoutSec $Timeout -ErrorAction Stop
        Write-Success "Startup check passed"
        return $true
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq 503) {
            Write-Warning "Startup in progress (HTTP 503)"
        }
        else {
            Write-Error "Startup check failed: $($_.Exception.Message)"
        }
        return $false
    }
}

function Test-Metrics {
    Write-Info "Checking metrics endpoint..."
    
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/health/metrics" -Method Get -TimeoutSec $Timeout -ErrorAction Stop
        Write-Success "Metrics endpoint accessible"
        return $true
    }
    catch {
        Write-Warning "Metrics endpoint not accessible: $($_.Exception.Message)"
        return $false
    }
}

function Test-ApiEndpoints {
    Write-Info "Checking core API endpoints..."
    
    $success = $true
    
    # Check OpenAPI docs
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/../docs" -Method Get -TimeoutSec $Timeout -ErrorAction Stop
        Write-Success "API documentation accessible"
    }
    catch {
        Write-Warning "API documentation not accessible: $($_.Exception.Message)"
        $success = $false
    }
    
    # Check OpenAPI spec
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/../openapi.json" -Method Get -TimeoutSec $Timeout -ErrorAction Stop
        Write-Success "OpenAPI specification accessible"
    }
    catch {
        Write-Warning "OpenAPI specification not accessible: $($_.Exception.Message)"
        $success = $false
    }
    
    return $success
}

function Wait-ForStartup {
    Write-Info "Waiting for application startup..."
    
    $maxAttempts = 30
    $attempt = 1
    $sleepInterval = 2
    
    while ($attempt -le $maxAttempts) {
        Write-Info "Startup check attempt $attempt/$maxAttempts"
        
        if (Test-Startup) {
            Write-Success "Application startup completed"
            return $true
        }
        
        if ($attempt -lt $maxAttempts) {
            Write-Info "Waiting ${sleepInterval}s before next attempt..."
            Start-Sleep -Seconds $sleepInterval
        }
        
        $attempt++
    }
    
    Write-Error "Application failed to start within expected time"
    return $false
}

function Wait-ForReadiness {
    Write-Info "Waiting for application readiness..."
    
    $maxAttempts = 15
    $attempt = 1
    $sleepInterval = 2
    
    while ($attempt -le $maxAttempts) {
        Write-Info "Readiness check attempt $attempt/$maxAttempts"
        
        if (Test-Readiness) {
            Write-Success "Application is ready"
            return $true
        }
        
        if ($attempt -lt $maxAttempts) {
            Write-Info "Waiting ${sleepInterval}s before next attempt..."
            Start-Sleep -Seconds $sleepInterval
        }
        
        $attempt++
    }
    
    Write-Error "Application failed to become ready within expected time"
    return $false
}

function Invoke-ComprehensiveCheck {
    Write-Info "Performing comprehensive health check..."
    
    $checksPassed = 0
    $totalChecks = 6
    
    # Basic health check
    if (Test-BasicHealth) {
        $checksPassed++
    }
    
    # Liveness check
    if (Test-Liveness) {
        $checksPassed++
    }
    
    # Startup check
    if (Test-Startup) {
        $checksPassed++
    }
    
    # Readiness check
    if (Test-Readiness) {
        $checksPassed++
    }
    
    # Metrics check
    if (Test-Metrics) {
        $checksPassed++
    }
    
    # API endpoints check
    if (Test-ApiEndpoints) {
        $checksPassed++
    }
    
    Write-Info "Health check summary: $checksPassed/$totalChecks checks passed"
    
    if ($checksPassed -eq $totalChecks) {
        Write-Success "All health checks passed!"
        return $true
    }
    elseif ($checksPassed -ge ($totalChecks - 1)) {
        Write-Warning "Most health checks passed, but some warnings detected"
        return $true
    }
    else {
        Write-Error "Multiple health checks failed"
        return $false
    }
}

function Show-Usage {
    Write-Host @"
Usage: .\health-check.ps1 [OPTIONS]

Parameters:
  -Host       Target host (default: localhost)
  -Port       Target port (default: 8000)
  -Protocol   Protocol to use (default: http)
  -Timeout    Request timeout in seconds (default: 30)

Switches:
  -WaitStartup      Wait for startup completion
  -WaitReady        Wait for readiness
  -Comprehensive    Run all checks
  -Help             Show this help message

Examples:
  .\health-check.ps1                                          # Check localhost:8000
  .\health-check.ps1 -Host "orm-calculator.com" -Port 443 -Protocol "https"  # Check production
  .\health-check.ps1 -WaitStartup                             # Wait for startup
  .\health-check.ps1 -Comprehensive                           # Run all checks
"@
}

# Main execution
if ($Help) {
    Show-Usage
    exit 0
}

Write-Info "ORM Capital Calculator Health Check"
Write-Info "Target: $BaseUrl"
Write-Info "Timeout: ${Timeout}s"
Write-Host ""

$exitCode = 0

if ($WaitStartup) {
    if (-not (Wait-ForStartup)) {
        $exitCode = 1
    }
}
elseif ($WaitReady) {
    if (-not (Wait-ForReadiness)) {
        $exitCode = 1
    }
}
elseif ($Comprehensive) {
    if (-not (Invoke-ComprehensiveCheck)) {
        $exitCode = 1
    }
}
else {
    if (-not (Invoke-ComprehensiveCheck)) {
        $exitCode = 1
    }
}

exit $exitCode