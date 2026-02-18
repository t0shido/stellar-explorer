"""
Rule engine orchestrator with deduplication
"""
import logging
import hashlib
from typing import List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.rules.base import BaseRule, RuleResult
from app.rules.large_transfer_rule import LargeTransferRule
from app.rules.new_counterparty_rule import NewCounterpartyRule
from app.rules.dormant_reactivation_rule import DormantReactivationRule
from app.rules.rapid_outflow_rule import RapidOutflowRule
from app.rules.asset_concentration_rule import AssetConcentrationRule
from app.core.config import settings

logger = logging.getLogger(__name__)


class RuleEngine:
    """
    Rule engine orchestrator
    
    Manages rule evaluation, deduplication, and alert/flag creation
    """
    
    def __init__(self, db: Session, dry_run: bool = None):
        """
        Initialize rule engine
        
        Args:
            db: Database session
            dry_run: Override dry-run mode (defaults to config)
        """
        self.db = db
        self.dry_run = dry_run if dry_run is not None else settings.RULE_ENGINE_DRY_RUN
        
        # Initialize all rules
        self.rules: List[BaseRule] = [
            LargeTransferRule(settings),
            NewCounterpartyRule(settings),
            DormantReactivationRule(settings),
            RapidOutflowRule(settings),
            AssetConcentrationRule(settings)
        ]
        
        logger.info(
            f"Rule engine initialized",
            extra={
                "dry_run": self.dry_run,
                "rules_count": len(self.rules),
                "enabled_rules": sum(1 for r in self.rules if r.is_enabled())
            }
        )
    
    def run(self) -> dict:
        """
        Run all enabled rules
        
        Returns:
            Summary dictionary with results
        """
        if not settings.RULE_ENGINE_ENABLED:
            logger.info("Rule engine is disabled")
            return {
                "enabled": False,
                "message": "Rule engine is disabled in configuration"
            }
        
        logger.info(f"Starting rule engine evaluation (dry_run={self.dry_run})")
        
        all_results = []
        rule_summaries = []
        
        # Evaluate each rule
        for rule in self.rules:
            if not rule.is_enabled():
                logger.debug(f"Skipping disabled rule: {rule.name}")
                continue
            
            try:
                logger.info(f"Evaluating rule: {rule.name}")
                results = rule.evaluate(self.db)
                all_results.extend(results)
                
                fired_count = sum(1 for r in results if r.fired)
                rule_summaries.append({
                    "rule_name": rule.name,
                    "evaluated": True,
                    "results_count": len(results),
                    "fired_count": fired_count
                })
                
            except Exception as e:
                logger.error(
                    f"Error evaluating rule {rule.name}: {e}",
                    exc_info=True
                )
                rule_summaries.append({
                    "rule_name": rule.name,
                    "evaluated": False,
                    "error": str(e)
                })
        
        # Process results (deduplicate and create alerts/flags)
        alerts_created = 0
        flags_created = 0
        duplicates_skipped = 0
        
        for result in all_results:
            if not result.fired:
                continue
            
            # Check for duplicate
            if self._is_duplicate(result):
                duplicates_skipped += 1
                logger.debug(
                    f"Skipping duplicate alert",
                    extra={
                        "rule": result.rule_name,
                        "account_id": result.account_id
                    }
                )
                continue
            
            # Create alert/flag based on rule type
            if self.dry_run:
                logger.info(
                    f"[DRY RUN] Would create alert/flag",
                    extra={
                        "rule": result.rule_name,
                        "severity": result.severity,
                        "account_id": result.account_id,
                        "evidence": result.evidence
                    }
                )
            else:
                if result.rule_name in ['large_transfer', 'new_counterparty', 'rapid_outflow', 'asset_concentration']:
                    # Create alert
                    self._create_alert(result)
                    alerts_created += 1
                else:
                    # Create flag for dormant reactivation
                    self._create_flag(result)
                    flags_created += 1
        
        summary = {
            "enabled": True,
            "dry_run": self.dry_run,
            "timestamp": datetime.utcnow().isoformat(),
            "rules_evaluated": len(rule_summaries),
            "total_results": len(all_results),
            "fired_results": sum(1 for r in all_results if r.fired),
            "alerts_created": alerts_created,
            "flags_created": flags_created,
            "duplicates_skipped": duplicates_skipped,
            "rule_summaries": rule_summaries
        }
        
        logger.info(
            f"Rule engine evaluation completed",
            extra=summary
        )
        
        return summary
    
    def _is_duplicate(self, result: RuleResult) -> bool:
        """
        Check if alert/flag already exists (deduplication)
        
        Uses a hash of rule_name + account_id + key evidence fields
        to detect duplicates within the deduplication window
        """
        from app.db.models import Alert, Flag
        
        # Create deduplication key
        dedup_key = self._create_dedup_key(result)
        
        # Check deduplication window
        cutoff_time = datetime.utcnow() - timedelta(hours=settings.ALERT_DEDUP_WINDOW_HOURS)
        
        # Check for existing alert
        existing_alert = self.db.query(Alert).filter(
            Alert.alert_type == result.rule_name,
            Alert.account_id == result.account_id,
            Alert.created_at >= cutoff_time,
            Alert.payload['dedup_key'].astext == dedup_key
        ).first()
        
        if existing_alert:
            return True
        
        # Check for existing flag
        existing_flag = self.db.query(Flag).filter(
            Flag.flag_type == result.rule_name,
            Flag.account_id == result.account_id,
            Flag.created_at >= cutoff_time,
            Flag.evidence['dedup_key'].astext == dedup_key
        ).first()
        
        return existing_flag is not None
    
    def _create_dedup_key(self, result: RuleResult) -> str:
        """Create a unique deduplication key for a result"""
        # Include rule name, account, and key evidence fields
        key_parts = [
            result.rule_name,
            str(result.account_id or ''),
            str(result.asset_id or '')
        ]
        
        # Add rule-specific fields
        if result.rule_name == 'large_transfer':
            key_parts.append(result.evidence.get('transaction_hash', ''))
        elif result.rule_name == 'new_counterparty':
            key_parts.append(result.evidence.get('counterparty_account', ''))
        elif result.rule_name == 'rapid_outflow':
            key_parts.append(result.evidence.get('window_start', ''))
        elif result.rule_name == 'asset_concentration':
            key_parts.append(str(result.evidence.get('concentration_percent', '')))
        
        # Create hash
        key_string = '|'.join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    def _create_alert(self, result: RuleResult):
        """Create an alert from a rule result"""
        from app.db.models import Alert
        
        # Add dedup key to payload
        payload = result.evidence.copy()
        payload['dedup_key'] = self._create_dedup_key(result)
        payload['rule_fired_at'] = result.timestamp.isoformat()
        
        alert = Alert(
            account_id=result.account_id,
            asset_id=result.asset_id,
            alert_type=result.rule_name,
            severity=result.severity,
            payload=payload
        )
        self.db.add(alert)
        self.db.commit()
        
        logger.info(
            f"Alert created",
            extra={
                "alert_id": alert.id,
                "rule": result.rule_name,
                "severity": result.severity,
                "account_id": result.account_id
            }
        )
    
    def _create_flag(self, result: RuleResult):
        """Create a flag from a rule result"""
        from app.db.models import Flag, Account
        
        # Add dedup key to evidence
        evidence = result.evidence.copy()
        evidence['dedup_key'] = self._create_dedup_key(result)
        evidence['rule_fired_at'] = result.timestamp.isoformat()
        
        flag = Flag(
            account_id=result.account_id,
            flag_type=result.rule_name,
            severity=result.severity,
            reason=result.message,
            evidence=evidence
        )
        self.db.add(flag)
        
        # Update account risk score
        if result.account_id:
            account = self.db.query(Account).filter(Account.id == result.account_id).first()
            if account:
                severity_scores = {
                    'low': 10,
                    'medium': 25,
                    'high': 50,
                    'critical': 75
                }
                account.risk_score = min(100.0, account.risk_score + severity_scores.get(result.severity, 0))
        
        self.db.commit()
        
        logger.info(
            f"Flag created",
            extra={
                "flag_id": flag.id,
                "rule": result.rule_name,
                "severity": result.severity,
                "account_id": result.account_id
            }
        )
