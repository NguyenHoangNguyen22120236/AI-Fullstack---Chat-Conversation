# 🚀 AI-Fullstack-Intern — Chat Conversation App

A full-stack chat application built with **FastAPI (Python)** and **React + TypeScript**, supporting **RAG**, **file uploads**, and **streaming AI responses**.

---

## 🧠 Tech Stack

- **Backend:** FastAPI (Python 3.12), SQLite, Uvicorn  
- **Frontend:** React + Vite + TypeScript, SCSS modules  
- **Database:** SQLite (`backend/db.sqlite3`)  
- **AI Logic:** Custom LLM integration (`services/llm.py`)

---

## ⚙️ Setup & Run Locally

### 1️⃣ Clone the project
```bash
git https://github.com/NguyenHoangNguyen22120236/AI-Fullstack---Chat-Conversation
cd AI-Fullstack---Chat-Conversation
```

### 🔑 Environment Variables
Create in **backend/.env**
```bash
OPENAI_API_KEY=your_open_ai_api
ALLOWED_ORIGINS=http://localhost:5173
OPENAI_TEXT_MODEL=gpt-4o-mini
OPENAI_VISION_MODEL=gpt-4o-mini
```

Create in **frontend/.env**
```bash
VITE_API_BASE=http://127.0.0.1:8000
```
### 2️⃣ Run Backend (FastAPI)
```bash
cd backend
python -m venv .venv

# Activate virtual environment:
# On Windows PowerShell:
.venv/Scripts/Activate.ps1
# On macOS / Linux:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app:app --reload
```
Backend will be available at http://localhost:8000

### 3️⃣ Run the Frontend (React + Vite)
```bash
cd frontend
npm install

# Start development server
npm run dev
```
Frontend will run at http://localhost:5173


### 🗂️ Project Structure
```bash
.
├── backend/
│   ├── routers/
│   │   ├── __init__.py
│   │   └── chat.py              # /chat endpoint
│   ├── services/
│   │   ├── csv_tools.py         # CSV utilities
│   │   ├── history.py           # Chat history & persistence
│   │   └── llm.py               # LLM client and stream logic
│   ├── uploads/                 # Temporary uploaded files
│   ├── app.py                   # FastAPI app entry point
│   ├── deps.py                  # Common dependencies (CORS, settings, etc.)
│   ├── models.py                # Pydantic/ORM models
│   ├── db.sqlite3               # Local development database
│   ├── .env
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── assets/
    │   ├── components/
    │   │   ├── ErrorBanner.tsx / .scss
    │   │   ├── MessageBubble.tsx / .scss
    │   │   ├── TypingBubble.tsx / .scss
    │   ├── styles/
    │   │   ├── _mixins.scss
    │   │   ├── _variables.scss
    │   │   └── app.scss
    │   ├── api.ts               # Frontend API client
    │   ├── App.tsx
    │   ├── index.css
    │   └── main.tsx
    ├── .env
    ├── index.html
    └── package.json
```