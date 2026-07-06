from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "orilla.duckdb"
DEFAULT_JSON_PATH = ROOT / "imports" / "ventas_mobile" / "ventas_mobile_ejemplo.json"


@dataclass
class SaleCandidate:
    mobile_sale_uid: str
    sale_at: str
    sku: str
    product_label: str
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal
    gross_amount: Decimal
    net_amount: Decimal
    payment_method: str
    notes: str
    stock_snapshot_generated_at: str | None


@dataclass
class ReviewLine:
    sale: SaleCandidate
    status: str
    message: str
    product_name: str | None = None
    available_stock: int | None = None
    fifo_cost: Decimal | None = None
    margin: Decimal | None = None


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def parse_decimal(value: Any, field: str, index: int) -> Decimal:
    raw = clean_text(value).replace("$", "").replace(" ", "")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"Venta {index}: {field} no es numerico: {value!r}") from exc
    if parsed < 0:
        raise ValueError(f"Venta {index}: {field} no puede ser negativo")
    return parsed


def parse_quantity(value: Any, index: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Venta {index}: quantity debe ser entero: {value!r}") from exc
    if parsed <= 0:
        raise ValueError(f"Venta {index}: quantity debe ser mayor a cero")
    return parsed


def parse_sale_at(value: str, index: int) -> str:
    raw = clean_text(value)
    if not raw:
        raise ValueError(f"Venta {index}: sale_at es obligatorio")
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Venta {index}: sale_at no es fecha ISO valida: {raw!r}") from exc
    return raw


def load_sales(json_path: Path) -> list[SaleCandidate]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if payload.get("source") != "orilla_mobile_sales":
        raise ValueError("El JSON no parece ser una exportacion de Orilla Ventas")
    raw_sales = payload.get("sales")
    if not isinstance(raw_sales, list):
        raise ValueError("El JSON no tiene una lista `sales` valida")

    sales: list[SaleCandidate] = []
    seen_uids: set[str] = set()
    for index, raw in enumerate(raw_sales, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Venta {index}: registro invalido")

        mobile_sale_uid = clean_text(raw.get("mobile_sale_uid"))
        sku = clean_text(raw.get("sku"))
        payment_method = clean_text(raw.get("payment_method"))
        if not mobile_sale_uid:
            raise ValueError(f"Venta {index}: mobile_sale_uid es obligatorio")
        if mobile_sale_uid in seen_uids:
            raise ValueError(f"Venta {index}: mobile_sale_uid duplicado en el archivo")
        seen_uids.add(mobile_sale_uid)
        if not sku:
            raise ValueError(f"Venta {index}: sku es obligatorio")
        if not payment_method:
            raise ValueError(f"Venta {index}: payment_method es obligatorio")

        quantity = parse_quantity(raw.get("quantity"), index)
        unit_price = parse_decimal(raw.get("unit_price"), "unit_price", index)
        discount_amount = parse_decimal(raw.get("discount_amount", 0), "discount_amount", index)
        gross_amount = quantity * unit_price
        net_amount = gross_amount - discount_amount
        if net_amount < 0:
            raise ValueError(f"Venta {index}: el descuento supera el total bruto")

        sales.append(
            SaleCandidate(
                mobile_sale_uid=mobile_sale_uid,
                sale_at=parse_sale_at(raw.get("sale_at"), index),
                sku=sku,
                product_label=clean_text(raw.get("product_label")),
                quantity=quantity,
                unit_price=unit_price,
                discount_amount=discount_amount,
                gross_amount=gross_amount,
                net_amount=net_amount,
                payment_method=payment_method,
                notes=clean_text(raw.get("notes")),
                stock_snapshot_generated_at=clean_text(raw.get("stock_snapshot_generated_at")) or None,
            )
        )

    return sales


def money(value: Decimal | None) -> str:
    if value is None:
        return "-"
    return f"${value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def get_variant(con: duckdb.DuckDBPyConnection, sku: str) -> dict[str, Any] | None:
    row = con.execute(
        """
        SELECT
          variant_id,
          sku,
          product_name,
          color,
          size,
          CAST(available_stock AS INTEGER) AS available_stock
        FROM v_stock_current
        WHERE sku = ?
        """,
        [sku],
    ).fetchone()
    if not row:
        return None
    return {
        "variant_id": row[0],
        "sku": row[1],
        "product_name": row[2],
        "color": row[3],
        "size": row[4],
        "available_stock": int(row[5]),
    }


def get_payment_method_id(con: duckdb.DuckDBPyConnection, name: str) -> str | None:
    row = con.execute(
        "SELECT payment_method_id FROM payment_methods WHERE lower(name) = lower(?) AND active = TRUE",
        [name],
    ).fetchone()
    return row[0] if row else None


def existing_mobile_uid(con: duckdb.DuckDBPyConnection, uid: str) -> bool:
    row = con.execute("SELECT 1 FROM sales WHERE mobile_sale_uid = ?", [uid]).fetchone()
    return row is not None


def fifo_preview(con: duckdb.DuckDBPyConnection, variant_id: str, quantity: int) -> tuple[bool, Decimal]:
    rows = con.execute(
        """
        SELECT remaining_quantity, unit_cost
        FROM inventory_lots
        WHERE variant_id = ?
          AND remaining_quantity > 0
        ORDER BY received_date, created_at, lot_id
        """,
        [variant_id],
    ).fetchall()

    remaining = quantity
    cost = Decimal("0")
    for lot_qty, unit_cost in rows:
        take = min(remaining, int(lot_qty))
        cost += Decimal(take) * Decimal(str(unit_cost))
        remaining -= take
        if remaining == 0:
            break
    return remaining == 0, cost


def review_sales(con: duckdb.DuckDBPyConnection, sales: list[SaleCandidate]) -> list[ReviewLine]:
    review: list[ReviewLine] = []
    projected_stock: dict[str, int] = {}
    seen_uids: set[str] = set()

    for sale in sales:
        if sale.mobile_sale_uid in seen_uids:
            review.append(ReviewLine(sale, "ERROR", "UID duplicado en el archivo"))
            continue
        seen_uids.add(sale.mobile_sale_uid)

        if existing_mobile_uid(con, sale.mobile_sale_uid):
            review.append(ReviewLine(sale, "OMITIR", "Venta ya importada"))
            continue

        variant = get_variant(con, sale.sku)
        if not variant:
            review.append(ReviewLine(sale, "ERROR", "SKU inexistente"))
            continue

        payment_method_id = get_payment_method_id(con, sale.payment_method)
        if not payment_method_id:
            review.append(ReviewLine(sale, "ERROR", "Medio de cobro inexistente", variant["product_name"]))
            continue

        available = projected_stock.get(sale.sku, variant["available_stock"])
        if sale.quantity > available:
            review.append(
                ReviewLine(
                    sale=sale,
                    status="ERROR",
                    message="Stock disponible insuficiente",
                    product_name=variant["product_name"],
                    available_stock=available,
                )
            )
            continue

        has_fifo, fifo_cost = fifo_preview(con, variant["variant_id"], sale.quantity)
        if not has_fifo:
            review.append(
                ReviewLine(
                    sale=sale,
                    status="ERROR",
                    message="Lotes FIFO insuficientes",
                    product_name=variant["product_name"],
                    available_stock=available,
                )
            )
            continue

        projected_stock[sale.sku] = available - sale.quantity
        review.append(
            ReviewLine(
                sale=sale,
                status="OK",
                message="Lista para importar",
                product_name=variant["product_name"],
                available_stock=available,
                fifo_cost=fifo_cost,
                margin=sale.net_amount - fifo_cost,
            )
        )

    return review


def print_review(review: list[ReviewLine]) -> None:
    print("Revision de ventas mobile")
    print("=" * 80)
    for index, line in enumerate(review, start=1):
        sale = line.sale
        print(f"{index}. [{line.status}] {sale.mobile_sale_uid}")
        print(f"   SKU: {sale.sku} - {line.product_name or sale.product_label}")
        print(f"   Cantidad: {sale.quantity} | Neto: {money(sale.net_amount)} | Medio: {sale.payment_method}")
        if line.available_stock is not None:
            print(f"   Stock disponible previo: {line.available_stock}")
        if line.fifo_cost is not None:
            print(f"   Costo FIFO: {money(line.fifo_cost)} | Margen: {money(line.margin)}")
        print(f"   Estado: {line.message}")
    print("=" * 80)
    print(f"OK: {sum(1 for line in review if line.status == 'OK')}")
    print(f"Omitir: {sum(1 for line in review if line.status == 'OMITIR')}")
    print(f"Errores: {sum(1 for line in review if line.status == 'ERROR')}")


def allocate_fifo(
    con: duckdb.DuckDBPyConnection,
    sale_line_id: str,
    variant_id: str,
    quantity: int,
) -> Decimal:
    lots = con.execute(
        """
        SELECT lot_id, remaining_quantity, unit_cost
        FROM inventory_lots
        WHERE variant_id = ?
          AND remaining_quantity > 0
        ORDER BY received_date, created_at, lot_id
        """,
        [variant_id],
    ).fetchall()

    remaining = quantity
    total_cost = Decimal("0")
    for lot_id, lot_qty, unit_cost_raw in lots:
        if remaining == 0:
            break
        unit_cost = Decimal(str(unit_cost_raw))
        take = min(remaining, int(lot_qty))
        line_cost = Decimal(take) * unit_cost
        con.execute(
            """
            INSERT INTO inventory_allocations (sale_line_id, lot_id, quantity, unit_cost, total_cost)
            VALUES (?, ?, ?, ?, ?)
            """,
            [sale_line_id, lot_id, take, unit_cost, line_cost],
        )
        con.execute(
            """
            UPDATE inventory_lots
            SET remaining_quantity = remaining_quantity - ?
            WHERE lot_id = ?
            """,
            [take, lot_id],
        )
        total_cost += line_cost
        remaining -= take

    if remaining != 0:
        raise ValueError("Lotes FIFO insuficientes durante la importacion")

    return total_cost


def import_confirmed(con: duckdb.DuckDBPyConnection, review: list[ReviewLine], source_path: Path) -> int:
    ok_lines = [line for line in review if line.status == "OK"]
    if not ok_lines:
        return 0

    batch_id = con.execute(
        """
        INSERT INTO import_batches (source, source_path, status, reviewed_at)
        VALUES ('ventas_mobile', ?, 'confirmed', current_timestamp)
        RETURNING import_batch_id
        """,
        [str(source_path)],
    ).fetchone()[0]

    imported = 0
    for line in ok_lines:
        sale = line.sale
        variant = get_variant(con, sale.sku)
        if not variant:
            raise ValueError(f"SKU inexistente durante importacion: {sale.sku}")
        payment_method_id = get_payment_method_id(con, sale.payment_method)
        if not payment_method_id:
            raise ValueError(f"Medio de cobro inexistente durante importacion: {sale.payment_method}")

        sale_id = con.execute(
            """
            INSERT INTO sales (
              sale_date, source, status, gross_amount, discount_amount,
              net_amount, notes, mobile_sale_uid
            )
            VALUES (?, 'mobile', 'confirmed', ?, ?, ?, ?, ?)
            RETURNING sale_id
            """,
            [
                sale.sale_at,
                sale.gross_amount,
                sale.discount_amount,
                sale.net_amount,
                sale.notes,
                sale.mobile_sale_uid,
            ],
        ).fetchone()[0]

        sale_line_id = con.execute(
            """
            INSERT INTO sale_lines (
              sale_id, variant_id, quantity, unit_price, discount_amount,
              line_total, cogs_amount, margin_amount
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, 0)
            RETURNING sale_line_id
            """,
            [
                sale_id,
                variant["variant_id"],
                sale.quantity,
                sale.unit_price,
                sale.discount_amount,
                sale.net_amount,
            ],
        ).fetchone()[0]

        cogs = allocate_fifo(con, sale_line_id, variant["variant_id"], sale.quantity)
        margin = sale.net_amount - cogs
        con.execute(
            """
            UPDATE sale_lines
            SET cogs_amount = ?, margin_amount = ?
            WHERE sale_line_id = ?
            """,
            [cogs, margin, sale_line_id],
        )

        con.execute(
            """
            INSERT INTO sale_payments (sale_id, payment_method_id, amount, payment_date, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            [sale_id, payment_method_id, sale.net_amount, sale.sale_at, "Importado desde app mobile"],
        )
        con.execute(
            """
            INSERT INTO stock_movements (
              movement_date, variant_id, movement_type, quantity,
              reference_table, reference_id, external_ref, reason, notes
            )
            VALUES (?, ?, 'venta', ?, 'sales', ?, ?, 'Venta mobile', ?)
            """,
            [
                sale.sale_at,
                variant["variant_id"],
                -sale.quantity,
                sale_id,
                f"venta_mobile:{sale.mobile_sale_uid}",
                sale.product_label,
            ],
        )
        con.execute(
            """
            INSERT INTO cash_movements (
              movement_date, payment_method_id, movement_type, amount,
              reference_table, reference_id, notes
            )
            VALUES (?, ?, 'venta', ?, 'sales', ?, ?)
            """,
            [sale.sale_at, payment_method_id, sale.net_amount, sale_id, sale.product_label],
        )
        con.execute(
            """
            INSERT INTO audit_log (entity_table, entity_id, action, details)
            VALUES ('sales', ?, 'import_mobile_sale', ?)
            """,
            [
                sale_id,
                json.dumps(
                    {
                        "batch_id": str(batch_id),
                        "mobile_sale_uid": sale.mobile_sale_uid,
                        "source_path": str(source_path),
                    },
                    ensure_ascii=False,
                ),
            ],
        )
        imported += 1

    return imported


def run(json_path: Path, confirm: bool) -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"No existe la base: {DB_PATH}. Ejecutar primero scripts/init_db.py")
    if not json_path.exists():
        raise SystemExit(f"No existe el archivo: {json_path}")

    sales = load_sales(json_path)
    with duckdb.connect(str(DB_PATH)) as con:
        review = review_sales(con, sales)
        print_review(review)

        errors = [line for line in review if line.status == "ERROR"]
        if errors:
            raise SystemExit("Hay errores. Corregir el JSON o la base antes de importar.")

        if not confirm:
            print("Modo revision. Para importar, volver a correr con --confirmar.")
            return

        con.execute("BEGIN TRANSACTION")
        try:
            imported = import_confirmed(con, review, json_path)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

    print(f"Ventas importadas: {imported}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Revisa o importa ventas exportadas desde Orilla Ventas.")
    parser.add_argument(
        "--archivo",
        type=Path,
        default=DEFAULT_JSON_PATH,
        help=f"JSON exportado desde la app mobile. Default: {DEFAULT_JSON_PATH}",
    )
    parser.add_argument(
        "--confirmar",
        action="store_true",
        help="Impacta las ventas OK en DuckDB. Sin este flag solo revisa.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(args.archivo, args.confirmar)


if __name__ == "__main__":
    main()
