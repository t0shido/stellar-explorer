"""
Rule 4: Rapid outflow burst (>= N outgoing transfers in M minutes)
"""
import logging
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timedelta

from app.rules.base import BaseRule, RuleResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class RapidOutflowRule(BaseRule):
    """Detect rapid outflow bursts from watched accounts"""
    
    def is_enabled(self) -> bool:
        return settings.RULE_RAPID_OUTFLOW_ENABLED
    
    def evaluate(self, db: Session) -> List[RuleResult]:
        """
        Check for rapid outflow bursts
        
        Logic:
        1. Get all watched accounts
        2. Count outgoing operations in time window
        3. Alert if count >= threshold
        """
        if not self.is_enabled():
            return []
        
        from app.db.models import (
            WatchlistMember, Account, Operation, Transaction, Asset
        )
        
        results = []
        tx_count_threshold = settings.RULE_RAPID_OUTFLOW_TX_COUNT
        time_window_minutes = settings.RULE_RAPID_OUTFLOW_MINUTES
        
        # Get all watched accounts
        watched_accounts = db.query(Account).join(
            WatchlistMember,
            Account.id == WatchlistMember.account_id
        ).distinct().all()
        
        logger.info(
            f"Evaluating rapid outflow rule",
            extra={
                "watched_accounts": len(watched_accounts),
                "tx_threshold": tx_count_threshold,
                "time_window_minutes": time_window_minutes
            }
        )
        
        # Define time window
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        for account in watched_accounts:
            # Count outgoing operations in time window
            outgoing_ops = db.query(Operation, Transaction, Asset).join(
                Transaction,
                Operation.tx_id == Transaction.id
            ).outerjoin(
                Asset,
                Operation.asset_id == Asset.id
            ).filter(
                and_(
                    Operation.from_account_id == account.id,
                    Operation.created_at >= cutoff_time,
                    Transaction.successful == True,
                    Operation.type.in_(['payment', 'path_payment_strict_send', 'path_payment_strict_receive'])
                )
            ).all()
            
            op_count = len(outgoing_ops)
            
            if op_count >= tx_count_threshold:
                # Calculate total amount and unique counterparties
                total_amount = sum(op.amount for op, tx, asset in outgoing_ops if op.amount)
                unique_counterparties = len(set(op.to_account_id for op, tx, asset in outgoing_ops if op.to_account_id))
                
                # Get asset breakdown
                asset_breakdown = {}
                for op, tx, asset in outgoing_ops:
                    asset_key = asset.asset_code if asset else "XLM"
                    if asset_key not in asset_breakdown:
                        asset_breakdown[asset_key] = {
                            "count": 0,
                            "total_amount": 0
                        }
                    asset_breakdown[asset_key]["count"] += 1
                    if op.amount:
                        asset_breakdown[asset_key]["total_amount"] += float(op.amount)
                
                result = RuleResult(
                    rule_name="rapid_outflow",
                    fired=True,
                    severity=settings.RULE_RAPID_OUTFLOW_SEVERITY,
                    account_id=account.id,
                    evidence={
                        "account_address": account.address,
                        "operation_count": op_count,
                        "threshold": tx_count_threshold,
                        "time_window_minutes": time_window_minutes,
                        "total_amount": str(total_amount),
                        "unique_counterparties": unique_counterparties,
                        "asset_breakdown": asset_breakdown,
                        "window_start": cutoff_time.isoformat(),
                        "window_end": datetime.utcnow().isoformat(),
                        "operations_per_minute": round(op_count / time_window_minutes, 2)
                    },
                    message=f"Rapid outflow burst detected: {op_count} outgoing transfers in {time_window_minutes} minutes from {account.address}"
                )
                results.append(result)
                
                logger.warning(
                    f"Rapid outflow burst detected",
                    extra={
                        "account": account.address,
                        "operation_count": op_count,
                        "time_window_minutes": time_window_minutes
                    }
                )
        
        self.log_evaluation(results)
        return results
