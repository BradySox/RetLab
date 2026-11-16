"""Measure an airframe's fuel burn from Tacview recordings, for a ``fuel:`` block.

Reads the player jet's FuelWeight from one or more .acmi files, cuts each flight
into one-minute slices, sorts the slices by phase and prints pooled rates:

    python tools/tacview_fuel_rates.py --pilot Flash --type F-4E <file.acmi> ...

Phases: ground (lb per minute), climb, cruise (15,000 ft and up, level),
low (under 3,000 ft AGL, over 300 KIAS, level) and combat (everything else
airborne), in pounds per nautical mile. Slices where fuel rises (a tanker) or
drops faster than 1,500 lb a minute (tanks jettisoned) are left out.
Stdlib only. See docs/modding/fuel-consumption-measurement.md.
"""

from __future__ import annotations

import argparse
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

KG_TO_LBS = 2.20462
M_TO_FT = 3.28084
MS_TO_KT = 1.94384
SLICE_SECONDS = 60.0


@dataclass
class Slice:
    seconds: float
    burn_lbs: float
    miles: float
    climb_fpm: float
    agl_ft: float
    ias_kt: float
    alt_ft: float


def _read(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            raw = archive.read(archive.namelist()[0])
    except zipfile.BadZipFile:
        raw = path.read_bytes()
    return raw.decode("utf-8-sig", "replace")


def _find_object(text: str, pilot: str, type_filter: str) -> Optional[str]:
    for line in text.splitlines():
        if f"Pilot={pilot}" in line and type_filter in line and "," in line:
            return line.split(",", 1)[0]
    return None


def _samples(text: str, oid: str) -> Iterator[tuple[float, dict[str, float]]]:
    ref_lon = ref_lat = 0.0
    now = 0.0
    state: dict[str, float] = {}
    for line in text.splitlines():
        if line.startswith("0,ReferenceLongitude="):
            ref_lon = float(line.split("=", 1)[1])
        elif line.startswith("0,ReferenceLatitude="):
            ref_lat = float(line.split("=", 1)[1])
        elif line.startswith("#"):
            try:
                now = float(line[1:])
            except ValueError:
                pass
        elif line.startswith("-" + oid):
            return
        elif line.startswith(oid + ","):
            for field in line.split(",")[1:]:
                key, _, value = field.partition("=")
                if key == "T":
                    parts = value.split("|")
                    if parts[0]:
                        state["lon"] = ref_lon + float(parts[0])
                    if len(parts) > 1 and parts[1]:
                        state["lat"] = ref_lat + float(parts[1])
                    if len(parts) > 2 and parts[2]:
                        state["alt"] = float(parts[2])
                elif key in ("FuelWeight", "IAS", "AGL"):
                    try:
                        state[key] = float(value)
                    except ValueError:
                        pass
            if "FuelWeight" in state and "lat" in state and "alt" in state:
                yield now, dict(state)


def _miles(a: dict[str, float], b: dict[str, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 3440.065 * math.asin(min(1.0, math.sqrt(h)))


def slices(text: str, oid: str) -> list[Slice]:
    picked: list[tuple[float, dict[str, float]]] = []
    for now, state in _samples(text, oid):
        if not picked or now - picked[-1][0] >= SLICE_SECONDS:
            picked.append((now, state))
    out = []
    for (t0, a), (t1, b) in zip(picked, picked[1:]):
        seconds = t1 - t0
        if seconds <= 0 or seconds > 2 * SLICE_SECONDS:
            continue
        out.append(
            Slice(
                seconds=seconds,
                burn_lbs=(a["FuelWeight"] - b["FuelWeight"]) * KG_TO_LBS,
                miles=_miles(a, b),
                climb_fpm=(b["alt"] - a["alt"]) * M_TO_FT / seconds * 60,
                agl_ft=min(a.get("AGL", 1e9), b.get("AGL", 1e9)) * M_TO_FT,
                ias_kt=(a.get("IAS", 0) + b.get("IAS", 0)) / 2 * MS_TO_KT,
                alt_ft=(a["alt"] + b["alt"]) / 2 * M_TO_FT,
            )
        )
    return out


def phase(s: Slice) -> Optional[str]:
    if s.burn_lbs < 0 or s.burn_lbs / s.seconds * 60 > 1500:
        return None
    if s.agl_ft < 40:
        return "ground" if s.ias_kt < 60 else None
    if s.climb_fpm > 1500 and s.alt_ft < 30000:
        return "climb"
    if s.alt_ft > 15000 and abs(s.climb_fpm) < 500 and s.ias_kt > 200:
        return "cruise"
    if s.agl_ft < 3000 and abs(s.climb_fpm) < 1500 and s.ias_kt > 300:
        return "low"
    if s.climb_fpm < -1500:
        return None  # descents are charged as cruise by the planner
    return "combat"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--pilot", required=True, help="Tacview Pilot= name")
    parser.add_argument("--type", default="", help="text in the aircraft line")
    args = parser.parse_args()

    pooled: dict[str, list[Slice]] = {}
    for path in args.files:
        text = _read(path)
        oid = _find_object(text, args.pilot, args.type)
        if oid is None:
            continue
        for s in slices(text, oid):
            name = phase(s)
            if name is not None:
                pooled.setdefault(name, []).append(s)

    for name in ("ground", "climb", "cruise", "combat", "low"):
        group = pooled.get(name, [])
        if not group:
            print(f"{name:7} no data")
            continue
        burn = sum(s.burn_lbs for s in group)
        if name == "ground":
            rate = burn / sum(s.seconds for s in group) * 60
            print(f"{name:7} {rate:6.1f} lb/min  ({len(group)} min)")
            continue
        rate = burn / max(sum(s.miles for s in group), 1e-6)
        ias = sum(s.ias_kt for s in group) / len(group)
        alt = sum(s.alt_ft for s in group) / len(group)
        print(
            f"{name:7} {rate:6.1f} lb/NM   ({len(group)} min, "
            f"{ias:.0f} KIAS, {alt:,.0f} ft)"
        )


if __name__ == "__main__":
    main()
