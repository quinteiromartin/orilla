from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "orilla.duckdb"
WAL_PATH = ROOT / "data" / "orilla.duckdb.wal"
BACKUPS_DIR = ROOT / "backups"
SCHEMA_PATH = ROOT / "scripts" / "schema.sql"


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_path(original: Path, stamp: str) -> Path:
    return BACKUPS_DIR / f"{original.stem}_{stamp}{original.suffix}"


def init_db() -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(DB_PATH)) as con:
        con.execute(sql)


def run(confirmar: bool) -> None:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = timestamp()
    existing = [path for path in (DB_PATH, WAL_PATH) if path.exists()]

    if not confirmar:
        print("Modo revision. No se modifica nada.")
        if existing:
            print("Se haria backup de:")
            for path in existing:
                print(f"- {path} -> {backup_path(path, stamp)}")
        else:
            print("No existe base previa para backupear.")
        print("Luego se recrearia la base vacia desde scripts/schema.sql.")
        print("Para ejecutar realmente, usar --confirmar.")
        return

    for path in existing:
        destino = backup_path(path, stamp)
        shutil.copy2(path, destino)
        path.unlink()
        print(f"Backup creado: {destino}")

    init_db()
    print(f"Base reiniciada: {DB_PATH}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hace backup de la base DuckDB actual y crea una base vacia nueva."
    )
    parser.add_argument(
        "--confirmar",
        action="store_true",
        help="Ejecuta el reset. Sin este flag solo muestra lo que haria.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(confirmar=args.confirmar)


if __name__ == "__main__":
    main()

