#!/usr/bin/env python3
"""Restore inline-math delimiters that were dropped during translation.

The repair is deliberately conservative: it only rewrites an exact source
formula found inside plain ASCII or full-width parentheses, and never touches
fenced code, display math, inline code, or an existing inline-math span.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

from translation_audit import POSTS, inline_formula_blocks, parse

LANGUAGE_SUFFIX = {"ja-JP": "ja", "en": "en", "fr-FR": "fr", "de-DE": "de"}
FENCED = r"^```[^\n]*\n.*?^```\s*$|^~~~[^\n]*\n.*?^~~~\s*$"
PROTECTED = re.compile(
    rf"(?:{FENCED}|\$\$.*?\$\$|\\\[.*?\\\]|`[^`\n]*`|\\\(.*?\\\))",
    re.MULTILINE | re.DOTALL,
)
RAW_INLINE = re.compile(r"\\\((.*?)\\\)|(?<!\$)\$(?!\$)([^$\n]+?)(?<!\$)\$(?!\$)", re.DOTALL)


def normalize(expression: str) -> str:
    return re.sub(r"\\text\{[^{}]*\}", r"\\text{<LOCALIZED_TEXT>}", expression.strip())


def raw_inline_formulas(body: str) -> list[str]:
    body = re.sub(FENCED, "", body, flags=re.MULTILINE | re.DOTALL)
    body = re.sub(r"`[^`\n]*`", "", body)
    return [(match.group(1) or match.group(2)).strip() for match in RAW_INLINE.finditer(body)]


def replace_outside_protected(text: str, needle: str, replacement: str, limit: int) -> tuple[str, int]:
    output: list[str] = []
    position = 0
    replaced = 0
    for match in PROTECTED.finditer(text):
        chunk = text[position : match.start()]
        if replaced < limit:
            count = min(chunk.count(needle), limit - replaced)
            chunk = chunk.replace(needle, replacement, count)
            replaced += count
        output.extend((chunk, match.group(0)))
        position = match.end()
    chunk = text[position:]
    if replaced < limit:
        count = min(chunk.count(needle), limit - replaced)
        chunk = chunk.replace(needle, replacement, count)
        replaced += count
    output.append(chunk)
    return "".join(output), replaced


def body_from_text(text: str) -> str:
    lines = text.splitlines()
    closing = lines.index("---", 1)
    return "\n".join(lines[closing + 1 :])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=tuple(LANGUAGE_SUFFIX), action="append", required=True)
    parser.add_argument("--key", action="append", help="limit repair to one or more translation keys")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    groups: dict[str, dict[str, Path]] = defaultdict(dict)
    for path in sorted(POSTS.glob("*.md")):
        post = parse(path)
        key = post.metadata.get("translation_key")
        lang = post.metadata.get("lang")
        if key and lang:
            groups[key][lang] = path

    changed = 0
    unresolved_total = 0
    for key, editions in sorted(groups.items()):
        if args.key and key not in args.key:
            continue
        source_path = editions.get("ko-KR")
        if source_path is None:
            continue
        source = parse(source_path)
        source_raw = raw_inline_formulas(source.body)
        for language in args.language:
            target_path = editions.get(language)
            if target_path is None:
                continue
            target = parse(target_path)
            available = Counter(inline_formula_blocks(target.body))
            missing: Counter[str] = Counter()
            for expression in source_raw:
                normalized = normalize(expression)
                if available[normalized]:
                    available[normalized] -= 1
                else:
                    missing[expression] += 1
            if not missing:
                continue

            text = target_path.read_text(encoding="utf-8")
            repaired = 0
            unresolved: Counter[str] = Counter()
            for expression, count in sorted(missing.items(), key=lambda item: len(item[0]), reverse=True):
                remaining = count
                for left, right in (("(", ")"), ("（", "）")):
                    if not remaining:
                        break
                    needle = f"{left}{expression}{right}"
                    replacement = rf"\({expression}\)"
                    text, restored = replace_outside_protected(text, needle, replacement, remaining)
                    repaired += restored
                    remaining -= restored
                if remaining:
                    unresolved[expression] += remaining

            remaining_missing = Counter(inline_formula_blocks(source.body)) - Counter(
                inline_formula_blocks(body_from_text(text))
            )
            normalized_unresolved: Counter[str] = Counter()
            for expression, count in unresolved.items():
                normalized_unresolved[normalize(expression)] += count
            if remaining_missing != normalized_unresolved:
                unresolved = Counter(remaining_missing)
            unresolved_total += sum(unresolved.values())
            print(
                f"{target_path.name}: restored={repaired}, unresolved={sum(unresolved.values())}"
            )
            for expression, count in unresolved.items():
                print(f"  {count} x {expression!r}")
            if args.write and repaired:
                target_path.write_text(text, encoding="utf-8")
                changed += 1

    mode = "updated" if args.write else "would update"
    print(f"Inline-math repair {mode} {changed} files; unresolved formulas: {unresolved_total}")
    return 1 if unresolved_total else 0


if __name__ == "__main__":
    raise SystemExit(main())
