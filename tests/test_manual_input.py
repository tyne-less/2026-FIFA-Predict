import pandas as pd
import pytest

from betting.odds import no_vig_probabilities
from betting.value import calculate_edge, calculate_ev, classify_risk
from manual_input import (
    build_manual_odds_record,
    find_group_for_teams,
    build_manual_match_from_local,
    get_scheduled_matches_for_group,
)


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


def test_get_scheduled_matches_for_group():
    matches_df = pd.DataFrame(
        [
            {"match_id": "D1", "group": "D", "home": "United States", "away": "Paraguay", "status": "completed"},
            {"match_id": "D3", "group": "D", "home": "United States", "away": "Australia", "status": "scheduled"},
            {"match_id": "E3", "group": "E", "home": "Germany", "away": "Ivory Coast", "status": "scheduled"},
        ]
    )

    scheduled = get_scheduled_matches_for_group(matches_df, "D")
    assert len(scheduled) == 1
    assert scheduled[0]["match_id"] == "D3"
    assert scheduled[0]["status"] == "scheduled"


def test_build_manual_match_from_local():
    match_row = {"match_id": "D3", "group": "D", "home": "United States", "away": "Australia", "status": "scheduled"}
    manual_match = build_manual_match_from_local(match_row)

    assert manual_match["match_id"] == "D3"
    assert manual_match["match_code"] == "D3"
    assert manual_match["home"] == "United States"
    assert manual_match["away"] == "Australia"
    assert manual_match["group"] == "D"
    assert manual_match["status"] == "scheduled"


def test_build_manual_odds_record_supports_custom_match_id():
    record = build_manual_odds_record(
        match_code="D3",
        league="世界杯",
        kickoff_time="2026-06-18 21:00",
        home_team="United States",
        away_team="Australia",
        normal_home_odds=1.47,
        normal_draw_odds=3.70,
        normal_away_odds=5.60,
        handicap=-1,
        handicap_home_odds=2.56,
        handicap_draw_odds=3.30,
        handicap_away_odds=2.30,
        match_id="D3",
    )

    assert record["match_id"] == "D3"
    assert record["match_code"] == "D3"


def test_find_group_for_teams_matches_local_correctly():
    groups_df = pd.DataFrame(
        [
            {"group": "D", "team": "United States"},
            {"group": "D", "team": "Australia"},
            {"group": "E", "team": "Germany"},
        ]
    )

    assert find_group_for_teams(groups_df, "United States", "Australia") == "D"
    assert find_group_for_teams(groups_df, "United States", "Germany") is None


def test_local_odds_can_be_overridden_by_manual():
    # 本地数据原始赔率
    local_odds_record = {
        "match_id": "D3",
        "home_odds": 2.00,
        "draw_odds": 3.20,
        "away_odds": 3.50,
    }

    # 用户手动输入覆盖
    manual_record = build_manual_odds_record(
        match_code="D3",
        league="世界杯",
        kickoff_time="",
        home_team="United States",
        away_team="Australia",
        normal_home_odds=1.47,  # 手动输入覆盖
        normal_draw_odds=3.70,  # 手动输入覆盖
        normal_away_odds=5.60,  # 手动输入覆盖
        handicap=-1,
        handicap_home_odds=2.56,
        handicap_draw_odds=3.30,
        handicap_away_odds=2.30,
        match_id="D3",
    )

    assert manual_record["normal"]["home_odds"] == 1.47
    assert manual_record["normal"]["home_odds"] != local_odds_record["home_odds"]


def test_local_scenario_data_still_loadable_with_manual_odds():
    # 模拟在手动覆盖赔率模式下，仍然能用本地 match_id 从 matches_df 中获取模拟场景数据
    matches_df = pd.DataFrame(
        [
            {"match_id": "D1", "group": "D", "home": "United States", "away": "Paraguay", "home_score": 4, "away_score": 1, "status": "completed"},
            {"match_id": "D3", "group": "D", "home": "United States", "away": "Australia", "home_score": None, "away_score": None, "status": "scheduled"},
        ]
    )

    # 通过手动输入得到关联的 match_id D3
    manual_match_id = "D3"
    group = "D"

    # 从 matches_df 中提取关联小组赛程
    group_matches = matches_df[matches_df["group"] == group]
    completed_matches = group_matches[group_matches["status"] == "completed"].to_dict(orient="records")
    remaining_matches = group_matches[group_matches["status"] == "scheduled"].to_dict(orient="records")

    assert len(completed_matches) == 1
    assert completed_matches[0]["match_id"] == "D1"
    assert len(remaining_matches) == 1
    assert remaining_matches[0]["match_id"] == manual_match_id

