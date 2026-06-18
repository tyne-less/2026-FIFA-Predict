import pandas as pd


def validate_manual_odds(*odds: float) -> None:
    invalid = [value for value in odds if value <= 1.0]
    if invalid:
        raise ValueError("manual odds must be greater than 1.0")


def build_manual_odds_record(
    match_code: str,
    league: str,
    kickoff_time: str,
    home_team: str,
    away_team: str,
    normal_home_odds: float,
    normal_draw_odds: float,
    normal_away_odds: float,
    handicap: int,
    handicap_home_odds: float,
    handicap_draw_odds: float,
    handicap_away_odds: float,
    match_id: str = None,
) -> dict:
    validate_manual_odds(
        normal_home_odds,
        normal_draw_odds,
        normal_away_odds,
        handicap_home_odds,
        handicap_draw_odds,
        handicap_away_odds,
    )
    return {
        "match_id": match_id or "manual_001",
        "match_code": match_code,
        "league": league,
        "kickoff_time": kickoff_time,
        "home": home_team,
        "away": away_team,
        "last_update": "manual",
        "normal": {
            "available": True,
            "home_odds": normal_home_odds,
            "draw_odds": normal_draw_odds,
            "away_odds": normal_away_odds,
        },
        "handicap": {
            "available": True,
            "handicap": handicap,
            "handicap_home_odds": handicap_home_odds,
            "handicap_draw_odds": handicap_draw_odds,
            "handicap_away_odds": handicap_away_odds,
        },
    }


def find_group_for_teams(groups_df: pd.DataFrame, home_team: str, away_team: str) -> str | None:
    home_groups = set(groups_df.loc[groups_df["team"] == home_team, "group"])
    away_groups = set(groups_df.loc[groups_df["team"] == away_team, "group"])
    shared_groups = sorted(home_groups & away_groups)
    return shared_groups[0] if shared_groups else None


def build_manual_match_from_local(match_row: dict, league: str = "世界杯") -> dict:
    return {
        "match_id": match_row["match_id"],
        "match_code": match_row["match_id"],
        "league": league,
        "home": match_row["home"],
        "away": match_row["away"],
        "group": match_row["group"],
        "status": "scheduled",
    }


def get_scheduled_matches_for_group(matches_df: pd.DataFrame, group: str) -> list[dict]:
    scheduled = matches_df[(matches_df["group"] == group) & (matches_df["status"] == "scheduled")]
    return scheduled.to_dict(orient="records")
