# chatbot/intent_schema.py

from __future__ import annotations
from typing import Literal, List, Optional, TypedDict


Polarity = Literal["easy", "hard", "neutral"]
QueryType = Literal["rank", "details"]


class Intent(TypedDict, total=False):
    """
    Standard shape for how we represent a parsed user query.

    Both the rule-based parser and the future LLM-based parser
    should return a dict matching this schema.

    This keeps the rest of the system (rank_professors, CLI, UI)
    simple and stable.
    """

    # What kind of question is this?
    # - "rank"    : find easy / hard courses & instructors
    # - "details" : drill-down on a specific course + instructor
    query_type: QueryType

    # Optional course filters
    subject: Optional[str]          # e.g. "CS", "BME"
    class_num: Optional[str]        # e.g. "580"
    level: Optional[int]            # e.g. 500 for "500-level"

    # Semantic keywords extracted from the user's text
    # e.g. ["ml"], ["data"], ["ai"], ["nlp"], ["bio"]
    keywords: List[str]

    # How strict vs lenient the user wants:
    # - "easy"    : higher A%, lower D/F/W
    # - "hard"    : higher D/F/W, lower A%
    # - "neutral" : just list courses without ranking by difficulty (future)
    polarity: Polarity

    # Recency preference: if True, focus on more recent years.
    recent: bool

    # Optional instructor filter (partial match)
    instructor_like: Optional[str]

    # Optional list of instructors to avoid (can be empty for now)
    exclude_instructors: List[str]

    # How many rows to return (ranked). We'll default to 5 if missing.
    top_n: int

    # Whether the user asked for an explanation of how we interpreted
    # their question (“--explain”, “why these?”, etc.)
    explain: bool
