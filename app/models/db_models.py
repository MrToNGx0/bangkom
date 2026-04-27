from sqlalchemy import Column, Integer, String
from app.core.database import Base

class Vocab(Base):
    __tablename__ = "vocab"
    id = Column(Integer, primary_key=True, index=True)
    word = Column(String, unique=True, index=True)

class Hallucination(Base):
    __tablename__ = "hallucinations"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, unique=True, index=True)
