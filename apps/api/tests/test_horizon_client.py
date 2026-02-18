"""
Tests for Horizon API client
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from stellar_sdk.exceptions import NotFoundError, BadRequestError

from app.services.horizon_client import (
    HorizonClient,
    HorizonClientError,
    AccountNotFoundError
)


class TestHorizonClient:
    """Test suite for HorizonClient"""
    
    def test_init(self):
        """Test client initialization"""
        client = HorizonClient()
        assert client.horizon_url is not None
        assert client.server is not None
    
    def test_init_custom_url(self):
        """Test client initialization with custom URL"""
        custom_url = "https://custom-horizon.stellar.org"
        client = HorizonClient(horizon_url=custom_url)
        assert client.horizon_url == custom_url
    
    @patch('app.services.horizon_client.Server')
    def test_fetch_account_success(self, mock_server):
        """Test successful account fetch"""
        # Setup mock
        mock_account_data = {
            "id": "GTEST",
            "sequence": "123",
            "balances": []
        }
        mock_server.return_value.accounts.return_value.account_id.return_value.call.return_value = mock_account_data
        
        client = HorizonClient()
        result = client.fetch_account("GTEST")
        
        assert result == mock_account_data
        assert result["id"] == "GTEST"
    
    @patch('app.services.horizon_client.Server')
    def test_fetch_account_not_found(self, mock_server):
        """Test account not found error"""
        # Setup mock to raise NotFoundError
        mock_server.return_value.accounts.return_value.account_id.return_value.call.side_effect = NotFoundError(
            Mock(status_code=404, text="Not found")
        )
        
        client = HorizonClient()
        
        with pytest.raises(AccountNotFoundError) as exc_info:
            client.fetch_account("GNONEXISTENT")
        
        assert "not found" in str(exc_info.value).lower()
    
    @patch('app.services.horizon_client.Server')
    def test_fetch_account_bad_request(self, mock_server):
        """Test bad request error"""
        # Setup mock to raise BadRequestError
        mock_server.return_value.accounts.return_value.account_id.return_value.call.side_effect = BadRequestError(
            Mock(status_code=400, text="Bad request")
        )
        
        client = HorizonClient()
        
        with pytest.raises(HorizonClientError) as exc_info:
            client.fetch_account("GINVALID")
        
        assert "bad request" in str(exc_info.value).lower()
    
    @patch('app.services.horizon_client.Server')
    def test_fetch_transactions_success(self, mock_server):
        """Test successful transactions fetch"""
        # Setup mock
        mock_response = {
            "_embedded": {
                "records": [
                    {"hash": "tx1", "ledger": 123},
                    {"hash": "tx2", "ledger": 124}
                ]
            }
        }
        mock_server.return_value.transactions.return_value.limit.return_value.order.return_value.call.return_value = mock_response
        
        client = HorizonClient()
        result = client.fetch_transactions(limit=10)
        
        assert "_embedded" in result
        assert len(result["_embedded"]["records"]) == 2
    
    @patch('app.services.horizon_client.Server')
    def test_fetch_transactions_with_cursor(self, mock_server):
        """Test transactions fetch with pagination cursor"""
        mock_response = {"_embedded": {"records": []}}
        mock_builder = Mock()
        mock_builder.cursor.return_value.call.return_value = mock_response
        mock_server.return_value.transactions.return_value.limit.return_value.order.return_value = mock_builder
        
        client = HorizonClient()
        result = client.fetch_transactions(limit=10, cursor="123456")
        
        mock_builder.cursor.assert_called_once_with("123456")
    
    @patch('app.services.horizon_client.Server')
    def test_fetch_transaction_operations_success(self, mock_server):
        """Test successful operations fetch"""
        mock_response = {
            "_embedded": {
                "records": [
                    {"id": "op1", "type": "payment"},
                    {"id": "op2", "type": "create_account"}
                ]
            }
        }
        mock_server.return_value.operations.return_value.for_transaction.return_value.call.return_value = mock_response
        
        client = HorizonClient()
        result = client.fetch_transaction_operations("tx_hash_123")
        
        assert len(result) == 2
        assert result[0]["type"] == "payment"
    
    @patch('app.services.horizon_client.Server')
    def test_fetch_account_transactions_success(self, mock_server):
        """Test successful account transactions fetch"""
        mock_response = {
            "_embedded": {
                "records": [{"hash": "tx1"}]
            }
        }
        mock_server.return_value.transactions.return_value.for_account.return_value.limit.return_value.order.return_value.call.return_value = mock_response
        
        client = HorizonClient()
        result = client.fetch_account_transactions("GTEST", limit=10)
        
        assert "_embedded" in result
        assert len(result["_embedded"]["records"]) == 1
    
    def test_context_manager(self):
        """Test client as context manager"""
        with HorizonClient() as client:
            assert client is not None
        
        # Client should be closed after context
        assert client.http_client.is_closed
    
    @patch('app.services.horizon_client.Server')
    def test_retry_on_connection_error(self, mock_server):
        """Test retry logic on connection errors"""
        # First two calls fail, third succeeds
        mock_server.return_value.accounts.return_value.account_id.return_value.call.side_effect = [
            Exception("Connection error"),
            Exception("Connection error"),
            {"id": "GTEST", "balances": []}
        ]
        
        client = HorizonClient()
        
        # Should succeed after retries
        result = client.fetch_account("GTEST")
        assert result["id"] == "GTEST"
        
        # Should have been called 3 times
        assert mock_server.return_value.accounts.return_value.account_id.return_value.call.call_count == 3
