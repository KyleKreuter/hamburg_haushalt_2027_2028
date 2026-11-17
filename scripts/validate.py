"""Cross-check the parsed CSV files against the totals printed in the PDFs.

Usage: .venv/bin/python -I scripts/validate.py <data_dir>
"""

import sys

import pandas as pd

YEARS = ["ist_2024", "ist_2025", "fplan_2026", "plan_2027", "plan_2028", "plan_2029", "plan_2030"]


def main(data):
    ok = True
    p = pd.read_csv(f"{data}/ipr_produkte.csv", dtype={"ipr_code": str, "epl": str, "ab_code": str, "pg_code": str})
    s = pd.read_csv(f"{data}/ipr_summen.csv", dtype={"ipr": str})

    # 1. Each IPR product's rows must add up to its printed "Summe" lines.
    calc = p.groupby(["ipr_code", "art"])[YEARS].sum(min_count=1).fillna(0)
    printed = s.groupby(["ipr", "art"])[YEARS].sum().rename_axis(["ipr_code", "art"])
    diff = (calc - printed).abs()
    # Every printed value is rounded to 1 Tsd. EUR, so the sum of n rounded
    # values may differ from the rounded total by up to n/2.
    n_rows = p.groupby(["ipr_code", "art"]).size()
    tol = n_rows / 2 + 1
    bad = diff[diff.gt(tol, axis=0).any(axis=1)]
    missing = set(calc.index) ^ set(printed.index)
    print(f"IPR-Produkte: {p.ipr_code.nunique()}, Summenzeilen: {len(s)}")
    if len(bad) or missing:
        ok = False
        print("Abweichungen je IPR-Produkt (Tsd. EUR):")
        print(diff.loc[bad.index].to_string())
        print("Ohne Gegenstück:", sorted(missing))
    else:
        print(f"IPR-Summen: alle Abweichungen im Rundungsrahmen, max. {diff.values.max():.0f} Tsd. EUR")

    # 2. Rows must carry a full hierarchy.
    for col in ["epl", "ab_code", "pg_code", "produkt"]:
        n = p[col].isna().sum() + (p[col].astype(str).str.strip() == "").sum()
        if n:
            ok = False
            print(f"{n} Zeilen ohne {col}")

    # 3. Each product needs exactly one Erlöse and one Kosten line.
    pairs = p.groupby(["ipr_code", "epl", "pg_code", "produkt"]).art.agg(lambda a: "".join(sorted(a.str[0])))
    odd = pairs[pairs != "EK"]
    if len(odd):
        ok = False
        print("Produkte ohne genau ein Erlöse/Kosten-Paar:")
        print(odd.to_string())

    # 4. Compare the product report totals with the overall result plan.
    erg = pd.read_csv(f"{data}/gesamtergebnisplan.csv")
    tot = p.groupby("art")[YEARS].sum()
    print("\nSumme Produktbericht (Mio. EUR, bereinigt um Verrechnungen):")
    print((tot / 1000).round(1).to_string())
    print("\nZum Vergleich Gesamtergebnisplan (Mio. EUR):")
    keep = erg[erg.ebene == 0].set_index("position")[YEARS]
    print(keep[keep.index.str.match(r"^(1|2|5|7|8|9|11|12|15|16|17|18|19|20|21|25|26)\. ")].round(1).to_string())
    return ok


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1]) else 1)
