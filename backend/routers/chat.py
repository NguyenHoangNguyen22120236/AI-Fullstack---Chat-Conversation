from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from deps import get_engine
from models import Session as ChatSession, Message
from services.llm import chat_text

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/session")
def create_session(title: str = "New Chat"):
    with Session(get_engine()) as db:
        s = ChatSession(title=title)
        db.add(s); db.commit(); db.refresh(s)
        return {"session_id": s.id}

@router.get("/history")
def history(session_id: int):
    with Session(get_engine()) as db:
        rows = db.exec(
            select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
        ).all()
    return [{"role": r.role, "content": r.content, "created_at": r.created_at.isoformat(),
             "attachment_type": r.attachment_type, "attachment_ref": r.attachment_ref} for r in rows]

@router.post("/send")
async def send(session_id: int, user_text: str):
    with Session(get_engine()) as db:
        db.add(Message(session_id=session_id, role="user", content=user_text)); db.commit()
    # build context (last N messages)
    with Session(get_engine()) as db:
        msgs = db.exec(
            select(Message).where(Message.session_id == session_id).order_by(Message.created_at.desc()).limit(10)
        ).all()[::-1]
    llm_msgs = [{"role": m.role, "content": m.content} for m in msgs]
    reply = await chat_text(llm_msgs)
    with Session(get_engine()) as db:
        db.add(Message(session_id=session_id, role="assistant", content=reply)); db.commit()
    return {"reply": reply}
