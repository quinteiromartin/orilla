# Publicacion en GitHub Pages

Objetivo:

- Jose entra siempre al mismo link.
- La app vive en `app_ventas/`.
- El stock publicado vive en `exports/foto_stock.json`.
- Cada vez que se actualiza DuckDB, se regenera `foto_stock.json` y se sube a GitHub.

## Estructura que debe publicarse

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

Por eso conviene publicar GitHub Pages desde la raiz del repo.

## Flujo operativo

1. Actualizar datos en DuckDB.
2. Regenerar stock:

```powershell
& "C:\Users\Martin\anaconda3\python.exe" scripts\export_foto_stock.py
```

3. Subir cambios a GitHub.
4. Jose abre siempre:

```text
https://<usuario>.github.io/<repo>/app_ventas/
```

## Inicializar repo local

Desde:

```powershell
cd "C:\Users\Martin\OneDrive\Trabajo\Orilla Tienda\sistema_integral"
```

Inicializar:

```powershell
git init
git add .
git commit -m "Initial Orilla management system"
```

Crear un repositorio en GitHub y vincularlo:

```powershell
git branch -M main
git remote add origin https://github.com/<usuario>/<repo>.git
git push -u origin main
```

## Activar GitHub Pages

En GitHub:

```text
Settings -> Pages -> Build and deployment
Source: Deploy from a branch
Branch: main
Folder: /root
Save
```

Luego abrir:

```text
https://<usuario>.github.io/<repo>/app_ventas/
```

## Importante

El archivo `exports/foto_stock.json` sera publico si el repo/GitHub Pages es publico.

