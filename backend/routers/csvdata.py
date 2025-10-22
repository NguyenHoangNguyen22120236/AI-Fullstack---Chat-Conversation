from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
from sqlmodel import Session
from models import Dataset, Message
from deps import get_engine
from services.csv_tools import load_csv, summarize, basic_stats, most_missing, histogram
import pandas as pd
import httpx

router = APIRouter(prefix="/csv", tags=["csv"])
CSV_DIR = Path("uploads/csv"); CSV_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    if "csv" not in file.content_type and not file.filename.endswith(".csv"):
        raise HTTPException(400, "Please upload a CSV file")
    path = CSV_DIR / file.filename
    with open(path, "wb") as f: f.write(await file.read())
    ds = Dataset(file_path=str(path), original_name=file.filename)
    with Session(get_engine()) as db:
        db.add(ds); db.commit(); db.refresh(ds)
    df = load_csv(str(path))
    return {"dataset_id": ds.id, "preview": summarize(df)}

@router.post("/from-url")
async def csv_from_url(url: str):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            r.raise_for_status()
        fname = url.split("/")[-1] or "data.csv"
        path = CSV_DIR / fname
        path.write_bytes(r.content)
    except Exception:
        raise HTTPException(400, "Could not fetch CSV from URL")
    ds = Dataset(file_path=str(path), original_name=fname)
    with Session(get_engine()) as db:
        db.add(ds); db.commit(); db.refresh(ds)
    df = load_csv(str(path))
    return {"dataset_id": ds.id, "preview": summarize(df)}

@router.get("/{dataset_id}/summary")
def get_summary(dataset_id: int):
    with Session(get_engine()) as db:
        ds = db.get(Dataset, dataset_id)
        if not ds: raise HTTPException(404, "Dataset not found")
    df = load_csv(ds.file_path)
    return summarize(df)

@router.get("/{dataset_id}/stats")
def get_stats(dataset_id: int):
    with Session(get_engine()) as db:
        ds = db.get(Dataset, dataset_id)
        if not ds: raise HTTPException(404, "Dataset not found")
    df = load_csv(ds.file_path)
    return basic_stats(df)

@router.get("/{dataset_id}/missing")
def get_missing(dataset_id: int):
    with Session(get_engine()) as db:
        ds = db.get(Dataset, dataset_id)
        if not ds: raise HTTPException(404, "Dataset not found")
    df = load_csv(ds.file_path)
    col, cnt = most_missing(df)
    return {"column": col, "missing": cnt}

@router.get("/{dataset_id}/histogram")
def get_hist(dataset_id: int, column: str, bins: int = 20):
    with Session(get_engine()) as db:
        ds = db.get(Dataset, dataset_id)
        if not ds: raise HTTPException(404, "Dataset not found")
    df = load_csv(ds.file_path)
    return histogram(df, column, bins)
