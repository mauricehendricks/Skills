#!/usr/bin/env python3
"""Validate the required structure of one custom storytelling framework."""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

REQUIRED_FIELDS = ("Purpose", "Structure", "Best fit", "Key rule")
RESERVED_FRAMEWORK_NAMES = {
    "traditional linear story framework",
    "in medias res start in the middle framework",
    "viral framework question journey answer",
    "educational value driven framework",
    "hstss framework personal transformation",
}


def normalized_name(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value.lower()))


def field_pattern(field: str) -> re.Pattern[str]:
    escaped = re.escape(field)
    return re.compile(
        rf"(?im)^\s*(?:#{1,6}\s+{escaped}\s*$|[-*]\s+\*\*{escaped}:?\*\*\s*:?\s*\S.*$)"
    )


def validate(path: Path) -> list[str]:
    if path.suffix.lower() != ".md":
        return ["Framework must be a Markdown file (.md)."]
    if not path.is_file():
        return [f"Framework file does not exist: {path}"]
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    title = re.search(r"(?m)^#\s+(.+?)\s*$", text)
    if not title:
        errors.append("Framework must have a level-one title.")
    elif normalized_name(title.group(1)) in RESERVED_FRAMEWORK_NAMES:
        errors.append("Custom framework name collides with a bundled framework.")
    errors.extend(
        f"Missing or empty required field: {field}"
        for field in REQUIRED_FIELDS
        if not field_pattern(field).search(text)
    )
    structure_match = re.search(r"(?im)^\s*[-*]\s+\*\*Structure:?\*\*.*$", text)
    if structure_match:
        tail = text[structure_match.end():]
        next_field = re.search(r"(?im)^\s*[-*]\s+\*\*(?:Best fit|Key rule):?\*\*", tail)
        structure_body = tail[: next_field.start()] if next_field else tail
        if len(re.findall(r"(?m)^\s+\d+\.\s+\*\*.+?\*\*", structure_body)) < 2:
            errors.append("Structure must contain at least two ordered, named beats.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("framework", type=Path)
    args = parser.parse_args()
    errors = validate(args.framework.resolve())
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Valid custom framework structure: {args.framework.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
