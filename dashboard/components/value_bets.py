import pandas as pd


def _stake_badge(stake: int) -> str:
    if stake == 3:
        return "🟢🟢🟢 3u"
    if stake == 2:
        return "🟢🟢 2u"
    if stake == 1:
        return "⚪ 1u"
    return "⛔ Sin valor"


def _market_label(market: str) -> str:
    labels = {
        "1x2_home": "Local",
        "1x2_draw": "Empate",
        "1x2_away": "Visitante",
        "over25": "Over 2.5",
        "under25": "Under 2.5",
    }
    return labels.get(market, market)


def _result_badge(result: str) -> str:
    if result == "win":
        return "✅ Ganado"
    if result == "loss":
        return "❌ Perdido"
    return "⏳ Pendiente"


def format_picks(picks: list[dict]) -> pd.DataFrame:
    if not picks:
        return pd.DataFrame()

    df = pd.DataFrame(picks)
    display = pd.DataFrame(
        {
            "Fecha": df["match_date"],
            "Partido": df["home_team"] + " vs " + df["away_team"],
            "Liga": df["division"],
            "Apuesta": df["market"].apply(_market_label),
            "Cuota": df["odd"].apply(lambda x: f"{x:.2f}"),
            "Ventaja": df["edge"].apply(lambda x: f"{x:.1%}"),
            "Unidades": df["stake"].apply(_stake_badge),
            "Valor Esperado": df["expected_value"].apply(lambda x: f"{x:.1%}"),
        }
    )
    return display


def format_resolved(picks: list[dict]) -> pd.DataFrame:
    if not picks:
        return pd.DataFrame()

    df = pd.DataFrame(picks)
    display = pd.DataFrame(
        {
            "Fecha": df["match_date"],
            "Partido": df["home_team"] + " vs " + df["away_team"],
            "Apuesta": df["market"].apply(_market_label),
            "Cuota": df["odd"].apply(lambda x: f"{x:.2f}"),
            "Unidades": df["stake"].apply(_stake_badge),
            "Resultado": df["result"].apply(_result_badge),
            "Ganancia": df["profit"].apply(lambda x: f"{x:+.2f}u"),
        }
    )
    return display
