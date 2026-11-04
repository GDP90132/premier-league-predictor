# Top-5 Leagues Match Predictor

A match prediction system for the Premier League, La Liga, Bundesliga, Serie A and Ligue 1. It predicts the outcome of a match (home win, draw, away win) and the total goals and corners, using each team's recent form. The pipeline downloads 20 years of results, stores them in PostgreSQL, refreshes itself on a schedule, and serves predictions through a Streamlit app.

Live app: LIVE_APP_URL

![Predictor page](docs/predictor.png)

## Results

All models were trained on matches before July 2024 (33,204 matches) and evaluated on 3,873 matches they never saw (August 2024 to November 2026). The split is by date, never random, so the model is never trained on games that happen after the ones it is tested on.

### Match outcome (home win / draw / away win)

| Model | Accuracy (95% range) | Log loss |
|---|---|---|
| Always pick the home team | 43.2% (41.7 to 44.8) | 1.075 |
| Random forest | 49.2% | 1.023 |
| Gradient boosting | 48.9% | 1.024 |
| **Logistic regression (used in the app)** | **49.3% (47.7 to 50.9)** | **1.018** |
| Bookmaker (Bet365 odds, margin removed) | 53.6% (52.1 to 55.2) | 0.970 |

The model clearly beats the naive baseline but trails the bookmaker by 4.3 points (95% range 3.0 to 5.6). That gap is expected: bookmakers see confirmed lineups, injuries and the betting market itself, and this model only sees recent results. The three model types finish within half a point of each other, which is inside the noise, so the simplest one was chosen.

Accuracy is similar across leagues (47.8% to 51.2%); with 659 to 857 test matches per league, those differences are not statistically meaningful.

The predicted home-win probabilities run 1.5 to 3.5 points higher than what actually happened in every probability bucket, so the model is slightly over-confident about home teams. A likely cause is that home advantage has declined since the older training seasons; this has not been tested.

The model almost never predicts a draw as its top pick. Draws are about a quarter of results but are rarely the single most likely outcome, which is typical for football models.

### Total goals and corners

Poisson regression predicts the expected total for each match, which is converted into the probability of going over each line. The baseline predicts the training-set average (or the historical over rate) for every match.

| Target | Baseline average error | Poisson regression | Gradient boosting |
|---|---|---|---|
| Total goals | 1.344 | 1.323 | 1.322 |
| Total corners | 2.772 | 2.733 | 2.732 |

Log loss on over/under lines (lower is better):

| Line | Baseline | Poisson regression |
|---|---|---|
| Goals over 1.5 | 0.5322 | 0.5278 |
| Goals over 2.5 | 0.6918 | 0.6834 |
| Goals over 3.5 | 0.6257 | 0.6174 |
| Corners over 8.5 | 0.6812 | 0.6748 |
| Corners over 9.5 | 0.6980 | 0.6910 |
| Corners over 10.5 | 0.6683 | 0.6602 |
| Corners over 11.5 | 0.5915 | 0.5816 |

Both models beat the baseline on every line, but the improvements are small. Recent form carries a modest amount of information about totals, and not much more.

This project is not betting advice, and the models do not beat bookmaker odds.

## How it works

```
football-data.co.uk CSVs
        |
   download + clean
        |
PostgreSQL: raw_matches (untouched rows) -> matches (cleaned, typed)
        |
   rolling features (last 5 matches, no leakage)
        |
   models: outcome (logistic regression), goals and corners (Poisson regression)
        |
   predict.py rebuilds a team's current form from the database
        |
   Streamlit app
```

A GitHub Actions job re-downloads the current season's files every 6 hours and upserts them into the database, so the data stays current without manual work. (Scheduled runs on GitHub can start late.)

## Design decisions

**Time-based evaluation.** Football results are a time series. Shuffling matches into a random train/test split would let the model learn from the future. The model is trained on older seasons and tested on newer ones.

**No leakage in the features.** Each match uses only games played before it. In pandas, each team's matches are sorted by date and the rolling average is shifted by one row, so a match never contributes to its own features. Features are blanked when a team's previous match was more than 150 days ago (promotion, relegation, or a long break), and each team's first five matches are dropped because there is no history. The live prediction code recomputes the same features from matches strictly before the prediction date, and this was checked against the training features (for example, Newcastle's last-5 points average was exactly 1.2 in both).

**Raw layer and cleaned layer.** Every downloaded row is stored untouched in `raw_matches` as JSON, so the cleaning logic can change later without re-downloading. The cleaned `matches` table has typed columns and a primary key.

**Idempotent loading.** Each match has a unique `match_id` built from the league code, date, home team and away team. Loads use `INSERT ... ON CONFLICT DO UPDATE`, so rerunning the pipeline never creates duplicates. This was tested by re-upserting 452 existing matches: the table stayed at 38,475 rows.

**PostgreSQL instead of a local file.** The scheduled update job, the app and any future API run in different places and need to share one database. A hosted PostgreSQL database (Neon) serves all of them. The app uses a pooled connection string and the setup and loading scripts use the direct one.

**One database module.** All database access goes through `db.py`. Queries use parameters, never string formatting, which avoids SQL injection.

**Simplest model that works.** Logistic regression performed as well as random forest and gradient boosting, so it is used for the outcome model. It is also the easiest to explain.

**Poisson regression for totals.** Goals and corners are small counts, so a Poisson model is a natural fit. Its expected value is converted into the probability of going over a line.

**Bookmaker odds are a benchmark, not an input.** Using them as features would raise accuracy mostly by copying the bookmaker, which says little about the model itself.

## Data

- Source: football-data.co.uk (free CSV files, one per league per season).
- Coverage: five leagues, seasons 2005/06 to 2026/27 (in progress), 38,475 matches.
- Fields kept in the cleaned table: result and half-time score, shots, shots on target, corners, fouls, cards, and Bet365 odds. The raw table keeps all ~210 original columns.
- 8 empty rows found in the downloaded files were removed during cleaning.

## Features

For each team, averages over its previous five matches (home and away combined): points, goals for, goals against, shots, shots on target, corners for and against, plus days of rest. The model also receives home-minus-away differences. For totals, matchup features combine one team's attack with the other's defence, and the average of the last five head-to-head meetings is included.

## Project structure

```
app.py                     Streamlit entry point
pages/
  1_Predictor.py           Prediction page (database + models)
  2_Stats.py               Player stats (static data, see limitations)
  3_Standing.py            League table (static data, see limitations)
db.py                      All database access (connections, queries, upserts)
cleaning.py                Cleaning rules shared by the loader and the update job
predict.py                 Builds live features and returns predictions
update_data.py             Re-downloads the current season and upserts (run by GitHub Actions)
download_data.py           One-time: download 20 years of files
clean_data.py              One-time: clean the raw table
create_tables.py           One-time: create the PostgreSQL tables
load_data.py               One-time: bulk load into PostgreSQL
features.py                Outcome features
features_totals.py         Goals and corners features
train_model.py             Train and compare outcome models
train_totals.py            Train and evaluate goals and corners models
evaluate.py                Confidence intervals, per-league accuracy, calibration
models/                    Saved models
.github/workflows/         Scheduled data update
```

## Running it locally

1. Install dependencies: `pip install -r requirements.txt`
2. Create a hosted PostgreSQL database and put its connection strings in `api.env`:
   ```
   DATABASE_URL=postgresql://...
   DATABASE_URL_POOLED=postgresql://...
   ```
3. Build the data and models, in order:
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
4. Start the app: `streamlit run app.py`

## Tech stack

Python, pandas, NumPy, scikit-learn, SciPy, PostgreSQL (Neon), psycopg2, Streamlit, GitHub Actions.

## Limitations

- The model sees only recent results. It has no lineups, injuries, transfers or match context, which is the main reason it trails the bookmaker.
- It almost never predicts draws, and its home-win probabilities are slightly high.
- Team names come from a single source. Adding a second data source would require a team-name mapping table.
- The Stats and Standings pages still use static files from an earlier version of this project and are not connected to the database.
- On free hosting, the first request after a quiet period can be slow.

## Next steps

- Elo-style team ratings and recency-weighted form, evaluated with the same time-based split.
- Recalibrate the home-win probabilities, or train on more recent seasons.
- A FastAPI layer over the same database and prediction code, and a JavaScript frontend on top of it.
- Player pages with per-season career statistics.
- Build the standings table directly from the matches table so it updates automatically.

## Data credit

Match data from football-data.co.uk.
