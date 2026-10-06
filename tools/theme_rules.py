"""Transparent first-pass theme labels for the Instagram archive.

These are navigation labels, not editorial claims about the meaning of a post.
Posts may receive several labels; uncertain assignments are flagged for review.
"""

from __future__ import annotations

import re
from collections import OrderedDict

RULES: OrderedDict[str, dict[str, int]] = OrderedDict(
    [
        ("Faith & Trust", {
            "god": 4, "allah": 5, "faith": 2, "trust": 2, "tawakkul": 5,
            "mercy": 2, "divine": 2, "blessing": 1, "soul": 1,
            "spiritual": 2, "sincerity": 2, "ihsan": 4, "belief": 2,
        }),
        ("Worship & Ramadan", {
            "ramadan": 6, "fasting": 4, "fast": 2, "prayer": 4,
            "pray": 3, "salah": 5, "quran": 5, "qur'an": 5,
            "du'a": 4, "dua": 3, "mosque": 4, "dhikr": 5,
            "worship": 4, "hajj": 5, "eid": 4,
        }),
        ("Prophet & Sacred Learning", {
            "prophet": 5, "muhammad": 4, "shaykh": 5, "sheikh": 5,
            "scholar": 4, "sunnah": 5, "hadith": 5,
            "sacred knowledge": 5, "islamic knowledge": 5,
            "islam": 2, "religion": 2, "muslim": 2,
        }),
        ("Inner Life & Healing", {
            "mental health": 6, "depression": 5, "anxiety": 5,
            "trauma": 5, "healing": 4, "grief": 4,
            "self-care": 6, "self care": 6, "emotion": 3,
            "pain": 2, "fear": 2, "rest": 3, "loneliness": 3,
            "heartbreak": 3, "vulnerability": 3, "forgive": 2,
        }),
        ("Love & Relationships", {
            "love": 2, "marriage": 5, "friendship": 5, "friend": 3,
            "family": 4, "mother": 4, "father": 4,
            "community": 3, "belonging": 4, "lonely": 3,
            "relationship": 4, "compassion": 3, "kindness": 2,
            "children": 2, "parent": 4,
        }),
        ("Justice & Society", {
            "palestine": 7, "gaza": 7, "sudan": 7,
            "genocide": 7, "oppression": 5, "injustice": 5,
            "justice": 4, "colonial": 5, "racism": 5,
            "refugee": 5, "war": 2, "human rights": 5,
            "politics": 4, "poverty": 2, "inequality": 4,
            "society": 2, "climate": 4,
        }),
        ("Writing & Learning", {
            "writing": 5, "writer": 4, "write": 3,
            "journal": 5, "poetry": 5, "poem": 5,
            "substack": 4, "workshop": 4, "storytelling": 4,
            "education": 4, "learning": 3, "teaching": 3,
            "course": 3, "reading": 2, "book": 2,
        }),
        ("Work & Simplicity", {
            "hustle": 5, "productivity": 5, "work": 2,
            "capitalism": 5, "minimalism": 6, "simplicity": 4,
            "money": 4, "wealth": 3, "success": 3,
            "career": 4, "contentment": 3, "business": 3,
            "consumerism": 5, "earning": 3,
        }),
        ("Journeys & Encounters", {
            "mauritania": 7, "travel": 5, "journey": 3,
            "visited": 4, "visit": 3, "encounter": 4,
            "met": 2, "pilgrimage": 5, "destination": 3,
            "morocco": 5, "egypt": 5,
        }),
        ("Culture & Media", {
            "netflix": 6, "film": 4, "movie": 4,
            "television": 4, "social media": 4,
            "internet": 3, "technology": 4, "artificial intelligence": 5,
            "ai": 3, "media": 3, "music": 3,
        }),
    ]
)

FALLBACK = "Life & Reflection"
VISUAL = "Visual / Needs Context"


def classify(text: str) -> tuple[str, list[str], dict[str, int], bool]:
    clean = re.sub(r"@\w+|https?://\S+", " ", text.lower())
    if not re.search(r"\w{3,}", clean):
        return VISUAL, [VISUAL], {}, True

    scores: dict[str, int] = {}
    for name, patterns in RULES.items():
        score = 0
        for phrase, weight in patterns.items():
            if re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", clean):
                score += weight
        if score:
            scores[name] = score

    if not scores or max(scores.values()) < 2:
        return FALLBACK, [FALLBACK], scores, True

    ranked = sorted(scores, key=lambda name: (-scores[name], list(RULES).index(name)))
    best = scores[ranked[0]]
    labels = [name for name in ranked if scores[name] >= max(3, best * 0.55)][:3]
    if not labels:
        labels = [ranked[0]]
    uncertain = best < 4 or (len(ranked) > 1 and best - scores[ranked[1]] <= 1)
    return labels[0], labels, scores, uncertain


def slug(name: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")
