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
class SaleItem:
    sku: str
    product_label: str
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal
    line_total: Decimal


@dataclass
class SaleCandidate:
    mobile_sale_uid: str
    sale_at: str
    payment_method: str
    notes: str
    gross_amount: Decimal
    discount_amount: Decimal
    net_amount: Decimal
    stock_snapshot_generated_at: str | None
    items: list[SaleItem]


@dataclass
class ItemReview:
    item: SaleItem
    status: str
    message: str
    product_name: str | None = None
    available_stock: int | None = None
    fifo_cost: Decimal | None = None


@dataclass
class SaleReview:
    sale: SaleCandidate
    status: str
    message: str
    item_reviews: list[ItemReview]
    fifo_cost: Decimal = Decimal("0")
    margin: Decimal = Decimal("0")


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


def parse_sale_at(value: Any, index: int) -> str:
    raw = clean_text(value)
    if not raw:
        raise ValueError(f"Venta {index}: sale_at es obligatorio")
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Venta {index}: sale_at no es fecha ISO valida: {raw!r}") from exc
    return raw


def normalize_items(raw: dict[str, Any], index: int) -> list[SaleItem]:
    raw_items = raw.get("items")
    if raw_items is None:
        raw_items = [
            {
                "sku": raw.get("sku"),
                "product_label": raw.get("product_label"),
                "quantity": raw.get("quantity"),
                "unit_price": raw.get("unit_price"),
                "discount_amount": raw.get("discount_amount", 0),
                "line_total": raw.get("net_amount", raw.get("line_total", 0)),
            }
        ]

    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError(f"Venta {index}: items debe ser una lista no vacia")

    items: list[SaleItem] = []
    for item_index, item in enumerate(raw_items, start=1):
        sku = clean_text(item.get("sku"))
        if not sku:
            raise ValueError(f"Venta {index}, item {item_index}: sku es obligatorio")
        quantity = parse_quantity(item.get("quantity"), index)
        unit_price = parse_decimal(item.get("unit_price"), "unit_price", index)
        discount = parse_decimal(item.get("discount_amount", 0), "discount_amount", index)
        expected_total = quantity * unit_price - discount
        if expected_total < 0:
            raise ValueError(f"Venta {index}, item {item_index}: descuento supera total")
        line_total = parse_decimal(item.get("line_total", expected_total), "line_total", index)
        if abs(line_total - expected_total) > Decimal("0.01"):
            line_total = expected_total
        items.append(
            SaleItem(
                sku=sku,
                product_label=clean_text(item.get("product_label")),
                quantity=quantity,
                unit_price=unit_price,
                discount_amount=discount,
                line_total=line_total,
            )
        )
    return items


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
        payment_method = clean_text(raw.get("payment_method"))
        if not mobile_sale_uid:
            raise ValueError(f"Venta {index}: mobile_sale_uid es obligatorio")
        if mobile_sale_uid in seen_uids:
            raise ValueError(f"Venta {index}: mobile_sale_uid duplicado en el archivo")
        seen_uids.add(mobile_sale_uid)
        if not payment_method:
            raise ValueError(f"Venta {index}: payment_method es obligatorio")

        items = normalize_items(raw, index)
        gross_amount = sum((item.quantity * item.unit_price for item in items), Decimal("0"))
        item_discounts = sum((item.discount_amount for item in items), Decimal("0"))
        sale_discount = parse_decimal(raw.get("discount_amount", 0), "discount_amount", index)
        net_amount = gross_amount - item_discounts - sale_discount
        if net_amount < 0:
            raise ValueError(f"Venta {index}: descuento supera total bruto")

        raw_net = raw.get("net_amount")
        if raw_net is not None:
            declared_net = parse_decimal(raw_net, "net_amount", index)
            if abs(declared_net - net_amount) > Decimal("0.01"):
                net_amount = declared_net

        sales.append(
            SaleCandidate(
                mobile_sale_uid=mobile_sale_uid,
                sale_at=parse_sale_at(raw.get("sale_at"), index),
                payment_method=payment_method,
                notes=clean_text(raw.get("notes")),
                gross_amount=gross_amount,
                discount_amount=item_discounts + sale_discount,
                net_amount=net_amount,
                stock_snapshot_generated_at=clean_text(raw.get("stock_snapshot_generated_at")) or None,
                items=items,
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
        SELECT variant_id, sku, product_name, color, size, CAST(available_stock AS INTEGER)
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
    return con.execute("SELECT 1 FROM sales WHERE mobile_sale_uid = ?", [uid]).fetchone() is not None


def fifo_preview(con: duckdb.DuckDBPyConnection, variant_id: str, quantity: int) -> tuple[bool, Decimal]:
    rows = con.execute(
        """
        SELECT remaining_quantity, unit_cost
        FROM inventory_lots
        WHERE variant_id = ? AND remaining_quantity > 0
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


def review_sales(con: duckdb.DuckDBPyConnection, sales: list[SaleCandidate]) -> list[SaleReview]:
    reviews: list[SaleReview] = []
    projected_stock: dict[str, int] = {}
    seen_uids: set[str] = set()

    for sale in sales:
        item_reviews: list[ItemReview] = []
        fifo_cost = Decimal("0")
        status = "OK"
        message = "Lista para importar"

        if sale.mobile_sale_uid in seen_uids:
            reviews.append(SaleReview(sale, "ERROR", "UID duplicado en el archivo", []))
            continue
        seen_uids.add(sale.mobile_sale_uid)

        if existing_mobile_uid(con, sale.mobile_sale_uid):
            reviews.append(SaleReview(sale, "OMITIR", "Venta ya importada", []))
            continue

        if not get_payment_method_id(con, sale.payment_method):
            reviews.append(SaleReview(sale, "ERROR", "Medio de cobro inexistente", []))
            continue

        for item in sale.items:
            variant = get_variant(con, item.sku)
            if not variant:
                status = "ERROR"
                item_reviews.append(ItemReview(item, "ERROR", "SKU inexistente"))
                continue

            available = projected_stock.get(item.sku, variant["available_stock"])
            if item.quantity > available:
                status = "ERROR"
                item_reviews.append(
                    ItemReview(item, "ERROR", "Stock disponible insuficiente", variant["product_name"], available)
                )
                continue

            has_fifo, item_cost = fifo_preview(con, variant["variant_id"], item.quantity)
            if not has_fifo:
                status = "ERROR"
                item_reviews.append(ItemReview(item, "ERROR", "Lotes FIFO insuficientes", variant["product_name"], available))
                continue

            projected_stock[item.sku] = available - item.quantity
            fifo_cost += item_cost
            item_reviews.append(ItemReview(item, "OK", "OK", variant["product_name"], available, item_cost))

        if status == "ERROR":
            message = "Hay errores en lineas de la venta"
        reviews.append(SaleReview(sale, status, message, item_reviews, fifo_cost, sale.net_amount - fifo_cost))
    return reviews


def print_review(reviews: list[SaleReview]) -> None:
    print("Revision de ventas mobile")
    print("=" * 80)
    for index, review in enumerate(reviews, start=1):
        sale = review.sale
        print(f"{index}. [{review.status}] {sale.mobile_sale_uid}")
        print(f"   Items: {len(sale.items)} | Neto: {money(sale.net_amount)} | Medio: {sale.payment_method}")
        if review.status == "OK":
            print(f"   Costo FIFO: {money(review.fifo_cost)} | Margen: {money(review.margin)}")
        print(f"   Estado: {review.message}")
        for item_review in review.item_reviews:
            item = item_review.item
            print(f"   - [{item_review.status}] {item.sku} {item.product_label}")
            print(f"     Cantidad: {item.quantity} | Total linea: {money(item.line_total)}")
            if item_review.available_stock is not None:
                print(f"     Stock disponible previo: {item_review.available_stock}")
            if item_review.fifo_cost is not None:
                print(f"     Costo FIFO linea: {money(item_review.fifo_cost)}")
            if item_review.message != "OK":
                print(f"     {item_review.message}")
    print("=" * 80)
    print(f"OK: {sum(1 for line in reviews if line.status == 'OK')}")
    print(f"Omitir: {sum(1 for line in reviews if line.status == 'OMITIR')}")
    print(f"Errores: {sum(1 for line in reviews if line.status == 'ERROR')}")


def allocate_fifo(con: duckdb.DuckDBPyConnection, sale_line_id: str, variant_id: str, quantity: int) -> Decimal:
    lots = con.execute(
        """
        SELECT lot_id, remaining_quantity, unit_cost
        FROM inventory_lots
        WHERE variant_id = ? AND remaining_quantity > 0
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
            "UPDATE inventory_lots SET remaining_quantity = remaining_quantity - ? WHERE lot_id = ?",
            [take, lot_id],
        )
        total_cost += line_cost
        remaining -= take
    if remaining != 0:
        raise ValueError("Lotes FIFO insuficientes durante la importacion")
    return total_cost


def import_confirmed(con: duckdb.DuckDBPyConnection, reviews: list[SaleReview], source_path: Path) -> int:
    ok_reviews = [review for review in reviews if review.status == "OK"]
    if not ok_reviews:
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
    for review in ok_reviews:
        sale = review.sale
        payment_method_id = get_payment_method_id(con, sale.payment_method)
        if not payment_method_id:
            raise ValueError(f"Medio de cobro inexistente: {sale.payment_method}")

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

        for item in sale.items:
            variant = get_variant(con, item.sku)
            if not variant:
                raise ValueError(f"SKU inexistente durante importacion: {item.sku}")
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
                    item.quantity,
                    item.unit_price,
                    item.discount_amount,
                    item.line_total,
                ],
            ).fetchone()[0]
            cogs = allocate_fifo(con, sale_line_id, variant["variant_id"], item.quantity)
            con.execute(
                "UPDATE sale_lines SET cogs_amount = ?, margin_amount = ? WHERE sale_line_id = ?",
                [cogs, item.line_total - cogs, sale_line_id],
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
                    -item.quantity,
                    sale_id,
                    f"venta_mobile:{sale.mobile_sale_uid}:{item.sku}",
                    item.product_label,
                ],
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
            INSERT INTO cash_movements (
              movement_date, payment_method_id, movement_type, amount,
              reference_table, reference_id, notes
            )
            VALUES (?, ?, 'venta', ?, 'sales', ?, ?)
            """,
            [sale.sale_at, payment_method_id, sale.net_amount, sale_id, sale.mobile_sale_uid],
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
                        "items": len(sale.items),
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
        reviews = review_sales(con, sales)
        print_review(reviews)
        if any(review.status == "ERROR" for review in reviews):
            raise SystemExit("Hay errores. Corregir el JSON o la base antes de importar.")
        if not confirm:
            print("Modo revision. Para importar, volver a correr con --confirmar.")
            return
        con.execute("BEGIN TRANSACTION")
        try:
            imported = import_confirmed(con, reviews, json_path)
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
    parser.add_argument("--confirmar", action="store_true", help="Impacta las ventas OK en DuckDB.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(args.archivo, args.confirmar)


if __name__ == "__main__":
    main()
