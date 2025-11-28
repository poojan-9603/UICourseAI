# UICourseAI — 2-minute demo script

1) What it is (10s)
- A tiny chatbot over UIC grade distributions (DuckDB warehouse).
- Answers “easiest/hardest” and lets you drill down by instructor.

2) Show 3 queries (60–80s)
- `easy cs 580`
- `show easy ml courses`
- `easy cs 580 recent --explain` (briefly show the rationale line)

3) Drilldown (20s)
- `details cs 580 yu` (recent semesters and distributions)

4) Wrap-up (20s)
- Tunable config (recency years, min enrollment).
- Next: thin web API → small UI.
