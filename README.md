# VIVI — Adaptive AI Interviewer

A responsive website and FastAPI interview engine for personalized AI engineering assessments.

## Run locally

```powershell
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

The required API contract is available at `POST /api/interview`. It uses deterministic, candidate-aware question selection until an LLM provider is connected.
