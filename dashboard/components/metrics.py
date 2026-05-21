import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go


def load_backtest_results(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def backtest_summary_table(results: dict) -> pd.DataFrame:
    rows = []
    for model_name, data in results.items():
        rows.append(
            {
                "Modelo": model_name,
                "Accuracy": f"{data.get('mean_accuracy', 0):.1%}",
                "Log Loss": f"{data.get('mean_log_loss', 0):.4f}",
                "ROI": f"{data.get('mean_roi_pct', 'N/A')}%"
                if "mean_roi_pct" in data
                else "N/A",
                "Folds": len(data.get("folds", [])),
            }
        )
    return pd.DataFrame(rows)


def calibration_chart(results: dict, model_name: str) -> go.Figure | None:
    if model_name not in results:
        return None
    folds = results[model_name].get("folds", [])
    if not folds:
        return None

    accuracies = [f["accuracy"] for f in folds]
    labels = [f["test_season"] for f in folds]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=labels,
            y=accuracies,
            marker_color="#3498db",
            name="Accuracy",
        )
    )

    if all("roi_pct" in f for f in folds):
        rois = [f["roi_pct"] for f in folds]
        fig.add_trace(
            go.Scatter(
                x=labels,
                y=[r / 100 for r in rois],
                mode="lines+markers",
                name="ROI %",
                yaxis="y2",
                line={"color": "#2ecc71"},
            )
        )
        fig.update_layout(
            yaxis2={
                "title": "ROI %",
                "overlaying": "y",
                "side": "right",
                "tickformat": ".0%",
            }
        )

    fig.update_layout(
        title=f"Rendimiento por Temporada — {model_name}",
        xaxis_title="Temporada",
        yaxis_title="Accuracy",
        yaxis_tickformat=".0%",
        template="plotly_dark",
        height=400,
    )
    return fig
