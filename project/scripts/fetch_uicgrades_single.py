import os
import requests
import pandas as pd

# --- Step 1: API base URL ---
BASE_URL = "https://uicgrades-api-adamnimer1.replit.app/api/specificCourse"

# --- Step 2: function to fetch one course ---
def fetch_course(subject, class_num):
    """
    Fetch one course's grade distribution from uicgrades API.
    Example: subject='CS', class_num='582'
    """
    # 1. Build URL with parameters
    params = {"subject": subject, "class_num": class_num}
    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()  # will stop if something fails

    data = response.json()["response"]

    # 2. Clean up small issues (like extra \r in semester)
    for row in data:
        if isinstance(row.get("semester"), str):
            row["semester"] = row["semester"].strip()

    # 3. Convert to DataFrame
    df = pd.DataFrame(data)

    return df

# --- Step 3: function to save CSV ---
def save_course_csv(df, subject, class_num):
    os.makedirs("data/raw", exist_ok=True)
    out_path = f"data/raw/{subject.upper()}_{class_num}.csv"
    df.to_csv(out_path, index=False)
    print(f"✅ Saved {len(df)} rows to {out_path}")

# --- Step 4: run the functions manually ---
if __name__ == "__main__":
    subject = input("Enter subject code (e.g., CS, MATH, STAT): ").strip().upper()
    class_num = input("Enter class number (e.g., 582): ").strip()

    df = fetch_course(subject, class_num)
    print(df.head())  # show first few rows
    save_course_csv(df, subject, class_num)
