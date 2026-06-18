import numpy as np

from tournament.standings import calculate_group_standings


HOME_WIN_SCORES = [(1, 0), (2, 0), (2, 1), (3, 1)]
DRAW_SCORES = [(0, 0), (1, 1), (2, 2)]
AWAY_WIN_SCORES = [(0, 1), (0, 2), (1, 2), (1, 3)]


def simulate_group_stage(
    completed_matches: list[dict],
    remaining_matches: list[dict],
    n_simulations: int = 10_000,
    seed: int | None = None,
) -> dict:
    rng = np.random.default_rng(seed)
    finishes = {}

    teams = sorted({team for match in completed_matches + remaining_matches for team in (match["home"], match["away"])})
    for team in teams:
        finishes[team] = {1: 0, 2: 0, 3: 0, 4: 0}

    for _ in range(n_simulations):
        simulated_matches = list(completed_matches)

        for match in remaining_matches:
            outcome = rng.choice(
                ["home", "draw", "away"],
                p=[match["p_home"], match["p_draw"], match["p_away"]],
            )
            if outcome == "home":
                home_score, away_score = HOME_WIN_SCORES[rng.integers(len(HOME_WIN_SCORES))]
            elif outcome == "draw":
                home_score, away_score = DRAW_SCORES[rng.integers(len(DRAW_SCORES))]
            else:
                home_score, away_score = AWAY_WIN_SCORES[rng.integers(len(AWAY_WIN_SCORES))]

            simulated_matches.append(
                {
                    "home": match["home"],
                    "away": match["away"],
                    "home_score": home_score,
                    "away_score": away_score,
                }
            )

        standings = calculate_group_standings(simulated_matches)
        for index, row in enumerate(standings, start=1):
            finishes[row["team"]][index] += 1

    return {
        team: {
            "finish_1st": float(counts[1] / n_simulations),
            "top_2": float((counts[1] + counts[2]) / n_simulations),
            "finish_3rd": float(counts[3] / n_simulations),
            "finish_4th": float(counts[4] / n_simulations),
        }
        for team, counts in finishes.items()
    }
