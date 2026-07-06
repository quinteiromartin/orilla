# Sistema integral de gestion - Orilla Tienda

Documento vivo de diseno del sistema integral para gestion de compras, ventas, stock, caja y reporting del emprendimiento de ropa.

Fecha de inicio del diseno: 2026-06-12

## Objetivo

Construir un sistema local-first, simple de usar y confiable, que permita:

- Registrar compras de mercaderia.
- Registrar gastos de estructura.
- Registrar ventas de manera muy simple, especialmente desde telefono.
- Mantener stock actualizado por producto y variante.
- Mantener una evolucion de caja.
- Calcular rentabilidad usando FIFO para costo de mercaderia vendida.
- Generar reportes interactivos en HTML.
- Cargar comprobantes de compras desde fotos/tickets/facturas con una etapa de revision antes de impactar la base.
- Proteger los datos contra perdida y errores desde el inicio.

La base principal sera DuckDB.

## Principios de diseno

- La carga diaria debe ser lo mas simple posible.
- Las ventas no se deben perder aunque no se registren inmediatamente en DuckDB.
- DuckDB sera la fuente consolidada y auditada.
- El sistema debe guardar movimientos, no solo estados finales.
- Las correcciones deben quedar trazables.
- El reporting no necesita estar online ni en tiempo real.
- La arquitectura debe permitir empezar con un MVP solido y crecer sin rehacer todo.

## Alcance funcional

### Modulo de productos

Los productos son prendas con nombre propio, por ejemplo:

- Remera Panama
- Jean Lisboa
- Campera Roma

Cada producto puede tener variantes.

Variantes esperadas:

- Talle
- Color
- Otros atributos futuros si hicieran falta

El stock alcanza con nivel producto-variante. No hace falta identificar cada unidad fisica de manera individual.

Ejemplo:

```text
Producto: Remera Panama
Color: Negro
Talle: M
Stock disponible: 2
```

Caracteristica importante del negocio:

- Hay pocas unidades de mucha variedad.
- Puede haber prendas casi unicas o con muy pocas unidades.

### Codigos / SKU

No existen codigos actuales. El sistema deberia generarlos.

Propuesta inicial:

```text
ORI-000001
ORI-000002
ORI-000003
```

El SKU deberia corresponder a la variante vendible, no solo al producto base.

Ejemplo:

```text
Producto base: Remera Panama
Variante: Negro / M
SKU: ORI-000127
```

Esto facilita stock, ventas, compras, reservas y reportes.

### Ubicacion

Por ahora habra una sola ubicacion de stock.

No se modelan multiples depositos, showroom, ferias o consignacion en el MVP.

Se deja abierta la posibilidad futura de agregar ubicaciones.

## Compras

El modulo de compras registra compras de mercaderia.

Campos esperados:

- Fecha
- Proveedor
- Comprobante asociado, si existe
- Medio de pago
- Productos comprados
- Cantidad
- Costo unitario
- Costo total
- Costos directos asociados a la compra, como envio si lo paga el negocio
- Observaciones

Las compras de mercaderia y los gastos fijos/de estructura se registran separados.

### Costos directos de compra

Cuando una compra de mercaderia tenga costos directos asociados, por ejemplo envio, esos costos deberian poder prorratearse entre los productos.

Objetivo:

- Calcular un costo real por unidad.
- Usar ese costo para FIFO.
- Estimar margen neto por venta.

Decision inicial:

- El sistema debe soportar prorrateo de costos directos sobre mercaderia.
- El metodo exacto de prorrateo queda por definir.

Opciones posibles:

- Por cantidad de unidades.
- Por costo relativo de cada item.
- Manual.

Recomendacion inicial:

- Prorratear por costo relativo de cada item, porque suele representar mejor el peso economico de la compra.

## Gastos de estructura

Los gastos de estructura se registran en un modulo separado.

Categorias iniciales:

- Packaging
- Publicidad
- Envios
- Otros

Campos esperados:

- Fecha
- Categoria
- Proveedor o contraparte, opcional
- Descripcion
- Medio de pago
- Importe
- Comprobante, opcional
- Observaciones

Estos gastos no impactan stock.

Sirven para reportes de resultado mensual, trimestral y anual.

## Ventas

La carga de ventas debe ser muy simple para que se use de manera consistente.

Campos minimos:

- Fecha
- Producto / variante
- Cantidad
- Precio de venta sugerido
- Precio de venta final editable
- Medio de cobro
- Descuento, si aplica
- Observaciones opcionales

Campos que por ahora no se cargan:

- Canal de venta
- Cliente obligatorio
- Datos de envio

El cliente puede ser anonimo.

### Canales de venta

Canales actuales:

- Instagram
- WhatsApp
- Showroom
- Ferias
- Pagina web en proceso

Decision MVP:

- No registrar canal de venta en la carga inicial, para mantener simple el formulario.

Nota:

- Se podria agregar mas adelante como campo opcional con valor por defecto.

### Medios de cobro

El sistema debe registrar medio de cobro.

Ejemplos:

- Efectivo
- Transferencia
- Mercado Pago
- Tarjeta
- Otro

Esto alimenta caja y reportes de cobros.

### Descuentos, senas y pagos parciales

El sistema debe contemplar:

- Precio definido por producto.
- Precio editable al cargar la venta.
- Descuentos.
- Senas.
- Pagos parciales.
- Cuotas o pagos diferidos si hiciera falta.

Para el MVP se puede simplificar:

- Registrar precio final de venta.
- Registrar uno o mas pagos asociados a la venta.
- Permitir que una venta quede con saldo pendiente.

### Cambios y devoluciones

Debe haber soporte para cambios y devoluciones.

Impactos esperados:

- Reingreso de stock cuando corresponde.
- Ajuste de caja si hay devolucion de dinero.
- Trazabilidad del movimiento.
- Ajuste en reportes de ventas y margen.

## Reservas

Puede haber prendas reservadas/apartadas.

Necesidad:

- Una unidad reservada no deberia figurar como disponible.
- Todavia no debe contarse como venta definitiva.

Modelo propuesto:

- Stock fisico
- Stock reservado
- Stock disponible = stock fisico - stock reservado

Una reserva podria convertirse en venta o cancelarse.

Para el MVP se puede decidir si las reservas entran desde el inicio o quedan como mejora inmediata.

## Stock

El stock debe surgir de movimientos, no de una tabla editada a mano sin historia.

Tipos de movimiento esperados:

- Stock inicial
- Compra
- Venta
- Devolucion
- Cambio
- Reserva
- Cancelacion de reserva
- Ajuste manual

Todo movimiento debe quedar auditado.

Campos esperados:

- Fecha
- Tipo de movimiento
- Producto / variante
- Cantidad positiva o negativa
- Referencia al origen, si existe
- Motivo
- Usuario/origen del cambio, si aplica
- Observaciones

### Stock inicial

Se cargara una vez al inicio, probablemente desde una pantalla o CSV.

Debe quedar registrado como movimiento de stock inicial.

### Ajustes manuales

Se permiten ajustes ad hoc, por ejemplo:

- Recuento fisico.
- Error de carga.
- Prenda danada.
- Diferencia detectada.

Los ajustes deben requerir motivo.

## Costeo y margen

El margen debe calcularse usando FIFO.

Definicion:

- FIFO = first in, first out.
- Las primeras unidades compradas son las primeras que se consideran vendidas.

Para cada venta, el sistema deberia poder determinar:

- Precio de venta final.
- Costo de mercaderia vendida.
- Costos directos asociados a esa mercaderia.
- Margen neto de la venta.

No se necesita historial de precios por ahora.

El producto tiene un precio definido actual, pero el precio puede modificarse en cada venta.

## Caja

Se necesita una tabla o modulo de evolucion de caja.

La caja debe reflejar:

- Ingresos por ventas.
- Egresos por compras de mercaderia.
- Egresos por gastos de estructura.
- Devoluciones.
- Ajustes manuales.
- Movimientos entre medios de pago si hiciera falta.

Debe poder analizarse por medio de pago.

Ejemplos:

- Efectivo
- Transferencia
- Mercado Pago
- Tarjeta

La caja tambien debe estar basada en movimientos auditables.

## Reporting

El reporting no necesita estar online.

Propuesta:

- Generar reportes HTML interactivos desde DuckDB.
- Abrirlos localmente desde la computadora.
- Opcionalmente guardarlos en una carpeta sincronizada por OneDrive.

Reportes deseados:

- Ventas.
- Ingresos.
- Margen neto.
- Stock actual.
- Reportes diarios o periodicos de stock.
- Resultado mensual, trimestral y anual.
- Margen neto menos costos fijos.
- Margen por producto.
- Inventario valorizado.
- Caja.
- Gastos por categoria.

### Periodicidad

Reportes de stock:

- Podrian ser diarios.

Informes de resultado:

- Mensual.
- Trimestral.
- Anual.

## Carga de comprobantes de compras

La mayoria de los comprobantes son fotos de tickets o facturas.

Los proveedores se repiten bastante.

Los comprobantes suelen tener detalle de producto, pero los nombres del comprobante no coinciden necesariamente con los nombres internos del sistema.

Necesidad:

- OCR desde imagen o PDF.
- Extraccion de proveedor, fecha, total y lineas.
- Mapeo entre nombre del proveedor y producto interno.
- Revision humana antes de insertar en DuckDB.

Flujo propuesto:

```text
Foto/ticket/factura
  -> OCR
  -> extraccion tentativa
  -> pantalla/archivo de revision
  -> correccion humana
  -> carga confirmada en DuckDB
```

Decision importante:

- Nunca cargar automaticamente sin revision.

### Mapeo de nombres

Se necesita trackear ambos nombres:

- Nombre original del comprobante/proveedor.
- Producto interno normalizado.

Ejemplo:

```text
Nombre en ticket: REM PANAMA NEG M
Producto interno: Remera Panama
Color: Negro
Talle: M
SKU: ORI-000127
```

Este mapeo puede mejorar con el tiempo.

## App de carga de ventas desde telefono

Necesidad principal:

- Que Jose pueda registrar ventas en el momento.
- Que las ventas no se pierdan.
- Que no sea obligatorio que impacten DuckDB en tiempo real.
- Que pueda acumular ventas y luego enviarlas o exportarlas para que sean cargadas/revisadas.

No se quiere depender de un servicio externo.

### Problema a resolver

Un HTML abierto en el telefono puede guardar datos localmente, pero no puede escribir directamente en DuckDB sin un backend.

Tampoco GitHub Pages sirve para escribir en DuckDB.

Por eso hay que separar:

- Captura de ventas en telefono.
- Consolidacion posterior en DuckDB.

### Opciones de arquitectura para la app mobile

#### Opcion A - HTML offline con almacenamiento local y exportacion

Una app HTML mobile-first que funciona en el navegador del telefono.

Caracteristicas:

- Carga productos desde un archivo exportado, por ejemplo `catalogo.json`.
- Guarda ventas en el almacenamiento local del navegador.
- Permite exportar ventas a archivo JSON/CSV.
- Ese archivo se manda por WhatsApp, mail, AirDrop/USB, OneDrive o se copia manualmente.
- Luego se importa y revisa en la computadora antes de entrar a DuckDB.

Ventajas:

- Muy simple.
- Sin servidor.
- No requiere internet.
- Baja dependencia tecnica.
- Las ventas quedan guardadas en el telefono hasta exportarlas.

Riesgos:

- Si se borra el navegador, se puede perder lo no exportado.
- Hay que crear habito de exportar/sincronizar.
- La app no ve stock actualizado automaticamente salvo que se le cargue un catalogo nuevo.

Mitigaciones:

- Boton grande de exportar.
- Exportacion semanal.
- Backup local del archivo exportado.
- Mostrar contador de ventas pendientes de exportar.
- Permitir copiar el JSON al portapapeles como respaldo rapido.

#### Opcion B - HTML offline + archivo compartido en OneDrive

Similar a la opcion A, pero la exportacion/importacion vive en una carpeta sincronizada por OneDrive.

Ventajas:

- Sigue siendo simple.
- Mejor backup.

Riesgos:

- En telefono puede depender de como OneDrive maneje archivos locales.
- Puede ser menos fluido que una app web normal.

#### Opcion C - Servidor local en la computadora

Una app web corre en la computadora y el telefono entra por WiFi.

Caracteristicas:

- El backend escribe directamente en DuckDB.
- Puede ver stock y productos actualizados.

Ventajas:

- Mas integrado.
- Menos pasos de importacion.

Riesgos:

- Requiere que la computadora este prendida.
- Requiere estar en la misma red o configurar acceso remoto.
- Es mas complejo.

#### Opcion D - Backend liviano online

No deseada por ahora porque se prefiere no usar servicios externos.

### Recomendacion actualizada

La app de ventas deberia ser un HTML fijo, idealmente instalable en la pantalla de inicio del telefono como si fuera una app.

No es viable generar un HTML nuevo cada vez que cambia el stock, porque Jose deberia entrar siempre al mismo lugar.

Por eso la opcion preferida pasa a ser:

```text
HTML fijo mobile-first
  -> carga catalogo/stock desde un archivo JSON publicado
  -> guarda ventas localmente en el telefono
  -> exporta ventas JSON/CSV
  -> revision/importacion posterior en DuckDB
```

El archivo de catalogo podria llamarse:

```text
foto_stock.json
```

Ese archivo se genera desde DuckDB en la computadora y se publica/actualiza en el mismo lugar donde vive el HTML.

Esto permite que:

- Jose entre siempre al mismo HTML/app.
- La app tome productos, variantes, precios y stock desde una foto actualizada.
- La app siga guardando ventas localmente aunque DuckDB no este disponible.
- DuckDB siga siendo la fuente consolidada y auditada.

## Catalogo para la app mobile

La app del telefono necesita conocer:

- Productos disponibles.
- Variantes.
- SKU.
- Precio sugerido.
- Stock disponible o al menos estado vendible.

Como no habra conexion directa con DuckDB, se propone generar un archivo:

```text
foto_stock.json
```

Ese archivo se exporta desde DuckDB y se carga en la app.

Contenido posible:

```json
[
  {
    "sku": "ORI-000127",
    "producto": "Remera Panama",
    "color": "Negro",
    "talle": "M",
    "precio_sugerido": 25000,
    "stock_disponible": 2
  }
]
```

### Publicacion del catalogo

Opcion preferida:

- El HTML vive en GitHub Pages u otra ubicacion estatica.
- En la misma ubicacion vive `foto_stock.json`.
- La app hace una lectura de ese JSON cuando abre o cuando se toca "Actualizar".
- Desde la computadora se regenera `foto_stock.json` a partir de DuckDB y se sube/publica.

Flujo:

```text
DuckDB
  -> script exporta foto_stock.json
  -> se publica junto al HTML
  -> app mobile lee foto_stock.json
  -> Jose carga ventas
  -> la app guarda ventas pendientes en el telefono
  -> Jose exporta ventas
  -> se importan/revisan en DuckDB
```

Puntos a cuidar:

- La app debe mostrar fecha/hora de actualizacion del catalogo.
- La app debe poder seguir usando el ultimo catalogo descargado si no hay internet.
- La app debe guardar solamente el ultimo `foto_stock.json` descargado en el telefono.
- No debe conservar historial de catalogos/stock en el telefono.
- El navegador puede cachear archivos; hay que evitar que use una version vieja sin avisar.
- Si GitHub Pages es publico, `foto_stock.json` tambien podria quedar publicamente accesible. Esto es aceptable para el proyecto.

### Actualizacion automatica del catalogo

La app debe intentar actualizar `foto_stock.json` automaticamente cada vez que se abre.

Comportamiento esperado:

1. La app abre.
2. Intenta descargar la ultima version de `foto_stock.json`.
3. Para evitar cache viejo, pide el archivo con un parametro variable, por ejemplo `foto_stock.json?t=<timestamp>`.
4. Si la descarga funciona y el JSON es valido, reemplaza el catalogo local anterior.
5. Si la descarga falla, usa el ultimo catalogo local guardado.
6. La pantalla muestra claramente la fecha/hora del catalogo que se esta usando.

Regla importante:

- En el telefono solo queda guardado el ultimo catalogo descargado.
- Las ventas pendientes se guardan aparte y no se borran al actualizar catalogo.

## DuckDB

DuckDB sera la base consolidada.

Archivo esperado:

```text
data/orilla.duckdb
```

Se recomienda separar:

- Base de datos.
- Scripts.
- Reportes generados.
- Comprobantes originales.
- Archivos importados/exportados.
- Backups.

Estructura tentativa de carpetas:

```text
sistema_integral/
  data/
    orilla.duckdb
  backups/
  app_ventas/
  comprobantes/
    compras/
    gastos/
  imports/
    ventas_mobile/
    compras_ocr/
  reports/
  scripts/
  docs/
```

## Modelo de datos inicial

Tablas tentativas:

### Maestros

- `products`
- `product_variants`
- `suppliers`
- `payment_methods`
- `expense_categories`

### Compras y gastos

- `purchases`
- `purchase_lines`
- `purchase_direct_costs`
- `expenses`

### Ventas

- `sales`
- `sale_lines`
- `sale_payments`
- `returns`
- `return_lines`

### Stock

- `stock_movements`
- `reservations`

### Caja

- `cash_movements`

### Costeo FIFO

- `inventory_lots`
- `inventory_allocations`

### Comprobantes y OCR

- `documents`
- `ocr_runs`
- `ocr_extracted_lines`
- `supplier_product_aliases`

### Auditoria

- `import_batches`
- `audit_log`

## Seguridad, control de errores y backups

Cuando se habla de que el sistema este protegido desde cero, las prioridades son:

- Evitar perdida de datos.
- Tener backups.
- Validar antes de importar.
- Mantener trazabilidad.
- Poder corregir errores sin borrar historia.

### OneDrive

OneDrive parece razonable como primera capa de backup/sincronizacion porque ya forma parte del entorno de trabajo.

Precauciones:

- DuckDB es un unico archivo de base de datos.
- Conviene evitar abrir/escribir la base desde dos procesos a la vez.
- Conviene hacer backups versionados antes de importaciones importantes.

Recomendacion:

- Mantener la base en OneDrive esta bien para este uso local, con cuidado.
- Crear backups automaticos con timestamp antes de cargas/importaciones.
- No depender solo de sincronizacion; guardar copias en `backups/`.

Ejemplo:

```text
backups/orilla_2026-06-12_1530.duckdb
```

## MVP propuesto

Una primera version util deberia incluir:

- Crear base DuckDB y esquema inicial.
- Cargar productos y variantes.
- Generar SKUs.
- Cargar stock inicial.
- Cargar compras de mercaderia.
- Cargar gastos de estructura.
- Cargar ventas desde una app HTML simple en telefono.
- Exportar ventas desde telefono.
- Importar ventas a DuckDB con revision.
- Actualizar stock por compras, ventas y ajustes.
- Calcular FIFO basico.
- Ver stock actual.
- Ver ventas, ingresos y margen.
- Ver caja por medio de pago.
- Ver gastos por categoria.
- Generar reporte HTML local.

## Producto final esperado

Aunque el MVP sea simple, el producto final deberia tender a:

- Una base consolidada confiable.
- Carga diaria muy simple.
- Importaciones revisables.
- Reportes claros de negocio.
- Caja y stock trazables.
- Costeo FIFO consistente.
- Flujo de comprobantes asistido por OCR.
- Posibilidad de operar sin servicios externos.

## Decisiones confirmadas

- Usar DuckDB.
- El sistema no necesita estar online.
- Una sola ubicacion de stock por ahora.
- Stock por producto-variante.
- Generar SKUs.
- Compras de mercaderia separadas de gastos de estructura.
- Categorizar gastos.
- Registrar medio de pago/cobro.
- Permitir devoluciones/cambios con impacto en stock.
- Usar FIFO para costo de mercaderia vendida.
- No exigir cliente en ventas.
- No registrar canal de venta en MVP.
- No exigir internet para la app de ventas.
- Hacer revision humana antes de importar OCR a DuckDB.
- Guardar nombre original del comprobante y producto interno.
- OneDrive es aceptable como primera capa de proteccion, con backups adicionales.

## Decisiones abiertas

- Metodo exacto de prorrateo de costos directos de compra.
- Si reservas entran en el MVP o en una segunda etapa inmediata.
- Como se actualizara el catalogo en el telefono.
- Formato de exportacion mobile principal: JSON, CSV o ambos.
- Flujo de revision de ventas importadas.
- Si habra una mini app local de escritorio para compras/gastos o si al inicio se carga por CSV/formulario simple.
- Nivel de detalle del modulo de caja en MVP.
- Herramienta exacta para OCR.
- Estructura final de reportes HTML.

## Proxima iteracion de diseno

Temas a definir antes de implementar:

1. Flujo exacto de venta desde telefono.
2. Flujo exacto de importacion/revision de ventas.
3. Modelo de caja.
4. Modelo FIFO.
5. Pantallas o formularios del MVP.
6. Esquema inicial DuckDB.
7. Carpeta y estrategia de backups.

## Avance implementado

Fecha: 2026-06-12

Se creo una primera base tecnica del MVP:

- Estructura de carpetas del proyecto.
- Esquema inicial DuckDB en `scripts/schema.sql`.
- Script de inicializacion en `scripts/init_db.py`.
- Base creada en `data/orilla.duckdb`.
- Script de exportacion de stock en `scripts/export_foto_stock.py`.
- Archivo inicial `exports/foto_stock.json`.
- App fija de ventas en `app_ventas/index.html`.
- Manifest e icono para anclar la app al telefono.
- Documento especifico del flujo mobile en `docs/FLUJO_MOBILE.md`.
- Plantilla de stock inicial en `imports/stock_inicial/stock_inicial.csv`.
- Importador de stock inicial en `scripts/import_stock_inicial.py`.
- JSON de ejemplo de ventas mobile en `imports/ventas_mobile/ventas_mobile_ejemplo.json`.
- Importador/revisor de ventas mobile en `scripts/import_ventas_mobile.py`.
- Modulo interactivo de compras para Spyder en `scripts/compras_interactivo.py`.
- Documento de uso de compras interactivas en `docs/COMPRAS_INTERACTIVO_SPYDER.md`.
- Script de reinicio seguro de base en `scripts/reset_db_seguro.py`.

Decision operativa posterior:

- Los scripts deben ejecutarse con el Python de Anaconda/Spyder usado habitualmente en la maquina.
- Python definido: `C:\Users\Martin\anaconda3\python.exe`.
- No se usaran runtimes alternativos ni instalaciones locales en `vendor/python` para este proyecto.

La app mobile:

- Intenta actualizar `foto_stock.json` automaticamente al abrir.
- Usa cache-busting con timestamp.
- Guarda solo el ultimo catalogo descargado.
- No guarda historial de catalogos.
- Guarda ventas pendientes separadas del catalogo.
- Permite exportar ventas pendientes a JSON.

El importador de stock inicial:

- Lee producto, color, talle, precio sugerido, stock inicial y costo unitario inicial.
- Genera SKUs automaticamente.
- Crea movimientos de stock inicial.
- Crea lotes FIFO iniciales.
- Evita duplicar stock inicial si se corre de nuevo.

El importador de ventas mobile:

- Lee el JSON exportado por la app.
- Corre por defecto en modo revision.
- Con `--confirmar` inserta la venta en DuckDB.
- Valida SKU, medio de cobro, duplicados y stock.
- Calcula costo FIFO y margen antes de importar.
- Registra venta, linea, pago, movimiento de stock, movimiento de caja y asignacion FIFO.
- Evita duplicar ventas usando `mobile_sale_uid`.

Prueba realizada:

- Se importo una venta de ejemplo `ejemplo-venta-001`.
- Venta neta: $25.000.
- Costo FIFO: $12.000.
- Margen: $13.000.
- Stock de `ORI-000001` bajo de 2 a 1.

Modulo de compras interactivas:

- No usa CSV.
- Esta pensado para usar desde Spyder.
- Permite listar y mostrar comprobantes de `comprobantes/compras/`.
- Usa Tesseract OCR desde `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- Permite construir una compra en memoria.
- Permite revisar totales y costos FIFO antes de confirmar.
- Al confirmar registra compra, lineas, stock, lotes FIFO, caja, proveedor y alias de producto.

Prueba realizada:

- Se cargo una compra interactiva de prueba para `Top Demo`.
- Se creo SKU `ORI-000004`.
- Stock agregado: 2 unidades.
- Egreso de caja registrado: -$17.000.
