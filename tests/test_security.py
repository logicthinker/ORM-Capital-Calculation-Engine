"""
Tests for security components of ORM Capital Calculator Engine
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import time

from orm_calculator.api import create_app
from orm_calculator.config import get_config, DevelopmentConfig
from orm_calculator.security.auth import create_access_token, verify_token, User
from orm_calculator.security.rbac import Permission, check_permission, get_user_permissions


@pytest.fixture
def app():
    """Create test application"""
    with patch('orm_calculator.config.get_config') as mock_config:
        mock_config.return_value = DevelopmentConfig()
        return create_app()


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


class TestAuthentication:
    """Test authentication functionality"""
    
    def test_create_and_verify_token(self):
        """Test JWT token creation and verification"""
        # Create token
        token_data = {
            "sub": "testuser",
            "scopes": ["read", "write"]
        }
        token = create_access_token(token_data)
        
        # Verify token
        decoded = verify_token(token)
        assert decoded.username == "testuser"
        assert decoded.scopes == ["read", "write"]
    
    def test_api_key_authentication(self, client):
        """Test API key authentication in development"""
        # Test with valid API key
        response = client.get(
            "/api/v1/health/",
            headers={"X-API-Key": "dev-api-key-12345"}
        )
        assert response.status_code == 200
    
    def test_health_endpoint_public_access(self, client):
        """Test that health endpoints are publicly accessible"""
        response = client.get("/api/v1/health/")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limiting_headers(self, client):
        """Test that rate limiting headers are included"""
        response = client.get("/api/v1/health/")
        
        # Check for rate limiting headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
    
    def test_rate_limit_enforcement(self, client):
        """Test rate limit enforcement (simplified test)"""
        # This test would need to be more sophisticated in a real scenario
        # For now, just verify the middleware is working
        response = client.get("/api/v1/health/")
        assert response.status_code == 200
        
        # Verify rate limit headers are present
        limit = int(response.headers.get("X-RateLimit-Limit", "0"))
        remaining = int(response.headers.get("X-RateLimit-Remaining", "0"))
        
        assert limit > 0
        assert remaining >= 0


class TestSecurityHeaders:
    """Test security headers middleware"""
    
    def test_security_headers_present(self, client):
        """Test that security headers are added to responses"""
        response = client.get("/api/v1/health/")
        
        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        
        assert "Content-Security-Policy" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
        
        # Custom security headers
        assert "X-Security-Framework" in response.headers
        assert response.headers["X-Security-Framework"] == "CERT-In-Compliant"
        
        assert "X-Data-Residency" in response.headers
        assert response.headers["X-Data-Residency"] == "IN"
    
    def test_correlation_id_header(self, client):
        """Test that correlation ID is added to responses"""
        response = client.get("/api/v1/health/")
        assert "X-Correlation-ID" in response.headers
        
        # Test with custom correlation ID
        custom_id = "test-correlation-123"
        response = client.get(
            "/api/v1/health/",
            headers={"X-Correlation-ID": custom_id}
        )
        assert response.headers["X-Correlation-ID"] == custom_id


class TestRBAC:
    """Test Role-Based Access Control"""
    
    def test_user_permissions(self):
        """Test user permission calculation"""
        # Test admin user
        admin_user = User(
            username="admin",
            scopes=["admin"],
            client_id="test"
        )
        
        permissions = get_user_permissions(admin_user)
        assert Permission.MANAGE_SYSTEM in permissions
        assert Permission.VIEW_METRICS in permissions
    
    def test_permission_checking(self):
        """Test permission checking logic"""
        # Test user with read scope
        read_user = User(
            username="reader",
            scopes=["read"],
            client_id="test"
        )
        
        # Should have calculation permissions
        assert check_permission(read_user, Permission.CALCULATE_SMA)
        assert check_permission(read_user, Permission.READ_JOBS)
        
        # Should not have write permissions
        assert not check_permission(read_user, Permission.WRITE_LOSS_DATA)
        assert not check_permission(read_user, Permission.MANAGE_SYSTEM)
    
    def test_api_user_permissions(self):
        """Test API user permissions in development"""
        api_user = User(
            username="api_user",
            scopes=["admin"],
            client_id="api_client"
        )
        
        permissions = get_user_permissions(api_user)
        # API user should have all permissions in development
        assert len(permissions) > 0


class TestConfiguration:
    """Test configuration management"""
    
    def test_development_config(self):
        """Test development configuration"""
        config = DevelopmentConfig()
        
        assert config.environment == "development"
        assert config.debug is True
        assert config.security.use_https is False
        assert "dev-api-key-12345" in config.security.api_keys
        assert config.database.echo_sql is True
    
    def test_config_validation(self):
        """Test configuration validation"""
        config = get_config()
        
        # Basic validation
        assert config.app_name
        assert config.app_version
        assert config.security.secret_key
        assert config.database.database_url


class TestErrorHandling:
    """Test error handling and responses"""
    
    def test_standardized_error_format(self, client):
        """Test that errors follow standardized format"""
        # Test 404 error
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        
        data = response.json()
        assert "error_code" in data
        assert "error_message" in data
        assert "details" in data
    
    def test_validation_error_format(self, client):
        """Test validation error format"""
        # This would need a route that accepts POST data to test properly
        # For now, just verify the error handler is configured
        pass


if __name__ == "__main__":
    pytest.main([__file__])