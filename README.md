# worldcup-betting-analyzer

Python MVP for analyzing World Cup group-stage betting markets.

The app combines decimal odds conversion, no-vig market probabilities, model probabilities, expected value, current group tables, scenario simulation, qualification swing analysis, and a structured Chinese match report. It is an analysis assistant only and does not guarantee betting outcomes.

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
