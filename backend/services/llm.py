# services/llm.py
import os, base64, json, re
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
import httpx
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy import desc

from models import Attachment, Message
from .csv_tools import (
    load_csv, basic_stats, histogram_plot, df_to_markdown_table, dtypes_to_markdown_table
)

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOADS = BASE_DIR / "uploads"
load_dotenv(BASE_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY in environment (.env).")

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", TEXT_MODEL)

# ---------- Low-level API callers ----------
async def _openai_post(payload: dict) -> dict:
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=120, trust_env=True) as client:
        r = await client.post(OPENAI_URL, headers=headers, json=payload)
        if r.status_code >= 400:
            try:
                print("OpenAI error payload:", r.json())
            except Exception:
                print("OpenAI error text:", r.text)
        r.raise_for_status()
        return r.json()

async def call_openai(messages: List[Dict], tools: Optional[List[Dict]] = None) -> dict:
    payload = {"model": TEXT_MODEL, "messages": messages}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    return await _openai_post(payload)

async def call_openai_vision(prompt: str, image_path: str) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    payload = {
        "model": VISION_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }],
    }
    data = await _openai_post(payload)
    return data["choices"][0]["message"]["content"]

# ---------- Runtime helpers ----------
def _public_url(path: Path) -> Optional[str]:
    try:
        return f"/static/{path.relative_to(UPLOADS).as_posix()}"
    except Exception:
        return None

def _latest_attachment(db: OrmSession, session_id: str, kind: str) -> Optional[Attachment]:
    return (
        db.query(Attachment)
        .join(Message, Attachment.message_id == Message.id)
        .filter(Message.session_id == session_id, Attachment.kind == kind)
        .order_by(Attachment.created_at.desc())
        .first()
    )
    
def _resolve_csv_path(db: OrmSession, session_id: str, csv_path: Optional[str]) -> Optional[Path]:
    """
    Cố gắng tìm đúng CSV thật trong uploads/csv theo format {session_id}_{tênfile}.csv
    """
    if not csv_path:
        return None

    p = Path(csv_path)
    if p.is_file():
        return p

    csv_dir = UPLOADS / "csv"

    # Trường hợp model chỉ gửi 'products_sample.csv' → tìm file có prefix session_id_
    for cand in csv_dir.glob(f"{session_id}_*{Path(csv_path).name}"):
        if cand.is_file():
            return cand

    # Trường hợp model gửi thẳng 'abc_products_sample.csv'
    maybe = csv_dir / csv_path
    if maybe.is_file():
        return maybe

    # Fallback: tìm trong DB Attachment mới nhất
    att = (
        db.query(Attachment)
        .join(Message, Attachment.message_id == Message.id)
        .filter(Message.session_id == session_id, Attachment.kind == "csv")
        .order_by(desc(Attachment.created_at))
        .first()
    )
    if att and Path(att.path).is_file():
        return Path(att.path)

    return None

# ---------- Tool implementations ----------
async def tool_get_context_assets(db: OrmSession, session_id: str, prefer: Optional[str] = None) -> dict:
    """
    Return latest csv/image for this session if exist.
    prefer: 'csv' | 'image' | None
    """
    out = {}
    if prefer in (None, "csv"):
        last_csv = _latest_attachment(db, session_id, "csv")
        if last_csv:
            out["csv_path"] = str(last_csv.path)
            out["csv_public_url"] = _public_url(Path(last_csv.path))
    if prefer in (None, "image"):
        last_img = _latest_attachment(db, session_id, "image")
        if last_img:
            out["image_path"] = str(last_img.path)
            out["image_public_url"] = _public_url(Path(last_img.path))
    return out

async def tool_analyze_csv(db: OrmSession, session_id: str, csv_path: str, question: str) -> dict:
    # Resolve đường dẫn thật
    rp = _resolve_csv_path(db, session_id, csv_path)
    if not rp or not rp.is_file():
        return {"error": f"CSV file not found for path: {csv_path}"}

    df = load_csv(rp)
    parts = [f"### CSV Overview\n- **Rows**: {df.shape[0]}  \n- **Columns**: {df.shape[1]}"]

    dtypes_map = {c: str(t) for c, t in df.dtypes.items()}
    parts += ["**Preview (first 5 rows)**", df_to_markdown_table(df.head(5)), "**Columns & Types**", dtypes_to_markdown_table(dtypes_map)]

    # Basic stats nếu có cột số
    num_cols = df.select_dtypes("number").columns.tolist()
    if num_cols:
        desc = df[num_cols].describe().round(4)
        header = "| Stat | " + " | ".join(num_cols) + " |"
        sep = "|" + ("---|" * (len(num_cols) + 1))
        rows = ["| " + " | ".join([idx] + [str(v) for v in row.tolist()]) + " |" for idx, row in desc.iterrows()]
        parts += ["\n### Basic Stats", "\n".join([header, sep, *rows])]

    return {
        "markdown": "\n\n".join(parts),
        "tool_outputs": {"csv_rows": int(df.shape[0]), "csv_cols": int(df.shape[1])},
    }


async def tool_plot_histogram(db: OrmSession, session_id: str, csv_path: str, column: str) -> dict:
    rp = _resolve_csv_path(db, session_id, csv_path)
    if not rp or not rp.is_file():
        return {"error": f"CSV file not found for path: {csv_path}"}

    df = load_csv(rp)
    out_dir = UPLOADS / "images" / "plots"
    out_path = histogram_plot(df, column, out_dir, session_id)
    public = _public_url(out_path)

    md = f"### Histogram of `{column}`\n\n![Histogram]({public})\n\n_File_: `{out_path.name}`"
    return {
        "markdown": md,
        "tool_outputs": {"histogram_image": str(out_path)},
        "new_attachments": [
            {
                "kind": "plot",
                "path": str(out_path),
                "mime": "image/png",
                "original_name": out_path.name,
                "public_url": public,
            }
        ],
    }


async def tool_answer_about_image(image_path: str, question: str) -> dict:
    ans = await call_openai_vision(
        "You are a helpful vision assistant. Refer strictly to the provided image.", image_path
    )
    return {"markdown": ans}

# ---------- Orchestrator with tools ----------
TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "get_context_assets",
            "description": "Fetch latest CSV or image that user uploaded in this session so we can reuse them.",
            "parameters": {
                "type": "object",
                "properties": {"prefer": {"type": "string", "enum": ["csv", "image"]}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_csv",
            "description": "Analyze a CSV (preview, columns, dtypes, basic numeric stats) for the user's question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "csv_path": {"type": "string"},
                    "question": {"type": "string"},
                },
                "required": ["csv_path", "question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plot_histogram",
            "description": "Create and save a histogram image for a numeric column and return a markdown snippet with the public URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "csv_path": {"type": "string"},
                    "column": {"type": "string"},
                },
                "required": ["csv_path", "column"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "answer_about_image",
            "description": "Answer questions about an image path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string"},
                    "question": {"type": "string"},
                },
                "required": ["image_path", "question"],
            },
        },
    },
]

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are an AI chat assistant. You can use tools to work with CSVs and images.\n"
        "- If the user asks about CSV (summary, stats, missing, histogram), call tools; "
        "first call get_context_assets if csv_path is unknown.\n"
        "- If the user asks about an image, call get_context_assets and then answer_about_image.\n"
        "- Prefer returning clean Markdown with lists/tables when helpful.\n"
        "- If no file exists yet, ask the user to upload a CSV/image briefly."
    ),
}

async def chat_orchestrator(
    *,
    db: OrmSession,
    session_id: str,
    message: str,
    history: List[Dict],
    # optional “fresh” paths from current request:
    image_path: Optional[str],
    csv_path: Optional[str],
) -> Tuple[str, Dict, List[Dict], List[dict]]:
    """
    Returns (assistant_markdown, tool_outputs, updated_history, new_attachments_for_assistant)
    """
    messages = [SYSTEM_PROMPT] + history + [{"role": "user", "content": message}]
    tool_outputs_acc: Dict = {}
    new_asst_attachments: List[dict] = []

    # seed context if caller already knows fresh paths
    tool_context_note = []
    if csv_path:
        tool_context_note.append(f"(server-note: csv_path ready at {csv_path})")
    if image_path:
        tool_context_note.append(f"(server-note: image_path ready at {image_path})")
    if tool_context_note:
        messages.append({"role": "system", "content": " ".join(tool_context_note)})

    # tool-call loop
    for _ in range(4):
        data = await call_openai(messages, tools=TOOLS_SPEC)
        msg = data["choices"][0]["message"]

        if "tool_calls" not in msg:
            # final text
            ans = msg.get("content", "")
            updated = history + [{"role": "user", "content": message}, {"role": "assistant", "content": ans}]
            return ans, tool_outputs_acc, updated, new_asst_attachments

        messages.append(msg)
        
        # execute tool calls
        for tc in msg["tool_calls"]:
            name = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"] or "{}")

            if name == "get_context_assets":
                prefer = args.get("prefer")
                if not csv_path or prefer == "csv":
                    if not csv_path:
                        ctx = await tool_get_context_assets(db, session_id, prefer="csv")
                        csv_path = ctx.get("csv_path") or csv_path
                if not image_path or prefer == "image":
                    if not image_path:
                        ctx = await tool_get_context_assets(db, session_id, prefer="image")
                        image_path = ctx.get("image_path") or image_path
                result = {"csv_path": csv_path, "image_path": image_path}

            elif name == "analyze_csv":
                cp = args.get("csv_path") or csv_path
                if not cp:
                    result = {"error": "No CSV available in this session. Ask user to upload one."}
                else:
                    result = await tool_analyze_csv(db, session_id, cp, args.get("question", ""))

            elif name == "plot_histogram":
                cp = args.get("csv_path") or csv_path
                if not cp:
                    result = {"error": "No CSV available in this session to plot."}
                else:
                    result = await tool_plot_histogram(db, session_id, cp, args["column"])
                    # collect outputs/attachments
                    tool_outputs_acc.update(result.get("tool_outputs") or {})
                    new_asst_attachments.extend(result.get("new_attachments") or [])

            elif name == "answer_about_image":
                ip = args.get("image_path") or image_path
                if not ip:
                    result = {"error": "No image available in this session. Ask user to upload one."}
                else:
                    result = await tool_answer_about_image(ip, args.get("question", ""))

            else:
                result = {"error": f"Unknown tool {name}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "name": name,
                "content": json.dumps(result, ensure_ascii=False)
            })

    # safety net
    fallback = "I couldn't complete the request with tools. Could you upload a CSV or image if needed?"
    updated = history + [{"role": "user", "content": message}, {"role": "assistant", "content": fallback}]
    return fallback, tool_outputs_acc, updated, new_asst_attachments
