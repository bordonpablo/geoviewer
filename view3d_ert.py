"""
Standalone 3D ERT viewer — Weisses Lauch, profiles 4–12.

Each XYZ file (Res2DInv export) is placed at a fixed Y offset so the
profiles appear as parallel vertical cross-sections in a single PyVista scene.

Run from the geoviewer root:
    .venv/Scripts/python view3d_ert.py
"""

import os
import numpy as np
import pandas as pd
import pyvista as pv

# ── Config ────────────────────────────────────────────────────────────────────
XYZ_DIR   = r"data\Weisses Lauch\xyz"
Y_SPACING = 15.0   # metres between profiles along Y axis

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

# ── I/O ───────────────────────────────────────────────────────────────────────

def read_xyz(path: str) -> pd.DataFrame:
    """Read Res2DInv XYZ export; skip / comment lines; return X, Z, Rho."""
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
    # Remove physically invalid values (Res2DInv edge artefacts)
    df = df[df["Rho"] > 0].reset_index(drop=True)
    return df


# ── Mesh building ─────────────────────────────────────────────────────────────

def make_surface(x: np.ndarray, z: np.ndarray,
                 log_rho: np.ndarray, y0: float) -> pv.PolyData:
    """
    Triangulate one ERT cross-section and place it at Y = y0.

    Strategy: PyVista delaunay_2d triangulates in the XY plane.
    We feed (X, Z, 0) so it triangulates in the X-Z plane (the profile plane),
    then swap columns so the mesh sits at the correct 3D position (X, y0, Z).
    """
    # Estimate alpha: must span depth-layer gaps without bridging across voids.
    # Use ~6× the median depth-step; generous enough for the trapezoidal mesh.
    z_unique = np.sort(np.unique(z))
    dz = np.median(np.abs(np.diff(z_unique))) if len(z_unique) > 1 else 1.0
    x_unique = np.sort(np.unique(x))
    dx = np.median(np.diff(x_unique)) if len(x_unique) > 1 else 1.0
    alpha = max(dz, dx) * 6.0

    pts_flat = np.column_stack([x, z, np.zeros(len(x))])
    cloud = pv.PolyData(pts_flat)
    cloud["log_rho"] = log_rho

    surf = cloud.delaunay_2d(alpha=alpha)

    # Remap to real 3D: old col0→X, old col1(=Z)→col2, y0→col1
    p = surf.points.copy()
    p[:, 2] = p[:, 1]
    p[:, 1] = y0
    surf.points = p

    return surf


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Reading XYZ files …")
    dfs: dict[int, pd.DataFrame] = {}
    all_log_rho: list[float] = []

    for num, fname in sorted(PROFILES.items()):
        path = os.path.join(XYZ_DIR, fname)
        if not os.path.isfile(path):
            print(f"  [skip] not found: {fname}")
            continue
        df = read_xyz(path)
        dfs[num] = df
        all_log_rho.extend(np.log10(df["Rho"].values).tolist())
        print(f"  P{num:2d}: {len(df):6d} pts  "
              f"X=[{df.X.min():.0f}, {df.X.max():.0f}] m  "
              f"Z=[{df.Z.min():.1f}, {df.Z.max():.1f}] m  "
              f"Rho=[{df.Rho.min():.0f}, {df.Rho.max():.0f}] Ω·m")

    # Global colour limits (2nd–98th percentile to clip outliers)
    clim = [float(np.percentile(all_log_rho, 2)),
            float(np.percentile(all_log_rho, 98))]
    print(f"\nColour range: 10^{clim[0]:.2f} – 10^{clim[1]:.2f} Ω·m  "
          f"({10**clim[0]:.0f} – {10**clim[1]:.0f} Ω·m)\n")

    plotter = pv.Plotter(window_size=(1500, 900),
                         title="Weisses Lauch — ERT Pseudo-3D")
    plotter.set_background("white")

    scalar_bar_added = False
    for num, df in sorted(dfs.items()):
        y0 = (num - 4) * Y_SPACING
        log_rho = np.log10(df["Rho"].values)

        print(f"  Building surface P{num} …")
        surf = make_surface(df["X"].values, df["Z"].values, log_rho, y0)

        plotter.add_mesh(
            surf,
            scalars="log_rho",
            cmap="Spectral_r",
            clim=clim,
            show_scalar_bar=not scalar_bar_added,
            scalar_bar_args=dict(
                title="Resistivity (Ω·m)",
                title_font_size=14,
                label_font_size=11,
                n_labels=5,
                fmt="%.1f",
                vertical=True,
                position_x=0.90,
                position_y=0.15,
                width=0.04,
                height=0.65,
            ),
        )
        scalar_bar_added = True

        # Label at the start of each profile, slightly above terrain
        z_top = df["Z"].max()
        label_pt = np.array([[df["X"].min(), y0, z_top + 5]])
        plotter.add_point_labels(
            label_pt, [f"P{num}"],
            font_size=12, text_color="black",
            point_color="black", point_size=1,
            always_visible=True,
        )

    plotter.add_axes(
        xlabel="Distance (m)",
        ylabel="Profile offset (m)",
        zlabel="Elevation (m)",
        line_width=2,
    )
    plotter.show_grid()

    # Isometric-ish camera: slightly in front and above
    plotter.camera_position = "iso"
    plotter.camera.azimuth   = -30
    plotter.camera.elevation =  25

    print("\nOpening 3D window — rotate with left-click, zoom with scroll.")
    plotter.show()


if __name__ == "__main__":
    main()
