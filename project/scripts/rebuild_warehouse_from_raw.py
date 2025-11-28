# scripts/rebuild_warehouse_from_raw.py

import os
from pathlib import Path
import duckdb

RAW_GLOB = "data/raw/*.csv"
WAREHOUSE_PATH = Path("data/warehouse/grades_master.parquet")

# 👇 EDIT THIS when you load a new term file
# Example: "FA24", "SP24", "FA23", etc.
TERM_CODE = "FA24"


def main():
    con = duckdb.connect()

    # 1) Read all CSVs in data/raw into a temporary table
    con.execute(
        f"""
        CREATE OR REPLACE TABLE grades_raw AS
        SELECT * FROM read_csv_auto(
            '{RAW_GLOB}',
            header := TRUE
        );
        """
    )

    # 2) Show columns so we can verify structure
    cols = con.execute("PRAGMA table_info('grades_raw')").fetchall()
    print("\n✅ Columns in grades_raw:\n")
    for i, row in enumerate(cols, start=1):
        # row = (cid, name, type, notnull, dflt_value, pk)
        print(f"{i:2d}. '{row[1]}'")

    # 3) Transform into our normalized warehouse schema
    con.execute(
        f"""
        CREATE OR REPLACE TABLE grades_clean AS
        SELECT
            UPPER(TRIM("CRS SUBJ CD"))                   AS subject,
            TRIM(CAST("CRS NBR" AS VARCHAR))             AS class_num,
            TRIM("CRS TITLE")                            AS class_title,
            TRIM(CAST("DEPT CD" AS VARCHAR))             AS dept_code,
            TRIM("DEPT NAME")                            AS dept_name,
            TRIM("Primary Instructor")                   AS instructor,

            -- All rows in this rebuild are for the same term
            '{TERM_CODE}'                                AS semester,

            -- grade buckets (coalesce nulls to 0)
            COALESCE("A",   0)                           AS A,
            COALESCE("B",   0)                           AS B,
            COALESCE("C",   0)                           AS C,
            COALESCE("D",   0)                           AS D,
            COALESCE("F",   0)                           AS F,
            COALESCE("ADV", 0)                           AS adv,
            COALESCE("CR",  0)                           AS credit,
            COALESCE("DFR", 0)                           AS deferred,
            COALESCE("I",   0)                           AS incomplete,
            COALESCE("NG",  0)                           AS non_graded,
            COALESCE("NR",  0)                           AS not_reported,
            COALESCE("O",   0)                           AS O,
            COALESCE("PR",  0)                           AS PR,
            COALESCE("S",   0)                           AS satisfactory,
            COALESCE("U",   0)                           AS unsatisfactory,
            COALESCE("W",   0)                           AS withdrawn,

            -- total students:
            -- prefer official Grade Regs, else sum grades
            COALESCE(
                "Grade Regs",
                COALESCE("A",   0) +
                COALESCE("B",   0) +
                COALESCE("C",   0) +
                COALESCE("D",   0) +
                COALESCE("F",   0) +
                COALESCE("ADV", 0) +
                COALESCE("CR",  0) +
                COALESCE("DFR", 0) +
                COALESCE("I",   0) +
                COALESCE("NG",  0) +
                COALESCE("NR",  0) +
                COALESCE("O",   0) +
                COALESCE("PR",  0) +
                COALESCE("S",   0) +
                COALESCE("U",   0) +
                COALESCE("W",   0)
            )                                            AS total_students

        FROM grades_raw;
        """
    )

    # 4) Export to Parquet warehouse
    os.makedirs(WAREHOUSE_PATH.parent, exist_ok=True)
    con.execute(
        f"""
        COPY grades_clean
        TO '{WAREHOUSE_PATH.as_posix()}'
        (FORMAT 'parquet');
        """
    )

    n = con.execute("SELECT COUNT(*) FROM grades_clean").fetchone()[0]
    print(
        f"\n✅ Warehouse rebuilt: {WAREHOUSE_PATH} "
        f"({n} rows, semester = '{TERM_CODE}')"
    )

    con.close()


if __name__ == "__main__":
    main()
