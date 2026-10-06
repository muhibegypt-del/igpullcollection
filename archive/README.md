# Instagram post collection — Phase 1

A searchable, theme-based collection of the source posts. This is an archive and transcription, not a book manuscript.

**Coverage:** 504 posts, 937 still images, 20 videos.

## Browse

- [All posts](INDEX.md)
- [Review queue](REVIEW.md)
- [Repeated material](DUPLICATES.md)
- [Coverage and method](QUALITY.md)

## Themes

- [Faith & Trust](themes/faith-trust.md) (141)
- [Worship & Ramadan](themes/worship-ramadan.md) (58)
- [Prophet & Sacred Learning](themes/prophet-sacred-learning.md) (27)
- [Inner Life & Healing](themes/inner-life-healing.md) (68)
- [Love & Relationships](themes/love-relationships.md) (96)
- [Justice & Society](themes/justice-society.md) (25)
- [Writing & Learning](themes/writing-learning.md) (38)
- [Work & Simplicity](themes/work-simplicity.md) (44)
- [Journeys & Encounters](themes/journeys-encounters.md) (27)
- [Culture & Media](themes/culture-media.md) (17)
- [Life & Reflection](themes/life-reflection.md) (113)
- [Visual / Needs Context](themes/visual-needs-context.md) (7)

## How to use the files

Each post has one Markdown record in `posts/`, preserving the order of carousel images and linking to the untouched original media folder at the repository root. Videos include an automated speech transcript and a link to time-stamped on-screen OCR.

The source repository currently has no caption or publication-date files. Those fields remain unknown. Instagram links are inferred from shortcodes. Transcriptions and theme labels need human review before publication.

## Rebuild the Markdown

The original OCR and speech records are in `source-data/`. From the repository root, run `python tools/build_archive.py` to regenerate the indexes, themes, post files, and manifest. The builder uses only Python's standard library. Edit `tools/theme_rules.py` to adjust the provisional theme taxonomy.
