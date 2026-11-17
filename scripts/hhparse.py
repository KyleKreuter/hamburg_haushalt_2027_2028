"""Shared helpers for parsing pdftotext -layout output of the Hamburg budget PDFs."""

import re
import subprocess
from collections import Counter

NUM_RE = re.compile(r"(?<!\S)-?\d{1,3}(?:\.\d{3})*(?:,\d+)?(?=\s|$)")
UNIT_RE = re.compile(r"(Tsd\.|Mio\.) EUR")


def page_text(pdf_path, page):
    """Return the layout text of one PDF page."""
    out = subprocess.run(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), pdf_path, "-"],
        check=True,
        capture_output=True,
    )
    return out.stdout.decode("utf-8")


def parse_number(token):
    """Convert a German formatted number like '-1.234,5' to float."""
    return float(token.replace(".", "").replace(",", "."))


def unit_columns(lines):
    """Return the right edge of every 'Tsd. EUR'/'Mio. EUR' header cell and the unit."""
    for line in lines:
        hits = list(UNIT_RE.finditer(line))
        if len(hits) >= 3:
            return [m.end() for m in hits], hits[0].group(1)
    return None, None


def numbers_by_column(segment, offset, col_ends, tolerance=6):
    """Assign right-aligned numbers in a line segment to the nearest column.

    Returns a list with one value (or None) per column. Raises ValueError when a
    number cannot be assigned unambiguously.
    """
    values = [None] * len(col_ends)
    for m in NUM_RE.finditer(segment):
        end = offset + m.end()
        dist = [abs(end - c) for c in col_ends]
        idx = min(range(len(col_ends)), key=dist.__getitem__)
        if dist[idx] > tolerance:
            raise ValueError(f"number {m.group()!r} at {end} matches no column {col_ends}")
        if values[idx] is not None:
            raise ValueError(f"column {idx} assigned twice in {segment!r}")
        values[idx] = parse_number(m.group())
    return values


def mode(values, default=None):
    counts = Counter(values)
    return counts.most_common(1)[0][0] if counts else default
