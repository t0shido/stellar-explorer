"""
Stellar Horizon API Client with retry logic and error handling
"""
import logging
import time
from collections import deque
from typing import Optional, Dict, Any, List
from stellar_sdk import Server, Account
from stellar_sdk.exceptions import (
    NotFoundError,
    BadRequestError,
    BadResponseError,
    ConnectionError as StellarConnectionError
)
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class HorizonClientError(Exception):
    """Base exception for Horizon client errors"""
    pass


class AccountNotFoundError(HorizonClientError):
    """Account not found on Stellar network"""
    pass


class HorizonClient:
    """
    Stellar Horizon API client with retry logic and structured logging
    """
    MAX_REQUESTS_PER_SECOND = 5  # basic per-process throttle
    _request_times = deque()
    
    def __init__(self, horizon_url: Optional[str] = None):
        """
        Initialize Horizon client
        
        Args:
            horizon_url: Horizon API URL (defaults to settings)
        """
        self.horizon_url = horizon_url or settings.STELLAR_HORIZON_URL
        self.server = Server(horizon_url=self.horizon_url)
        self.http_client = httpx.Client(timeout=30.0)
        
        logger.info(
            "Initialized Horizon client",
            extra={
                "horizon_url": self.horizon_url,
                "network": settings.STELLAR_NETWORK
            }
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            StellarConnectionError,
            BadResponseError,
            httpx.TimeoutException,
            httpx.ConnectError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def fetch_account(self, address: str) -> Dict[str, Any]:
        """
        Fetch account data from Horizon with retry logic
        
        Args:
            address: Stellar account address
            
        Returns:
            Account data dictionary
            
        Raises:
            AccountNotFoundError: If account doesn't exist
            HorizonClientError: For other API errors
        """
        self._throttle()
        try:
            logger.info(f"Fetching account data", extra={"address": address})
            
            account = self.server.accounts().account_id(address).call()
            
            logger.info(
                "Successfully fetched account",
                extra={
                    "address": address,
                    "balance_count": len(account.get('balances', [])),
                    "sequence": account.get('sequence')
                }
            )
            
            return account
            
        except NotFoundError:
            logger.warning(f"Account not found", extra={"address": address})
            raise AccountNotFoundError(f"Account {address} not found on network")
            
        except BadRequestError as e:
            logger.error(
                "Bad request to Horizon API",
                extra={"address": address, "error": str(e)}
            )
            raise HorizonClientError(f"Bad request: {str(e)}")
            
        except Exception as e:
            logger.error(
                "Unexpected error fetching account",
                extra={"address": address, "error": str(e), "error_type": type(e).__name__}
            )
            raise HorizonClientError(f"Failed to fetch account: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            StellarConnectionError,
            BadResponseError,
            httpx.TimeoutException
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def fetch_transactions(
        self,
        limit: int = 100,
        cursor: Optional[str] = None,
        order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Fetch recent transactions from Horizon
        
        Args:
            limit: Number of transactions to fetch (max 200)
            cursor: Pagination cursor
            order: Sort order ('asc' or 'desc')
            
        Returns:
            Transactions response with embedded records
            
        Raises:
            HorizonClientError: For API errors
        """
        self._throttle()
        try:
            logger.info(
                "Fetching transactions",
                extra={"limit": limit, "cursor": cursor, "order": order}
            )
            
            builder = self.server.transactions().limit(limit).order(desc=(order == "desc"))
            
            if cursor:
                builder = builder.cursor(cursor)
            
            response = builder.call()
            
            tx_count = len(response.get('_embedded', {}).get('records', []))
            logger.info(
                "Successfully fetched transactions",
                extra={"count": tx_count, "limit": limit}
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Error fetching transactions",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            raise HorizonClientError(f"Failed to fetch transactions: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            StellarConnectionError,
            BadResponseError,
            httpx.TimeoutException
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def fetch_operations(
        self,
        limit: int = 200,
        cursor: Optional[str] = None,
        order: str = "asc"
    ) -> Dict[str, Any]:
        """
        Fetch operations from Horizon

        Args:
            limit: Number of operations to fetch (max 200)
            cursor: Pagination cursor
            order: Sort order ('asc' or 'desc')

        Returns:
            Operations response with embedded records

        Raises:
            HorizonClientError: For API errors
        """
        self._throttle()
        try:
            logger.info(
                "Fetching operations",
                extra={"limit": limit, "cursor": cursor, "order": order}
            )

            builder = self.server.operations().limit(limit).order(desc=(order == "desc"))
            if cursor:
                builder = builder.cursor(cursor)

            response = builder.call()

            op_count = len(response.get('_embedded', {}).get('records', []))
            logger.info(
                "Successfully fetched operations",
                extra={"count": op_count, "limit": limit}
            )

            return response

        except Exception as e:
            logger.error(
                "Error fetching operations",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            raise HorizonClientError(f"Failed to fetch operations: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            StellarConnectionError,
            BadResponseError,
            httpx.TimeoutException
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def fetch_transaction_detail(self, tx_hash: str) -> Dict[str, Any]:
        """
        Fetch single transaction details by hash.
        """
        self._throttle()
        try:
            logger.info("Fetching transaction detail", extra={"tx_hash": tx_hash})
            response = self.server.transactions().transaction(tx_hash).call()
            return response
        except NotFoundError:
            logger.warning("Transaction not found", extra={"tx_hash": tx_hash})
            raise HorizonClientError(f"Transaction {tx_hash} not found")
        except Exception as e:
            logger.error(
                "Error fetching transaction detail",
                extra={"tx_hash": tx_hash, "error": str(e), "error_type": type(e).__name__}
            )
            raise HorizonClientError(f"Failed to fetch transaction {tx_hash}: {str(e)}")

    def _throttle(self):
        """
        Simple per-process token bucket to cap request rate.
        """
        now = time.time()
        window = 1.0
        max_req = self.MAX_REQUESTS_PER_SECOND

        dq = self._request_times
        while dq and now - dq[0] > window:
            dq.popleft()

        if len(dq) >= max_req:
            sleep_for = window - (now - dq[0]) + 0.01
            if sleep_for > 0:
                time.sleep(sleep_for)

        dq.append(time.time())
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            StellarConnectionError,
            BadResponseError,
            httpx.TimeoutException
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def fetch_transaction_operations(self, transaction_hash: str) -> List[Dict[str, Any]]:
        """
        Fetch operations for a specific transaction
        
        Args:
            transaction_hash: Transaction hash
            
        Returns:
            List of operation records
            
        Raises:
            HorizonClientError: For API errors
        """
        try:
            logger.debug(
                "Fetching transaction operations",
                extra={"tx_hash": transaction_hash}
            )
            
            response = self.server.operations().for_transaction(transaction_hash).call()
            operations = response.get('_embedded', {}).get('records', [])
            
            logger.debug(
                "Fetched operations",
                extra={"tx_hash": transaction_hash, "count": len(operations)}
            )
            
            return operations
            
        except Exception as e:
            logger.error(
                "Error fetching operations",
                extra={"tx_hash": transaction_hash, "error": str(e)}
            )
            raise HorizonClientError(f"Failed to fetch operations: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            StellarConnectionError,
            BadResponseError,
            httpx.TimeoutException
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def fetch_account_transactions(
        self,
        address: str,
        limit: int = 100,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch transactions for a specific account
        
        Args:
            address: Stellar account address
            limit: Number of transactions to fetch
            cursor: Pagination cursor
            
        Returns:
            Transactions response
            
        Raises:
            HorizonClientError: For API errors
        """
        try:
            logger.debug(
                "Fetching account transactions",
                extra={"address": address, "limit": limit}
            )
            
            builder = self.server.transactions().for_account(address).limit(limit).order(desc=True)
            
            if cursor:
                builder = builder.cursor(cursor)
            
            response = builder.call()
            
            tx_count = len(response.get('_embedded', {}).get('records', []))
            logger.debug(
                "Fetched account transactions",
                extra={"address": address, "count": tx_count}
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Error fetching account transactions",
                extra={"address": address, "error": str(e)}
            )
            raise HorizonClientError(f"Failed to fetch account transactions: {str(e)}")
    
    def close(self):
        """Close HTTP client connections"""
        self.http_client.close()
        logger.info("Closed Horizon client connections")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
