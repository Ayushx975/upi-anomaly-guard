"""Synthetic UPI transaction ledger generator - normal + fraudulent behavior."""
import csv
import os
import random

random.seed(42)

ACCOUNTS = [f"A-{i:04d}" for i in range(1, 61)]
MULES = random.sample(ACCOUNTS, 8)

NORMAL_AMOUNTS = (120, 4500)
MULE_AMOUNTS = (8000, 45000)


def normal_txn(acct: str) -> dict:
    hour = random.choice(range(7, 23))
    return {
        "account": acct,
        "amount": round(random.uniform(*NORMAL_AMOUNTS), 2),
        "timestamp": f"2026-09-{random.randint(1, 12):02d} {hour:02d}:{random.randint(0, 59):02d}",
        "merchant": random.choice(["grocery", "fuel", "retail", "utilities", "food"]),
    }


def mule_txn(acct: str, idx: int) -> dict:
    # mules: bursts of transfers, odd hours, high amounts, rapid drain-out
    hour = random.choice([1, 2, 3, 4, 23] + list(range(8, 22)))
    return {
        "account": acct,
        "amount": round(random.uniform(*MULE_AMOUNTS), 2),
        "timestamp": f"2026-09-{random.randint(1, 12):02d} {hour:02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}",
        "merchant": "transfer",
    }


def main() -> None:
    os.makedirs("data", exist_ok=True)
    rows = []
    for acct in ACCOUNTS:
        if acct in MULES:
            # burst: several txns within a tight window
            for i in range(random.randint(8, 16)):
                rows.append(mule_txn(acct, i))
        else:
            for _ in range(random.randint(6, 20)):
                rows.append(normal_txn(acct))

    random.shuffle(rows)
    with open("data/transactions.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["account", "amount", "timestamp", "merchant"])
        w.writeheader()
        w.writerows(rows)

    print(f"generated {len(rows)} txns across {len(ACCOUNTS)} accounts ({len(MULES)} mules)")
    print("mule accounts:", ", ".join(MULES))


if __name__ == "__main__":
    main()
