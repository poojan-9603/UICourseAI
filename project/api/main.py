# api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List

from chatbot.llm_intent import parse_with_llm
from chatbot.intent import parse
from chatbot.actions import rank_professors

app = FastAPI(title="UICourseAI API")

# --- CORS so the React app (localhost:5173) can call us ---
origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request / Response models ---


class ChatRequest(BaseModel):
    message: str
    use_llm: bool = True


class ChatResponse(BaseModel):
    used_llm: bool
    intent: Dict[str, Any]
    results: List[Dict[str, Any]]


@app.post("/api/query", response_model=ChatResponse)
def query_chat(req: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint that the frontend will call.
    """
    if req.use_llm:
        intent = parse_with_llm(req.message)
        used_llm = True
    else:
        intent = parse(req.message)
        used_llm = False

    results = rank_professors(intent, top_n=5)

    return ChatResponse(
        used_llm=used_llm,
        intent=intent,
        results=results,
    )
