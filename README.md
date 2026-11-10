# Football Match Predictor

A football data platform for the Premier League, La Liga, Bundesliga, Serie A and Ligue 1. It predicts match outcomes and total goals and corners from each team's recent form, and it shows league tables back to 2005/06 and player stats (goals, assists, clean sheets) back to 2012/13. The system combines data cleaning, a PostgreSQL database, machine learning models, a FastAPI backend and a web interface.

**Live demo:** https://football-match-predictor.netlify.app

**API docs:** https://premier-league-predictor-138n.onrender.com/docs

The API runs on a free host that sleeps when idle, so the first request after a quiet period can take up to a minute.

## Table of Contents

- [Overview](#overview)
- [Technology Stack](#technology-stack)
- [Features](#features)
- [Data Pipeline](#data-pipeline)
- [Models and Results](#models-and-results)
- [Backend Core](#backend-core)
- [Frontend Application](#frontend-application)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Running It Locally](#running-it-locally)
- [Notes](#notes)
- [Limitations](#limitations)
- [Next Steps](#next-steps)

## Overview

The project turns 20 years of match results and 14 years of player stats into predictions and statistics that anyone can browse.

Highlights:

- **38,475 matches** from 2005/06 to 2026/27 (in progress), stored in PostgreSQL and refreshed automatically
- **Outcome model** (home win, draw, away win) at 49.3% accuracy on 3,873 unseen matches, compared with 43.2% for always picking the home team and 53.6% for Bet365 odds
- **Goals and corners models** that give the chance of going over each line, such as 2.5 goals
- **League tables** for any league and season, calculated from match results
- **About 72,000 player-season rows**, split by league, Champions League, Europa League and domestic cups
- **Time-based evaluation** with no leakage: models are trained on matches before July 2024 and tested only on later games

The system supports four views in the web app: a predictor, standings, player leaders, and player search with season-by-season careers.

## Technology Stack

**Backend**

- `FastAPI` and `Uvicorn`: web framework and server
- `PostgreSQL` on `Neon`: hosted relational database
- `psycopg2`: database driver, with parameterised queries
- `scikit-learn`: logistic regression and Poisson regression
- `joblib`: saved models

**Frontend**

- `HTML`, `CSS` and plain `JavaScript`, with no framework
- `fetch` with async and await for API calls
- `Netlify`: static hosting

**Data Processing**

- `pandas` and `NumPy`: cleaning and feature engineering
- `SciPy`: probability calculations
- `DuckDB`: reads the Transfermarkt player file

**Data Sources**

- `football-data.co.uk`: match results, shots, corners, cards and odds
- `Transfermarkt datasets` (dcaribou/transfermarkt-datasets): player appearances, goals, assists and minutes

**Infrastructure**

- `Neon`: PostgreSQL hosting
- `Render`: API hosting (free web service)
- `Netlify`: web app hosting
- `GitHub Actions`: scheduled data refresh every 6 hours

## Features

**Match prediction**

- Pick a league and two teams to get win, draw and loss chances
- Expected total goals and corners, with the chance of going over each line
- Predictions built from each team's last five matches

**Standings**

- League table for any of the five leagues and any season from 2005/06 to today
- Played, won, drawn, lost, goals for, goals against, goal difference and points

**Player stats**

- Leaders for goals, assists, clean sheets, games or minutes
- Filter by competition (league, Champions League, Europa League, cups) and season, or see all seasons
- Player search with a season-by-season career table
- An arrow on each season opens the split by competition

## Data Pipeline

Match data:

**1. Download (`download_data.py`)**

- Downloads one CSV per league per season from football-data.co.uk
- Stores every row untouched in the `raw_matches` table as JSON, so cleaning can change later without re-downloading

**2. Cleaning (`clean_data.py`, `cleaning.py`)**

- Converts types and removes empty rows (8 were found)
- Keeps result, half-time score, shots, corners, fouls, cards and Bet365 odds
- Builds a unique `match_id` from league, date, home team and away team

**3. Database loading (`create_tables.py`, `load_data.py`)**

- Creates the `raw_matches` and `matches` tables
- Loads with `INSERT ... ON CONFLICT DO UPDATE`, so reruns never create duplicates (tested: 452 existing matches re-upserted, the table stayed at 38,475 rows)

**4. Scheduled updates (`update_data.py`)**

- Run by a GitHub Actions workflow every 6 hours
- Re-downloads the current season and upserts it

**5. Feature engineering (`features.py`, `features_totals.py`)**

- Averages over each team's previous five matches: points, goals for and against, shots, shots on target, corners, days of rest
- Home-minus-away differences, and for totals, one team's attack combined with the other's defence
- Each match uses only games played before it, so there is no leakage

**6. Training and evaluation (`train_model.py`, `train_totals.py`, `evaluate.py`)**

- Trains on matches before July 2024, tests on August 2024 onward
- Compares models, and computes confidence intervals, per-league accuracy and calibration

Player data:

**7. Player stats (`build_player_stats.py`)**

- Reads the Transfermarkt DuckDB file (about 1.9 million player-match rows)
- Keeps the five leagues, Champions League, Europa League and domestic cups, for players who played in one of the five leagues that season
- Adds up games, minutes, goals, assists, cards and goalkeeper clean sheets per player, season, competition and club
- Loads the result into the `player_season_stats` table in PostgreSQL (about 72,000 rows)
- Run with no options for a preview that changes nothing, and with `--load` to write the table

## Models and Results

All models were trained on 33,204 matches before July 2024 and evaluated on 3,873 matches they never saw (August 2024 to November 2026). The split is by date, never random.

**Match outcome (home win, draw, away win)**

| Model | Accuracy (95% range) | Log loss |
|---|---|---|
| Always pick the home team | 43.2% (41.7 to 44.8) | 1.075 |
| Random forest | 49.2% | 1.023 |
| Gradient boosting | 48.9% | 1.024 |
| Logistic regression (used in the app) | 49.3% (47.7 to 50.9) | 1.018 |
| Bookmaker (Bet365 odds, margin removed) | 53.6% (52.1 to 55.2) | 0.970 |

- The model beats the naive baseline but trails the bookmaker by 4.3 points (95% range 3.0 to 5.6)
- Bookmakers see lineups, injuries and the betting market, and this model only sees recent results
- The three model types finish within half a point of each other, so the simplest one was chosen
- Accuracy is similar across leagues (47.8% to 51.2%), and the differences are not statistically meaningful
- Home-win probabilities run 1.5 to 3.5 points too high in every bucket
- The model almost never picks a draw as its top choice, which is typical for football models

**Total goals and corners**

- Poisson regression predicts the expected total, which is converted into the chance of going over each line
- Average error: goals 1.323 against a baseline of 1.344, corners 2.733 against 2.772
- Log loss beats the baseline on every line, but only by a small margin, so recent form says a little about totals and not much more

This project is not betting advice, and the models do not beat bookmaker odds.

## Backend Core

`main.py` and `players.py` form a FastAPI service over the database and the prediction code. Interactive documentation is at `/docs`.

| Endpoint | What it returns |
|---|---|
| `GET /leagues` | The five league names |
| `GET /teams?league=Premier League` | Teams that have played in that league recently |
| `GET /predict?home=Arsenal&away=Chelsea` | Outcome probabilities plus expected goals and corners |
| `GET /seasons?league=Premier League` | Seasons available for a league, such as `2324` |
| `GET /standings?league=Premier League&season=2324` | The league table for a season |
| `GET /top-players?stat=goals&competition=GB1&season=2324` | Leaders for goals, assists, clean sheets, games or minutes. `competition` and `season` can be `all` |
| `GET /player-search?q=haaland` | Players whose name contains the text |
| `GET /player/{player_id}` | One player's stats for every season, split by competition and club |
| `GET /player-seasons` and `GET /player-competitions` | Values for the dropdowns |

Example response from `/predict` (the numbers are illustrative; probabilities are percentages):

```json
{
  "home": "Arsenal",
  "away": "Chelsea",
  "outcome": { "home_win": 48.2, "draw": 26.1, "away_win": 25.7 },
  "totals": {
    "goals": { "expected": 2.74, "over": { "1.5": 83.1, "2.5": 52.0, "3.5": 26.3 } },
    "corners": { "expected": 10.21, "over": { "8.5": 74.5, "9.5": 59.9, "10.5": 44.0, "11.5": 29.8 } }
  }
}
```

Errors come back as `{"detail": "..."}`. A team with fewer than five recent matches returns status 400, and an unknown league returns 404.

**Key modules**

- `db.py`: all database access, with parameterised queries and a pooled connection for the API
- `predict.py`: rebuilds a team's current form from the database and returns predictions
- `players.py`: the player stats routes, added to the app with `app.include_router`

## Frontend Application

A static site in `frontend/` built with plain HTML, CSS and JavaScript.

**Pages**

- Home (`index.html`): the results, how it works and what it can't do
- Predictor (`predict.html`): choose a league and two teams
- Standings (`standings.html`): choose a league and a season
- Players (`players.html`): leaders, player search and career tables

**Behaviour**

- Shows the API's error messages, and explains the delay when the free host is waking up
- Ignores slow responses that have been replaced by a newer choice
- Shared code is in `common.js`, and each page has its own script
- Works on phones, and respects reduced-motion settings

## Deployment

| Part | Where it runs |
|---|---|
| Database | `Neon` (hosted PostgreSQL) |
| API | `Render` (free web service) |
| Web app | `Netlify` (static hosting) |
| Data refresh | `GitHub Actions`, every 6 hours |

- Connection strings are never committed. Locally they live in `api.env` (gitignored), and in production they are set as environment variables
- The API accepts browser requests only from the web app's address (CORS allowlist), plus localhost for development

## Project Structure

```
football-predictor/
├── main.py                    # FastAPI service: predictions, standings
├── players.py                 # FastAPI routes for player stats
├── db.py                      # All database access
├── predict.py                 # Builds live features and returns predictions
├── cleaning.py                # Cleaning rules shared by the loader and the update job
├── update_data.py             # Re-downloads the current season (GitHub Actions)
├── download_data.py           # One-time: download 20 years of files
├── clean_data.py              # One-time: clean the raw table
├── create_tables.py           # One-time: create the PostgreSQL tables
├── load_data.py               # One-time: bulk load into PostgreSQL
├── build_player_stats.py      # One-time: build the player stats table
├── features.py                # Outcome features
├── features_totals.py         # Goals and corners features
├── train_model.py             # Train and compare outcome models
├── train_totals.py            # Train and evaluate goals and corners models
├── evaluate.py                # Confidence intervals, per-league accuracy, calibration
├── models/                    # Saved models
├── frontend/
│   ├── index.html             # Landing page
│   ├── predict.html           # Predictor page
│   ├── standings.html         # League tables
│   ├── players.html           # Player leaders, search and careers
│   ├── common.js              # Shared API calls and helpers
│   ├── predictor.js           # Predictor page logic
│   ├── standings.js           # Standings page logic
│   ├── players.js             # Players page logic
│   └── style.css              # Shared styles
├── .github/workflows/         # Scheduled data update
├── app.py, pages/             # Original Streamlit version, replaced by the web app
├── requirements.txt           # Python dependencies for the API
└── requirements-update.txt    # Dependencies for the scheduled update
```

## Running It Locally

1. Install dependencies: `pip install -r requirements.txt`
2. Create a hosted PostgreSQL database and put its connection strings in `api.env`:
   ```
   DATABASE_URL=postgresql://...
   DATABASE_URL_POOLED=postgresql://...
   ```
3. Build the match data and models, in order:
   ```
   python download_data.py
   python clean_data.py
   python create_tables.py
   python load_data.py
   python features.py
   python features_totals.py
   python train_model.py
   python train_totals.py
   ```
4. For player stats, download the DuckDB file from the Transfermarkt datasets project into `data/`, run `pip install duckdb`, then `python build_player_stats.py` to preview and `python build_player_stats.py --load` to write the table
5. Start the API: `uvicorn main:app --reload --port 8001`, then open `http://127.0.0.1:8001/docs`
6. To run the web app against your local API, set `API_URL` at the top of `frontend/common.js` to `http://127.0.0.1:8001`, add the local server's address to the CORS list in `main.py`, and open `frontend/index.html` with a local server such as VS Code Live Server

## Notes

- **Time-based evaluation.** Football results are a time series, so a random split would let the model learn from the future. The model is trained on older seasons and tested on newer ones
- **No leakage in the features.** Each team's matches are sorted by date and the rolling average is shifted by one row, so a match never contributes to its own features. Features are blanked when a team's previous match was more than 150 days ago, and each team's first five matches are dropped. The live prediction code recomputes the same features and was checked against the training features
- **Raw layer and cleaned layer.** Every downloaded row is kept untouched in `raw_matches`, so the cleaning logic can change without re-downloading
- **Standings are calculated, not stored.** The table is a SQL query over `matches`, so it updates itself when new results arrive. Ties are ordered by goal difference, then goals scored, and points deductions are not included
- **Player stats are pre-aggregated.** About 1.9 million player-match rows become about 72,000 rows, so the API answers quickly and the database stays small
- **An API between the models and the web page.** A page in the browser can't run Python or reach the database, so FastAPI wraps the prediction code and returns JSON
- **Simplest model that works.** Logistic regression performed as well as random forest and gradient boosting, and it is the easiest to explain
- **Poisson regression for totals.** Goals and corners are small counts, so a Poisson model fits, and its expected value is converted into the chance of going over a line
- **Bookmaker odds are a benchmark, not an input.** Using them as features would mostly copy the bookmaker
- **Security.** Queries are parameterised. The one query that chooses a column (`/top-players`) accepts only names from a fixed list. League names are checked against a fixed list. Secrets are kept out of the repository. Not done yet: rate limiting and an automated dependency audit
- Match data comes from football-data.co.uk, and player data comes from the Transfermarkt datasets project, which is built from Transfermarkt

## Limitations

- The model sees only recent results, with no lineups, injuries, transfers or match context, which is the main reason it trails the bookmaker
- It almost never predicts draws, and its home-win probabilities are slightly high
- Team names come from a single source, so a second data source would need a team-name mapping table
- Player stats cover 2012/13 to 2025/26. The current season is not included, and the source does not have the EFL Cup or the Coupe de France
- A clean sheet counts when a goalkeeper played 90 minutes and his team conceded no goals, so it is an approximation. Assists and clean sheets may differ from other sites
- Player search is accent-sensitive, so a player is found by "Ødegaard", not "Odegaard"
- On free hosting, the first request after a quiet period can take up to a minute

## Next Steps

- Current-season player stats from a free API, refreshed on a schedule (goals are available for free, but assists are often missing)
- Elo-style team ratings and recency-weighted form, evaluated with the same time-based split
- Recalibrate the home-win probabilities, or train on more recent seasons
- Rate limiting and a dependency audit for the API
