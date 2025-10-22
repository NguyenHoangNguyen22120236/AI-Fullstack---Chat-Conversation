# app.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, image, csvdata

app = FastAPI(title="AI Chat Lite")
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

app.include_router(chat.router)
app.include_router(image.router)
app.include_router(csvdata.router)

@app.get("/health")
def health(): return {"ok": True}
