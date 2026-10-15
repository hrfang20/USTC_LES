"""Visualize and diagnose a long Campus 202 uDALES continuation run."""
from pathlib import Path
import argparse
import io
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor/python-deps"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import netCDF4 as nc
import numpy as np
from PIL import Image


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=ROOT / "outputs/validation/run/202/202_run7200",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "outputs/validation/figures/campus202_7200",
    )
    parser.add_argument("--gif-frames", type=int, default=80)
    return parser.parse_args()


def save(fig, out, name):
    fig.savefig(out / f"{name}.png", dpi=160, bbox_inches="tight")
    fig.savefig(out / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def weighted_surface_series(path, areas, variables, chunk=120):
    result = {}
    with nc.Dataset(path) as data:
        time_name = "t" if "t" in data.variables else "time"
        result["time"] = np.asarray(data[time_name][:], dtype=float)
        for name in variables:
            values = np.empty(len(result["time"]), dtype=float)
            mins = np.empty_like(values) if name == "T" else None
            maxs = np.empty_like(values) if name == "T" else None
            for start in range(0, len(values), chunk):
                stop = min(start + chunk, len(values))
                block = np.ma.filled(data[name][start:stop], np.nan)
                if block.ndim == 3:
                    block = block[:, 0, :]
                values[start:stop] = np.average(block, axis=1, weights=areas)
                if name == "T":
                    mins[start:stop] = np.nanmin(block, axis=1)
                    maxs[start:stop] = np.nanmax(block, axis=1)
            result[name] = values
            if name == "T":
                result["Tmin"], result["Tmax"] = mins, maxs
    return result


args = arguments()
run = args.run_dir.resolve()
out = args.out_dir.resolve()
out.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 10, "figure.dpi": 130, "axes.formatter.useoffset": False})

files = sorted(run.glob("fielddump.*.*.202.nc"))
if len(files) != 4:
    raise RuntimeError(f"Expected four MPI field files, found {len(files)}")
with nc.Dataset(files[0]) as data:
    times = np.asarray(data["time"][:], dtype=float)
    z = np.asarray(data["zt"][:], dtype=float)
if len(times) < 2 or np.any(np.diff(times) <= 0):
    raise RuntimeError("Field times are missing or not strictly increasing")

nx, ny = 218, 270
dx = 5.0
x, y = np.meshgrid((np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dx)
heights = [7.5, 17.5, 57.5]
ks = [int(np.argmin(abs(z - height))) for height in heights]
fields = {
    name: np.full((len(times), len(ks), ny, nx), np.nan, np.float32)
    for name in ["u", "v", "thl", "qt"]
}
coverage = np.zeros((ny, nx), dtype=np.int8)
for path in files:
    with nc.Dataset(path) as data:
        np.testing.assert_allclose(data["time"][:], times, rtol=0, atol=1e-4)
        ix = np.rint(np.asarray(data["xt"][:]) / dx - 0.5).astype(int)
        iy = np.rint(np.asarray(data["yt"][:]) / dx - 0.5).astype(int)
        coverage[np.ix_(iy, ix)] += 1
        for name in fields:
            for ih, k in enumerate(ks):
                fields[name][:, ih, iy[:, None], ix] = np.ma.filled(
                    data[name][:, k], np.nan
                )
if not np.all(coverage == 1):
    raise RuntimeError("MPI tiles do not cover the horizontal domain exactly once")
if not all(np.isfinite(values).all() for values in fields.values()):
    raise RuntimeError("Non-finite values found in sampled 3-D fields")

# Put staggered u and v onto scalar-cell centres. The domain is periodic.
fields["u"] = 0.5 * (fields["u"] + np.roll(fields["u"], -1, axis=3))
fields["v"] = 0.5 * (fields["v"] + np.roll(fields["v"], -1, axis=2))
solid = np.zeros((len(z), ny, nx), dtype=bool)
ijk = np.loadtxt(run / "solid_c.txt", comments="#", dtype=int)
solid[ijk[:, 2] - 1, ijk[:, 1] - 1, ijk[:, 0] - 1] = True
for values in fields.values():
    for ih, k in enumerate(ks):
        values[:, ih, solid[k]] = np.nan
speed = np.hypot(fields["u"], fields["v"])
speed_max = np.ceil(np.nanpercentile(speed, 99.8) * 2) / 2

snapshot_indices = np.linspace(0, len(times) - 1, 6).round().astype(int)
arrows = np.s_[::14, ::14]


def plan_view(ax, it, ih, values, low, high, cmap, title, vectors=False):
    image = ax.pcolormesh(x, y, values, cmap=cmap, vmin=low, vmax=high,
                          shading="nearest", rasterized=True)
    ax.contourf(x, y, solid[ks[ih]], levels=[0.5, 1.5], colors=["#929ca4"])
    if vectors:
        ax.quiver(x[arrows], y[arrows], fields["u"][it, ih][arrows],
                  fields["v"][it, ih][arrows], color="white", scale=45,
                  width=0.003)
    ax.set(xlim=(0, 1090), ylim=(0, 1350), aspect="equal", xlabel="x (m)",
           ylabel="y (m)", title=title)
    return image


for ih, k in enumerate(ks):
    fig, axes = plt.subplots(2, 3, figsize=(13, 11), constrained_layout=True)
    for it, ax in zip(snapshot_indices, axes.flat):
        image = plan_view(ax, it, ih, speed[it, ih], 0, speed_max, "viridis",
                          f"t = {times[it] / 3600:.2f} h", True)
    fig.colorbar(image, ax=axes.ravel().tolist(), label="Horizontal speed (m/s)", shrink=0.7)
    fig.suptitle(f"Campus 202 long run | z = {z[k]:.1f} m")
    save(fig, out, f"202_long_wind_z{z[k]:g}".replace(".", "p"))

gif_indices = np.unique(np.linspace(0, len(times) - 1,
                                    min(args.gif_frames, len(times))).round().astype(int))
frames = []
for it in gif_indices:
    fig, axes = plt.subplots(1, 2, figsize=(10, 6), constrained_layout=True)
    for ih, ax in enumerate(axes):
        image = plan_view(ax, it, ih, speed[it, ih], 0, speed_max, "viridis",
                          f"t={times[it] / 3600:.2f} h | z={z[ks[ih]]:.1f} m", True)
    fig.colorbar(image, ax=axes, label="Horizontal speed (m/s)", shrink=0.7)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=95)
    plt.close(fig)
    buffer.seek(0)
    frames.append(Image.open(buffer).convert("RGB").copy())
frames[0].save(out / "202_long_wind_evolution.gif", save_all=True,
               append_images=frames[1:], duration=180, loop=0)

fig, axes = plt.subplots(2, 3, figsize=(13, 10), constrained_layout=True)
thermal_indices = [0, len(times) // 2, len(times) - 1]
for row, (name, unit, factor) in enumerate([("thl", "K", 1), ("qt", "g/kg", 1000)]):
    values = fields[name][:, 0] * factor
    low, high = np.nanpercentile(values, [0.2, 99.8])
    if high <= low:
        high = low + np.finfo(float).eps
    for ax, it in zip(axes[row], thermal_indices):
        image = plan_view(ax, it, 0, values[it], low, high, "magma",
                          f"{name} | t={times[it] / 3600:.2f} h")
    fig.colorbar(image, ax=axes[row].tolist(), label=unit, shrink=0.7)
fig.suptitle(f"Campus 202 long run | thermal/moisture fields | z={z[ks[0]]:.1f} m")
save(fig, out, "202_long_thermal_maps")

with nc.Dataset(run / "xytdump.202.nc") as data:
    profile_time = np.asarray(data["time"][:], dtype=float)
    profiles = {
        name: np.ma.filled(data[name][:], np.nan)
        for name in ["uxyt", "thlxyt", "qtxyt", "tketxyc", "upwpxyt", "wpthlpxyt"]
    }
if not all(np.isfinite(values).all() for values in profiles.values()):
    raise RuntimeError("Non-finite values found in statistical profiles")

last_hour = profile_time >= profile_time[-1] - 3600
previous_hour = ((profile_time >= profile_time[-1] - 7200)
                 & (profile_time < profile_time[-1] - 3600))
if not np.any(previous_hour):
    midpoint = len(profile_time) // 2
    previous_hour = np.arange(len(profile_time)) < midpoint
    last_hour = np.arange(len(profile_time)) >= midpoint

profile_specs = [
    ("uxyt", "Mean u (m/s)", "zt", 1),
    ("thlxyt", "Liquid-water potential temperature (K)", "zt", 1),
    ("qtxyt", "Total water mixing ratio (g/kg)", "zt", 1000),
    ("tketxyc", "Resolved TKE (m²/s²)", "zt", 1),
    ("upwpxyt", "Resolved u-w covariance (m²/s²)", "zm", 1),
    ("wpthlpxyt", "Resolved heat covariance (K m/s)", "zm", 1),
]
fig, axes = plt.subplots(2, 3, figsize=(14, 9), constrained_layout=True)
for ax, (name, label, coordinate, factor) in zip(axes.flat, profile_specs):
    zz = z if coordinate == "zt" else z - 2.5
    ax.plot(np.mean(profiles[name][previous_hour], axis=0) * factor, zz,
            label="Previous 1 h mean")
    ax.plot(np.mean(profiles[name][last_hour], axis=0) * factor, zz,
            label="Final 1 h mean")
    ax.set(xlabel=label, ylabel="z (m)", ylim=(0, 100))
    ax.grid(alpha=0.2)
    ax.legend()
fig.suptitle("Campus 202 | comparison of final two hourly profile means")
save(fig, out, "202_long_profiles_hourly_comparison")

fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True, sharey=True)
for ax, (name, label) in zip(axes, [("uxyt", "Mean u (m/s)"),
                                    ("thlxyt", "thl (K)"),
                                    ("tketxyc", "Resolved TKE (m²/s²)")]):
    image = ax.pcolormesh(profile_time / 3600, z, profiles[name].T,
                          shading="auto", cmap="viridis", rasterized=True)
    ax.set(xlabel="Simulation time (h)", ylabel="z (m)", ylim=(0, 100), title=label)
    fig.colorbar(image, ax=ax, shrink=0.85)
fig.suptitle("Campus 202 | time-height evolution")
save(fig, out, "202_long_time_height")

areas = np.loadtxt(run / "facetarea.inp.202", comments="#")
surface_t = weighted_surface_series(run / "facT.202.nc", areas, ["T"])
surface_flux = weighted_surface_series(
    run / "facEB.202.nc", areas, ["netsw", "LWin", "LWout", "hf", "ef"]
)
fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)
for height in heights:
    k = int(np.argmin(abs(z - height)))
    axes[0].plot(profile_time / 3600, profiles["uxyt"][:, k], label=f"z={z[k]:g} m")
axes[0].set(xlabel="Simulation time (h)", ylabel="Mean u (m/s)")
axes[0].legend()
axes[1].plot(surface_t["time"] / 3600, surface_t["T"], label="Area-weighted mean")
axes[1].fill_between(surface_t["time"] / 3600, surface_t["Tmin"], surface_t["Tmax"],
                     alpha=0.2, label="Facet min-max")
axes[1].set(xlabel="Simulation time (h)", ylabel="Surface temperature (K)")
axes[1].legend()
for name in ["netsw", "LWin", "LWout", "hf", "ef"]:
    axes[2].plot(surface_flux["time"] / 3600, surface_flux[name], label=name)
axes[2].set(xlabel="Simulation time (h)", ylabel="Stored area-weighted flux (W/m²)")
axes[2].legend(ncol=2)
for ax in axes:
    ax.grid(alpha=0.2)
fig.suptitle("Campus 202 | long-run diagnostics")
save(fig, out, "202_long_diagnostics")

def window_mean(name, mask, k, factor=1):
    return float(np.mean(profiles[name][mask, k]) * factor)

stationarity = {}
for height in heights:
    k = int(np.argmin(abs(z - height)))
    old = window_mean("uxyt", previous_hour, k)
    new = window_mean("uxyt", last_hour, k)
    stationarity[str(height)] = {
        "previous_hour_mean_u_m_s": old,
        "final_hour_mean_u_m_s": new,
        "relative_change_percent": 100 * (new - old) / old,
    }
summary = {
    "field_time_range_s": [float(times[0]), float(times[-1])],
    "field_snapshots": int(len(times)),
    "field_interval_median_s": float(np.median(np.diff(times))),
    "profile_time_range_s": [float(profile_time[0]), float(profile_time[-1])],
    "surface_time_range_s": [float(surface_t["time"][0]), float(surface_t["time"][-1])],
    "surface_temperature_K": {
        "initial_mean": float(surface_t["T"][0]),
        "final_mean": float(surface_t["T"][-1]),
        "final_min": float(surface_t["Tmin"][-1]),
        "final_max": float(surface_t["Tmax"][-1]),
    },
    "mean_u_stationarity": stationarity,
    "final_hour_lowest_level": {
        "mean_thl_K": window_mean("thlxyt", last_hour, 0),
        "mean_qt_g_kg": window_mean("qtxyt", last_hour, 0, 1000),
        "mean_resolved_tke_m2_s2": window_mean("tketxyc", last_hour, 0),
    },
    "final_flux_area_means_W_m2": {
        name: float(surface_flux[name][-1])
        for name in ["netsw", "LWin", "LWout", "hf", "ef"]
    },
    "notes": [
        "The run is a continuation from about 200 s; the final physical time is about 7400 s.",
        "Hourly comparisons use the final two available one-hour windows.",
        "Stored energy-balance flux signs are retained.",
    ],
}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
