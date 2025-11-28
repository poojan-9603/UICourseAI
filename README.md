# UICourseAI

UICourseAI is an AI-powered course advisor for UIC students.  
You can ask things like:

- “easy 500-level ML class taught recently”
- “hard CS operating systems course”
- “chill data science class, I don’t want to die”

The app uses official UIC grade distribution data and an LLM to understand natural language and rank instructors/courses based on A% and D/F/W rates.

---

## Tech stack

- **Frontend:** React + TypeScript + Vite
- **Backend:** FastAPI (Python)
- **Data:** DuckDB + Parquet warehouse built from UIC grade distribution CSVs
- **AI / NLP:** OpenAI GPT model for intent parsing

---

## Features (MVP)

- Natural language queries for “easy” / “hard” courses
- Easy/Hard mode toggle
- Recency bias (prefers recent semesters)
- Results ranked by A% vs D/F/W%, with enrollment shown
- Nice UI card layout to compare instructors quickly

---

## Running locally

### 1. Backend (API)

```bash
cd project
python -m venv .venv
.venv\Scripts\activate     # on Windows

pip install -e .
uvicorn api.main:app --reload
