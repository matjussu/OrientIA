"""Vague C — Historical trends from Parcoursup 2023/2024 vs 2025.

Joint key : cod_aff_form (verified stable 95-96% across years on the full
open-data dumps). This is the clean path to produce trend signals per
formation that no LLM with a January 2026 cutoff can know.

Exposed at the fiche level:
- `admission.historique`: per-year snapshot (taux_acces, places, voeux totaux,
  profil_admis splits) for each year the fiche existed.
- `trends`: directional summary with interpretation strings for the LLM.

Principle: numeric, structured. Goes into the generator context (not into
the embedding — same separation-of-concerns rule as Vague A/B).
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


# Columns to snapshot per year (subset of what parcoursup.py reads — just the
# metrics that carry meaningful temporal signal).
HIST_COLS = {
    "taux_acces": "taux_acces_ens",
    "places": "capa_fin",
    "voeux_totaux": "voe_tot",
    "voeux_phase_principale": "nb_voe_pp",
    "pct_bg": "pct_bg",
    "pct_bt": "pct_bt",
    "pct_bp": "pct_bp",
    "pct_tb": "pct_tb",
    "pct_b": "pct_b",
    "pct_bours": "pct_bours",
    "pct_f": "pct_f",
}

# Thresholds for "significant" trend (below these, direction reported as
# "stable" to avoid noise-driven narratives).
SIGNIFICANT_TAUX_ACCES_DELTA = 10.0   # ≥ 10 percentage points = meaningful
SIGNIFICANT_PLACES_DELTA_PCT = 20.0    # ≥ 20% change in places
SIGNIFICANT_VOEUX_DELTA_PCT = 25.0     # ≥ 25% change in voeux volume


def _safe_float(val) -> float | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _safe_int(val) -> int | None:
    f = _safe_float(val)
    if f is None:
        return None
    return int(f)


def load_historical_snapshots(
    csv_path: str | Path,
    year: int,
) -> dict[str, dict]:
    """Parse a Parcoursup CSV for a given year, keyed by cod_aff_form.

    Returns a dict `{cod_aff_form: snapshot}` where snapshot contains the
    HIST_COLS metrics. Rows without cod_aff_form are skipped.
    """
    snapshots: dict[str, dict] = {}
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            code = (row.get("cod_aff_form") or "").strip()
            if not code:
                continue
            snap: dict = {"year": year}
            for field, col in HIST_COLS.items():
                val = row.get(col)
                if field in ("places", "voeux_totaux", "voeux_phase_principale"):
                    snap[field] = _safe_int(val)
                else:
                    snap[field] = _safe_float(val)
            snapshots[code] = snap
    return snapshots


def _trend_direction(
    values: list[tuple[int, float]],
    *,
    mode: str,
    sig_threshold: float,
) -> str:
    """Return 'up' / 'down' / 'stable' based on first-to-last comparison.

    - mode='abs' compares absolute delta to threshold (e.g. pp for taux_acces).
    - mode='pct' compares relative (%) delta to threshold (e.g. for volumes).
    """
    if len(values) < 2:
        return "stable"
    # Sort by year then first-vs-last
    values_sorted = sorted(values)
    start_y, start_v = values_sorted[0]
    end_y, end_v = values_sorted[-1]
    if start_v is None or end_v is None:
        return "stable"
    if mode == "abs":
        delta = end_v - start_v
        if delta >= sig_threshold:
            return "up"
        if delta <= -sig_threshold:
            return "down"
        return "stable"
    # mode == 'pct'
    if start_v == 0:
        return "stable"
    pct = (end_v - start_v) / start_v * 100.0
    if pct >= sig_threshold:
        return "up"
    if pct <= -sig_threshold:
        return "down"
    return "stable"


def compute_trends(historique: dict[int, dict]) -> dict:
    """Compute trend summary from a per-year snapshot dict.

    `historique` is a dict `{year: snapshot}` where snapshot has the
    HIST_COLS metrics. Returns a dict of trend entries per metric family
    with direction + delta + human-readable interpretation.
    """
    if not historique or len(historique) < 2:
        return {}

    years = sorted(historique.keys())
    trends: dict = {}

    # Taux d'accès — direction with pp-absolute threshold
    taux_values = [(y, historique[y].get("taux_acces")) for y in years
                   if historique[y].get("taux_acces") is not None]
    if len(taux_values) >= 2:
        direction = _trend_direction(taux_values, mode="abs",
                                     sig_threshold=SIGNIFICANT_TAUX_ACCES_DELTA)
        start_y, start_v = min(taux_values)
        end_y, end_v = max(taux_values)
        delta = end_v - start_v
        if direction == "down":
            interp = (f"taux d'accès en baisse {start_y}→{end_y} "
                      f"({start_v:g}% → {end_v:g}%) : formation devenue plus sélective")
        elif direction == "up":
            interp = (f"taux d'accès en hausse {start_y}→{end_y} "
                      f"({start_v:g}% → {end_v:g}%) : formation devenue plus accessible")
        else:
            interp = (f"taux d'accès stable {start_y}→{end_y} "
                      f"({start_v:g}% → {end_v:g}%)")
        trends["taux_acces"] = {
            "direction": direction,
            "delta_pp": round(delta, 2),
            "start_year": start_y,
            "end_year": end_y,
            "start_value": start_v,
            "end_value": end_v,
            "interpretation": interp,
        }

    # Places — direction with %-relative threshold
    places_values = [(y, historique[y].get("places")) for y in years
                     if historique[y].get("places") is not None]
    if len(places_values) >= 2:
        direction = _trend_direction(places_values, mode="pct",
                                     sig_threshold=SIGNIFICANT_PLACES_DELTA_PCT)
        start_y, start_v = min(places_values)
        end_y, end_v = max(places_values)
        delta = end_v - start_v
        if direction == "up":
            interp = (f"places en hausse {start_y}→{end_y} "
                      f"({start_v} → {end_v}) : ouverture de capacité")
        elif direction == "down":
            interp = (f"places en baisse {start_y}→{end_y} "
                      f"({start_v} → {end_v}) : fermeture partielle")
        else:
            interp = None  # Stable places are uninteresting
        trends["places"] = {
            "direction": direction,
            "delta": delta,
            "start_year": start_y,
            "end_year": end_y,
            "start_value": start_v,
            "end_value": end_v,
            "interpretation": interp,
        }

    # Vœux totaux — direction with %-relative threshold (popularity)
    voeux_values = [(y, historique[y].get("voeux_totaux")) for y in years
                    if historique[y].get("voeux_totaux") is not None]
    if len(voeux_values) >= 2:
        direction = _trend_direction(voeux_values, mode="pct",
                                     sig_threshold=SIGNIFICANT_VOEUX_DELTA_PCT)
        start_y, start_v = min(voeux_values)
        end_y, end_v = max(voeux_values)
        delta = end_v - start_v
        if direction == "up":
            interp = (f"popularité en hausse {start_y}→{end_y} "
                      f"({start_v} → {end_v} vœux) : attrait renforcé")
        elif direction == "down":
            interp = (f"popularité en baisse {start_y}→{end_y} "
                      f"({start_v} → {end_v} vœux) : attrait en repli")
        else:
            interp = None
        trends["voeux"] = {
            "direction": direction,
            "delta": delta,
            "start_year": start_y,
            "end_year": end_y,
            "start_value": start_v,
            "end_value": end_v,
            "interpretation": interp,
        }

    return trends


def attach_trends(
    fiches: list[dict],
    csv_paths_by_year: dict[int, str | Path],
) -> list[dict]:
    """Attach admission.historique + trends to each fiche based on its cod_aff_form.

    `csv_paths_by_year` is `{2023: 'path/to/2023.csv', 2024: '...', 2025: '...'}`.
    Fiches without cod_aff_form (ONISEP-only) are left untouched.

    Safe no-op if any historical CSV is missing (graceful degradation).
    """
    # Load all available snapshots
    snapshots_by_year: dict[int, dict[str, dict]] = {}
    for year, path in csv_paths_by_year.items():
        p = Path(path)
        if not p.exists():
            continue
        snapshots_by_year[year] = load_historical_snapshots(p, year)

    if not snapshots_by_year:
        return fiches  # no historical data available

    for fiche in fiches:
        code = fiche.get("cod_aff_form")
        if not code:
            continue
        historique: dict[int, dict] = {}
        for year, snaps in snapshots_by_year.items():
            snap = snaps.get(code)
            if snap is not None:
                historique[year] = snap
        if not historique:
            continue
        # Attach to admission.historique (stored as str keys in JSON)
        adm = fiche.setdefault("admission", {})
        adm["historique"] = {str(y): v for y, v in sorted(historique.items())}
        # Compute trends summary
        trends = compute_trends(historique)
        if trends:
            fiche["trends"] = trends

    return fiches
