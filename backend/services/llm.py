import os, base64, re
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
import httpx
from .csv_tools import load_csv, basic_stats, histogram_plot, df_to_markdown_table, dtypes_to_markdown_table

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY in environment (.env).")

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", TEXT_MODEL)

async def call_openai(messages: List[Dict]) -> str:
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": TEXT_MODEL, "messages": messages}
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(OPENAI_URL, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            print("OpenAI error:", r.status_code, r.text)
            raise
    data = r.json()
    return data["choices"][0]["message"]["content"]

async def call_openai_vision(prompt: str, image_path: str) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}" }},
                ],
            }
        ],
    }
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(OPENAI_URL, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            print("OpenAI Vision error:", r.status_code, r.text)
            raise
    return r.json()["choices"][0]["message"]["content"]

def detect_histogram_request(message: str) -> Optional[str]:
    msg = message.lower()
    m = re.search(r"histogram\s+of\s+([a-zA-Z0-9_\- ]+)", msg)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"plot\s+(?:a\s+)?hist(?:ogram)?\s+of\s+([a-zA-Z0-9_\- ]+)", msg)
    if m2:
        return m2.group(1).strip()
    return None

def wants_summary(message: str) -> bool:
    return any(k in message.lower() for k in ["summarize", "overview", "tóm tắt"])

def wants_stats(message: str) -> bool:
    return any(k in message.lower() for k in ["basic stats", "stats", "describe", "thống kê"])

def wants_missing(message: str) -> bool:
    return "missing" in message.lower() or "null" in message.lower() or "na" in message.lower()

async def chat_core(
    *,
    session_id: str,
    message: str,
    history: List[Dict],
    image_path: Optional[str],
    csv_path: Optional[str],
    csv_url: Optional[str],
) -> Tuple[str, Dict, List[Dict]]:
    tool_outputs: Dict = {}

    if image_path:
        prompt = (
            "You are a helpful vision assistant. Refer strictly to the provided image "
            "when answering the user's question."
        )
        ans = await call_openai_vision(f"{prompt}\nQ: {message}", image_path)
        tool_outputs["image_path"] = image_path
        updated_history = history + [{"role":"user","content":message},{"role":"assistant","content":ans}]
        return ans, tool_outputs, updated_history

    if csv_path or csv_url:
        df = load_csv(Path(csv_path))
        tool_outputs["csv_rows"] = int(df.shape[0])
        tool_outputs["csv_cols"] = int(df.shape[1])

        response_parts = [f"### CSV Overview\n- **Rows**: {df.shape[0]}  \n- **Columns**: {df.shape[1]}"]

        if wants_summary(message):
            dtypes_map = {col: str(dtype) for col, dtype in df.dtypes.to_dict().items()}
            response_parts.append("### Summary")
            response_parts.append("**Preview (first 5 rows)**")
            response_parts.append(df_to_markdown_table(df.head(5)))
            response_parts.append("**Columns & Types**")
            response_parts.append(dtypes_to_markdown_table(dtypes_map))

        if wants_stats(message):
            stats = basic_stats(df)
            tool_outputs["basic_stats"] = stats
            num_cols = df.select_dtypes("number").columns.tolist()
            if num_cols:
                desc = df[num_cols].describe().round(4)
                header = "| Stat | " + " | ".join(num_cols) + " |"
                sep    = "|" + "---|" * (len(num_cols)+1)
                rows = []
                for idx, row in desc.iterrows():
                    cells = [idx] + [str(v) for v in row.tolist()]
                    rows.append("| " + " | ".join(cells) + " |")
                response_parts.append("### Basic Stats\n" + "\n".join([header, sep, *rows]))
            else:
                response_parts.append("> No numeric columns found for basic stats.")

        if wants_missing(message):
            mv = df.isna().sum().sort_values(ascending=False)
            mv_dict = mv[mv > 0].to_dict()
            tool_outputs["missing_values"] = mv_dict
            if mv_dict:
                header = "| Column | Missing |\n|---|---|"
                rows = [f"| {k} | {v} |" for k, v in list(mv_dict.items())[:15]]
                response_parts.append("### Missing Values (Top)\n" + "\n".join([header, *rows]))
            else:
                response_parts.append("> No missing values detected.")

        hist_col = detect_histogram_request(message)
        if hist_col:
            print("Detected histogram request for column:", hist_col)
            try:
                plot_dir = Path(csv_path).parent.parent / "images" / "plots"
                plot_path = histogram_plot(df, hist_col, plot_dir, session_id)
                tool_outputs["histogram_image"] = str(plot_path)
                public_url = f"/static/{plot_path.relative_to(Path(csv_path).parents[2]).as_posix()}"
                response_parts.append(f"### Histogram\n![Histogram]({public_url})\n\n_File_: `{plot_path.name}`")
            except Exception as e:
                response_parts.append(f"> Failed to plot histogram for **{hist_col}**: {e}")

        if len(response_parts) > 1:
            ans = "\n\n".join(response_parts)
            updated_history = history + [{"role":"user","content":message},{"role":"assistant","content":ans}]
            return ans, tool_outputs, updated_history

        if len(response_parts) == 1:
            head_text = df.head(10).to_csv(index=False)
            system = {
                "role": "system",
                "content": (
                    "You are a data assistant. Respond in clean Markdown with lists/tables where appropriate."
                ),
            }
            user = {
                "role": "user",
                "content": f"CSV preview (first 10 rows):\n{head_text}\n\nUser question: {message}",
            }
            ans = await call_openai([system] + history + [user])
            updated_history = history + [{"role":"user","content":message},{"role":"assistant","content":ans}]
            return ans, tool_outputs, updated_history
        else:
            ans = "\n\n".join(response_parts)
            updated_history = history + [{"role":"user","content":message},{"role":"assistant","content":ans}]
            return ans, tool_outputs, updated_history

    system = {
        "role": "system",
        "content": (
            "You are a concise, helpful assistant. Always format responses in Markdown. "
            "Use bullet lists, tables, and code blocks when that improves readability."
        ),
    }
    user = {"role": "user", "content": message}
    ans = await call_openai([system] + history + [user])
    updated_history = history + [{"role":"user","content":message},{"role":"assistant","content":ans}]
    return ans, tool_outputs, updated_history
