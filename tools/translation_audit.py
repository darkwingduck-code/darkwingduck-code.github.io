#!/usr/bin/env python3
"""Check multilingual coverage and preservation of technical material."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "_posts"
LANGUAGES = ("ko-KR", "ja-JP", "en", "fr-FR", "de-DE", "es")
FENCE = re.compile(
    r"^(?:```([^\n]*)\n(.*?)^```\s*$|~~~([^\n]*)\n(.*?)^~~~\s*$)",
    re.MULTILINE | re.DOTALL,
)
URL = re.compile(r"https?://[^\s)>\]}'\"]+")
HANGUL = re.compile(r"[가-힣]")
JAPANESE_KANA = re.compile(r"[\u3040-\u30ff]")
NON_LATIN_PROSE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
LATIN_WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿÄÖÜäöüß]+")
LATIN_STOPWORDS = {
    "en": frozenset(
        "a an and are as at be by can for from has have if in into is it not of on or that the their this to was were when which with will".split()
    ),
    "fr-FR": frozenset(
        "au aux avec ce ces cette comme dans de des du elle en est et être il ils la le les leur mais ne nous ou par pas pour que qui se sont sur un une vous".split()
    ),
    "de-DE": frozenset(
        "aber als auf aus bei das dass dem den der des die ein eine einer einem einen es für im in ist kann mit nicht oder sind sich und von wenn werden wird zu zum zur".split()
    ),
    "es": frozenset(
        "al como con cuando de del el en es esta este la las lo los más no o para por que se sin son su sus un una y".split()
    ),
}


@dataclass(frozen=True)
class Post:
    path: Path
    metadata: dict[str, str]
    body: str


def parse(path: Path) -> Post:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    closing = lines.index("---", 1)
    values: dict[str, str] = {}
    for line in lines[1:closing]:
        match = re.match(r"^([a-z_]+):\s*(.*?)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2).strip('"\'')
    return Post(path, values, "\n".join(lines[closing + 1 :]))


def exact_code_blocks(body: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for backtick_language, backtick_block, tilde_language, tilde_block in FENCE.findall(body):
        language = backtick_language or tilde_language
        block = backtick_block or tilde_block
        if language.strip().lower() != "mermaid":
            blocks.append((language.strip(), block.rstrip()))
    return blocks


def mermaid_count(body: str) -> int:
    return sum(
        1
        for backtick_language, _, tilde_language, _ in FENCE.findall(body)
        if (backtick_language or tilde_language).strip().lower() == "mermaid"
    )


def formula_blocks(body: str) -> list[str]:
    blocks = re.findall(r"\$\$(.*?)\$\$", body, re.DOTALL)
    blocks.extend(re.findall(r"\\\[(.*?)\\\]", body, re.DOTALL))
    return [re.sub(r"\\text\{[^{}]*\}", r"\\text{<LOCALIZED_TEXT>}", block.strip()) for block in blocks]


def inline_formula_blocks(body: str) -> list[str]:
    prose = FENCE.sub("", body)
    prose = re.sub(r"`[^`\n]*`", "", prose)
    blocks = re.findall(r"\\\((.*?)\\\)", prose, re.DOTALL)
    blocks.extend(re.findall(r"(?<!\$)\$(?!\$)([^$\n]+?)(?<!\$)\$(?!\$)", prose))
    return [re.sub(r"\\text\{[^{}]*\}", r"\\text{<LOCALIZED_TEXT>}", block.strip()) for block in blocks]


def prose_only(body: str) -> str:
    return FENCE.sub("", body)


def latin_language_scores(text: str) -> dict[str, int]:
    tokens = (token.lower() for token in LATIN_WORD.findall(text))
    counts = Counter(tokens)
    return {
        language: sum(counts[word] for word in stopwords)
        for language, stopwords in LATIN_STOPWORDS.items()
    }


def compare(source: Post, target: Post) -> list[str]:
    errors: list[str] = []
    label = f"{target.metadata.get('translation_key')}/{target.metadata.get('lang')}"
    if exact_code_blocks(source.body) != exact_code_blocks(target.body):
        errors.append(f"{label}: non-Mermaid fenced code changed")
    if mermaid_count(source.body) != mermaid_count(target.body):
        errors.append(f"{label}: Mermaid block count changed")
    if formula_blocks(source.body) != formula_blocks(target.body):
        errors.append(f"{label}: display formulas changed")
    if Counter(inline_formula_blocks(source.body)) - Counter(inline_formula_blocks(target.body)):
        errors.append(f"{label}: inline formulas changed")
    if Counter(URL.findall(source.body)) != Counter(URL.findall(target.body)):
        errors.append(f"{label}: external URL set changed")
    source_headings = len(re.findall(r"^#{2,6}\s+", source.body, re.MULTILINE))
    target_headings = len(re.findall(r"^#{2,6}\s+", target.body, re.MULTILINE))
    if source_headings != target_headings:
        errors.append(f"{label}: heading count changed ({source_headings} -> {target_headings})")
    if target.metadata.get("title") == source.metadata.get("title"):
        errors.append(f"{label}: title was not translated")
    if target.metadata.get("description") == source.metadata.get("description"):
        errors.append(f"{label}: description was not translated")
    localized = "\n".join((target.metadata.get("title", ""), target.metadata.get("description", ""), prose_only(target.body)))
    if HANGUL.search(localized):
        errors.append(f"{label}: Korean prose remains outside fenced blocks")
    if target.metadata.get("lang") == "ja-JP" and not JAPANESE_KANA.search(localized):
        errors.append(f"{label}: Japanese prose heuristic failed (no kana found)")
    target_language = target.metadata.get("lang")
    if target_language in LATIN_STOPWORDS:
        if NON_LATIN_PROSE.search(localized):
            errors.append(f"{label}: Japanese or CJK prose remains in a Latin-language edition")
        scores = latin_language_scores(localized)
        target_score = scores[target_language]
        competing_score = max(score for language, score in scores.items() if language != target_language)
        if target_score < 12 or target_score <= competing_score:
            errors.append(
                f"{label}: target-language prose heuristic failed "
                "(scores: " + ", ".join(f"{language}={score}" for language, score in scores.items()) + ")"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-incomplete", action="store_true")
    parser.add_argument("--language", choices=LANGUAGES[1:])
    args = parser.parse_args()
    groups: dict[str, dict[str, Post]] = defaultdict(dict)
    errors: list[str] = []
    for path in sorted(POSTS.glob("*.md")):
        post = parse(path)
        if post.metadata.get("translation_exempt") == "true":
            continue
        key = post.metadata.get("translation_key", "")
        lang = post.metadata.get("lang", "")
        if not key or not lang:
            errors.append(f"{path.name}: missing translation metadata")
            continue
        if lang in groups[key]:
            errors.append(f"{key}/{lang}: duplicate edition")
            continue
        groups[key][lang] = post
    expected = set(LANGUAGES)
    for key, editions in sorted(groups.items()):
        actual = set(editions)
        if actual != expected and not args.allow_incomplete:
            errors.append(f"{key}: language set is {sorted(actual)}, expected {sorted(expected)}")
            continue
        if "ko-KR" not in editions:
            errors.append(f"{key}: Korean source edition is missing")
            continue
        source = editions["ko-KR"]
        target_languages = (args.language,) if args.language else LANGUAGES[1:]
        for lang in target_languages:
            if lang in editions:
                errors.extend(compare(source, editions[lang]))
    if errors:
        print("Translation audit failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    edition_count = sum(len(editions) for editions in groups.values())
    print(f"Translation audit passed: {len(groups)} groups, {edition_count} editions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
