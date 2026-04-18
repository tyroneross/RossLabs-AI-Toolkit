#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize build-loop-auto-research state files in a target repo.")
    parser.add_argument("--workdir", default=".", help="Target repo path.")
    parser.add_argument("--goal", default="", help="Goal text to seed into goal.md and state.json.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workdir = Path(args.workdir).expanduser().resolve()
    loop_dir = workdir / ".build-loop-auto-research"
    scorecards_dir = loop_dir / "scorecards"
    context_dir = loop_dir / "context" / "snapshots"
    lessons_dir = loop_dir / "lessons"
    scorecards_dir.mkdir(parents=True, exist_ok=True)
    context_dir.mkdir(parents=True, exist_ok=True)
    lessons_dir.mkdir(parents=True, exist_ok=True)

    goal_path = loop_dir / "goal.md"
    state_path = loop_dir / "state.json"

    if not goal_path.exists():
        goal_path.write_text(
            "\n".join(
                [
                    "# Goal",
                    "",
                    "## One-sentence goal",
                    args.goal or "Not set yet.",
                    "",
                    "## Expected UX improvement",
                    "",
                    "## Constraints",
                    "",
                    "## Scoring criteria",
                    "",
                ]
            )
        )

    if not state_path.exists():
        state = {
            "active": True,
            "phase": "ASSESS",
            "iteration": 0,
            "goal": args.goal,
            "confidence": "medium",
            "integration_points": [],
            "open_items": [],
            "lessons_written": [],
            "initialized_at": datetime.now(timezone.utc).isoformat(),
        }
        state_path.write_text(json.dumps(state, indent=2))

    print(json.dumps({"goal_path": str(goal_path), "state_path": str(state_path)}, indent=2))


if __name__ == "__main__":
    main()
