from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Transaction
from app.schemas.transaction import TransactionResponse, TransactionCreate

router = APIRouter()


@router.get("/", response_model=List[TransactionResponse])
def get_transactions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get list of transactions"""
    transactions = db.query(Transaction).offset(skip).limit(limit).all()
    return transactions


@router.get("/{tx_hash}", response_model=TransactionResponse)
def get_transaction(tx_hash: str, db: Session = Depends(get_db)):
    """Get transaction by hash"""
    transaction = db.query(Transaction).filter(Transaction.tx_hash == tx_hash).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.post("/", response_model=TransactionResponse)
def create_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    """Create new transaction"""
    db_transaction = Transaction(**transaction.model_dump())
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction
