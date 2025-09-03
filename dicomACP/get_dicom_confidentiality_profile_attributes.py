#!/usr/bin/env python3
"""
Extract DICOM PS3.15 Annex E, Table E.1-1 (Attribute Confidentiality Profiles) to CSV.

- Preserves ALL columns (including multi-row headers).
- Auto-detects how many header rows the table uses.
- Optionally flattens multi-row headers for tools that prefer single-row CSV headers.
- Can also write Excel (.xlsx) (untested - beware of type conversions with tag numbers)

Usage:
  python annexE_table_e1_1_to_csv.py --out E1-1.csv          # CSV with flattened headers (default)
  python annexE_table_e1_1_to_csv.py --no-flatten --xlsx     # CSV + XLSX, keep multi-row header
  python annexE_table_e1_1_to_csv.py -h                      # help
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://dicom.nema.org/medical/dicom/current/output/chtml/part15/chapter_E.html#table_E.1-1"


def _flatten_columns(cols: pd.MultiIndex | pd.Index) -> list[str]:
    """
    Flatten a (possibly) multi-level columns object to single strings,
    removing 'Unnamed: level X' placeholders and collapsing whitespace.
    """
    def clean_token(tok: str) -> str:
        s = " ".join(str(tok).split())
        return "" if s.startswith("Unnamed: level") else s

    out: list[str] = []
    if isinstance(cols, pd.MultiIndex):
        for tup in cols:
            tokens = [clean_token(t) for t in tup]
            tokens = [t for t in tokens if t]  # drop empty placeholders
            out.append(" / ".join(tokens) if tokens else "")
    else:
        out = [" ".join(str(c).split()) for c in cols]
    return out


def _strip_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace in all string-like cells (without dropping columns)."""
    return df.applymap(lambda x: " ".join(str(x).split()) if pd.notna(x) else "")


def _find_table_soup(html: str) -> str:
    """
    Find the HTML for Table E.1-1 precisely, falling back to the first table
    that contains a 'Tag' and 'Attribute Name' column if the id is missing.
    """
    soup = BeautifulSoup(html, "lxml")
    # Primary: a table with id or a caption that includes 'Table E.1-1'
    tbl = soup.find("table", {"id": "table_E.1-1"})
    if tbl is None:
        # Some builds label the caption instead of the table id
        for candidate in soup.find_all("table"):
            cap = candidate.find("caption")
            if cap and "Table E.1-1" in cap.get_text(" ", strip=True):
                tbl = candidate
                break
    if tbl is None:
        # Heuristic fallback: first table that has 'Tag' & 'Attribute Name' somewhere
        for candidate in soup.find_all("table"):
            text = candidate.get_text(" ", strip=True)
            if "Tag" in text and "Attribute Name" in text:
                tbl = candidate
                break
    if tbl is None:
        raise RuntimeError("Could not locate Table E.1-1 in the HTML.")
    return str(tbl)


def _detect_header_rows(tbl_html: str) -> list[int]:
    """
    Count header rows based on <thead><tr>…</tr></thead>.
    If no THEAD, fall back to single header row.
    """
    soup = BeautifulSoup(tbl_html, "lxml")
    thead = soup.find("thead")
    if thead:
        n = len(thead.find_all("tr"))
        if n >= 2:
            return list(range(n))  # e.g., [0,1] or [0,1,2]
    return [0]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Convert DICOM PS3.15 Annex E Table E.1-1 to CSV/XLSX (all columns preserved)."
    )
    ap.add_argument(
        "-o",
        "--out",
        default="dicom_annexE_table_E1-1.csv",
        help="Output CSV path (default: %(default)s)",
    )
    ap.add_argument(
        "--no-flatten",
        action="store_true",
        help="Keep multi-row header in CSV (MultiIndex). Default flattens to one row.",
    )
    ap.add_argument(
        "--xlsx",
        action="store_true",
        help="Also write an Excel file next to the CSV with the same base name.",
    )
    if len(sys.argv) == 1:
        ap.print_help()
        sys.exit(2)
    args = ap.parse_args()

    # Download the page
    resp = requests.get(URL, timeout=60)
    resp.raise_for_status()
    html = resp.text

    # Isolate the exact table HTML
    table_html = _find_table_soup(html)

    # Work out how many header rows exist and read with that
    header_rows = _detect_header_rows(table_html)
    # pandas will build a MultiIndex when header has multiple rows
    dfs = pd.read_html(table_html, flavor="bs4", header=header_rows)
    if not dfs:
        raise RuntimeError("pandas.read_html returned no tables from the selected HTML.")
    df = dfs[0]

    # Clean cell whitespace, preserve every column
    df = _strip_frame(df)

    # Optionally flatten multirow headers to a single header line
    if not args.no_flatten:
        df.columns = _flatten_columns(df.columns)

    # Write CSV
    out_csv = Path(args.out)
    df.to_csv(out_csv, index=False)

    # Optionally write XLSX
    if args.xlsx:
        out_xlsx = out_csv.with_suffix(".xlsx")
        with pd.ExcelWriter(out_xlsx, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="AnnexE_Table_E1-1")

    print(f"Wrote CSV: {out_csv.resolve()}")
    if args.xlsx:
        print(f"Wrote XLSX: {out_xlsx.resolve()}")


if __name__ == "__main__":
    main()

