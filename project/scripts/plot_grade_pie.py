# scripts/plot_grade_pie.py
import os
import re
import pandas as pd
import matplotlib.pyplot as plt

WAREHOUSE_PATH = "data/warehouse/grades_master.parquet"
OUT_DIR = "reports/figures"

def sanitize(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", s.strip())
    return s.strip("_") or "unknown"

def load():
    if not os.path.exists(WAREHOUSE_PATH):
        raise SystemExit(f"⚠️ Missing {WAREHOUSE_PATH}. Run the warehouse step first.")
    try:
        return pd.read_parquet(WAREHOUSE_PATH)
    except Exception as e:
        raise SystemExit(f"Could not read {WAREHOUSE_PATH}: {e}")

def main():
    df = load()

    subject = input("Subject (e.g., CS): ").strip().upper()
    class_num = input("Class number (e.g., 580): ").strip()
    instructor = input("Instructor (full or partial, e.g., Yu): ").strip()
    term = input("Term (e.g., FA23) or leave blank for ALL: ").strip().upper()

    # basic filters
    mask = (df["subject"].astype(str).str.upper() == subject) & \
           (df["class_num"].astype(str).str.strip() == class_num)

    if term:
        mask &= (df["semester"].astype(str).str.upper() == term)

    if instructor:
        mask &= df["instructor"].astype(str).str.contains(instructor, case=False, na=False)

    course = df.loc[mask].copy()
    if course.empty:
        print("😕 No matching rows. Check inputs.")
        return

    # sum across matching sections
    numeric = ["A","B","C","D","F","withdrawn","total_students"]
    for col in numeric:
        course[col] = pd.to_numeric(course[col], errors="coerce").fillna(0).astype(int)
    agg = course[numeric].sum()

    # prepare pie
    labels = ["A","B","C","D","F","Withdrawn"]
    values = [agg["A"], agg["B"], agg["C"], agg["D"], agg["F"], agg["withdrawn"]]
    total = sum(values)
    if total == 0:
        print("No students in selection.")
        return

    # plot
    plt.figure()
    plt.pie(values, labels=[f"{l} ({v})" for l,v in zip(labels, values)],
            autopct=lambda p: f"{p:.1f}%")
    title_parts = [f"{subject} {class_num}"]
    if instructor: title_parts.append(instructor)
    if term: title_parts.append(term)
    plt.title(" • ".join(title_parts))

    # save
    os.makedirs(OUT_DIR, exist_ok=True)
    fname = f"{sanitize(subject)}_{sanitize(class_num)}"
    if instructor: fname += f"_{sanitize(instructor)}"
    if term: fname += f"_{sanitize(term)}"
    out_path = os.path.join(OUT_DIR, f"{fname}.png")
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    print(f"✅ Saved pie chart -> {out_path}")

if __name__ == "__main__":
    main()
