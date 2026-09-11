"""Small CLI that calls the same API contract as the Vue app.

Usage from the backend directory:
    python -m cli.oa_cli capabilities
    python -m cli.oa_cli run --skill legacy.page.explain --input "案件列表"
"""

import argparse
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request(path: str, method: str = "GET", payload: dict[str, object] | None = None) -> dict[str, object]:
    base_url = os.environ.get("OA_API_URL", "http://127.0.0.1:8002")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if body else {}
    try:
        with urlopen(Request(f"{base_url}{path}", data=body, headers=headers, method=method), timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        raise SystemExit(f"OA API unavailable: {exc}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(prog="oa", description="Local OA Agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("health")
    subparsers.add_parser("capabilities")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--skill", required=True)
    run_parser.add_argument("--input", required=True)
    args = parser.parse_args()
    if args.command == "health":
        result = request("/health")
    elif args.command == "capabilities":
        result = request("/api/v1/agent/capabilities")
    else:
        result = request("/api/v1/agent/runs", "POST", {"skill": args.skill, "input": args.input})
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

