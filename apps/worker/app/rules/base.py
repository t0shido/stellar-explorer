"""
Base rule class and rule engine
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RuleResult:
    """Result of a rule evaluation"""
    
    def __init__(
        self,
        rule_name: str,
        fired: bool,
        severity: str,
        account_id: Optional[int] = None,
        asset_id: Optional[int] = None,
        evidence: Optional[Dict[str, Any]] = None,
        message: str = ""
    ):
        self.rule_name = rule_name
        self.fired = fired
        self.severity = severity
        self.account_id = account_id
        self.asset_id = asset_id
        self.evidence = evidence or {}
        self.message = message
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "rule_name": self.rule_name,
            "fired": self.fired,
            "severity": self.severity,
            "account_id": self.account_id,
            "asset_id": self.asset_id,
            "evidence": self.evidence,
            "message": self.message,
            "timestamp": self.timestamp.isoformat()
        }


class BaseRule(ABC):
    """Base class for all rules"""
    
    def __init__(self, config: Any):
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def evaluate(self, db: Session) -> List[RuleResult]:
        """
        Evaluate the rule and return results
        
        Args:
            db: Database session
            
        Returns:
            List of RuleResult objects
        """
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if rule is enabled in configuration"""
        pass
    
    def log_evaluation(self, results: List[RuleResult]):
        """Log rule evaluation results"""
        fired_count = sum(1 for r in results if r.fired)
        logger.info(
            f"Rule evaluation completed",
            extra={
                "rule": self.name,
                "total_results": len(results),
                "fired": fired_count,
                "enabled": self.is_enabled()
            }
        )
