"""Generate synthetic order data: one clean file and one with known problems."""
import csv
import datetime as dt
import random
import sys
from pathlib import Path

HEADER = ["order_id", "customer_email", "order_date", "region", "amount", "status"]
REGIONS = ["Midwest", "Northeast", "South", "West"]
STATUSES = ["pending", "shipped", "delivered", "cancelled"]


def clean_rows(rng, n=200):
    start = dt.date(2026, 1, 1)
    rows = []
    for i in range(n):
        rows.append([
            1000 + i,
            f"customer{rng.randint(1, 80)}@example.com",
            (start + dt.timedelta(days=rng.randint(0, 180))).isoformat(),
            rng.choice(REGIONS),
            f"{rng.uniform(5, 900):.2f}",
            rng.choice(STATUSES),
        ])
    return rows


def dirty_rows(rows):
    rows = [list(r) for r in rows]
    rows[3][1] = ""                 # missing email
    rows[10][1] = "not-an-email"    # bad email pattern
    rows[15][2] = "2026-13-45"      # impossible date
    rows[22][4] = "-12.50"          # negative amount
    rows[30][4] = "99999"           # amount over the limit
    rows[41][5] = "shiped"          # status typo
    rows[50][3] = "Mars"            # unknown region (warning)
    rows[60][0] = rows[59][0]       # duplicate order id
    rows[70][4] = "abc"             # amount is not a number
    rows.append(list(rows[80]))     # exact duplicate row
    rows.append([1999, "short@example.com"])  # row with too few fields
    return rows


def write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "examples")
    out.mkdir(parents=True, exist_ok=True)
    base = clean_rows(random.Random(7))
    write(out / "orders_clean.csv", base)
    write(out / "orders_dirty.csv", dirty_rows(base))
    print("wrote", out)
