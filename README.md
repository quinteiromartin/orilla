# Orilla Tienda - sistema integral

Sistema local-first para gestion de compras, ventas, stock, caja y reportes.

El diseno funcional esta documentado en `PROYECTO_SISTEMA_INTEGRAL.md`.

## Estructura

```text
app_ventas/      App HTML fija para cargar ventas desde telefono
backups/         Copias de seguridad de la base DuckDB
data/            Base principal DuckDB
docs/            Documentacion adicional
exports/         Archivos publicados/exportados, como foto_stock.json
imports/         Archivos pendientes de revision/importacion
reports/         Reportes HTML generados
scripts/         Scripts operativos
```

## Primer MVP

- Base DuckDB con esquema inicial.
- Exportacion de catalogo/stock a `exports/foto_stock.json`.
- App mobile que lee `foto_stock.json`, guarda ventas pendientes localmente y permite exportarlas.

## Uso previsto

1. Inicializar la base con `scripts/init_db.py`.
2. Cargar productos y stock inicial desde `imports/stock_inicial/stock_inicial.csv`.
3. Exportar la foto de stock con `scripts/export_foto_stock.py`.
4. Publicar `app_ventas/` y `exports/foto_stock.json`.
5. Cargar ventas desde el telefono.
6. Exportar ventas pendientes y revisarlas antes de importarlas a DuckDB.

Nota: ejecutar los scripts con el Python de Anaconda/Spyder que ya usa el proyecto:

```text
C:\Users\Martin\anaconda3\python.exe
```

## Comandos utiles

Desde PowerShell:

```powershell
& "C:\Users\Martin\anaconda3\python.exe" scripts\init_db.py
& "C:\Users\Martin\anaconda3\python.exe" scripts\import_stock_inicial.py
& "C:\Users\Martin\anaconda3\python.exe" scripts\export_foto_stock.py
```

Ejecutar estas tareas una por vez. DuckDB usa un archivo local y puede bloquearse si dos procesos intentan escribir/leer durante una inicializacion o importacion.

## Reinicio seguro de base

Para empezar con datos reales sin mezclar pruebas, primero revisar:

```powershell
& "C:\Users\Martin\anaconda3\python.exe" scripts\reset_db_seguro.py
```

Si esta OK, confirmar:

```powershell
& "C:\Users\Martin\anaconda3\python.exe" scripts\reset_db_seguro.py --confirmar
```

El script hace backup en `backups/` antes de recrear la base vacia.

## Stock inicial

Editar:

```text
imports/stock_inicial/stock_inicial.csv
```

Columnas:

```text
producto,color,talle,precio_sugerido,stock_inicial,costo_unitario_inicial
```

El importador:

- Crea productos.
- Crea variantes.
- Genera SKUs `ORI-000001`, `ORI-000002`, etc.
- Registra stock inicial como movimiento auditable.
- Crea lotes FIFO iniciales.
- Se puede correr mas de una vez sin duplicar el stock inicial ya importado.

## Ventas mobile

La app exporta ventas a JSON. Esos archivos se guardan en:

```text
imports/ventas_mobile/
```

Primero revisar:

```powershell
& "C:\Users\Martin\anaconda3\python.exe" scripts\import_ventas_mobile.py --archivo imports\ventas_mobile\ventas_mobile_ejemplo.json
```

Si la revision esta OK, confirmar:

```powershell
& "C:\Users\Martin\anaconda3\python.exe" scripts\import_ventas_mobile.py --archivo imports\ventas_mobile\ventas_mobile_ejemplo.json --confirmar
& "C:\Users\Martin\anaconda3\python.exe" scripts\export_foto_stock.py
```

El importador:

- Valida SKU.
- Valida medio de cobro.
- Revisa stock disponible.
- Calcula costo FIFO.
- Muestra margen estimado antes de importar.
- Inserta venta, linea, pago, movimiento de stock, movimiento de caja y asignacion FIFO.
- Evita duplicar ventas ya importadas usando `mobile_sale_uid`.

La app envia ventas a GitHub al finalizar una compra si el dispositivo tiene configurado un token local. El destino previsto es el repo privado:

```text
quinteiromartin/orilla-ventas-inbox
```

El flujo principal de la app es carrito -> finalizar compra -> envio a GitHub. La exportacion manual queda solo como respaldo tecnico.

Para importar desde el repo privado, guardar un token local en:

```text
config/github_token.txt
```

Ese archivo no se sube a GitHub.

Revisar ventas disponibles en GitHub:

```powershell
& "C:\Users\Martin\anaconda3\python.exe" scripts\import_ventas_github.py
```

Confirmar importacion:

```powershell
& "C:\Users\Martin\anaconda3\python.exe" scripts\import_ventas_github.py --confirmar
& "C:\Users\Martin\anaconda3\python.exe" scripts\export_foto_stock.py
git add exports\foto_stock.json
git commit -m "Update stock after GitHub mobile sales"
git push
```

## Compras interactivas en Spyder

Las compras de mercaderia se cargan desde Python interactivo, no desde CSV.

Documento de uso:

```text
docs/COMPRAS_INTERACTIVO_SPYDER.md
```

Modulo:

```python
from scripts.compras_interactivo import *
```

Funciones principales:

- `listar_comprobantes()`
- `mostrar_comprobante("ticket.png")`
- `nueva_compra(...)`
- `agregar_linea(...)`
- `revisar_compra(compra)`
- `confirmar_compra(compra)`

## Publicacion de la app

La guia para publicar la app en GitHub Pages esta en:

```text
docs/GITHUB_PAGES.md
```

Para probar la app en la computadora:

```powershell
cd "C:\Users\Martin\OneDrive\Trabajo\Orilla Tienda\sistema_integral"
& "C:\Users\Martin\anaconda3\python.exe" -m http.server 8765 --bind 127.0.0.1
```

Luego abrir:

```text
http://127.0.0.1:8765/app_ventas/
```
