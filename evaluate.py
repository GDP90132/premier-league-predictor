import joblib
import numpy as np
import pandas as pd

df = pd.read_csv("data/features.csv", parse_dates=["Date"]).sort_values("Date")
test = df[df["Date"] >=
          "2024-07-01"].dropna(subset=["B365H", "B365D", "B365A"])
LABELS = ["A", "D", "H"]
y = test["FTR"].to_numpy()
n = len(test)

saved = joblib.load("models/logistic_regression.joblib")
model = saved["model"]
probs = model.predict_proba(test[saved["features"]])
pred = model.classes_[probs.argmax(axis=1)]

raw = 1 / test[["B365A", "B365D", "B365H"]].to_numpy()
book = raw / raw.sum(axis=1, keepdims=True)
book_pred = np.array(LABELS)[book.argmax(axis=1)]

correct = {
    "logistic regression": (pred == y).astype(int),
    "bookmaker": (book_pred == y).astype(int),
    "always home": (y == "H").astype(int),
}

# bootstrap: resample the test matches 2000 times to see how much accuracy could wobble
rng = np.random.default_rng(1)
idx = rng.integers(0, n, size=(2000, n))
print(f"test matches: {n}\n")
for name, c in correct.items():
    lo, hi = np.percentile(c[idx].mean(axis=1), [2.5, 97.5])
    print(f"{name:20s} accuracy {c.mean():.3f}   95% range {lo:.3f} to {hi:.3f}")

diff = (correct["bookmaker"] -
        correct["logistic regression"])[idx].mean(axis=1)
lo, hi = np.percentile(diff, [2.5, 97.5])
print(
    f"\nbookmaker minus our model: {diff.mean():.3f}   95% range {lo:.3f} to {hi:.3f}")

print("\naccuracy by league:")
print(test.assign(correct=correct["logistic regression"])
      .groupby("league")["correct"].agg(accuracy="mean", matches="size").round(3))

print("\ncalibration of the home-win probability (5 equal-sized groups):")
p_home = probs[:, list(model.classes_).index("H")]
cal = pd.DataFrame({"predicted": p_home, "actual": (y == "H").astype(int)})
cal["group"] = pd.qcut(cal["predicted"], 5, labels=False)
print(cal.groupby("group").mean().round(3))
