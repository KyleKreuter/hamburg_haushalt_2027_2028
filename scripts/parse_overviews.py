"""Parse the overall plans and the per-Einzelplan overviews of the Gesamthaushalt PDF.

Usage: python3 -I scripts/parse_overviews.py <gesamthaushalt.pdf> <out_dir>
"""

import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hhparse import NUM_RE, numbers_by_column, page_text, unit_columns  # noqa: E402

YEARS_7 = ["ist_2024", "ist_2025", "fplan_2026", "plan_2027", "plan_2028", "plan_2029", "plan_2030"]
ROW_START = re.compile(r"^\s*(\d+\.(?=\s)|[a-e]\)|davon\b)")


def parse_total_plan(pdf, pages):
    """Parse Gesamtergebnisplan or Gesamtfinanzplan rows (values in Mio. EUR)."""
    rows, seen = [], set()
    for page in pages:
        lines = page_text(pdf, page).splitlines()
        col_ends, unit = unit_columns(lines)
        if not col_ends:
            continue
        assert unit == "Mio." and len(col_ends) == 7, (page, col_ends)
        num_start = col_ends[0] - 10
        current = None
        for line in lines:
            if UNIT_SKIP(line):
                continue
            first = NUM_RE.search(line, num_start)
            label_part = line[: first.start() if first else len(line)].strip()
            values = numbers_by_column(line[num_start:], num_start, col_ends)
            has_values = any(v is not None for v in values)
            if ROW_START.match(line):
                pos = ROW_START.match(line).group(1)
                current = {"label": label_part, "values": values, "pos": pos}
                rows.append(current)
            elif current is not None and label_part and not has_values and not re.match(r"^\d+$", label_part):
                current["label"] += " " + label_part
            else:
                current = None
    out, parent = [], None
    for r in rows:
        level = 0 if re.match(r"\d+\.", r["pos"]) else 1
        label = re.sub(r"\s+", " ", r["label"].replace("\u2013", "-")).strip()
        key = label
        if level == 0:
            parent = label
            if key in seen:
                continue
            seen.add(key)
        out.append({"ebene": level, "oberposition": "" if level == 0 else parent, "position": label,
                    **dict(zip(YEARS_7, r["values"]))})
    return out


def UNIT_SKIP(line):
    s = line.strip()
    return (not s or "EUR" in s or s.startswith("Ist 2024") or s == "2026"
            or s.startswith("<h") or "Gesamthaushalt der Freien" in s)


EPL_LINE = re.compile(r"^\s*(\d(?:\.\d{1,2})?|Gesamtsumme)\s{2,}(\S.*?)?(?=\s{2,}-?\d|\s*$)")


def parse_epl_table(pdf, page):
    """Parse one per-Einzelplan overview page: two measures x three years (Tsd. EUR)."""
    lines = page_text(pdf, page).splitlines()
    col_ends, unit = unit_columns(lines)
    assert unit == "Tsd." and len(col_ends) == 6, (page, col_ends)
    # The two measure titles sit above the columns; take the text lines between
    # the section title and the "Einzelplan" header.
    header_idx = next(i for i, l in enumerate(lines) if l.strip() == "Einzelplan" or l.strip().startswith("Einzelplan"))
    mid = (col_ends[2] + col_ends[3]) // 2
    left, right = [], []
    for l in lines[:header_idx]:
        s = l.strip()
        if not s or s.startswith("<h") or "Gesamthaushalt der" in s or re.match(r"^\d(\.\d)? ", s):
            continue
        for m in re.finditer(r"\S+(?: \S+)*", l):
            (left if m.start() < mid - 10 else right).append(m.group())
    measures = [" ".join(left), " ".join(right)]
    num_start = col_ends[0] - 14
    rows = []
    for line in lines:
        m = EPL_LINE.match(line)
        if not m:
            continue
        code = m.group(1)
        name = line[m.end(1):num_start].strip()
        values = numbers_by_column(line[num_start:], num_start, col_ends)
        rows.append((code, name, values))
    return measures, rows


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main(pdf, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    write_csv(os.path.join(out_dir, "gesamtergebnisplan.csv"), parse_total_plan(pdf, range(4, 8)))
    write_csv(os.path.join(out_dir, "gesamtfinanzplan.csv"), parse_total_plan(pdf, range(8, 10)))

    # The investment overview has a three-level header; name its measures explicitly.
    measure_override = {
        15: ["Investitionen Einzahlungen", "Investitionen Auszahlungen"],
        16: ["Darlehen Einzahlungen", "Darlehen Auszahlungen"],
    }
    long_rows = []
    for name, pages in (("epl_ergebnis", range(10, 15)), ("epl_investitionen", range(15, 17))):
        rows_out = []
        for page in pages:
            measures, rows = parse_epl_table(pdf, page)
            measures = measure_override.get(page, measures)
            for code, epl_name, values in rows:
                for mi, measure in enumerate(measures):
                    for yi, year in enumerate(["fplan_2026", "plan_2027", "plan_2028"]):
                        rows_out.append({"epl": code, "epl_name": epl_name, "kategorie": measure,
                                         "jahr": year, "tsd_eur": values[mi * 3 + yi]})
        write_csv(os.path.join(out_dir, f"{name}.csv"), rows_out)
        long_rows += rows_out
    print("ok")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
