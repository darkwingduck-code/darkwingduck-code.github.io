#!/usr/bin/env python3
"""Generate Spanish editions from the English editions.

Technical tokens are replaced with opaque placeholders before translation so
URLs, code, formulas, Liquid tags, and HTML remain byte-for-byte stable.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "_posts"
ENDPOINT = "https://translate.googleapis.com/translate_a/single"
FENCE = re.compile(r"^(```|~~~)")
PROTECTED = re.compile(
    r"(`[^`\n]+`|"
    r"\{\%.*?\%\}|\{\{.*?\}\}|"
    r"\{:\s*[^}\n]+\}|"
    r"https?://[^\s)>\]}'\"]+|"
    r"\\\(.+?\\\)|\\\[.*?\\\]|\$\$.*?\$\$|(?<!\$)\$(?!\$).+?(?<!\$)\$(?!\$)|"
    r"<[^>\n]+>|"
    r"\b[A-Z][A-Z0-9/+.-]{1,}\b|"
    r"\b(?:Airflow|Bowtie|Codex|CUDA|Docker|GitHub|JAX|Kubernetes|Mermaid|"
    r"OpenID|Parquet|PowerShell|PyTorch|Temporal|Terraform|Windows|WSL|"
    r"prompt|Prompt)\b)",
    re.DOTALL,
)
FRONT_VALUE = re.compile(r"^(title|description):\s*(.*)$")


def request_translation(text: str, retries: int = 6) -> str:
    query = urllib.parse.urlencode(
        {"client": "gtx", "sl": "en", "tl": "es", "dt": "t", "q": text}
    )
    request = urllib.request.Request(
        f"{ENDPOINT}?{query}",
        headers={"User-Agent": "technical-notes-spanish-generator/1.0"},
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.load(response)
            return "".join(segment[0] for segment in payload[0] if segment[0])
        except Exception:
            if attempt + 1 == retries:
                raise
            time.sleep(min(30, 2 ** attempt))
    raise AssertionError("unreachable")


def protect(text: str) -> tuple[str, list[str]]:
    values: list[str] = []

    def replace(match: re.Match[str]) -> str:
        token = f"<x-keep-{len(values):05d}/>"
        values.append(match.group(0))
        return token

    return PROTECTED.sub(replace, text), values


def restore(text: str, values: list[str]) -> str:
    for index, value in enumerate(values):
        token = re.compile(rf"<x-keep-{index:05d}\s*/>", re.IGNORECASE)
        if not token.search(text):
            raise ValueError(f"translator changed protected token {token}")
        text = token.sub(lambda _: value, text)
    leftovers = re.findall(r"<x-keep-\d{5}\s*/>", text, re.IGNORECASE)
    if leftovers:
        raise ValueError(f"unrestored protected tokens: {leftovers[:3]}")
    return text


def translate_text(text: str) -> str:
    if not re.search(r"[A-Za-z]", text):
        return text
    leading = re.match(r"^\s*", text).group(0)
    trailing = re.search(r"\s*$", text).group(0)
    end = len(text) - len(trailing) if trailing else len(text)
    core = text[len(leading) : end]
    if not core:
        return text
    protected, values = protect(core)
    translated = request_translation(protected)
    return leading + restore(translated, values) + trailing


def translate_body(body: str, max_chars: int = 3200) -> str:
    lines = body.splitlines(keepends=True)
    output: list[str] = []
    prose: list[str] = []
    prose_length = 0
    in_fence = False
    math_closer = ""

    def flush() -> None:
        nonlocal prose, prose_length
        if prose:
            output.append(translate_text("".join(prose)))
            prose = []
            prose_length = 0

    for line in lines:
        stripped = line.strip()
        if math_closer:
            flush()
            output.append(line)
            if math_closer in stripped:
                math_closer = ""
            continue
        if stripped.startswith("$$") and stripped.count("$$") == 1:
            flush()
            output.append(line)
            math_closer = "$$"
            continue
        if stripped.startswith(r"\[") and r"\]" not in stripped:
            flush()
            output.append(line)
            math_closer = r"\]"
            continue
        if FENCE.match(line):
            flush()
            output.append(line)
            in_fence = not in_fence
            continue
        if in_fence:
            output.append(line)
            continue
        if prose and prose_length + len(line) > max_chars:
            flush()
        prose.append(line)
        prose_length += len(line)
    flush()
    return "".join(output)


def parse_document(path: Path) -> tuple[list[str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing front matter: {path}")
    closing = text.index("\n---\n", 4)
    front = text[4:closing].splitlines()
    return front, text[closing + 5 :]


def translate_front(front: list[str]) -> list[str]:
    translated: list[str] = []
    for line in front:
        match = FRONT_VALUE.match(line)
        if match:
            key, value = match.groups()
            quote = '"' if value.startswith('"') and value.endswith('"') else ""
            raw = value[1:-1] if quote else value
            localized = translate_text(raw).replace('"', '\\"') if quote else translate_text(raw)
            translated.append(f"{key}: {quote}{localized}{quote}")
        elif line.startswith("lang:"):
            translated.append("lang: es")
        else:
            translated.append(line)
    return translated


def output_path(source: Path) -> Path:
    return source.with_name(f"{source.stem[:-3]}-es.md")


def generate(source: Path, force: bool) -> Path:
    target = output_path(source)
    if target.exists() and not force:
        return target
    front, body = parse_document(source)
    localized = "---\n" + "\n".join(translate_front(front)) + "\n---\n" + translate_body(body)
    target.write_text(localized, encoding="utf-8", newline="\n")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--key", action="append", default=[])
    args = parser.parse_args()
    sources = sorted(POSTS.glob("*-en.md"))
    if args.key:
        keys = set(args.key)
        sources = [
            source
            for source in sources
            if any(source.stem.endswith(f"-{key}-en") for key in keys)
        ]
    sources = sources[max(0, args.start - 1) :]
    if args.limit is not None:
        sources = sources[: args.limit]
    for index, source in enumerate(sources, start=1):
        target = generate(source, args.force)
        print(f"[{index}/{len(sources)}] {target.name}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
