from __future__ import annotations
from pathlib import Path
import io
import pandas as pd
import numpy as np
import httpx
import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt

def ensure_dirs(*dirs: Path):
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

async def download_csv_from_url(url: str, out_dir: Path, session_id: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{session_id}_from_url.csv"
    out_path = out_dir / filename
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(url)
        r.raise_for_status()
        out_path.write_bytes(r.content)
    return out_path

def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)

def summarize_dataframe(df: pd.DataFrame) -> str:
    rows, cols = df.shape
    col_types = df.dtypes.astype(str).to_dict()
    sample_cols = ", ".join(list(df.columns[:8]))
    return (
        f"Dataset has {rows} rows and {cols} columns.\n"
        f"First columns: {sample_cols}\n"
        f"Types: {col_types}"
    )

def basic_stats(df: pd.DataFrame) -> dict:
    stats = {}
    numeric_df = df.select_dtypes(include=[np.number])
    if not numeric_df.empty:
        desc = numeric_df.describe().to_dict()
        stats["numeric_summary"] = desc
    mv = df.isna().sum().sort_values(ascending=False)
    stats["missing_values"] = mv[mv > 0].to_dict()
    return stats

def histogram_plot(df: pd.DataFrame, column: str, out_dir: Path, session_id: str) -> Path:
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found.")
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        raise ValueError(f"Column '{column}' is not numeric or has no data.")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{session_id}_hist_{column}.png"

    plt.figure()
    plt.hist(series, bins=20)
    plt.title(f"Histogram of {column}")
    plt.xlabel(column)
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    return out_path

def _escape_md(val: str) -> str:
    return str(val).replace("|", "\\|")

def df_to_markdown_table(df, *, max_rows: int = 5, max_cols: int = 8) -> str:
    if df is None or df.empty:
        return "> *(empty dataframe)*"
    df2 = df.copy().iloc[:max_rows, :max_cols]

    headers = [str(c) for c in df2.columns.tolist()]
    header_line = "| " + " | ".join(_escape_md(h) for h in headers) + " |"
    sep_line = "|" + " --- |" * len(headers)

    body_lines = []
    for _, row in df2.iterrows():
        cells = [ _escape_md(row[c]) if not isinstance(row[c], (int, float)) else row[c] for c in df2.columns ]
        body_lines.append("| " + " | ".join(str(c) for c in cells) + " |")

    return "\n".join([header_line, sep_line, *body_lines])

def dtypes_to_markdown_table(dtypes_map: dict) -> str:
    if not dtypes_map:
        return "> *(no columns)*"
    header = "| Column | Type |\n| --- | --- |"
    rows = [f"| {_escape_md(k)} | {_escape_md(v)} |" for k, v in dtypes_map.items()]
    return "\n".join([header, *rows])