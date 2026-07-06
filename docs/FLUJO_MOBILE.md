# Flujo mobile de ventas

## Objetivo

Jose entra siempre al mismo HTML desde el telefono, idealmente anclado a la pantalla de inicio.

La app:

- Descarga automaticamente la ultima foto de stock al abrir.
- Guarda solamente el ultimo catalogo descargado.
- Guarda ventas pendientes aparte.
- Permite exportar ventas a JSON para revision/importacion posterior.

## Archivos publicados

Para GitHub Pages, publicar estos archivos manteniendo la relacion de carpetas:

```text
app_ventas/
  index.html
  manifest.json
  icon.svg
exports/
  foto_stock.json
```

La app busca el stock en:

```text
../exports/foto_stock.json
```

Si la URL publicada fuera distinta, hay que ajustar `STOCK_URL` en `app_ventas/index.html`.

## Actualizacion de stock

Desde DuckDB se genera:

```text
exports/foto_stock.json
```

La app intenta descargar ese archivo cada vez que abre.

Para evitar cache viejo, lo pide con un parametro variable:

```text
foto_stock.json?t=<timestamp>
```

Si la descarga funciona:

- Reemplaza el ultimo catalogo local.
- No guarda historial.

Si la descarga falla:

- Usa el ultimo catalogo guardado en el telefono.

## Ventas pendientes

Las ventas se guardan en el telefono hasta exportarlas.

Actualizar stock no borra ventas pendientes.

El boton `Exportar` genera un archivo:

```text
ventas_orilla_YYYYMMDDHHMMSS.json
```

Ese archivo se revisa e importa despues a DuckDB.

## Regla operativa

Despues de exportar y confirmar que el archivo llego bien a la computadora, se pueden borrar las ventas pendientes del telefono.

## Importacion a DuckDB

Guardar el JSON exportado en:

```text
imports/ventas_mobile/
```

Revisar sin impactar la base:

```powershell
& "C:\Users\Martin\anaconda3\python.exe" scripts\import_ventas_mobile.py --archivo imports\ventas_mobile\<archivo>.json
```

Confirmar si la revision esta OK:

```powershell
& "C:\Users\Martin\anaconda3\python.exe" scripts\import_ventas_mobile.py --archivo imports\ventas_mobile\<archivo>.json --confirmar
```

Luego regenerar la foto de stock:

```powershell
& "C:\Users\Martin\anaconda3\python.exe" scripts\export_foto_stock.py
```
