from tournament.simulation import simulate_group_stage
from tournament.standings import calculate_group_standings


FORCED_SCENARIOS = {
    "home_win": (2, 1),
    "draw": (1, 1),
    "away_win": (1, 2),
}


def analyze_match_scenarios(
    completed_matches: list[dict],
    selected_match: dict,
    remaining_matches: list[dict],
    match_probabilities: list[dict],
    n_simulations: int = 10000,
    seed: int = 42,
) -> dict:
    scenarios = {}
    teams = sorted(
        {
            team
            for match in completed_matches + remaining_matches + [selected_match]
            for team in (match["home"], match["away"])
        }
    )

    for index, (scenario_name, score) in enumerate(FORCED_SCENARIOS.items()):
        home_score, away_score = score
        forced_match = {
            "home": selected_match["home"],
            "away": selected_match["away"],
            "home_score": home_score,
            "away_score": away_score,
        }
        completed_after_result = completed_matches + [forced_match]
        rest_remaining = [
            match
            for match in remaining_matches
            if not _same_fixture(match, selected_match)
        ]
        rest_with_probabilities = _add_probabilities(rest_remaining, match_probabilities)

        scenarios[scenario_name] = {
            "forced_result": (
                f"{selected_match['home']} {home_score}-{away_score} "
                f"{selected_match['away']}"
            ),
            "table_after_result": calculate_group_standings(completed_after_result, teams=teams),
            "qualification_probabilities": simulate_group_stage(
                completed_after_result,
                rest_with_probabilities,
                n_simulations=n_simulations,
                seed=seed + index,
            ),
        }

    return {
        "current_table": calculate_group_standings(completed_matches, teams=teams),
        "scenarios": scenarios,
    }


def calculate_qualification_swing(scenario_result: dict, home_team: str, away_team: str) -> dict:
    scenarios = scenario_result["scenarios"]
    swing = {}

    for team in (home_team, away_team):
        top_2_if_win = scenarios["home_win"]["qualification_probabilities"][team]["top_2"]
        top_2_if_draw = scenarios["draw"]["qualification_probabilities"][team]["top_2"]
        top_2_if_loss = scenarios["away_win"]["qualification_probabilities"][team]["top_2"]

        if team == away_team:
            top_2_if_win = scenarios["away_win"]["qualification_probabilities"][team]["top_2"]
            top_2_if_loss = scenarios["home_win"]["qualification_probabilities"][team]["top_2"]

        swing[team] = {
            "top_2_if_win": top_2_if_win,
            "top_2_if_draw": top_2_if_draw,
            "top_2_if_loss": top_2_if_loss,
            "win_vs_draw_swing": top_2_if_win - top_2_if_draw,
            "draw_vs_loss_swing": top_2_if_draw - top_2_if_loss,
        }

    return swing


def _add_probabilities(matches: list[dict], match_probabilities: list[dict]) -> list[dict]:
    return [
        {
            **match,
            **_find_probabilities(match, match_probabilities),
        }
        for match in matches
    ]


def _find_probabilities(match: dict, match_probabilities: list[dict]) -> dict:
    for probabilities in match_probabilities:
        if probabilities["home"] == match["home"] and probabilities["away"] == match["away"]:
            return {
                "p_home": probabilities["p_home"],
                "p_draw": probabilities["p_draw"],
                "p_away": probabilities["p_away"],
            }

    for probabilities in match_probabilities:
        if _same_fixture(match, probabilities):
            return {
                "p_home": probabilities["p_away"],
                "p_draw": probabilities["p_draw"],
                "p_away": probabilities["p_home"],
            }

    raise ValueError(f"missing probabilities for {match['home']} vs {match['away']}")


def _same_fixture(first: dict, second: dict) -> bool:
    return {first["home"], first["away"]} == {second["home"], second["away"]}
