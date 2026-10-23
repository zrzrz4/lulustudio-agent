from __future__ import annotations

import argparse
import json

from .config import Settings
from .database import Database


def main() -> None:
    parser = argparse.ArgumentParser(prog="lulu-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db")
    serve = subparsers.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8010)
    export = subparsers.add_parser("export-trajectories")
    export.add_argument("--output")
    args = parser.parse_args()
    settings = Settings.from_env()

    if args.command == "init-db":
        Database(settings.db_path).init_schema()
        print(settings.db_path)
    elif args.command == "serve":
        import uvicorn

        uvicorn.run("lulustudio.api:app", host=args.host, port=args.port, reload=False)
    elif args.command == "export-trajectories":
        payload = json.dumps(Database(settings.db_path).export_trajectories(), ensure_ascii=False, indent=2)
        if args.output:
            from pathlib import Path

            Path(args.output).write_text(payload, encoding="utf-8")
        else:
            print(payload)


if __name__ == "__main__":
    main()
