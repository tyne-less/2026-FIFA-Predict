import pandas as pd
import pytest

from betting.odds import no_vig_probabilities
from betting.value import calculate_edge, calculate_ev, classify_risk
from manual_input import build_manual_odds_record, find_group_for_teams


def test_build_manual_odds_record_creates_normal_and_handicap_data():
    record = build_manual_odds_record(
        match_code="手动001",
        league="世界杯",
        kickoff_time="2026-06-18 21:00",
        home_team="美国",
        away_team="澳大利亚",
        normal_home_odds=1.47,
        normal_draw_odds=3.70,
        normal_away_odds=5.60,
        handicap=-1,
        handicap_home_odds=2.56,
        handicap_draw_odds=3.30,
        handicap_away_odds=2.30,
    )

    assert record["match_id"] == "manual_001"
    assert record["match_code"] == "手动001"
    assert record["normal"]["available"] is True
    assert record["normal"]["home_odds"] == 1.47
    assert record["handicap"]["available"] is True
    assert record["handicap"]["handicap"] == -1


def test_find_group_for_teams_returns_group_if_both_teams_are_in_same_group():
    groups_df = pd.DataFrame(
        [
            {"group": "D", "team": "美国"},
            {"group": "D", "team": "澳大利亚"},
            {"group": "E", "team": "日本"},
        ]
    )

    assert find_group_for_teams(groups_df, "美国", "澳大利亚") == "D"


def test_find_group_for_teams_returns_none_if_teams_are_not_in_same_group():
    groups_df = pd.DataFrame(
        [
            {"group": "D", "team": "美国"},
            {"group": "E", "team": "澳大利亚"},
        ]
    )

    assert find_group_for_teams(groups_df, "美国", "澳大利亚") is None


def test_manual_odds_validation_rejects_invalid_odds():
    with pytest.raises(ValueError):
        build_manual_odds_record(
            match_code="手动001",
            league="世界杯",
            kickoff_time="",
            home_team="美国",
            away_team="澳大利亚",
            normal_home_odds=1.00,
            normal_draw_odds=3.70,
            normal_away_odds=5.60,
            handicap=-1,
            handicap_home_odds=2.56,
            handicap_draw_odds=3.30,
            handicap_away_odds=2.30,
        )


def test_manual_mode_can_produce_market_rows_for_normal_market():
    record = build_manual_odds_record(
        match_code="手动001",
        league="世界杯",
        kickoff_time="",
        home_team="美国",
        away_team="澳大利亚",
        normal_home_odds=1.47,
        normal_draw_odds=3.70,
        normal_away_odds=5.60,
        handicap=-1,
        handicap_home_odds=2.56,
        handicap_draw_odds=3.30,
        handicap_away_odds=2.30,
    )
    odds = {
        "home": record["normal"]["home_odds"],
        "draw": record["normal"]["draw_odds"],
        "away": record["normal"]["away_odds"],
    }
    model_probs = {"home": 0.50, "draw": 0.28, "away": 0.22}
    market_probs = no_vig_probabilities(odds["home"], odds["draw"], odds["away"])
    row = {
        "outcome": "home",
        "market_prob": market_probs["home"],
        "model_prob": model_probs["home"],
        "edge": calculate_edge(model_probs["home"], market_probs["home"]),
        "ev": calculate_ev(model_probs["home"], odds["home"]),
    }
    row["risk"] = classify_risk(row["edge"], row["ev"])

    assert row["outcome"] == "home"
    assert isinstance(row["market_prob"], float)
    assert isinstance(row["ev"], float)
    assert row["risk"]
