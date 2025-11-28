# scripts/query_easiest_prof.py
import os
import sys
import pandas as pd

ANALYTICS_PATH = os.getenv("ANALYTICS_PATH", "data/analytics/grades_analytics.parquet")
WAREHOUSE_PATH = "data/warehouse/grades_master.parquet"

def load_any_parquet(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        print(f"⚠️ File not found: {path}")
        sys.exit(1)
    try:
        return pd.read_parquet(path)           # needs pyarrow (or fastparquet)
    except Exception as e:
        print(f"Failed to read {path}: {e}")
        sys.exit(1)

def main():
    # ---- Inputs ----
    subject = input("Subject (e.g., CS, MATH, STAT): ").strip().upper()
    class_num = input("Class number (e.g., 582): ").strip()
    term_filter = input("Term (e.g., FA23, SP24) or leave blank for ALL: ").strip().upper()

    # ---- Load analytics if available; otherwise fall back to warehouse and compute on the fly ----
    if os.path.exists(ANALYTICS_PATH):
        df = load_any_parquet(ANALYTICS_PATH)
    else:
        df = load_any_parquet(WAREHOUSE_PATH)

    # ---- Basic sanity columns (work with either analytics or warehouse) ----
    needed = {"subject","class_num","instructor","semester","A","B","C","D","F","withdrawn","total_students"}
    missing = needed - set(map(str, df.columns))
    if missing:
        print(f"⚠️ Missing columns in data: {sorted(missing)}")
        sys.exit(1)

    # Coerce types safely
    df["subject"] = df["subject"].astype(str).str.upper()
    df["class_num"] = df["class_num"].astype(str).str.strip()
    for col in ["A","B","C","D","F","withdrawn","total_students"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # ---- Filter to the course (+ optional term) ----
    mask = (df["subject"] == subject) & (df["class_num"] == class_num)
    if term_filter:
        mask &= (df["semester"].astype(str).str.upper() == term_filter)
    course = df.loc[mask].copy()

    if course.empty:
        print("😕 No rows match that course/term. Try a different term or check your inputs.")
        sys.exit(0)

    # ---- Aggregate by instructor (weighted by students) ----
    grouped = (
        course.groupby("instructor", dropna=False)[["A","B","C","D","F","withdrawn","total_students"]]
        .sum()
        .reset_index()
    )

    # Weighted rates
    grouped["A_rate"]  = (grouped["A"]  / grouped["total_students"] * 100).round(1)
    grouped["B_rate"]  = (grouped["B"]  / grouped["total_students"] * 100).round(1)
    grouped["C_rate"]  = (grouped["C"]  / grouped["total_students"] * 100).round(1)
    grouped["DFW_rate"] = ((grouped["D"] + grouped["F"] + grouped["withdrawn"]) / grouped["total_students"] * 100).round(1)

    # How many semesters did we observe per instructor (for context)
    sem_counts = course.groupby("instructor")["semester"].nunique().rename("semesters_observed")
    grouped = grouped.merge(sem_counts, on="instructor", how="left")

    # Rank by A_rate (highest first)
    out = grouped.sort_values(["A_rate","total_students"], ascending=[False, False])

    # Pretty print
    cols = ["instructor","total_students","semesters_observed","A_rate","B_rate","C_rate","DFW_rate"]
    print("\n📊 Easiest instructors (by %A, weighted by enrollment):")
    print(out[cols].to_string(index=False))

if __name__ == "__main__":
    main()
