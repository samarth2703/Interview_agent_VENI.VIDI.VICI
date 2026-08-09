from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

with (DATA / "curriculum.json").open(encoding="utf-8") as f:
    CURRICULUM = json.load(f)

SESSIONS: dict[str, dict[str, Any]] = {}

QUESTION_BANK = [
    (7, "Embeddings & Vector Search", "You have learned embeddings. Why can vector search retrieve relevant information when keyword search misses it?"),
    (8, "Embeddings & Vector Search", "A semantic search system returns similar but irrelevant chunks. How would you diagnose and improve retrieval quality?"),
    (10, "Retrieval Architecture", "Design a retrieval pipeline that decides when to use SQL, vector search, or hybrid retrieval. What trade-offs matter?"),
    (11, "RAG", "Walk me through a production RAG request from a user question to a grounded response. Where can hallucinations still occur?"),
    (12, "Prompt Engineering", "How would you evaluate two system prompts for accuracy, safety, and tone instead of choosing by intuition?"),
    (13, "Structured Outputs", "When would you use function calling and Pydantic validation in an AI application? What can fail?"),
    (20, "Conversation Memory", "How would you preserve useful conversation memory while preventing context growth from increasing cost and latency?"),
    (22, "Agentic AI", "When is a multi-agent workflow genuinely useful, and when would a single orchestrated agent be the better design?"),
    (23, "MCP", "Explain how MCP changes the way an AI application connects to tools. How would you secure those tool calls?"),
    (27, "AI Security", "An internal RAG assistant receives untrusted documents. What controls would you add for prompt injection, access control, and data leakage?"),
    (28, "Deployment", "Design a reliable deployment for an AI service. Which health, scaling, observability, and rollback signals would you monitor?"),
    (29, "Observability", "Which metrics would you use to distinguish a retrieval problem, a model problem, and an application latency problem?"),
]


class InterviewRequest(BaseModel):
    sessionId: str
    candidate: dict[str, Any] | None = None
    message: str | None = None


def score_answer(message: str) -> float:
    words = message.split()
    signals = sum(term in message.lower() for term in ["because", "trade", "monitor", "evaluate", "retriev", "security", "latency", "context"])
    return min(0.93, max(0.32, 0.35 + len(words) / 130 + signals * 0.055))


def build_questions(candidate: dict[str, Any]) -> list[tuple[int, str, str]]:
    missions = candidate.get("missions", [])
    passed_days = {m.get("day") for m in missions if m.get("passed")}
    weak_days = {m.get("day") for m in missions if m.get("skipped") or m.get("passed") is False or m.get("attempts", 1) >= 4}
    selected = [q for q in QUESTION_BANK if q[0] in passed_days]
    selected.sort(key=lambda q: (q[0] not in weak_days, q[0]))
    if len(selected) < 8:
        selected += [q for q in QUESTION_BANK if q not in selected]
    return selected[:8]


def feedback(session: dict[str, Any]) -> dict[str, Any]:
    average = sum(session["scores"]) / max(1, len(session["scores"]))
    candidate = session["candidate"]
    weak = [m["title"] for m in candidate.get("missions", []) if m.get("skipped") or m.get("passed") is False]
    covered = [q[1] for q in session["questions"]]
    strengths = [f"Engaged with {covered[0]} concepts through applied reasoning.", "Communicated an approach rather than relying only on definitions."]
    gaps = ([f"Revisit {weak[0]} and connect it to production decisions."] if weak else ["Push further on trade-offs, failure modes, and production observability."])
    return {
        "summary": f"{candidate.get('member', {}).get('name', 'The candidate')} showed a {'strong' if average > .7 else 'developing'} AI engineering foundation across {len(set(covered))} focus areas.",
        "strengths": strengths,
        "gaps": gaps,
        "next": ["Practice one system-design scenario with explicit trade-offs.", "Write an evaluation plan before changing a retrieval or prompting strategy.", "Reassess after completing the recommended learning path."],
        "score": round(average * 100),
        "dimensions": {"Technical knowledge": round(average * 100), "Problem solving": round(min(.95, average + .04) * 100), "System design": round(max(.55, average - .03) * 100), "Communication": round(min(.96, average + .06) * 100)},
    }


app = FastAPI(title="VIVI Interview Engine")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def home() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/candidates")
def candidates() -> dict[str, Any]:
    with (DATA / "candidates.json").open(encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/curriculum")
def curriculum() -> dict[str, Any]:
    return CURRICULUM


@app.post("/api/interview")
def interview(request: InterviewRequest) -> dict[str, Any]:
    if request.candidate:
        questions = build_questions(request.candidate)
        SESSIONS[request.sessionId] = {"candidate": request.candidate, "questions": questions, "index": 0, "scores": [], "answers": []}
        first = questions[0]
        return {"reply": f"Welcome. I reviewed your learning journey and will tailor this interview as we go. {first[2]}", "done": False, "meta": {"topic": first[1], "question": 1, "total": len(questions), "difficulty": 5}}
    session = SESSIONS.get(request.sessionId)
    if not session:
        raise HTTPException(404, "Interview session not found. Start with a candidate object.")
    if not request.message:
        raise HTTPException(422, "A message is required for a conversation turn.")
    session["scores"].append(score_answer(request.message))
    session["answers"].append(request.message)
    session["index"] += 1
    if session["index"] >= len(session["questions"]):
        return {"reply": "Interview completed. Your personalized assessment is ready.", "done": True, "feedback": feedback(session)}
    q = session["questions"][session["index"]]
    level = 7 if session["scores"][-1] > .7 else 5
    acknowledgement = "That is a thoughtful direction. Let's deepen the assessment." if level == 7 else "Good start. Let's explore the next area together."
    return {"reply": f"{acknowledgement} {q[2]}", "done": False, "meta": {"topic": q[1], "question": session["index"] + 1, "total": len(session["questions"]), "difficulty": level}}
