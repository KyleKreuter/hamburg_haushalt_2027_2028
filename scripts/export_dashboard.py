"""Write the dashboard's data files ({rows, meta}) from data/site.json.

Usage: .venv/bin/python -I scripts/export_dashboard.py <site.json> <out_dir>
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def code(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return {"label": name, "value": f.read(), "type": "code", "lang": "python"}


SOURCE_PDF = {"label": "Quelle", "value": "Haushaltsplan-Entwurf 2027/2028, Band Gesamthaushalt (PDF, Finanzbehörde Hamburg, Juli 2026)"}


def write(out_dir, name, rows, meta):
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "meta": meta}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{path}: {len(rows)} Zeilen, {os.path.getsize(path) / 1024:.0f} KB")


IST = ("24", "25")
PLAN = ("27", "28", "29", "30")


def has(p, years):
    return any(p[f"{a}{y}"] for a in ("k", "e") for y in years)


def name_key(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


def link_moved_products(prod):
    """Map the actuals of products that moved to a new row onto that row.

    A product that changes its Einzelplan or name for the 2027 plan appears twice in the
    IPR report: the old row carries only actuals (2024, 2025), the new row only plan values.
    Adds vk24, vk25, ve24, ve25 = actuals in the structure of the 2027 plan, plus wechsel
    ('zugang' | 'abgang' | '') and wechsel_text.
    """
    from difflib import SequenceMatcher

    for p in prod:
        for a in ("k", "e"):
            for y in IST:
                p[f"v{a}{y}"] = p[f"{a}{y}"]
        p["wechsel"], p["wechsel_text"], p["wechsel_extern"] = "", "", False

    pre = [p for p in prod if has(p, IST) and not has(p, PLAN)]
    suc = [p for p in prod if has(p, PLAN) and not has(p, IST)]
    # Pass 1: same IPR number and same name. Several old and new rows may share one group,
    # for example a transfer payment that moves from the district offices to one authority.
    groups = {}
    for s in suc:
        olds = [p for p in pre if p["ipr"] == s["ipr"] and name_key(p["produkt"]) == name_key(s["produkt"])]
        if olds:
            g = groups.setdefault((s["ipr"], name_key(s["produkt"])), (set(), []))
            g[0].update(p["id"] for p in olds)
            g[1].append(s)
    # Pass 2: same IPR number and a near-identical name, one new row per old row.
    used_pre = {i for g in groups.values() for i in g[0]}
    used_suc = {s["id"] for g in groups.values() for s in g[1]}
    for s in suc:
        if s["id"] in used_suc:
            continue
        cands = [(SequenceMatcher(None, name_key(p["produkt"]), name_key(s["produkt"])).ratio(), p)
                 for p in pre if p["id"] not in used_pre and p["ipr"] == s["ipr"]]
        cands = [c for c in cands if c[0] >= 0.9]
        if cands:
            p = max(cands, key=lambda c: c[0])[1]
            used_pre.add(p["id"])
            groups[("fuzzy", s["id"])] = ({p["id"]}, [s])

    by_id = {p["id"]: p for p in prod}
    for pre_ids, sucs in groups.values():
        olds = [by_id[i] for i in sorted(pre_ids, key=int)]
        weights = [max(s["k27"], 0) or max(s["e27"], 0) for s in sucs]
        total = sum(weights) or len(sucs)
        weights = [w / total if sum(weights) else 1 / len(sucs) for w in weights]
        for s, w in zip(sucs, weights):
            for a in ("k", "e"):
                for y in IST:
                    s[f"v{a}{y}"] = round(sum(o[f"{a}{y}"] for o in olds) * w, 1)
            s["wechsel"] = "zugang"
            s["wechsel_extern"] = any(o["epl"] != s["epl"] for o in olds)
            s["wechsel_text"] = describe_origin(s, olds, len(sucs) > 1)
        for o in olds:
            for a in ("k", "e"):
                for y in IST:
                    o[f"v{a}{y}"] = 0
            o["wechsel"] = "abgang"
            o["wechsel_extern"] = any(x["epl"] != o["epl"] for x in sucs)
            o["wechsel_text"] = describe_target(o, sucs)
    moved = sum(len(g[0]) for g in groups.values())
    print(f"verschobene Produkte: {moved} alte Zeilen, {sum(len(g[1]) for g in groups.values())} neue Zeilen")


def plans(rows):
    names = sorted({r["epl_kurz"] for r in rows})
    return f"im Einzelplan {names[0]}" if len(names) == 1 else "in den Einzelplänen " + ", ".join(names)


def describe_origin(s, olds, split):
    o = olds[0]
    if len(olds) == 1 and o["epl"] == s["epl"] and name_key(o["produkt"]) == name_key(s["produkt"]):
        src = f"der früheren Produktgruppe „{o['pg_name']}“"
    elif len(olds) == 1 and o["epl"] == s["epl"]:
        src = f"dem früheren Produkt „{o['produkt']}“"
    elif len(olds) == 1:
        src = f"dem Produkt „{o['produkt']}“ {plans(olds)}"
    else:
        src = f"{len(olds)} Produkten {plans(olds)}"
    tail = ", anteilig nach den Kosten 2027" if split else ""
    return f"Das Ist 2024 und 2025 stammt aus {src}{tail}."


def describe_target(o, sucs):
    s = sucs[0]
    if len(sucs) == 1 and s["epl"] == o["epl"] and name_key(o["produkt"]) == name_key(s["produkt"]):
        return f"Ab 2027 in der Produktgruppe „{s['pg_name']}“ veranschlagt."
    if len(sucs) == 1 and s["epl"] == o["epl"]:
        return f"Ab 2027 als „{s['produkt']}“ veranschlagt."
    return f"Ab 2027 {plans(sucs)} veranschlagt."


DETAIL_YEARS = ["2024", "2025", "2026", "2027", "2028", "2029", "2030"]
# Cost rows of the Ergebnisplan der Produktgruppe in display order; 'davon' rows are subsets.
COST_ROWS = [
    ("3", "Personalkosten", "haupt"),
    ("3a", "Entgelte", "davon"),
    ("3b", "Bezüge (Beamtinnen und Beamte)", "davon"),
    ("3c", "Sonstige Kosten mit Entgelt- oder Bezugscharakter", "davon"),
    ("3d", "Sozialleistungen", "davon"),
    ("3e", "Versorgungsleistungen", "davon"),
    ("2", "Kosten aus laufender Verwaltungstätigkeit", "haupt"),
    ("2a", "davon Mieten, Pachten und Erbbauzinsen", "davon"),
    ("2b", "davon IT-Kosten", "davon"),
    ("2c", "davon Prüfung, Beratung, Rechtsschutz", "davon"),
    ("4", "Transferleistungen", "haupt"),
    ("5", "Abschreibungen", "haupt"),
    ("6", "Sonstige Kosten", "haupt"),
    ("9", "Kosten des Finanzergebnisses", "haupt"),
    ("12", "Globale Mehrkosten", "haupt"),
    ("13", "Globale Minderkosten (Einsparvorgabe)", "haupt"),
]


def export_details(out_dir, prod):
    """Write kostenarten.json and kennzahlen.json from data/epl_*.json (parse_epl.py)."""
    import glob

    data_dir = os.path.join(HERE, "..", "data")
    kosten, kennz, sources = [], [], []
    known = {e["epl"] for e in prod}

    def norm(code):
        # Page headers write "7.0" or "2"; the overview uses either form.
        for c in (code, code + ".0", code[:-2] if code.endswith(".0") else None):
            if c in known:
                return c
        return None

    for path in sorted(glob.glob(os.path.join(data_dir, "epl_*.json"))):
        with open(path, encoding="utf-8") as f:
            band = json.load(f)
        for g in band["produktgruppen"]:
            epl = norm(g.get("epl") or "")
            if epl is None:
                print(f"{path}: Einzelplan {g.get('epl')!r} unbekannt, Produktgruppe {g['pg']} übersprungen")
                continue
            if epl not in sources:
                sources.append(epl)
            rows = g["ergebnisplan"]
            if not rows:
                continue
            base = {"epl": epl, "pg": g["pg"], "pg_name": g["name"], "produkt_id": ""}

            def row(pos, label, ebene, vals, **extra):
                kosten.append({**base, **extra, "pos": pos, "label": label, "ebene": ebene,
                               **{f"j{y}": v for y, v in zip(DETAIL_YEARS, vals)}})

            for pos, label, ebene in COST_ROWS:
                vals = rows.get(pos, [None] * 7)
                if any(vals):
                    row(pos, label, ebene, vals)
            # Allocation of the authority's internal services (Jahresergebnis 2).
            alloc_k = [sum((q.get("k2") or [None] * 7)[i] or 0 for q in g["produkte"]) for i in range(7)]
            alloc_e = [sum((q.get("e2") or [None] * 7)[i] or 0 for q in g["produkte"]) for i in range(7)]
            alloc_k[2] = alloc_e[2] = None  # The volume shows no allocation for 2026.
            if any(alloc_k):
                row("V", "Anteil an internen Dienstleistungen der Behörde", "haupt", alloc_k)
            erl = [(a or 0) + (b or 0) + (c or 0) if any(v is not None for v in (a, b, c)) else None
                   for a, b, c in zip(rows.get("1", [None] * 7), rows.get("8", [None] * 7), alloc_e)]
            row("E", "Erlöse", "erloese", erl)
            # Direct costs and allocated costs per product, matched to the product report.
            for q in g["produkte"]:
                hit = [p for p in prod if p["epl"] == epl and p["pg"] == g["pg"] and p["ipr"] == q["ipr"] and p["produkt"] == q["produkt"]]
                if len(hit) != 1:
                    continue
                pid = hit[0]["id"]
                row("P1", "Direkte Kosten", "produkt", q.get("k1") or [None] * 7, produkt_id=pid)
                if any(q.get("k2") or []):
                    k2 = list(q["k2"])
                    k2[2] = None
                    row("P2", "Anteil an internen Dienstleistungen der Behörde", "produkt", k2, produkt_id=pid)
            for k in g["kennzahlen"]:
                kennz.append({"epl": epl, "pg": g["pg"], "code": k["code"], "name": k["name"], "einheit": k["einheit"],
                              **{f"j{y}": k[y] for y in DETAIL_YEARS}})
    if not sources:
        return
    src = {"label": "Quelle", "value": "Haushaltsplan-Entwurf 2027/2028, Einzelplan-Bände " + ", ".join(sources) + " (PDF, Finanzbehörde Hamburg)"}
    write(out_dir, "kostenarten.json", kosten, [
        src, {"label": "Tabellen", "value": "Ergebnisplan der Produktgruppe; Kosten und Erlöse der Produktgruppe (Jahresergebnis 1 und 2)"},
        {"label": "Einheit", "value": "Tsd. EUR"},
        {"label": "Hinweis", "value": "jJJJJ = Wert des Jahres (2024 und 2025 Ist, 2026 fortgeschriebener Plan, 2027 und 2028 Plan, 2029 und 2030 Finanzplanung). Zeilen mit ebene 'davon' sind Teilmengen der Hauptzeile darüber. pos V = Kosten interner Dienstleistungen der Behörde, die im Jahresergebnis 2 auf die Produkte verteilt werden; für 2026 weist der Band keine Verteilung aus. pos E = Erlöse einschließlich Finanzergebnis und Verteilung. Zeilen P1 und P2 gelten für ein Produkt (produkt_id). Die Werte sind nicht um haushaltsinterne Verrechnungen bereinigt und liegen deshalb bis zu 1 % über dem Produktbericht."},
        code("parse_epl.py"), code("export_dashboard.py")])
    write(out_dir, "kennzahlen.json", kennz, [
        src, {"label": "Tabelle", "value": "Kennzahlen der Produktgruppe"},
        {"label": "Hinweis", "value": "jJJJJ = Wert des Jahres; einheit wie im Band (ANZ = Anzahl)."},
        code("parse_epl.py")])


def main(site_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with open(site_path, encoding="utf-8") as f:
        site = json.load(f)
    r = site["reihe"]

    eck = []
    for i, jahr in enumerate(r["jahre"]):
        eck.append({
            "jahr": jahr, "art": r["art"][i], "aufwand": r["aufwand"][i], "ertrag": r["ertrag"][i],
            "jahresergebnis": r["jahresergebnis"][i], "steuern": r["steuern"][i], "personal": r["personal"][i],
            "transfer": r["transfer"][i], "zinsen": r["zinsen"][i],
            "nettokreditaufnahme": r["nettokreditaufnahme"][i], "investitionen": r["investitionen"][i],
            "darlehen": r["darlehen"][i], "ruecklage_entnahme": r["rücklage_entnahme"][i],
        })
    write(out_dir, "eckwerte.json", eck, [
        SOURCE_PDF, {"label": "Tabellen", "value": "2.1 Gesamtergebnisplan, 2.2 Doppischer Gesamtfinanzplan (S. 1-6)"},
        {"label": "Einheit", "value": "Mio. EUR"}, code("parse_overviews.py"), code("build_dataset.py")])

    epl = []
    for e in site["einzelplaene"]:
        row = {"code": e["code"], "name": e["name"], "kurz": e["kurz"]}
        for jahr, vals in e["jahre"].items():
            for k, v in vals.items():
                row[f"{k}_{jahr}"] = v
        epl.append(row)
    write(out_dir, "einzelplaene.json", epl, [
        SOURCE_PDF, {"label": "Tabellen", "value": "3.1 Haushaltsübersicht Kosten und Erlöse, 3.2 Investitionen und Darlehen der Einzelpläne (S. 7-13)"},
        {"label": "Einheit", "value": "Mio. EUR"}, code("parse_overviews.py"), code("build_dataset.py")])

    n = site["namen"]
    prod = []
    for i, p in enumerate(sorted(site["produkte"], key=lambda p: -p["k27"])):
        g = p["ipr"][0]
        prod.append({
            "id": str(i + 1), "epl": p["epl"], "epl_kurz": next(e["kurz"] for e in site["einzelplaene"] if e["code"] == p["epl"]),
            "ab": p["ab"], "ab_name": n["ab"].get(p["ab"], ""), "pg": p["pg"], "pg_name": n["pg"].get(p["pg"], ""),
            "ipr": p["ipr"], "ipr_name": n["ipr"].get(p["ipr"], ""), "gruppe": g, "gruppe_name": n["ipr_gruppen"][g],
            "produkt": p["name"],
            **{f"{a}{y}": p[f"{a}{y}"] for a in ("k", "e") for y in ("24", "25", "27", "28", "29", "30")},
        })
    link_moved_products(prod)
    write(out_dir, "produkte.json", prod, [
        SOURCE_PDF, {"label": "Tabelle", "value": "4 IPR-Produktbericht, bereinigt um Erlöse/Kosten aus haushaltsrelevanten Verrechnungen (S. 16-118)"},
        {"label": "Einheit", "value": "Tsd. EUR"},
        {"label": "Hinweis", "value": "Felder kJJ = Kosten, eJJ = Erlöse des Jahres 20JJ (2024 und 2025 Ist, 2027 und 2028 Plan, 2029 und 2030 Finanzplanung). Der Produktbericht enthält keine Werte für den fortgeschriebenen Plan 2026. Die Gruppen (Spalte gruppe_name) fassen IPR-Produkte nach ihrer ersten Ziffer zusammen; die Gruppennamen sind eigene Bezeichnungen."},
        {"label": "Verschobene Produkte", "value": "Wechselt ein Produkt zum Plan 2027 den Einzelplan oder den Namen, führt der Produktbericht zwei Zeilen: die alte nur mit Ist, die neue nur mit Plan. Die Felder vk24, vk25, ve24, ve25 enthalten das Ist in der Gliederung des Plans 2027: Die neue Zeile übernimmt das Ist der alten, bei mehreren neuen Zeilen anteilig nach den Kosten 2027; die alte Zeile erhält 0. Zuordnung: gleiche IPR-Nummer und gleicher oder fast gleicher Produktname (Ähnlichkeit ab 0,9). wechsel ist 'zugang' oder 'abgang', wechsel_extern ist true bei einem Wechsel des Einzelplans, wechsel_text beschreibt die Zuordnung."},
        code("parse_ipr.py"), code("build_dataset.py")])

    export_details(out_dir, prod)

    nk, st = site["nka_komponenten"], site["steuertrend"]
    fb = []
    for i, jahr in enumerate(nk["jahre"]):
        fb.append({
            "jahr": jahr, "konjunktur": nk["Konjunkturkomponente"][i],
            "finanzielle_transaktionen": nk["Finanzielle Transaktionen"][i],
            "strukturkomponente": nk["Strukturkomponente (StruKomLäG)"][i],
            "steuertrend": st["trend"][i], "steuern": next(e["steuern"] for e in eck if e["jahr"] == jahr),
        })
    write(out_dir, "finanzbericht.json", fb, [
        {"label": "Quelle", "value": "Finanzbericht 2027/2028, Stand August 2026, Tabelle 2 (S. 14) und Tabelle 3 (S. 15)"},
        {"label": "Erfassung", "value": "Konjunktur-, Transaktions- und Strukturkomponente sowie Steuertrend von Hand aus dem PDF übertragen; veranschlagte Steuern aus dem Gesamtergebnisplan."},
        {"label": "Einheit", "value": "Mio. EUR"}, code("build_dataset.py"), code("export_dashboard.py")])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
