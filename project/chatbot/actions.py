from typing import List, Dict, Optional
from pathlib import Path
import logging
import yaml
import duckdb
from datetime import datetime

log = logging.getLogger("chatbot.actions")

PROJECT_ROOT = Path(__file__).resolve().parents[1]

WAREHOUSE_DEFAULT = PROJECT_ROOT / "data" / "warehouse" / "grades_master.parquet"
CONFIG_PATH = PROJECT_ROOT / "config" / "app.yaml"


def _load_config() -> Dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


CFG = _load_config()
DEFAULT_RECENCY_YEARS = int(CFG.get("default_recency_years", 5))
MIN_ENROLLMENT = int(CFG.get("min_enrollment", 8))


def _base_query(warehouse: Path) -> str:
    """
    Compute rates on-the-fly. Note: source uses 'class_title' (not 'course_title').
    """
    return f"""
        SELECT
            subject,
            class_num,
            class_title,
            instructor,
            semester,
            total_students,
            CAST(A AS DOUBLE) AS A_raw,
            CAST(B AS DOUBLE) AS B_raw,
            CAST(C AS DOUBLE) AS C_raw,
            CAST(D AS DOUBLE) AS D_raw,
            CAST(F AS DOUBLE) AS F_raw,
            CAST(withdrawn AS DOUBLE) AS W_raw,
            CASE WHEN total_students > 0 THEN (A_raw / total_students) * 100 ELSE 0 END AS A_rate,
            CASE WHEN total_students > 0 THEN ((D_raw + F_raw + W_raw) / total_students) * 100 ELSE 0 END AS DFW_rate
        FROM '{warehouse.as_posix()}'
        WHERE total_students IS NOT NULL AND total_students > 0
    """


def _semester_year_sql() -> str:
    # Convert e.g., 'FA23' -> 2023, 'SP24' -> 2024
    return """
        CASE
            WHEN LENGTH(semester) = 4 AND TRY_CAST(SUBSTR(semester, 3, 2) AS INTEGER) IS NOT NULL
                THEN 2000 + CAST(SUBSTR(semester, 3, 2) AS INTEGER)
            ELSE NULL
        END
    """


def _escape_single_quotes(s: str) -> str:
    return s.replace("'", "''")


def _apply_filters(sql: str, params: Dict) -> str:
    clauses: List[str] = []

    if params.get("subject"):
        clauses.append(f"UPPER(subject) = '{params['subject'].upper()}'")
    if params.get("class_num"):
        clauses.append(f"class_num = '{params['class_num']}'")

    # level filter: e.g., 500-level -> 500..599
    if params.get("level"):
        lvl = int(params["level"])
        clauses.append(f"TRY_CAST(class_num AS INTEGER) BETWEEN {lvl} AND {lvl + 99}")

    # keywords: match in class_title
    kw = params.get("keywords") or []
    keyword_clause = []
    for k in kw:
        k_low = str(k).lower()
        if k_low == "ml":
            keyword_clause.append(
                "LOWER(class_title) LIKE '%machine%' OR LOWER(class_title) LIKE '%learning%' OR LOWER(class_title) LIKE '%ai%'"
            )
        elif k_low == "ai":
            keyword_clause.append("LOWER(class_title) LIKE '%artificial%' OR LOWER(class_title) LIKE '%intelligence%' OR LOWER(class_title) LIKE '%ai%'")
        elif k_low == "data":
            keyword_clause.append("LOWER(class_title) LIKE '%data%'")
        elif k_low in {"nlp", "language"}:
            keyword_clause.append("LOWER(class_title) LIKE '%language%' OR LOWER(class_title) LIKE '%nlp%' OR LOWER(class_title) LIKE '%text%'")
        elif k_low in {"query", "retrieval", "ir"}:
            keyword_clause.append("LOWER(class_title) LIKE '%query%' OR LOWER(class_title) LIKE '%retrieval%' OR LOWER(class_title) LIKE '%information%'")
    if keyword_clause:
        clauses.append("(" + " OR ".join(keyword_clause) + ")")

    # instructor partial
    inst = params.get("instructor_like")
    if inst:
        inst_escaped = _escape_single_quotes(inst.lower())
        clauses.append(f"LOWER(instructor) LIKE '%{inst_escaped}%'")

    # minimum enrollment unless user forced specific class_num
    if not params.get("class_num"):
        clauses.append(f"total_students >= {MIN_ENROLLMENT}")

    # recency window
    if params.get("recent"):
        year_now = datetime.now().year
        ybound = year_now - int(DEFAULT_RECENCY_YEARS)
        clauses.append(f"{_semester_year_sql()} >= {ybound}")

    if clauses:
        if "WHERE" in sql:
            sql += " AND " + " AND ".join(clauses)
        else:
            sql += " WHERE " + " AND ".join(clauses)

    return sql


def _order_clause(polarity: str) -> str:
    # tie-breakers: prefer more students, then newer semester
    if polarity == "hard":
        return f"ORDER BY DFW_rate DESC, A_rate ASC, total_students DESC, {_semester_year_sql()} DESC"
    return f"ORDER BY A_rate DESC, DFW_rate ASC, total_students DESC, {_semester_year_sql()} DESC"


def rank_professors(params: Dict, top_n: int = 5, warehouse_override: Optional[Path] = None) -> List[Dict]:
    """
    Return ranked sections (one row per section) respecting filters.
    """
    warehouse = warehouse_override or WAREHOUSE_DEFAULT
    if not warehouse.exists():
        log.warning("Warehouse not found at %s", warehouse)
        return []

    base = _base_query(warehouse)
    sql = _apply_filters(base, params)

    polarity = params.get("polarity", "easy")
    order = _order_clause(polarity)

    final_sql = f"""
        WITH ranked AS ({sql})
        SELECT
            subject,
            class_num,
            class_title,
            instructor,
            semester,
            CAST(A_rate AS DOUBLE) AS A_rate,
            CAST(DFW_rate AS DOUBLE) AS DFW_rate,
            CAST(total_students AS BIGINT) AS total_students
        FROM ranked
        {order}
        LIMIT {int(top_n)}
    """

    log.info("SQL:\\n%s", final_sql)
    con = duckdb.connect()
    try:
        df = con.execute(final_sql).df()  # small frame; pandas not required
    finally:
        con.close()

    return df.to_dict(orient="records")


def details_section(subject: str, class_num: str, instructor_like: str, warehouse_override: Optional[Path] = None) -> List[Dict]:
    """
    Drill-down table: semester-by-semester for an instructor.
    """
    warehouse = warehouse_override or WAREHOUSE_DEFAULT
    if not warehouse.exists():
        return []

    base = _base_query(warehouse)
    params = {
        "subject": subject,
        "class_num": class_num,
        "instructor_like": instructor_like,
    }
    sql = _apply_filters(base, params)

    final_sql = f"""
        WITH s AS ({sql})
        SELECT
            semester,
            subject,
            class_num,
            class_title,
            instructor,
            total_students,
            ROUND(A_rate, 1) AS A_rate,
            ROUND(DFW_rate, 1) AS DFW_rate
        FROM s
        ORDER BY {_semester_year_sql()} DESC
        LIMIT 20
    """
    con = duckdb.connect()
    try:
        df = con.execute(final_sql).df()
    finally:
        con.close()
    return df.to_dict(orient="records")
