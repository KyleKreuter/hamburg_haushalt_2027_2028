"""Build the JSON dataset for the visualisation page from the parsed CSV files.

Usage: .venv/bin/python -I scripts/build_dataset.py <gesamthaushalt.pdf> <data_dir> <out.json>
"""

import json
import os
import re
import subprocess
import sys

import pandas as pd

YEARS = ["ist_2024", "ist_2025", "fplan_2026", "plan_2027", "plan_2028", "plan_2029", "plan_2030"]

# Full Einzelplan names; the overview tables abbreviate some of them.
EPL_NAMES = {
    "1.01": "Bürgerschaft", "1.02": "Verfassungsgericht", "1.03": "Rechnungshof",
    "1.04": "Datenschutzbeauftragter (HmbBfDI)", "1.1": "Senat und Personalamt",
    "1.2": "Bezirksamt Hamburg-Mitte", "1.3": "Bezirksamt Altona", "1.4": "Bezirksamt Eimsbüttel",
    "1.5": "Bezirksamt Hamburg-Nord", "1.6": "Bezirksamt Wandsbek", "1.7": "Bezirksamt Bergedorf",
    "1.8": "Bezirksamt Harburg", "2": "Justiz und Verbraucherschutz",
    "3.1": "Schule, Familie und Berufsbildung", "3.2": "Wissenschaft, Forschung und Gleichstellung",
    "3.3": "Kultur und Medien", "4": "Gesundheit, Soziales und Integration",
    "6.1": "Stadtentwicklung und Wohnen", "6.2": "Umwelt, Klima, Energie und Agrarwirtschaft",
    "7.0": "Wirtschaft, Arbeit und Innovation", "7.1": "Verkehr und Mobilitätswende",
    "8.1": "Inneres und Sport", "9.1": "Finanzen und Bezirke", "9.2": "Allgemeine Finanzwirtschaft",
}
EPL_SHORT = {
    "1.01": "Bürgerschaft", "1.02": "Verfassungsgericht", "1.03": "Rechnungshof", "1.04": "HmbBfDI",
    "1.1": "Senat", "1.2": "BA Mitte", "1.3": "BA Altona", "1.4": "BA Eimsbüttel", "1.5": "BA Nord",
    "1.6": "BA Wandsbek", "1.7": "BA Bergedorf", "1.8": "BA Harburg", "2": "Justiz", "3.1": "Schule",
    "3.2": "Wissenschaft", "3.3": "Kultur", "4": "Soziales", "6.1": "Stadtentwicklung", "6.2": "Umwelt",
    "7.0": "Wirtschaft", "7.1": "Verkehr", "8.1": "Inneres", "9.1": "Finanzbehörde",
    "9.2": "Allg. Finanzwirtschaft",
}
# Main groups of the IPR functional classification. The labels are derived from
# the IPR products that each first digit contains.
IPR_GROUPS = {
    "0": "Politische Führung und zentrale Verwaltung", "1": "Innere Sicherheit und Ordnung",
    "2": "Justiz", "3": "Bildung, Wissenschaft und Kultur", "4": "Verkehr, Stadtentwicklung und Wohnen",
    "5": "Soziales, Kinder, Jugend und Familie", "6": "Gesundheit, Verbraucherschutz und Sport",
    "7": "Umwelt- und Naturschutz", "8": "Wirtschaft, Arbeit und Energie", "9": "Finanzen und zentrale Positionen",
}
# Table 3 of the Finanzbericht 2027/2028 (page 15), Mio. EUR, transcribed by hand.
NKA_COMPONENTS = {
    "jahre": [2027, 2028, 2029, 2030],
    "Konjunkturkomponente": [1457.4, 1977.5, 2539.5, 3182.3],
    "Finanzielle Transaktionen": [2030.7, 1993.4, 1843.1, 1850.7],
    "Strukturkomponente (StruKomLäG)": [415.0, 415.0, 415.0, 415.0],
}
# Table 2 of the Finanzbericht 2027/2028 (page 14), Mio. EUR.
TAX_TREND = {"jahre": [2027, 2028, 2029, 2030], "trend": [18259.7, 19238.0, 20333.6, 21503.8]}


def hierarchy_names(pdf):
    """Read full Aufgabenbereich and Produktgruppe names from section 9 of the PDF."""
    out = subprocess.run(["pdftotext", "-layout", "-f", "316", "-l", "323", pdf, "-"],
                         check=True, capture_output=True).stdout.decode()
    ab, pg = {}, {}
    for line in out.splitlines():
        m = re.match(r"^\s*Aufgabenbereich (\d{3}) ?- ?(.+?)\s*$", line)
        if m:
            ab[m.group(1)] = m.group(2)
        m = re.match(r"^\s*Produktgruppe (\d{3}\.\d{2}) ?- ?(.+?)\s*$", line)
        if m:
            pg[m.group(1)] = m.group(2)
    return ab, pg


def r1(x):
    return None if pd.isna(x) else round(float(x), 1)


def main(pdf, data, out_path):
    erg = pd.read_csv(f"{data}/gesamtergebnisplan.csv")
    fin = pd.read_csv(f"{data}/gesamtfinanzplan.csv")
    epl = pd.read_csv(f"{data}/epl_ergebnis.csv", dtype={"epl": str})
    inv = pd.read_csv(f"{data}/epl_investitionen.csv", dtype={"epl": str})
    ipr = pd.read_csv(f"{data}/ipr_produkte.csv", dtype={"ipr_code": str, "epl": str, "ab_code": str, "pg_code": str})
    ab_names, pg_names = hierarchy_names(pdf)

    def erg_row(prefix):
        row = erg[(erg.ebene == 0) & erg.position.str.startswith(prefix)].iloc[0]
        return [r1(row[y]) for y in YEARS]

    def fin_row(prefix):
        row = fin[fin.position.str.startswith(prefix)].iloc[0]
        return [r1(row[y]) for y in YEARS]

    # Overall time series 2024-2030 (Mio. EUR).
    cost_rows = ["7.", "8.", "9.", "10.", "11.", "12.", "20.", "21.", "22.", "25.", "26."]
    income_rows = ["1.", "2.", "3.", "4.", "5.", "15.", "16.", "17.", "18.", "19."]

    def total(prefixes):
        vals = [erg_row(p + " ") for p in prefixes]
        return [round(sum(v[i] or 0 for v in vals), 1) for i in range(len(YEARS))]

    series = {
        "jahre": [2024, 2025, 2026, 2027, 2028, 2029, 2030],
        "art": ["Ist", "Ist", "Fortg. Plan", "Plan", "Plan", "Finanzplan", "Finanzplan"],
        "aufwand": total(cost_rows),
        "ertrag": total(income_rows),
        "jahresergebnis": erg_row("27. "),
        "steuern": [r1(erg[erg.position == "a) Steuererträge"].iloc[0][y]) for y in YEARS],
        "personal": erg_row("8. "),
        "transfer": erg_row("9. "),
        "zinsen": erg_row("21. "),
        "nettokreditaufnahme": fin_row("27. "),
        # Gross investment payments: rows 8-14 of the Gesamtfinanzplan.
        "investitionen": [round(sum((fin_row(f"{n}. ")[k] or 0) for n in range(8, 15)), 1) for k in range(len(YEARS))],
        "darlehen": [round(-(v or 0), 1) for v in fin_row("18. ")],
        "rücklage_entnahme": erg_row("43. "),
    }

    # Per Einzelplan: cost categories, revenues, investments (Mio. EUR).
    cats = {
        "Personalkosten": "personal", "Kosten aus Transferleistungen": "transfer",
        "Kosten aus lfd. Verwaltungstätigkeit": "verwaltung", "Kosten aus Abschreibungen": "abschreibungen",
        "Sonstige Kosten": "sonstige", "Kosten des Finanzergebnisses": "finanz",
        "Globale Mehrkosten": "global_mehr", "Globale Minderkosten": "global_minder",
        "Erlöse": "erlöse", "Erlöse des Finanzergebnisses": "erlöse_finanz",
    }
    e = epl[epl.epl != "Gesamtsumme"].copy()
    e["key"] = e.kategorie.map(cats)
    piv = e.pivot_table(index=["epl"], columns=["key", "jahr"], values="tsd_eur", aggfunc="sum").fillna(0) / 1000
    i = inv[inv.epl != "Gesamtsumme"].pivot_table(index="epl", columns=["kategorie", "jahr"], values="tsd_eur",
                                                 aggfunc="sum").fillna(0) / 1000
    epl_list = []
    for code in EPL_NAMES:
        rec = {"code": code, "name": EPL_NAMES[code], "kurz": EPL_SHORT[code], "jahre": {}}
        for jahr in ["fplan_2026", "plan_2027", "plan_2028"]:
            vals = {k: round(piv.loc[code, (k, jahr)], 1) if (k, jahr) in piv.columns else 0.0
                    for k in cats.values()}
            vals["kosten_gesamt"] = round(sum(vals[k] for k in ["personal", "transfer", "verwaltung",
                                                                 "abschreibungen", "sonstige", "finanz",
                                                                 "global_mehr", "global_minder"]), 1)
            vals["invest_aus"] = round(i.loc[code, ("Investitionen Auszahlungen", jahr)], 1)
            vals["invest_ein"] = round(i.loc[code, ("Investitionen Einzahlungen", jahr)], 1)
            vals["darlehen_aus"] = round(i.loc[code, ("Darlehen Auszahlungen", jahr)], 1)
            rec["jahre"][jahr[-4:]] = vals
        epl_list.append(rec)

    # Product tree from the IPR product report (Tsd. EUR, cleaned of internal charges).
    wide = ipr.pivot_table(index=["ipr_code", "ipr_name", "epl", "ab_code", "ab_name", "pg_code", "pg_name", "produkt"],
                           columns="art", values=["ist_2024", "ist_2025", "plan_2027", "plan_2028", "plan_2029", "plan_2030"],
                           aggfunc="sum").fillna(0)
    wide.columns = [f"{a}_{b}" for a, b in wide.columns]
    wide = wide.reset_index()
    produkte = []
    for _, r in wide.iterrows():
        produkte.append({
            "epl": r.epl, "ab": r.ab_code, "pg": r.pg_code, "ipr": r.ipr_code, "name": r.produkt,
            # The report has no values for the updated plan 2026.
            **{f"{a}{y[-2:]}": r[f"{y}_{art}"] for a, art in (("k", "Kosten"), ("e", "Erlöse"))
               for y in ("ist_2024", "ist_2025", "plan_2027", "plan_2028", "plan_2029", "plan_2030")},
        })
    ab_map = {r.ab_code: ab_names.get(r.ab_code, r.ab_name) for _, r in wide.iterrows()}
    pg_map = {r.pg_code: pg_names.get(r.pg_code, r.pg_name) for _, r in wide.iterrows()}
    ipr_map = {r.ipr_code: r.ipr_name for _, r in wide.iterrows()}

    k27 = erg_row("27. ")[3]
    site = {
        "stand": "Haushaltsplan-Entwurf 2027/2028, Senatsbeschluss Juli 2026",
        "kpi": {
            "2027": {"aufwand": series["aufwand"][3], "ertrag": series["ertrag"][3], "ergebnis": k27,
                     "nka": series["nettokreditaufnahme"][3], "invest": series["investitionen"][3],
                     "steuern": series["steuern"][3], "zinsen": series["zinsen"][3]},
            "2028": {"aufwand": series["aufwand"][4], "ertrag": series["ertrag"][4], "ergebnis": series["jahresergebnis"][4],
                     "nka": series["nettokreditaufnahme"][4], "invest": series["investitionen"][4],
                     "steuern": series["steuern"][4], "zinsen": series["zinsen"][4]},
            "2026": {"aufwand": series["aufwand"][2], "ertrag": series["ertrag"][2], "ergebnis": series["jahresergebnis"][2],
                     "nka": series["nettokreditaufnahme"][2], "invest": series["investitionen"][2],
                     "steuern": series["steuern"][2], "zinsen": series["zinsen"][2]},
        },
        "reihe": series,
        "nka_komponenten": NKA_COMPONENTS,
        "steuertrend": TAX_TREND,
        "einzelplaene": epl_list,
        "namen": {"ab": ab_map, "pg": pg_map, "ipr": ipr_map, "ipr_gruppen": IPR_GROUPS},
        "produkte": produkte,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(site, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{out_path}: {os.path.getsize(out_path) / 1024:.0f} KB, {len(produkte)} Produkte")
    print("KPI", json.dumps(site["kpi"], ensure_ascii=False))
    print("Aufwand", series["aufwand"])
    print("Ertrag", series["ertrag"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
