from pathlib import Path
import sys

# 确保 src/ 目录在 sys.path 中，以便 Streamlit Cloud 部署时能正确导入项目模块
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pandas as pd
import streamlit as st

from analysis_engine import build_match_analysis, build_signal_explanation
from betting.handicap import format_handicap_line, format_handicap_result_label
from betting.odds import no_vig_probabilities
from betting.value import calculate_edge, calculate_ev, classify_risk
from data_loader import (
    get_completed_matches,
    get_group_matches,
    get_groups,
    get_handicap_odds_for_match,
    get_match_probabilities_for_group,
    get_model_probabilities_for_match,
    get_odds_for_match,
    get_remaining_matches,
    load_groups,
    load_match_probabilities,
    load_matches,
    load_odds,
    validate_tournament_data,
)
from display import format_edge, format_ev, format_probability, localize_risk, outcome_label
from manual_input import build_manual_odds_record, find_group_for_teams
from providers.errors import ProviderError
from report.generator import generate_match_report
from services.live_data_service import get_odds_data
from tournament.scenario import analyze_match_scenarios, calculate_qualification_swing


st.set_page_config(page_title="世界杯投注分析助手", layout="wide")
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.4rem; }
    h1 { font-size: 1.8rem !important; }
    h2, h3 { margin-top: .75rem !important; }
    div[data-testid="stMetric"] { padding: .25rem .4rem; }
    div[data-testid="stAlert"] { padding: .55rem .7rem; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("世界杯投注分析助手")
st.caption("用于辅助分析世界杯小组赛赔率、EV 与出线情景，不构成投注建议。")
st.divider()


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    groups_df = load_groups()
    matches_df = load_matches()
    probabilities_df = load_match_probabilities()
    odds_df = load_odds()
    validate_tournament_data(groups_df, matches_df, probabilities_df, odds_df)
    return groups_df, matches_df, probabilities_df, odds_df


def format_standings(table: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(table).rename(
        columns={
            "team": "球队",
            "played": "场次",
            "wins": "胜",
            "draws": "平",
            "losses": "负",
            "goals_for": "进球",
            "goals_against": "失球",
            "goal_difference": "净胜球",
            "points": "积分",
        }
    )


def format_qualification_probabilities(probabilities: dict) -> pd.DataFrame:
    df = pd.DataFrame.from_dict(probabilities, orient="index").reset_index(names="球队")
    return pd.DataFrame(
        {
            "球队": df["球队"],
            "小组第1": df["finish_1st"].map(format_probability),
            "前二概率": df["top_2"].map(format_probability),
            "小组第3": df["finish_3rd"].map(format_probability),
            "小组第4": df["finish_4th"].map(format_probability),
        }
    )


def format_swing_table(swing: dict, analysis: dict) -> pd.DataFrame:
    df = pd.DataFrame.from_dict(swing, orient="index").reset_index(names="球队")
    return pd.DataFrame(
        {
            "球队": df["球队"],
            "赢球后前二概率": df["top_2_if_win"].map(format_probability),
            "打平后前二概率": df["top_2_if_draw"].map(format_probability),
            "输球后前二概率": df["top_2_if_loss"].map(format_probability),
            "赢球相对平局提升": df["win_vs_draw_swing"].map(format_edge),
            "平局相对输球提升": df["draw_vs_loss_swing"].map(format_edge),
            "争胜动机": df["球队"].map(lambda team: motivation_for_team(analysis, team, "win_motivation")),
            "保平/不败动机": df["球队"].map(lambda team: motivation_for_team(analysis, team, "avoid_loss_motivation")),
        }
    )


def motivation_for_team(analysis: dict, team: str, field: str) -> str:
    for side in ("home", "away"):
        if analysis["motivation"][side]["team"] == team:
            return analysis["motivation"][side][field]
    return ""


def normalize_probabilities(probabilities: dict) -> dict:
    total = sum(probabilities.values())
    return {key: value / total for key, value in probabilities.items()}


def market_result_label(outcome: str, home_team: str, away_team: str, handicap: int | None, market_type: str) -> str:
    if market_type == "handicap":
        return format_handicap_result_label(home_team, away_team, int(handicap), outcome)
    return outcome_label(outcome, home_team, away_team)


def market_interpretation(best_row: dict, edge_rows: list[dict], market_type: str) -> str:
    positive_count = sum(1 for row in edge_rows if row["ev"] > 0)
    if positive_count:
        value_sentence = f"最高 EV 是 {best_row['label']}，当前共有 {positive_count} 个正 EV 选项。"
    else:
        value_sentence = f"最高 EV 是 {best_row['label']}，但三项均未达到正 EV。"

    diff = abs(best_row["model_prob"] - best_row["market_prob"])
    if diff <= 0.02:
        price_sentence = "模型与市场对最高 EV 选项定价接近。"
    elif best_row["model_prob"] > best_row["market_prob"]:
        price_sentence = "模型概率高于市场隐含概率。"
    else:
        price_sentence = "模型概率低于市场隐含概率，赔率偏贵。"

    if market_type == "handicap":
        return f"{value_sentence} {price_sentence} 让球胜平负是调整后赛果，穿盘逻辑需结合比分区间。"
    return f"{value_sentence} {price_sentence}"


def find_provider_odds(provider_rows: list[dict], match_id: str, home_team: str, away_team: str) -> dict | None:
    for row in provider_rows:
        if row.get("match_id") == match_id:
            return row
    for row in provider_rows:
        if row.get("home") == home_team and row.get("away") == away_team:
            return row
    return None


def probability_preset_values(name: str, market_type: str) -> dict:
    if name == "均衡 33/34/33":
        return {"home": 0.33, "draw": 0.34, "away": 0.33}
    if name == "客队优势":
        return {"home": 0.22, "draw": 0.28, "away": 0.50}
    if name == "让球保守盘":
        return {"home": 0.28, "draw": 0.34, "away": 0.38}
    if name == "自定义" and market_type == "handicap":
        return {"home": 0.40, "draw": 0.30, "away": 0.30}
    return {"home": 0.50, "draw": 0.28, "away": 0.22}


def build_market_only_analysis(match_label: str, edge_rows: list[dict], market_type: str) -> dict:
    best = max(edge_rows, key=lambda row: row["ev"])
    positive_rows = [row for row in edge_rows if row["ev"] > 0]
    all_negative = not positive_rows
    if all_negative:
        value_summary = "当前三项赛果均未显示正期望收益，赔率层面暂不构成明显入场点。"
        value_short = "当前没有明显正 EV，赔率层面以观望为主。"
    else:
        value_summary = (
            f"{best['label']} 期望收益（EV）为 {format_ev(best['ev'], show_positive_sign=True)}，"
            f"概率差为 {format_edge(best['edge'])}。"
        )
        value_short = f"{best['label']} EV 最高，为 {format_ev(best['ev'], show_positive_sign=True)}。"
    market_context = (
        "当前市场为让球胜平负，判断对象是让球后的赛果。"
        if market_type == "handicap"
        else "当前市场为普通胜平负，直接对应真实比赛赛果。"
    )
    risk_summary = "当前未匹配本地小组情景，主要风险来自模型概率、临场阵容和赔率变化。"
    final = f"{value_summary} {risk_summary}"
    return {
        "market_context_summary": market_context,
        "core_summary": f"{match_label}：{final}",
        "value_summary": value_summary,
        "motivation_summary": "暂无本地出线情景数据。",
        "risk_summary": risk_summary,
        "final_view": final,
        "ui_summary": {
            "value": value_short,
            "motivation": "暂无本地出线情景，仅分析赔率与模型概率。",
            "risk": risk_summary,
            "final": "当前为市场-only 判断，需以出票时刻赔率为准。",
        },
        "key_flags": [],
        "best_value": {
            "outcome": best["label"],
            "ev": best["ev"],
            "edge": best["edge"],
            "risk": localize_risk(best["risk"]),
            **({"type": "best_relative_option"} if all_negative else {}),
        },
        "motivation": {},
    }


def market_only_signal(row: dict) -> str:
    diff = row["model_prob"] - row["market_prob"]
    if row["ev"] > 0 and diff > 0.05:
        return "正 EV；模型高于市场"
    if row["ev"] > 0:
        return "正 EV，需结合临场信息"
    if abs(diff) <= 0.02:
        return "市场充分定价"
    if diff < -0.05:
        return "模型低于市场"
    return "需结合临场信息"


try:
    groups_df, matches_df, probabilities_df, odds_df = load_data()
except ValueError as error:
    st.error(f"数据校验失败：请检查 CSV 文件。{error}")
    st.stop()

st.subheader("比赛与市场选择")
data_source_options = ["本地 CSV", "中国体彩实时数据（实验）", "手动输入赔率"]
data_source_display = st.selectbox("数据源", data_source_options, key="data_source")
manual_mode = data_source_display == "手动输入赔率"
provider_name = "sporttery" if data_source_display == "中国体彩实时数据（实验）" else "csv"
data_status_container = st.container()

if manual_mode:
    # 增加手动模式子模式选择
    manual_sub_mode = st.radio("手动模式", ["选择本地场次", "自定义比赛"], index=0, horizontal=True)
    
    # 市场类型选择器（通用）
    market_display = st.selectbox("市场类型", ["普通胜平负", "让球胜平负"])
    market_type = "handicap" if market_display == "让球胜平负" else "normal"

    if manual_sub_mode == "选择本地场次":
        # 1. 选择小组
        selected_group_manual = st.selectbox("小组", get_groups(groups_df), key="manual_group_select")
        
        # 2. 获取该小组未完赛的比赛
        from manual_input import get_scheduled_matches_for_group
        scheduled_matches = get_scheduled_matches_for_group(matches_df, selected_group_manual)
        
        if not scheduled_matches:
            st.warning("该小组暂无未赛场次。")
            st.stop()
        else:
            match_options = {
                f"{row['match_id']} | {row['home']} vs {row['away']}": row
                for row in scheduled_matches
            }
            selected_label = st.selectbox("比赛", list(match_options), key="manual_match_select")
            selected_row = match_options[selected_label]
            
            group = selected_group_manual
            match_id = selected_row["match_id"]
            match_code = match_id
            home_team = selected_row["home"]
            away_team = selected_row["away"]
            league = "世界杯"
            kickoff_time = ""
            supports_single = False
            
            st.success("已绑定本地场次，可同时显示赔率分析与出线情景。")
            st.caption(f"当前场次：{match_id} | {home_team} vs {away_team}")
    else:  # 自定义比赛
        info_cols = st.columns([1.2, 1.1, 1.1, 1.0])
        match_code = info_cols[0].text_input("比赛编号", value="手动001")
        league = info_cols[1].text_input("赛事", value="世界杯")
        kickoff_time = info_cols[2].text_input("开赛时间", value="")
        supports_single = info_cols[3].checkbox("是否单关", value=False)

        st.caption("手动比赛信息")
        team_cols = st.columns(2)
        home_team = team_cols[0].text_input("主队", value="美国")
        away_team = team_cols[1].text_input("客队", value="澳大利亚")
        match_id = match_code

        group = find_group_for_teams(groups_df, home_team, away_team)
        if group:
            st.success(f"已匹配本地小组：{group}组，可显示出线情景。")
        else:
            st.info("当前自定义比赛未匹配本地小组数据，因此仅显示赔率市场分析。")

    # 默认赔率预填逻辑
    if manual_sub_mode == "选择本地场次":
        from data_loader import get_odds_for_match, get_handicap_odds_for_match
        local_normal_odds = get_odds_for_match(odds_df, match_id)
        local_handicap_odds = get_handicap_odds_for_match(odds_df, match_id)
        
        if local_normal_odds:
            default_normal_home = local_normal_odds["home"]
            default_normal_draw = local_normal_odds["draw"]
            default_normal_away = local_normal_odds["away"]
        else:
            default_normal_home = 2.00
            default_normal_draw = 3.20
            default_normal_away = 3.50
            
        if local_handicap_odds:
            default_handicap_val = local_handicap_odds["handicap"]
            default_handicap_home = local_handicap_odds["handicap_home_odds"]
            default_handicap_draw = local_handicap_odds["handicap_draw_odds"]
            default_handicap_away = local_handicap_odds["handicap_away_odds"]
        else:
            default_handicap_val = 0
            default_handicap_home = 2.00
            default_handicap_draw = 3.20
            default_handicap_away = 3.50
    else:
        # 自定义比赛
        default_normal_home = 1.47
        default_normal_draw = 3.70
        default_normal_away = 5.60
        default_handicap_val = -1
        default_handicap_home = 2.56
        default_handicap_draw = 3.30
        default_handicap_away = 2.30

    st.subheader("手动录入赔率")
    st.caption("普通胜平负")
    normal_cols = st.columns(3)
    normal_home_odds = normal_cols[0].number_input(
        "主胜赔率", min_value=1.01, value=default_normal_home, step=0.05, key=f"{match_id}_{manual_sub_mode}_normal_home"
    )
    normal_draw_odds = normal_cols[1].number_input(
        "平局赔率", min_value=1.01, value=default_normal_draw, step=0.05, key=f"{match_id}_{manual_sub_mode}_normal_draw"
    )
    normal_away_odds = normal_cols[2].number_input(
        "主负赔率", min_value=1.01, value=default_normal_away, step=0.05, key=f"{match_id}_{manual_sub_mode}_normal_away"
    )

    st.caption("让球胜平负")
    handicap_cols = st.columns(4)
    handicap_value = handicap_cols[0].number_input(
        "让球", value=int(default_handicap_val), step=1, key=f"{match_id}_{manual_sub_mode}_handicap_val"
    )
    handicap_home_odds = handicap_cols[1].number_input(
        "让胜赔率", min_value=1.01, value=default_handicap_home, step=0.05, key=f"{match_id}_{manual_sub_mode}_handicap_home"
    )
    handicap_draw_odds = handicap_cols[2].number_input(
        "让平赔率", min_value=1.01, value=default_handicap_draw, step=0.05, key=f"{match_id}_{manual_sub_mode}_handicap_draw"
    )
    handicap_away_odds = handicap_cols[3].number_input(
        "让负赔率", min_value=1.01, value=default_handicap_away, step=0.05, key=f"{match_id}_{manual_sub_mode}_handicap_away"
    )

    manual_record = build_manual_odds_record(
        match_code=match_code,
        league=league,
        kickoff_time=kickoff_time,
        home_team=home_team,
        away_team=away_team,
        normal_home_odds=normal_home_odds,
        normal_draw_odds=normal_draw_odds,
        normal_away_odds=normal_away_odds,
        handicap=int(handicap_value),
        handicap_home_odds=handicap_home_odds,
        handicap_draw_odds=handicap_draw_odds,
        handicap_away_odds=handicap_away_odds,
        match_id=match_id,
    )
    if market_type == "handicap":
        odds_defaults = {
            "home": manual_record["handicap"]["handicap_home_odds"],
            "draw": manual_record["handicap"]["handicap_draw_odds"],
            "away": manual_record["handicap"]["handicap_away_odds"],
        }
        st.caption(f"当前分析市场：让球胜平负（{format_handicap_line(home_team, int(handicap_value))}）")
    else:
        odds_defaults = {
            "home": manual_record["normal"]["home_odds"],
            "draw": manual_record["normal"]["draw_odds"],
            "away": manual_record["normal"]["away_odds"],
        }
        st.caption("当前分析市场：普通胜平负")

    core_container = st.container()
    with st.expander("模型概率输入", expanded=False):
        if manual_sub_mode == "选择本地场次":
            preset_options = ["本地 CSV 概率", "均衡 33/34/33", "主队优势", "客队优势", "让球保守盘", "自定义"]
        else:
            preset_options = ["均衡 33/34/33", "主队优势", "客队优势", "让球保守盘", "自定义"]

        probability_preset = st.selectbox(
            "概率预设",
            preset_options,
            key=f"{match_id}_{manual_sub_mode}_prob_preset"
        )

        if probability_preset == "本地 CSV 概率":
            from data_loader import get_model_probabilities_for_match
            prob_val = get_model_probabilities_for_match(probabilities_df, match_id, market_type)
            if prob_val:
                probability_defaults = {
                    "home": prob_val["home"],
                    "draw": prob_val["draw"],
                    "away": prob_val["away"]
                }
            else:
                if market_type == "handicap":
                    probability_defaults = {"home": 0.40, "draw": 0.30, "away": 0.30}
                else:
                    probability_defaults = {"home": 0.50, "draw": 0.28, "away": 0.22}
        else:
            probability_defaults = probability_preset_values(probability_preset, market_type)

        probability_labels = (
            ("模型让胜概率", "模型让平概率", "模型让负概率")
            if market_type == "handicap"
            else ("模型主胜概率", "模型平局概率", "模型主负概率")
        )
        prob_cols = st.columns(3)
        model_home = prob_cols[0].number_input(
            probability_labels[0],
            min_value=0.0,
            max_value=1.0,
            value=probability_defaults["home"],
            step=0.01,
            key=f"{market_type}_{probability_preset}_{match_id}_{manual_sub_mode}_manual_model_home",
        )
        model_draw = prob_cols[1].number_input(
            probability_labels[1],
            min_value=0.0,
            max_value=1.0,
            value=probability_defaults["draw"],
            step=0.01,
            key=f"{market_type}_{probability_preset}_{match_id}_{manual_sub_mode}_manual_model_draw",
        )
        model_away = prob_cols[2].number_input(
            probability_labels[2],
            min_value=0.0,
            max_value=1.0,
            value=probability_defaults["away"],
            step=0.01,
            key=f"{market_type}_{probability_preset}_{match_id}_{manual_sub_mode}_manual_model_away",
        )
        odds = odds_defaults
        model_probs = {"home": model_home, "draw": model_draw, "away": model_away}
        if abs(sum(model_probs.values()) - 1.0) > 0.001:
            st.warning("模型概率之和不等于 100%，系统已在内部归一化后计算。")
            model_probs = normalize_probabilities(model_probs)
        if model_probs != probability_defaults:
            st.caption("当前概率：自定义")
else:
    selection_cols = st.columns([0.8, 1.8, 1.3, 1.2])
    group = selection_cols[0].selectbox("小组", get_groups(groups_df))
    group_matches = get_group_matches(matches_df, group)
    scheduled_matches = group_matches.loc[group_matches["status"] == "scheduled"].copy()
    match_options = {
        f"{row.match_id} | {row.home} vs {row.away}": row.match_id
        for row in scheduled_matches.itertuples(index=False)
    }
    selected_label = selection_cols[1].selectbox("比赛", list(match_options))
    market_display = selection_cols[2].selectbox("市场类型", ["普通胜平负", "让球胜平负"])
    market_type = "handicap" if market_display == "让球胜平负" else "normal"
    summary_container = selection_cols[3].container()

    match_id = match_options[selected_label]
    selected_row = scheduled_matches.loc[scheduled_matches["match_id"] == match_id].iloc[0]
    home_team = selected_row["home"]
    away_team = selected_row["away"]
    supports_single = None

    provider_warning = None
    try:
        odds_data_result = get_odds_data(provider_name)
    except ProviderError as error:
        odds_data_result = get_odds_data("csv")
        provider_warning = f"实时数据暂不可用，已回退到本地 CSV。{error}"

    provider_odds = find_provider_odds(odds_data_result["data"], match_id, home_team, away_team)
    if provider_warning:
        data_status_container.warning(provider_warning)
    elif odds_data_result.get("warning"):
        data_status_container.warning(odds_data_result["warning"])
    elif provider_name == "sporttery":
        last_update = provider_odds.get("last_update") if provider_odds else None
        data_status_container.caption(f"实时数据更新时间：{last_update or '未提供'}")

    handicap_odds_missing = False
    handicap_probabilities_missing = False
    handicap_value = None
    if market_type == "handicap":
        handicap_odds = None
        if provider_name == "sporttery" and provider_odds and provider_odds.get("handicap", {}).get("available"):
            handicap_odds = provider_odds["handicap"]
        if handicap_odds is None:
            handicap_odds = get_handicap_odds_for_match(odds_df, match_id)
        if handicap_odds:
            handicap_value = handicap_odds["handicap"]
            odds_defaults = {
                "home": handicap_odds["handicap_home_odds"],
                "draw": handicap_odds["handicap_draw_odds"],
                "away": handicap_odds["handicap_away_odds"],
            }
        else:
            handicap_odds_missing = True
            handicap_value = 0
            odds_defaults = {"home": 2.00, "draw": 3.20, "away": 3.50}

        probability_defaults = get_model_probabilities_for_match(probabilities_df, match_id, "handicap")
        if probability_defaults is None:
            handicap_probabilities_missing = True
            probability_defaults = {"home": 0.33, "draw": 0.34, "away": 0.33}
    else:
        live_normal_odds = provider_odds.get("normal") if provider_name == "sporttery" and provider_odds else None
        if live_normal_odds and live_normal_odds.get("available"):
            odds_defaults = {
                "home": live_normal_odds["home_odds"],
                "draw": live_normal_odds["draw_odds"],
                "away": live_normal_odds["away_odds"],
            }
        else:
            odds_defaults = get_odds_for_match(odds_df, match_id) or {"home": 2.00, "draw": 3.20, "away": 3.50}
        probability_defaults = get_model_probabilities_for_match(probabilities_df, match_id, "normal")

    core_container = st.container()

    with st.expander("赔率与模型输入", expanded=False):
        if market_type == "handicap":
            if handicap_odds_missing:
                st.warning("当前比赛没有让球赔率数据，请手动输入。")
            if handicap_probabilities_missing:
                st.warning("当前比赛没有让球模型概率，请手动输入。")
            handicap_value = st.number_input("让球", value=int(handicap_value), step=1)
            st.caption(f"让球：{format_handicap_line(home_team, int(handicap_value))}")

        odds_cols = st.columns(3)
        odds_labels = ("让胜赔率", "让平赔率", "让负赔率") if market_type == "handicap" else ("主胜赔率", "平局赔率", "客胜赔率")
        home_odds = odds_cols[0].number_input(
            odds_labels[0], min_value=1.01, value=odds_defaults["home"], step=0.05, key=f"{match_id}_{market_type}_home_odds"
        )
        draw_odds = odds_cols[1].number_input(
            odds_labels[1], min_value=1.01, value=odds_defaults["draw"], step=0.05, key=f"{match_id}_{market_type}_draw_odds"
        )
        away_odds = odds_cols[2].number_input(
            odds_labels[2], min_value=1.01, value=odds_defaults["away"], step=0.05, key=f"{match_id}_{market_type}_away_odds"
        )

        prob_cols = st.columns(3)
        probability_labels = (
            ("模型让胜概率", "模型让平概率", "模型让负概率")
            if market_type == "handicap"
            else ("模型主胜概率", "模型平局概率", "模型客胜概率")
        )
        model_home = prob_cols[0].number_input(
            probability_labels[0], min_value=0.0, max_value=1.0, value=probability_defaults["home"], step=0.01, key=f"{match_id}_{market_type}_model_home"
        )
        model_draw = prob_cols[1].number_input(
            probability_labels[1], min_value=0.0, max_value=1.0, value=probability_defaults["draw"], step=0.01, key=f"{match_id}_{market_type}_model_draw"
        )
        model_away = prob_cols[2].number_input(
            probability_labels[2], min_value=0.0, max_value=1.0, value=probability_defaults["away"], step=0.01, key=f"{match_id}_{market_type}_model_away"
        )

        odds = {"home": home_odds, "draw": draw_odds, "away": away_odds}
        model_probs = {"home": model_home, "draw": model_draw, "away": model_away}
        if abs(sum(model_probs.values()) - 1.0) > 0.001:
            st.warning("模型概率之和不等于 100%，系统已在内部归一化后计算。")
            model_probs = normalize_probabilities(model_probs)

    with summary_container:
        if market_type == "handicap":
            st.caption(f"让球：{format_handicap_line(home_team, int(handicap_value))}")
        else:
            st.caption("市场：普通胜平负")

market_probs = no_vig_probabilities(odds["home"], odds["draw"], odds["away"])
edge_rows = []
outcome_specs = (
    [("handicap_home", "home"), ("handicap_draw", "draw"), ("handicap_away", "away")]
    if market_type == "handicap"
    else [("home", "home"), ("draw", "draw"), ("away", "away")]
)
for outcome, probability_key in outcome_specs:
    edge = calculate_edge(model_probs[probability_key], market_probs[probability_key])
    ev = calculate_ev(model_probs[probability_key], odds[probability_key])
    risk = classify_risk(edge, ev)
    edge_rows.append(
        {
            "outcome": outcome,
            "label": market_result_label(outcome, home_team, away_team, handicap_value, market_type),
            "market_prob": market_probs[probability_key],
            "model_prob": model_probs[probability_key],
            "edge": edge,
            "ev": ev,
            "risk": risk,
        }
    )

scenario_analysis = None
swing = None
if group:
    completed_matches = get_completed_matches(matches_df, group)
    remaining_matches = get_remaining_matches(matches_df, group)
    match_probabilities = get_match_probabilities_for_group(matches_df, probabilities_df, group)
    scenario_analysis = analyze_match_scenarios(
        completed_matches,
        {"home": home_team, "away": away_team},
        remaining_matches,
        match_probabilities,
        n_simulations=1000,
        seed=42,
    )
    swing = calculate_qualification_swing(scenario_analysis, home_team, away_team)
    analysis = build_match_analysis(
        match_label=f"{group}组 {match_id}: {home_team} vs {away_team}",
        home_team=home_team,
        away_team=away_team,
        market_rows=edge_rows,
        current_table=scenario_analysis["current_table"],
        qualification_swing=swing,
        scenario_analysis=scenario_analysis,
        market_type=market_type,
        handicap=int(handicap_value) if market_type == "handicap" else None,
    )
else:
    analysis = build_market_only_analysis(
        match_label=f"{match_id}: {home_team} vs {away_team}",
        edge_rows=edge_rows,
        market_type=market_type,
    )

best_row = max(edge_rows, key=lambda row: row["ev"])
best_market = max(market_probs, key=market_probs.get)
best_model = max(model_probs, key=model_probs.get)
best_market_outcome = f"handicap_{best_market}" if market_type == "handicap" else best_market
best_model_outcome = f"handicap_{best_model}" if market_type == "handicap" else best_model
best_market_label = market_result_label(best_market_outcome, home_team, away_team, handicap_value, market_type)
best_model_label = market_result_label(best_model_outcome, home_team, away_team, handicap_value, market_type)

with core_container:
    st.subheader("核心摘要")
    metric_cols = st.columns(4)
    metric_cols[0].metric("市场最看好", f"{best_market_label} {format_probability(market_probs[best_market])}")
    metric_cols[1].metric("模型最看好", f"{best_model_label} {format_probability(model_probs[best_model])}")
    metric_cols[2].metric("最高 EV", f"{best_row['label']} {format_ev(best_row['ev'], show_positive_sign=True)}")
    metric_cols[3].metric("综合判断", localize_risk(best_row["risk"]))

    summary_cols = st.columns(3)
    summary_cols[0].info(f"赔率结论\n\n{analysis['ui_summary']['value']}")
    summary_cols[1].info(f"出线动机\n\n{analysis['ui_summary']['motivation']}")
    summary_cols[2].warning(f"风险提醒\n\n{analysis['ui_summary']['risk']}")
    st.caption(f"综合观点：{analysis['ui_summary']['final']}")

analysis_df = pd.DataFrame(
    [
        {
            "赛果": row["label"],
            "市场概率": format_probability(row["market_prob"]),
            "模型概率": format_probability(row["model_prob"]),
            "概率差": format_edge(row["edge"]),
            "期望收益": format_ev(row["ev"]),
            "风险判断": localize_risk(row["risk"]),
            "信号解释": build_signal_explanation(row, analysis, home_team, away_team, market_type) if scenario_analysis else market_only_signal(row),
        }
        for row in edge_rows
    ]
)

tab_market, tab_scenario = st.tabs(["市场分析", "出线情景"])
with tab_market:
    market_cols = st.columns([1.2, 1])
    with market_cols[0]:
        st.subheader("市场赔率分析")
        st.table(analysis_df)
        st.write(f"综合风险判断：{localize_risk(best_row['risk'])}")
    with market_cols[1]:
        st.subheader("市场解释")
        st.info(analysis["market_context_summary"])
        st.write(market_interpretation(best_row, edge_rows, market_type))
        if manual_mode:
            st.caption("手动录入赔率不保证与实时体彩一致，需以出票时刻为准。")
        if market_type == "handicap":
            st.caption("让球市场分析的是让球后的赛果，不直接代表真实胜平负或出线动机。")

with tab_scenario:
    st.caption("以下情景基于真实比赛赛果，不使用让球后的赛果。")
    if scenario_analysis:
        scenario_cols = st.columns([1, 1.3])
        with scenario_cols[0]:
            st.subheader("当前小组积分榜")
            st.dataframe(format_standings(scenario_analysis["current_table"]), hide_index=True, use_container_width=True)
            st.subheader("出线概率变化")
            st.table(format_swing_table(swing, analysis))
        with scenario_cols[1]:
            st.subheader("小组出线情景分析")
            tabs = st.tabs(["主队赢球", "平局", "客队赢球"])
            scenario_configs = [
                ("home_win", f"主队赢球后积分榜：{scenario_analysis['scenarios']['home_win']['forced_result']}"),
                ("draw", f"平局后积分榜：{scenario_analysis['scenarios']['draw']['forced_result']}"),
                ("away_win", f"客队赢球后积分榜：{scenario_analysis['scenarios']['away_win']['forced_result']}"),
            ]
            for tab, (scenario_key, label) in zip(tabs, scenario_configs):
                scenario = scenario_analysis["scenarios"][scenario_key]
                with tab:
                    st.write(label)
                    st.dataframe(format_standings(scenario["table_after_result"]), hide_index=True, use_container_width=True)
                    st.dataframe(
                        format_qualification_probabilities(scenario["qualification_probabilities"]),
                        hide_index=True,
                        use_container_width=True,
                    )
    else:
        st.info("暂无本地出线情景数据。")
        if manual_mode:
            st.caption("当前手动比赛未匹配本地小组数据，因此仅显示赔率市场分析。")

report = generate_match_report(
    {
        "group": group,
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "odds": odds,
        "model_probabilities": model_probs,
        "scenario_analysis": scenario_analysis,
        "analysis": analysis if scenario_analysis else None,
        "market_type": market_type,
        "handicap": int(handicap_value) if market_type == "handicap" else None,
        "data_source": "manual" if manual_mode else provider_name,
        "supports_single": supports_single,
    }
)

st.subheader("中文比赛分析报告")
with st.expander("查看完整分析报告", expanded=False):
    st.text_area("报告", report, height=420)
