#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture a local context snapshot for the current project.")
    parser.add_argument("--workdir", default=".", help="Project directory to write the context snapshot into.")
    parser.add_argument(
        "--registry-dir",
        default=str(Path.home() / ".build-loop-auto-research"),
        help="Directory that stores the global registry.",
    )
    parser.add_argument("--summary", default="", help="Current task summary.")
    parser.add_argument("--status", default="", help="Current status.")
    parser.add_argument("--decision", action="append", default=[], help="Key decision. Repeat as needed.")
    parser.add_argument("--open-item", action="append", default=[], help="Open item. Repeat as needed.")
    parser.add_argument("--unknown", action="append", default=[], help="Unknown or blocker. Repeat as needed.")
    parser.add_argument("--file", action="append", default=[], help="Important file. Repeat as needed.")
    parser.add_argument("--trigger", default="manual", help="Why the snapshot was taken.")
    return parser.parse_args()


def bulletize(values: list[str], empty_text: str) -> list[str]:
    if not values:
        return [f"- {empty_text}"]
    return [f"- {value}" for value in values]


def main() -> None:
    args = parse_args()
    workdir = Path(args.workdir).expanduser().resolve()
    context_dir = workdir / ".build-loop-auto-research" / "context"
    snapshots_dir = context_dir / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    global_dir = Path(args.registry_dir).expanduser().resolve()
    global_dir.mkdir(parents=True, exist_ok=True)
    registry_path = global_dir / "registry.json"

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    snapshot_path = snapshots_dir / f"{timestamp}.md"
    current_path = context_dir / "current-context.md"
    trailhead_path = context_dir / "trailhead.md"
    identity_path = context_dir / "identity.json"

    content = [
        "# Context Snapshot",
        "",
        f"- Trigger: `{args.trigger}`",
        f"- Timestamp: `{timestamp}`",
        "",
        "## Current task",
        args.summary or "Not provided.",
        "",
        "## Status",
        args.status or "Not provided.",
        "",
        "## Key decisions",
        *bulletize(args.decision, "No decisions recorded."),
        "",
        "## Open items",
        *bulletize(args.open_item, "No open items recorded."),
        "",
        "## Unknowns",
        *bulletize(args.unknown, "No unknowns recorded."),
        "",
        "## Important files",
        *bulletize(args.file, "No files recorded."),
        "",
    ]
    body = "\n".join(content)
    snapshot_path.write_text(body)
    current_path.write_text(body)
    trailhead_path.write_text(body)
    identity_path.write_text(
        json.dumps(
            {
                "workspace_path": str(workdir),
                "workspace_name": workdir.name,
                "updated_at": timestamp,
            },
            indent=2,
        )
    )

    registry = {
        "last_active_workspace": str(workdir),
        "workspaces": {},
    }
    if registry_path.exists():
        registry = json.loads(registry_path.read_text())
    registry.setdefault("workspaces", {})
    registry["last_active_workspace"] = str(workdir)
    registry["workspaces"][str(workdir)] = {
        "workspace_name": workdir.name,
        "updated_at": timestamp,
        "trailhead_path": str(trailhead_path),
        "latest_snapshot_path": str(snapshot_path),
    }
    registry_path.write_text(json.dumps(registry, indent=2))

    print(json.dumps({"snapshot_path": str(snapshot_path), "trailhead_path": str(trailhead_path)}, indent=2))


if __name__ == "__main__":
    main()
