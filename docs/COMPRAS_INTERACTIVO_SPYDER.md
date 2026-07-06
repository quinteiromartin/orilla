# Compras de mercaderia en Spyder

El flujo de compras no usa CSV.

La idea es trabajar interactivo desde Spyder:

1. Poner fotos/tickets/facturas en `comprobantes/compras/`.
2. Abrir/ver la imagen desde Python.
3. Cargar la compra como objeto.
4. Agregar lineas de mercaderia.
5. Revisar totales y costo FIFO.
6. Confirmar contra DuckDB.
7. Regenerar `foto_stock.json`.

## Setup en Spyder

Abrir Spyder en:

```text
C:\Users\Martin\OneDrive\Trabajo\Orilla Tienda\sistema_integral
```

Ejecutar:

```python
from scripts.compras_interactivo import *
```

El proyecto usa Tesseract desde:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

## Ver comprobantes disponibles

```python
listar_comprobantes()
```

## Mostrar un comprobante

```python
mostrar_comprobante("ticket.png")
```

## Leer texto con OCR

```python
idiomas_ocr()
leer_texto_comprobante("ticket.png")
```

Si `idiomas_ocr()` no muestra `spa`, el OCR usa ingles por defecto. Para tickets en espanol conviene instalar el idioma `spa` de Tesseract.

## Cargar una compra

```python
compra = nueva_compra(
    fecha="2026-06-16",
    proveedor="Proveedor X",
    medio_pago="Transferencia",
    comprobante="ticket.png",
    costo_directo=1500,
    notas="Carga interactiva desde Spyder",
)
```

## Agregar lineas

```python
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
```

Se pueden agregar varias lineas a la misma compra.

## Revisar antes de confirmar

```python
revisar_compra(compra)
```

La revision muestra:

- Subtotal de mercaderia.
- Costo directo.
- Total de compra/caja.
- Costo directo prorrateado.
- Costo unitario FIFO.
- Precio sugerido.

## Confirmar

Solo confirmar cuando la revision esta OK:

```python
confirmar_compra(compra)
```

Al confirmar, el sistema:

- Crea proveedor si no existe.
- Crea producto si no existe.
- Crea variante/SKU si no existe.
- Actualiza precio sugerido si la variante ya existe.
- Registra compra.
- Registra lineas.
- Crea lotes FIFO.
- Sube stock.
- Registra egreso de caja.
- Guarda alias entre nombre del comprobante y producto interno.
- Guarda referencia al comprobante si fue informado.

## Actualizar app mobile

Despues de confirmar compras:

```python
import subprocess
subprocess.run([
    r"C:\Users\Martin\anaconda3\python.exe",
    "scripts/export_foto_stock.py",
])
```

O desde PowerShell:

```powershell
& "C:\Users\Martin\anaconda3\python.exe" scripts\export_foto_stock.py
```
