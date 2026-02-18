"""
Stellar data ingestion service with idempotent operations
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.models import (
    Account, Asset, AccountBalance, Transaction, Operation,
    CounterpartyEdge, WatchlistMember
)
from app.services.horizon_client import HorizonClient, AccountNotFoundError, HorizonClientError

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Service for ingesting Stellar data from Horizon API into database
    Ensures idempotency and data consistency
    """
    
    def __init__(self, db: Session, horizon_client: Optional[HorizonClient] = None):
        """
        Initialize ingestion service
        
        Args:
            db: Database session
            horizon_client: Horizon API client (creates new if None)
        """
        self.db = db
        self.horizon_client = horizon_client or HorizonClient()
        self._owns_client = horizon_client is None
    
    def ingest_account(self, address: str) -> Tuple[Account, int, int]:
        """
        Fetch and store account data including balances and trustlines
        
        Args:
            address: Stellar account address
            
        Returns:
            Tuple of (Account, balances_created, assets_created)
            
        Raises:
            AccountNotFoundError: If account doesn't exist
            HorizonClientError: For API errors
        """
        logger.info(f"Starting account ingestion", extra={"address": address})
        
        try:
            # Fetch account data from Horizon
            account_data = self.horizon_client.fetch_account(address)
            
            # Upsert account
            account = self._upsert_account(address, account_data)
            
            # Process balances and trustlines
            balances_created = 0
            assets_created = 0
            
            for balance_data in account_data.get('balances', []):
                asset, is_new_asset = self._upsert_asset(balance_data)
                if is_new_asset:
                    assets_created += 1
                
                balance_created = self._upsert_account_balance(account, asset, balance_data)
                if balance_created:
                    balances_created += 1
            
            self.db.commit()
            
            logger.info(
                "Account ingestion completed",
                extra={
                    "address": address,
                    "balances_created": balances_created,
                    "assets_created": assets_created
                }
            )
            
            return account, balances_created, assets_created
            
        except Exception as e:
            self.db.rollback()
            logger.error(
                "Account ingestion failed",
                extra={"address": address, "error": str(e)}
            )
            raise
    
    def ingest_latest_transactions(self, limit: int = 100) -> Tuple[int, int]:
        """
        Fetch and store latest transactions with operations
        
        Args:
            limit: Number of transactions to fetch (max 200)
            
        Returns:
            Tuple of (transactions_created, operations_created)
            
        Raises:
            HorizonClientError: For API errors
        """
        logger.info(f"Starting transaction ingestion", extra={"limit": limit})
        
        try:
            # Fetch transactions from Horizon
            response = self.horizon_client.fetch_transactions(limit=limit)
            transactions = response.get('_embedded', {}).get('records', [])
            
            transactions_created = 0
            operations_created = 0
            
            for tx_data in transactions:
                # Check if transaction already exists
                tx_hash = tx_data.get('hash')
                existing_tx = self.db.query(Transaction).filter(
                    Transaction.tx_hash == tx_hash
                ).first()
                
                if existing_tx:
                    logger.debug(f"Transaction already exists", extra={"tx_hash": tx_hash})
                    continue
                
                # Ingest transaction and operations
                tx_created, ops_created = self._ingest_transaction(tx_data)
                if tx_created:
                    transactions_created += 1
                operations_created += ops_created
            
            self.db.commit()
            
            logger.info(
                "Transaction ingestion completed",
                extra={
                    "transactions_created": transactions_created,
                    "operations_created": operations_created,
                    "limit": limit
                }
            )
            
            return transactions_created, operations_created
            
        except Exception as e:
            self.db.rollback()
            logger.error(
                "Transaction ingestion failed",
                extra={"limit": limit, "error": str(e)}
            )
            raise
    
    def ingest_watchlist_accounts(self) -> Dict[str, Any]:
        """
        Refresh data for all accounts in watchlists
        
        Returns:
            Summary dictionary with counts
        """
        logger.info("Starting watchlist account ingestion")
        
        try:
            # Get all unique accounts in watchlists
            watchlist_accounts = self.db.query(Account).join(
                WatchlistMember,
                Account.id == WatchlistMember.account_id
            ).distinct().all()
            
            total_accounts = len(watchlist_accounts)
            successful = 0
            failed = 0
            total_balances = 0
            total_transactions = 0
            
            for account in watchlist_accounts:
                try:
                    # Refresh account data
                    _, balances_created, _ = self.ingest_account(account.address)
                    total_balances += balances_created
                    
                    # Fetch recent transactions
                    tx_response = self.horizon_client.fetch_account_transactions(
                        account.address,
                        limit=10
                    )
                    
                    for tx_data in tx_response.get('_embedded', {}).get('records', []):
                        tx_created, _ = self._ingest_transaction(tx_data)
                        if tx_created:
                            total_transactions += 1
                    
                    # Update last_seen
                    account.last_seen = datetime.utcnow()
                    successful += 1
                    
                except Exception as e:
                    logger.error(
                        "Failed to ingest watchlist account",
                        extra={"address": account.address, "error": str(e)}
                    )
                    failed += 1
            
            self.db.commit()
            
            summary = {
                "total_accounts": total_accounts,
                "successful": successful,
                "failed": failed,
                "balances_updated": total_balances,
                "transactions_ingested": total_transactions
            }
            
            logger.info(
                "Watchlist account ingestion completed",
                extra=summary
            )
            
            return summary
            
        except Exception as e:
            self.db.rollback()
            logger.error(
                "Watchlist ingestion failed",
                extra={"error": str(e)}
            )
            raise
    
    def _upsert_account(self, address: str, account_data: Dict[str, Any]) -> Account:
        """
        Upsert account record (idempotent)
        
        Args:
            address: Account address
            account_data: Raw account data from Horizon
            
        Returns:
            Account instance
        """
        # Check if account exists
        account = self.db.query(Account).filter(Account.address == address).first()
        
        if account:
            # Update existing account
            account.last_seen = datetime.utcnow()
            account.metadata = {
                **account.metadata,
                "sequence": account_data.get('sequence'),
                "subentry_count": account_data.get('subentry_count'),
                "num_sponsoring": account_data.get('num_sponsoring', 0),
                "num_sponsored": account_data.get('num_sponsored', 0),
                "last_modified_ledger": account_data.get('last_modified_ledger'),
                "raw_data_snippet": {
                    "id": account_data.get('id'),
                    "paging_token": account_data.get('paging_token'),
                    "flags": account_data.get('flags', {})
                }
            }
            logger.debug(f"Updated existing account", extra={"address": address})
        else:
            # Create new account
            account = Account(
                address=address,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                risk_score=0.0,
                metadata={
                    "sequence": account_data.get('sequence'),
                    "subentry_count": account_data.get('subentry_count'),
                    "num_sponsoring": account_data.get('num_sponsoring', 0),
                    "num_sponsored": account_data.get('num_sponsored', 0),
                    "last_modified_ledger": account_data.get('last_modified_ledger'),
                    "raw_data_snippet": {
                        "id": account_data.get('id'),
                        "paging_token": account_data.get('paging_token'),
                        "flags": account_data.get('flags', {})
                    }
                }
            )
            self.db.add(account)
            self.db.flush()  # Get ID
            logger.debug(f"Created new account", extra={"address": address, "id": account.id})
        
        return account
    
    def _upsert_asset(self, balance_data: Dict[str, Any]) -> Tuple[Optional[Asset], bool]:
        """
        Upsert asset record (idempotent)
        
        Args:
            balance_data: Balance data containing asset info
            
        Returns:
            Tuple of (Asset or None for native, is_new)
        """
        asset_type = balance_data.get('asset_type')
        
        # Native XLM doesn't need an asset record
        if asset_type == 'native':
            return None, False
        
        asset_code = balance_data.get('asset_code')
        asset_issuer = balance_data.get('asset_issuer')
        
        # Check if asset exists
        asset = self.db.query(Asset).filter(
            Asset.asset_code == asset_code,
            Asset.asset_issuer == asset_issuer
        ).first()
        
        if asset:
            return asset, False
        
        # Create new asset
        asset = Asset(
            asset_code=asset_code,
            asset_issuer=asset_issuer,
            asset_type=asset_type,
            metadata={
                "raw_data_snippet": {
                    "asset_code": asset_code,
                    "asset_issuer": asset_issuer,
                    "asset_type": asset_type
                }
            }
        )
        self.db.add(asset)
        self.db.flush()  # Get ID
        
        logger.debug(
            f"Created new asset",
            extra={"asset_code": asset_code, "issuer": asset_issuer}
        )
        
        return asset, True
    
    def _upsert_account_balance(
        self,
        account: Account,
        asset: Optional[Asset],
        balance_data: Dict[str, Any]
    ) -> bool:
        """
        Create new balance snapshot (always creates new record for history)
        
        Args:
            account: Account instance
            asset: Asset instance (None for native XLM)
            balance_data: Balance data from Horizon
            
        Returns:
            True if created, False if skipped
        """
        balance_value = Decimal(balance_data.get('balance', '0'))
        limit_value = Decimal(balance_data.get('limit', '0')) if 'limit' in balance_data else None
        buying_liabilities = Decimal(balance_data.get('buying_liabilities', '0'))
        selling_liabilities = Decimal(balance_data.get('selling_liabilities', '0'))
        
        # Create balance snapshot
        balance = AccountBalance(
            account_id=account.id,
            asset_id=asset.id if asset else None,
            balance=balance_value,
            limit=limit_value,
            buying_liabilities=buying_liabilities,
            selling_liabilities=selling_liabilities,
            snapshot_at=datetime.utcnow()
        )
        self.db.add(balance)
        
        return True
    
    def _ingest_transaction(self, tx_data: Dict[str, Any]) -> Tuple[bool, int]:
        """
        Ingest transaction and its operations
        
        Args:
            tx_data: Transaction data from Horizon
            
        Returns:
            Tuple of (transaction_created, operations_created)
        """
        tx_hash = tx_data.get('hash')
        
        # Check if transaction exists (idempotency)
        existing_tx = self.db.query(Transaction).filter(
            Transaction.tx_hash == tx_hash
        ).first()
        
        if existing_tx:
            return False, 0
        
        # Get or create source account
        source_address = tx_data.get('source_account')
        source_account = self.db.query(Account).filter(
            Account.address == source_address
        ).first()
        
        if not source_account:
            source_account = Account(
                address=source_address,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                risk_score=0.0,
                metadata={"discovered_via": "transaction"}
            )
            self.db.add(source_account)
            self.db.flush()
        
        # Create transaction
        transaction = Transaction(
            tx_hash=tx_hash,
            ledger=tx_data.get('ledger'),
            created_at=datetime.fromisoformat(tx_data.get('created_at').replace('Z', '+00:00')),
            source_account_id=source_account.id,
            fee_charged=tx_data.get('fee_charged', 0),
            operation_count=tx_data.get('operation_count', 0),
            memo=tx_data.get('memo'),
            successful=tx_data.get('successful', True)
        )
        self.db.add(transaction)
        self.db.flush()  # Get ID
        
        # Fetch and ingest operations
        operations = self.horizon_client.fetch_transaction_operations(tx_hash)
        operations_created = 0
        
        for op_data in operations:
            if self._ingest_operation(transaction, op_data):
                operations_created += 1
        
        logger.debug(
            "Ingested transaction",
            extra={
                "tx_hash": tx_hash,
                "operations": operations_created,
                "ledger": transaction.ledger
            }
        )
        
        return True, operations_created
    
    def _ingest_operation(self, transaction: Transaction, op_data: Dict[str, Any]) -> bool:
        """
        Ingest single operation
        
        Args:
            transaction: Parent transaction
            op_data: Operation data from Horizon
            
        Returns:
            True if created, False if skipped
        """
        op_id = op_data.get('id')
        
        # Check if operation exists (idempotency)
        existing_op = self.db.query(Operation).filter(Operation.op_id == op_id).first()
        if existing_op:
            return False
        
        op_type = op_data.get('type')
        
        # Extract account references
        from_account_id = None
        to_account_id = None
        asset_id = None
        amount = None
        
        # Handle different operation types
        if op_type in ['payment', 'path_payment_strict_send', 'path_payment_strict_receive']:
            from_address = op_data.get('from')
            to_address = op_data.get('to')
            
            if from_address:
                from_account = self._get_or_create_account(from_address)
                from_account_id = from_account.id
            
            if to_address:
                to_account = self._get_or_create_account(to_address)
                to_account_id = to_account.id
            
            # Get asset
            if op_data.get('asset_type') != 'native':
                asset = self._get_or_create_asset(
                    op_data.get('asset_code'),
                    op_data.get('asset_issuer'),
                    op_data.get('asset_type')
                )
                asset_id = asset.id
            
            amount = Decimal(op_data.get('amount', '0'))
            
            # Update counterparty edge
            if from_account_id and to_account_id:
                self._update_counterparty_edge(from_account_id, to_account_id, asset_id, amount)
        
        elif op_type == 'create_account':
            from_address = op_data.get('funder')
            to_address = op_data.get('account')
            
            if from_address:
                from_account = self._get_or_create_account(from_address)
                from_account_id = from_account.id
            
            if to_address:
                to_account = self._get_or_create_account(to_address)
                to_account_id = to_account.id
            
            amount = Decimal(op_data.get('starting_balance', '0'))
        
        # Create operation
        operation = Operation(
            op_id=op_id,
            tx_id=transaction.id,
            type=op_type,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            asset_id=asset_id,
            amount=amount,
            raw=op_data,  # Store complete operation data
            created_at=datetime.fromisoformat(op_data.get('created_at').replace('Z', '+00:00'))
        )
        self.db.add(operation)
        
        return True
    
    def _get_or_create_account(self, address: str) -> Account:
        """Get existing account or create minimal record"""
        account = self.db.query(Account).filter(Account.address == address).first()
        
        if not account:
            account = Account(
                address=address,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                risk_score=0.0,
                metadata={"discovered_via": "operation"}
            )
            self.db.add(account)
            self.db.flush()
        
        return account
    
    def _get_or_create_asset(
        self,
        asset_code: str,
        asset_issuer: str,
        asset_type: str
    ) -> Asset:
        """Get existing asset or create new record"""
        asset = self.db.query(Asset).filter(
            Asset.asset_code == asset_code,
            Asset.asset_issuer == asset_issuer
        ).first()
        
        if not asset:
            asset = Asset(
                asset_code=asset_code,
                asset_issuer=asset_issuer,
                asset_type=asset_type,
                metadata={"discovered_via": "operation"}
            )
            self.db.add(asset)
            self.db.flush()
        
        return asset
    
    def _update_counterparty_edge(
        self,
        from_account_id: int,
        to_account_id: int,
        asset_id: Optional[int],
        amount: Decimal
    ):
        """Update or create counterparty edge"""
        edge = self.db.query(CounterpartyEdge).filter(
            CounterpartyEdge.from_account_id == from_account_id,
            CounterpartyEdge.to_account_id == to_account_id,
            CounterpartyEdge.asset_id == asset_id
        ).first()
        
        if edge:
            edge.tx_count += 1
            edge.total_amount += amount
            edge.last_seen = datetime.utcnow()
        else:
            edge = CounterpartyEdge(
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                asset_id=asset_id,
                tx_count=1,
                total_amount=amount,
                last_seen=datetime.utcnow()
            )
            self.db.add(edge)
    
    def close(self):
        """Close resources"""
        if self._owns_client:
            self.horizon_client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
