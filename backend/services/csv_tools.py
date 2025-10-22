from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)

def summarize(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "shape": df.shape,
        "columns": list(df.columns),
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "head": df.head(5).fillna("").to_dict(orient="records"),
    }

def basic_stats(df: pd.DataFrame) -> Dict[str, Any]:
    numeric = df.select_dtypes(include=[np.number])
    desc = numeric.describe().to_dict()
    return {"numeric_columns": list(numeric.columns), "describe": desc}

def most_missing(df: pd.DataFrame) -> Tuple[str, int]:
    s = df.isna().sum()
    col = s.idxmax()
    return col, int(s[col])

def histogram(df: pd.DataFrame, column: str, bins: int = 20) -> Dict[str, Any]:
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    counts, edges = np.histogram(series, bins=bins)
    return {"counts": counts.tolist(), "edges": edges.tolist()}
