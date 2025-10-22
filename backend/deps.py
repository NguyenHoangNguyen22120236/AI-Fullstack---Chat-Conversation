# deps.py
from sqlmodel import SQLModel, create_engine

_engine = None
def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine("sqlite:///db.sqlite3", connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(_engine)
    return _engine
