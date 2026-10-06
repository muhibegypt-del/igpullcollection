"""Build a browsable Markdown archive from local OCR and speech records.

Original media folders remain untouched. Generated files live under archive/.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from theme_rules import FALLBACK, RULES, VISUAL, classify, slug

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "archive"
IMG_OCR = OUT / "source-data" / "image-ocr.jsonl"
VIDEO_OCR = OUT / "source-data" / "video-frame-ocr.jsonl"
SPEECH = OUT / "source-data" / "video-speech.jsonl"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ""}
VIDEO_EXT = {".mp4"}
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def shortcode_order(shortcode: str) -> int:
    number = 0
    for character in shortcode:
        number = number * 64 + ALPHABET.index(character)
    return number


def media_sort_key(path: Path) -> tuple[int, int, str]:
    stem = path.stem
    match = re.search(r"_(\d+)$", stem)
    number = int(match.group(1)) if match else 0
    return (1 if "_cover" in stem else 0, number, path.name.lower())


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def md_link(path: str, label: str) -> str:
    return f"[{label}](../../{path})"


def pretty_time(seconds: float) -> str:
    whole = int(seconds)
    return f"{whole // 60:02d}:{whole % 60:02d}"


def clean_for_compare(text: str) -> str:
    text = re.sub(r"@(?:muhibthewriter|muhiblog|relytsikcaj)\b", " ", text, flags=re.I)
    text = re.sub(r"\bMuhib\b", " ", text, flags=re.I)
    text = re.sub(r"https?://\S+|\S+\.substack\.com", " ", text, flags=re.I)
    return re.sub(r"[^\w]+", " ", text.casefold()).strip()


def image_paragraphs(lines: list[dict]) -> list[str]:
    if not lines:
        return []
    heights = []
    for line in lines:
        box = line.get("box") or []
        if box:
            heights.append(max(point[1] for point in box) - min(point[1] for point in box))
    typical_height = statistics.median(heights) if heights else 30
    paragraphs: list[list[str]] = []
    current: list[str] = []
    previous_bottom: float | None = None
    for line in lines:
        text = line["text"].strip()
        if not text:
            continue
        box = line.get("box") or []
        top = min((point[1] for point in box), default=0)
        bottom = max((point[1] for point in box), default=top)
        gap = top - previous_bottom if previous_bottom is not None else 0
        begins_list = bool(re.match(r"^(?:[-•]|\d+[.)])\s", text))
        if current and (gap > max(24, typical_height * 0.8) or begins_list):
            paragraphs.append(current)
            current = []
        current.append(text)
        previous_bottom = bottom
    if current:
        paragraphs.append(current)
    return [" ".join(part).replace("- ", "-") for part in paragraphs]


def title_from(post_id: str, images: list[tuple[Path, dict]], speech: list[dict]) -> str:
    for _, record in images:
        # A low-confidence image can be a photo with accidental lettering.
        # Do not turn that lettering into a post title.
        lines = record.get("lines", [])
        if lines and statistics.mean(line["score"] for line in lines) < 0.85:
            continue
        for paragraph in image_paragraphs(record.get("lines", [])):
            text = paragraph.strip(" -|•\t")
            text = re.sub(r"(?i)^muhib\s*[∞o.]?\s*@\w+\s*", "", text).strip()
            if not text or re.fullmatch(r"@\w+", text):
                continue
            if re.fullmatch(r"(?i)muhib\.?", text):
                continue
            if text.casefold() in {"thoughts in public", "thoughts in public."}:
                continue
            if len(text.split()) == 1 and text.isupper() and len(text) > 6:
                continue
            if len(text) < 8:
                continue
            sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
            candidate = sentence if len(sentence) <= 90 else text[:87].rsplit(" ", 1)[0] + "…"
            return candidate.replace("#", "").replace("\n", " ")
    for record in speech:
        for segment in record.get("segments", []):
            text = segment["text"].strip()
            if len(text) >= 8:
                return (text[:87].rsplit(" ", 1)[0] + "…") if len(text) > 90 else text
    return f"Post {post_id}"


def source_url(post_id: str, media: list[Path]) -> tuple[str, str]:
    videos = [path for path in media if path.suffix.lower() in VIDEO_EXT]
    non_covers = [path for path in media if path.suffix.lower() in IMAGE_EXT and "_cover" not in path.stem]
    kind = "reel" if videos and not non_covers else "post"
    return f"https://www.instagram.com/{'reel' if kind == 'reel' else 'p'}/{post_id}/", kind


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_duplicate_groups(posts: dict[str, dict]) -> list[list[str]]:
    parent = {post_id: post_id for post_id in posts}

    def find(value: str) -> str:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(first: str, second: str) -> None:
        parent[find(second)] = find(first)

    by_exact: dict[str, list[str]] = defaultdict(list)
    by_prefix: dict[str, list[str]] = defaultdict(list)
    for post_id, post in posts.items():
        normalized = clean_for_compare(post["text"])
        post["comparison_text"] = normalized
        if len(normalized) >= 50:
            by_exact[normalized].append(post_id)
        if len(normalized) >= 100:
            by_prefix[" ".join(normalized.split()[:8])].append(post_id)
    for group in by_exact.values():
        for other in group[1:]:
            union(group[0], other)
    for candidates in by_prefix.values():
        for index, first in enumerate(candidates):
            for second in candidates[index + 1:]:
                a, b = posts[first]["comparison_text"], posts[second]["comparison_text"]
                if min(len(a), len(b)) / max(len(a), len(b)) < 0.85:
                    continue
                if SequenceMatcher(None, a, b, autojunk=False).ratio() >= 0.94:
                    union(first, second)
    grouped: dict[str, list[str]] = defaultdict(list)
    for post_id in posts:
        grouped[find(post_id)].append(post_id)
    return [sorted(group, key=shortcode_order) for group in grouped.values() if len(group) > 1]


def frame_ocr_segments(records: list[dict]) -> list[dict]:
    segments: list[dict] = []
    active: dict[str, dict] = {}
    for frame in sorted(records, key=lambda row: row["approx_second"]):
        second = frame["approx_second"]
        for line in frame.get("lines", []):
            text = line["text"].strip()
            normalized = clean_for_compare(text)
            # Low-confidence background lettering can dominate a whole reel.
            # Preserve readable lines individually; merge consecutive sightings
            # without repeating a fixed title or subtitle on every frame.
            if line["score"] < 0.85 or len(normalized) < 3:
                continue
            existing = active.get(normalized)
            if existing and second <= existing["end"] + 2:
                existing["end"] = second
                if line["score"] > existing["score"]:
                    existing["text"] = text
                    existing["score"] = line["score"]
                continue
            segment = {"start": second, "end": second, "text": text, "score": line["score"]}
            segments.append(segment)
            active[normalized] = segment
    return sorted(segments, key=lambda item: item["start"])


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    image_rows = rows(IMG_OCR)
    frame_rows = rows(VIDEO_OCR)
    speech_rows = rows(SPEECH)
    image_by_path = {row["path"]: row for row in image_rows}
    frame_by_path = {row["frame_path"]: row for row in frame_rows}
    frame_by_video: dict[str, list[dict]] = defaultdict(list)
    for row in frame_rows:
        frame_by_video[row["video_path"]].append(row)
    speech_by_video = {row["video_path"]: row for row in speech_rows}

    post_dirs = sorted(
        (path for path in ROOT.iterdir() if path.is_dir() and len(path.name) == 11 and all(char in ALPHABET for char in path.name)),
        key=lambda p: shortcode_order(p.name),
    )
    originals = [path for directory in post_dirs for path in directory.iterdir() if path.is_file()]
    images = [path for path in originals if path.suffix.lower() in IMAGE_EXT]
    videos = [path for path in originals if path.suffix.lower() in VIDEO_EXT]
    other = [rel(path) for path in originals if path not in images and path not in videos]
    assert not other, f"Unexpected original file types: {other}"
    assert len(image_by_path) == len(images) and set(image_by_path) == {rel(path) for path in images}
    assert len(speech_by_video) == len(videos) and set(speech_by_video) == {rel(path) for path in videos}
    assert set(frame_by_video) == {rel(path) for path in videos}
    assert len(frame_by_path) == len(frame_rows), "Repeated frame OCR records"
    assert not any("error" in row for row in image_rows + frame_rows + speech_rows), "OCR or speech errors need review"

    media_hashes: dict[str, list[str]] = defaultdict(list)
    for path in originals:
        media_hashes[sha256(path)].append(rel(path))

    posts: dict[str, dict] = {}
    for directory in post_dirs:
        post_id = directory.name
        media = sorted((path for path in directory.iterdir() if path.is_file()), key=media_sort_key)
        post_images = [(path, image_by_path[rel(path)]) for path in media if path in images]
        post_videos = [(path, speech_by_video[rel(path)]) for path in media if path in videos]
        parts = [line["text"] for _, row in post_images for line in row.get("lines", [])]
        parts.extend(segment["text"] for _, row in post_videos for segment in row.get("segments", []))
        text = " ".join(parts)
        visible_handles = sorted({
            handle.lower() for _, row in post_images
            for line in row.get("lines", [])[:4]
            for handle in re.findall(r"@([A-Za-z0-9_.]+)", line["text"])
            if handle.lower() not in {"muhibthewriter", "muhiblog"}
        })
        primary, themes, scores, uncertain = classify(text)
        url, kind = source_url(post_id, media)
        posts[post_id] = {
            "shortcode": post_id,
            "media": [rel(path) for path in media],
            "images": post_images,
            "videos": post_videos,
            "title": title_from(post_id, post_images, [row for _, row in post_videos]),
            "text": text,
            "source_url": url,
            "source_url_inferred": True,
            "kind": kind,
            "primary_theme": primary,
            "themes": themes,
            "theme_scores": scores,
            "theme_uncertain": uncertain,
            "other_handles_visible": visible_handles,
            "image_ocr_low_score_lines": sum(sum(line["score"] < 0.85 for line in row.get("lines", [])) for _, row in post_images),
            "images_without_text": [rel(path) for path, row in post_images if not row.get("lines")],
        }

    duplicates = text_duplicate_groups(posts)
    duplicate_lookup = {post_id: group for group in duplicates for post_id in group}
    for post_id, post in posts.items():
        post["duplicate_group"] = duplicate_lookup.get(post_id, [])

    video_text_dir = OUT / "video-text"
    for video_path, records in frame_by_video.items():
        path = ROOT / video_path
        segments = frame_ocr_segments(records)
        lines = [
            f"# On-screen text: {path.stem}", "",
            f"Video: {md_link(video_path, path.name)}", "",
            "OCR sampled one frame per second. Lines below 0.85 confidence were omitted from this readable view; timings are approximate. Text may be incomplete or misread.", "",
        ]
        if not segments:
            lines.append("No on-screen text detected in the sampled frames.")
        for segment in segments:
            when = pretty_time(segment["start"])
            if segment["end"] > segment["start"]:
                when += f"–{pretty_time(segment['end'])}"
            lines.append(f"- **{when}** {segment['text']}")
        write_text(video_text_dir / f"{path.stem}.md", "\n".join(lines))

    for post_id, post in posts.items():
        header = [
            "---",
            f"shortcode: {json.dumps(post_id)}",
            f"source_url: {json.dumps(post['source_url'])}",
            f"post_type: {json.dumps(post['kind'])}",
            "published_date: null",
            "caption_available: false",
            f"primary_theme: {json.dumps(post['primary_theme'], ensure_ascii=False)}",
            "themes:",
            *[f"  - {json.dumps(theme, ensure_ascii=False)}" for theme in post["themes"]],
            "transcription_reviewed: false",
            "---", "",
            f"# {post['title']}", "",
            f"[Instagram post]({post['source_url']}) · Source URL inferred from the shortcode · Publication date unavailable", "",
            "Themes: " + ", ".join(f"[{theme}](../themes/{slug(theme)}.md)" for theme in post["themes"]), "",
            "> Automated transcription for research and organization. Check wording against the original media before publication.", "",
            "## Caption", "", "The source repository contains no Instagram caption for this post.", "",
            "## Image text", "",
        ]
        if not post["images"]:
            header.append("No still image files in this post.")
        for index, (path, record) in enumerate(post["images"], 1):
            header.extend(["", f"### Image {index}: `{path.name}`", "", md_link(rel(path), "Open original image"), ""])
            paragraphs = image_paragraphs(record.get("lines", []))
            if paragraphs:
                header.extend([paragraph + "\n" for paragraph in paragraphs])
            else:
                header.append("_No text detected in this image._")
            low = [line for line in record.get("lines", []) if line["score"] < 0.85]
            if low:
                header.extend(["", f"_Review suggested: {len(low)} OCR line(s) below 0.85 confidence._"])

        if post["videos"]:
            header.extend(["", "## Videos and spoken text", ""])
            for index, (path, record) in enumerate(post["videos"], 1):
                header.extend([
                    f"### Video {index}: `{path.name}`", "",
                    md_link(rel(path), "Open original video"), "",
                    f"[Time-stamped on-screen OCR](../video-text/{path.stem}.md)", "",
                    "**Automated speech transcript**", "",
                ])
                if record.get("segments"):
                    header.extend(f"- **{pretty_time(segment['start'])}** {segment['text']}" for segment in record["segments"])
                elif record.get("no_audio_stream"):
                    header.append("_This clip has no audio stream._")
                else:
                    header.append("_No English speech detected._")
                header.append("")

        if post["duplicate_group"]:
            others = [other for other in post["duplicate_group"] if other != post_id]
            header.extend([
                "## Related copies", "",
                "Similar or identical text also appears in: " + ", ".join(f"[{other}]({other}.md)" for other in others) + ".", "",
            ])
        flags = []
        if post["theme_uncertain"]:
            flags.append("Theme assignment is tentative.")
        if post["image_ocr_low_score_lines"]:
            flags.append(f"{post['image_ocr_low_score_lines']} low-confidence image OCR line(s).")
        if post["images_without_text"]:
            flags.append(f"{len(post['images_without_text'])} image(s) yielded no OCR text.")
        if post["other_handles_visible"]:
            flags.append("Other handle(s) visible near the top of media: " + ", ".join("@" + handle for handle in post["other_handles_visible"]) + ". Check attribution before reuse.")
        if flags:
            header.extend(["## Review notes", "", *[f"- {flag}" for flag in flags], ""])
        write_text(OUT / "posts" / f"{post_id}.md", "\n".join(header))

    theme_names = list(RULES) + [FALLBACK, VISUAL]
    theme_members: dict[str, list[str]] = {name: [] for name in theme_names}
    for post_id, post in posts.items():
        for theme in post["themes"]:
            theme_members[theme].append(post_id)
    for theme, members in theme_members.items():
        lines = [
            f"# {theme}", "",
            "Suggested theme links from automated text classification. A post can appear in several themes.", "",
            f"{len(members)} posts", "",
        ]
        for post_id in sorted(members, key=shortcode_order, reverse=True):
            post = posts[post_id]
            lines.append(f"- [{post['title']}](../posts/{post_id}.md) — `{post_id}`")
        write_text(OUT / "themes" / f"{slug(theme)}.md", "\n".join(lines))

    ordered_posts = sorted(posts, key=shortcode_order, reverse=True)
    index = [
        "# All posts", "",
        f"{len(posts)} post folders. Order follows shortcode media IDs, not verified publication dates.", "",
        "| Post | Primary theme | Media | Notes |", "|---|---|---:|---|",
    ]
    for post_id in ordered_posts:
        post = posts[post_id]
        title = post["title"].replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")
        notes = []
        if post["duplicate_group"]:
            notes.append("related copy")
        if post["theme_uncertain"]:
            notes.append("theme review")
        if post["image_ocr_low_score_lines"]:
            notes.append("OCR review")
        index.append(f"| [{title}](posts/{post_id}.md) | {post['primary_theme']} | {len(post['media'])} | {', '.join(notes)} |")
    write_text(OUT / "INDEX.md", "\n".join(index))

    duplicates_page = ["# Repeated material", "", "Posts stay separate; these links surface text and media reused across posts.", ""]
    duplicates_page.extend(["## Repeated post text", ""])
    if not duplicates:
        duplicates_page.append("No repeated text groups detected by the current comparison rules.")
    for group in sorted(duplicates, key=lambda values: shortcode_order(values[0])):
        duplicates_page.append("- " + ", ".join(f"[{post_id}](posts/{post_id}.md)" for post_id in group))
    repeated_media = [paths for paths in media_hashes.values() if len({p.split('/')[0] for p in paths}) > 1]
    duplicates_page.extend(["", "## Identical media files", ""])
    if not repeated_media:
        duplicates_page.append("No binary-identical media reused across posts.")
    for group in repeated_media:
        duplicates_page.append("- " + ", ".join(f"`{path}`" for path in group))
    write_text(OUT / "DUPLICATES.md", "\n".join(duplicates_page))

    low_ocr = [(post_id, post["image_ocr_low_score_lines"]) for post_id, post in posts.items() if post["image_ocr_low_score_lines"]]
    uncertain_theme = [post_id for post_id, post in posts.items() if post["theme_uncertain"]]
    no_image_text = [(post_id, path) for post_id, post in posts.items() for path in post["images_without_text"]]
    other_attribution = [(post_id, post["other_handles_visible"]) for post_id, post in posts.items() if post["other_handles_visible"]]
    review = [
        "# Review queue", "",
        "All text is machine-generated and should be checked against the original media before reuse in a book.", "",
        "## Missing from the source archive", "",
        "- Instagram captions: no caption files were present.",
        "- Publication dates: no date metadata was present.",
        "- Original Instagram URLs are inferred from folder shortcodes and have not been individually verified.", "",
        f"## Low-confidence image OCR ({len(low_ocr)} posts)", "",
    ]
    review.extend(f"- [{post_id}](posts/{post_id}.md): {count} line(s)" for post_id, count in low_ocr)
    review.extend(["", f"## Images with no detected text ({len(no_image_text)} images)", ""])
    review.extend(f"- [{post_id}](posts/{post_id}.md): `{path}`" for post_id, path in no_image_text)
    review.extend(["", f"## Tentative theme assignments ({len(uncertain_theme)} posts)", ""])
    review.extend(f"- [{post_id}](posts/{post_id}.md)" for post_id in uncertain_theme)
    review.extend(["", f"## Other handles visible near the top of media ({len(other_attribution)} posts)", ""])
    review.extend(f"- [{post_id}](posts/{post_id}.md): " + ", ".join("@" + handle for handle in handles) for post_id, handles in other_attribution)
    write_text(OUT / "REVIEW.md", "\n".join(review))

    frame_with_text = sum(bool(row.get("lines")) for row in frame_rows)
    quality = [
        "# Coverage and method", "",
        "| Item | Count |", "|---|---:|",
        f"| Original post folders | {len(posts)} |",
        f"| Original still images | {len(images)} |",
        f"| Images OCR processed | {len(image_rows)} |",
        f"| Images with detected text | {sum(bool(row.get('lines')) for row in image_rows)} |",
        f"| Original videos | {len(videos)} |",
        f"| Videos speech processed | {len(speech_rows)} |",
        f"| Video frames OCR processed | {len(frame_rows)} |",
        f"| Video frames with detected text | {frame_with_text} |",
        f"| Repeated-text groups | {len(duplicates)} |",
        f"| Identical-media groups across posts | {len(repeated_media)} |", "",
        "## Method", "",
        "- Still images: RapidOCR 3.9.2, original resolution. One record per image, including the extensionless JPEG.",
        "- Videos: frames sampled at one frame per second and OCR'd with RapidOCR 3.9.2; frame lines below 0.85 confidence were omitted from the readable Markdown; English speech transcribed locally with faster-whisper base.en.",
        "- Dates and captions are left unknown because the repository contains no corresponding metadata files.",
        "- Theme labels are first-pass navigation aids from transparent keyword rules, not final editorial decisions.",
        "- Repeated text is detected by exact normalization and high-similarity comparisons within shared opening phrases. Media duplication uses SHA-256.",
        "- Raw OCR and speech output is preserved in [source-data](source-data/) with boxes, confidence scores, and timestamps.",
        "- All original media folders remain unchanged. OCR and speech text may contain errors; see [review queue](REVIEW.md).", "",
    ]
    write_text(OUT / "QUALITY.md", "\n".join(quality))

    readme = [
        "# Instagram post collection — Phase 1", "",
        "A searchable, theme-based collection of the source posts. This is an archive and transcription, not a book manuscript.", "",
        f"**Coverage:** {len(posts)} posts, {len(images)} still images, {len(videos)} videos.", "",
        "## Browse", "",
        "- [All posts](INDEX.md)", "- [Review queue](REVIEW.md)",
        "- [Repeated material](DUPLICATES.md)", "- [Coverage and method](QUALITY.md)", "",
        "## Themes", "",
    ]
    readme.extend(f"- [{theme}](themes/{slug(theme)}.md) ({len(theme_members[theme])})" for theme in theme_names)
    readme.extend([
        "", "## How to use the files", "",
        "Each post has one Markdown record in `posts/`, preserving the order of carousel images and linking to the untouched original media folder at the repository root. Videos include an automated speech transcript and a link to time-stamped on-screen OCR.", "",
        "The source repository currently has no caption or publication-date files. Those fields remain unknown. Instagram links are inferred from shortcodes. Transcriptions and theme labels need human review before publication.", "",
        "## Rebuild the Markdown", "",
        "The original OCR and speech records are in `source-data/`. From the repository root, run `python tools/build_archive.py` to regenerate the indexes, themes, post files, and manifest. The builder uses only Python's standard library. Edit `tools/theme_rules.py` to adjust the provisional theme taxonomy.", "",
    ])
    write_text(OUT / "README.md", "\n".join(readme))
    write_text(ROOT / "README.md", "# Instagram post archive\n\n[Browse the themed Markdown collection](archive/README.md).\n\nOriginal media folders are preserved at the repository root.\n")

    manifest = {
        "source_repository": "https://github.com/muhibegypt-del/igpullcollection",
        "counts": {
            "posts": len(posts), "images": len(images), "videos": len(videos),
            "image_ocr_records": len(image_rows), "video_ocr_frames": len(frame_rows),
            "speech_records": len(speech_rows),
        },
        "posts": [
            {key: value for key, value in post.items() if key not in {"images", "videos", "text", "comparison_text"}}
            for post in posts.values()
        ],
    }
    write_text(OUT / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps(manifest["counts"], indent=2))
    print(f"Theme pages: {len(theme_names)}; duplicate text groups: {len(duplicates)}; image OCR review posts: {len(low_ocr)}")


if __name__ == "__main__":
    main()
