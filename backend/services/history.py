import json
from pathlib import Path
from typing import List, Dict

def ensure_file(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]", encoding="utf-8")

def session_file(base: Path, session_id: str) -> Path:
    return base / f"{session_id}.json"

def load_history(base: Path, session_id: str) -> List[Dict]:
    f = session_file(base, session_id)
    ensure_file(f)
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []

def append_history(base: Path, session_id: str, role: str, content: str):
    f = session_file(base, session_id)
    ensure_file(f)
    hist = json.loads(f.read_text(encoding="utf-8"))
    hist.append({"role": role, "content": content})
    f.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
