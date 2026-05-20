from backend.services.teams import TeamNormalizer


def test_normalize_known_alias():
    tn = TeamNormalizer()
    assert tn.normalize("Man United") == "Manchester United"
    assert tn.normalize("Man City") == "Manchester City"
    assert tn.normalize("Ath Madrid") == "Atletico Madrid"
    assert tn.normalize("Ath Bilbao") == "Athletic Bilbao"


def test_normalize_already_canonical():
    tn = TeamNormalizer()
    assert tn.normalize("Arsenal") == "Arsenal"
    assert tn.normalize("Barcelona") == "Barcelona"


def test_normalize_duplicate_variants():
    tn = TeamNormalizer()
    assert tn.normalize("MGladbach") == tn.normalize("M'gladbach")
    assert tn.normalize("Nott'm Forest") == tn.normalize("Nottm Forest")


def test_normalize_unknown_passes_through():
    tn = TeamNormalizer()
    assert tn.normalize("Some Unknown FC") == "Some Unknown FC"


def test_get_all_aliases():
    tn = TeamNormalizer()
    aliases = tn.get_aliases("Manchester United")
    assert "Man United" in aliases


def test_all_teams_list():
    tn = TeamNormalizer()
    teams = tn.all_canonical()
    assert "Manchester United" in teams
    assert "Barcelona" in teams
    assert len(teams) > 50
