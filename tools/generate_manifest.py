#!/usr/bin/env python3
"""Generate the post and translation manifest."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "_posts"
OUTPUT = ROOT / "docs" / "POST_MANIFEST.md"
LANGUAGES = ("ko-KR", "ja-JP", "en", "fr-FR", "de-DE", "es")
LABELS = {"ko-KR": "KO", "ja-JP": "JA", "en": "EN", "fr-FR": "FR", "de-DE": "DE", "es": "ES"}


def parse(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    closing = lines.index("---", 1)
    values: dict[str, str] = {}
    for line in lines[1:closing]:
        match = re.match(r"^([a-z_]+):\s*(.*?)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2).strip('"\'')
    return values


def main() -> int:
    groups: dict[str, dict[str, tuple[Path, dict[str, str]]]] = defaultdict(dict)
    for path in sorted(POSTS.glob("*.md")):
        meta = parse(path)
        if meta.get("translation_exempt") == "true":
            continue
        key, lang = meta.get("translation_key", ""), meta.get("lang", "")
        if key and lang:
            groups[key][lang] = (path, meta)
    counts = {lang: sum(lang in editions for editions in groups.values()) for lang in LANGUAGES}
    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M KST")
    lines = [
        "# Technical Notes 포스트·번역 manifest", "", f"생성 시각: {now}", "",
        f"- 지식 단위: {len(groups)}편", f"- 언어판: {sum(counts.values())}개",
        "- 언어별 수: " + ", ".join(f"{LABELS[x]} {counts[x]}" for x in LANGUAGES),
        "- 한국어판이 의미 기준 원문이며 나머지 판은 같은 `translation_key`로 연결됩니다.", "",
        "| # | translation_key | 한국어 제목 | KO | JA | EN | FR | DE | ES |",
        "|---:|---|---|---|---|---|---|---|---|",
    ]
    for index, (key, editions) in enumerate(sorted(groups.items()), start=1):
        title = editions.get("ko-KR", (Path(), {}))[1].get("title", key).replace("|", "\\|")
        links = []
        for lang in LANGUAGES:
            links.append(f"[{LABELS[lang]}](../_posts/{editions[lang][0].name})" if lang in editions else "—")
        lines.append(f"| {index} | `{key}` | {title} | " + " | ".join(links) + " |")
    lines += ["", "## 검증 명령", "", "```bash", "python3 tools/content_audit.py", "python3 tools/translation_audit.py", "bash tools/test.sh", "```", ""]
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {OUTPUT.relative_to(ROOT)} with {len(groups)} groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
