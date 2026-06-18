from analysis_engine import build_match_analysis
from betting.handicap import format_handicap_line, format_handicap_result_label
from betting.odds import no_vig_probabilities
from betting.value import calculate_edge, calculate_ev, classify_risk
from display import format_edge, format_ev, format_probability, outcome_label
from tournament.scenario import calculate_qualification_swing


def generate_match_report(input_data: dict) -> str:
    group = input_data.get("group", "")
    match_id = input_data.get("match_id", "")
    home_team = input_data["home_team"]
    away_team = input_data["away_team"]
    odds = input_data["odds"]
    model_probs = input_data["model_probabilities"]
    scenario_analysis = input_data.get("scenario_analysis")
    analysis = input_data.get("analysis")
    market_type = input_data.get("market_type", "normal")
    handicap = input_data.get("handicap")
    data_source = input_data.get("data_source")

    market_probs = no_vig_probabilities(odds["home"], odds["draw"], odds["away"])
    rows = _build_market_rows(home_team, away_team, odds, model_probs, market_probs, market_type, handicap)
    if analysis is None and scenario_analysis:
        analysis = build_match_analysis(
            match_label=_format_match_name(group, match_id, home_team, away_team),
            home_team=home_team,
            away_team=away_team,
            market_rows=rows,
            current_table=scenario_analysis["current_table"],
            qualification_swing=calculate_qualification_swing(scenario_analysis, home_team, away_team),
            scenario_analysis=scenario_analysis,
            market_type=market_type,
            handicap=handicap,
        )

    if analysis is None:
        return _fallback_report(group, match_id, home_team, away_team, rows, market_type, data_source)

    best_market = max(market_probs, key=market_probs.get)
    best_model = max(model_probs, key=model_probs.get)
    best_value = analysis["best_value"]

    lines = [
        f"比赛：{_format_match_name(group, match_id, home_team, away_team)}",
        f"市场：{_format_market_name(market_type, home_team, handicap)}",
        *(_data_source_lines(data_source, scenario_analysis)),
        "",
        "一、核心判断",
        analysis["core_summary"],
        analysis["market_context_summary"],
        "",
        "二、赔率与价值判断",
        analysis["value_summary"],
        f"- 市场最看好：{_display_outcome_label(best_market, home_team, away_team, market_type, handicap)} {format_probability(market_probs[best_market])}",
        f"- 模型最看好：{_display_outcome_label(best_model, home_team, away_team, market_type, handicap)} {format_probability(model_probs[best_model])}",
        f"- 最高 EV：{best_value['outcome']} {format_ev(best_value['ev'], show_positive_sign=True)}，概率差 {format_edge(best_value['edge'])}",
        f"- 信号是否一致：{_signal_alignment_text(analysis)}",
        "",
        "三、出线动机",
        analysis["motivation_summary"],
        _format_motivation_line(analysis["motivation"]["home"]),
        _format_motivation_line(analysis["motivation"]["away"]),
        "",
        "四、风险点",
        analysis["risk_summary"],
        f"- 积分形势：{_format_table_context(scenario_analysis['current_table']) if scenario_analysis else '暂无积分榜数据。'}",
        f"- 情景敏感度：{_format_sensitivity(analysis)}",
        "- 临场关注：首发阵容、伤停信息、盘口变化以及比赛后段的节奏选择。",
        "",
        "五、最终观点",
        analysis["final_view"],
        *(_manual_final_notes(data_source, scenario_analysis, market_type)),
        *(_handicap_final_notes() if market_type == "handicap" else []),
        "以上内容仅作为辅助判断，不构成明确投注建议。",
    ]
    return "\n".join(lines)


def _build_market_rows(
    home_team: str,
    away_team: str,
    odds: dict,
    model_probs: dict,
    market_probs: dict,
    market_type: str,
    handicap: int | None,
) -> list[dict]:
    rows = []
    outcome_specs = [
        ("handicap_home", "home"),
        ("handicap_draw", "draw"),
        ("handicap_away", "away"),
    ] if market_type == "handicap" else [
        ("home", "home"),
        ("draw", "draw"),
        ("away", "away"),
    ]
    for outcome, probability_key in outcome_specs:
        edge = calculate_edge(model_probs[probability_key], market_probs[probability_key])
        ev = calculate_ev(model_probs[probability_key], odds[probability_key])
        rows.append(
            {
                "outcome": outcome,
                "label": format_handicap_result_label(home_team, away_team, int(handicap or 0), outcome) if market_type == "handicap" else outcome_label(outcome, home_team, away_team),
                "market_prob": market_probs[probability_key],
                "model_prob": model_probs[probability_key],
                "edge": edge,
                "ev": ev,
                "risk": classify_risk(edge, ev),
            }
        )
    return rows


def _format_market_name(market_type: str, home_team: str, handicap: int | None) -> str:
    if market_type == "handicap":
        return f"让球胜平负（{format_handicap_line(home_team, int(handicap or 0))}）"
    return "普通胜平负"


def _display_outcome_label(outcome: str, home_team: str, away_team: str, market_type: str, handicap: int | None) -> str:
    if market_type == "handicap":
        return format_handicap_result_label(home_team, away_team, int(handicap or 0), f"handicap_{outcome}")
    return outcome_label(outcome, home_team, away_team)


def _format_match_name(group: str, match_id: str, home_team: str, away_team: str) -> str:
    prefix = ""
    if group:
        prefix += f"{group}组"
    if match_id:
        prefix += f" {match_id}"
    if prefix:
        prefix += ": "
    return f"{prefix}{home_team} vs {away_team}"


def _format_motivation_line(team_data: dict) -> str:
    return (
        f"- {team_data['team']}：赢球后前二概率 {format_probability(team_data['top2_if_win'])}，"
        f"打平 {format_probability(team_data['top2_if_draw'])}，"
        f"输球 {format_probability(team_data['top2_if_loss'])}；"
        f"争胜动机 {team_data['win_motivation']}，保平/不败动机 {team_data['avoid_loss_motivation']}。"
    )


def _format_table_context(table: list[dict]) -> str:
    return "；".join(
        f"{row['team']} {row['points']}分，净胜球{row['goal_difference']}"
        for row in table
    )


def _format_sensitivity(analysis: dict) -> str:
    home = analysis["motivation"]["home"]
    away = analysis["motivation"]["away"]
    return (
        f"{home['team']} 前二概率区间跨度 {format_edge(home['top2_range'])}，"
        f"{away['team']} 前二概率区间跨度 {format_edge(away['top2_range'])}。"
    )


def _signal_alignment_text(analysis: dict) -> str:
    final_view = analysis["final_view"]
    if "冲突" in final_view or "不一定便宜" in final_view:
        return "赔率价值与出线动机存在分歧。"
    if "方向一致" in final_view or "没有明显冲突" in final_view:
        return "赔率信号与出线动机大体一致。"
    return "需要结合临场信息继续验证。"


def _handicap_final_notes() -> list[str]:
    return [
        "让球胜平负分析的是让球后的赛果，出线形势仍然基于真实比赛结果。",
        "因此，赔率 value 与战意之间可能不是一一对应关系。",
        "如果预期强队小胜概率较高，让负或让平可能更值得关注；如果预期比赛后段保守，让球盘穿盘难度可能上升。",
    ]


def _data_source_lines(data_source: str | None, scenario_analysis: dict | None) -> list[str]:
    if data_source != "manual":
        return []
    lines = [
        "数据来源：手动输入赔率。",
        "当前赔率为用户手动录入，需以出票时刻为准。",
    ]
    if not scenario_analysis:
        lines.append("本场未匹配本地小组情景，因此报告仅分析市场赔率与模型概率。")
    return lines


def _manual_final_notes(data_source: str | None, scenario_analysis: dict | None, market_type: str) -> list[str]:
    if data_source != "manual":
        return []
    notes = ["手动录入赔率不保证与实时体彩一致。"]
    if not scenario_analysis:
        notes.append("本场未匹配本地小组情景，因此报告仅分析市场赔率与模型概率。")
    if market_type == "handicap":
        notes.append("让球胜平负分析的是让球后的赛果。")
    return notes


def _fallback_report(group: str, match_id: str, home_team: str, away_team: str, rows: list[dict], market_type: str, data_source: str | None) -> str:
    best = max(rows, key=lambda row: row["ev"])
    return "\n".join(
        [
            f"比赛：{_format_match_name(group, match_id, home_team, away_team)}",
            f"市场：{'让球胜平负' if market_type == 'handicap' else '普通胜平负'}",
            *(_data_source_lines(data_source, None)),
            "",
            "一、核心判断",
            "当前缺少完整小组情景数据，只能进行赔率与模型概率层面的初步判断。",
            "",
            "二、赔率与价值判断",
            f"相对最高的期望收益来自 {best['label']}，期望收益（EV）为 {format_ev(best['ev'], show_positive_sign=True)}。",
            "",
            "五、最终观点",
            "该结果仅作为辅助判断，不构成明确投注建议。",
            *(_manual_final_notes(data_source, None, market_type)),
        ]
    )
