"""
Pytest configuration and fixtures
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import Account, Asset, Watchlist, WatchlistMember


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test
    Uses in-memory SQLite for speed
    """
    # Create in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_account_data():
    """Sample account data from Horizon API"""
    return {
        "id": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H",
        "account_id": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H",
        "sequence": "123456789",
        "subentry_count": 2,
        "last_modified_ledger": 12345,
        "balances": [
            {
                "balance": "10000.0000000",
                "limit": "922337203685.4775807",
                "buying_liabilities": "0.0000000",
                "selling_liabilities": "0.0000000",
                "asset_type": "credit_alphanum4",
                "asset_code": "USD",
                "asset_issuer": "GDUKMGUGDZQK6YHYA5Z6AY2G4XDSZPSZ3SW5UN3ARVMO6QSRDWP5YLEX"
            },
            {
                "balance": "5000.0000000",
                "buying_liabilities": "0.0000000",
                "selling_liabilities": "0.0000000",
                "asset_type": "native"
            }
        ],
        "flags": {
            "auth_required": False,
            "auth_revocable": False
        },
        "paging_token": "123456789"
    }


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data from Horizon API"""
    return {
        "hash": "abc123def456",
        "ledger": 12345,
        "created_at": "2024-02-16T20:00:00Z",
        "source_account": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H",
        "fee_charged": 100,
        "operation_count": 1,
        "memo": "Test transaction",
        "successful": True
    }


@pytest.fixture
def sample_operation_data():
    """Sample operation data from Horizon API"""
    return {
        "id": "123456789-1",
        "type": "payment",
        "created_at": "2024-02-16T20:00:00Z",
        "from": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H",
        "to": "GDUKMGUGDZQK6YHYA5Z6AY2G4XDSZPSZ3SW5UN3ARVMO6QSRDWP5YLEX",
        "amount": "100.0000000",
        "asset_type": "native"
    }


@pytest.fixture
def sample_watchlist(db_session):
    """Create a sample watchlist with members"""
    # Create watchlist
    watchlist = Watchlist(
        name="Test Watchlist",
        description="Test watchlist for unit tests"
    )
    db_session.add(watchlist)
    db_session.flush()
    
    # Create accounts
    accounts = []
    for i in range(3):
        account = Account(
            address=f"G{'A' * 55}{i}",
            risk_score=0.0,
            metadata={}
        )
        db_session.add(account)
        db_session.flush()
        accounts.append(account)
        
        # Add to watchlist
        member = WatchlistMember(
            watchlist_id=watchlist.id,
            account_id=account.id,
            reason=f"Test account {i}"
        )
        db_session.add(member)
    
    db_session.commit()
    
    return watchlist, accounts
