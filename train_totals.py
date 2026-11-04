from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import log_loss, mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

df = pd.read_csv("data/features_totals.csv",
                 parse_dates=["Date"]).sort_values("Date")
df["total_goals"] = df["FTHG"] + df["FTAG"]
df["total_corners"] = df["HC"] + df["AC"]

FEATURES = [c for c in df.columns if c.startswith(("home_", "away_"))]
FEATURES += ["form_total_goals", "form_total_corners",
             "h2h_goals5", "h2h_corners5", "h2h_n"]

TARGETS = {
    "goals": ("total_goals", [1.5, 2.5, 3.5]),
    "corners": ("total_corners", [8.5, 9.5, 10.5, 11.5]),
}

CUTOFF = "2024-07-01"
train = df[df["Date"] < CUTOFF]
test = df[df["Date"] >= CUTOFF]


def make_models():
    return {
        "poisson_regression": make_pipeline(
            SimpleImputer(strategy="mean"), StandardScaler(),
            PoissonRegressor(alpha=1.0, max_iter=1000),
        ),
        "gradient_boosting": HistGradientBoostingRegressor(
            loss="poisson", max_depth=3, learning_rate=0.05,
            max_iter=150, early_stopping=False, random_state=1,
        ),
    }


Path("models").mkdir(exist_ok=True)

for name, (target, lines) in TARGETS.items():
    tr = train.dropna(subset=[target])
    te = test.dropna(subset=[target])
    X_tr, y_tr, X_te, y_te = tr[FEATURES], tr[target], te[FEATURES], te[target]
    print(f"\n===== {name.upper()}: train {len(tr)}, test {len(te)}, "
          f"test average {y_te.mean():.2f} =====")

    # predictions: expected value for each test match
    preds = {"baseline (train avg)": np.full(len(te), y_tr.mean())}
    for mname, model in make_models().items():
        model.fit(X_tr, y_tr)
        preds[mname] = model.predict(X_te)
        joblib.dump({"model": model, "features": FEATURES},
                    f"models/{name}_{mname}.joblib")

    # how far off is the predicted number? (average error)
    print("\naverage error (MAE), lower is better:")
    for mname, lam in preds.items():
        print(f"  {mname:22s} {mean_absolute_error(y_te, lam):.3f}")

    # over/under lines
    rows = []
    for line in lines:
        actual = (y_te > line).astype(int).to_numpy()
        for mname, lam in preds.items():
            if mname.startswith("baseline"):
                # best constant guess
                p = np.full(len(te), (y_tr > line).mean())
            else:
                p = poisson.sf(np.floor(line), lam)  # P(total > line)
            p = np.clip(p, 0.001, 0.999)
            rows.append({
                "line": line, "model": mname,
                "accuracy": ((p > 0.5).astype(int) == actual).mean(),
                "log_loss": log_loss(actual, p, labels=[0, 1]),
                "actual_over_rate": actual.mean(),
            })
    print("\nover/under results:")
    print(pd.DataFrame(rows).round(4).to_string(index=False))
