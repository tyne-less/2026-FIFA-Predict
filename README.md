# worldcup-betting-analyzer

Python MVP for analyzing World Cup group-stage betting markets.

The app combines decimal odds conversion, no-vig market probabilities, model probabilities, expected value, current group tables, scenario simulation, qualification swing analysis, and a structured Chinese match report. It is an analysis assistant only and does not guarantee betting outcomes.

## 数据与赔率说明 (v0.9)

1. **A–L 小组示例数据**：目前 `data/*.csv` 已经补全了 2026 世界杯 A–L 共 12 个小组（48 支球队，每个小组 6 场比赛，共 72 场比赛）的示例赛程、已完赛比分及后续赛程。
2. **赔率与模型概率为示例数据**：
   - `data/odds.csv` 中的赔率和 `data/match_probabilities.csv` 中的模型概率均为**合理估算的示例数据 (sample data)**，并不代表中国体育彩票官方实时赔率，亦不代表真实赛事模型的真实概率。
3. **真实赔率分析方式**：
   - 若要对真实比赛进行精确分析，建议在 Web 界面中的数据源下拉菜单中选择 **“手动输入赔率”** 模式，并手动录入体育彩票官方或小程序上的临场实时赔率与模型概率。
4. **出线情景模拟依据**：
   - “出线情景分析”模块的计算结果是基于本地 `data/matches.csv` 中记录的已完赛比分、未完赛赛程，并结合 `data/match_probabilities.csv` 中的示例模型概率，通过 1000 次蒙特卡洛模拟计算得出的。

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run tests

```bash
pytest
```

## Run Streamlit

```bash
PYTHONPATH=src streamlit run src/app/streamlit_app.py
```

## Data-driven usage

Streamlit loads tournament data from CSV files in `data/`. The user selects a group and scheduled match, then the app automatically loads completed matches, remaining matches, model probabilities, and any available odds for that match. Odds and model probabilities remain editable in the UI.

## CSV schema

`data/groups.csv`

```csv
group,team
F,Netherlands
F,Japan
F,Sweden
F,Tunisia
```

`data/matches.csv`

```csv
match_id,group,home,away,home_score,away_score,status
F1,F,Netherlands,Japan,2,2,completed
F4,F,Tunisia,Japan,,,scheduled
```

`status` must be `completed` or `scheduled`. Completed matches require scores.

`data/match_probabilities.csv`

```csv
match_id,p_home,p_draw,p_away,p_handicap_home,p_handicap_draw,p_handicap_away
F4,0.22,0.28,0.50,0.46,0.27,0.27
```

Each scheduled match must have a normal 1X2 probability row, and probabilities must sum to about 1.0. Handicap probabilities are optional; if one handicap probability is present, all three must be present and sum to about 1.0.

`data/odds.csv`

```csv
match_id,home_odds,draw_odds,away_odds,handicap,handicap_home_odds,handicap_draw_odds,handicap_away_odds
F4,4.50,3.40,1.85,1,1.75,3.60,3.95
```

Odds are optional per match, but any listed decimal odds must be greater than 1.0. Handicap values are integer goals applied to the home team, matching Chinese Sports Lottery style handicap 1X2.

## Add another group

1. Add the four group teams to `data/groups.csv`.
2. Add completed and scheduled fixtures to `data/matches.csv`.
3. Add one probability row for every scheduled fixture to `data/match_probabilities.csv`.
4. Add normal odds rows to `data/odds.csv` for matches where market odds are available.
5. Add optional handicap, handicap odds, and handicap probabilities when the handicap market is available.

## Group scenario analysis

The scenario module estimates how each possible match result changes group-stage qualification probabilities. It is especially useful from the second group-stage round onward, because team motivation changes depending on points, goal difference, and remaining fixtures.

For a selected match, it compares a home win, draw, and away win, then simulates the remaining group fixtures to estimate each team's chance of finishing 1st, top 2, 3rd, and 4th.

## Limitations

The simulator uses simple fixed scoreline samples and user-provided 1X2 probabilities. It does not model injuries, lineups, tactical changes, market movement, or tie-breakers beyond points, goal difference, and goals scored.
