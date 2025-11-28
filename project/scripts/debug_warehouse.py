# scripts/debug_warehouse.py
from pathlib import Path
import duckdb
import pandas as pd

WAREHOUSE = Path("data/warehouse/grades_master.parquet")

if not WAREHOUSE.exists():
    print("❌ Warehouse not found:", WAREHOUSE)
    raise SystemExit(1)

con = duckdb.connect()
try:
    print("✅ Found warehouse. Schema:\n")
    df_schema = con.execute(f"DESCRIBE SELECT * FROM '{WAREHOUSE.as_posix()}' LIMIT 0").df()
    print(df_schema.to_string(index=False))

    print("\nSample rows:\n")
    sample = con.execute(f"SELECT * FROM '{WAREHOUSE.as_posix()}' LIMIT 5").df()
    print(sample)
finally:
    con.close()
