from display import format_edge, format_ev, format_probability, localize_risk


def build_match_analysis(
    match_label: str,
    home_team: str,
    away_team: str,
    market_rows: list[dict],
    current_table: list[dict],
    qualification_swing: list[dict] | dict,
    scenario_analysis: dict,
    market_type: str = "normal",
    handicap: int | None = None,
) -> dict:
    swing = _normalize_swing(qualification_swing)
    best = max(market_rows, key=lambda row: row["ev"])
    positive_rows = [row for row in market_rows if row["ev"] > 0]
    all_negative = not positive_rows
    best_value = _build_best_value(best, all_negative)
    motivation = {
        "home": _build_team_motivation(home_team, swing[home_team]),
        "away": _build_team_motivation(away_team, swing[away_team]),
    }

    market_context_summary = _build_market_context_summary(market_type, handicap)
    market_sentence = _market_model_sentence(best, market_type)
    value_summary = _build_value_summary(best, all_negative, market_sentence, market_type)
    motivation_summary = _build_motivation_summary(home_team, away_team, motivation)
    risk_summary = _build_risk_summary(motivation)
    contradiction = _detect_signal_alignment(best, home_team, away_team, market_rows, motivation, market_type)
    core_summary = f"{match_label}：{value_summary} {contradiction}"
    final_view = _build_final_view(value_summary, motivation_summary, risk_summary, contradiction)
    ui_summary = _build_ui_summary(best, all_negative, motivation, risk_summary, contradiction, market_type)

    return {
        "market_context_summary": market_context_summary,
        "core_summary": core_summary,
        "value_summary": value_summary,
        "motivation_summary": motivation_summary,
        "risk_summary": risk_summary,
        "final_view": final_view,
        "ui_summary": ui_summary,
        "key_flags": _build_key_flags(best, all_negative, motivation, risk_summary, contradiction),
        "best_value": best_value,
        "motivation": motivation,
    }


def build_signal_explanation(row: dict, analysis: dict, home_team: str, away_team: str, market_type: str = "normal") -> str:
    explanations = []
    diff = row["model_prob"] - row["market_prob"]
    if row["ev"] > 0:
        explanations.append("正 EV，需结合真实赛果倾向" if market_type == "handicap" else "正 EV，但需验证")
    if diff > 0.05:
        explanations.append("让球后模型高于市场" if market_type == "handicap" else "模型高于市场")
    elif abs(diff) <= 0.02:
        explanations.append("让球市场充分定价" if market_type == "handicap" else "市场充分定价")
    elif diff < -0.05:
        explanations.append("让球后赔率偏贵" if market_type == "handicap" else "模型低于市场")

    if market_type == "handicap" and row["ev"] > 0:
        explanations.append("让球 value 与出线动机不完全等价")
        return "；".join(explanations)

    if row["outcome"] in ("home", "away"):
        side = "home" if row["outcome"] == "home" else "away"
        other_side = "away" if side == "home" else "home"
        own_motivation = analysis["motivation"][side]["win_vs_draw_swing"]
        other_motivation = analysis["motivation"][other_side]["win_vs_draw_swing"]
        if row["ev"] > 0 and own_motivation >= other_motivation:
            explanations.append("战意支持")
        elif row["ev"] > 0 and other_motivation - own_motivation >= 0.15:
            explanations.append("战意与赔率信号冲突")
    elif row["ev"] > 0:
        home_avoid = analysis["motivation"]["home"]["draw_vs_loss_swing"]
        away_avoid = analysis["motivation"]["away"]["draw_vs_loss_swing"]
        if home_avoid >= 0.25 and away_avoid >= 0.25:
            explanations.append("战意支持")

    return "；".join(explanations) if explanations else "需结合临场信息"


def _normalize_swing(qualification_swing: list[dict] | dict) -> dict:
    if isinstance(qualification_swing, dict):
        return qualification_swing
    return {row["team"]: row for row in qualification_swing}


def _build_best_value(best: dict, all_negative: bool) -> dict:
    result = {
        "outcome": best["label"],
        "ev": best["ev"],
        "edge": best["edge"],
        "risk": localize_risk(best["risk"]),
    }
    if all_negative:
        result["type"] = "best_relative_option"
    return result


def _build_market_context_summary(market_type: str, handicap: int | None) -> str:
    if market_type == "handicap":
        return "当前市场为让球胜平负，判断对象是让球后的赛果，需要和真实出线动机分开理解。"
    return "当前市场为普通胜平负，直接对应真实比赛赛果。"


def _build_value_summary(best: dict, all_negative: bool, market_sentence: str, market_type: str) -> str:
    if all_negative:
        prefix = "当前三项让球赛果均未显示正期望收益" if market_type == "handicap" else "当前三项赛果均未显示正期望收益"
        return f"{prefix}，赔率层面暂不构成明显入场点。{market_sentence}"

    if best["ev"] >= 0.10 and best["edge"] >= 0.05:
        label = "存在一定 value"
    elif best["edge"] < 0.03:
        label = "优势较弱"
    elif "High" in best["risk"] or "uncertainty" in best["risk"].lower():
        label = "有 value，但波动较大"
    else:
        label = "存在正期望收益"

    if market_type == "handicap":
        detail = _handicap_value_detail(best["outcome"])
        return (
            f"{best['label']} {label}，期望收益（EV）为 {format_ev(best['ev'], show_positive_sign=True)}，"
            f"概率差为 {format_edge(best['edge'])}。当前分析对象为让球胜平负，赔率价值基于让球后的赛果，不等同于真实胜平负。"
            f"{detail}{market_sentence}"
        )

    return f"{best['label']} {label}，期望收益（EV）为 {format_ev(best['ev'], show_positive_sign=True)}，概率差为 {format_edge(best['edge'])}。{market_sentence}"


def _handicap_value_detail(outcome: str) -> str:
    if outcome == "handicap_home":
        return "让胜存在正期望收益时，需要注意出线动机影响真实比赛策略，不一定直接对应让球穿盘。"
    if outcome == "handicap_away":
        return "让负 value 可能代表客队不败或主队小胜的情形，需要结合比分区间理解。"
    if outcome == "handicap_draw":
        return "让平 value 通常依赖较窄比分区间，需要结合强弱差距和比赛节奏理解。"
    return ""


def _market_model_sentence(row: dict, market_type: str) -> str:
    diff = row["model_prob"] - row["market_prob"]
    prefix = "让球后" if market_type == "handicap" else ""
    if diff > 0.05:
        return f"{prefix}模型明显高于市场。"
    if abs(diff) <= 0.02:
        return "让球市场基本充分定价。" if market_type == "handicap" else "模型与市场接近，赔率基本充分定价。"
    if diff < -0.05:
        return "让球后模型低于市场，当前赔率偏贵。" if market_type == "handicap" else "模型低于市场，当前赔率偏贵。"
    return "模型与市场存在一定分歧，但幅度不算极端。"


def _build_team_motivation(team: str, swing: dict) -> dict:
    win_level = _motivation_level(swing["win_vs_draw_swing"])
    avoid_loss_level = _motivation_level(swing["draw_vs_loss_swing"])
    return {
        "team": team,
        "top2_if_win": swing["top_2_if_win"],
        "top2_if_draw": swing["top_2_if_draw"],
        "top2_if_loss": swing["top_2_if_loss"],
        "win_vs_draw_swing": swing["win_vs_draw_swing"],
        "draw_vs_loss_swing": swing["draw_vs_loss_swing"],
        "motivation_level": _combined_motivation_level(win_level, avoid_loss_level),
        "win_motivation": win_level,
        "avoid_loss_motivation": avoid_loss_level,
        "top2_range": max(swing["top_2_if_win"], swing["top_2_if_draw"], swing["top_2_if_loss"])
        - min(swing["top_2_if_win"], swing["top_2_if_draw"], swing["top_2_if_loss"]),
    }


def _motivation_level(value: float) -> str:
    if value >= 0.25:
        return "强"
    if value >= 0.10:
        return "中等"
    return "较弱"


def _combined_motivation_level(win_level: str, avoid_loss_level: str) -> str:
    if win_level == "强" and avoid_loss_level == "强":
        return "强"
    if win_level == "强" or avoid_loss_level == "强":
        return "中等偏强"
    if win_level == "中等" or avoid_loss_level == "中等":
        return "中等"
    return "较弱"


def _build_motivation_summary(home_team: str, away_team: str, motivation: dict) -> str:
    parts = []
    for side in ("home", "away"):
        team_data = motivation[side]
        team = team_data["team"]
        if team_data["win_motivation"] == "强":
            parts.append(f"{team} 赢球相对平局能显著提升前二出线概率，主动争胜动机较强。")
        if team_data["avoid_loss_motivation"] == "强":
            parts.append(f"{team} 平局相对输球能保留大量出线概率，比赛后段可能更重视不输。")

    if motivation["home"]["avoid_loss_motivation"] == "强" and motivation["away"]["avoid_loss_motivation"] == "强":
        parts.append("双方都存在较强的不败需求，平局或低风险策略需要重点关注。")

    diff = motivation["home"]["win_vs_draw_swing"] - motivation["away"]["win_vs_draw_swing"]
    if abs(diff) >= 0.15:
        stronger = home_team if diff > 0 else away_team
        parts.append(f"双方战意并不对称，{stronger} 对胜利的边际收益更高。")

    return " ".join(parts) if parts else "双方出线动机差异不算极端，需要结合临场阵容与比赛进程判断。"


def _build_risk_summary(motivation: dict) -> str:
    parts = []
    home_range = motivation["home"]["top2_range"]
    away_range = motivation["away"]["top2_range"]
    if home_range >= 0.50 or away_range >= 0.50:
        parts.append("本场对出线概率影响极大，比赛策略可能随比分变化明显。")
    if home_range >= 0.30 and away_range >= 0.30:
        parts.append("双方出线情景都较敏感，赛中状态和临场选择会显著改变风险。")
    return " ".join(parts) if parts else "情景波动处于可控区间，但仍需要关注临场阵容、伤停和市场变化。"


def _detect_signal_alignment(best: dict, home_team: str, away_team: str, market_rows: list[dict], motivation: dict, market_type: str) -> str:
    if market_type == "handicap":
        return "让球赔率价值与真实出线动机不是一一对应关系，需要结合比分分布和比赛阶段分开判断。"

    home_win_motivation = motivation["home"]["win_vs_draw_swing"]
    away_win_motivation = motivation["away"]["win_vs_draw_swing"]
    home_row = _find_row(market_rows, "home")
    draw_row = _find_row(market_rows, "draw")

    if draw_row["ev"] > 0 and motivation["home"]["avoid_loss_motivation"] == "强" and motivation["away"]["avoid_loss_motivation"] == "强":
        return "平局 value 与双方不败需求方向一致。"
    if best["outcome"] == "away" and home_win_motivation - away_win_motivation >= 0.15:
        return "赔率层面更偏向客胜 value，但出线动机层面主队更需要胜利，信号并不完全一致。"
    if best["outcome"] == "home" and away_win_motivation - home_win_motivation >= 0.15:
        return "赔率层面更偏向主胜 value，但出线动机层面客队更需要胜利，信号并不完全一致。"
    if home_win_motivation >= 0.25 and home_row["ev"] <= 0:
        return "主队战意较强，但主胜赔率已经部分反映该因素，当前不一定便宜。"
    return "赔率信号与出线动机没有明显冲突，但仍需要临场信息验证。"


def _find_row(rows: list[dict], outcome: str) -> dict:
    for row in rows:
        if row["outcome"] == outcome:
            return row
    raise ValueError(f"missing outcome row: {outcome}")


def _build_final_view(value_summary: str, motivation_summary: str, risk_summary: str, contradiction: str) -> str:
    return f"{value_summary} {motivation_summary} {risk_summary} {contradiction}"


def _build_ui_summary(best: dict, all_negative: bool, motivation: dict, risk_summary: str, contradiction: str, market_type: str) -> dict:
    if all_negative:
        value = "当前没有明显正 EV，赔率层面以观望为主。"
    else:
        suffix = "，让球盘需看比分区间" if market_type == "handicap" else ""
        value = f"{best['label']} EV 最高，为 {format_ev(best['ev'], show_positive_sign=True)}{suffix}。"

    home = motivation["home"]
    away = motivation["away"]
    if home["motivation_level"] == away["motivation_level"]:
        motivation_text = f"双方出线动机均为{home['motivation_level']}，需看比赛阶段变化。"
    else:
        stronger = home if home["top2_range"] >= away["top2_range"] else away
        motivation_text = f"{stronger['team']} 出线波动更大，战术取向更值得关注。"

    risk = "出线情景高度敏感，临场和比分变化会放大风险。" if "影响极大" in risk_summary else "主要风险来自临场阵容、伤停和市场变化。"
    final = "让球 value 与真实出线动机需分开判断。" if market_type == "handicap" else contradiction
    return {"value": value, "motivation": motivation_text, "risk": risk, "final": final}


def _build_key_flags(best: dict, all_negative: bool, motivation: dict, risk_summary: str, contradiction: str) -> list[dict]:
    flags = []
    if all_negative:
        flags.append({"type": "no_positive_ev", "level": "low", "text": "当前没有明显正期望收益。"})
    else:
        level = "medium" if best["ev"] < 0.15 else "high"
        flags.append({"type": "positive_ev", "level": level, "text": f"{best['label']}存在正期望收益，但仍需要结合临场信息。"})

    if "冲突" in contradiction or "不一定便宜" in contradiction:
        flags.append({"type": "signal_conflict", "level": "medium", "text": contradiction})

    if "影响极大" in risk_summary:
        flags.append({"type": "scenario_instability", "level": "high", "text": "出线情景对本场结果高度敏感。"})

    for side in ("home", "away"):
        team_data = motivation[side]
        if team_data["motivation_level"] in ("强", "中等偏强"):
            flags.append({"type": "motivation", "level": "medium", "text": f"{team_data['team']} 出线动机为{team_data['motivation_level']}。"})

    return flags
