# scripts/plot_one.py
from pathlib import Path
import duckdb
import matplotlib.pyplot as plt
import argparse

WAREHOUSE = Path("data/warehouse/grades_master.parquet")

def fetch_data(subject: str, class_num: str, instructor: str):
    con = duckdb.connect()
    sql = f"""
        SELECT
            subject, class_num, class_title, instructor, semester,
            A, B, C, D, F, withdrawn, total_students
        FROM '{WAREHOUSE.as_posix()}'
        WHERE UPPER(subject) = '{subject.upper()}'
          AND class_num = '{class_num}'
          AND LOWER(instructor) LIKE '%{instructor.lower()}%'
        ORDER BY semester DESC
        LIMIT 1
    """
    df = con.execute(sql).df()
    con.close()
    return df

def plot_pie(df):
    if df.empty:
        print("No matching course found.")
        return

    row = df.iloc[0]
    grades = ["A", "B", "C", "D", "F", "withdrawn"]
    counts = [row[g] for g in grades]
    title = f"{row['subject']} {row['class_num']} — {row['class_title']}\n{row['instructor']} ({row['semester']})"

    plt.figure(figsize=(6, 6))
    plt.pie(counts, labels=grades, autopct='%1.1f%%', startangle=90)
    plt.title(title)
    plt.tight_layout()

    out_dir = Path("plots")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{row['subject']}_{row['class_num']}_{row['instructor'].split()[0]}_{row['semester']}.png"
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"✅ Saved pie chart to {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot grade distribution for a course/instructor.")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--class_num", required=True)
    parser.add_argument("--instructor", required=True)
    args = parser.parse_args()

    df = fetch_data(args.subject, args.class_num, args.instructor)
    plot_pie(df)
