# chatbot/llm_intent.py

"""
LLM-backed intent parser.

Goal: take a natural-language query like:
    "easy 500-level ML courses recent --explain"

and turn it into the SAME intent dict that chatbot.intent.parse() returns, e.g.:

{
    "polarity": "easy",
    "subject": None,
    "class_num": None,
    "keywords": ["ml"],
    "recent": True,
    "level": 500,
    "instructor_like": None,
    "explain": True,
    "details": False,
}

So the rest of the code (actions.py, main_cli.py) can work unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
import json
import os

from openai import OpenAI

# ---------------------------
# 1) Intent dataclass (same shape as our rule-based parser)
# ---------------------------


@dataclass
class Intent:
    polarity: str = "easy"                 # "easy" or "hard"
    subject: Optional[str] = None          # e.g. "CS"
    class_num: Optional[str] = None        # e.g. "580"
    keywords: List[str] = None             # ["ml", "data", "nlp", ...]
    recent: bool = False                   # "recent", "last few years"
    level: Optional[int] = None            # 400, 500, etc.
    instructor_like: Optional[str] = None  # partial instructor name
    explain: bool = False                  # ask for reasoning/explanation
    details: bool = False                  # ask for section-by-section breakdown

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # avoid None list
        if d["keywords"] is None:
            d["keywords"] = []
        return d


# ---------------------------
# 2) System prompt + JSON schema
# ---------------------------

SYSTEM_PROMPT = """
You are an intent parser for a course-selection assistant for UIC.

You NEVER answer the question directly. Your ONLY job is to convert
the user's text into a structured JSON intent object.

JSON FIELDS (all keys must be present):

- polarity: "easy" or "hard"
    "easier", "chill", "lenient", "safe bet" → "easy"
    "strict", "hard", "tough", "challenging" → "hard"
    If unclear, default to "easy".

- subject: subject code like "CS", "STAT", "ECE".
    If the user mentions a subject (e.g., "cs", "stat"),
    normalize to uppercase. If none, use null.

- class_num: course number as a string, e.g. "580", "418".
    If user doesn't specify exactly, use null.

- keywords: list of lowercase tags from:
    ["ml", "data", "nlp", "ai", "bio", "stats", "systems", "theory"]
    Map user language to these:
        - "machine learning", "ml", "deep learning" → "ml"
        - "data", "data science", "database", "big data" → "data"
        - "nlp", "language", "text" → "nlp"
        - "ai", "artificial intelligence" → "ai"
        - "bio", "biomed", "biomedical", "medical" → "bio"
        - "stats", "statistics", "probability" → "stats"
        - "systems", "os", "operating systems", "networks" → "systems"
        - "theory", "algorithms", "complexity" → "theory"
    If nothing fits, use [].

- recent: boolean.
    true if the user mentions "recent", "last few years",
    "modern", "current profs", or a recent range. Otherwise false.

- level: integer or null.
    If the user says "500-level", use 500.
    If "400-level", use 400.
    If they give an explicit course number like 580,
       you may leave level null (class_num will carry it).
    If not specified, use null.

- instructor_like: partial instructor name as lowercase string,
    e.g. "yu" or "sintos".
    If the user mentions a prof name, set this to a short substring.
    Otherwise null.

- explain: boolean.
    true if the user asks "why", "explain", "show reasoning",
    "--explain", etc. Otherwise false.

- details: boolean.
    true if the user asks for semester-by-semester detail,
    history, trend, "show all semesters", or "--details".
    Otherwise false.

You MUST output ONLY a JSON object, no extra text, no markdown,
no explanations.
"""

# ---------------------------
# 3) Prompt builder
# ---------------------------


def build_prompt(user_text: str) -> str:
    """
    Build the user-facing part of the prompt.
    The system message explains the schema; this adds examples and the actual text.
    """
    examples = [
        {
            "user": "easy cs 580 recent",
            "intent": {
                "polarity": "easy",
                "subject": "CS",
                "class_num": "580",
                "keywords": [],
                "recent": True,
                "level": None,
                "instructor_like": None,
                "explain": False,
                "details": False,
            },
        },
        {
            "user": "hard 500-level ml classes",
            "intent": {
                "polarity": "hard",
                "subject": None,
                "class_num": None,
                "keywords": ["ml"],
                "recent": False,
                "level": 500,
                "instructor_like": None,
                "explain": False,
                "details": False,
            },
        },
        {
            "user": "show easy data cs courses --explain",
            "intent": {
                "polarity": "easy",
                "subject": "CS",
                "class_num": None,
                "keywords": ["data"],
                "recent": False,
                "level": None,
                "instructor_like": None,
                "explain": True,
                "details": False,
            },
        },
        {
            "user": "details for cs 580 yu",
            "intent": {
                "polarity": "easy",
                "subject": "CS",
                "class_num": "580",
                "keywords": [],
                "recent": False,
                "level": None,
                "instructor_like": "yu",
                "explain": False,
                "details": True,
            },
        },
    ]

    examples_text = "\n\n".join(
        [
            f"User: {ex['user']}\nIntent JSON: {json.dumps(ex['intent'])}"
            for ex in examples
        ]
    )

    return f"""
Here are examples of how to map natural language to intent JSON:

{examples_text}

Now parse this new user query into an intent JSON:

User: {user_text}
Intent JSON:
""".strip()


# ---------------------------
# 4) Helpers: client + JSON extraction + normalization
# ---------------------------


def _get_client() -> OpenAI:
    """
    Create an OpenAI client.
    Requires OPENAI_API_KEY in the environment.
    """
    # If OPENAI_API_KEY is not set, OpenAI() will raise an error when used.
    return OpenAI()


def _extract_json(text: str) -> str:
    """
    Be defensive: sometimes models wrap JSON with text.
    We take the substring between the first '{' and the last '}'.
    """
    if not text:
        return "{}"
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return "{}"
    return text[start : end + 1]


def _normalize_intent_dict(data: Dict[str, Any], original_text: str) -> Intent:
    """
    Take raw dict from the model and enforce types + defaults,
    so the rest of the app can rely on it.
    """

    text_lower = original_text.lower()

    polarity = str(data.get("polarity") or "").lower()
    if polarity not in ("easy", "hard"):
        # simple heuristic fallback
        if "hard" in text_lower or "strict" in text_lower:
            polarity = "hard"
        else:
            polarity = "easy"

    subject = data.get("subject")
    if isinstance(subject, str) and subject.strip():
        subject = subject.upper().strip()
    else:
        subject = None

    class_num = data.get("class_num")
    if isinstance(class_num, (int, float)):
        class_num = str(int(class_num))
    elif isinstance(class_num, str):
        class_num = class_num.strip() or None
    else:
        class_num = None

    raw_keywords = data.get("keywords") or []
    if not isinstance(raw_keywords, list):
        raw_keywords = []
    keywords: List[str] = []
    for k in raw_keywords:
        if not isinstance(k, str):
            continue
        k = k.lower().strip()
        if k in {"ml", "data", "nlp", "ai", "bio", "stats", "systems", "theory"}:
            keywords.append(k)
    # dedupe
    keywords = sorted(set(keywords))

    recent = bool(data.get("recent"))

    level = data.get("level")
    if isinstance(level, (int, float)):
        level = int(level)
    else:
        level = None

    instr = data.get("instructor_like")
    if isinstance(instr, str) and instr.strip():
        instructor_like = instr.strip().lower()
    else:
        instructor_like = None

    explain = bool(data.get("explain"))
    details = bool(data.get("details"))

    return Intent(
        polarity=polarity,
        subject=subject,
        class_num=class_num,
        keywords=keywords,
        recent=recent,
        level=level,
        instructor_like=instructor_like,
        explain=explain,
        details=details,
    )


# ---------------------------
# 5) Main entry: parse_with_llm()
# ---------------------------


def parse_with_llm(
    user_text: str,
    model: str = "gpt-4.1-mini",
) -> Dict[str, Any]:
    """
    Call the LLM and return an intent dict matching chatbot.intent.parse().

    Usage example (later):

        from chatbot.llm_intent import parse_with_llm
        intent = parse_with_llm("easy data cs recent --explain")
        results = rank_professors(intent)

    """
    client = _get_client()
    prompt = build_prompt(user_text)

    resp = client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    content = resp.choices[0].message.content or ""
    json_str = _extract_json(content)

    try:
        raw = json.loads(json_str)
    except Exception:
        raw = {}

    intent_obj = _normalize_intent_dict(raw, original_text=user_text)
    return intent_obj.to_dict()
