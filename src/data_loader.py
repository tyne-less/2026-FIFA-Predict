import pandas as pd


def load_groups(path: str = "data/groups.csv") -> pd.DataFrame:
    return pd.read_csv(path)


def load_matches(path: str = "data/matches.csv") -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"match_id": str})
    _validate_matches(df)
    return df


def load_match_probabilities(path: str = "data/match_probabilities.csv") -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"match_id": str})
    _validate_probabilities(df)
    return df


def load_odds(path: str = "data/odds.csv") -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"match_id": str})
    _validate_odds(df)
    return df


def get_groups(groups_df: pd.DataFrame) -> list[str]:
    return sorted(groups_df["group"].dropna().unique().tolist())


def get_group_teams(groups_df: pd.DataFrame, group: str) -> list[str]:
    teams = groups_df.loc[groups_df["group"] == group, "team"].tolist()
    if not teams:
        raise ValueError(f"group {group} is not defined in groups.csv")
    return teams


def get_group_matches(matches_df: pd.DataFrame, group: str) -> pd.DataFrame:
    return matches_df.loc[matches_df["group"] == group].copy()


def get_completed_matches(matches_df: pd.DataFrame, group: str) -> list[dict]:
    group_matches = get_group_matches(matches_df, group)
    completed = group_matches.loc[group_matches["status"] == "completed"]
    return [
        {
            "home": row.home,
            "away": row.away,
            "home_score": int(row.home_score),
            "away_score": int(row.away_score),
        }
        for row in completed.itertuples(index=False)
    ]


def get_remaining_matches(matches_df: pd.DataFrame, group: str) -> list[dict]:
    group_matches = get_group_matches(matches_df, group)
    scheduled = group_matches.loc[group_matches["status"] == "scheduled"]
    return [
        {
            "home": row.home,
            "away": row.away,
        }
        for row in scheduled.itertuples(index=False)
    ]


def get_match_probabilities_for_group(
    matches_df: pd.DataFrame,
    probabilities_df: pd.DataFrame,
    group: str,
) -> list[dict]:
    _validate_probabilities(probabilities_df)
    scheduled = get_group_matches(matches_df, group)
    scheduled = scheduled.loc[scheduled["status"] == "scheduled"]
    merged = scheduled.merge(probabilities_df, on="match_id", how="left")

    missing = merged.loc[merged[["p_home", "p_draw", "p_away"]].isna().any(axis=1), "match_id"].tolist()
    if missing:
        raise ValueError(f"missing probability row for scheduled match(es): {', '.join(missing)}")

    return [
        {
            "home": row.home,
            "away": row.away,
            "p_home": float(row.p_home),
            "p_draw": float(row.p_draw),
            "p_away": float(row.p_away),
        }
        for row in merged.itertuples(index=False)
    ]


def get_odds_for_match(odds_df: pd.DataFrame, match_id: str) -> dict | None:
    _validate_odds(odds_df)
    rows = odds_df.loc[odds_df["match_id"] == match_id]
    if rows.empty:
        return None

    row = rows.iloc[0]
    return {
        "home": float(row["home_odds"]),
        "draw": float(row["draw_odds"]),
        "away": float(row["away_odds"]),
    }


def get_handicap_odds_for_match(odds_df: pd.DataFrame, match_id: str) -> dict | None:
    _validate_odds(odds_df)
    rows = odds_df.loc[odds_df["match_id"] == match_id]
    if rows.empty:
        return None

    row = rows.iloc[0]
    required = ["handicap", "handicap_home_odds", "handicap_draw_odds", "handicap_away_odds"]
    if not all(column in odds_df.columns for column in required):
        return None
    if row[required].isna().any():
        return None

    return {
        "handicap": int(row["handicap"]),
        "handicap_home_odds": float(row["handicap_home_odds"]),
        "handicap_draw_odds": float(row["handicap_draw_odds"]),
        "handicap_away_odds": float(row["handicap_away_odds"]),
    }


def get_model_probabilities_for_match(
    probabilities_df: pd.DataFrame,
    match_id: str,
    market_type: str,
) -> dict | None:
    _validate_probabilities(probabilities_df)
    rows = probabilities_df.loc[probabilities_df["match_id"] == match_id]
    if rows.empty:
        return None

    row = rows.iloc[0]
    if market_type == "normal":
        return {
            "home": float(row["p_home"]),
            "draw": float(row["p_draw"]),
            "away": float(row["p_away"]),
        }

    if market_type == "handicap":
        required = ["p_handicap_home", "p_handicap_draw", "p_handicap_away"]
        if not all(column in probabilities_df.columns for column in required):
            return None
        if row[required].isna().any():
            return None
        return {
            "home": float(row["p_handicap_home"]),
            "draw": float(row["p_handicap_draw"]),
            "away": float(row["p_handicap_away"]),
        }

    raise ValueError(f"unknown market_type: {market_type}")


def validate_tournament_data(
    groups_df: pd.DataFrame,
    matches_df: pd.DataFrame,
    probabilities_df: pd.DataFrame,
    odds_df: pd.DataFrame,
) -> None:
    _validate_matches(matches_df)
    _validate_match_teams(groups_df, matches_df)
    _validate_scheduled_match_probabilities(matches_df, probabilities_df)
    _validate_probabilities(probabilities_df)
    _validate_odds(odds_df)


def _validate_match_teams(groups_df: pd.DataFrame, matches_df: pd.DataFrame) -> None:
    teams_by_group = {
        group: set(group_rows["team"])
        for group, group_rows in groups_df.groupby("group")
    }
    for row in matches_df.itertuples(index=False):
        teams = teams_by_group.get(row.group)
        if teams is None:
            raise ValueError(f"match {row.match_id} references unknown group {row.group}")
        missing = [team for team in (row.home, row.away) if team not in teams]
        if missing:
            raise ValueError(f"match {row.match_id} references unknown team(s): {', '.join(missing)}")


def _validate_matches(matches_df: pd.DataFrame) -> None:
    valid_statuses = {"completed", "scheduled"}
    invalid_statuses = sorted(set(matches_df["status"]) - valid_statuses)
    if invalid_statuses:
        raise ValueError(f"invalid match status value(s): {', '.join(invalid_statuses)}")

    completed = matches_df.loc[matches_df["status"] == "completed"]
    missing_scores = completed.loc[completed[["home_score", "away_score"]].isna().any(axis=1), "match_id"].tolist()
    if missing_scores:
        raise ValueError(f"completed match(es) missing scores: {', '.join(missing_scores)}")


def _validate_scheduled_match_probabilities(matches_df: pd.DataFrame, probabilities_df: pd.DataFrame) -> None:
    scheduled_ids = set(matches_df.loc[matches_df["status"] == "scheduled", "match_id"])
    probability_ids = set(probabilities_df["match_id"])
    missing = sorted(scheduled_ids - probability_ids)
    if missing:
        raise ValueError(f"missing probability row for scheduled match(es): {', '.join(missing)}")


def _validate_probabilities(probabilities_df: pd.DataFrame) -> None:
    for row in probabilities_df.itertuples(index=False):
        total = float(row.p_home) + float(row.p_draw) + float(row.p_away)
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"probabilities for match {row.match_id} must sum to 1.0")
        if min(float(row.p_home), float(row.p_draw), float(row.p_away)) < 0:
            raise ValueError(f"probabilities for match {row.match_id} must be non-negative")

    handicap_columns = ["p_handicap_home", "p_handicap_draw", "p_handicap_away"]
    if not all(column in probabilities_df.columns for column in handicap_columns):
        return

    for _, row in probabilities_df.iterrows():
        values = row[handicap_columns]
        present_count = values.notna().sum()
        if present_count == 0:
            continue
        if present_count != 3:
            raise ValueError(f"handicap probabilities for match {row['match_id']} must all be present or all be empty")
        total = float(values["p_handicap_home"]) + float(values["p_handicap_draw"]) + float(values["p_handicap_away"])
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"handicap probabilities for match {row['match_id']} must sum to 1.0")
        if min(float(values["p_handicap_home"]), float(values["p_handicap_draw"]), float(values["p_handicap_away"])) < 0:
            raise ValueError(f"handicap probabilities for match {row['match_id']} must be non-negative")


def _validate_odds(odds_df: pd.DataFrame) -> None:
    for row in odds_df.itertuples(index=False):
        if min(float(row.home_odds), float(row.draw_odds), float(row.away_odds)) <= 1.0:
            raise ValueError(f"decimal odds for match {row.match_id} must be greater than 1.0")

    handicap_columns = ["handicap", "handicap_home_odds", "handicap_draw_odds", "handicap_away_odds"]
    if not all(column in odds_df.columns for column in handicap_columns):
        return

    for _, row in odds_df.iterrows():
        values = row[handicap_columns]
        present_count = values.notna().sum()
        if present_count == 0:
            continue
        if present_count != 4:
            raise ValueError(f"handicap odds for match {row['match_id']} must all be present or all be empty")
        if min(float(values["handicap_home_odds"]), float(values["handicap_draw_odds"]), float(values["handicap_away_odds"])) <= 1.0:
            raise ValueError(f"handicap decimal odds for match {row['match_id']} must be greater than 1.0")
