#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_-]{4,}", text.lower()))


def verdict_for_score(score: int) -> str:
    if score >= 8:
        return "KNOWN_FIX"
    if score >= 5:
        return "LIKELY_MATCH"
    if score >= 3:
        return "WEAK_SIGNAL"
    return "NO_MATCH"


def search_memory(query: str, memory_dir: Path) -> dict[str, object]:
    query_tokens = tokenize(query)
    lessons = []

    for path in sorted((memory_dir / "lessons").glob("*.md")):
        text = path.read_text(errors="ignore")
        lesson_tokens = tokenize(text)
        overlap = sorted(query_tokens & lesson_tokens)
        score = len(overlap)
        if score == 0:
            continue
        title = text.splitlines()[0].lstrip("# ").strip() if text else path.stem
        lessons.append(
            {
                "title": title,
                "path": str(path),
                "score": score,
                "overlap": overlap[:10],
            }
        )

    lessons.sort(key=lambda item: item["score"], reverse=True)
    top_score = lessons[0]["score"] if lessons else 0
    return {
        "query": query,
        "verdict": verdict_for_score(top_score),
        "matches": lessons[:5],
    }


def render_markdown(result: dict[str, object]) -> str:
    lines = [
        "# Memory Lookup",
        "",
        f"- Query: `{result['query']}`",
        f"- Verdict: `{result['verdict']}`",
        "",
    ]
    matches = result["matches"]
    if not matches:
        lines.append("- No matching lessons found.")
        return "\n".join(lines)

    lines.append("## Matches")
    for match in matches:
        overlap = ", ".join(f"`{token}`" for token in match["overlap"])
        lines.append(
            f"- {match['title']} | score={match['score']} | overlap: {overlap} | path: `{match['path']}`"
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search modular lesson memory.")
    parser.add_argument("--query", required=True, help="Query or symptom to search for.")
    parser.add_argument(
        "--memory-dir",
        default=str(Path(__file__).resolve().parent.parent / "memory"),
        help="Memory directory containing lessons.",
    )
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = search_memory(args.query, Path(args.memory_dir))
    if args.format == "json":
        print(json.dumps(result, indent=2))
        return
    print(render_markdown(result))


if __name__ == "__main__":
    main()
