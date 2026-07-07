from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import duckdb

from import_ventas_mobile import (
    DB_PATH,
    SaleReview,
    import_confirmed,
    load_sales,
    print_review,
    review_sales,
)


ROOT = Path(__file__).resolve().parents[1]
TOKEN_PATH = ROOT / "config" / "github_token.txt"
DOWNLOAD_DIR = ROOT / "imports" / "ventas_mobile" / "github"

DEFAULT_OWNER = "quinteiromartin"
DEFAULT_REPO = "orilla-ventas-inbox"
DEFAULT_BRANCH = "main"
DEFAULT_FOLDER = "ventas"


def read_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text(encoding="utf-8").strip()
    raise SystemExit(
        "No encontre token de GitHub. Usar variable GITHUB_TOKEN o crear config/github_token.txt"
    )


def github_request(url: str, token: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "orilla-importer",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub HTTP {exc.code}: {body}") from exc


def list_json_files(owner: str, repo: str, folder: str, branch: str, token: str) -> list[dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{folder}?ref={branch}"
    payload = json.loads(github_request(url, token).decode("utf-8"))
    if not isinstance(payload, list):
        raise SystemExit("La respuesta de GitHub no es una lista de archivos")
    return [
        item
        for item in payload
        if item.get("type") == "file" and item.get("name", "").lower().endswith(".json")
    ]


def download_file(file_info: dict, token: str) -> Path:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = DOWNLOAD_DIR / file_info["name"]
    data = github_request(file_info["download_url"], token)
    target.write_bytes(data)
    return target


def load_github_sales(paths: list[Path]) -> tuple[list, dict[str, list[Path]]]:
    sales = []
    sale_paths: dict[str, list[Path]] = {}
    for path in paths:
        for sale in load_sales(path):
            sales.append(sale)
            sale_paths.setdefault(sale.mobile_sale_uid, []).append(path)
    return sales, sale_paths


def dedupe_reviews(reviews: list[SaleReview], sale_paths: dict[str, list[Path]]) -> list[SaleReview]:
    seen: set[str] = set()
    output: list[SaleReview] = []
    for review in reviews:
        uid = review.sale.mobile_sale_uid
        if uid in seen:
            paths = ", ".join(path.name for path in sale_paths.get(uid, []))
            output.append(
                SaleReview(
                    sale=review.sale,
                    status="OMITIR",
                    message=f"Venta duplicada en GitHub ({paths})",
                    item_reviews=[],
                )
            )
            continue
        seen.add(uid)
        output.append(review)
    return output


def print_github_sources(sale_paths: dict[str, list[Path]]) -> None:
    print("\nOrigenes GitHub")
    print("=" * 80)
    for uid, paths in sorted(sale_paths.items()):
        joined = ", ".join(path.name for path in paths)
        print(f"{uid}: {joined}")


def process_all(paths: list[Path], confirm: bool) -> tuple[int, int, int]:
    sales, sale_paths = load_github_sales(paths)
    with duckdb.connect(str(DB_PATH)) as con:
        reviews = review_sales(con, sales)
        reviews = dedupe_reviews(reviews, sale_paths)
        print("\nRevision consolidada GitHub")
        print_review(reviews)
        print_github_sources(sale_paths)

        errors = sum(1 for review in reviews if review.status == "ERROR")
        ok = sum(1 for review in reviews if review.status == "OK")
        omitted = sum(1 for review in reviews if review.status == "OMITIR")

        if not confirm:
            return ok, omitted, errors

        importable_reviews = [review for review in reviews if review.status == "OK"]
        if not importable_reviews:
            print("No hay ventas OK para importar.")
            return 0, omitted, errors

        con.execute("BEGIN TRANSACTION")
        try:
            imported = import_confirmed(con, importable_reviews, DOWNLOAD_DIR)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        print(f"Ventas importadas desde GitHub: {imported}")
        return imported, omitted, errors


def run(args: argparse.Namespace) -> None:
    token = read_token()
    files = list_json_files(args.owner, args.repo, args.folder, args.branch, token)
    print(f"Archivos JSON encontrados en GitHub: {len(files)}")
    if not files:
        return

    paths = []
    for file_info in sorted(files, key=lambda item: item["name"]):
        paths.append(download_file(file_info, token))

    total_ok, total_omitted, total_errors = process_all(paths, args.confirmar)

    print("\nResumen GitHub")
    print("=" * 80)
    if args.confirmar:
        print(f"Importadas: {total_ok}")
    else:
        print(f"OK para importar: {total_ok}")
        print("Modo revision. Para importar, volver a correr con --confirmar.")
    print(f"Omitidas: {total_omitted}")
    print(f"Errores: {total_errors}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Importa ventas mobile desde GitHub privado.")
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--folder", default=DEFAULT_FOLDER)
    parser.add_argument("--confirmar", action="store_true")
    return parser.parse_args()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
