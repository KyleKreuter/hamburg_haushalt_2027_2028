"""Parse cost types and key figures per Produktgruppe from an Einzelplan PDF.

For every Produktgruppe the Einzelplan volume has an "Ergebnisplan der Produktgruppe"
(costs by type, Tsd. EUR, 2024-2030 including the updated plan 2026) and usually a table
"Kennzahlen der Produktgruppe" (key figures such as numbers of students).

The Einzelplan of each Produktgruppe comes from the page header ("Einzelplan 3.1 ..."),
so one volume may cover several Einzelpläne.

Usage: python3 -I scripts/parse_epl.py <einzelplan.pdf> <out.json>
"""

import json
import os
import re
import subprocess
import sys

YEARS = ["2024", "2025", "2026", "2027", "2028", "2029", "2030"]
NUM_RE = re.compile(r"(?<!\S)-?\d{1,3}(?:\.\d{3})*(?:,\d+)?(?=\s|$)")
ERG_RE = re.compile(r"<h6>[\d.]+ Ergebnisplan der Produktgruppe (\d{3}\.\d{2}) (.*?)</h6>")
KZ_RE = re.compile(r"<h6>[\d.]+ Kennzahlen der Produktgruppe (\d{3}\.\d{2})")
MAIN_RE = re.compile(r"^\s*(\d{1,2})\.\s+(\S.*?)\s*$")
SUB_RE = re.compile(r"^\s*([a-e])\)\s+(\S.*?)\s*$")
KZ_ROW_RE = re.compile(r"^(\s*)([A-Z]_\d{3}_\d{2}_\d{3})\s+(.*)$")
HEAD_RE = re.compile(r"Ist 2024|Ist 2025|Fortg\. Plan|Plan 2027|Plan 2028|Plan 2029|Plan 2030")

# Row labels of the standard Ergebnisplan, keyed by position.
LABELS = {
    "1": "Erlöse",
    "2": "Kosten aus laufender Verwaltungstätigkeit",
    "2a": "davon Mieten, Pachten und Erbbauzinsen",
    "2b": "davon IT-Kosten",
    "2c": "davon Prüfung, Beratung, Rechtsschutz",
    "3": "Personalkosten",
    "3a": "Entgelte",
    "3b": "Bezüge",
    "3c": "Sonstige Kosten mit Entgelt- oder Bezugscharakter",
    "3d": "Sozialleistungen",
    "3e": "Versorgungsleistungen",
    "4": "Kosten aus Transferleistungen",
    "5": "Kosten aus Abschreibungen",
    "6": "Sonstige Kosten",
    "7": "Ergebnis der laufenden Verwaltungstätigkeit",
    "8": "Erlöse des Finanzergebnisses",
    "9": "Kosten des Finanzergebnisses",
    "10": "Finanzergebnis",
    "11": "Jahresergebnis",
    "12": "Globale Mehrkosten",
    "13": "Globale Minderkosten",
    "14": "Jahresergebnis einschließlich globaler Mehr- und Minderkosten",
}


def pages(pdf):
    out = subprocess.run(["pdftotext", "-layout", pdf, "-"], check=True, capture_output=True)
    return out.stdout.decode("utf-8").split("\f")


def number(tok):
    return float(tok.replace(".", "").replace(",", "."))


def header_centers(lines):
    """Return the centre of each year header cell, or None."""
    for line in lines:
        hits = list(HEAD_RE.finditer(line))
        if len(hits) == 7:
            return [(m.start() + m.end()) / 2 for m in hits]
    return None


def values(line, start, centers):
    """Assign the numbers right of `start` to the nearest year column."""
    vals = [None] * len(centers)
    for m in NUM_RE.finditer(line, start):
        mid = (m.start() + m.end()) / 2
        idx = min(range(len(centers)), key=lambda i: abs(mid - centers[i]))
        if vals[idx] is not None:
            raise ValueError(f"column {YEARS[idx]} assigned twice: {line!r}")
        vals[idx] = number(m.group())
    return vals


def label_end(line):
    """Index after the label text: the first number preceded by two spaces."""
    m = re.search(r"\S\s{2,}-?\d", line)
    return m.start() + 1 if m else len(line)


def parse_ergebnisplan(text):
    lines = text.splitlines()
    centers = header_centers(lines)
    if not centers:
        return None
    rows, main = {}, None
    for line in lines:
        cut = label_end(line)
        label = line[:cut]
        m, s = MAIN_RE.match(label), SUB_RE.match(label)
        if m and m.group(1) in LABELS:
            main = m.group(1)
            key = main
        elif s and main in ("2", "3"):
            key = main + s.group(1)
        else:
            continue
        if key in rows:
            continue
        rows[key] = values(line, cut, centers)
        if key == "14":
            break
    return rows


def parse_kennzahlen(text):
    lines = text.splitlines()
    centers = header_centers(lines)
    if not centers:
        return []
    out, cur = [], None
    for line in lines:
        m = KZ_ROW_RE.match(line)
        if m:
            rest = m.group(3)
            # Name and unit are separated from the numbers by two or more spaces.
            parts = re.split(r"\s{2,}", rest.strip())
            name = parts[0]
            unit = parts[1] if len(parts) > 1 and not NUM_RE.fullmatch(parts[1]) else ""
            start = line.index(unit, len(m.group(1)) + len(m.group(2)) + len(name)) + len(unit) if unit else len(m.group(1)) + len(m.group(2)) + 1 + len(name)
            cur = {"code": m.group(2), "name": name, "einheit": unit, "indent": len(m.group(1)),
                   **dict(zip(YEARS, values(line, start, centers)))}
            out.append(cur)
        elif cur and line.strip() and not NUM_RE.search(line) and len(line) - len(line.lstrip()) >= cur["indent"] - 2:
            cur["name"] += " " + line.strip()
        else:
            cur = None
    for k in out:
        k.pop("indent")
        k["name"] = re.sub(r"\s+", " ", k["name"]).replace("- ", "-") if k["name"].endswith("-") else re.sub(r"\s+", " ", k["name"])
    return out


PROD_RE = re.compile(r"^\s*(\S.*?)\s{2,}(\d{3}|INT)\s*$")
KE_RE = re.compile(r"^\s*(Erlöse|Kosten)(?=\s|$)")
SALDO_RE = re.compile(r"^\s*Saldo Jahresergebnis ([12])")
END_RE = re.compile(r"<h6>[\d.]+ (?!Kosten und Erlöse)")


def parse_produkte(texts):
    """Parse 'Kosten und Erlöse der Produktgruppe' over one or more pages.

    Per product: e1/k1 = revenue and costs of Jahresergebnis 1 (direct), e2/k2 = revenue and
    costs added in Jahresergebnis 2 (allocation of the authority's internal services).
    """
    out, cur, stage, centers = [], None, 0, None
    for text in texts:
        for line in text.splitlines():
            if END_RE.search(line):
                return out
            c = header_centers([line])
            if c:
                centers = c
                continue
            if centers is None:
                continue
            s = SALDO_RE.match(line)
            if s:
                stage = 2 if s.group(1) == "1" else 0
                continue
            k = KE_RE.match(line)
            if k and cur is not None and stage:
                key = ("e" if k.group(1) == "Erlöse" else "k") + str(stage)
                cur[key] = values(line, k.end(), centers)
                continue
            p = PROD_RE.match(line)
            if p and not NUM_RE.search(p.group(1)):
                cur = {"produkt": p.group(1).strip(), "ipr": p.group(2)}
                out.append(cur)
                stage = 1
    return out


PAGE_EPL_RE = re.compile(r"Einzelplan\s+(\d+(?:\.\d+)?)\s")


def page_epl(text):
    """Return the Einzelplan code from the page header, or None."""
    for line in text.splitlines()[:6]:
        m = PAGE_EPL_RE.search(line)
        if m:
            return m.group(1)
    return None


def main(pdf, out_path):
    pg_pages = pages(pdf)
    result = {"quelle": os.path.basename(pdf), "produktgruppen": []}
    for i, text in enumerate(pg_pages):
        for m in ERG_RE.finditer(text):
            pg, name = m.group(1), m.group(2).strip()
            rows = parse_ergebnisplan(text[m.end():]) or None
            nxt = pg_pages[i + 1] if i + 1 < len(pg_pages) else ""
            if rows is None and "<h6>" not in nxt.split("Tsd. EUR")[0]:
                # The table starts on the next page when the heading sits at the bottom.
                rows = parse_ergebnisplan(nxt) or None
            produkte = []
            # The product table and key figures follow before the next Produktgruppe.
            stop = next((j for j in range(i + 1, len(pg_pages)) if ERG_RE.search(pg_pages[j])), len(pg_pages))
            for j in range(i, stop):
                h = re.search(r"<h6>[\d.]+ Kosten und Erlöse der Produktgruppe " + re.escape(pg), pg_pages[j])
                if h:
                    produkte = parse_produkte([pg_pages[j][h.end():], *pg_pages[j + 1:j + 8]])
                    break
            kz = []
            for j in range(i, stop):
                k = KZ_RE.search(pg_pages[j])
                if k and k.group(1) == pg:
                    kz = parse_kennzahlen(pg_pages[j][k.end():])
                    break
            result["produktgruppen"].append({"epl": page_epl(text), "pg": pg, "name": name, "seite": i + 1, "ergebnisplan": rows, "produkte": produkte, "kennzahlen": kz})
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"{out_path}: {len(result['produktgruppen'])} Produktgruppen")


if __name__ == "__main__":
    main(*sys.argv[1:3])
