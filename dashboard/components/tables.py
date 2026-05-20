import pandas as pd


def standings_table(matches_df: pd.DataFrame, xg_df: pd.DataFrame | None = None) -> pd.DataFrame:
    teams = sorted(set(matches_df["home_team"]) | set(matches_df["away_team"]))
    rows = []
    for team in teams:
        home = matches_df[matches_df["home_team"] == team]
        away = matches_df[matches_df["away_team"] == team]
        hw = len(home[home["ft_result"] == "H"])
        hd = len(home[home["ft_result"] == "D"])
        hl = len(home[home["ft_result"] == "A"])
        aw = len(away[away["ft_result"] == "A"])
        ad = len(away[away["ft_result"] == "D"])
        al_ = len(away[away["ft_result"] == "H"])

        gf = int(home["ft_home_goals"].sum() + away["ft_away_goals"].sum())
        ga = int(home["ft_away_goals"].sum() + away["ft_home_goals"].sum())

        p = len(home) + len(away)
        w = hw + aw
        d = hd + ad
        l_count = hl + al_
        pts = w * 3 + d

        row = {
            "Team": team,
            "P": p,
            "W": w,
            "D": d,
            "L": l_count,
            "GF": gf,
            "GA": ga,
            "GD": gf - ga,
            "Pts": pts,
        }

        if xg_df is not None and not xg_df.empty:
            xg_home = xg_df[xg_df["home_team"] == team]
            xg_away = xg_df[xg_df["away_team"] == team]
            xg_for = float(xg_home["home_xg"].sum() + xg_away["away_xg"].sum())
            xg_against = float(xg_home["away_xg"].sum() + xg_away["home_xg"].sum())
            row["xG"] = round(xg_for, 1)
            row["xGA"] = round(xg_against, 1)
            row["xGD"] = round(xg_for - xg_against, 1)

        rows.append(row)

    result = pd.DataFrame(rows)
    result.sort_values("Pts", ascending=False, inplace=True)
    result.insert(0, "Pos", range(1, len(result) + 1))
    return result


def form_indicator(matches_df: pd.DataFrame, team: str, n: int = 5) -> str:
    all_matches = pd.concat(
        [
            matches_df[matches_df["home_team"] == team].assign(
                result=matches_df["ft_result"].map({"H": "W", "D": "D", "A": "L"})
            ),
            matches_df[matches_df["away_team"] == team].assign(
                result=matches_df["ft_result"].map({"A": "W", "D": "D", "H": "L"})
            ),
        ]
    )
    all_matches = all_matches.sort_values("match_date", ascending=False)
    last_n = all_matches.head(n)["result"].tolist()
    return " ".join(last_n)


def last_n_results(matches_df: pd.DataFrame, team: str, n: int = 10) -> pd.DataFrame:
    home = matches_df[matches_df["home_team"] == team].copy()
    home["opponent"] = home["away_team"]
    home["score"] = home["ft_home_goals"].astype(str) + "-" + home["ft_away_goals"].astype(str)
    home["venue"] = "H"

    away = matches_df[matches_df["away_team"] == team].copy()
    away["opponent"] = away["home_team"]
    away["score"] = away["ft_away_goals"].astype(str) + "-" + away["ft_home_goals"].astype(str)
    away["venue"] = "A"

    combined = pd.concat([home, away]).sort_values("match_date", ascending=False)
    return combined[["match_date", "opponent", "score", "venue", "ft_result"]].head(n)
