from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "imports" / "stock_inicial" / "Stock julio 2026.xlsx"
OUTPUT_PATH = ROOT / "imports" / "stock_inicial" / "stock_inicial.csv"
REVIEW_PATH = ROOT / "imports" / "stock_inicial" / "stock_inicial_revision.csv"
REPORT_PATH = ROOT / "imports" / "stock_inicial" / "stock_inicial_resumen.txt"

PRICE_FIXES = {
    ("Pantalón Rock", "camel", 580000): 58000,
    ("Pantalón Ombú", "negro", 250000): 25000,
}


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def main() -> None:
    if not SOURCE_PATH.exists():
        raise SystemExit(f"No existe el archivo fuente: {SOURCE_PATH}")

    source = pd.read_excel(SOURCE_PATH)
    required = {
        "PRODUCTO",
        "CANTIDAD",
        "COLOR",
        "PRECIO DE COMPRA",
        "PRECIO DE VENTA",
        "PROVEEDOR",
    }
    missing = required - set(source.columns)
    if missing:
        raise SystemExit(f"Faltan columnas: {', '.join(sorted(missing))}")

    rows = []
    fixes_applied = []
    proxy_cost_count = 0
    missing_supplier_count = 0

    for index, row in source.iterrows():
        producto = clean_text(row["PRODUCTO"])
        color = clean_text(row["COLOR"])
        proveedor = clean_text(row["PROVEEDOR"])
        cantidad = int(row["CANTIDAD"])
        precio_venta = int(row["PRECIO DE VENTA"])

        fixed_price = PRICE_FIXES.get((producto, color, precio_venta))
        if fixed_price is not None:
            fixes_applied.append((producto, color, precio_venta, fixed_price))
            precio_venta = fixed_price

        precio_compra_raw = row["PRECIO DE COMPRA"]
        if pd.isna(precio_compra_raw):
            costo_unitario = round(precio_venta * 0.5, 2)
            proxy_cost_count += 1
        else:
            costo_unitario = round(float(precio_compra_raw), 2)

        if not proveedor:
            missing_supplier_count += 1

        rows.append(
            {
                "producto": producto,
                "color": color,
                "talle": "único",
                "precio_sugerido": precio_venta,
                "stock_inicial": cantidad,
                "costo_unitario_inicial": costo_unitario,
                "proveedor_origen": proveedor,
            }
        )

    review = pd.DataFrame(rows)
    output = review[
        [
            "producto",
            "color",
            "talle",
            "precio_sugerido",
            "stock_inicial",
            "costo_unitario_inicial",
        ]
    ]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    review.to_csv(REVIEW_PATH, index=False, encoding="utf-8-sig")

    total_units = int(output["stock_inicial"].sum())
    inventory_sale_value = float((output["precio_sugerido"] * output["stock_inicial"]).sum())
    inventory_cost_value = float((output["costo_unitario_inicial"] * output["stock_inicial"]).sum())

    report = [
        "Resumen stock inicial desde Excel",
        "=" * 40,
        f"Archivo fuente: {SOURCE_PATH}",
        f"CSV generado: {OUTPUT_PATH}",
        f"CSV revision: {REVIEW_PATH}",
        f"Filas: {len(output)}",
        f"Unidades totales: {total_units}",
        f"Valor venta inventario: {inventory_sale_value:,.2f}",
        f"Valor costo inventario: {inventory_cost_value:,.2f}",
        f"Costos estimados al 50%: {proxy_cost_count}",
        f"Proveedores vacios: {missing_supplier_count}",
        "",
        "Correcciones aplicadas:",
    ]
    if fixes_applied:
        for producto, color, original, fixed in fixes_applied:
            report.append(f"- {producto} / {color}: {original} -> {fixed}")
    else:
        report.append("- Ninguna")

    report.append("")
    report.append("Primeras filas:")
    report.append(output.head(12).to_string(index=False))
    report_text = "\n".join(report)
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    print(report_text)


if __name__ == "__main__":
    main()
