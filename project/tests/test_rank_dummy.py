from pathlib import Path
import duckdb
from chatbot.actions import rank_professors

def _make_dummy_parquet(tmp_path: Path) -> Path:
    out = tmp_path / "dummy.parquet"
    con = duckdb.connect()
    try:
        # tiny synthetic dataset (two sections)
        con.execute("""
            CREATE TABLE t AS
            SELECT * FROM (
                VALUES
                ('CS','580','Query Process Database Systms','Yu, Clement T','FA23',30, 17,7,4,1,0,1),
                ('CS','580','Query Process Database Systms','Sintos, Stavros','SP24',31, 28,3,0,0,0,0)
            ) AS v(subject,class_num,class_title,instructor,semester,total_students,A,B,C,D,F,withdrawn);
        """)
        con.execute(f"COPY t TO '{out.as_posix()}' (FORMAT PARQUET)")
    finally:
        con.close()
    return out

def test_rank_easy(tmp_path):
    pqt = _make_dummy_parquet(tmp_path)
    params = {"polarity":"easy","subject":"CS","class_num":"580"}
    rows = rank_professors(params, top_n=2, warehouse_override=pqt)
    assert len(rows) == 2
    # Easier first (Sintos)
    assert "Sintos" in rows[0]["instructor"]
