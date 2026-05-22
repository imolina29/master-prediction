import numpy as np
import pandas as pd
import plotly.graph_objects as go

PLOTLY_LAYOUT = {
    "template": "plotly_dark",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(14,17,23,0.8)",
    "font": {"color": "#e0e0e0"},
}


def reliability_diagram(
    predicted_probs: np.ndarray, actual_outcomes: np.ndarray, n_bins: int = 10
) -> go.Figure:
    bins = np.linspace(0, 1, n_bins + 1)
    bin_centers = []
    observed_freqs = []
    counts = []

    for i in range(n_bins):
        mask = (predicted_probs >= bins[i]) & (predicted_probs < bins[i + 1])
        if mask.sum() == 0:
            continue
        bin_centers.append((bins[i] + bins[i + 1]) / 2)
        observed_freqs.append(actual_outcomes[mask].mean())
        counts.append(int(mask.sum()))

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            line={"color": "rgba(255,255,255,0.3)", "dash": "dash"},
            name="Calibracion perfecta",
            showlegend=True,
        )
    )

    fig.add_trace(
        go.Bar(
            x=bin_centers,
            y=[c / max(counts) * 0.3 for c in counts],
            marker_color="rgba(76,175,80,0.15)",
            name="Volumen",
            yaxis="y2",
            width=1 / n_bins * 0.8,
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=bin_centers,
            y=observed_freqs,
            mode="lines+markers",
            line={"color": "#4CAF50", "width": 2},
            marker={"color": "#FFD700", "size": 8},
            name="Modelo",
            text=[f"n={c}" for c in counts],
            hovertemplate="Predicho: %{x:.0%}<br>Real: %{y:.0%}<br>%{text}",
        )
    )

    fig.update_layout(
        title="Diagrama de Confiabilidad",
        xaxis_title="Probabilidad Predicha",
        yaxis_title="Frecuencia Observada",
        xaxis={"range": [0, 1], "tickformat": ".0%"},
        yaxis={"range": [0, 1], "tickformat": ".0%"},
        yaxis2={"overlaying": "y", "showticklabels": False, "range": [0, 1]},
        height=450,
        **PLOTLY_LAYOUT,
    )
    return fig


def calibration_metrics(predicted_probs: np.ndarray, actual_outcomes: np.ndarray) -> dict:
    from sklearn.metrics import brier_score_loss

    brier = brier_score_loss(actual_outcomes, predicted_probs)
    bins = np.linspace(0, 1, 11)
    ece = 0.0
    total = len(predicted_probs)
    for i in range(10):
        mask = (predicted_probs >= bins[i]) & (predicted_probs < bins[i + 1])
        if mask.sum() == 0:
            continue
        bin_acc = actual_outcomes[mask].mean()
        bin_conf = predicted_probs[mask].mean()
        ece += mask.sum() / total * abs(bin_acc - bin_conf)

    return {"brier_score": round(brier, 4), "ece": round(ece, 4)}


def build_calibration_data(backtest_results: dict) -> pd.DataFrame:
    rows = []
    for model_key, data in backtest_results.items():
        folds = data.get("folds", [])
        for fold in folds:
            rows.append(
                {
                    "modelo": model_key,
                    "temporada": fold.get("test_season", ""),
                    "accuracy": fold.get("accuracy", 0),
                    "log_loss": fold.get("log_loss", 0),
                    "brier_score": fold.get("brier_score"),
                    "roi_pct": fold.get("roi_pct"),
                    "n_test": fold.get("n_test", 0),
                }
            )
    return pd.DataFrame(rows)


def model_comparison_chart(backtest_results: dict) -> go.Figure:
    models = []
    accuracies = []
    log_losses = []

    for model_key, data in backtest_results.items():
        models.append(model_key)
        accuracies.append(data.get("mean_accuracy", 0))
        log_losses.append(data.get("mean_log_loss", 0))

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=models,
            y=accuracies,
            name="Accuracy",
            marker_color="#4CAF50",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=models,
            y=log_losses,
            mode="lines+markers",
            name="Log Loss",
            yaxis="y2",
            line={"color": "#FFD700"},
            marker={"color": "#FFD700", "size": 8},
        )
    )
    fig.update_layout(
        title="Comparacion de Modelos",
        yaxis={"title": "Accuracy", "tickformat": ".0%"},
        yaxis2={"title": "Log Loss", "overlaying": "y", "side": "right"},
        barmode="group",
        height=400,
        **PLOTLY_LAYOUT,
    )
    return fig
