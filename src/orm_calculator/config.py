"""
Configuration management for ORM Capital Calculator Engine

Provides environment-based configuration using Pydantic Settings with support for
OAuth 2.0 authentication, HTTPS/TLS, rate limiting, and security controls.
"""

import os
from typing import Optional, List, Literal, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from pydantic.networks import AnyHttpUrl
import secrets


class SecurityConfig(BaseSettings):
    """Security configuration settings"""
    
    # JWT/OAuth 2.0 settings
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # OAuth 2.0 client credentials
    oauth2_token_url: Optional[str] = None
    oauth2_client_id: Optional[str] = None
    oauth2_client_secret: Optional[str] = None
    oauth2_scopes: List[str] = ["read", "write", "admin"]
    
    # API Key fallback for development
    api_key_header: str = "X-API-Key"
    api_keys: List[str] = []
    
    # TLS/HTTPS settings
    use_https: bool = False
    ssl_cert_file: Optional[str] = None
    ssl_key_file: Optional[str] = None
    ssl_ca_file: Optional[str] = None
    
    # Security headers
    enable_security_headers: bool = True
    hsts_max_age: int = 31536000  # 1 year
    
    # CORS settings
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: List[str] = ["*"]
    
    # Trusted hosts
    trusted_hosts: List[str] = ["*"]
    
    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = False


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration"""
    
    # General rate limits (requests per minute)
    default_rate_limit: int = 100
    calculation_rate_limit: int = 50
    health_rate_limit: int = 1000
    
    # Rate limiting storage
    rate_limit_storage: Literal["memory", "redis"] = "memory"
    redis_url: Optional[str] = None
    
    # Rate limit headers
    include_headers: bool = True
    
    class Config:
        env_prefix = "RATE_LIMIT_"
        case_sensitive = False


class DatabaseConfig(BaseSettings):
    """Database configuration settings"""
    
    # Database URL (supports SQLite, PostgreSQL, MySQL, etc.)
    database_url: str = "sqlite:///./data/orm_calculator.db"
    
    # Connection pool settings
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    # SQLAlchemy settings
    echo_sql: bool = False
    
    class Config:
        env_prefix = "DATABASE_"
        case_sensitive = False


class LoggingConfig(BaseSettings):
    """Logging configuration settings"""
    
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Security event logging
    security_log_file: Optional[str] = None
    audit_log_file: Optional[str] = None
    
    # SOC integration
    soc_endpoint: Optional[str] = None
    soc_api_key: Optional[str] = None
    
    class Config:
        env_prefix = "LOG_"
        case_sensitive = False


class PerformanceConfig(BaseSettings):
    """Performance and scaling configuration"""
    
    # Async execution thresholds
    async_threshold_seconds: int = 60
    max_concurrent_jobs: int = 50
    
    # Caching
    cache_ttl_seconds: int = 3600
    enable_caching: bool = True
    
    # Request timeouts
    request_timeout_seconds: int = 300
    
    class Config:
        env_prefix = "PERFORMANCE_"
        case_sensitive = False


class ComplianceConfig(BaseSettings):
    """Compliance and regulatory configuration"""
    
    # Data residency
    data_residency_region: str = "IN"  # India
    enforce_data_residency: bool = True
    
    # Audit retention
    audit_retention_days: int = 180
    
    # Time synchronization
    ntp_servers: List[str] = ["time.nic.in", "time.npl.co.uk"]
    
    # CERT-In compliance
    cert_in_compliance: bool = True
    incident_reporting_endpoint: Optional[str] = None
    
    class Config:
        env_prefix = "COMPLIANCE_"
        case_sensitive = False


class ApplicationConfig(BaseSettings):
    """Main application configuration"""
    
    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    
    # Application metadata
    app_name: str = "ORM Capital Calculator Engine"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    
    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1
    
    # Component configurations
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig)
    
    @field_validator("debug")
    @classmethod
    def debug_must_be_false_in_production(cls, v, info):
        """Ensure debug is False in production"""
        if info.data.get("environment") == "production" and v:
            raise ValueError("Debug must be False in production environment")
        return v
    
    @field_validator("security")
    @classmethod
    def validate_security_config(cls, v, info):
        """Validate security configuration based on environment"""
        environment = info.data.get("environment", "development")
        
        if environment == "production":
            # Production security requirements
            if not v.use_https:
                raise ValueError("HTTPS must be enabled in production")
            if v.cors_origins == ["*"]:
                raise ValueError("CORS origins must be restricted in production")
            if v.trusted_hosts == ["*"]:
                raise ValueError("Trusted hosts must be restricted in production")
            if not v.oauth2_token_url:
                raise ValueError("OAuth 2.0 token URL must be configured in production")
        
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Allow nested environment variables
        env_nested_delimiter = "__"


# Global configuration instance
config = ApplicationConfig()


def get_config() -> ApplicationConfig:
    """Get the global configuration instance"""
    return config


def reload_config() -> ApplicationConfig:
    """Reload configuration from environment"""
    global config
    config = ApplicationConfig()
    return config


# Environment-specific configurations
class DevelopmentConfig(ApplicationConfig):
    """Development environment configuration"""
    
    environment: Literal["development"] = "development"
    debug: bool = True
    
    # Relaxed security for development
    security: SecurityConfig = SecurityConfig(
        use_https=False,
        cors_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        trusted_hosts=["localhost", "127.0.0.1"],
        api_keys=["dev-api-key-12345"]
    )
    
    # Lower rate limits for development
    rate_limit: RateLimitConfig = RateLimitConfig(
        default_rate_limit=1000,
        calculation_rate_limit=100
    )
    
    # SQLite for development
    database: DatabaseConfig = DatabaseConfig(
        database_url="sqlite:///./data/orm_calculator.db",
        echo_sql=True
    )
    
    # Verbose logging for development
    logging: LoggingConfig = LoggingConfig(
        log_level="DEBUG"
    )


class ProductionConfig(ApplicationConfig):
    """Production environment configuration"""
    
    environment: Literal["production"] = "production"
    debug: bool = False
    
    # Strict security for production
    security: SecurityConfig = SecurityConfig(
        use_https=True,
        enable_security_headers=True,
        cors_origins=[],  # Must be set via environment
        trusted_hosts=[],  # Must be set via environment
        oauth2_token_url="",  # Must be set via environment
        oauth2_client_id="",  # Must be set via environment
        oauth2_client_secret=""  # Must be set via environment
    )
    
    # Production rate limits
    rate_limit: RateLimitConfig = RateLimitConfig(
        default_rate_limit=100,
        calculation_rate_limit=50,
        rate_limit_storage="redis"
    )
    
    # Production database (PostgreSQL recommended)
    database: DatabaseConfig = DatabaseConfig(
        database_url="",  # Must be set via environment
        echo_sql=False,
        pool_size=20,
        max_overflow=30
    )
    
    # Production logging
    logging: LoggingConfig = LoggingConfig(
        log_level="INFO",
        security_log_file="/var/log/orm-calculator/security.log",
        audit_log_file="/var/log/orm-calculator/audit.log"
    )
    
    # Production performance settings
    performance: PerformanceConfig = PerformanceConfig(
        max_concurrent_jobs=50,
        enable_caching=True
    )
    
    # Compliance settings
    compliance: ComplianceConfig = ComplianceConfig(
        enforce_data_residency=True,
        cert_in_compliance=True
    )


def get_environment_config(environment: str) -> ApplicationConfig:
    """Get configuration for specific environment"""
    if environment == "development":
        return DevelopmentConfig()
    elif environment == "production":
        return ProductionConfig()
    else:
        return ApplicationConfig(environment=environment)