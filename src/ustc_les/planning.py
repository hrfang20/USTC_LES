"""Planning helpers: never allocate a three-dimensional flow field."""
import json
import math
from pathlib import Path
from .physics import coriolis_parameter


def read_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _positive(value, name):
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


def preflight(config, project_root):
    lengths, spacing = config["domain_m"], config["grid_spacing_m"]
    if len(lengths) != 3 or len(spacing) != 3:
        raise ValueError("Domain and spacing must each have three components")
    counts = []
    for length, delta in zip(lengths, spacing):
        _positive(length, "Domain length")
        _positive(delta, "Grid spacing")
        ratio = length / delta
        if not math.isclose(ratio, round(ratio), abs_tol=1e-9, rel_tol=0):
            raise ValueError("Domain lengths must be integer multiples of grid spacing")
        counts.append(round(ratio))
    for key in ("planning_speed_m_s", "advection_cfl_target",
                "field_count_for_memory_estimate", "bytes_per_value"):
        _positive(config[key], key)
    for key in ("field_count_for_memory_estimate", "bytes_per_value"):
        if int(config[key]) != config[key]:
            raise ValueError(f"{key} must be an integer")
    f = coriolis_parameter(config["latitude_deg"])
    geometry = read_config(Path(project_root) / config["geometry_file"])
    if geometry.get("type") != "FeatureCollection" or not isinstance(geometry.get("features"), list):
        raise ValueError("Geometry must be a GeoJSON FeatureCollection")
    buildings = geometry["features"]
    blockers = []
    if not config.get("campus_boundary_verified"):
        blockers.append("Road-bounded study area coordinates and computational domain placement need verification")
    if config.get("coordinate_origin_wgs84") is None:
        blockers.append("Local coordinate origin is missing")
    if not buildings:
        blockers.append("No real building footprints or heights have been collected")
    else:
        blockers.append("Building completeness and assumed heights need independent verification")
    if not config.get("solver"):
        blockers.append("Three-dimensional LES solver has not been selected or implemented")
    if config.get("status") != "validated":
        blockers.append("Meteorology, thermal conditions and grid resolution remain draft")
    input_status_path = Path(project_root) / 'cases/001/input_status.json'
    input_status = read_config(input_status_path) if input_status_path.is_file() else None
    if config.get('solver') == 'uDALES' and (not input_status or not input_status.get('ibm_completed')):
        blockers.append("uDALES compiled IBM preprocessing and complete solver inputs are pending")
    cells = math.prod(counts)
    return {
        "case": config["case"], "grid_cells": counts, "total_cells": cells,
        "study_area": config.get("study_area"),
        "geometry_simplification": config.get("geometry_simplification"),
        "solver": config.get("solver"),
        "udales_input_status": input_status,
        "field_storage_lower_bound_GiB": cells * config["field_count_for_memory_estimate"] * config["bytes_per_value"] / 2**30,
        "advection_dt_estimate_s": config["advection_cfl_target"] * min(spacing) / config["planning_speed_m_s"],
        "dt_note": "Planning only; multidimensional CFL, diffusion and solver constraints may require smaller dt",
        "coriolis_parameter_s_inv": f,
        "inertial_period_h": 2 * math.pi / abs(f) / 3600 if f else None,
        "building_count": len(buildings), "les_ready": False, "blockers": blockers,
        "readiness_note": "This preflight cannot certify a production LES even when inputs are filled",
    }
