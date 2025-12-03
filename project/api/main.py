# project/api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from project.chatbot.llm_intent import parse_with_llm
from project.chatbot.intent import parse
from project.chatbot.actions import rank_professors, details_section


app = FastAPI(
    title="UICourseAI API",
    version="0.1.0",
)

# 👇 CORS: allow local dev + GitHub Pages frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",          # Vite dev server
        "https://poojan-9603.github.io",  # GitHub Pages
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    message: str


class QueryResponse(BaseModel):
    used_llm: bool
    intent: dict
    results: list[dict]


@app.get("/")
def healthcheck():
    return {"status": "ok", "service": "uicourseai-api"}


@app.post("/api/query", response_model=QueryResponse)
def query_chat(req: QueryRequest):
    text = req.message.strip()

    # simple rule: use LLM for more natural / long questions
    use_llm = len(text) > 40 or any(
        w in text.lower()
        for w in ["prof", "professor", "chill", "recommend", "advisor"]
    )

    if use_llm:
        intent = parse_with_llm(text)
    else:
        intent = parse(text)

    # details view vs ranking
    if intent.get("details"):
        subj = intent.get("subject") or ""
        cnum = intent.get("class_num") or ""
        inst = intent.get("instructor_like") or ""
        rows = details_section(subj, cnum, inst)
    else:
        rows = rank_professors(intent, top_n=5)

    return QueryResponse(
        used_llm=use_llm,
        intent=intent,
        results=rows,
    )
