"""
Rule 1: Large transfer from watched account above threshold
"""
import logging
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from decimal import Decimal

from app.rules.base import BaseRule, RuleResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class LargeTransferRule(BaseRule):
    """Detect large transfers from watched accounts"""
    
    def is_enabled(self) -> bool:
        return settings.RULE_LARGE_TRANSFER_ENABLED
    
    def evaluate(self, db: Session) -> List[RuleResult]:
        """
        Check for large transfers from watched accounts
        
        Logic:
        1. Get all watched accounts
        2. Find recent operations with amount > threshold
        3. Create alert for each violation
        """
        if not self.is_enabled():
            return []
        
        from app.db.models import (
            WatchlistMember, Account, Operation, Transaction, Asset
        )
        
        results = []
        threshold = Decimal(str(settings.RULE_LARGE_TRANSFER_THRESHOLD))
        
        # Get all watched accounts
        watched_accounts = db.query(Account).join(
            WatchlistMember,
            Account.id == WatchlistMember.account_id
        ).distinct().all()
        
        logger.info(
            f"Evaluating large transfer rule",
            extra={
                "watched_accounts": len(watched_accounts),
                "threshold": float(threshold)
            }
        )
        
        # Check recent operations (last hour to avoid re-processing)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        for account in watched_accounts:
            # Get recent large outgoing operations
            large_ops = db.query(Operation, Transaction, Asset).join(
                Transaction,
                Operation.tx_id == Transaction.id
            ).outerjoin(
                Asset,
                Operation.asset_id == Asset.id
            ).filter(
                and_(
                    Operation.from_account_id == account.id,
                    Operation.amount >= threshold,
                    Operation.created_at >= cutoff_time,
                    Transaction.successful == True
                )
            ).all()
            
            for operation, transaction, asset in large_ops:
                # Create result
                result = RuleResult(
                    rule_name="large_transfer",
                    fired=True,
                    severity=settings.RULE_LARGE_TRANSFER_SEVERITY,
                    account_id=account.id,
                    asset_id=asset.id if asset else None,
                    evidence={
                        "account_address": account.address,
                        "amount": str(operation.amount),
                        "threshold": str(threshold),
                        "asset_code": asset.asset_code if asset else "XLM",
                        "asset_issuer": asset.asset_issuer if asset else None,
                        "transaction_hash": transaction.tx_hash,
                        "ledger": transaction.ledger,
                        "operation_id": operation.op_id,
                        "operation_type": operation.type,
                        "to_account": operation.to_account_id,
                        "timestamp": operation.created_at.isoformat()
                    },
                    message=f"Large transfer of {operation.amount} {asset.asset_code if asset else 'XLM'} from watched account {account.address}"
                )
                results.append(result)
                
                logger.warning(
                    f"Large transfer detected",
                    extra={
                        "account": account.address,
                        "amount": str(operation.amount),
                        "threshold": str(threshold)
                    }
                )
        
        self.log_evaluation(results)
        return results
