"""Run the ratification tool locally.

  atr-ratify --reviewer person:slug --reviewer-name "Teacher Name"

Opens a local web page (default http://127.0.0.1:8000) where a teacher reviews the
ingested techniques and writes corrections to data/taxonomy/ratifications.json.
"""

from __future__ import annotations

import argparse

import uvicorn

from .app import create_app


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="atr-ratify", description="Teacher ratification loop")
    p.add_argument("--reviewer", default="person:reviewing-teacher",
                   help="person:<slug> of the ratifying teacher (keyed to the data map)")
    p.add_argument("--reviewer-name", default=None, help="display name of the teacher")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args(argv)

    app = create_app(args.reviewer, args.reviewer_name)
    who = args.reviewer_name or args.reviewer
    print(f"ATR ratification -- reviewer: {who}")
    print(f"Open http://{args.host}:{args.port}/  (Ctrl-C to stop)")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
