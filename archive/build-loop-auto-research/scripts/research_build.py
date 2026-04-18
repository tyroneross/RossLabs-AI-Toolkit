#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from core import build_research_packet, infer_artifact_mode, infer_mode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local research-build packet.")
    parser.add_argument("--task", required=True, help="Task or request text.")
    parser.add_argument(
        "--repo-path",
        default=".",
        help="Repo or project path to scan.",
    )
    parser.add_argument(
        "--mode",
        choices=("quick", "balanced", "max_accuracy"),
        help="Optimization mode override.",
    )
    parser.add_argument(
        "--artifact-mode",
        choices=("research_only", "plan_only", "research_plus_plan"),
        help="Artifact mode override.",
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
    mode = args.mode or infer_mode(args.task)
    artifact_mode = args.artifact_mode or infer_artifact_mode(args.task)
    packet = build_research_packet(
        task_text=args.task,
        repo_path=Path(args.repo_path).expanduser().resolve(),
        mode=mode,
        artifact_mode=artifact_mode,
    )
    if args.format == "json":
        print(
            json.dumps(
                {
                    "repo_path": str(Path(args.repo_path).expanduser().resolve()),
                    "mode": mode,
                    "artifact_mode": artifact_mode,
                    "packet": packet,
                },
                indent=2,
            )
        )
        return
    print(packet)


if __name__ == "__main__":
    main()
