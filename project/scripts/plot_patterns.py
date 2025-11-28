import os
import pandas as pd
import matplotlib.pyplot as plt

# -------- 1) Ask which processed summary to plot ----------
# Example: if your earlier file was data/processed/summary_CS_582.csv
# enter: summary_CS_582.csv
filename = input("Enter processed summary filename (e.g., summary_CS_582.csv): ").strip()
if not filename.lower().endswith(".csv"):
    filename += ".csv"

file_path = filename if os.path.exists(filename) else os.path.join("data", "processed", filename)
if not os.path.exists(file_path):
    print(f"⚠️ File not found: {file_path}")
    raise SystemExit(1)

# -------- 2) Load data ----------
df = pd.read_csv(file_path)
if df.empty:
    print("⚠️ Processed summary file is empty.")
    raise SystemExit(1)

# Expected columns: instructor, A_pct, B_pct, C_pct, D_pct, F_pct, withdrawn_pct, Difficulty_Index
required = {"instructor", "A_pct", "B_pct", "C_pct", "D_pct", "F_pct", "withdrawn_pct", "Difficulty_Index"}
missing = required - set(df.columns)
if missing:
    print(f"⚠️ Missing expected columns in {file_path}: {sorted(missing)}")
    raise SystemExit(1)

# Ensure consistent order (already sorted by Difficulty in view script, but we enforce)
df = df.sort_values("Difficulty_Index", ascending=False).reset_index(drop=True)

# Make sure the output directory exists
os.makedirs("data/figures", exist_ok=True)

# A helper to build a green↔red color ramp from difficulty
def difficulty_colors(series):
    """
    Map Difficulty_Index (min = easiest, max = hardest) to a red→green gradient.
    Highest difficulty = more red; lowest = more green.
    """
    s = series.astype(float)
    if s.max() == s.min():
        # All the same difficulty -> use neutral gray
        return ["#888888"] * len(s)

    # Normalize 0..1 (0=easiest, 1=hardest)
    norm = (s - s.min()) / (s.max() - s.min())
    # Build hex colors by interpolating:
    # hard (1.0) -> red (#d62728), easy (0.0) -> green (#2ca02c)
    hard_rgb = (0xD6, 0x27, 0x28)
    easy_rgb = (0x2C, 0xA0, 0x2C)
    colors = []
    for v in norm:
        r = int(easy_rgb[0] + (hard_rgb[0] - easy_rgb[0]) * v)
        g = int(easy_rgb[1] + (hard_rgb[1] - easy_rgb[1]) * v)
        b = int(easy_rgb[2] + (hard_rgb[2] - easy_rgb[2]) * v)
        colors.append(f"#{r:02x}{g:02x}{b:02x}")
    return colors

# -------- 3) Plot: Difficulty Index by instructor ----------
instructors = df["instructor"].tolist()
diff_vals = df["Difficulty_Index"].tolist()
colors = difficulty_colors(df["Difficulty_Index"])

plt.figure(figsize=(12, 6))
bars = plt.bar(instructors, diff_vals, edgecolor="black", linewidth=0.6, color=colors)
plt.title("Difficulty Index by Instructor (higher = tougher)", pad=12)
plt.ylabel("Difficulty Index")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()

# Annotate bars with values
for b, v in zip(bars, diff_vals):
    plt.text(b.get_x() + b.get_width()/2, b.get_height() + 0.5, f"{v:.1f}", ha="center", va="bottom", fontsize=8)

fig1_path = os.path.join("data", "figures", f"{os.path.splitext(os.path.basename(file_path))[0]}_difficulty.png")
plt.savefig(fig1_path, dpi=150)
plt.close()
print(f"✅ Saved: {fig1_path}")

# -------- 4) Plot: A% by instructor ----------
a_vals = df["A_pct"].tolist()

plt.figure(figsize=(12, 6))
bars = plt.bar(instructors, a_vals, edgecolor="black", linewidth=0.6)
plt.title("A Percentage by Instructor", pad=12)
plt.ylabel("A (%)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()

for b, v in zip(bars, a_vals):
    plt.text(b.get_x() + b.get_width()/2, b.get_height() + 0.5, f"{v:.1f}%", ha="center", va="bottom", fontsize=8)

fig2_path = os.path.join("data", "figures", f"{os.path.splitext(os.path.basename(file_path))[0]}_A_pct.png")
plt.savefig(fig2_path, dpi=150)
plt.close()
print(f"✅ Saved: {fig2_path}")

print("\nDone. Open the images in data/figures/ to view the charts.")
