#!/usr/bin/env python3
"""Stargate Atlantis: strict offline completeness + metadata quality gate (stdlib only)."""
from pathlib import Path
import json
import re
import sys

root = Path(__file__).resolve().parent
files = sorted(root.glob("season-*/S??E??-*.md"))
issues = []
word_counts = []
seen = set()

def field(text, name):
    match = re.search(r"^" + re.escape(name) + r":\s*(.*?)\s*$", text, re.M)
    return match.group(1).strip() if match else None

expected_codes = {
    f"S{season:02d}E{episode:02d}"
    for season in range(1, 6) for episode in range(1, 21)
}
for path in files:
    code = path.name[:6]
    match = re.fullmatch(r"S(0[1-5])E(0[1-9]|1[0-9]|20)-[a-z0-9-]+\.md", path.name)
    if match is None:
        issues.append(f"{path.name}: invalid filename")
        continue
    season, episode = int(match.group(1)), int(match.group(2))
    if path.parent.name != f"season-{season:02d}":
        issues.append(f"{path.name}: wrong season directory")
    if code in seen:
        issues.append(f"{code}: duplicate episode identifier")
    seen.add(code)
    content = path.read_text(encoding="utf-8")
    if field(content, "status") != "complete":
        issues.append(f"{code}: status must be complete")
    if field(content, "source_verified") != "true":
        issues.append(f"{code}: source_verified must be true")
    if field(content, "spoilers") != "true":
        issues.append(f"{code}: spoilers must be true")
    if field(content, "season") != str(season) or field(content, "episode") != str(episode):
        issues.append(f"{code}: season/episode metadata mismatch")
    if field(content, "series") != '"Stargate Atlantis"':
        issues.append(f"{code}: series metadata mismatch")
    if not field(content, "title_original"):
        issues.append(f"{code}: missing original title")
    if "## Türkçe olay özeti\n\n" not in content or "\n\n## Kaynaklar" not in content:
        issues.append(f"{code}: missing synopsis/source section")
        continue
    summary = content.split("## Türkçe olay özeti\n\n", 1)[1].split("\n\n## Kaynaklar", 1)[0].strip()
    count = len(summary.split())
    word_counts.append(count)
    declared = field(content, "word_count")
    if declared != str(count):
        issues.append(f"{code}: stated words {declared}; actual {count}")
    if not 250 <= count <= 400:
        issues.append(f"{code}: synopsis word count outside 250–400 ({count})")
    if not re.search(r"https://www\.gateworld\.net/atlantis/s[1-5]/[^)\s]+", content):
        issues.append(f"{code}: missing GateWorld episode source")
    if not re.search(r"https://stargate-sg1-solutions\.com/wiki/[^)\s]+", content):
        issues.append(f"{code}: missing StargateWiki episode source")

missing = sorted(expected_codes - seen)
extra = sorted(seen - expected_codes)
if len(files) != 100:
    issues.append(f"Episode file count {len(files)} != 100")
for season in range(1, 6):
    actual = sum(1 for code in seen if code.startswith(f"S{season:02d}"))
    if actual != 20:
        issues.append(f"Season {season}: {actual} != 20")
if missing:
    issues.append(f"Missing episode IDs: {', '.join(missing)}")
if extra:
    issues.append(f"Unexpected episode IDs: {', '.join(extra)}")

catalog = (root / "CATALOG.md").read_text(encoding="utf-8")
for code in expected_codes:
    if code not in catalog:
        issues.append(f"Catalog missing {code}")
readme = (root / "README.md").read_text(encoding="utf-8")
if "Tamamlanmış özet: **100/100**" not in readme:
    issues.append("README completion count differs from strict catalog")
result = {
    "expected": 100,
    "files": len(files),
    "complete": sum(field(p.read_text(encoding="utf-8"), "status") == "complete" for p in files),
    "minimum_words": min(word_counts, default=0),
    "maximum_words": max(word_counts, default=0),
    "total_summary_words": sum(word_counts),
    "issues": issues,
    "result": "PASS" if not issues else "FAIL",
}
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(1 if issues else 0)
