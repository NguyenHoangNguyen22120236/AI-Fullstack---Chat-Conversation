# routers/chat.py
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from deps import get_db
from models import SessionChat, Message, Attachment
from services.llm import chat_core
from services.csv_tools import ensure_dirs, download_csv_from_url

router = APIRouter(prefix="", tags=["chat"])

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "uploads"
IMG_DIR = UPLOAD_DIR / "images"
CSV_DIR = UPLOAD_DIR / "csv"
ensure_dirs(IMG_DIR, CSV_DIR, UPLOAD_DIR)

def make_public_url(path: str) -> Optional[str]:
    up = BASE_DIR / "uploads"
    p = Path(path)
    try:
        rel = p.relative_to(up)
        return f"/static/{rel.as_posix()}"
    except Exception:
        return None

@router.post("/chat")
async def chat(
    session_id: str = Form(...),
    message: str = Form(...),
    file: Optional[UploadFile] = File(None),
    csv_url: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    sess = db.get(SessionChat, session_id)
    if not sess:
        sess = SessionChat(id=session_id, title=message[:120])
        db.add(sess)
        db.flush()
    else:
        sess.title = sess.title or message[:120]

    saved_image_path = None
    saved_csv_path = None
    user_attachments: list[dict] = []   

    if file is not None:
        content_type = (file.content_type or "").lower()
        filename = file.filename or "upload"
        suffix = Path(filename).suffix.lower()

        if "image" in content_type or suffix in [".png", ".jpg", ".jpeg"]:
            saved_image_path = IMG_DIR / f"{session_id}_{filename}"
            with open(saved_image_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
        elif suffix == ".csv" or "csv" in content_type:
            saved_csv_path = CSV_DIR / f"{session_id}_{filename}"
            with open(saved_csv_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type.")

    if csv_url and not saved_csv_path:
        saved_csv_path = await download_csv_from_url(csv_url, CSV_DIR, session_id)

    user_msg = Message(session_id=session_id, role="user", content=message, tool_outputs=None)
    db.add(user_msg)
    db.flush()

    if saved_image_path:
        att = Attachment(
            message_id=user_msg.id,
            kind="image",
            path=str(saved_image_path),
            original_name=file.filename if file else None,
            mime=file.content_type if file else None,
        )
        db.add(att)
        db.flush()
        user_attachments.append({
            "id": att.id,
            "kind": "image",
            "path": att.path,
            "original_name": att.original_name,
            "mime": att.mime,
            "public_url": make_public_url(att.path),
        })

    if saved_csv_path:
        att = Attachment(
            message_id=user_msg.id,
            kind="csv",
            path=str(saved_csv_path),
            original_name=file.filename if file else None,
            mime=file.content_type if file else None,
        )
        db.add(att)
        db.flush()
        user_attachments.append({
            "id": att.id,
            "kind": "csv",
            "path": att.path,
            "original_name": att.original_name,
            "mime": att.mime,
            "public_url": make_public_url(att.path),
        })

    assistant_message, tool_outputs, _ = await chat_core(
        session_id=session_id,
        message=message,
        history=[{"role": m.role, "content": m.content} for m in sess.messages],
        image_path=str(saved_image_path) if saved_image_path else None,
        csv_path=str(saved_csv_path) if saved_csv_path else None,
        csv_url=csv_url,
    )

    asst_msg = Message(
        session_id=session_id, role="assistant", content=assistant_message, tool_outputs=tool_outputs or None
    )
    db.add(asst_msg)
    db.flush()

    assistant_attachments: list[dict] = [] 

    if tool_outputs and tool_outputs.get("histogram_image"):
        att = Attachment(
            message_id=asst_msg.id,
            kind="plot",
            path=tool_outputs["histogram_image"],
            original_name=Path(tool_outputs["histogram_image"]).name,
            mime="image/png",
        )
        db.add(att)
        db.flush()
        assistant_attachments.append({
            "id": att.id,
            "kind": "plot",
            "path": att.path,
            "original_name": att.original_name,
            "mime": att.mime,
            "public_url": make_public_url(att.path),
        })

    sess.updated_at = func.now()
    db.commit()
    db.refresh(asst_msg)

    return JSONResponse(
        {
            "session_id": session_id,
            "assistant_message": assistant_message,
            "tool_outputs": tool_outputs,
            "message_id": asst_msg.id,
            "user_message": {
                "id": user_msg.id,
                "attachments": user_attachments,
            },
            "assistant_message_meta": {
                "id": asst_msg.id,
                "attachments": assistant_attachments,
            },
        }
    )

@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    q = db.query(SessionChat).order_by(desc(SessionChat.updated_at)).offset(offset).limit(limit)
    rows = []
    for s in q.all():
        last_msg = db.execute(
            select(Message).where(Message.session_id == s.id).order_by(desc(Message.created_at)).limit(1)
        ).scalar_one_or_none()
        count = db.execute(
            select(func.count()).select_from(Message).where(Message.session_id == s.id)
        ).scalar_one()
        rows.append(
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "last_message": last_msg.content[:200] if last_msg else "",
                "message_count": int(count),
            }
        )
    return {"sessions": rows, "offset": offset, "limit": limit}

@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    sess = db.get(SessionChat, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    def serialize_message(m: Message):
        return {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "tool_outputs": m.tool_outputs,
            "created_at": m.created_at.isoformat(),
            "attachments": [
                {
                    "id": a.id,
                    "kind": a.kind,
                    "path": a.path,
                    "original_name": a.original_name,
                    "mime": a.mime,
                    "public_url": f"/static/{Path(a.path).relative_to(Path(__file__).resolve().parents[1] / 'uploads').as_posix()}"
                                  if Path(a.path).as_posix().find("/uploads/") >= 0 or "uploads" in Path(a.path).parts else None
                }
                for a in m.attachments
            ],
        }

    return {
        "session": {
            "id": sess.id,
            "title": sess.title,
            "created_at": sess.created_at.isoformat(),
            "updated_at": sess.updated_at.isoformat(),
        },
        "messages": [serialize_message(m) for m in sess.messages],
    }
