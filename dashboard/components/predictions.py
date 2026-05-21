import pandas as pd


def _color_prob(val: float) -> str:
    if val > 0.50:
        return "background-color: #27ae60; color: white"
    if val > 0.35:
        return "background-color: #f39c12; color: white"
    return "background-color: #e74c3c; color: white"


def _confidence_badge(conf: str) -> str:
    badges = {"alta": "🟢 Alta", "media": "🟡 Media", "baja": "⚪ Baja"}
    return badges.get(conf, conf)


def format_predictions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    display = df[
        [
            "match_date",
            "home_team",
            "away_team",
            "division",
            "prob_home",
            "prob_draw",
            "prob_away",
            "predicted_result",
            "prob_over25",
            "prob_btts",
            "confidence",
            "model_variant",
        ]
    ].copy()

    result_map = {"H": "Local", "D": "Empate", "A": "Visitante"}
    display["predicted_result"] = display["predicted_result"].map(result_map)
    display["confidence"] = display["confidence"].apply(_confidence_badge)

    for col in ["prob_home", "prob_draw", "prob_away", "prob_over25", "prob_btts"]:
        display[col] = display[col].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "-")

    display.columns = [
        "Fecha",
        "Local",
        "Visitante",
        "Liga",
        "P(H)",
        "P(D)",
        "P(A)",
        "Prediccion",
        "P(O2.5)",
        "P(BTTS)",
        "Confianza",
        "Modelo",
    ]
    return display
