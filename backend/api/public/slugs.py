"""Slug utilities for public API URLs."""

import re
import unicodedata


def slugify_team(name: str) -> str:
    nfkd = unicodedata.normalize("NFD", name)
    stripped = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    lower = stripped.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lower).strip("-")
    return slug


_REVERSE_CACHE: dict[str, dict[str, str]] | None = None


def _build_reverse_cache() -> dict[str, dict[str, str]]:
    from webapp.data import load_features

    features = load_features()
    if features.empty:
        return {}
    teams = features[["team", "division"]].drop_duplicates()
    cache: dict[str, dict[str, str]] = {}
    for _, row in teams.iterrows():
        slug = slugify_team(row["team"])
        div = row["division"]
        key = f"{slug}:{div}" if div else slug
        cache[key] = {"name": row["team"], "division": div}
        if slug not in cache:
            cache[slug] = {"name": row["team"], "division": div}
    return cache


def deslugify_team(slug: str, division: str | None = None) -> str | None:
    global _REVERSE_CACHE
    if _REVERSE_CACHE is None:
        _REVERSE_CACHE = _build_reverse_cache()
    if division:
        key = f"{slug}:{division}"
        if key in _REVERSE_CACHE:
            return _REVERSE_CACHE[key]["name"]
    entry = _REVERSE_CACHE.get(slug)
    return entry["name"] if entry else None


DIVISION_SLUGS: dict[str, str] = {
    "E0": "premier-league",
    "SP1": "la-liga",
    "I1": "serie-a",
    "D1": "bundesliga",
    "F1": "ligue-1",
    "EC": "champions-league",
}

SLUG_TO_DIVISION: dict[str, str] = {v: k for k, v in DIVISION_SLUGS.items()}

DIVISION_DISPLAY: dict[str, str] = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "I1": "Serie A",
    "D1": "Bundesliga",
    "F1": "Ligue 1",
    "EC": "Champions League",
}

DIVISION_FLAGS: dict[str, str] = {
    "E0": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "SP1": "🇪🇸",
    "I1": "🇮🇹",
    "D1": "🇩🇪",
    "F1": "🇫🇷",
    "EC": "🏆",
}
