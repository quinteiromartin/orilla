from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOKEN_PATH = ROOT / "config" / "github_token.txt"

DEFAULT_OWNER = "quinteiromartin"
DEFAULT_REPO = "orilla-ventas-inbox"
DEFAULT_BRANCH = "main"
DEFAULT_FOLDER = "ventas"


@dataclass
class GithubFile:
    name: str
    path: str
    sha: str


def read_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text(encoding="utf-8").strip()
    raise SystemExit("No encontre token. Crear config/github_token.txt o usar GITHUB_TOKEN.")


def github_request(url: str, token: str, method: str = "GET", payload: dict | None = None) -> bytes:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "orilla-cleaner",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub HTTP {exc.code}: {body}") from exc


def list_json_files(owner: str, repo: str, folder: str, branch: str, token: str) -> list[GithubFile]:
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{folder}?ref={branch}"
    payload = json.loads(github_request(url, token).decode("utf-8"))
    if not isinstance(payload, list):
        raise SystemExit("La respuesta de GitHub no es una lista.")
    files = []
    for item in payload:
        if item.get("type") == "file" and item.get("name", "").lower().endswith(".json"):
            files.append(GithubFile(name=item["name"], path=item["path"], sha=item["sha"]))
    return sorted(files, key=lambda item: item.name)


def delete_file(owner: str, repo: str, branch: str, token: str, file: GithubFile) -> None:
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file.path}"
    github_request(
        url,
        token,
        method="DELETE",
        payload={
            "message": f"Eliminar venta de prueba {file.name}",
            "sha": file.sha,
            "branch": branch,
        },
    )


def run(args: argparse.Namespace) -> None:
    token = read_token()
    files = list_json_files(args.owner, args.repo, args.folder, args.branch, token)
    if not files:
        print("No hay JSONs en GitHub.")
        return

    keep = args.keep or files[-1].name
    to_delete = [file for file in files if file.name != keep]

    print(f"JSONs encontrados: {len(files)}")
    print(f"Se conserva: {keep}")
    print("Se borrarian:")
    for file in to_delete:
        print(f"- {file.name}")

    if not args.confirmar:
        print("Modo revision. No se borro nada. Para borrar, correr con --confirmar.")
        return

    for file in to_delete:
        delete_file(args.owner, args.repo, args.branch, token, file)
        print(f"Borrado: {file.name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Limpia JSONs viejos de ventas en GitHub.")
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--folder", default=DEFAULT_FOLDER)
    parser.add_argument("--keep", help="Nombre exacto del JSON que se quiere conservar. Default: el mas nuevo por nombre.")
    parser.add_argument("--confirmar", action="store_true")
    return parser.parse_args()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()

