# AI Customer Support Agent (RAG) — AI Support Agent

A scaffold for an AI-powered customer support chat agent, built for a fictional
 business. Answers questions about services, pricing, hours, policies,
and FAQs using Retrieval-Augmented Generation.

**Stack:** React (Vite) · FastAPI · PostgreSQL · Qdrant


## Getting started

### 1. Infrastructure (Postgres + Qdrant)

```bash
Create Database and user, grant permission and configure the .env accordingly
```


```bash
Install and configure Qdrant on Local System tehn run it 

./qdrant.exe
```

### 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # then edit values if needed

uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

- App: http://localhost:5173

