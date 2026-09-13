"""UPI anomaly detection: Isolation Forest + explainable rule flags."""
import argparse
import csv
from collections import defaultdict
from datetime import datetime

import numpy as np
from sklearn.ensemble import IsolationForest

FMT = "%Y-%m-%d %H:%M:%S"
FMT_SHORT = "%Y-%m-%d %H:%M"
ODD_HOURS = set(range(0, 6))  # 12 AM - 5:59 AM


def parse_ts(ts: str) -> datetime:
    for fmt in (FMT, FMT_SHORT):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    raise ValueError(f"unparseable timestamp: {ts}")


def load(path: str) -> list[dict]:
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["amount"] = float(r["amount"])
        r["dt"] = parse_ts(r["timestamp"])
    rows.sort(key=lambda r: r["dt"])
    return rows


def velocity_flags(rows: list[dict]) -> dict[str, int]:
    """max txns by one account inside any rolling 10-minute window."""
    by_acct = defaultdict(list)
    for r in rows:
        by_acct[r["account"]].append(r["dt"])

    out = {}
    for acct, times in by_acct.items():
        times.sort()
        best = 0
        j = 0
        for i in range(len(times)):
            while times[i] - times[j] > (times[i] - times[i]).fromordinal(0).replace(hour=0, minute=10) if False else False:
                break
        # simple O(n^2) is fine for ledger sizes here
        best = 0
        for i in range(len(times)):
            cnt = 0
            for j in range(len(times)):
                if abs((times[i] - times[j]).total_seconds()) <= 600:
                    cnt += 1
            best = max(best, cnt)
        out[acct] = best
    return out


def build_features(rows: list[dict]) -> tuple[list[str], dict[str, dict]]:
    by_acct = defaultdict(list)
    for r in rows:
        by_acct[r["account"]].append(r)

    feats = {}
    amounts = np.array([r["amount"] for r in rows])
    global_median = float(np.median(amounts))
    global_std = float(np.std(amounts) or 1.0)

    vel = velocity_flags(rows)

    for acct, txns in by_acct.items():
        amts = np.array([t["amount"] for t in txns])
        odd = sum(1 for t in txns if t["dt"].hour in ODD_HOURS)
        feats[acct] = {
            "txn_count": len(txns),
            "amount_median": float(np.median(amts)),
            "amount_max": float(np.max(amts)),
            "odd_hour_ratio": odd / len(txns),
            "velocity_10min": vel[acct],
            "transfer_ratio": sum(1 for t in txns if t["merchant"] == "transfer") / len(txns),
            "amount_z": abs(float(np.median(amts)) - global_median) / global_std,
        }
    return list(feats.keys()), feats


def rule_flags(f: dict) -> list[str]:
    reasons = []
    if f["velocity_10min"] >= 5:
        reasons.append(f"velocity: {f['velocity_10min']} txns in 10min")
    if f["odd_hour_ratio"] >= 0.3:
        reasons.append(f"odd-hour activity: {f['odd_hour_ratio']:.0%}")
    if f["amount_z"] >= 1.5:
        reasons.append("amount outlier")
    if f["transfer_ratio"] >= 0.8:
        reasons.append("almost pure transfer-out pattern")
    return reasons


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/transactions.csv")
    ap.add_argument("--check", help="deep-dive a single account id")
    args = ap.parse_args()

    rows = load(args.data)
    accounts, feats = build_features(rows)

    # isolation forest over feature matrix
    keys = ["txn_count", "amount_median", "amount_max", "odd_hour_ratio", "velocity_10min", "transfer_ratio"]
    X = np.array([[feats[a][k] for k in keys] for a in accounts])
    iso = IsolationForest(contamination=0.15, random_state=42)
    iso.fit(X)
    raw = -iso.score_samples(X)  # higher = more anomalous
    ml_score = (raw - raw.min()) / (raw.max() - raw.min() or 1.0)

    results = []
    for a, s in zip(accounts, ml_score):
        flags = rule_flags(feats[a])
        rule_score = min(1.0, 0.25 * len(flags))
        score = max(s, rule_score)
        verdict = "HIGH" if score >= 0.6 else ("MEDIUM" if score >= 0.35 else "LOW")
        results.append((a, feats[a]["txn_count"], verdict, score, flags))

    results.sort(key=lambda r: -r[3])

    if args.check:
        tgt = [r for r in results if r[0] == args.check]
        if not tgt:
            print(f"no transactions found for {args.check}")
            return
        a, n, v, s, flags = tgt[0]
        print(f"Account {a}: {n} txns -> {v} (score {s:.2f})")
        for fl in flags:
            print(f"  - {fl}")
        if not flags:
            print("  - no rule flags; verdict driven by ML ensemble")
        return

    print(f"{'Account':<12}{'Txns':>5}  {'Risk':<7}Reasons")
    for a, n, v, s, flags in results:
        print(f"{a:<12}{n:>5}  {v:<7}{', '.join(flags) if flags else '-'}")


if __name__ == "__main__":
    main()
