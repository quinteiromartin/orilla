# Flujo mobile de ventas

## Objetivo

Jose entra siempre al mismo HTML desde el telefono, idealmente anclado a la pantalla de inicio.

La app:

- Descarga automaticamente la ultima foto de stock al abrir.
- Guarda solamente el ultimo catalogo descargado.
- Maneja un carrito local antes de cerrar la venta.
- Descuenta stock local apenas se agrega una prenda al carrito.
- Intenta enviar a GitHub al finalizar una compra.
- Mantiene ventas no enviadas si falla el envio.
- Mantiene ventas enviadas recientes hasta que DuckDB las incorpore.
- Permite exportar ventas locales como respaldo tecnico.

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

## Stock disponible local

Jose ve cantidad disponible, no stock bruto.

La disponibilidad local se calcula asi:

```text
disponible local =
  stock oficial de DuckDB
  - carrito actual
  - ventas no enviadas
  - ventas enviadas recientes aun no incorporadas a DuckDB
```

Cuando una prenda entra al carrito, baja la disponibilidad local.

Cuando se quita del carrito, vuelve a estar disponible.

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

Flujo principal:

```text
Agregar al carrito
  -> baja disponible local
Finalizar compra
  -> crea mobile_sale_uid unico
  -> sube un JSON a GitHub
  -> si falla, no borra nada
  -> si funciona, queda en enviadas recientes
```

La app no borra automaticamente las ventas enviadas recientes. Las limpia cuando una nueva `foto_stock.json` informa que DuckDB ya incorporo esos `mobile_sale_uid`.

## Reconciliacion con DuckDB

`foto_stock.json` incluye:

```json
{
  "ventas_mobile_importadas": ["..."]
}
```

Cuando la app actualiza stock:

- descarga la foto oficial nueva
- identifica ventas enviadas recientes que ya estan importadas
- las elimina del descuento local
- recalcula disponibilidad

## Regla operativa

## Respaldo tecnico

El link `Respaldo tecnico: exportar ventas locales` no es el flujo principal.

Sirve solo si GitHub falla o si hace falta rescatar ventas desde el dispositivo.

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
