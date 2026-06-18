import pandas as pd
import pytest

from data_loader import (
    get_completed_matches,
    get_group_matches,
    get_groups,
    get_handicap_odds_for_match,
    get_match_probabilities_for_group,
    get_model_probabilities_for_match,
    get_remaining_matches,
    get_odds_for_match,
    load_groups,
    load_matches,
    load_match_probabilities,
    load_odds,
    validate_tournament_data,
)


def test_groups_load_correctly(tmp_path):
    path = tmp_path / "groups.csv"
    path.write_text("group,team\nF,Japan\nF,Tunisia\n", encoding="utf-8")

    groups_df = load_groups(str(path))

    assert get_groups(groups_df) == ["F"]


def test_matches_load_and_split_correctly(tmp_path):
    path = tmp_path / "matches.csv"
    path.write_text(
        "match_id,group,home,away,home_score,away_score,status\n"
        "F1,F,Japan,Tunisia,2,1,completed\n"
        "F2,F,Japan,Sweden,,,scheduled\n",
        encoding="utf-8",
    )

    matches_df = load_matches(str(path))

    assert len(get_group_matches(matches_df, "F")) == 2
    assert get_completed_matches(matches_df, "F") == [
        {"home": "Japan", "away": "Tunisia", "home_score": 2, "away_score": 1}
    ]
    assert get_remaining_matches(matches_df, "F") == [
        {"home": "Japan", "away": "Sweden"}
    ]


def test_probabilities_sum_validation_works(tmp_path):
    path = tmp_path / "match_probabilities.csv"
    path.write_text("match_id,p_home,p_draw,p_away\nF2,0.50,0.20,0.20\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must sum to 1.0"):
        load_match_probabilities(str(path))


def test_missing_probability_row_raises_value_error():
    matches_df = pd.DataFrame(
        [
            {"match_id": "F1", "group": "F", "home": "Japan", "away": "Tunisia", "status": "scheduled"},
        ]
    )
    probabilities_df = pd.DataFrame(
        [
            {"match_id": "F2", "p_home": 0.40, "p_draw": 0.30, "p_away": 0.30},
        ]
    )

    with pytest.raises(ValueError, match="missing probability row"):
        get_match_probabilities_for_group(matches_df, probabilities_df, "F")


def test_invalid_odds_raises_value_error(tmp_path):
    path = tmp_path / "odds.csv"
    path.write_text("match_id,home_odds,draw_odds,away_odds\nF4,1.00,3.40,1.85\n", encoding="utf-8")

    with pytest.raises(ValueError, match="greater than 1.0"):
        load_odds(str(path))


def test_odds_for_match_returns_dict_or_none():
    odds_df = pd.DataFrame(
        [
            {"match_id": "F4", "home_odds": 4.50, "draw_odds": 3.40, "away_odds": 1.85},
        ]
    )

    assert get_odds_for_match(odds_df, "F4") == {"home": 4.50, "draw": 3.40, "away": 1.85}
    assert get_odds_for_match(odds_df, "F3") is None


def test_handicap_odds_load_correctly():
    odds_df = pd.DataFrame(
        [
            {
                "match_id": "F3",
                "home_odds": 2.00,
                "draw_odds": 3.20,
                "away_odds": 3.50,
                "handicap": -1,
                "handicap_home_odds": 4.20,
                "handicap_draw_odds": 3.70,
                "handicap_away_odds": 1.62,
            }
        ]
    )

    assert get_handicap_odds_for_match(odds_df, "F3") == {
        "handicap": -1,
        "handicap_home_odds": 4.20,
        "handicap_draw_odds": 3.70,
        "handicap_away_odds": 1.62,
    }


def test_missing_handicap_odds_returns_none():
    odds_df = pd.DataFrame(
        [
            {"match_id": "F4", "home_odds": 4.50, "draw_odds": 3.40, "away_odds": 1.85},
        ]
    )

    assert get_handicap_odds_for_match(odds_df, "F4") is None


def test_invalid_handicap_odds_raises_value_error(tmp_path):
    path = tmp_path / "odds.csv"
    path.write_text(
        "match_id,home_odds,draw_odds,away_odds,handicap,handicap_home_odds,handicap_draw_odds,handicap_away_odds\n"
        "F3,2.00,3.20,3.50,-1,1.00,3.70,1.62\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="handicap decimal odds"):
        load_odds(str(path))


def test_partial_handicap_probabilities_raise_value_error(tmp_path):
    path = tmp_path / "match_probabilities.csv"
    path.write_text(
        "match_id,p_home,p_draw,p_away,p_handicap_home,p_handicap_draw,p_handicap_away\n"
        "F3,0.38,0.30,0.32,0.21,,0.54\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must all be present"):
        load_match_probabilities(str(path))


def test_complete_handicap_probabilities_sum_validation_works(tmp_path):
    path = tmp_path / "match_probabilities.csv"
    path.write_text(
        "match_id,p_home,p_draw,p_away,p_handicap_home,p_handicap_draw,p_handicap_away\n"
        "F3,0.38,0.30,0.32,0.21,0.25,0.50\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="handicap probabilities"):
        load_match_probabilities(str(path))


def test_model_probabilities_for_match_by_market():
    probabilities_df = pd.DataFrame(
        [
            {
                "match_id": "F3",
                "p_home": 0.38,
                "p_draw": 0.30,
                "p_away": 0.32,
                "p_handicap_home": 0.21,
                "p_handicap_draw": 0.25,
                "p_handicap_away": 0.54,
            }
        ]
    )

    assert get_model_probabilities_for_match(probabilities_df, "F3", "normal") == {"home": 0.38, "draw": 0.30, "away": 0.32}
    assert get_model_probabilities_for_match(probabilities_df, "F3", "handicap") == {"home": 0.21, "draw": 0.25, "away": 0.54}


def test_validate_tournament_data_rejects_unknown_team():
    groups_df = pd.DataFrame([{"group": "F", "team": "Japan"}])
    matches_df = pd.DataFrame(
        [
            {
                "match_id": "F1",
                "group": "F",
                "home": "Japan",
                "away": "Tunisia",
                "home_score": 2,
                "away_score": 1,
                "status": "completed",
            }
        ]
    )
    probabilities_df = pd.DataFrame(columns=["match_id", "p_home", "p_draw", "p_away"])
    odds_df = pd.DataFrame(columns=["match_id", "home_odds", "draw_odds", "away_odds"])

    with pytest.raises(ValueError, match="unknown team"):
        validate_tournament_data(groups_df, matches_df, probabilities_df, odds_df)


def test_data_integrity_for_all_groups():
    groups_df = load_groups()
    matches_df = load_matches()
    probabilities_df = load_match_probabilities()
    odds_df = load_odds()

    # 1. 确认 groups.csv 包含 A–L 共 12 个小组。
    groups = groups_df["group"].dropna().unique().tolist()
    expected_groups = [chr(i) for i in range(ord('A'), ord('L') + 1)]
    assert sorted(groups) == expected_groups

    # 2. 确认每个小组有 4 支球队。
    for g in expected_groups:
        teams = groups_df[groups_df["group"] == g]["team"].tolist()
        assert len(teams) == 4, f"Group {g} must have 4 teams"

    # 3. 确认每个小组有 6 场比赛。
    for g in expected_groups:
        matches = matches_df[matches_df["group"] == g]
        assert len(matches) == 6, f"Group {g} must have 6 matches"

    # 4. 确认每个 scheduled match 都有 match_probabilities.csv 行。
    scheduled_matches = matches_df[matches_df["status"] == "scheduled"]
    scheduled_ids = scheduled_matches["match_id"].tolist()
    prob_ids = probabilities_df["match_id"].tolist()

    for mid in scheduled_ids:
        assert mid in prob_ids, f"Scheduled match {mid} must have a row in match_probabilities.csv"

    # 5. 确认所有 normal probabilities 合计约等于 1.0。
    for row in probabilities_df.itertuples(index=False):
        total = float(row.p_home) + float(row.p_draw) + float(row.p_away)
        assert abs(total - 1.0) < 0.01, f"Match {row.match_id} normal probabilities sum must be 1.0"

    # 6. 如果 handicap probabilities 存在，确认三项合计约等于 1.0。
    if "p_handicap_home" in probabilities_df.columns:
        for _, row in probabilities_df.iterrows():
            if pd.notna(row["p_handicap_home"]) and pd.notna(row["p_handicap_draw"]) and pd.notna(row["p_handicap_away"]):
                total = float(row["p_handicap_home"]) + float(row["p_handicap_draw"]) + float(row["p_handicap_away"])
                assert abs(total - 1.0) < 0.01, f"Match {row['match_id']} handicap probabilities sum must be 1.0"

    # 7. 确认 odds.csv 中所有非空赔率都 > 1.0。
    for _, row in odds_df.iterrows():
        for col in ["home_odds", "draw_odds", "away_odds"]:
            if pd.notna(row[col]):
                assert float(row[col]) > 1.0, f"Match {row['match_id']} {col} must be > 1.0"
        for col in ["handicap_home_odds", "handicap_draw_odds", "handicap_away_odds"]:
            if pd.notna(row[col]):
                assert float(row[col]) > 1.0, f"Match {row['match_id']} {col} must be > 1.0"

    # 8. 确认 handicap 是整数或空值。
    for _, row in odds_df.iterrows():
        if pd.notna(row["handicap"]):
            val = row["handicap"]
            assert int(val) == val, f"Match {row['match_id']} handicap must be an integer"
