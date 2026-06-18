RISK_LABELS = {
    "No value": "无明显价值",
    "Small edge": "小幅优势",
    "Medium edge": "中等优势",
    "High edge / High uncertainty": "高优势 / 高不确定性",
}


def format_probability(value: float) -> str:
    return f"{value:.1%}"


def format_edge(value: float) -> str:
    return f"{value:+.1%}"


def format_ev(value: float, show_positive_sign: bool = False) -> str:
    if show_positive_sign:
        return f"{value:+.3f}"
    return f"{value:.3f}"


def localize_risk(risk: str) -> str:
    return RISK_LABELS.get(risk, risk)


def outcome_label(outcome: str, home_team: str, away_team: str) -> str:
    if outcome == "home":
        return f"{home_team} 胜"
    if outcome == "away":
        return f"{away_team} 胜"
    return "平局"
