from analysis_engine import build_match_analysis


def test_all_negative_ev_returns_no_value_summary_and_required_keys():
    result = build_match_analysis(
        match_label="F组 F4: Tunisia vs Japan",
        home_team="Tunisia",
        away_team="Japan",
        market_rows=[
            _row("home", "Tunisia 胜", 0.30, 0.25, -0.05, -0.10),
            _row("draw", "平局", 0.30, 0.29, -0.01, -0.03),
            _row("away", "Japan 胜", 0.40, 0.38, -0.02, -0.02),
        ],
        current_table=[],
        qualification_swing=_swing(),
        scenario_analysis={},
    )

    assert "当前三项赛果均未显示正期望收益" in result["value_summary"]
    assert result["best_value"]["type"] == "best_relative_option"
    assert {
        "market_context_summary",
        "core_summary",
        "value_summary",
        "motivation_summary",
        "risk_summary",
        "final_view",
        "ui_summary",
        "key_flags",
        "best_value",
        "motivation",
    } <= set(result)


def test_handicap_market_returns_context_summary():
    result = build_match_analysis(
        match_label="F组 F3: Netherlands vs Sweden",
        home_team="Netherlands",
        away_team="Sweden",
        market_rows=[
            _row("handicap_home", "让胜", 0.22, 0.21, -0.01, -0.05),
            _row("handicap_draw", "让平", 0.25, 0.25, 0.00, -0.02),
            _row("handicap_away", "让负", 0.53, 0.54, 0.01, 0.02),
        ],
        current_table=[],
        qualification_swing=_swing(),
        scenario_analysis={},
        market_type="handicap",
        handicap=-1,
    )

    assert "让球胜平负" in result["market_context_summary"]
    assert "让球后的赛果" in result["value_summary"]
    assert "不等同于真实胜平负" in result["value_summary"]
    assert result["ui_summary"]["final"] == "让球 value 与真实出线动机需分开判断。"


def test_ui_summary_contains_compact_dashboard_fields():
    result = build_match_analysis(
        match_label="F组 F3: Netherlands vs Sweden",
        home_team="Netherlands",
        away_team="Sweden",
        market_rows=[
            _row("home", "Netherlands 胜", 0.45, 0.38, -0.07, -0.24),
            _row("draw", "平局", 0.28, 0.30, 0.02, -0.04),
            _row("away", "Sweden 胜", 0.26, 0.32, 0.06, 0.12),
        ],
        current_table=[],
        qualification_swing=_swing(),
        scenario_analysis={},
    )

    assert {"value", "motivation", "risk", "final"} <= set(result["ui_summary"])
    assert all(isinstance(value, str) and value for value in result["ui_summary"].values())


def test_positive_ev_returns_best_value():
    result = build_match_analysis(
        match_label="F组 F3: Netherlands vs Sweden",
        home_team="Netherlands",
        away_team="Sweden",
        market_rows=[
            _row("home", "Netherlands 胜", 0.45, 0.38, -0.07, -0.24),
            _row("draw", "平局", 0.28, 0.30, 0.02, -0.04),
            _row("away", "Sweden 胜", 0.26, 0.32, 0.06, 0.12),
        ],
        current_table=[],
        qualification_swing=_swing(),
        scenario_analysis={},
    )

    assert result["best_value"]["outcome"] == "Sweden 胜"
    assert result["best_value"]["ev"] == 0.12
    assert "存在一定 value" in result["value_summary"]


def test_strong_win_swing_gives_strong_motivation():
    result = build_match_analysis(
        match_label="F组 F3: Netherlands vs Sweden",
        home_team="Netherlands",
        away_team="Sweden",
        market_rows=[
            _row("home", "Netherlands 胜", 0.45, 0.38, -0.07, -0.24),
            _row("draw", "平局", 0.28, 0.30, 0.02, -0.04),
            _row("away", "Sweden 胜", 0.26, 0.32, 0.06, 0.12),
        ],
        current_table=[],
        qualification_swing=_swing(home_win_vs_draw=0.37),
        scenario_analysis={},
    )

    assert result["motivation"]["home"]["win_motivation"] == "强"


def test_large_top2_range_triggers_instability_warning():
    result = build_match_analysis(
        match_label="F组 F3: Netherlands vs Sweden",
        home_team="Netherlands",
        away_team="Sweden",
        market_rows=[
            _row("home", "Netherlands 胜", 0.45, 0.38, -0.07, -0.24),
            _row("draw", "平局", 0.28, 0.30, 0.02, -0.04),
            _row("away", "Sweden 胜", 0.26, 0.32, 0.06, 0.12),
        ],
        current_table=[],
        qualification_swing=_swing(top2_if_win=0.95, top2_if_loss=0.30),
        scenario_analysis={},
    )

    assert "影响极大" in result["risk_summary"]


def test_contradiction_between_ev_and_motivation_is_detected():
    result = build_match_analysis(
        match_label="F组 F3: Netherlands vs Sweden",
        home_team="Netherlands",
        away_team="Sweden",
        market_rows=[
            _row("home", "Netherlands 胜", 0.45, 0.38, -0.07, -0.24),
            _row("draw", "平局", 0.28, 0.30, 0.02, -0.04),
            _row("away", "Sweden 胜", 0.26, 0.32, 0.06, 0.12),
        ],
        current_table=[],
        qualification_swing=_swing(home_win_vs_draw=0.40, away_win_vs_draw=0.12),
        scenario_analysis={},
    )

    assert "信号并不完全一致" in result["final_view"]


def _row(outcome: str, label: str, market_prob: float, model_prob: float, edge: float, ev: float) -> dict:
    return {
        "outcome": outcome,
        "label": label,
        "market_prob": market_prob,
        "model_prob": model_prob,
        "edge": edge,
        "ev": ev,
        "risk": "Medium edge" if ev > 0 else "No value",
    }


def _swing(
    home_win_vs_draw: float = 0.20,
    away_win_vs_draw: float = 0.16,
    top2_if_win: float = 0.80,
    top2_if_loss: float = 0.30,
) -> dict:
    home_draw = top2_if_win - home_win_vs_draw
    away_draw = 0.80 - away_win_vs_draw
    return {
        "Netherlands": {
            "top_2_if_win": top2_if_win,
            "top_2_if_draw": home_draw,
            "top_2_if_loss": top2_if_loss,
            "win_vs_draw_swing": home_win_vs_draw,
            "draw_vs_loss_swing": home_draw - top2_if_loss,
        },
        "Sweden": {
            "top_2_if_win": 0.80,
            "top_2_if_draw": away_draw,
            "top_2_if_loss": 0.35,
            "win_vs_draw_swing": away_win_vs_draw,
            "draw_vs_loss_swing": away_draw - 0.35,
        },
        "Tunisia": {
            "top_2_if_win": top2_if_win,
            "top_2_if_draw": home_draw,
            "top_2_if_loss": top2_if_loss,
            "win_vs_draw_swing": home_win_vs_draw,
            "draw_vs_loss_swing": home_draw - top2_if_loss,
        },
        "Japan": {
            "top_2_if_win": 0.80,
            "top_2_if_draw": away_draw,
            "top_2_if_loss": 0.35,
            "win_vs_draw_swing": away_win_vs_draw,
            "draw_vs_loss_swing": away_draw - 0.35,
        },
    }
