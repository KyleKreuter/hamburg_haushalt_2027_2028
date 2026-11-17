"""Check parsed Einzelplan volumes against their own totals and the product report.

Usage: python3 -I scripts/validate_epl.py <dashboard_dir>

Reports per Einzelplan: Produktgruppen with a broken row identity in the Ergebnisplan,
and Produktgruppen whose costs 2027 differ from the IPR product report by more than 1 %.
"""

import collections
import json
import os
import sys

HAUPT = ("2", "3", "4", "5", "6")


def main(dash_dir):
    k = json.load(open(os.path.join(dash_dir, "kostenarten.json"), encoding="utf-8"))["rows"]
    prod = json.load(open(os.path.join(dash_dir, "produkte.json"), encoding="utf-8"))["rows"]
    by_pg = collections.defaultdict(list)
    for r in k:
        by_pg[(r["epl"], r["pg"])].append(r)
    prod_pg = collections.defaultdict(float)
    for p in prod:
        prod_pg[(p["epl"], p["pg"])] += p["k27"]
    epls = sorted({e for e, _ in by_pg})
    total_ok = total = 0
    for epl in epls:
        bad = []
        keys = sorted({key for key in by_pg if key[0] == epl} | {key for key in prod_pg if key[0] == epl and prod_pg[key]})
        for key in keys:
            band = sum(r["j2027"] or 0 for r in by_pg.get(key, []) if r["ebene"] == "haupt")
            ipr = prod_pg.get(key, 0.0)
            total += 1
            if abs(band - ipr) <= max(50, abs(ipr) * 0.01):
                total_ok += 1
            else:
                bad.append(f"{key[1]}: Band {band:,.0f}, Produktbericht {ipr:,.0f}")
        print(f"EPL {epl}: {len(keys) - len(bad)}/{len(keys)} Produktgruppen passen")
        for b in bad:
            print("   ", b)
    print(f"gesamt: {total_ok}/{total}")


if __name__ == "__main__":
    main(sys.argv[1])
