"""
3D ERT viewer — Weisses Lauch, profiles 4-12.

Run from the geoviewer root:
    .venv/Scripts/python view3d_ert.py

What it does:
  - Reads all Res2DInv XYZ exports (skip / comment lines, drop Rho <= 0)
  - Places each profile at Y = 0, 15, 30 ... 120 m
  - Interpolates with scipy.griddata onto a 2x2x1 m regular 3D grid
  - Renders as a solid volume with interactive orthogonal slices
  - Color scale: real Ohm*m, log scale, clim=[15, 2000]
"""

import os
import numpy as np
import pandas as pd
import pyvista as pv
import matplotlib.colors as mcolors
from scipy.interpolate import griddata

# ── Config ────────────────────────────────────────────────────────────────────
XYZ_DIR   = r"data\Weisses Lauch\xyz"
Y_SPACING = 15.0          # metres between profiles

PROFILES = {
    4:  "profil4-865pkt-corr.xyz",
    5:  "Profile 5 WS-2-12+R1-corr.xyz",
    6:  "Profile 6 WS-2-12+R1.xyz",
    7:  "Profile 7 WS-12-2-corr.xyz",
    8:  "Profile 8 WS-12-2-corr.xyz",
    9:  "Profile 9 WS-48-2-13-cor.xyz",
    10: "Profile 10 WS-48-12-corr.xyz",
    11: "Profile 11 WS-48-corr_bis.xyz",
    12: "Profile 12 .xyz",
}

CLIM  = [15.0, 2000.0]   # Ohm*m color limits (log scale)
RES_X = 2.0              # grid resolution X (m)
RES_Y = 2.0              # grid resolution Y (m)
RES_Z = 1.0              # grid resolution Z (m)

# ── ERT resistivity colormap ──────────────────────────────────────────────────
# 11 colors for 11 bands between the 12 breakpoints below
_ERT_BOUNDS = [15, 25, 35, 55, 85, 115, 155, 200, 300, 500, 1000, 2000]
_ERT_COLORS = [
    "#00008B",  # 15–25     deep blue
    "#005EC8",  # 25–35     blue
    "#00BBEE",  # 35–55     cyan
    "#00BB44",  # 55–85     green
    "#AACC00",  # 85–115    yellow-green
    "#FFEE00",  # 115–155   yellow
    "#C8A870",  # 155–200   light brown / tan
    "#FF8C00",  # 200–300   orange
    "#EE0000",  # 300–500   red
    "#880000",  # 500–1000  dark red / burgundy
    "#440022",  # 1000–2000 dark purple / maroon
]

def _build_ert_cmap(n_lut: int = 512) -> mcolors.LinearSegmentedColormap:
    """
    Build a LinearSegmentedColormap that respects the ERT BoundaryNorm breakpoints
    in log space, so PyVista's log_scale=True maps colors correctly.
    """
    listed  = mcolors.ListedColormap(_ERT_COLORS)
    bnorm   = mcolors.BoundaryNorm(_ERT_BOUNDS, listed.N)
    # Sample the BoundaryNorm at log-spaced values across [CLIM[0], CLIM[1]].
    # PyVista with log_scale=True maps [log(clim0), log(clim1)] → [0, 1] linearly,
    # so sampling here in log space makes the two transformations consistent.
    log_samples = np.linspace(np.log10(CLIM[0]), np.log10(CLIM[1]), n_lut)
    ohm_samples = 10.0 ** log_samples
    rgba        = listed(bnorm(ohm_samples))
    return mcolors.LinearSegmentedColormap.from_list("ERT_rho", rgba, N=n_lut)

ERT_CMAP = _build_ert_cmap()

# ── I/O ───────────────────────────────────────────────────────────────────────

def read_xyz(path: str) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("/"):
                continue
            parts = s.split()
            if len(parts) >= 3:
                try:
                    rows.append((float(parts[0]), float(parts[1]), float(parts[2])))
                except ValueError:
                    continue
    df = pd.DataFrame(rows, columns=["X", "Z", "Rho"])
    return df[df["Rho"] > 0].reset_index(drop=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:

    # 1. Load all profiles into a single point cloud (X, Y, Z, Rho)
    print("Reading XYZ files ...")
    px, py, pz, prho = [], [], [], []

    for num, fname in sorted(PROFILES.items()):
        path = os.path.join(XYZ_DIR, fname)
        if not os.path.isfile(path):
            print(f"  [skip] not found: {fname}")
            continue
        df   = read_xyz(path)
        y0   = (num - 4) * Y_SPACING
        px.extend(df["X"].values)
        py.extend(np.full(len(df), y0))
        pz.extend(df["Z"].values)
        prho.extend(df["Rho"].values)
        print(f"  P{num:2d}: {len(df):5d} pts  Y={y0:5.0f} m  "
              f"X=[{df.X.min():.0f}, {df.X.max():.0f}] m  "
              f"Z=[{df.Z.min():.1f}, {df.Z.max():.1f}] m")

    src_pts = np.column_stack([px, py, pz])
    src_rho = np.array(prho)

    # 2. Build regular 3D grid
    x_min, x_max = src_pts[:, 0].min(), src_pts[:, 0].max()
    y_min, y_max = src_pts[:, 1].min(), src_pts[:, 1].max()
    z_min, z_max = src_pts[:, 2].min(), src_pts[:, 2].max()

    gx = np.arange(x_min, x_max + RES_X, RES_X)
    gy = np.arange(y_min, y_max + RES_Y, RES_Y)
    gz = np.arange(z_min, z_max + RES_Z, RES_Z)
    nx, ny, nz = len(gx), len(gy), len(gz)

    print(f"\nGrid: {nx} x {ny} x {nz} = {nx*ny*nz:,} points  "
          f"(resolution {RES_X}x{RES_Y}x{RES_Z} m)")
    print("Interpolating with scipy griddata (linear) — this may take ~30 s ...")

    GX, GY, GZ = np.meshgrid(gx, gy, gz, indexing="ij")
    dst_pts = np.column_stack([GX.ravel(), GY.ravel(), GZ.ravel()])

    rho_flat = griddata(src_pts, src_rho, dst_pts,
                        method="linear", fill_value=np.nan)
    rho_vol  = rho_flat.reshape((nx, ny, nz))

    # 3. PyVista ImageData (uniform grid)
    # Point ordering in VTK: X varies fastest → ravel with Fortran order
    vol = pv.ImageData()
    vol.dimensions = (nx, ny, nz)
    vol.origin     = (float(gx[0]), float(gy[0]), float(gz[0]))
    vol.spacing    = (RES_X, RES_Y, RES_Z)

    # Replace NaN (outside data hull) with sentinel -1; threshold will drop them
    rho_safe = np.where(np.isnan(rho_vol), -1.0, rho_vol)
    vol.point_data["Resistivity"] = rho_safe.ravel(order="F")

    # Keep only cells with valid (positive) resistivity
    vol_clean = vol.threshold(0.1, scalars="Resistivity")
    print(f"Valid cells after threshold: {vol_clean.n_cells:,}")

    # 4. Render
    print("Opening PyVista window ...")
    plotter = pv.Plotter(window_size=(1500, 900),
                         title="Weisses Lauch — ERT 3D Block")
    plotter.set_background("white")

    mesh_kw = dict(
        scalars="Resistivity",
        cmap=ERT_CMAP,
        clim=CLIM,
        log_scale=True,          # PyVista maps log([15,2000])→[0,1]; LUT was sampled the same way
        scalar_bar_args=dict(
            title="Resistivity (Ohm*m)",
            title_font_size=14,
            label_font_size=11,
            n_labels=7,           # ~15, 30, 60, 120, 250, 500, 2000
            vertical=True,
            position_x=0.89,
            position_y=0.15,
            width=0.04,
            height=0.65,
        ),
    )

    # Semi-transparent shell so you can see inside while using slices
    plotter.add_mesh(vol_clean, opacity=0.06, show_scalar_bar=False,
                     **{k: v for k, v in mesh_kw.items()
                        if k != "scalar_bar_args"})

    # Interactive orthogonal slices (drag the handles to move each plane)
    plotter.add_mesh_slice_orthogonal(vol_clean, **mesh_kw)

    plotter.add_axes(
        xlabel="Distance (m)",
        ylabel="Profile offset (m)",
        zlabel="Depth (m)",
        line_width=2,
    )
    plotter.show_grid()
    plotter.camera_position = "iso"
    plotter.camera.azimuth   = -30
    plotter.camera.elevation =  25

    print("\nControls:")
    print("  Left-click + drag  : rotate")
    print("  Scroll             : zoom")
    print("  Right-click + drag : pan")
    print("  Drag slice handles : move orthogonal cut planes")
    plotter.show()


if __name__ == "__main__":
    main()
