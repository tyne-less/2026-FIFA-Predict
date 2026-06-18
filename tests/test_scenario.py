from tournament.scenario import analyze_match_scenarios, calculate_qualification_swing


def test_analyze_match_scenarios_returns_tables_and_probabilities():
    result = analyze_match_scenarios(
        completed_matches=[
            {"home": "Netherlands", "away": "Japan", "home_score": 2, "away_score": 2},
            {"home": "Sweden", "away": "Tunisia", "home_score": 5, "away_score": 1},
        ],
        selected_match={"home": "Japan", "away": "Tunisia"},
        remaining_matches=[
            {"home": "Netherlands", "away": "Sweden"},
            {"home": "Tunisia", "away": "Japan"},
            {"home": "Tunisia", "away": "Netherlands"},
            {"home": "Japan", "away": "Sweden"},
        ],
        match_probabilities=[
            {"home": "Netherlands", "away": "Sweden", "p_home": 0.35, "p_draw": 0.30, "p_away": 0.35},
            {"home": "Tunisia", "away": "Japan", "p_home": 0.22, "p_draw": 0.28, "p_away": 0.50},
            {"home": "Tunisia", "away": "Netherlands", "p_home": 0.12, "p_draw": 0.23, "p_away": 0.65},
            {"home": "Japan", "away": "Sweden", "p_home": 0.33, "p_draw": 0.29, "p_away": 0.38},
        ],
        n_simulations=100,
        seed=7,
    )

    assert "current_table" in result
    assert set(result["scenarios"]) == {"home_win", "draw", "away_win"}

    for scenario in result["scenarios"].values():
        assert scenario["table_after_result"]
        assert scenario["qualification_probabilities"]
        for probabilities in scenario["qualification_probabilities"].values():
            assert 0 <= probabilities["finish_1st"] <= 1
            assert 0 <= probabilities["top_2"] <= 1
            assert 0 <= probabilities["finish_3rd"] <= 1
            assert 0 <= probabilities["finish_4th"] <= 1


def test_calculate_qualification_swing_returns_selected_team_keys():
    scenario_result = {
        "scenarios": {
            "home_win": {
                "qualification_probabilities": {
                    "Japan": {"top_2": 0.80},
                    "Tunisia": {"top_2": 0.20},
                }
            },
            "draw": {
                "qualification_probabilities": {
                    "Japan": {"top_2": 0.55},
                    "Tunisia": {"top_2": 0.35},
                }
            },
            "away_win": {
                "qualification_probabilities": {
                    "Japan": {"top_2": 0.25},
                    "Tunisia": {"top_2": 0.70},
                }
            },
        }
    }

    swing = calculate_qualification_swing(scenario_result, "Japan", "Tunisia")

    assert set(swing) == {"Japan", "Tunisia"}
    for team in ("Japan", "Tunisia"):
        assert set(swing[team]) == {
            "top_2_if_win",
            "top_2_if_draw",
            "top_2_if_loss",
            "win_vs_draw_swing",
            "draw_vs_loss_swing",
        }

