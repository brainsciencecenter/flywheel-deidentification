#!/usr/bin/env python3
"""
Apply a Flywheel DICOM de-identification profile from YAML.

If replace-with: '' in YAML, this script sets the element to an EMPTY VALUE
  appropriate for its VR (zero-length), instead of deleting it.

Empty value policy by VR:
- Text-like (PN, LO, SH, ST, LT, UC, UT, AE, CS, DA, TM, AS, DS, IS, UI, UR): ""
- Integer (US, SS, UL, SL, SV, UV): []
- Float (FL, FD): []
- Binary large numeric (OF, OD, OL): b""
- Binary (OB, OW, UN): b""
- Sequence (SQ): []
- Attribute Tag (AT): []

This may be overkill because pydicom does much of this automatically.

The default values do not guarantee compliance, for example some integer fields might be required to be non-empty.

By default, the script emulates Flywheel's behavior of creating any missing fields as empty elements.

Usage:
  python deid_apply_yaml.py PROFILE.yaml INPUT_PATH [-o OUTDIR | --inplace] [--add-missing] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import yaml
from pydicom import dcmread
from pydicom.dataset import Dataset
from pydicom.dataelem import DataElement
from pydicom.datadict import tag_for_keyword, dictionary_VR
from pydicom.tag import BaseTag
from pydicom.errors import InvalidDicomError


TEXT_VRS = {
    "PN", "LO", "SH", "ST", "LT", "UC", "UT", "AE", "CS", "DA", "TM", "AS", "DS", "IS", "UI", "UR"
}
INT_VRS = {"US", "SS", "UL", "SL", "SV", "UV"}
FLOAT_VRS = {"FL", "FD"}
BIN_VRS_BYTES = {"OB", "OW", "UN"}  # zero-length bytes
BIN_NUM_VRS_BYTES = {"OF", "OD", "OL"}  # numeric/binary, zero-length bytes
SEQ_VRS = {"SQ"}
TAG_VRS = {"AT"}


@dataclass
class Profile:
    compute_age: bool
    age_units: str | None  # 'Y', 'M', 'D', or None for AUTO
    fields: list[dict[str, Any]]

    @classmethod
    def from_yaml(cls, path: Path) -> "Profile":
        data = yaml.safe_load(Path(path).read_text())
        dicom = data.get("dicom", {}) or {}
        compute_age = bool(dicom.get("patient-age-from-birthdate", False))
        units = dicom.get("patient-age-units")
        if isinstance(units, str):
            units = units.strip().upper()
            if units not in {"Y", "M", "D"}:
                units = None
        else:
            units = None
        fields = dicom.get("fields") or []
        if not isinstance(fields, list):
            raise ValueError("dicom.fields must be a list")
        return cls(compute_age=compute_age, age_units=units, fields=fields)


def iter_paths(root: Path, recursive: bool = True) -> Iterable[Path]:
    if root.is_file():
        yield root
    elif root.is_dir():
        if recursive:
            yield from (p for p in root.rglob("*") if p.is_file())
        else:
            yield from (p for p in root.iterdir() if p.is_file())


def parse_da(da: str | None) -> date | None:
    if not da:
        return None
    s = str(da).strip()
    if len(s) != 8 or not s.isdigit():
        return None
    try:
        return date(int(s[0:4]), int(s[4:6]), int(s[6:8]))
    except ValueError:
        return None


def choose_reference_date(ds: Dataset) -> date | None:
    for kw in ("StudyDate", "SeriesDate", "AcquisitionDate", "ContentDate", "InstanceCreationDate"):
        d = parse_da(getattr(ds, kw, None))
        if d:
            return d
    return None


def ymd_diff(born: date, ref: date) -> tuple[int, int, int]:
    if ref < born:
        return (0, 0, 0)
    years = ref.year - born.year - ((ref.month, ref.day) < (born.month, born.day))
    months = (ref.year - born.year) * 12 + (ref.month - born.month) - (1 if ref.day < born.day else 0)
    days = (ref - born).days
    return years, months, days


def format_patient_age(value: int, unit: str) -> str:
    unit = unit.upper()
    if unit not in {"Y", "M", "D"}:
        raise ValueError("unit must be 'Y', 'M', or 'D'")
    v = max(0, min(999, int(value)))
    return f"{v:03d}{unit}"


def compute_patient_age_value(ds: Dataset, pref_unit: str | None) -> str | None:
    dob = parse_da(getattr(ds, "PatientBirthDate", None))
    ref = choose_reference_date(ds)
    if not dob or not ref:
        return None
    y, m, d = ymd_diff(dob, ref)
    if pref_unit in {"Y", "M", "D"}:
        unit = pref_unit
    else:
        unit = "D" if d < 1000 else ("M" if m < 1000 else "Y")
    value = {"Y": y, "M": m, "D": d}[unit]
    return format_patient_age(value, unit)


def empty_value_for_vr(vr: str) -> Any:
    vr = vr.upper()
    if vr in TEXT_VRS:
        return ""
    if vr in INT_VRS:
        return []
    if vr in FLOAT_VRS:
        return []
    if vr in BIN_NUM_VRS_BYTES:
        return b""
    if vr in BIN_VRS_BYTES:
        return b""
    if vr in SEQ_VRS:
        return []
    if vr in TAG_VRS:
        return []
    # Fallback: safest is zero-length string
    return ""


def set_empty_element(ds: Dataset, tag: BaseTag, vr: str, add_missing: bool) -> str:
    if tag in ds:
        empty_val = empty_value_for_vr(vr)
        ds[tag].value = empty_val
        return "emptied"
    if add_missing:
        empty_val = empty_value_for_vr(vr)
        ds.add(DataElement(tag, vr, empty_val))
        return "added-empty"
    return "missing"


def apply_field(ds: Dataset, name: str, replacement: Any, add_missing: bool) -> str:
    tag = tag_for_keyword(name)
    if tag is None:
        return f"skipped (unknown keyword '{name}')"
    vr = dictionary_VR(tag)
    if vr is None:
        # If VR unknown, try to infer from existing element; else fall back to text empty
        if tag in ds and ds[tag].VR:
            vr = ds[tag].VR
        else:
            vr = "LO"
    if replacement == "":
        return set_empty_element(ds, tag, vr, add_missing)
    try:
        setattr(ds, name, replacement)
        return "set"
    except Exception:
        try:
            ds[tag] = replacement  # type: ignore[assignment]
            return "set"
        except Exception:
            return "skipped (set failed)"


def process_dataset(ds: Dataset, profile: Profile, add_missing: bool) -> list[str]:
    actions: list[str] = []

    if profile.compute_age:
        age_val = compute_patient_age_value(ds, profile.age_units)
        if age_val:
            setattr(ds, "PatientAge", age_val)
            actions.append(f"PatientAge={age_val}")
        else:
            actions.append("PatientAge not set (missing DOB or reference date)")

    for entry in profile.fields:
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        replacement = entry.get("replace-with", "")
        status = apply_field(ds, name, replacement, add_missing=add_missing)
        if replacement == "":
            actions.append(f"{name}: {status}")
        else:
            actions.append(f"{name}: {status} -> {replacement!r}")
    return actions


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Apply a DICOM de-identification YAML profile (blank → VR-consistent empty)."
    )
    ap.add_argument("profile", help="Path to YAML profile (with dicom.fields etc.)")
    ap.add_argument("input", help="DICOM file or directory")
    ap.add_argument("-o", "--outdir", help="Write outputs to this directory (preserve filenames)")
    ap.add_argument("--inplace", action="store_true", help="Modify files in place (cannot be combined with --outdir)")
    ap.add_argument("--no-recursive", action="store_true", help="Do not recurse into subdirectories")
    ap.add_argument("--dry-run", action="store_true", help="Analyze and print actions without writing")
    ap.add_argument("--no-add-missing", action="store_true", help="If a field is absent, do not add it as an empty element. "
                    "The default is to add missing fields as empty elements, because that's what Flywheel does.")
    ap.add_argument("-v", "--verbose", action="store_true", help="Print detailed per-field actions")
    if len(sys.argv) == 1:
        ap.print_help()
        sys.exit(2)
    args = ap.parse_args()

    verbose = args.verbose

    add_missing = not args.no_add_missing

    if args.dry_run:
        verbose = True

    profile = Profile.from_yaml(Path(args.profile))

    input_path = Path(args.input)
    if args.inplace and args.outdir:
        print("Error: --inplace cannot be used with --outdir", file=sys.stderr)
        sys.exit(2)
    outdir = Path(args.outdir) if args.outdir else None
    if outdir and not outdir.exists():
        outdir.mkdir(parents=True, exist_ok=True)

    total = 0
    edited = 0
    for p in iter_paths(input_path, recursive=not args.no_recursive):
        total += 1
        try:
            ds = dcmread(p, force=True)
        except InvalidDicomError:
            continue
        actions = process_dataset(ds, profile, add_missing=add_missing)
        if not args.dry_run:
            if args.inplace:
                ds.save_as(p, write_like_original=True)
            else:
                target = (outdir / p.name) if outdir else p.with_suffix(".deid.dcm")
                ds.save_as(target, write_like_original=True)
        edited += 1
        print(f"[OK] {p}")
        if verbose:
            for a in actions:
                print(f"  - {a}")

    if edited == 0:
        print("No DICOM files processed (nothing matched).", file=sys.stderr)
    else:
        where = "in place" if args.inplace else (f"to {outdir}" if outdir else "to *.deid.dcm")
        print(f"\nProcessed {edited}/{total} file(s); wrote {where}.")


if __name__ == "__main__":
    main()

