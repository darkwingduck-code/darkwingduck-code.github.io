#!/usr/bin/env python3
"""Fail on likely sensitive data and malformed Technical Notes posts.

The scanner deliberately uses only Python's standard library so it can run in
the existing GitHub Pages workflow without installing extra dependencies.
It is a high-signal guardrail, not a substitute for human review.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "_posts"
TEXT_ROOTS = (ROOT / "_posts", ROOT / "_tabs", ROOT / "docs", ROOT / "languages")


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    rule: str
    excerpt: str


SENSITIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private-key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    ),
    ("chat-history-url", re.compile(r"https?://(?:www\.)?chatgpt\.com/c/")),
    ("local-file-uri", re.compile(r"\bfile://")),
    (
        "windows-user-path",
        re.compile(r"(?i)\b[A-Z]:\\Users\\(?!example\\|<[^>]+>\\)[^\\\s]+\\"),
    ),
    (
        "unix-user-path",
        re.compile(r"/(?:home|Users)/(?!example/|<[^>]+>/)[^/\s]+/"),
    ),
    (
        "email-address",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    ),
    (
        "korean-mobile-number",
        re.compile(r"(?<!\d)01[016789][ -]?\d{3,4}[ -]?\d{4}(?!\d)"),
    ),
    ("resident-id-shape", re.compile(r"(?<!\d)\d{6}[ -]?[1-4]\d{6}(?!\d)")),
)

REQUIRED_FRONT_MATTER = ("title", "date", "categories", "tags", "description")
POST_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
DATE_VALUE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2} (?:[+-]\d{4}|[+-]\d{2}:\d{2})$"
)
SUPPORTED_LANGUAGES = ("ko-KR", "ja-JP", "en", "fr-FR", "de-DE")
LANGUAGE_SUFFIXES = {"ko-KR": "", "ja-JP": "ja", "en": "en", "fr-FR": "fr", "de-DE": "de"}
TRANSLATION_INCLUDE = "{% include language-switcher.html %}"


def iter_text_files() -> list[Path]:
    paths: list[Path] = [ROOT / "README.md"]
    for directory in TEXT_ROOTS:
        if directory.exists():
            paths.extend(sorted(directory.rglob("*.md")))
    return [path for path in paths if path.exists()]


def front_matter(path: Path, text: str) -> tuple[dict[str, str], int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, 0

    try:
        closing = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return {}, -1

    values: dict[str, str] = {}
    for line in lines[1:closing]:
        match = re.match(r"^([a-z_]+):\s*(.*?)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2)
    return values, closing


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def scan_sensitive(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in SENSITIVE_PATTERNS:
            if pattern.search(line):
                findings.append(
                    Finding(
                        path=path,
                        line=line_number,
                        rule=rule,
                        excerpt=line.strip()[:160],
                    )
                )
    return findings


def validate_post(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    relative = path.relative_to(ROOT)

    if not POST_NAME.fullmatch(path.name):
        findings.append(Finding(relative, 1, "post-filename", path.name))

    metadata, closing = front_matter(path, text)
    if closing <= 0:
        findings.append(Finding(relative, 1, "front-matter", "missing closing ---"))
        return findings

    for key in REQUIRED_FRONT_MATTER:
        if not metadata.get(key):
            findings.append(Finding(relative, 1, "front-matter", f"missing {key}"))

    lang = unquote(metadata.get("lang", ""))
    if lang not in SUPPORTED_LANGUAGES:
        findings.append(Finding(relative, 1, "language", f"expected one of {SUPPORTED_LANGUAGES}, got {lang!r}"))

    translation_exempt = metadata.get("translation_exempt") == "true"
    translation_key = unquote(metadata.get("translation_key", ""))
    if not translation_exempt:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", translation_key):
            findings.append(Finding(relative, 1, "translation-key", translation_key or "missing translation_key"))
        if TRANSLATION_INCLUDE not in text:
            findings.append(Finding(relative, closing + 2, "language-switcher", f"add {TRANSLATION_INCLUDE}"))
        suffix = LANGUAGE_SUFFIXES.get(lang)
        if translation_key and suffix is not None:
            translated_slug = translation_key if not suffix else f"{translation_key}-{suffix}"
            expected_name = f"{path.name[:11]}{translated_slug}.md"
            if path.name != expected_name:
                findings.append(Finding(relative, 1, "translation-filename", f"expected {expected_name}"))
        if lang in SUPPORTED_LANGUAGES and lang != "ko-KR" and metadata.get("hidden") != "true":
            findings.append(Finding(relative, 1, "translation-visibility", "non-Korean editions need `hidden: true`"))

    date = unquote(metadata.get("date", ""))
    if date and not DATE_VALUE.fullmatch(date):
        findings.append(Finding(relative, 1, "date-format", date))

    for key in ("categories", "tags"):
        value = metadata.get(key, "")
        if value and not (value.startswith("[") and value.endswith("]")):
            findings.append(Finding(relative, 1, f"{key}-format", value))

    categories = metadata.get("categories", "")
    if categories.startswith("[") and categories.endswith("]"):
        category_items = [unquote(item.strip()) for item in categories[1:-1].split(",") if item.strip()]
        if len(category_items) != 2:
            findings.append(
                Finding(relative, 1, "categories-count", f"expected 2, got {len(category_items)}")
            )

    tags = metadata.get("tags", "")
    if tags:
        for tag in (unquote(item.strip()) for item in tags[1:-1].split(",")):
            if tag and tag != tag.lower():
                findings.append(Finding(relative, 1, "tag-case", tag))
            if tag and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", tag):
                findings.append(Finding(relative, 1, "tag-format", tag))

    if re.search(r"^```mermaid\s*$", text, re.MULTILINE) and metadata.get("mermaid") != "true":
        findings.append(Finding(relative, 1, "mermaid-flag", "add `mermaid: true`"))

    if re.search(r"\$\$|\\\(|\\\[", text) and metadata.get("math") != "true":
        findings.append(Finding(relative, 1, "math-flag", "add `math: true`"))

    fence_count = sum(1 for line in text.splitlines() if line.strip().startswith("```"))
    if fence_count % 2:
        findings.append(Finding(relative, 1, "markdown-fence", f"odd count: {fence_count}"))

    if text.count("$$") % 2:
        findings.append(Finding(relative, 1, "math-delimiter", "unbalanced $$ delimiter"))
    for opening, closing_delimiter in ((r"\[", r"\]"), (r"\(", r"\)")):
        opening_count = text.count(opening)
        closing_count = text.count(closing_delimiter)
        if opening_count != closing_count:
            findings.append(Finding(relative, 1, "math-delimiter", f"{opening}={opening_count}, {closing_delimiter}={closing_count}"))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-incomplete-translations", action="store_true")
    args = parser.parse_args()

    findings: list[Finding] = []
    paths = iter_text_files()
    titles: dict[str, Path] = {}
    translation_groups: dict[str, dict[str, Path]] = {}

    for path in paths:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        findings.extend(scan_sensitive(relative, text))
        if path.parent == POSTS:
            findings.extend(validate_post(path, text))
            metadata, _ = front_matter(path, text)
            title = metadata.get("title", "").strip('"\'')
            if title in titles:
                findings.append(
                    Finding(relative, 1, "duplicate-title", f"also used by {titles[title]}")
                )
            elif title:
                titles[title] = relative

            if metadata.get("translation_exempt") != "true":
                translation_key = unquote(metadata.get("translation_key", ""))
                lang = unquote(metadata.get("lang", ""))
                if translation_key and lang:
                    group = translation_groups.setdefault(translation_key, {})
                    if lang in group:
                        findings.append(Finding(relative, 1, "duplicate-translation", f"{translation_key}/{lang} also used by {group[lang]}"))
                    else:
                        group[lang] = relative

    expected_languages = set(SUPPORTED_LANGUAGES)
    for translation_key, group in sorted(translation_groups.items()):
        actual_languages = set(group)
        if actual_languages != expected_languages and not args.allow_incomplete_translations:
            missing = sorted(expected_languages - actual_languages)
            extra = sorted(actual_languages - expected_languages)
            details: list[str] = []
            if missing:
                details.append(f"missing {', '.join(missing)}")
            if extra:
                details.append(f"unsupported {', '.join(extra)}")
            findings.append(Finding(next(iter(group.values())), 1, "translation-completeness", f"{translation_key}: {'; '.join(details)}"))

    if findings:
        print("Content audit failed:", file=sys.stderr)
        for finding in findings:
            print(
                f"- {finding.path}:{finding.line} [{finding.rule}] {finding.excerpt}",
                file=sys.stderr,
            )
        return 1

    post_count = len(list(POSTS.glob("*.md")))
    print(f"Content audit passed: {len(paths)} Markdown files, {post_count} posts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
