"""
Rule 5: Asset concentration warning (top 10 holders control > X%)
"""
import logging
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from decimal import Decimal

from app.rules.base import BaseRule, RuleResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class AssetConcentrationRule(BaseRule):
    """Detect high asset concentration among top holders"""
    
    def is_enabled(self) -> bool:
        return settings.RULE_ASSET_CONCENTRATION_ENABLED
    
    def evaluate(self, db: Session) -> List[RuleResult]:
        """
        Check for asset concentration
        
        Logic:
        1. Get all assets
        2. Calculate top 10 holders' percentage
        3. Alert if percentage > threshold
        """
        if not self.is_enabled():
            return []
        
        from app.db.models import Asset, AccountBalance, Account
        
        results = []
        concentration_threshold = settings.RULE_ASSET_CONCENTRATION_PERCENT
        
        # Get all assets
        assets = db.query(Asset).all()
        
        logger.info(
            f"Evaluating asset concentration rule",
            extra={
                "assets_count": len(assets),
                "concentration_threshold": concentration_threshold
            }
        )
        
        for asset in assets:
            # Get latest balances for this asset
            subquery = db.query(
                AccountBalance.account_id,
                func.max(AccountBalance.snapshot_at).label('max_snapshot')
            ).filter(
                AccountBalance.asset_id == asset.id
            ).group_by(
                AccountBalance.account_id
            ).subquery()
            
            # Get top 10 holders
            top_holders = db.query(
                AccountBalance,
                Account
            ).join(
                subquery,
                and_(
                    AccountBalance.account_id == subquery.c.account_id,
                    AccountBalance.snapshot_at == subquery.c.max_snapshot
                )
            ).join(
                Account,
                AccountBalance.account_id == Account.id
            ).filter(
                AccountBalance.asset_id == asset.id
            ).order_by(
                desc(AccountBalance.balance)
            ).limit(10).all()
            
            if not top_holders:
                continue
            
            # Calculate total supply
            total_supply = db.query(
                func.sum(AccountBalance.balance)
            ).join(
                subquery,
                and_(
                    AccountBalance.account_id == subquery.c.account_id,
                    AccountBalance.snapshot_at == subquery.c.max_snapshot
                )
            ).filter(
                AccountBalance.asset_id == asset.id
            ).scalar() or Decimal('0')
            
            if total_supply == 0:
                continue
            
            # Calculate top 10 concentration
            top_10_total = sum(balance.balance for balance, account in top_holders)
            concentration_percent = float((top_10_total / total_supply) * 100)
            
            if concentration_percent >= concentration_threshold:
                # Build holder details
                holder_details = []
                for balance, account in top_holders:
                    holder_percent = float((balance.balance / total_supply) * 100)
                    holder_details.append({
                        "account_address": account.address,
                        "account_label": account.label,
                        "balance": str(balance.balance),
                        "percentage": round(holder_percent, 4)
                    })
                
                result = RuleResult(
                    rule_name="asset_concentration",
                    fired=True,
                    severity=settings.RULE_ASSET_CONCENTRATION_SEVERITY,
                    asset_id=asset.id,
                    evidence={
                        "asset_code": asset.asset_code,
                        "asset_issuer": asset.asset_issuer,
                        "concentration_percent": round(concentration_percent, 2),
                        "threshold_percent": concentration_threshold,
                        "total_supply": str(total_supply),
                        "top_10_total": str(top_10_total),
                        "holder_count": len(top_holders),
                        "top_holders": holder_details
                    },
                    message=f"High asset concentration: Top 10 holders control {concentration_percent:.2f}% of {asset.asset_code}"
                )
                results.append(result)
                
                logger.warning(
                    f"Asset concentration warning",
                    extra={
                        "asset_code": asset.asset_code,
                        "concentration_percent": concentration_percent
                    }
                )
        
        self.log_evaluation(results)
        return results
