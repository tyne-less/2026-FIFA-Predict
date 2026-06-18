def calculate_group_standings(matches: list[dict], teams: list[str] | None = None) -> list[dict]:
    table = {}

    for team in teams or []:
        table[team] = _empty_row(team)

    for match in matches:
        home = match["home"]
        away = match["away"]
        home_score = int(match["home_score"])
        away_score = int(match["away_score"])

        for team in (home, away):
            table.setdefault(team, _empty_row(team))

        table[home]["played"] += 1
        table[away]["played"] += 1
        table[home]["goals_for"] += home_score
        table[home]["goals_against"] += away_score
        table[away]["goals_for"] += away_score
        table[away]["goals_against"] += home_score

        if home_score > away_score:
            table[home]["wins"] += 1
            table[away]["losses"] += 1
            table[home]["points"] += 3
        elif home_score < away_score:
            table[away]["wins"] += 1
            table[home]["losses"] += 1
            table[away]["points"] += 3
        else:
            table[home]["draws"] += 1
            table[away]["draws"] += 1
            table[home]["points"] += 1
            table[away]["points"] += 1

        table[home]["goal_difference"] = table[home]["goals_for"] - table[home]["goals_against"]
        table[away]["goal_difference"] = table[away]["goals_for"] - table[away]["goals_against"]

    return sorted(
        table.values(),
        key=lambda row: (row["points"], row["goal_difference"], row["goals_for"]),
        reverse=True,
    )


def _empty_row(team: str) -> dict:
    return {
        "team": team,
        "played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
        "goal_difference": 0,
        "points": 0,
    }
