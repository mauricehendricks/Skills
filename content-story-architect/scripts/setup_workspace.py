#!/usr/bin/env python3
"""Create, remember, or validate a Content Storytelling Kit workspace."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

DIRECTORIES = ("frameworks", "content", "references", "sessions")
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "content-story-architect"
CONFIG_FILE = CONFIG_DIR / "config.json"


def read_config() -> dict[str, str]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read configuration: {exc}") from exc
    return data if isinstance(data, dict) else {}


def configured_workspace() -> Path | None:
    raw = read_config().get("workspace")
    return Path(raw).expanduser().resolve() if raw else None


def validate_workspace(workspace: Path) -> list[str]:
    errors: list[str] = []
    if not workspace.is_dir():
        return [f"Workspace does not exist: {workspace}"]
    for name in DIRECTORIES:
        if not (workspace / name).is_dir():
            errors.append(f"Missing directory: {workspace / name}")
    return errors


def write_config(workspace: Path) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"workspace": str(workspace)}, indent=2) + "\n"
    handle, temp_name = tempfile.mkstemp(prefix="config-", suffix=".json", dir=CONFIG_DIR)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(payload)
        os.replace(temp_name, CONFIG_FILE)
    finally:
        temp_path = Path(temp_name)
        if temp_path.exists():
            temp_path.unlink()


def setup(path: str) -> int:
    workspace = Path(path).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    for name in DIRECTORIES:
        (workspace / name).mkdir(exist_ok=True)
    write_config(workspace)
    print(workspace)
    return 0


def show() -> int:
    workspace = configured_workspace()
    if workspace is None:
        print("No Content Storytelling Kit is configured.", file=sys.stderr)
        return 1
    print(workspace)
    return 0


def check() -> int:
    workspace = configured_workspace()
    if workspace is None:
        print("No Content Storytelling Kit is configured.", file=sys.stderr)
        return 1
    errors = validate_workspace(workspace)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Valid Content Storytelling Kit: {workspace}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--path", help="Create or reconnect to this workspace path.")
    group.add_argument("--show", action="store_true", help="Show the configured workspace path.")
    group.add_argument("--check", action="store_true", help="Validate the configured workspace.")
    args = parser.parse_args()
    if args.path:
        return setup(args.path)
    if args.show:
        return show()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())

