#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from core import analyze_history_dir, render_history_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Codex archived sessions.")
    parser.add_argument(
        "--history-dir",
        default=str(Path.home() / ".codex" / "archived_sessions"),
        help="Directory containing archived Codex JSONL sessions.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = analyze_history_dir(Path(args.history_dir).expanduser())
    if args.format == "json":
        print(json.dumps(summary, indent=2))
        return
    print(render_history_markdown(summary))


if __name__ == "__main__":
    main()
