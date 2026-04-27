import os
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.db_models import Vocab, Hallucination
from app.core import config

def migrate():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    
    # Migrate Vocab
    vocab_path = os.path.join(config.VOCAB_DIR, "vocab.txt")
    if os.path.exists(vocab_path):
        print(f"Migrating Vocab from {vocab_path}...")
        with open(vocab_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            for line in lines:
                # Split by comma or newline
                words = [w.strip() for w in line.split(",") if w.strip()]
                for word in words:
                    exists = db.query(Vocab).filter(Vocab.word == word).first()
                    if not exists:
                        db.add(Vocab(word=word))
        db.commit()

    # Migrate Hallucinations
    h_path = os.path.join(config.VOCAB_DIR, "hallucinations.txt")
    if os.path.exists(h_path):
        print(f"Migrating Hallucinations from {h_path}...")
        with open(h_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            for line in lines:
                exists = db.query(Hallucination).filter(Hallucination.text == line).first()
                if not exists:
                    db.add(Hallucination(text=line))
        db.commit()
    
    db.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
