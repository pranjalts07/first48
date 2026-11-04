"""Build the DuckDB warehouse from raw collector files.

Raw JSONL files from the live and backfill folders are loaded as they are,
then the SQL models in sql/models run in name order. Each query in
sql/tests returns the rows that break a rule, so a test passes when it
returns nothing.

    python -m first48.warehouse
"""
import argparse
import sys
from pathlib import Path

import duckdb

SQL = Path(__file__).resolve().parent.parent / "sql"

RAW_TABLES = {
    "raw_new_pages": ("new_pages_*.jsonl", {
        "page_id": "BIGINT",
        "title": "VARCHAR",
        "t0": "VARCHAR",
        "source": "VARCHAR",
        "fetched_at": "VARCHAR",
    }),
    "raw_snapshots": ("snapshot_*.jsonl", {
        "page_id": "BIGINT",
        "taken_at": "VARCHAR",
        "exists": "BOOLEAN",
        "namespace": "INTEGER",
        "is_redirect": "BOOLEAN",
        "title": "VARCHAR",
        "last_rev_id": "BIGINT",
        "wikidata_item": "VARCHAR",
        "instance_of": "VARCHAR[]",
    }),
    "raw_views": ("views_*.jsonl", {
        "page_id": "BIGINT",
        "title": "VARCHAR",
        "fetched_at": "VARCHAR",
        "views": "MAP(VARCHAR, INTEGER)",
    }),
    "raw_edits": ("edits_*.jsonl", {
        "page_id": "BIGINT",
        "edits_d0": "INTEGER",
        "edits_48h": "INTEGER",
        "editors_48h": "INTEGER",
        "size_d0": "INTEGER",
        "size_d1": "INTEGER",
    }),
}


def load_raw(con, sources):
    for table, (pattern, columns) in RAW_TABLES.items():
        ddl = ", ".join(f'"{name}" {kind}' for name, kind in columns.items())
        con.execute(f"create or replace table {table} ({ddl}, filename varchar, dataset varchar)")
        for dataset, folder in sources.items():
            files = sorted(str(p) for p in Path(folder).glob(pattern))
            if files:
                con.execute(
                    f"insert into {table} select *, ? from read_json(?, columns={columns!r}, filename=true)",
                    [dataset, files],
                )


def run_models(con):
    seeds = SQL / "seeds" / "article_types.csv"
    con.execute(f"create or replace table seed_article_types as select * from read_csv('{seeds}')")
    for path in sorted((SQL / "models").glob("*.sql")):
        con.execute(path.read_text())


def run_tests(con):
    failures = []
    for path in sorted((SQL / "tests").glob("*.sql")):
        n = con.execute(f"select count(*) from ({path.read_text()})").fetchone()[0]
        if n:
            failures.append(f"{path.stem}: {n} rows")
    return failures


def build(db, sources):
    con = duckdb.connect(str(db))
    load_raw(con, sources)
    run_models(con)
    return con, run_tests(con)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/first48.duckdb"))
    parser.add_argument("--live", type=Path, default=Path("data/raw"))
    parser.add_argument("--backfill", type=Path, default=Path("data/backfill"))
    args = parser.parse_args()

    con, failures = build(args.db, {"live": args.live, "backfill": args.backfill})
    for table in ["raw_new_pages", "stg_new_pages", "stg_daily_views", "fct_articles", "fct_early_views"]:
        n = con.execute(f"select count(*) from {table}").fetchone()[0]
        print(f"{table}: {n:,} rows")
    # Plain CSV copy for the R analysis.
    con.execute(f"copy fct_articles to '{args.db.with_name('fct_articles.csv')}'")
    if failures:
        sys.exit("data tests failed:\n" + "\n".join(failures))
    print("all data tests passed")


if __name__ == "__main__":
    main()
