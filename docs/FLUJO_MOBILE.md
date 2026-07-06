# Flujo mobile de ventas

## Objetivo

Jose entra siempre al mismo HTML desde el telefono, idealmente anclado a la pantalla de inicio.

La app:

- Descarga automaticamente la ultima foto de stock al abrir.
- Guarda solamente el ultimo catalogo descargado.
- Guarda ventas pendientes aparte.
- Permite exportar ventas a JSON para revision/importacion posterior.
- Permite enviar ventas a un repo privado de GitHub si el dispositivo tiene token configurado.

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

## Envio a GitHub

La app puede subir las ventas pendientes a:

```text
quinteiromartin/orilla-ventas-inbox
```

Ese repo debe ser privado.

La configuracion se guarda solo en el navegador/dispositivo:

- Token de GitHub.
- Repo destino.
- Rama.
- Carpeta destino.

El token no se guarda en el codigo y no se sube al repo publico.

Flujo:

```text
Guardar venta
  -> queda pendiente en el telefono
Enviar
  -> sube un JSON a GitHub
  -> si falla, no borra nada
  -> si funciona, muestra confirmacion
```

La app no borra automaticamente despues de enviar. Primero hay que confirmar que la venta llego bien y fue importada.

## Regla operativa

Despues de exportar y confirmar que el archivo llego bien a la computadora, se pueden borrar las ventas pendientes del telefono.

Despues de enviar a GitHub y confirmar que fue importado en DuckDB, tambien se pueden borrar las ventas pendientes del telefono.

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
