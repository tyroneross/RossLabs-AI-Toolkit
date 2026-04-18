#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restore the latest local context snapshot.")
    parser.add_argument("--workdir", default=".", help="Project directory that contains .build-loop-auto-research/context.")
    parser.add_argument("--list", action="store_true", help="List available snapshots instead of restoring the latest.")
    parser.add_argument("--max-age-days", type=int, default=7, help="Maximum age before a snapshot is treated as stale.")
    parser.add_argument(
        "--registry-dir",
        default=str(Path.home() / ".build-loop-auto-research"),
        help="Directory that stores the global registry.",
    )
    return parser.parse_args()


def is_stale(path: Path, max_age_days: int) -> bool:
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return modified < datetime.now(timezone.utc) - timedelta(days=max_age_days)


def main() -> None:
    args = parse_args()
    workdir = Path(args.workdir).expanduser().resolve()
    snapshots_dir = workdir / ".build-loop-auto-research" / "context" / "snapshots"
    snapshots = sorted(snapshots_dir.glob("*.md"))
    registry_path = Path(args.registry_dir).expanduser().resolve() / "registry.json"

    if args.list:
        for snapshot in snapshots[-10:]:
            print(snapshot.name)
        return

    warning = None
    source = "current-workspace"
    target_path: Path | None = snapshots[-1] if snapshots else None

    if target_path is None and registry_path.exists():
        registry = json.loads(registry_path.read_text())
        last_active = registry.get("last_active_workspace")
        workspace_entry = registry.get("workspaces", {}).get(last_active or "", {})
        candidate = workspace_entry.get("latest_snapshot_path")
        if candidate:
            target_path = Path(candidate)
            source = "registry-fallback"
            if last_active and Path(last_active) != workdir:
                warning = f"Path mismatch: restoring from `{last_active}` instead of current workspace `{workdir}`."

    if target_path is None or not target_path.exists():
        raise SystemExit("No context snapshots found.")

    if is_stale(target_path, args.max_age_days):
        raise SystemExit(f"Latest snapshot is stale: {target_path}")

    if warning:
        print(f"WARNING: {warning}\n")
    print(f"Source: {source}\n")
    print(target_path.read_text())


if __name__ == "__main__":
    main()
