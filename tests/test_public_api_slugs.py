from backend.api.public.slugs import (
    DIVISION_DISPLAY,
    DIVISION_SLUGS,
    SLUG_TO_DIVISION,
    slugify_team,
)


def test_slugify_plain():
    assert slugify_team("Real Madrid") == "real-madrid"


def test_slugify_accents():
    assert slugify_team("Atlético Madrid") == "atletico-madrid"


def test_slugify_special():
    assert slugify_team("RC Deportivo La Coruña") == "rc-deportivo-la-coruna"


def test_slugify_multiple_spaces():
    assert slugify_team("ES Troyes AC") == "es-troyes-ac"


def test_division_slugs_complete():
    assert set(DIVISION_SLUGS.keys()) == {"E0", "SP1", "I1", "D1", "F1", "EC"}


def test_slug_to_division_roundtrip():
    for code, slug in DIVISION_SLUGS.items():
        assert SLUG_TO_DIVISION[slug] == code


def test_division_display_names():
    assert DIVISION_DISPLAY["E0"] == "Premier League"
    assert DIVISION_DISPLAY["SP1"] == "La Liga"
    assert DIVISION_DISPLAY["EC"] == "Champions League"
