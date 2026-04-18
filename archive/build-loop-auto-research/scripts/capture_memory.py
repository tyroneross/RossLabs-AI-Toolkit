#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture a modular lesson-memory note.")
    parser.add_argument("--title", required=True, help="Short lesson title.")
    parser.add_argument("--situation", required=True, help="Context for the lesson.")
    parser.add_argument("--what-happened", required=True, help="What went wrong or required iteration.")
    parser.add_argument("--why", required=True, help="Why it happened.")
    parser.add_argument(
        "--specific-improvement",
        required=True,
        help="How to improve future iterations in this specific situation.",
    )
    parser.add_argument(
        "--general-improvement",
        required=True,
        help="How to solve this class of problem better next time.",
    )
    parser.add_argument("--signals", default="", help="Early warning signals to watch for.")
    parser.add_argument("--confidence-impact", default="", help="How this affected confidence.")
    parser.add_argument("--related", default="", help="Related files, systems, or integrations.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plugin_root = Path(__file__).resolve().parent.parent
    memory_dir = plugin_root / "memory"
    lessons_dir = memory_dir / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{timestamp}-{slugify(args.title)}.md"
    lesson_path = lessons_dir / filename

    lesson_body = "\n".join(
        [
            f"# {args.title}",
            "",
            "## Situation",
            args.situation,
            "",
            "## What happened",
            args.what_happened,
            "",
            "## Why it happened",
            args.why,
            "",
            "## What to do differently in this specific situation",
            args.specific_improvement,
            "",
            "## How to solve this class of problem better next time",
            args.general_improvement,
            "",
            "## Signals to detect earlier",
            args.signals or "None recorded.",
            "",
            "## Confidence impact",
            args.confidence_impact or "Not recorded.",
            "",
            "## Related files / systems",
            args.related or "Not recorded.",
            "",
        ]
    )
    lesson_path.write_text(lesson_body)

    index_path = memory_dir / "MEMORY.md"
    index_text = index_path.read_text() if index_path.exists() else "# Build Loop Research Memory\n\n## Lesson Index\n"
    entry = f"- [{args.title}](./lessons/{filename})"
    if entry not in index_text:
        if "- No lessons captured yet." in index_text:
            index_text = index_text.replace("- No lessons captured yet.", entry)
        else:
            index_text = index_text.rstrip() + "\n" + entry + "\n"
        index_path.write_text(index_text)

    print(lesson_path)


if __name__ == "__main__":
    main()
