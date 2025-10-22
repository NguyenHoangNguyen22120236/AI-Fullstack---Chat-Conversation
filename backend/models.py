from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class Session(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = "Default"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    attachment_type: Optional[str] = None  # 'image' | 'csv' | None
    attachment_ref: Optional[str] = None   # file path or dataset_id

class Dataset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    file_path: str
    original_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
