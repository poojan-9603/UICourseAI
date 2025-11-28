# chatbot/nlu_rules.py
import re
from typing import Dict, List, Optional

EASY_WORDS = {"easy", "easiest", "lenient", "chill", "good"}
HARD_WORDS = {"hard", "strict", "tough", "difficult"}

SUBJECT_PATTERN = re.compile(r"\b([A-Z]{2,5})\b")
CLASSNUM_PATTERN = re.compile(r"\b(\d{3,4})\b")

def parse_user_text(text: str) -> Dict:
    t = text.lower().strip()

    # intent: for MVP everything is a ranking request
    intent = "rank_professors"

    # polarity: easy vs hard (default to easy if none)
    polarity = "easy"
    if any(w in t for w in HARD_WORDS):
        polarity = "hard"
    elif any(w in t for w in EASY_WORDS):
        polarity = "easy"

    # subject and class number extraction (e.g., "cs 580")
    subject: Optional[str] = None
    class_num: Optional[str] = None

    # try to find patterns like "cs 580" or "cs580"
    compact = re.findall(r"\b([A-Z]{2,5})\s*-?\s*(\d{3,4})\b", text, flags=re.I)
    if compact:
        subject = compact[0][0].upper()
        class_num = compact[0][1]
    else:
        # fallback: separate captures
        sub = SUBJECT_PATTERN.findall(text.upper())
        num = CLASSNUM_PATTERN.findall(text)
        # keep it conservative: only accept subject if it looks like “CS”, “STAT”...
        if sub:
            # pick the first that is likely a subject
            for candidate in sub:
                if candidate.isalpha() and len(candidate) <= 5:
                    subject = candidate.upper()
                    break
        if num:
            class_num = num[0]

    # keywords (for things like "ml", "machine learning", "data")
    keywords: List[str] = []
    if "ml" in t or "machine learning" in t:
        keywords.append("ml")
    if "data" in t:
        keywords.append("data")

    # term: keep out for now (MVP = any term)
    return {
        "intent": intent,
        "polarity": polarity,
        "subject": subject,
        "class_num": class_num,
        "keywords": keywords,
    }
