from __future__ import annotations

import argparse
import json
from urllib import error, request


def _fetch_json(url: str, method: str = "GET", body: dict | None = None) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
      data = json.dumps(body).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Interact with the Data Quality Triage Assistant API")
    parser.add_argument("--base-url", default="http://127.0.0.1:7860", help="Server base URL")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    health = _fetch_json(f"{base_url}/health")
    reset = _fetch_json(f"{base_url}/reset", method="POST", body={"task_id": "easy_missing_and_dupes"})

    print(json.dumps({"health": health, "reset": reset}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except error.URLError as exc:
        raise SystemExit(f"Failed to contact environment: {exc}") from exc