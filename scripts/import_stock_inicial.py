from __future__ import annotations

import csv
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "orilla.duckdb"
DEFAULT_CSV_PATH = ROOT / "imports" / "stock_inicial" / "stock_inicial.csv"

REQUIRED_COLUMNS = {
    "producto",
    "color",
    "talle",
    "precio_sugerido",
    "stock_inicial",
    "costo_unitario_inicial",
}


def clean_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def parse_decimal(value: str, field: str, row_number: int) -> Decimal:
    raw = clean_text(value).replace("$", "").replace(" ", "")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"Fila {row_number}: {field} no es numerico: {value!r}") from exc
    if parsed < 0:
        raise ValueError(f"Fila {row_number}: {field} no puede ser negativo")
    return parsed


def parse_int(value: str, field: str, row_number: int) -> int:
    raw = clean_text(value)
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ValueError(f"Fila {row_number}: {field} no es entero: {value!r}") from exc
    if parsed < 0:
        raise ValueError(f"Fila {row_number}: {field} no puede ser negativo")
    return parsed


def normalize_key(*parts: str) -> str:
    joined = "|".join(clean_text(part).casefold() for part in parts)
    return re.sub(r"\s+", " ", joined)


def next_sku(con: duckdb.DuckDBPyConnection) -> str:
    value = con.execute("SELECT nextval('seq_product_variant')").fetchone()[0]
    return f"ORI-{int(value):06d}"


def get_or_create_product(con: duckdb.DuckDBPyConnection, name: str) -> str:
    existing = con.execute(
        "SELECT product_id FROM products WHERE lower(name) = lower(?)",
        [name],
    ).fetchone()
    if existing:
        return existing[0]

    return con.execute(
        "INSERT INTO products (name) VALUES (?) RETURNING product_id",
        [name],
    ).fetchone()[0]


def get_or_create_variant(
    con: duckdb.DuckDBPyConnection,
    product_id: str,
    color: str,
    size: str,
    default_price: Decimal,
) -> tuple[str, str]:
    existing = con.execute(
        """
        SELECT variant_id, sku
        FROM product_variants
        WHERE product_id = ?
          AND coalesce(lower(color), '') = coalesce(lower(?), '')
          AND coalesce(lower(size), '') = coalesce(lower(?), '')
        """,
        [product_id, color or None, size or None],
    ).fetchone()
    if existing:
        con.execute(
            """
            UPDATE product_variants
            SET default_price = ?, updated_at = current_timestamp
            WHERE variant_id = ?
            """,
            [default_price, existing[0]],
        )
        return existing[0], existing[1]

    sku = next_sku(con)
    row = con.execute(
        """
        INSERT INTO product_variants (product_id, sku, color, size, default_price)
        VALUES (?, ?, ?, ?, ?)
        RETURNING variant_id, sku
        """,
        [product_id, sku, color or None, size or None, default_price],
    ).fetchone()
    return row[0], row[1]


def load_rows(csv_path: Path) -> list[dict[str, object]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError("El CSV no tiene encabezados")

        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Faltan columnas obligatorias: {', '.join(sorted(missing))}")

        rows = []
        seen_keys: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            product = clean_text(row.get("producto"))
            color = clean_text(row.get("color"))
            size = clean_text(row.get("talle"))
            if not product:
                raise ValueError(f"Fila {row_number}: producto es obligatorio")

            key = normalize_key(product, color, size)
            if key in seen_keys:
                raise ValueError(f"Fila {row_number}: producto/variante duplicado en el CSV")
            seen_keys.add(key)

            rows.append(
                {
                    "row_number": row_number,
                    "product": product,
                    "color": color,
                    "size": size,
                    "default_price": parse_decimal(row.get("precio_sugerido", ""), "precio_sugerido", row_number),
                    "initial_stock": parse_int(row.get("stock_inicial", ""), "stock_inicial", row_number),
                    "initial_unit_cost": parse_decimal(
                        row.get("costo_unitario_inicial", ""),
                        "costo_unitario_inicial",
                        row_number,
                    ),
                }
            )

    return rows


def import_stock(csv_path: Path) -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"No existe la base: {DB_PATH}. Ejecutar primero scripts/init_db.py")
    if not csv_path.exists():
        raise SystemExit(f"No existe el CSV: {csv_path}")

    rows = load_rows(csv_path)
    imported = 0
    skipped_existing_stock = 0

    with duckdb.connect(str(DB_PATH)) as con:
        con.execute("BEGIN TRANSACTION")
        try:
            for row in rows:
                product_id = get_or_create_product(con, row["product"])
                variant_id, sku = get_or_create_variant(
                    con,
                    product_id,
                    row["color"],
                    row["size"],
                    row["default_price"],
                )

                external_ref = f"stock_inicial:{sku}"
                already_loaded = con.execute(
                    """
                    SELECT 1
                    FROM stock_movements
                    WHERE movement_type = 'stock_inicial'
                      AND external_ref = ?
                    """,
                    [external_ref],
                ).fetchone()
                if already_loaded:
                    skipped_existing_stock += 1
                    continue

                quantity = int(row["initial_stock"])
                unit_cost = row["initial_unit_cost"]
                if quantity > 0:
                    con.execute(
                        """
                        INSERT INTO stock_movements (
                          movement_date, variant_id, movement_type, quantity,
                          external_ref, reason, notes
                        )
                        VALUES (current_timestamp, ?, 'stock_inicial', ?, ?, 'Carga inicial', ?)
                        """,
                        [
                            variant_id,
                            quantity,
                            external_ref,
                            f"Importado desde {csv_path.name}, fila {row['row_number']}",
                        ],
                    )
                    con.execute(
                        """
                        INSERT INTO inventory_lots (
                          variant_id, external_ref, received_date, original_quantity,
                          remaining_quantity, unit_cost
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        [variant_id, external_ref, date.today(), quantity, quantity, unit_cost],
                    )
                imported += 1
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

    print(f"Filas leidas: {len(rows)}")
    print(f"Variantes importadas/actualizadas: {imported}")
    print(f"Stock inicial ya existente omitido: {skipped_existing_stock}")


def main() -> None:
    import_stock(DEFAULT_CSV_PATH)


if __name__ == "__main__":
    main()
