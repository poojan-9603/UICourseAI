import re
import sys
from pathlib import Path
import pandas as pd

WAREHOUSE_PATH = Path("data/warehouse/grades_master.parquet")

# ---- Heuristics / knobs you can tweak later ----
ML_KEYWORDS = [
    "machine", "ml", "learning", "neural", "deep", "data mining",
    "data science", "ai", "artificial intelligence", "pattern recognition",
    "statistical learning", "analytics"
]
RECENT_TERM_REGEX = re.compile(r"^(FA|SP|SU)\d{2}$", re.I)  # e.g., FA23

def load_warehouse(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"⚠️ Warehouse not found at {path}. Run the merge step first.")
        sys.exit(1)
    df = pd.read_parquet(path)
    # normalize
    for c in ["subject", "class_title", "instructor", "semester"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str).str.strip()
    if "total_students" in df.columns:
        df["total_students"] = pd.to_numeric(df["total_students"], errors="coerce").fillna(0).astype(int)
    # guard: keep sensible rows
    df = df[df.get("total_students", 0) > 0].copy()
    return df

def add_rate_columns(df: pd.DataFrame) -> pd.DataFrame:
    # compute per-row rates
    for col in ["A","B","C","D","F","withdrawn"]:
        if col not in df.columns:
            df[col] = 0
    denom = df["total_students"].replace(0, pd.NA)
    for g in ["A","B","C","D","F","withdrawn"]:
        df[f"{g}_rate"] = (df[g] / denom * 100).astype(float)
    df["DFW_rate"] = df[["D_rate","F_rate","withdrawn_rate"]].sum(axis=1)  # crude “difficulty”
    return df

def parse_query(q: str):
    ql = q.lower()

    want_ml = any(k in ql for k in ML_KEYWORDS)
    want_easy = any(k in ql for k in ["easy", "lenient", "high a", "grade friendly"])
    want_hard = "hard" in ql or "strict" in ql

    # subject filter like "subject=CS" or "CS only"
    m_sub = re.search(r"\bsubject\s*=\s*([A-Za-z]{2,4})\b", q)
    subject = m_sub.group(1).upper() if m_sub else None
    if not subject:
        m_cs = re.search(r"\b([A-Za-z]{2,4})\b", q)
        # only accept as subject if explicitly hinted like "in CS" or "for CS"
        if m_cs and re.search(rf"\b(in|for)\s+{m_cs.group(1)}\b", ql):
            subject = m_cs.group(1).upper()

    # course number if present (“580”, “CS 580”)
    m_num = re.search(r"\b(\d{3})\b", q)
    class_num = m_num.group(1) if m_num else None

    # term filter (optional), e.g., “FA23”, “SP24”
    m_term = re.search(r"\b(FA|SP|SU)\d{2}\b", q, flags=re.I)
    term = m_term.group(0).upper() if m_term else None

    topk = 10
    m_top = re.search(r"\btop\s+(\d{1,2})\b", ql)
    if m_top:
        try: topk = max(3, min(20, int(m_top.group(1))))
        except: pass

    return dict(
        want_ml=want_ml,
        want_easy=want_easy,
        want_hard=want_hard,
        subject=subject,
        class_num=class_num,
        term=term,
        topk=topk,
    )

def filter_df(df: pd.DataFrame, intent: dict) -> pd.DataFrame:
    out = df.copy()
    if intent["subject"]:
        out = out[out["subject"].str.upper() == intent["subject"]]
    if intent["class_num"]:
        out = out[out["class_num"].astype(str) == intent["class_num"]]
    if intent["term"]:
        out = out[out["semester"].str.upper() == intent["term"]]
    if intent["want_ml"]:
        title_mask = out["class_title"].str.lower()
        ml_mask = pd.Series(False, index=out.index)
        for kw in ML_KEYWORDS:
            ml_mask |= title_mask.str.contains(rf"\b{re.escape(kw)}\b", regex=True)
        out = out[ml_mask]
    return out

def rank_instructors(df: pd.DataFrame, topk: int, prefer_easy=True) -> pd.DataFrame:
    """
    Aggregate by (subject, class_num, class_title, instructor) and rank.
    prefer_easy=True => higher A_rate and lower DFW_rate.
    """
    if df.empty:
        return df

    grp_cols = ["subject","class_num","class_title","instructor"]
    agg = (
        df.groupby(grp_cols)
          .agg(
              total_students=("total_students","sum"),
              semesters=("semester","nunique"),
              A_rate=("A_rate","mean"),
              B_rate=("B_rate","mean"),
              C_rate=("C_rate","mean"),
              DFW_rate=("DFW_rate","mean"),
          )
          .reset_index()
    )

    # simple scoring
    if prefer_easy:
        agg["score"] = agg["A_rate"] * 1.0 - agg["DFW_rate"] * 0.7
    else:
        agg["score"] = agg["DFW_rate"] * 1.0 - agg["A_rate"] * 0.5

    # quality guardrails
    agg = agg[agg["total_students"] >= 20]  # avoid ultra tiny sections
    agg = agg.sort_values(["score","A_rate"], ascending=False).head(topk)
    return agg

def format_rows(rows: pd.DataFrame) -> str:
    if rows.empty:
        return "No matching results. Try adding/removing subject, course number, or term."
    lines = []
    for _, r in rows.iterrows():
        line = (
            f"{r['subject']} {r['class_num']} — {r['class_title']} | "
            f"Instructor: {r['instructor']} | "
            f"A≈{r['A_rate']:.1f}%  DFW≈{r['DFW_rate']:.1f}% | "
            f"Students: {int(r['total_students'])} | "
            f"Semesters: {int(r['semesters'])}"
        )
        lines.append(line)
    return "\n".join(lines)

def answer(df: pd.DataFrame, q: str) -> str:
    intent = parse_query(q)
    filt = filter_df(df, intent)

    if intent["want_hard"]:
        ranked = rank_instructors(filt, intent["topk"], prefer_easy=False)
        header = "💪 Strict/Harder picks (higher D/F/W, lower A%):"
    else:
        ranked = rank_instructors(filt, intent["topk"], prefer_easy=True)
        header = "😌 Easier/lenient picks (higher A%, lower D/F/W):"

    return header + "\n" + format_rows(ranked)

def main():
    df = load_warehouse(WAREHOUSE_PATH)
    df = add_rate_columns(df)
    print("🤖 Chatbot MVP ready. Ask things like:")
    print('  - "show easy ml courses"')
    print('  - "easy ml in CS"')
    print('  - "easiest instructor for CS 580"')
    print('  - "strict ml in SP24"')
    print('  - "top 5 easy ml subject=STAT"')
    print("Type 'exit' to quit.\n")

    while True:
        try:
            q = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye!")
            break
        if not q or q.lower() in {"exit","quit"}:
            print("bye!")
            break
        print(answer(df, q), "\n")

if __name__ == "__main__":
    main()
