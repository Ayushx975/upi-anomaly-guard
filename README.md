# UPI Anomaly Guard

Real-time UPI transaction anomaly detection using Isolation Forest + statistical rules.

A lightweight, zero-dependency-heavy fraud screening tool inspired by my CyberShield 2026 (Bank of India x IIT Hyderabad) work on money-mule detection. This project focuses on **velocity checks, amount outliers, and odd-hour activity** — the three biggest signals in UPI fraud.

## Features

- Synthetic UPI transaction stream generator (realistic patterns + injected fraud)
- Isolation Forest anomaly scoring (scikit-learn)
- Rule-based velocity checks: multiple transactions within short windows
- Odd-hour detection (12 AM - 5 AM high-value transfers)
- Risk verdicts: LOW / MEDIUM / HIGH with per-signal reasons
- CLI batch mode + single transaction check

## Quick Start

```bash
pip install -r requirements.txt
python generate_data.py     # creates data/transactions.csv
python detect.py            # runs full anomaly scan
python detect.py --check 9876543210   # single-account deep dive
```

## Sample Output

```
Account      Txns   Risk    Reasons
A-1042         14    HIGH    velocity: 6 txns in 10min, odd-hour: 02:14 AM, amount outlier
A-0987          8    MEDIUM  amount outlier
A-0311         22    LOW     -
```

## How It Works

1. `generate_data.py` builds a synthetic ledger with normal + fraudulent behavior
2. `detect.py` extracts per-account features (velocity, amount z-score, hour pattern)
3. Isolation Forest scores each account; rules add explainable flags
4. Final verdict = max(ML score, rule score) — every flag has a human-readable reason

## Tech

Python 3.11 | scikit-learn | pandas | numpy

## Why This Exists

Built as a focused follow-up to MuleShield (https://github.com/Ayushx975/muleshield-web) — isolating the anomaly-detection core so it can be reused in any payment pipeline.

## License

MIT
