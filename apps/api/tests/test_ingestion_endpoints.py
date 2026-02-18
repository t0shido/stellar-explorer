"""
Tests for ingestion API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app
from app.db.database import get_db
from app.services.horizon_client import AccountNotFoundError, HorizonClientError


@pytest.fixture
def client(db_session):
    """Create test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestIngestionEndpoints:
    """Test suite for ingestion API endpoints"""
    
    @patch('app.services.ingestion_service.HorizonClient')
    def test_ingest_account_success(self, mock_horizon_client, client, sample_account_data):
        """Test successful account ingestion"""
        # Setup mock
        mock_client_instance = Mock()
        mock_client_instance.fetch_account.return_value = sample_account_data
        mock_horizon_client.return_value = mock_client_instance
        
        response = client.post(
            f"/api/v1/ingest/account/{sample_account_data['account_id']}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "account" in data
        assert data["account"]["address"] == sample_account_data["account_id"]
        assert "balances_created" in data
        assert "assets_created" in data
    
    @patch('app.services.ingestion_service.HorizonClient')
    def test_ingest_account_not_found(self, mock_horizon_client, client):
        """Test account not found error"""
        # Setup mock to raise AccountNotFoundError
        mock_client_instance = Mock()
        mock_client_instance.fetch_account.side_effect = AccountNotFoundError("Not found")
        mock_horizon_client.return_value = mock_client_instance
        
        response = client.post("/api/v1/ingest/account/GNONEXISTENT")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    @patch('app.services.ingestion_service.HorizonClient')
    def test_ingest_account_horizon_error(self, mock_horizon_client, client):
        """Test Horizon API error"""
        # Setup mock to raise HorizonClientError
        mock_client_instance = Mock()
        mock_client_instance.fetch_account.side_effect = HorizonClientError("API error")
        mock_horizon_client.return_value = mock_client_instance
        
        response = client.post("/api/v1/ingest/account/GTEST")
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
    
    @patch('app.services.ingestion_service.HorizonClient')
    def test_ingest_latest_transactions_success(
        self,
        mock_horizon_client,
        client,
        sample_transaction_data,
        sample_operation_data
    ):
        """Test successful transaction ingestion"""
        # Setup mock
        mock_client_instance = Mock()
        mock_client_instance.fetch_transactions.return_value = {
            "_embedded": {"records": [sample_transaction_data]}
        }
        mock_client_instance.fetch_transaction_operations.return_value = [sample_operation_data]
        mock_horizon_client.return_value = mock_client_instance
        
        response = client.post("/api/v1/ingest/transactions/latest?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "transactions_created" in data
        assert "operations_created" in data
        assert data["limit"] == 10
    
    def test_ingest_latest_transactions_invalid_limit(self, client):
        """Test invalid limit parameter"""
        response = client.post("/api/v1/ingest/transactions/latest?limit=300")
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
    
    @patch('app.services.ingestion_service.HorizonClient')
    def test_refresh_watchlist_success(
        self,
        mock_horizon_client,
        client,
        sample_watchlist,
        sample_account_data
    ):
        """Test successful watchlist refresh"""
        # Setup mock
        mock_client_instance = Mock()
        mock_client_instance.fetch_account.return_value = sample_account_data
        mock_client_instance.fetch_account_transactions.return_value = {
            "_embedded": {"records": []}
        }
        mock_horizon_client.return_value = mock_client_instance
        
        response = client.post("/api/v1/ingest/watchlist/refresh")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_accounts" in data
        assert "successful" in data
    
    @patch('app.services.ingestion_service.HorizonClient')
    def test_refresh_watchlist_async(self, mock_horizon_client, client):
        """Test async watchlist refresh"""
        # Setup mock
        mock_client_instance = Mock()
        mock_horizon_client.return_value = mock_client_instance
        
        response = client.post("/api/v1/ingest/watchlist/refresh-async")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        assert "queued" in data["message"].lower()
