from tournament.simulation import simulate_group_stage


def test_simulate_group_stage_is_reproducible():
    completed = [
        {"home": "Netherlands", "away": "Japan", "home_score": 2, "away_score": 2},
        {"home": "Sweden", "away": "Tunisia", "home_score": 5, "away_score": 1},
    ]
    remaining = [
        {"home": "Netherlands", "away": "Sweden", "p_home": 0.35, "p_draw": 0.30, "p_away": 0.35},
        {"home": "Tunisia", "away": "Japan", "p_home": 0.22, "p_draw": 0.28, "p_away": 0.50},
        {"home": "Tunisia", "away": "Netherlands", "p_home": 0.12, "p_draw": 0.23, "p_away": 0.65},
        {"home": "Japan", "away": "Sweden", "p_home": 0.33, "p_draw": 0.29, "p_away": 0.38},
    ]

    first = simulate_group_stage(completed, remaining, n_simulations=100, seed=7)
    second = simulate_group_stage(completed, remaining, n_simulations=100, seed=7)

    assert first == second
    assert set(first) == {"Japan", "Netherlands", "Sweden", "Tunisia"}
    for result in first.values():
        assert result["finish_1st"] + result["finish_3rd"] + result["finish_4th"] <= 1.0
        assert 0 <= result["top_2"] <= 1
