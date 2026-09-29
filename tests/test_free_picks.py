from backend.notifications.telegram import _format_prediction_line


def _make_pred(
    home="Arsenal", away="Chelsea", division="E0", result="H", confidence="alta", over25=0.8
):
    return {
        "home_team": home,
        "away_team": away,
        "division": division,
        "predicted_result": result,
        "confidence": confidence,
        "prob_over25": over25,
        "prob_home": 0.6,
        "prob_draw": 0.2,
        "prob_away": 0.2,
        "match_date": "2026-09-28",
    }


def test_format_prediction_home_win():
    line = _format_prediction_line(_make_pred(result="H"))
    assert "Gana Arsenal" in line
    assert "Over 2.5" in line


def test_format_prediction_away_win():
    line = _format_prediction_line(_make_pred(result="A"))
    assert "Gana Chelsea" in line


def test_format_prediction_draw():
    line = _format_prediction_line(_make_pred(result="D"))
    assert "Empate" in line


def test_format_prediction_under_25():
    line = _format_prediction_line(_make_pred(over25=0.3))
    assert "Under 2.5" in line


def test_format_prediction_confidence_icons():
    alta = _format_prediction_line(_make_pred(confidence="alta"))
    media = _format_prediction_line(_make_pred(confidence="media"))
    baja = _format_prediction_line(_make_pred(confidence="baja"))
    assert "🟢" in alta
    assert "🟡" in media
    assert "🔴" in baja
