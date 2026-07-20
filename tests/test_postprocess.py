"""Tests for league post-processing (Poisson ensemble + draw intelligence)."""



from backend.ml.postprocess import (
    _classify_confidence,
    _pick_result,
    apply_league_draw_zone,
    apply_league_ensemble,
    get_league_poisson_probs,
)


class TestGetLeaguePoissonProbs:
    def test_returns_valid_distribution(self):
        result = get_league_poisson_probs(
            home_goals_avg3=1.5,
            home_conceded_avg3=0.8,
            away_goals_avg3=1.2,
            away_conceded_avg3=1.0,
            home_elo=1800,
            away_elo=1700,
            division="E0",
        )
        assert result is not None
        total = result["prob_home"] + result["prob_draw"] + result["prob_away"]
        assert abs(total - 1.0) < 0.01
        assert 0 <= result["prob_home"] <= 1
        assert 0 <= result["prob_draw"] <= 1
        assert 0 <= result["prob_away"] <= 1

    def test_returns_lambda_values(self):
        result = get_league_poisson_probs(
            home_goals_avg3=2.0,
            home_conceded_avg3=0.5,
            away_goals_avg3=1.5,
            away_conceded_avg3=1.0,
            home_elo=1900,
            away_elo=1800,
            division="SP1",
        )
        assert result is not None
        assert 0.3 <= result["lambda_home"] <= 4.5
        assert 0.3 <= result["lambda_away"] <= 4.5

    def test_returns_over25_and_btts(self):
        result = get_league_poisson_probs(
            home_goals_avg3=1.5,
            home_conceded_avg3=1.0,
            away_goals_avg3=1.3,
            away_conceded_avg3=0.8,
            home_elo=1800,
            away_elo=1800,
            division="D1",
        )
        assert result is not None
        assert 0 <= result["prob_over25"] <= 1
        assert 0 <= result["prob_btts"] <= 1

    def test_returns_none_when_missing_data(self):
        result = get_league_poisson_probs(
            home_goals_avg3=None,
            home_conceded_avg3=0.8,
            away_goals_avg3=1.2,
            away_conceded_avg3=1.0,
            home_elo=1800,
            away_elo=1700,
            division="E0",
        )
        assert result is None

    def test_returns_none_when_nan(self):
        result = get_league_poisson_probs(
            home_goals_avg3=float("nan"),
            home_conceded_avg3=0.8,
            away_goals_avg3=1.2,
            away_conceded_avg3=1.0,
            home_elo=1800,
            away_elo=1700,
            division="E0",
        )
        assert result is None

    def test_uses_league_specific_home_advantage(self):
        # Serie A (I1) has 1.18 home advantage, EC has 1.0
        result_i1 = get_league_poisson_probs(1.5, 1.0, 1.5, 1.0, 1800, 1800, "I1")
        result_ec = get_league_poisson_probs(1.5, 1.0, 1.5, 1.0, 1800, 1800, "EC")
        assert result_i1 is not None and result_ec is not None
        assert result_i1["prob_home"] > result_ec["prob_home"]


class TestApplyLeagueEnsemble:
    def _make_preds(self, h=0.50, d=0.30, a=0.20, ou=0.55, btts=0.45):
        return {
            "prob_home": h,
            "prob_draw": d,
            "prob_away": a,
            "prob_over25": ou,
            "prob_btts": btts,
            "predicted_result": "H",
            "confidence": "media",
            "model_variant": "premium",
        }

    def _make_poisson(self, h=0.40, d=0.35, a=0.25, ou=0.50, btts=0.40):
        return {
            "prob_home": h,
            "prob_draw": d,
            "prob_away": a,
            "prob_over25": ou,
            "prob_btts": btts,
        }

    def test_blends_70_30(self):
        preds = self._make_preds(h=0.50, d=0.30, a=0.20)
        poisson = self._make_poisson(h=0.40, d=0.35, a=0.25)
        result = apply_league_ensemble(preds, poisson)

        expected_h = 0.70 * 0.50 + 0.30 * 0.40
        expected_d = 0.70 * 0.30 + 0.30 * 0.35
        expected_a = 0.70 * 0.20 + 0.30 * 0.25

        assert abs(result["prob_home"] - expected_h) < 0.001
        assert abs(result["prob_draw"] - expected_d) < 0.001
        assert abs(result["prob_away"] - expected_a) < 0.001

    def test_blends_over25_and_btts(self):
        preds = self._make_preds(ou=0.60, btts=0.50)
        poisson = self._make_poisson(ou=0.40, btts=0.30)
        result = apply_league_ensemble(preds, poisson)

        expected_ou = 0.70 * 0.60 + 0.30 * 0.40
        expected_btts = 0.70 * 0.50 + 0.30 * 0.30

        assert abs(result["prob_over25"] - expected_ou) < 0.001
        assert abs(result["prob_btts"] - expected_btts) < 0.001

    def test_sum_near_one(self):
        preds = self._make_preds(h=0.45, d=0.30, a=0.25)
        poisson = self._make_poisson(h=0.35, d=0.40, a=0.25)
        result = apply_league_ensemble(preds, poisson)
        total = result["prob_home"] + result["prob_draw"] + result["prob_away"]
        assert abs(total - 1.0) < 0.01

    def test_agreement_boosts_confidence(self):
        preds = self._make_preds(h=0.55, d=0.25, a=0.20)
        preds["predicted_result"] = "H"
        poisson = self._make_poisson(h=0.50, d=0.30, a=0.20)
        result = apply_league_ensemble(preds, poisson)
        assert result["confidence"] in ("alta", "media")

    def test_disagreement_lowers_confidence(self):
        preds = self._make_preds(h=0.40, d=0.32, a=0.28)
        preds["predicted_result"] = "H"
        poisson = self._make_poisson(h=0.25, d=0.30, a=0.45)
        result = apply_league_ensemble(preds, poisson)
        assert result["confidence"] in ("baja", "media")

    def test_returns_unchanged_when_poisson_none(self):
        preds = self._make_preds()
        original_h = preds["prob_home"]
        result = apply_league_ensemble(preds, None)
        assert result["prob_home"] == original_h


class TestPickResult:
    def test_prefers_draw_when_tight_and_draw_is_second(self):
        assert _pick_result([0.38, 0.34, 0.28]) == "D"

    def test_prefers_draw_when_tight_and_draw_is_top(self):
        assert _pick_result([0.33, 0.37, 0.30]) == "D"

    def test_picks_clear_winner(self):
        assert _pick_result([0.55, 0.25, 0.20]) == "H"

    def test_picks_away_when_clear(self):
        assert _pick_result([0.20, 0.25, 0.55]) == "A"

    def test_no_draw_preference_when_margin_large(self):
        assert _pick_result([0.50, 0.30, 0.20]) == "H"

    def test_tight_margin_between_home_and_away_no_draw_preference(self):
        # H=0.38, D=0.20, A=0.42 — tight between H and A, not involving D
        assert _pick_result([0.38, 0.20, 0.42]) == "A"


class TestApplyLeagueDrawZone:
    def _make_preds(self, h=0.34, d=0.33, a=0.33):
        return {
            "prob_home": h,
            "prob_draw": d,
            "prob_away": a,
            "predicted_result": "H",
            "confidence": "media",
        }

    def test_triggers_when_conditions_met(self):
        preds = self._make_preds(h=0.34, d=0.33, a=0.33)
        result = apply_league_draw_zone(preds, elo_diff=50, home_elo=1800, away_elo=1750)
        assert result["predicted_result"] == "D"

    def test_does_not_trigger_low_draw_prob(self):
        preds = self._make_preds(h=0.50, d=0.25, a=0.25)
        result = apply_league_draw_zone(preds, elo_diff=50, home_elo=1800, away_elo=1750)
        assert result["predicted_result"] == "H"

    def test_does_not_trigger_high_elo_diff(self):
        preds = self._make_preds(h=0.34, d=0.33, a=0.33)
        result = apply_league_draw_zone(preds, elo_diff=120, home_elo=1900, away_elo=1780)
        assert result["predicted_result"] == "H"

    def test_does_not_trigger_high_spread(self):
        preds = self._make_preds(h=0.50, d=0.30, a=0.20)
        result = apply_league_draw_zone(preds, elo_diff=30, home_elo=1800, away_elo=1770)
        assert result["predicted_result"] == "H"

    def test_skips_when_both_elo_default(self):
        preds = self._make_preds(h=0.34, d=0.33, a=0.33)
        result = apply_league_draw_zone(preds, elo_diff=0, home_elo=1500.0, away_elo=1500.0)
        assert result["predicted_result"] == "H"


class TestClassifyConfidence:
    def test_alta(self):
        assert _classify_confidence(0.65) == "alta"

    def test_media(self):
        assert _classify_confidence(0.50) == "media"

    def test_baja(self):
        assert _classify_confidence(0.40) == "baja"
