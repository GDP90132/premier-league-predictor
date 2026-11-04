from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

df = pd.read_csv("data/features.csv", parse_dates=["Date"]).sort_values("Date")

base = ["pts5", "gf5", "ga5", "shots5", "sot5"]
FEATURES = (
    [f"home_{c}" for c in base]
    + [f"away_{c}" for c in base]
    + ["home_rest_days", "away_rest_days"]
    + [f"{c}_diff" for c in base]
)
LABELS = ["A", "D", "H"]  # sklearn sorts classes alphabetically

# time-based split: train on older matches, test on newer ones
CUTOFF = "2024-07-01"
train = df[df["Date"] < CUTOFF]
test = df[df["Date"] >= CUTOFF]
# keep only test matches that have bookmaker odds, so every comparison is fair
test = test.dropna(subset=["B365H", "B365D", "B365A"])

X_train, y_train = train[FEATURES], train["FTR"]
X_test, y_test = test[FEATURES], test["FTR"]
print(
    f"train: {len(train)} matches ({train['Date'].min().date()} to {train['Date'].max().date()})")
print(
    f"test:  {len(test)} matches ({test['Date'].min().date()} to {test['Date'].max().date()})\n")

results = []

# baseline 1: always pick home (probabilities = training class frequencies)
freq = y_train.value_counts(normalize=True).reindex(LABELS).to_numpy()
const_probs = np.tile(freq, (len(test), 1))
results.append({
    "model": "always home",
    "accuracy": (y_test == "H").mean(),
    "log_loss": log_loss(y_test, const_probs, labels=LABELS),
    "pred_draws": 0,
})

# baseline 2: bookmaker (Bet365) odds -> probabilities with the margin removed
raw = 1 / test[["B365A", "B365D", "B365H"]].to_numpy()
book_probs = raw / raw.sum(axis=1, keepdims=True)
book_pred = np.array(LABELS)[book_probs.argmax(axis=1)]
results.append({
    "model": "bookmaker (Bet365)",
    "accuracy": accuracy_score(y_test, book_pred),
    "log_loss": log_loss(y_test, book_probs, labels=LABELS),
    "pred_draws": int((book_pred == "D").sum()),
})

# our models
models = {
    "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
    "random_forest": RandomForestClassifier(
        n_estimators=300, max_depth=6, min_samples_leaf=20, random_state=1, n_jobs=-1
    ),
    "gradient_boosting": HistGradientBoostingClassifier(
        max_depth=3, learning_rate=0.05, max_iter=150, early_stopping=False, random_state=1
    ),
}

Path("models").mkdir(exist_ok=True)
for name, model in models.items():
    model.fit(X_train, y_train)
    # columns follow model.classes_ = A, D, H
    probs = model.predict_proba(X_test)
    preds = model.predict(X_test)
    results.append({
        "model": name,
        "accuracy": accuracy_score(y_test, preds),
        "log_loss": log_loss(y_test, probs, labels=LABELS),
        "pred_draws": int((preds == "D").sum()),
    })
    joblib.dump({"model": model, "features": FEATURES},
                f"models/{name}.joblib")

print(pd.DataFrame(results).round(4).to_string(index=False))
