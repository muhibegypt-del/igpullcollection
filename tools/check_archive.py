"""Check generated archive coverage and local Markdown links."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "archive"
manifest = json.loads((ARCHIVE / "manifest.json").read_text(encoding="utf-8"))
posts = manifest["posts"]
post_ids = {post["shortcode"] for post in posts}
source_ids = {path.name for path in ROOT.iterdir() if path.is_dir() and len(path.name) == 11}
assert len(posts) == len(post_ids) == 504
assert post_ids == source_ids
assert len(list((ARCHIVE / "posts").glob("*.md"))) == len(posts)

media = {item for post in posts for item in post["media"]}
assert len(media) == manifest["counts"]["images"] + manifest["counts"]["videos"]
assert all((ROOT / item).is_file() for item in media)

missing: list[str] = []
checked = 0
for doc in [ROOT / "README.md", *ARCHIVE.rglob("*.md")]:
    text = doc.read_text(encoding="utf-8")
    for target in re.findall(r"(?<!!)\[[^\]\n]+\]\(([^)]+)\)", text):
        if re.match(r"^[a-z]+://", target, re.I):
            continue
        checked += 1
        target_path = (doc.parent / unquote(target.split("#", 1)[0])).resolve()
        if not target_path.exists():
            missing.append(f"{doc.relative_to(ROOT)} -> {target}")

if missing:
    raise SystemExit("Missing links:\n" + "\n".join(missing[:50]))
print(f"Checked {len(posts)} posts, {len(media)} media files, {checked} local links; all passed.")
