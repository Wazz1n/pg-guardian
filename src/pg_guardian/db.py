import psycopg
from psycopg.rows import dict_row

SCHEMA_SUMMARY_QUERY = """
    SELECT
        s.relname AS table_name,
        pg_size_pretty(pg_total_relation_size(s.relid)) AS total_size,
        s.n_live_tup AS estimated_rows,
        (
            SELECT COUNT(*)
            FROM pg_indexes i
            WHERE i.schemaname = s.schemaname
              AND i.tablename = s.relname
        ) AS index_count
    FROM pg_stat_user_tables s
    WHERE s.schemaname = %(schema)s
    ORDER BY pg_total_relation_size(s.relid) DESC, s.relname
"""


def get_schema_summary(dsn: str, schema: str = "public") -> list[dict]:
    """Return one row per table: name, size, estimated rows and index count.

    index_count includes the primary key index, so 0 means the table has
    neither a primary key nor any other index.
    """
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        conn.read_only = True
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SUMMARY_QUERY, {"schema": schema})
            return cur.fetchall()
