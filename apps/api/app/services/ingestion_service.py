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
    CounterpartyEdge, WatchlistMember, IngestionState
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
        
        stream_name = "transactions_global"
        try:
            # Read or initialize checkpoint
            state = self._get_ingestion_state(stream_name)
            cursor = state.last_paging_token

            # Fetch transactions from Horizon using durable cursor
            response = self.horizon_client.fetch_transactions(
                limit=limit,
                cursor=cursor,
                order="asc"
            )
            transactions = response.get('_embedded', {}).get('records', [])
            
            transactions_created = 0
            operations_created = 0
            last_token = None
            last_ledger = None
            
            for tx_data in transactions:
                last_token = tx_data.get('paging_token') or last_token
                last_ledger = tx_data.get('ledger') or last_ledger

                tx_created, ops_created = self._upsert_transaction_record(tx_data)
                if tx_created:
                    transactions_created += 1
                operations_created += ops_created

            # Update checkpoint if we processed anything
            if last_token:
                self._update_ingestion_state(stream_name, last_token, last_ledger)

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

    def ingest_operations_stream(self, limit: int = 200) -> Tuple[int, int]:
        """
        Stream operations using durable cursor (operations-first ingestion).

        Args:
            limit: Number of operations to fetch (max 200)

        Returns:
            Tuple of (transactions_created, operations_created)
        """
        logger.info("Starting operations ingestion", extra={"limit": limit})

        stream_name = "operations_global"
        try:
            state = self._get_ingestion_state(stream_name)
            cursor = state.last_paging_token

            response = self.horizon_client.fetch_operations(
                limit=limit,
                cursor=cursor,
                order="asc"
            )
            operations = response.get('_embedded', {}).get('records', [])

            transactions_created = 0
            operations_created = 0
            last_token = None
            last_ledger = None

            for op_data in operations:
                op_id = op_data.get('id')
                if not op_id:
                    continue

                last_token = op_data.get('paging_token') or last_token
                last_ledger = op_data.get('ledger') or last_ledger

                tx_hash = op_data.get('transaction_hash')
                transaction, tx_created = self._ensure_transaction(tx_hash, op_data)
                if tx_created:
                    transactions_created += 1
                if not transaction:
                    continue

                created = self._upsert_operation(transaction, op_data)
                if created:
                    operations_created += 1

            if last_token:
                self._update_ingestion_state(stream_name, last_token, last_ledger)

            self.db.commit()

            logger.info(
                "Operations ingestion completed",
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
                "Operations ingestion failed",
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
            account.meta_data = {
                **(account.meta_data or {}),
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
                meta_data={
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
            meta_data={
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
            source_account = self._upsert_account(source_address, tx_data)
        
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
        
        # Operations are ingested via the operations stream (to avoid N+1).
        logger.debug(
            "Ingested transaction",
            extra={
                "tx_hash": tx_hash,
                "operations": 0,
                "ledger": transaction.ledger
            }
        )
        
        return True, 0
    
    def _upsert_transaction_record(self, tx_data: Dict[str, Any]) -> Tuple[bool, int]:
        """
        Upsert transaction from a transaction record (no per-tx operations fetch).
        """
        tx_hash = tx_data.get('hash')
        if not tx_hash:
            return False, 0

        source_address = tx_data.get('source_account')
        source_account = self._get_or_create_account(source_address) if source_address else None

        created_at_raw = tx_data.get('created_at')
        created_at_dt = datetime.fromisoformat(created_at_raw.replace('Z', '+00:00')) if created_at_raw else datetime.utcnow()

        stmt = insert(Transaction).values(
            tx_hash=tx_hash,
            ledger=tx_data.get('ledger'),
            created_at=created_at_dt,
            source_account_id=source_account.id if source_account else None,
            fee_charged=tx_data.get('fee_charged', 0),
            operation_count=tx_data.get('operation_count', 0),
            memo=tx_data.get('memo'),
            successful=tx_data.get('successful', True)
        ).on_conflict_do_nothing()

        result = self.db.execute(stmt)
        created = result.rowcount == 1 if hasattr(result, "rowcount") else False
        return created, 0
    
    def _ensure_transaction(self, tx_hash: str, op_data: Dict[str, Any]) -> Tuple[Optional[Transaction], bool]:
        """Ensure transaction exists; create from detail if missing."""
        if not tx_hash:
            return None, False

        existing_tx = self.db.query(Transaction).filter(Transaction.tx_hash == tx_hash).first()
        if existing_tx:
            return existing_tx, False

        try:
            tx_detail = self.horizon_client.fetch_transaction_detail(tx_hash)
        except Exception as e:
            logger.error("Failed to fetch transaction detail", extra={"tx_hash": tx_hash, "error": str(e)})
            return None, False

        source_address = tx_detail.get('source_account')
        source_account = self._get_or_create_account(source_address) if source_address else None

        created_at = tx_detail.get('created_at')
        created_at_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00')) if created_at else datetime.utcnow()

        stmt = insert(Transaction).values(
            tx_hash=tx_hash,
            ledger=tx_detail.get('ledger'),
            created_at=created_at_dt,
            source_account_id=source_account.id if source_account else None,
            fee_charged=tx_detail.get('fee_charged', 0),
            operation_count=tx_detail.get('operation_count', 0),
            memo=tx_detail.get('memo'),
            successful=tx_detail.get('successful', True),
        ).on_conflict_do_nothing()

        result = self.db.execute(stmt)
        created = result.rowcount == 1 if hasattr(result, "rowcount") else False

        tx = self.db.query(Transaction).filter(Transaction.tx_hash == tx_hash).first()
        return tx, created

    def _upsert_operation(self, transaction: Transaction, op_data: Dict[str, Any]) -> bool:
        """Upsert a single operation (operations-first ingestion)."""
        op_id = op_data.get('id')
        if not op_id:
            return False

        op_type = op_data.get('type')

        from_account_id = None
        to_account_id = None
        asset_id = None
        amount = None

        if op_type in ['payment', 'path_payment_strict_send', 'path_payment_strict_receive']:
            from_address = op_data.get('from')
            to_address = op_data.get('to')

            if from_address:
                from_account = self._get_or_create_account(from_address)
                from_account_id = from_account.id

            if to_address:
                to_account = self._get_or_create_account(to_address)
                to_account_id = to_account.id

            if op_data.get('asset_type') != 'native':
                asset = self._get_or_create_asset(
                    op_data.get('asset_code'),
                    op_data.get('asset_issuer'),
                    op_data.get('asset_type')
                )
                asset_id = asset.id

            amount = Decimal(op_data.get('amount', '0'))

            if from_account_id and to_account_id:
                self._upsert_counterparty_edge(from_account_id, to_account_id, asset_id, amount)

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

        created_at_raw = op_data.get('created_at')
        created_at_dt = datetime.fromisoformat(created_at_raw.replace('Z', '+00:00')) if created_at_raw else datetime.utcnow()

        stmt = insert(Operation).values(
            op_id=op_id,
            tx_id=transaction.id,
            type=op_type,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            asset_id=asset_id,
            amount=amount,
            raw=op_data,
            created_at=created_at_dt,
        ).on_conflict_do_nothing()

        result = self.db.execute(stmt)
        return result.rowcount == 1 if hasattr(result, "rowcount") else False

    def _upsert_counterparty_edge(
        self,
        from_account_id: int,
        to_account_id: int,
        asset_id: Optional[int],
        amount: Decimal
    ):
        """Upsert counterparty edge accumulators."""
        stmt = insert(CounterpartyEdge).values(
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            asset_id=asset_id,
            tx_count=1,
            total_amount=amount,
            last_seen=datetime.utcnow(),
        ).on_conflict_do_update(
            index_elements=[
                CounterpartyEdge.from_account_id,
                CounterpartyEdge.to_account_id,
                CounterpartyEdge.asset_id,
            ],
            set_=dict(
                tx_count=CounterpartyEdge.tx_count + 1,
                total_amount=CounterpartyEdge.total_amount + amount,
                last_seen=datetime.utcnow(),
            ),
        )
        self.db.execute(stmt)
    
    def _get_or_create_account(self, address: str) -> Account:
        """Get existing account or create minimal record"""
        account = self.db.query(Account).filter(Account.address == address).first()
        
        if not account:
            account = Account(
                address=address,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                risk_score=0.0,
                meta_data={"discovered_via": "operation"}
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
                meta_data={"discovered_via": "operation"}
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

    def _get_ingestion_state(self, stream_name: str) -> IngestionState:
        """Fetch or initialize ingestion state for a stream."""
        state = (
            self.db.query(IngestionState)
            .filter(IngestionState.stream_name == stream_name)
            .first()
        )

        if not state:
            state = IngestionState(
                stream_name=stream_name,
                last_paging_token="now",
                last_ledger=None,
                error_count=0,
            )
            self.db.add(state)
            self.db.flush()

        return state

    def _update_ingestion_state(
        self,
        stream_name: str,
        last_paging_token: str,
        last_ledger: Optional[int],
        last_error: Optional[str] = None,
    ):
        """Upsert ingestion state for a stream."""
        stmt = insert(IngestionState).values(
            stream_name=stream_name,
            last_paging_token=last_paging_token,
            last_ledger=last_ledger,
            updated_at=datetime.utcnow(),
            error_count=0 if not last_error else 1,
            last_error=last_error,
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=[IngestionState.stream_name],
            set_=dict(
                last_paging_token=last_paging_token,
                last_ledger=last_ledger,
                updated_at=datetime.utcnow(),
                error_count=IngestionState.error_count + 1 if last_error else 0,
                last_error=last_error,
            ),
        )

        self.db.execute(stmt)

    def close(self):
        """Close resources"""
        if self._owns_client:
            self.horizon_client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
