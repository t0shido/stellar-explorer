"""
Rule 2: New counterparty for watched account with amount above threshold
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


class NewCounterpartyRule(BaseRule):
    """Detect new counterparty relationships with large amounts"""
    
    def is_enabled(self) -> bool:
        return settings.RULE_NEW_COUNTERPARTY_ENABLED
    
    def evaluate(self, db: Session) -> List[RuleResult]:
        """
        Check for new counterparties with large initial transactions
        
        Logic:
        1. Get all watched accounts
        2. Find counterparty edges created recently
        3. Check if first transaction exceeds threshold
        """
        if not self.is_enabled():
            return []
        
        from app.db.models import (
            WatchlistMember, Account, CounterpartyEdge, Asset
        )
        
        results = []
        threshold = Decimal(str(settings.RULE_NEW_COUNTERPARTY_THRESHOLD))
        
        # Get all watched accounts
        watched_accounts = db.query(Account).join(
            WatchlistMember,
            Account.id == WatchlistMember.account_id
        ).distinct().all()
        
        logger.info(
            f"Evaluating new counterparty rule",
            extra={
                "watched_accounts": len(watched_accounts),
                "threshold": float(threshold)
            }
        )
        
        # Check recent edges (last hour)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        for account in watched_accounts:
            # Get recent counterparty edges (both directions)
            new_edges_out = db.query(CounterpartyEdge, Account, Asset).join(
                Account,
                CounterpartyEdge.to_account_id == Account.id
            ).outerjoin(
                Asset,
                CounterpartyEdge.asset_id == Asset.id
            ).filter(
                and_(
                    CounterpartyEdge.from_account_id == account.id,
                    CounterpartyEdge.last_seen >= cutoff_time,
                    CounterpartyEdge.tx_count == 1,  # First transaction
                    CounterpartyEdge.total_amount >= threshold
                )
            ).all()
            
            new_edges_in = db.query(CounterpartyEdge, Account, Asset).join(
                Account,
                CounterpartyEdge.from_account_id == Account.id
            ).outerjoin(
                Asset,
                CounterpartyEdge.asset_id == Asset.id
            ).filter(
                and_(
                    CounterpartyEdge.to_account_id == account.id,
                    CounterpartyEdge.last_seen >= cutoff_time,
                    CounterpartyEdge.tx_count == 1,  # First transaction
                    CounterpartyEdge.total_amount >= threshold
                )
            ).all()
            
            # Process outgoing edges
            for edge, counterparty, asset in new_edges_out:
                result = RuleResult(
                    rule_name="new_counterparty",
                    fired=True,
                    severity=settings.RULE_NEW_COUNTERPARTY_SEVERITY,
                    account_id=account.id,
                    asset_id=asset.id if asset else None,
                    evidence={
                        "watched_account": account.address,
                        "counterparty_account": counterparty.address,
                        "direction": "outgoing",
                        "amount": str(edge.total_amount),
                        "threshold": str(threshold),
                        "asset_code": asset.asset_code if asset else "XLM",
                        "asset_issuer": asset.asset_issuer if asset else None,
                        "first_seen": edge.last_seen.isoformat(),
                        "tx_count": edge.tx_count
                    },
                    message=f"New counterparty {counterparty.address} with large outgoing transfer of {edge.total_amount} {asset.asset_code if asset else 'XLM'}"
                )
                results.append(result)
                
                logger.warning(
                    f"New counterparty detected",
                    extra={
                        "account": account.address,
                        "counterparty": counterparty.address,
                        "amount": str(edge.total_amount)
                    }
                )
            
            # Process incoming edges
            for edge, counterparty, asset in new_edges_in:
                result = RuleResult(
                    rule_name="new_counterparty",
                    fired=True,
                    severity=settings.RULE_NEW_COUNTERPARTY_SEVERITY,
                    account_id=account.id,
                    asset_id=asset.id if asset else None,
                    evidence={
                        "watched_account": account.address,
                        "counterparty_account": counterparty.address,
                        "direction": "incoming",
                        "amount": str(edge.total_amount),
                        "threshold": str(threshold),
                        "asset_code": asset.asset_code if asset else "XLM",
                        "asset_issuer": asset.asset_issuer if asset else None,
                        "first_seen": edge.last_seen.isoformat(),
                        "tx_count": edge.tx_count
                    },
                    message=f"New counterparty {counterparty.address} with large incoming transfer of {edge.total_amount} {asset.asset_code if asset else 'XLM'}"
                )
                results.append(result)
                
                logger.warning(
                    f"New counterparty detected",
                    extra={
                        "account": account.address,
                        "counterparty": counterparty.address,
                        "amount": str(edge.total_amount)
                    }
                )
        
        self.log_evaluation(results)
        return results
