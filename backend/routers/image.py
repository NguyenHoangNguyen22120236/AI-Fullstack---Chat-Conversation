from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from pathlib import Path
import os
from sqlmodel import Session, select
from models import Message
from deps import get_engine
from services.llm import chat_vision

router = APIRouter(prefix="/image", tags=["image"])
UPLOAD_DIR = Path("uploads/images"); UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload")
async def upload_image(
    session_id: int = Form(...),            
    file: UploadFile = File(...),
):
    if file.content_type not in ["image/png", "image/jpeg"]:
        raise HTTPException(400, "Only PNG/JPG allowed")
    path = UPLOAD_DIR / file.filename
    with open(path, "wb") as f:
        f.write(await file.read())
    return {"image_path": str(path)}

@router.post("/ask")
async def ask_about_image(session_id: int, image_path: str, question: str):
    answer = await chat_vision(f"Refer to the provided image and answer: {question}", image_path)
    # persist message
    with Session(get_engine()) as db:
        db.add(Message(session_id=session_id, role="user", content=f"[image question] {question}", attachment_type="image", attachment_ref=image_path))
        db.add(Message(session_id=session_id, role="assistant", content=answer))
        db.commit()
    return {"answer": answer}
