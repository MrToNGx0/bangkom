from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.core.database import get_db
from app.models.db_models import Vocab, Hallucination

router = APIRouter()

# Pydantic models for request/response
class ItemBase(BaseModel):
    text: str

class ItemResponse(ItemBase):
    id: int
    class Config:
        from_attributes = True

# Vocab Endpoints
@router.get("/vocab", response_model=List[ItemResponse])
def get_vocab(db: Session = Depends(get_db)):
    items = db.query(Vocab).all()
    # Map 'word' to 'text' for uniform API
    return [{"id": i.id, "text": i.word} for i in items]

@router.post("/vocab", response_model=ItemResponse)
def create_vocab(item: ItemBase, db: Session = Depends(get_db)):
    db_item = Vocab(word=item.text)
    db.add(db_item)
    try:
        db.commit()
        db.refresh(db_item)
    except:
        db.rollback()
        raise HTTPException(status_code=400, detail="Word already exists")
    return {"id": db_item.id, "text": db_item.word}

@router.delete("/vocab/{item_id}")
def delete_vocab(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Vocab).filter(Vocab.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return {"status": "deleted"}

# Hallucination Endpoints
@router.get("/hallucinations", response_model=List[ItemResponse])
def get_hallucinations(db: Session = Depends(get_db)):
    items = db.query(Hallucination).all()
    return items

@router.post("/hallucinations", response_model=ItemResponse)
def create_hallucination(item: ItemBase, db: Session = Depends(get_db)):
    db_item = Hallucination(text=item.text)
    db.add(db_item)
    try:
        db.commit()
        db.refresh(db_item)
    except:
        db.rollback()
        raise HTTPException(status_code=400, detail="Hallucination already exists")
    return db_item

@router.delete("/hallucinations/{item_id}")
def delete_hallucination(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Hallucination).filter(Hallucination.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return {"status": "deleted"}
