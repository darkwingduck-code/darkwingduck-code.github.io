#!/usr/bin/env python3
"""Add deterministic multilingual metadata to Korean source posts."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "_posts"
SWITCHER = "{% include language-switcher.html %}"
POST_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\.md$")


def metadata(lines: list[str], closing: int) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines[1:closing]:
        match = re.match(r"^([a-z_]+):\s*(.*?)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def migrate(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"missing front matter: {path}")
    closing = lines.index("---", 1)
    values = metadata(lines, closing)
    if values.get("translation_exempt") == "true":
        return False
    if values.get("lang") not in (None, "ko-KR"):
        return False
    match = POST_NAME.fullmatch(path.name)
    if not match:
        raise ValueError(f"unexpected post filename: {path.name}")
    slug = match.group("slug")
    additions: list[str] = []
    if "lang" not in values:
        additions.append("lang: ko-KR")
    if "translation_key" not in values:
        additions.append(f"translation_key: {slug}")
    elif values["translation_key"] != slug:
        raise ValueError(f"translation_key mismatch in {path.name}")
    front = lines[:closing] + additions + ["---"]
    body = lines[closing + 1 :]
    while body and not body[0].strip():
        body.pop(0)
    if SWITCHER not in body:
        body = [SWITCHER, ""] + body
    updated = "\n".join(front + [""] + body) + "\n"
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    changed = [path for path in sorted(POSTS.glob("*.md")) if migrate(path)]
    print(f"Prepared {len(changed)} Korean source posts for translation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
