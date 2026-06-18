from data_loader import (
    get_handicap_odds_for_match,
    get_odds_for_match,
    load_matches,
    load_odds,
)


class CsvProvider:
    def __init__(self, matches_path: str = "data/matches.csv", odds_path: str = "data/odds.csv"):
        self.matches_path = matches_path
        self.odds_path = odds_path

    def fetch_matches(self, date: str | None = None) -> list[dict]:
        matches_df = load_matches(self.matches_path)
        return [
            {
                "match_id": row.match_id,
                "match_code": row.match_id,
                "league": "世界杯",
                "kickoff_time": None,
                "home": row.home,
                "away": row.away,
                "status": "open" if row.status == "scheduled" else "closed",
                "sale_status": "selling" if row.status == "scheduled" else "closed",
                "supports_single": True,
            }
            for row in matches_df.itertuples(index=False)
        ]

    def fetch_odds(self, match_id: str) -> dict | None:
        matches_df = load_matches(self.matches_path)
        odds_df = load_odds(self.odds_path)
        rows = matches_df.loc[matches_df["match_id"] == match_id]
        if rows.empty:
            return None

        row = rows.iloc[0]
        normal_odds = get_odds_for_match(odds_df, match_id)
        handicap_odds = get_handicap_odds_for_match(odds_df, match_id)
        if normal_odds is None:
            return None

        return {
            "match_id": match_id,
            "match_code": match_id,
            "home": row["home"],
            "away": row["away"],
            "last_update": None,
            "normal": {
                "available": True,
                "home_odds": normal_odds["home"],
                "draw_odds": normal_odds["draw"],
                "away_odds": normal_odds["away"],
            },
            "handicap": _format_handicap_odds(handicap_odds),
        }

    def fetch_all_odds(self, date: str | None = None) -> list[dict]:
        return [
            odds
            for match in self.fetch_matches(date)
            if (odds := self.fetch_odds(match["match_id"])) is not None
        ]


def _format_handicap_odds(handicap_odds: dict | None) -> dict:
    if handicap_odds is None:
        return {"available": False}
    return {
        "available": True,
        "handicap": handicap_odds["handicap"],
        "handicap_home_odds": handicap_odds["handicap_home_odds"],
        "handicap_draw_odds": handicap_odds["handicap_draw_odds"],
        "handicap_away_odds": handicap_odds["handicap_away_odds"],
    }

