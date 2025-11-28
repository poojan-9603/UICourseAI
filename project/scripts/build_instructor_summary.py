import os
import pandas as pd

WAREHOUSE_PATH = os.path.join("data", "warehouse", "grades_master.parquet")
OUT_DIR = os.path.join("data", "analytics")
OUT_PARQUET = os.path.join(OUT_DIR, "instructor_summary.parquet")
OUT_CSV = os.path.join(OUT_DIR, "instructor_summary.csv")

def main():
    if not os.path.exists(WAREHOUSE_PATH):
        print(f"⚠️ Not found: {WAREHOUSE_PATH}")
        return

    df = pd.read_parquet(WAREHOUSE_PATH)
    if df.empty:
        print("⚠️ Warehouse is empty.")
        return

    # Expect these columns from your API/warehouse step:
    # subject, class_num, instructor, semester, total_students, A,B,C,D,F,withdrawn
    needed = ["subject","class_num","instructor","semester",
              "total_students","A","B","C","D","F","withdrawn"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        print(f"⚠️ Missing columns in warehouse: {missing}")
        return

    # Percent columns per section
    grade_cols = ["A","B","C","D","F","withdrawn"]
    for c in grade_cols:
        df[f"{c}_pct"] = (df[c] / df["total_students"]).replace([pd.NA, pd.NaT], 0) * 100

    # Aggregate per instructor+course
    agg = (
        df.groupby(["subject","class_num","instructor"], dropna=False)
          .agg(
              terms_taught=("semester","nunique"),
              sections=("semester","count"),
              students=("total_students","sum"),
              A_pct_avg=("A_pct","mean"),
              B_pct_avg=("B_pct","mean"),
              C_pct_avg=("C_pct","mean"),
              D_pct_avg=("D_pct","mean"),
              F_pct_avg=("F_pct","mean"),
              W_pct_avg=("withdrawn_pct","mean"),
              most_recent_term=("semester","max"),
          )
          .reset_index()
    )

    # Simple difficulty proxy (higher → harder)
    agg["Difficulty_Index"] = 100 - (agg["A_pct_avg"] + agg["B_pct_avg"])

    # Sort for convenience
    agg = agg.sort_values(["subject","class_num","Difficulty_Index"])

    os.makedirs(OUT_DIR, exist_ok=True)
    agg.to_parquet(OUT_PARQUET, index=False)
    agg.to_csv(OUT_CSV, index=False)

    # Small verification printout
    print(f"✅ Wrote {len(agg)} instructor rows → {OUT_PARQUET}")
    print("🔎 Preview:")
    preview_cols = ["subject","class_num","instructor","terms_taught",
                    "students","A_pct_avg","B_pct_avg","Difficulty_Index","most_recent_term"]
    print(agg[preview_cols].head(10).to_string(index=False, float_format=lambda x: f'{x:.1f}'))

if __name__ == "__main__":
    main()
