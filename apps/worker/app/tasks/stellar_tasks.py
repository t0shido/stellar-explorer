from celery import Task
import requests
from stellar_sdk import Server
from app.celery_app import celery_app
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Stellar server
server = Server(horizon_url=settings.STELLAR_HORIZON_URL)


class StellarTask(Task):
    """Base task for Stellar operations"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed: {exc}")
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(base=StellarTask, bind=True)
def sync_recent_transactions(self):
    """Sync recent transactions from Stellar network"""
    try:
        logger.info("Starting transaction sync...")
        transactions = server.transactions().limit(100).order(desc=True).call()
        
        # Process transactions
        tx_count = len(transactions.get("_embedded", {}).get("records", []))
        logger.info(f"Synced {tx_count} transactions")
        
        return {"status": "success", "count": tx_count}
    except Exception as e:
        logger.error(f"Error syncing transactions: {e}")
        raise


@celery_app.task(base=StellarTask, bind=True)
def ingest_operations_stream(self, limit: int = 200):
    """
    Trigger operations-first ingestion via API.
    """
    try:
        url = f"{settings.API_BASE_URL}/ingest/operations/stream"
        logger.info("Starting operations stream ingestion", extra={"url": url, "limit": limit})

        response = requests.post(
            url,
            params={"limit": limit},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        logger.info(
            "Operations stream ingestion completed",
            extra={
                "transactions_created": data.get("transactions_created"),
                "operations_created": data.get("operations_created"),
                "limit": data.get("limit"),
            },
        )
        return data
    except Exception as e:
        logger.error("Error ingesting operations stream", extra={"error": str(e)})
        raise


@celery_app.task(base=StellarTask, bind=True)
def update_network_stats(self):
    """Update network statistics"""
    try:
        logger.info("Updating network stats...")
        
        # Fetch network data
        # This is a placeholder - implement actual stats collection
        stats = {
            "network": settings.STELLAR_NETWORK,
            "status": "active"
        }
        
        logger.info("Network stats updated")
        return stats
    except Exception as e:
        logger.error(f"Error updating network stats: {e}")
        raise


@celery_app.task(base=StellarTask, bind=True)
def fetch_account_details(self, account_id: str):
    """Fetch detailed account information"""
    try:
        logger.info(f"Fetching account details for {account_id}")
        account = server.accounts().account_id(account_id).call()
        
        return {
            "status": "success",
            "account_id": account_id,
            "data": account
        }
    except Exception as e:
        logger.error(f"Error fetching account {account_id}: {e}")
        raise


@celery_app.task(base=StellarTask, bind=True)
def analyze_transaction(self, tx_hash: str):
    """Analyze a specific transaction"""
    try:
        logger.info(f"Analyzing transaction {tx_hash}")
        
        # Fetch transaction details
        transaction = server.transactions().transaction(tx_hash).call()
        
        # Perform analysis (placeholder)
        analysis = {
            "hash": tx_hash,
            "analyzed": True,
            "operations": transaction.get("operation_count", 0)
        }
        
        return analysis
    except Exception as e:
        logger.error(f"Error analyzing transaction {tx_hash}: {e}")
        raise


@celery_app.task(base=StellarTask, bind=True)
def run_rule_engine(self):
    """
    Run the rule engine to evaluate all rules and create alerts/flags
    
    This task runs periodically (configured by RULE_ENGINE_INTERVAL_MINUTES)
    and evaluates all enabled rules against the current database state.
    """
    from app.db.database import SessionLocal
    from app.rules.engine import RuleEngine
    
    logger.info("Starting rule engine evaluation")
    
    db = SessionLocal()
    try:
        engine = RuleEngine(db)
        summary = engine.run()
        
        logger.info(
            f"Rule engine evaluation completed",
            extra={
                "alerts_created": summary.get("alerts_created", 0),
                "flags_created": summary.get("flags_created", 0),
                "duplicates_skipped": summary.get("duplicates_skipped", 0)
            }
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Error running rule engine: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()
