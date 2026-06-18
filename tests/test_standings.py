from tournament.standings import calculate_group_standings


def test_calculate_group_standings():
    matches = [
        {"home": "Netherlands", "away": "Japan", "home_score": 2, "away_score": 2},
        {"home": "Sweden", "away": "Tunisia", "home_score": 5, "away_score": 1},
    ]

    standings = calculate_group_standings(matches)

    assert standings[0]["team"] == "Sweden"
    assert standings[0]["points"] == 3
    assert standings[0]["goal_difference"] == 4
    assert standings[1]["team"] == "Netherlands"
    assert standings[1]["points"] == 1
    assert standings[2]["team"] == "Japan"
    assert standings[2]["points"] == 1
    assert standings[3]["team"] == "Tunisia"
    assert standings[3]["points"] == 0

