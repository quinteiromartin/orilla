from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "orilla.duckdb"


def main() -> None:
    parser = argparse.ArgumentParser(description="Muestra stock, movimientos y ventas de un producto.")
    parser.add_argument("texto", help="Texto a buscar en nombre de producto o SKU")
    args = parser.parse_args()

    pattern = f"%{args.texto.lower()}%"
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        print("STOCK ACTUAL")
        print(
            con.execute(
                """
                SELECT sku, product_name, color, size, physical_stock, reserved_stock, available_stock
                FROM v_stock_current
                WHERE lower(product_name) LIKE ?
                   OR lower(sku) LIKE ?
                ORDER BY sku
                """,
                [pattern, pattern],
            ).fetchdf().to_string(index=False)
        )
        print("\nMOVIMIENTOS")
        print(
            con.execute(
                """
                SELECT
                  sm.movement_date,
                  pv.sku,
                  p.name AS product_name,
                  pv.color,
                  pv.size,
                  sm.movement_type,
                  sm.quantity,
                  sm.reason,
                  sm.notes
                FROM stock_movements sm
                JOIN product_variants pv ON pv.variant_id = sm.variant_id
                JOIN products p ON p.product_id = pv.product_id
                WHERE lower(p.name) LIKE ?
                   OR lower(pv.sku) LIKE ?
                ORDER BY sm.movement_date, sm.created_at
                """,
                [pattern, pattern],
            ).fetchdf().to_string(index=False)
        )
        print("\nVENTAS")
        print(
            con.execute(
                """
                SELECT
                  s.sale_date,
                  s.mobile_sale_uid,
                  pv.sku,
                  p.name AS product_name,
                  sl.quantity,
                  sl.line_total,
                  sl.cogs_amount,
                  sl.margin_amount
                FROM sales s
                JOIN sale_lines sl ON sl.sale_id = s.sale_id
                JOIN product_variants pv ON pv.variant_id = sl.variant_id
                JOIN products p ON p.product_id = pv.product_id
                WHERE lower(p.name) LIKE ?
                   OR lower(pv.sku) LIKE ?
                ORDER BY s.sale_date
                """,
                [pattern, pattern],
            ).fetchdf().to_string(index=False)
        )


if __name__ == "__main__":
    main()

