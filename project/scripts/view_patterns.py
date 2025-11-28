# scripts/view_pattern.py
from pathlib import Path
import duckdb
import argparse
import pandas as pd

WAREHOUSE = Path("data/warehouse/grades_master.parquet")

def show_pattern(subject: str, class_num: str, instructor: str):
    con = duckdb.connect()
    sql = f"""
        SELECT
            semester,
            subject,
            class_num,
            class_title,
            instructor,
            total_students,
            ROUND((A * 100.0 / total_students), 1) AS A_pct,
            ROUND(((D + F + withdrawn) * 100.0 / total_students), 1) AS DFW_pct
        FROM '{WAREHOUSE.as_posix()}'
        WHERE UPPER(subject) = '{subject.upper()}'
          AND class_num = '{class_num}'
          AND LOWER(instructor) LIKE '%{instructor.lower()}%'
        ORDER BY semester DESC
    """
    df = con.execute(sql).df()
    con.close()
    if df.empty:
        print("No matching rows.")
    else:
        print(f"\n📊 {subject} {class_num} — {df.iloc[0]['class_title']} ({instructor})")
        print(df.to_string(index=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Show per-semester grade trends for a course/instructor.")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--class_num", required=True)
    parser.add_argument("--instructor", required=True)
    args = parser.parse_args()
    show_pattern(args.subject, args.class_num, args.instructor)
