"""Parse the IPR-Produktbericht (section 4) of the Gesamthaushalt PDF.

Each product has an "Erlöse" and a "Kosten" line with values for seven years in
Tsd. EUR. Names of Aufgabenbereich, Produktgruppe and Produkt wrap onto
following lines; the parser slices each line by column positions learned per page.

Usage: python3 -I scripts/parse_ipr.py <gesamthaushalt.pdf> <first_page> <last_page> <out_dir>
"""

import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hhparse import numbers_by_column, page_text, unit_columns, mode  # noqa: E402

YEARS = ["ist_2024", "ist_2025", "fplan_2026", "plan_2027", "plan_2028", "plan_2029", "plan_2030"]
LABEL_RE = re.compile(r"(?<=\s)(Erlöse|Kosten)(?=\s|$)")
PG_RE = re.compile(r"(?<!\S)(\d{3}\.\d{2})(?=\s)")
AB_RE = re.compile(r"^\s*(\d{3})\s{2,}")
EPL_RE = re.compile(r"^\s*(\d(?:\.\d{1,2})?)\s+(\S.*)$")
IPR_RE = re.compile(r"^\s*IPR-Produkt\s+(\d+)\s+(.*\S)\s*$")
CHUNK_RE = re.compile(r"\S+(?: \S+)*")
LABEL_TOL = 12
TAIL_RE = re.compile(r"^[\s\d.,-]*$")


def word_start(line, x):
    """Move a split position left so it does not cut a word in half."""
    x = min(x, len(line))
    while 0 < x < len(line) and line[x - 1] != " " and line[x] != " ":
        x -= 1
    return x


def split3(line, pg_x, prod_x, end):
    """Split a line into Aufgabenbereich, Produktgruppe and Produkt segments."""
    a = word_start(line, pg_x)
    b = max(word_start(line, prod_x), a)
    return line[:a], line[a:b], line[b:end]


def find_label(line):
    """Return the Erlöse/Kosten label after which only numbers follow, or None."""
    hits = [m for m in LABEL_RE.finditer(line) if TAIL_RE.match(line[m.end():])]
    return hits[-1] if hits else None


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def page_geometry(lines):
    """Learn label, Produktgruppe and Produkt column positions of one page."""
    label_pos = [m.start() for m in map(find_label, lines) if m]
    if not label_pos:
        return None
    label_x = mode(label_pos)
    pg_pos, prod_pos = [], []
    for l in lines:
        m = find_label(l)
        if not m or abs(m.start() - label_x) > LABEL_TOL:
            continue
        pg_pos += [p.start() for p in PG_RE.finditer(l[:m.start()])]
    pg_x = mode(pg_pos)
    if pg_x is not None:
        for l in lines:
            m = find_label(l)
            if not m or abs(m.start() - label_x) > LABEL_TOL:
                continue
            prod_pos += [c.start() for c in CHUNK_RE.finditer(l[:m.start()]) if c.start() > pg_x + 9]
    prod_x = mode(prod_pos)
    return label_x, pg_x, prod_x


def main(pdf, first, last, out_dir):
    rows, sums, problems, problems_fixed = [], [], [], []
    ipr = {"code": None, "name": None}
    epl = ab = pg = prod = None
    in_summe = None
    geometry = None
    for page in range(first, last + 1):
        lines = page_text(pdf, page).splitlines()
        col_ends, unit = unit_columns(lines)
        if not col_ends:
            problems.append((page, "no unit header"))
            continue
        assert unit == "Tsd." and len(col_ends) == 7, (page, col_ends)
        geo = page_geometry(lines)
        if geo is None:
            continue
        label_x, pg_x, prod_x = geo
        # Fall back to the previous page's columns when this page has no own anchors.
        if pg_x is None or prod_x is None:
            # Pages holding only sums or a single continued line carry no anchors.
            # Their label lines have no name text, so any split position works.
            pg_x = pg_x if pg_x is not None else label_x
            prod_x = prod_x if prod_x is not None else label_x
            for l in lines:
                m = find_label(l)
                if m and l[:m.start()].strip() and not l.strip().startswith("Summe"):
                    problems.append((page, f"name text on page without anchors: {l.strip()[:80]}"))
        header_seen = False
        for line in lines:
            s = line.strip()
            if not s:
                continue
            if not header_seen:
                if "Tsd. EUR" in line:
                    header_seen = True
                m = IPR_RE.match(line)
                if m:
                    ipr = {"code": m.group(1), "name": m.group(2)}
                continue
            if re.fullmatch(r"\d+", s):
                continue  # page number
            m = IPR_RE.match(line)
            if m:
                ipr = {"code": m.group(1), "name": m.group(2)}
                continue
            lab = find_label(line)
            if lab and abs(lab.start() - label_x) <= LABEL_TOL:
                kind = lab.group(1)
                values = numbers_by_column(line[lab.end():], lab.end(), col_ends)
                prefix = line[:lab.start()].ljust(prod_x)
                if prefix.strip().startswith("Summe") or (in_summe and kind == "Kosten" and not prefix.strip()):
                    sums.append({"ipr": ipr["code"], "art": kind, **dict(zip(YEARS, values))})
                    in_summe = kind == "Erlöse"
                    continue
                in_summe = None
                ab_seg, pg_seg, prod_seg = split3(prefix, pg_x, prod_x, len(prefix))
                if kind == "Erlöse":
                    am = AB_RE.match(ab_seg)
                    if am:
                        ab = {"code": am.group(1), "name": ab_seg[am.end():]}
                    elif ab_seg.strip() and ab is not None:
                        ab["name"] += " " + ab_seg
                    pm = PG_RE.match(pg_seg.lstrip())
                    if pm:
                        pg = {"code": pm.group(1), "name": pg_seg.lstrip()[len(pm.group(1)):]}
                    elif pg_seg.strip() and pg is not None:
                        pg["name"] += " " + pg_seg
                    prod = {"name": prod_seg, "ipr": dict(ipr), "epl": epl, "ab": ab, "pg": pg}
                else:
                    if prod is None:
                        problems.append((page, f"Kosten line without product: {s[:80]}"))
                        continue
                    for ent, seg in ((ab, ab_seg), (pg, pg_seg), (prod, prod_seg)):
                        if seg.strip() and ent is not None:
                            ent["name"] += " " + seg
                rows.append((prod, kind, values))
                continue
            # Lines without a label: values that slipped below an empty Erlöse line,
            # Einzelplan headers, or wrapped name parts.
            if rows and rows[-1][1] == "Erlöse" and all(v is None for v in rows[-1][2]) and not rows[-1][0]["name"].strip():
                zone = col_ends[0] - 12
                vals = numbers_by_column(line[zone:], zone, col_ends)
                if any(v is not None for v in vals):
                    rows[-1] = (rows[-1][0], "Erlöse", vals)
                    rows[-1][0]["name"] = line[word_start(line, prod_x):zone]
                    problems_fixed.append((page, s[:60]))
                    continue
            em = EPL_RE.match(line)
            if em and len(line) - len(line.lstrip()) < pg_x and not AB_RE.match(line):
                epl = em.group(1)
                continue
            if prod is not None:
                for ent, seg in zip((ab, pg, prod), split3(line, pg_x, prod_x, label_x)):
                    if seg.strip() and ent is not None:
                        ent["name"] += " " + seg
            else:
                problems.append((page, f"unassigned line: {s[:80]}"))

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "ipr_produkte.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ipr_code", "ipr_name", "epl", "ab_code", "ab_name", "pg_code", "pg_name", "produkt", "art", *YEARS])
        for prod, kind, values in rows:
            w.writerow([prod["ipr"]["code"], clean(prod["ipr"]["name"]), prod["epl"],
                        prod["ab"]["code"] if prod["ab"] else "", clean(prod["ab"]["name"]) if prod["ab"] else "",
                        prod["pg"]["code"] if prod["pg"] else "", clean(prod["pg"]["name"]) if prod["pg"] else "",
                        clean(prod["name"]), kind, *values])
    with open(os.path.join(out_dir, "ipr_summen.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ipr", "art", *YEARS])
        w.writeheader()
        w.writerows(sums)
    for p in problems:
        print("PROBLEM", p)
    for p in problems_fixed:
        print("FIXED slipped Erlöse values", p)
    for prod, kind, _ in rows:
        if kind == "Erlöse" and not clean(prod["name"]):
            print("PROBLEM product without name", prod["ipr"]["code"], prod["pg"] and prod["pg"]["code"])
    print(f"{len(rows)} rows, {len(sums)} sums, {len(problems)} problems")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
