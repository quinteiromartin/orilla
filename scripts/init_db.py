from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import duckdb

DB_PATH = ROOT / "data" / "orilla.duckdb"
SCHEMA_PATH = ROOT / "scripts" / "schema.sql"


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with duckdb.connect(str(DB_PATH)) as con:
        con.execute(sql)
    print(f"Base inicializada: {DB_PATH}")


if __name__ == "__main__":
    main()
