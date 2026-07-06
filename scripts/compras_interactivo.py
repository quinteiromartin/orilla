from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "orilla.duckdb"
COMPROBANTES_DIR = ROOT / "comprobantes" / "compras"
TESSERACT_EXE = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")

try:
    import pytesseract

    if TESSERACT_EXE.exists():
        pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_EXE)
except ImportError:
    pytesseract = None


@dataclass
class LineaCompra:
    nombre_en_comprobante: str
    producto: str
    color: str
    talle: str
    cantidad: int
    costo_unitario: Decimal
    precio_sugerido: Decimal

    @property
    def subtotal(self) -> Decimal:
        return q(self.costo_unitario * self.cantidad)


@dataclass
class CompraInteractiva:
    fecha: date
    proveedor: str
    medio_pago: str
    comprobante: str | None = None
    costo_directo: Decimal = Decimal("0")
    notas: str = ""
    lineas: list[LineaCompra] = field(default_factory=list)

    @property
    def subtotal(self) -> Decimal:
        return q(sum((linea.subtotal for linea in self.lineas), Decimal("0")))

    @property
    def total(self) -> Decimal:
        return q(self.subtotal + self.costo_directo)


def q(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def decimal(value: Any, nombre: str = "valor") -> Decimal:
    if isinstance(value, Decimal):
        parsed = value
    else:
        raw = str(value).strip().replace("$", "").replace(" ", "")
        if "," in raw and "." in raw:
            raw = raw.replace(".", "").replace(",", ".")
        elif "," in raw:
            raw = raw.replace(",", ".")
        try:
            parsed = Decimal(raw)
        except InvalidOperation as exc:
            raise ValueError(f"{nombre} no es numerico: {value!r}") from exc
    if parsed < 0:
        raise ValueError(f"{nombre} no puede ser negativo")
    return q(parsed)


def listar_comprobantes() -> list[Path]:
    COMPROBANTES_DIR.mkdir(parents=True, exist_ok=True)
    extensiones = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}
    return sorted(path for path in COMPROBANTES_DIR.iterdir() if path.suffix.lower() in extensiones)


def mostrar_comprobante(nombre_o_path: str | Path, ancho: int = 12) -> Image.Image:
    path = resolver_comprobante(nombre_o_path)
    img = Image.open(path)
    try:
        import matplotlib.pyplot as plt

        alto = max(6, ancho * img.height / max(img.width, 1))
        plt.figure(figsize=(ancho, alto))
        plt.imshow(img)
        plt.axis("off")
        plt.title(path.name)
        plt.show()
    except Exception:
        pass
    return img


def idiomas_ocr() -> list[str]:
    if pytesseract is None:
        raise RuntimeError("pytesseract no esta instalado en este Python")
    return pytesseract.get_languages(config="")


def leer_texto_comprobante(nombre_o_path: str | Path, lang: str | None = None) -> str:
    if pytesseract is None:
        raise RuntimeError("pytesseract no esta instalado en este Python")
    if lang is None:
        disponibles = set(idiomas_ocr())
        lang = "spa+eng" if "spa" in disponibles else "eng"
    path = resolver_comprobante(nombre_o_path)
    img = Image.open(path)
    texto = pytesseract.image_to_string(img, lang=lang)
    print(texto)
    return texto


def resolver_comprobante(nombre_o_path: str | Path) -> Path:
    path = Path(nombre_o_path)
    if not path.is_absolute():
        path = COMPROBANTES_DIR / path
    if not path.exists():
        raise FileNotFoundError(f"No existe el comprobante: {path}")
    return path


def nueva_compra(
    fecha: str | date,
    proveedor: str,
    medio_pago: str,
    comprobante: str | Path | None = None,
    costo_directo: Any = 0,
    notas: str = "",
) -> CompraInteractiva:
    if isinstance(fecha, str):
        fecha_parseada = date.fromisoformat(fecha)
    else:
        fecha_parseada = fecha

    comprobante_path = str(resolver_comprobante(comprobante)) if comprobante else None
    return CompraInteractiva(
        fecha=fecha_parseada,
        proveedor=limpiar(proveedor),
        medio_pago=limpiar(medio_pago),
        comprobante=comprobante_path,
        costo_directo=decimal(costo_directo, "costo_directo"),
        notas=limpiar(notas),
    )


def agregar_linea(
    compra: CompraInteractiva,
    nombre_en_comprobante: str,
    producto: str,
    color: str,
    talle: str,
    cantidad: int,
    costo_unitario: Any,
    precio_sugerido: Any,
) -> CompraInteractiva:
    if cantidad <= 0:
        raise ValueError("cantidad debe ser mayor a cero")
    compra.lineas.append(
        LineaCompra(
            nombre_en_comprobante=limpiar(nombre_en_comprobante),
            producto=limpiar(producto),
            color=limpiar(color),
            talle=limpiar(talle),
            cantidad=int(cantidad),
            costo_unitario=decimal(costo_unitario, "costo_unitario"),
            precio_sugerido=decimal(precio_sugerido, "precio_sugerido"),
        )
    )
    return compra


def revisar_compra(compra: CompraInteractiva) -> pd.DataFrame:
    validar_compra(compra)
    filas = []
    for idx, linea in enumerate(compra.lineas, start=1):
        costo_directo = prorratear_costo_directo(compra, linea)
        efectivo_unitario = q((linea.subtotal + costo_directo) / linea.cantidad)
        filas.append(
            {
                "linea": idx,
                "nombre_en_comprobante": linea.nombre_en_comprobante,
                "producto": linea.producto,
                "color": linea.color,
                "talle": linea.talle,
                "cantidad": linea.cantidad,
                "costo_unitario": linea.costo_unitario,
                "subtotal": linea.subtotal,
                "costo_directo_prorrateado": costo_directo,
                "costo_unitario_fifo": efectivo_unitario,
                "precio_sugerido": linea.precio_sugerido,
            }
        )
    df = pd.DataFrame(filas)
    print(f"Proveedor: {compra.proveedor}")
    print(f"Fecha: {compra.fecha.isoformat()}")
    print(f"Medio de pago: {compra.medio_pago}")
    print(f"Subtotal mercaderia: ${compra.subtotal}")
    print(f"Costo directo: ${compra.costo_directo}")
    print(f"Total compra/caja: ${compra.total}")
    return df


def confirmar_compra(compra: CompraInteractiva) -> str:
    validar_compra(compra)
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base: {DB_PATH}")

    with duckdb.connect(str(DB_PATH)) as con:
        con.execute("BEGIN TRANSACTION")
        try:
            supplier_id = get_or_create_supplier(con, compra.proveedor)
            payment_method_id = get_payment_method_id(con, compra.medio_pago)
            purchase_id = con.execute(
                """
                INSERT INTO purchases (
                  purchase_date, supplier_id, payment_method_id, invoice_number,
                  subtotal, direct_cost_total, total, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING purchase_id
                """,
                [
                    compra.fecha,
                    supplier_id,
                    payment_method_id,
                    Path(compra.comprobante).name if compra.comprobante else None,
                    compra.subtotal,
                    compra.costo_directo,
                    compra.total,
                    compra.notas,
                ],
            ).fetchone()[0]

            for linea in compra.lineas:
                product_id = get_or_create_product(con, linea.producto)
                variant_id, sku = get_or_create_variant(
                    con,
                    product_id,
                    linea.color,
                    linea.talle,
                    linea.precio_sugerido,
                )
                costo_directo = prorratear_costo_directo(compra, linea)
                costo_unitario_fifo = q((linea.subtotal + costo_directo) / linea.cantidad)
                purchase_line_id = con.execute(
                    """
                    INSERT INTO purchase_lines (
                      purchase_id, variant_id, supplier_item_name, quantity,
                      unit_cost, allocated_direct_cost, effective_unit_cost, line_total
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    RETURNING purchase_line_id
                    """,
                    [
                        purchase_id,
                        variant_id,
                        linea.nombre_en_comprobante,
                        linea.cantidad,
                        linea.costo_unitario,
                        costo_directo,
                        costo_unitario_fifo,
                        linea.subtotal,
                    ],
                ).fetchone()[0]
                con.execute(
                    """
                    INSERT INTO inventory_lots (
                      variant_id, purchase_line_id, received_date, original_quantity,
                      remaining_quantity, unit_cost
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        variant_id,
                        purchase_line_id,
                        compra.fecha,
                        linea.cantidad,
                        linea.cantidad,
                        costo_unitario_fifo,
                    ],
                )
                con.execute(
                    """
                    INSERT INTO stock_movements (
                      movement_date, variant_id, movement_type, quantity,
                      reference_table, reference_id, reason, notes
                    )
                    VALUES (?, ?, 'compra', ?, 'purchases', ?, 'Compra mercaderia', ?)
                    """,
                    [
                        datetime.combine(compra.fecha, datetime.min.time()),
                        variant_id,
                        linea.cantidad,
                        purchase_id,
                        linea.nombre_en_comprobante,
                    ],
                )
                guardar_alias(con, supplier_id, linea.nombre_en_comprobante, variant_id)

            con.execute(
                """
                INSERT INTO cash_movements (
                  movement_date, payment_method_id, movement_type, amount,
                  reference_table, reference_id, notes
                )
                VALUES (?, ?, 'compra_mercaderia', ?, 'purchases', ?, ?)
                """,
                [
                    datetime.combine(compra.fecha, datetime.min.time()),
                    payment_method_id,
                    -compra.total,
                    purchase_id,
                    compra.proveedor,
                ],
            )
            if compra.comprobante:
                con.execute(
                    """
                    INSERT INTO documents (
                      document_type, original_path, supplier_id, document_date,
                      total_amount, status
                    )
                    VALUES ('compra_mercaderia', ?, ?, ?, ?, 'confirmed')
                    """,
                    [compra.comprobante, supplier_id, compra.fecha, compra.total],
                )
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

    print(f"Compra confirmada: {purchase_id}")
    return str(purchase_id)


def validar_compra(compra: CompraInteractiva) -> None:
    if not compra.proveedor:
        raise ValueError("proveedor es obligatorio")
    if not compra.medio_pago:
        raise ValueError("medio_pago es obligatorio")
    if not compra.lineas:
        raise ValueError("la compra no tiene lineas")
    for idx, linea in enumerate(compra.lineas, start=1):
        if not linea.producto:
            raise ValueError(f"linea {idx}: producto es obligatorio")
        if linea.cantidad <= 0:
            raise ValueError(f"linea {idx}: cantidad debe ser mayor a cero")


def prorratear_costo_directo(compra: CompraInteractiva, linea: LineaCompra) -> Decimal:
    if compra.costo_directo == 0 or compra.subtotal == 0:
        return Decimal("0.00")
    return q(compra.costo_directo * linea.subtotal / compra.subtotal)


def limpiar(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def get_or_create_supplier(con: duckdb.DuckDBPyConnection, name: str) -> str:
    row = con.execute("SELECT supplier_id FROM suppliers WHERE lower(name) = lower(?)", [name]).fetchone()
    if row:
        return row[0]
    return con.execute("INSERT INTO suppliers (name) VALUES (?) RETURNING supplier_id", [name]).fetchone()[0]


def get_payment_method_id(con: duckdb.DuckDBPyConnection, name: str) -> str:
    row = con.execute(
        "SELECT payment_method_id FROM payment_methods WHERE lower(name) = lower(?) AND active = TRUE",
        [name],
    ).fetchone()
    if not row:
        raise ValueError(f"No existe el medio de pago: {name!r}")
    return row[0]


def get_or_create_product(con: duckdb.DuckDBPyConnection, name: str) -> str:
    row = con.execute("SELECT product_id FROM products WHERE lower(name) = lower(?)", [name]).fetchone()
    if row:
        return row[0]
    return con.execute("INSERT INTO products (name) VALUES (?) RETURNING product_id", [name]).fetchone()[0]


def next_sku(con: duckdb.DuckDBPyConnection) -> str:
    value = con.execute("SELECT nextval('seq_product_variant')").fetchone()[0]
    return f"ORI-{int(value):06d}"


def get_or_create_variant(
    con: duckdb.DuckDBPyConnection,
    product_id: str,
    color: str,
    size: str,
    default_price: Decimal,
) -> tuple[str, str]:
    row = con.execute(
        """
        SELECT variant_id, sku
        FROM product_variants
        WHERE product_id = ?
          AND coalesce(lower(color), '') = coalesce(lower(?), '')
          AND coalesce(lower(size), '') = coalesce(lower(?), '')
        """,
        [product_id, color or None, size or None],
    ).fetchone()
    if row:
        con.execute(
            """
            UPDATE product_variants
            SET default_price = ?, updated_at = current_timestamp
            WHERE variant_id = ?
            """,
            [default_price, row[0]],
        )
        return row[0], row[1]

    sku = next_sku(con)
    created = con.execute(
        """
        INSERT INTO product_variants (product_id, sku, color, size, default_price)
        VALUES (?, ?, ?, ?, ?)
        RETURNING variant_id, sku
        """,
        [product_id, sku, color or None, size or None, default_price],
    ).fetchone()
    return created[0], created[1]


def guardar_alias(
    con: duckdb.DuckDBPyConnection,
    supplier_id: str,
    supplier_item_name: str,
    variant_id: str,
) -> None:
    if not supplier_item_name:
        return
    exists = con.execute(
        """
        SELECT 1
        FROM supplier_product_aliases
        WHERE supplier_id = ?
          AND lower(supplier_item_name) = lower(?)
          AND variant_id = ?
        """,
        [supplier_id, supplier_item_name, variant_id],
    ).fetchone()
    if exists:
        return
    con.execute(
        """
        INSERT INTO supplier_product_aliases (
          supplier_id, supplier_item_name, variant_id, confidence
        )
        VALUES (?, ?, ?, 'manual')
        """,
        [supplier_id, supplier_item_name, variant_id],
    )


def ejemplo_de_uso() -> None:
    print(
        """
from scripts.compras_interactivo import *

listar_comprobantes()
mostrar_comprobante("ticket.png")
leer_texto_comprobante("ticket.png")

compra = nueva_compra(
    fecha="2026-06-16",
    proveedor="Proveedor X",
    medio_pago="Transferencia",
    comprobante="ticket.png",
    costo_directo=1500,
    notas="Carga interactiva desde Spyder",
)

agregar_linea(
    compra,
    nombre_en_comprobante="REM PAN NEG M",
    producto="Remera Panama",
    color="Negro",
    talle="M",
    cantidad=2,
    costo_unitario=12000,
    precio_sugerido=25000,
)

revisar_compra(compra)
confirmar_compra(compra)
"""
    )
