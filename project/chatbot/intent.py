# chatbot/intent.py
from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Dict, List, Optional

SUBJECT_CODES = {"CS", "MATH", "STAT", "ECE", "BIOE", "IE", "IDS", "DA", "DS"}  # extend as needed

POLARITY_MAP = {
    "easy": "easy",
    "easier": "easy",
    "lenient": "easy",
    "chill": "easy",
    "good": "easy",
    "hard": "hard",
    "strict": "hard",
    "tough": "hard",
}

# Supported keyword families we map to actions.py
KEYWORD_SYNONYMS = {
    "ml": {"ml", "machine", "learning", "machine-learning", "deep", "dl", "ai"},
    "ai": {"ai", "artificial", "intelligence"},
    "data": {"data", "mining", "analytics"},
    "nlp": {"nlp", "language", "text"},
    "query": {"query", "retrieval", "information-retrieval", "ir", "search"},
}

RECENT_TOKENS = {"recent", "latest", "new", "newer"}

DETAIL_TOKENS = {"details", "detail", "breakdown", "per-semester", "semester"}

@dataclass
class Intent:
    polarity: str = "easy"                     # "easy" or "hard"
    subject: Optional[str] = None              # ex: CS
    class_num: Optional[str] = None            # ex: 580
    keywords: List[str] = None                 # normalized keys: "ml","ai","data","nlp","query"
    recent: bool = False
    level: Optional[int] = None                # 500-level etc.
    instructor_like: Optional[str] = None
    explain: bool = False
    details: bool = False

    def to_dict(self) -> Dict:
        return {
            "polarity": self.polarity,
            "subject": self.subject,
            "class_num": self.class_num,
            "keywords": self.keywords or [],
            "recent": self.recent,
            "level": self.level,
            "instructor_like": self.instructor_like,
            "explain": self.explain,
            "details": self.details,
        }

def _tokenize(text: str) -> List[str]:
    # simple lowercase split; keep alphanum and dashes
    text = text.lower()
    return re.findall(r"[a-z0-9\-]+", text)

def _extract_subject(tokens: List[str]) -> Optional[str]:
    for t in tokens:
        if t.upper() in SUBJECT_CODES:
            return t.upper()
    return None

def _extract_class_num(tokens: List[str]) -> Optional[str]:
    for t in tokens:
        if t.isdigit():
            return t
        # handle 500-level phrasing like "500-level"
        if t.endswith("-level"):
            num = t.split("-")[0]
            if num.isdigit():
                return num
    return None

def _extract_level(tokens: List[str]) -> Optional[int]:
    # 500-level, 400-level, etc.
    for i, t in enumerate(tokens):
        if t.endswith("-level"):
            num = t.split("-")[0]
            if num.isdigit():
                return int(num)
        if t.isdigit() and i + 1 < len(tokens) and tokens[i+1] == "level":
            return int(t)
    return None

def _extract_polarity(tokens: List[str]) -> str:
    for t in tokens:
        if t in POLARITY_MAP:
            return POLARITY_MAP[t]
    return "easy"

def _extract_keywords(tokens: List[str]) -> List[str]:
    found = set()
    for t in tokens:
        for key, synonyms in KEYWORD_SYNONYMS.items():
            if t in synonyms:
                found.add(key)
    return list(found)

def _extract_recent(tokens: List[str]) -> bool:
    return any(t in RECENT_TOKENS for t in tokens)

def _extract_details(tokens: List[str]) -> bool:
    return any(t in DETAIL_TOKENS for t in tokens)

def _extract_instructor_like(text: str) -> Optional[str]:
    # crude heuristic: if user writes "details cs 580 yu" we’ll capture 'yu'
    # Grab a trailing word that isn’t a known token/number/subject
    tokens = _tokenize(text)
    garbage = set().union(
        RECENT_TOKENS, DETAIL_TOKENS,
        set(POLARITY_MAP.keys()),
        set().union(*KEYWORD_SYNONYMS.values()),
        {s.lower() for s in SUBJECT_CODES}, {"level"}
    )
    tail = [t for t in tokens if not t.isdigit() and t not in garbage]
    # If the last leftover token looks like a name fragment, return it
    return tail[-1] if tail else None

def parse(user_text: str) -> Dict:
    tokens = _tokenize(user_text)
    intent = Intent()
    intent.polarity = _extract_polarity(tokens)
    intent.subject = _extract_subject(tokens)
    intent.class_num = _extract_class_num(tokens)
    intent.level = _extract_level(tokens)
    intent.keywords = _extract_keywords(tokens)
    intent.recent = _extract_recent(tokens)
    intent.details = _extract_details(tokens)
    intent.explain = ("--explain" in user_text.lower()) or ("-explain" in user_text.lower())

    # instructor_like only when user likely asked details or gave a trailing name
    if intent.details or ("details" in tokens):
        intent.instructor_like = _extract_instructor_like(user_text)

    return intent.to_dict()
