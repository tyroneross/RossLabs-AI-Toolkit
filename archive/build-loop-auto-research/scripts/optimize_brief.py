#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from core import optimize_brief_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optimize a rough build brief.")
    parser.add_argument("--text", help="Inline rough brief text.")
    parser.add_argument("--input-file", help="File containing the rough brief.")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.input_file:
        text = Path(args.input_file).expanduser().read_text()
    elif args.text:
        text = args.text
    else:
        raise SystemExit("Provide --text or --input-file.")

    result = optimize_brief_text(text)
    if args.format == "json":
        print(json.dumps({"optimized_brief": result}, indent=2))
        return
    print(result)


if __name__ == "__main__":
    main()
