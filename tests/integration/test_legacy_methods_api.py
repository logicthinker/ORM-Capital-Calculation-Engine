"""
Integration tests for BIA and TSA API endpoints

Tests the complete API flow for legacy calculation methods.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import date

from src.orm_calculator.main import app


class TestLegacyMethodsAPI:
    """Integration tests for BIA and TSA API endpoints"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
    
    def test_bia_calculation_api(self):
        """Test BIA calculation through API"""
        request_data = {
            "model_name": "bia",
            "execution_mode": "sync",
            "entity_id": "TEST_BANK_001",
            "calculation_date": "2024-03-31",
            "parameters": {
                "alpha_coefficient": 0.15,
                "rwa_multiplier": 12.5
            }
        }
        
        response = self.client.post("/api/v1/calculation-jobs", json=request_data)
        
        # Should return 200 for sync execution
        assert response.status_code == 200
        
        result = response.json()
        assert result["methodology"] == "bia"
        assert result["entity_id"] == "TEST_BANK_001"
        assert "operational_risk_capital" in result
        assert "risk_weighted_assets" in result
        assert result["operational_risk_capital"] > 0
        assert result["risk_weighted_assets"] > 0
        
        # BIA specific fields
        assert result["bucket"] == 1  # BIA is conceptually similar to Bucket 1
        assert result["ilm_gated"] == False  # BIA doesn't have ILM gating
    
    def test_tsa_calculation_api(self):
        """Test TSA calculation through API"""
        request_data = {
            "model_name": "tsa",
            "execution_mode": "sync",
            "entity_id": "TEST_BANK_001",
            "calculation_date": "2024-03-31",
            "parameters": {
                "beta_factors": {
                    "retail_banking": 0.12,
                    "commercial_banking": 0.15,
                    "trading_sales": 0.18
                },
                "rwa_multiplier": 12.5
            }
        }
        
        response = self.client.post("/api/v1/calculation-jobs", json=request_data)
        
        # Should return 200 for sync execution
        assert response.status_code == 200
        
        result = response.json()
        assert result["methodology"] == "tsa"
        assert result["entity_id"] == "TEST_BANK_001"
        assert "operational_risk_capital" in result
        assert "risk_weighted_assets" in result
        assert result["operational_risk_capital"] > 0
        assert result["risk_weighted_assets"] > 0
        
        # TSA specific fields
        assert result["bucket"] == 2  # TSA is conceptually similar to Bucket 2
        assert result["ilm_gated"] == False  # TSA doesn't have ILM gating
        assert result["internal_loss_multiplier"] == 1.0  # TSA doesn't use ILM
    
    def test_async_bia_calculation(self):
        """Test async BIA calculation"""
        request_data = {
            "model_name": "bia",
            "execution_mode": "async",
            "entity_id": "TEST_BANK_001",
            "calculation_date": "2024-03-31"
        }
        
        response = self.client.post("/api/v1/calculation-jobs", json=request_data)
        
        # Should return 202 for async execution
        assert response.status_code == 202
        
        result = response.json()
        assert "job_id" in result
        assert "run_id" in result
        assert result["status"] == "queued"
    
    def test_async_tsa_calculation(self):
        """Test async TSA calculation"""
        request_data = {
            "model_name": "tsa",
            "execution_mode": "async",
            "entity_id": "TEST_BANK_001",
            "calculation_date": "2024-03-31"
        }
        
        response = self.client.post("/api/v1/calculation-jobs", json=request_data)
        
        # Should return 202 for async execution
        assert response.status_code == 202
        
        result = response.json()
        assert "job_id" in result
        assert "run_id" in result
        assert result["status"] == "queued"
    
    def test_invalid_model_name(self):
        """Test invalid model name returns error"""
        request_data = {
            "model_name": "invalid_method",
            "execution_mode": "sync",
            "entity_id": "TEST_BANK_001",
            "calculation_date": "2024-03-31"
        }
        
        response = self.client.post("/api/v1/calculation-jobs", json=request_data)
        
        # Should return 422 for validation error
        assert response.status_code == 422
    
    def test_bia_parameter_validation(self):
        """Test BIA with custom parameters"""
        request_data = {
            "model_name": "bia",
            "execution_mode": "sync",
            "entity_id": "TEST_BANK_001",
            "calculation_date": "2024-03-31",
            "parameters": {
                "alpha_coefficient": 0.18,  # Custom alpha
                "lookback_years": 5         # Custom lookback
            }
        }
        
        response = self.client.post("/api/v1/calculation-jobs", json=request_data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["methodology"] == "bia"
    
    def test_tsa_parameter_validation(self):
        """Test TSA with custom parameters"""
        request_data = {
            "model_name": "tsa",
            "execution_mode": "sync",
            "entity_id": "TEST_BANK_001",
            "calculation_date": "2024-03-31",
            "parameters": {
                "beta_factors": {
                    "retail_banking": 0.10,
                    "commercial_banking": 0.13
                },
                "floor_annual_at_zero": False
            }
        }
        
        response = self.client.post("/api/v1/calculation-jobs", json=request_data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["methodology"] == "tsa"
    
    def test_multiple_methods_comparison(self):
        """Test that different methods return different results"""
        base_request = {
            "execution_mode": "sync",
            "entity_id": "TEST_BANK_001",
            "calculation_date": "2024-03-31"
        }
        
        # Test SMA
        sma_request = {**base_request, "model_name": "sma"}
        sma_response = self.client.post("/api/v1/calculation-jobs", json=sma_request)
        assert sma_response.status_code == 200
        sma_result = sma_response.json()
        
        # Test BIA
        bia_request = {**base_request, "model_name": "bia"}
        bia_response = self.client.post("/api/v1/calculation-jobs", json=bia_request)
        assert bia_response.status_code == 200
        bia_result = bia_response.json()
        
        # Test TSA
        tsa_request = {**base_request, "model_name": "tsa"}
        tsa_response = self.client.post("/api/v1/calculation-jobs", json=tsa_request)
        assert tsa_response.status_code == 200
        tsa_result = tsa_response.json()
        
        # Results should be different
        assert sma_result["methodology"] == "sma"
        assert bia_result["methodology"] == "bia"
        assert tsa_result["methodology"] == "tsa"
        
        # All should have positive capital
        assert sma_result["operational_risk_capital"] > 0
        assert bia_result["operational_risk_capital"] > 0
        assert tsa_result["operational_risk_capital"] > 0
        
        # Methods should produce different results
        assert sma_result["operational_risk_capital"] != bia_result["operational_risk_capital"]
        assert bia_result["operational_risk_capital"] != tsa_result["operational_risk_capital"]
    
    def test_lineage_tracking_bia(self):
        """Test that BIA calculations create proper lineage records"""
        request_data = {
            "model_name": "bia",
            "execution_mode": "sync",
            "entity_id": "TEST_BANK_001",
            "calculation_date": "2024-03-31"
        }
        
        response = self.client.post("/api/v1/calculation-jobs", json=request_data)
        assert response.status_code == 200
        
        result = response.json()
        run_id = result["run_id"]
        
        # Check lineage endpoint
        lineage_response = self.client.get(f"/api/v1/lineage/{run_id}")
        assert lineage_response.status_code == 200
        
        lineage = lineage_response.json()
        assert lineage["run_id"] == run_id
        assert "final_outputs" in lineage
        assert "intermediates" in lineage
    
    def test_lineage_tracking_tsa(self):
        """Test that TSA calculations create proper lineage records"""
        request_data = {
            "model_name": "tsa",
            "execution_mode": "sync",
            "entity_id": "TEST_BANK_001",
            "calculation_date": "2024-03-31"
        }
        
        response = self.client.post("/api/v1/calculation-jobs", json=request_data)
        assert response.status_code == 200
        
        result = response.json()
        run_id = result["run_id"]
        
        # Check lineage endpoint
        lineage_response = self.client.get(f"/api/v1/lineage/{run_id}")
        assert lineage_response.status_code == 200
        
        lineage = lineage_response.json()
        assert lineage["run_id"] == run_id
        assert "final_outputs" in lineage
        assert "intermediates" in lineage