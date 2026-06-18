def get_handicap_result(home_score: int, away_score: int, handicap: int) -> str:
    adjusted_home_score = home_score + handicap
    if adjusted_home_score > away_score:
        return "handicap_home"
    if adjusted_home_score == away_score:
        return "handicap_draw"
    return "handicap_away"


def format_handicap_result_label(
    home_team: str,
    away_team: str,
    handicap: int,
    outcome: str,
) -> str:
    labels = {
        "handicap_home": "让胜",
        "handicap_draw": "让平",
        "handicap_away": "让负",
    }
    return labels[outcome]


def format_handicap_line(home_team: str, handicap: int) -> str:
    return f"{home_team} {handicap:+d}" if handicap != 0 else f"{home_team} 0"
