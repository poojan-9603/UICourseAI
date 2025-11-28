import os
import pandas as pd

# --- Step 1: ask the user which file to verify ---
# You can type either just the filename (like CS_582.csv)
# or the full path (like data/raw/CS_582.csv)
filename = input("Enter CSV filename to verify (e.g., CS_582.csv): ").strip()

# --- Step 2: build the full path ---
if not filename.lower().endswith(".csv"):
    filename += ".csv"

# Assume files live in data/raw by default
file_path = filename if os.path.exists(filename) else os.path.join("data", "raw", filename)

# --- Step 3: check if file exists ---
if not os.path.exists(file_path):
    print(f"⚠️ File not found: {file_path}")
    exit()

# --- Step 4: load CSV ---
try:
    df = pd.read_csv(file_path)
except Exception as e:
    print(f"❌ Failed to read CSV: {e}")
    exit()

# --- Step 5: show quick info ---
print(f"\n✅ Loaded {len(df)} rows from {file_path}")
print("\n📋 Columns in this CSV:")
print(df.columns.tolist())
print("\n🔍 Sample data:")
print(df.head(3).to_string(index=False))

# --- Step 6: check for missing values ---
missing_values = df.isnull().sum()
if missing_values.any():
    print("\n⚠️ Missing values detected:")
    print(missing_values[missing_values > 0])
else:
    print("\n✅ No missing values detected.")

# --- Step 7: confirm expected structure ---
expected_columns = [
    "subject","class_num","class_title","dept_code","dept_name",
    "A","B","C","D","F","adv","credit","deferred","incomplete",
    "non_graded","not_reported","O","PR","satisfactory","unsatisfactory",
    "withdrawn","instructor","total_students","semester"
]

missing_cols = [c for c in expected_columns if c not in df.columns]
extra_cols = [c for c in df.columns if c not in expected_columns]

if not missing_cols and not extra_cols:
    print("\n✅ Column structure looks correct.")
else:
    if missing_cols:
        print(f"\n⚠️ Missing columns: {missing_cols}")
    if extra_cols:
        print(f"⚠️ Extra/unexpected columns: {extra_cols}")
