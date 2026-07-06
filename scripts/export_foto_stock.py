from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
import duckdb

DB_PATH = ROOT / "data" / "orilla.duckdb"
EXPORT_PATH = ROOT / "exports" / "foto_stock.json"


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"No existe la base: {DB_PATH}. Ejecutar primero scripts/init_db.py")

    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        rows = con.execute(
            """
            SELECT
              sku,
              product_name AS producto,
              color,
              size AS talle,
              CAST(default_price AS DOUBLE) AS precio_sugerido,
              CAST(physical_stock AS INTEGER) AS stock_fisico,
              CAST(reserved_stock AS INTEGER) AS stock_reservado,
              CAST(available_stock AS INTEGER) AS stock_disponible
            FROM v_stock_current
            WHERE available_stock > 0
            ORDER BY product_name, color, size, sku
            """
        ).fetchall()
        columns = [desc[0] for desc in con.description]

    productos = [dict(zip(columns, row)) for row in rows]
    payload = {
        "version": 1,
        "generado_en": datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).isoformat(timespec="seconds"),
        "productos": productos,
    }

    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exportado: {EXPORT_PATH} ({len(productos)} productos disponibles)")


if __name__ == "__main__":
    main()
