"""
Tests for ingestion service
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime

from app.services.ingestion_service import IngestionService
from app.services.horizon_client import AccountNotFoundError
from app.db.models import Account, Asset, AccountBalance, Transaction, Operation, CounterpartyEdge


class TestIngestionService:
    """Test suite for IngestionService"""
    
    def test_init(self, db_session):
        """Test service initialization"""
        service = IngestionService(db_session)
        assert service.db == db_session
        assert service.horizon_client is not None
    
    def test_init_with_custom_client(self, db_session):
        """Test service initialization with custom client"""
        mock_client = Mock()
        service = IngestionService(db_session, horizon_client=mock_client)
        assert service.horizon_client == mock_client
    
    def test_ingest_account_new(self, db_session, sample_account_data):
        """Test ingesting a new account"""
        mock_client = Mock()
        mock_client.fetch_account.return_value = sample_account_data
        
        service = IngestionService(db_session, horizon_client=mock_client)
        account, balances_created, assets_created = service.ingest_account(
            sample_account_data["account_id"]
        )
        
        # Verify account was created
        assert account is not None
        assert account.address == sample_account_data["account_id"]
        assert account.first_seen is not None
        
        # Verify balances were created
        assert balances_created == 2  # USD + XLM
        
        # Verify assets were created
        assert assets_created == 1  # USD (native doesn't create asset)
        
        # Verify database state
        db_accounts = db_session.query(Account).all()
        assert len(db_accounts) == 1
        
        db_assets = db_session.query(Asset).all()
        assert len(db_assets) == 1
        assert db_assets[0].asset_code == "USD"
        
        db_balances = db_session.query(AccountBalance).all()
        assert len(db_balances) == 2
    
    def test_ingest_account_existing(self, db_session, sample_account_data):
        """Test ingesting an existing account (idempotency)"""
        # Create existing account
        existing_account = Account(
            address=sample_account_data["account_id"],
            risk_score=50.0,
            metadata={"existing": True}
        )
        db_session.add(existing_account)
        db_session.commit()
        
        mock_client = Mock()
        mock_client.fetch_account.return_value = sample_account_data
        
        service = IngestionService(db_session, horizon_client=mock_client)
        account, balances_created, assets_created = service.ingest_account(
            sample_account_data["account_id"]
        )
        
        # Verify account was updated, not duplicated
        assert account.id == existing_account.id
        assert account.risk_score == 50.0  # Preserved
        assert account.last_seen is not None
        
        # Should still be only one account
        db_accounts = db_session.query(Account).all()
        assert len(db_accounts) == 1
    
    def test_ingest_account_not_found(self, db_session):
        """Test ingesting non-existent account"""
        mock_client = Mock()
        mock_client.fetch_account.side_effect = AccountNotFoundError("Not found")
        
        service = IngestionService(db_session, horizon_client=mock_client)
        
        with pytest.raises(AccountNotFoundError):
            service.ingest_account("GNONEXISTENT")
    
    def test_ingest_latest_transactions(self, db_session, sample_transaction_data, sample_operation_data):
        """Test ingesting latest transactions"""
        mock_client = Mock()
        mock_client.fetch_transactions.return_value = {
            "_embedded": {
                "records": [sample_transaction_data]
            }
        }
        mock_client.fetch_transaction_operations.return_value = [sample_operation_data]
        
        service = IngestionService(db_session, horizon_client=mock_client)
        transactions_created, operations_created = service.ingest_latest_transactions(limit=10)
        
        # Verify counts
        assert transactions_created == 1
        assert operations_created == 1
        
        # Verify database state
        db_transactions = db_session.query(Transaction).all()
        assert len(db_transactions) == 1
        assert db_transactions[0].tx_hash == sample_transaction_data["hash"]
        
        db_operations = db_session.query(Operation).all()
        assert len(db_operations) == 1
        assert db_operations[0].type == "payment"
    
    def test_ingest_transactions_idempotency(self, db_session, sample_transaction_data, sample_operation_data):
        """Test transaction ingestion idempotency"""
        # Create existing transaction
        existing_account = Account(
            address=sample_transaction_data["source_account"],
            risk_score=0.0,
            metadata={}
        )
        db_session.add(existing_account)
        db_session.flush()
        
        existing_tx = Transaction(
            tx_hash=sample_transaction_data["hash"],
            ledger=sample_transaction_data["ledger"],
            source_account_id=existing_account.id,
            fee_charged=100,
            operation_count=1,
            successful=True
        )
        db_session.add(existing_tx)
        db_session.commit()
        
        mock_client = Mock()
        mock_client.fetch_transactions.return_value = {
            "_embedded": {
                "records": [sample_transaction_data]
            }
        }
        
        service = IngestionService(db_session, horizon_client=mock_client)
        transactions_created, operations_created = service.ingest_latest_transactions(limit=10)
        
        # Should skip existing transaction
        assert transactions_created == 0
        assert operations_created == 0
        
        # Should still be only one transaction
        db_transactions = db_session.query(Transaction).all()
        assert len(db_transactions) == 1
    
    def test_ingest_watchlist_accounts(self, db_session, sample_watchlist, sample_account_data):
        """Test ingesting watchlist accounts"""
        watchlist, accounts = sample_watchlist
        
        mock_client = Mock()
        mock_client.fetch_account.return_value = sample_account_data
        mock_client.fetch_account_transactions.return_value = {
            "_embedded": {"records": []}
        }
        
        service = IngestionService(db_session, horizon_client=mock_client)
        summary = service.ingest_watchlist_accounts()
        
        # Verify summary
        assert summary["total_accounts"] == 3
        assert summary["successful"] == 3
        assert summary["failed"] == 0
        
        # Verify accounts were updated
        for account in accounts:
            db_session.refresh(account)
            assert account.last_seen is not None
    
    def test_upsert_asset_native(self, db_session):
        """Test upserting native XLM (should return None)"""
        service = IngestionService(db_session)
        
        balance_data = {
            "asset_type": "native",
            "balance": "100.0"
        }
        
        asset, is_new = service._upsert_asset(balance_data)
        
        assert asset is None
        assert is_new is False
        
        # No assets should be created
        db_assets = db_session.query(Asset).all()
        assert len(db_assets) == 0
    
    def test_upsert_asset_new(self, db_session):
        """Test upserting a new asset"""
        service = IngestionService(db_session)
        
        balance_data = {
            "asset_type": "credit_alphanum4",
            "asset_code": "USD",
            "asset_issuer": "GISSUER"
        }
        
        asset, is_new = service._upsert_asset(balance_data)
        
        assert asset is not None
        assert is_new is True
        assert asset.asset_code == "USD"
        assert asset.asset_issuer == "GISSUER"
        
        # Verify database state
        db_assets = db_session.query(Asset).all()
        assert len(db_assets) == 1
    
    def test_upsert_asset_existing(self, db_session):
        """Test upserting an existing asset (idempotency)"""
        # Create existing asset
        existing_asset = Asset(
            asset_code="USD",
            asset_issuer="GISSUER",
            asset_type="credit_alphanum4",
            metadata={}
        )
        db_session.add(existing_asset)
        db_session.commit()
        
        service = IngestionService(db_session)
        
        balance_data = {
            "asset_type": "credit_alphanum4",
            "asset_code": "USD",
            "asset_issuer": "GISSUER"
        }
        
        asset, is_new = service._upsert_asset(balance_data)
        
        assert asset is not None
        assert is_new is False
        assert asset.id == existing_asset.id
        
        # Should still be only one asset
        db_assets = db_session.query(Asset).all()
        assert len(db_assets) == 1
    
    def test_update_counterparty_edge_new(self, db_session):
        """Test creating new counterparty edge"""
        # Create accounts
        account1 = Account(address="GFROM", risk_score=0.0, metadata={})
        account2 = Account(address="GTO", risk_score=0.0, metadata={})
        db_session.add_all([account1, account2])
        db_session.flush()
        
        service = IngestionService(db_session)
        service._update_counterparty_edge(
            account1.id,
            account2.id,
            None,
            Decimal("100.0")
        )
        db_session.commit()
        
        # Verify edge was created
        edges = db_session.query(CounterpartyEdge).all()
        assert len(edges) == 1
        assert edges[0].from_account_id == account1.id
        assert edges[0].to_account_id == account2.id
        assert edges[0].tx_count == 1
        assert edges[0].total_amount == Decimal("100.0")
    
    def test_update_counterparty_edge_existing(self, db_session):
        """Test updating existing counterparty edge"""
        # Create accounts and edge
        account1 = Account(address="GFROM", risk_score=0.0, metadata={})
        account2 = Account(address="GTO", risk_score=0.0, metadata={})
        db_session.add_all([account1, account2])
        db_session.flush()
        
        edge = CounterpartyEdge(
            from_account_id=account1.id,
            to_account_id=account2.id,
            asset_id=None,
            tx_count=1,
            total_amount=Decimal("100.0")
        )
        db_session.add(edge)
        db_session.commit()
        
        service = IngestionService(db_session)
        service._update_counterparty_edge(
            account1.id,
            account2.id,
            None,
            Decimal("50.0")
        )
        db_session.commit()
        
        # Verify edge was updated
        db_session.refresh(edge)
        assert edge.tx_count == 2
        assert edge.total_amount == Decimal("150.0")
        
        # Should still be only one edge
        edges = db_session.query(CounterpartyEdge).all()
        assert len(edges) == 1
    
    def test_context_manager(self, db_session):
        """Test service as context manager"""
        with IngestionService(db_session) as service:
            assert service is not None
    
    def test_rollback_on_error(self, db_session):
        """Test database rollback on error"""
        mock_client = Mock()
        mock_client.fetch_account.side_effect = Exception("API error")
        
        service = IngestionService(db_session, horizon_client=mock_client)
        
        with pytest.raises(Exception):
            service.ingest_account("GTEST")
        
        # Database should be rolled back
        db_accounts = db_session.query(Account).all()
        assert len(db_accounts) == 0
