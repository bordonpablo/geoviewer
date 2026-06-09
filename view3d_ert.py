"""
3D ERT viewer — multi-zone.

Usage:
    .venv/Scripts/python view3d_ert.py weisseslauch
    .venv/Scripts/python view3d_ert.py kleinsee

What it does:
  - Reads Res2DInv XYZ exports for the chosen zone
  - Places each profile at evenly spaced Y positions
  - Interpolates with scipy.griddata onto a regular 3D grid
  - Renders as a solid volume with interactive slices and fence diagram
  - Color scale: real Ohm*m, log scale
"""

import os
import sys
import numpy as np
import pandas as pd
import pyvista as pv
import matplotlib.colors as mcolors
from scipy.interpolate import griddata

# ── Zone configs ──────────────────────────────────────────────────────────────
ZONES = {
    "weisseslauch": {
        "title":     "Weißes Lauch",
        "xyz_dir":   r"data\Weisses Lauch\xyz",
        "y_ref":     4,       # profile number placed at Y = 0
        "y_spacing": 15.0,
        "ve":        5,
        "clim":      [15.0, 2000.0],
        "res":       (2.0, 2.0, 1.0),
        "profiles": {
            1:  "Profil 1-Whlg.721pkt-corr.xyz",
            2:  "Profil 2 -Messung1-865pkt-corr.xyz",
            4:  "profil4-865pkt-corr.xyz",
            5:  "Profile 5 WS-2-12+R1-corr.xyz",
            6:  "Profile 6 WS-2-12+R1.xyz",
            7:  "Profile 7 WS-12-2-corr.xyz",
            8:  "Profile 8 WS-12-2-corr.xyz",
            9:  "Profile 9 WS-48-2-13-cor.xyz",
            10: "Profile 10 WS-48-12-corr.xyz",
            11: "Profile 11 WS-48-corr_bis.xyz",
            12: "Profile 12 .xyz",
        },
    },
    "kleinsee": {
        "title":     "Kleinsee",
        "xyz_dir":   r"data\Kleinsee\xyz",
        "y_ref":     1,       # profile 1 at Y = 0
        "y_spacing": 15.0,
        "ve":        5,
        "clim":      [15.0, 2000.0],
        "res":       (2.0, 2.0, 1.0),
        "profiles": {
            1: "profile1.xyz",
            2: "profile2.xyz",
            3: "profile3.xyz",
            4: "profile4.xyz",
        },
    },
}

# ── Select zone from command-line argument ────────────────────────────────────
if len(sys.argv) < 2 or sys.argv[1].lower() not in ZONES:
    print(f"Usage:  python view3d_ert.py <zone>")
    print(f"Zones:  {', '.join(ZONES.keys())}")
    sys.exit(1)

cfg       = ZONES[sys.argv[1].lower()]
XYZ_DIR   = cfg["xyz_dir"]
PROFILES  = cfg["profiles"]
Y_SPACING = cfg["y_spacing"]
Y_REF     = cfg["y_ref"]
VE        = cfg["ve"]
CLIM      = cfg["clim"]
RES_X, RES_Y, RES_Z = cfg["res"]
TITLE     = cfg["title"]

# ── ERT resistivity colormap ──────────────────────────────────────────────────
# 11 colors for 11 bands between the 12 breakpoints (matches Surfer profile images)
_ERT_BOUNDS = [15, 25, 35, 55, 85, 115, 155, 200, 300, 500, 1000, 2000]
_ERT_COLORS = [
    "#0000AA",  # 15–25     dark blue
    "#0055FF",  # 25–35     blue
    "#00CCFF",  # 35–55     cyan
    "#00FF99",  # 55–85     light green
    "#AAFF00",  # 85–115    yellow-green
    "#FFFF00",  # 115–155   yellow
    "#AA7733",  # 155–200   brown / tan
    "#FF8800",  # 200–300   orange
    "#FF0000",  # 300–500   red
    "#880000",  # 500–1000  dark red / burgundy
    "#440033",  # 1000–2000 dark purple
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
        y0   = (num - Y_REF) * Y_SPACING
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

    # Apply vertical exaggeration: scale Z by VE for display only.
    # All render calls use vol_disp; raw data and Y coords are unchanged.
    vol_disp = vol_clean.copy()
    vol_disp.points[:, 2] *= VE

    # ── 4. Render ─────────────────────────────────────────────────────────────
    print("Opening PyVista window ...")
    plotter = pv.Plotter(window_size=(1500, 900),
                         title=f"{TITLE} — ERT 3D  |  T = toggle mode  |  right-click = identify profile")
    plotter.set_background("white")

    mesh_kw = dict(
        scalars="Resistivity",
        cmap=ERT_CMAP,
        clim=CLIM,
        log_scale=True,
        scalar_bar_args=dict(
            title="Resistivity (Ohm*m)",
            title_font_size=14,
            label_font_size=11,
            n_labels=7,
            vertical=True,
            position_x=0.89,
            position_y=0.15,
            width=0.04,
            height=0.65,
        ),
    )
    mesh_kw_no_bar = {k: v for k, v in mesh_kw.items() if k != "scalar_bar_args"}

    # ── Profile labels ────────────────────────────────────────────────────────
    # Place labels clearly to the LEFT of the data and above the surface so
    # they are never occluded.  One call with all points is more reliable than
    # one call per profile.
    valid_nums  = sorted(n for n in PROFILES if
                         os.path.isfile(os.path.join(XYZ_DIR, PROFILES[n])))

    # Profile labels: placed left of block, above the (VE-scaled) surface
    label_pts   = np.array([[x_min - 8, (n - Y_REF) * Y_SPACING, z_max * VE + 5]
                             for n in valid_nums], dtype=float)
    label_texts = [f"Profile {n}" for n in valid_nums]

    plotter.add_point_labels(
        label_pts, label_texts,
        font_size=14,
        bold=True,
        text_color="black",
        shape="rounded_rect",
        shape_color="lightyellow",
        shape_opacity=0.9,
        always_visible=True,
        show_points=False,
    )

    # ── Depth ruler (right side, real depths labeled) ────────────────────────
    # Ticks every 2 m; positions are VE-scaled so they align with the mesh.
    ruler_x = x_max + 8
    ruler_y = y_max
    tick_depths  = np.arange(0, z_min - 0.5, -2)   # [0, -2, -4, ..., z_min]
    ruler_pts    = np.array([[ruler_x, ruler_y, d * VE] for d in tick_depths])
    ruler_labels = [f"{int(abs(d))} m" for d in tick_depths]

    plotter.add_point_labels(
        ruler_pts, ruler_labels,
        font_size=11,
        bold=False,
        text_color="black",
        shape=None,
        always_visible=True,
        show_points=True,
        point_color="black",
        point_size=5,
    )
    # Vertical spine of the ruler
    spine_pts = pv.Line(
        [ruler_x, ruler_y, 0],
        [ruler_x, ruler_y, z_min * VE],
    )
    plotter.add_mesh(spine_pts, color="black", line_width=2)
    plotter.add_text(f"VE = {VE}×", position="lower_right",
                     font_size=10, color="dimgray")

    # ── Distance ruler along X (front edge of block, at surface level) ───────
    dist_y = y_min - 8          # in front of the block
    dist_z = z_max * VE + 1     # just above the scaled surface
    tick_xs     = np.arange(
        round(x_min / 20) * 20,
        x_max + 1, 20
    )                           # ticks every 20 m
    dist_pts    = np.array([[x, dist_y, dist_z] for x in tick_xs])
    dist_labels = [f"{int(x)} m" for x in tick_xs]

    plotter.add_point_labels(
        dist_pts, dist_labels,
        font_size=11,
        bold=False,
        text_color="black",
        shape=None,
        always_visible=True,
        show_points=True,
        point_color="black",
        point_size=5,
    )
    # Horizontal spine of the distance ruler
    dist_spine = pv.Line(
        [x_min, dist_y, dist_z],
        [x_max, dist_y, dist_z],
    )
    plotter.add_mesh(dist_spine, color="black", line_width=2)

    # ── Pre-compute fence panels (one solid slice per profile Y position) ───────
    fence_actors = []
    for num in valid_nums:
        y0 = (num - Y_REF) * Y_SPACING
        panel = vol_disp.slice(normal=[0, 1, 0], origin=[0, y0, 0])
        if panel.n_points == 0:
            continue
        actor = plotter.add_mesh(panel, show_scalar_bar=False, **mesh_kw_no_bar)
        actor.visibility = False
        fence_actors.append(actor)

    # ── Transparent shell + orthogonal slices (SLICES mode) ──────────────────
    shell_actor = plotter.add_mesh(vol_disp, opacity=0.06,
                                   show_scalar_bar=False, **mesh_kw_no_bar)
    plotter.add_mesh_slice_orthogonal(vol_disp, **mesh_kw)

    # ── Mode indicator text ───────────────────────────────────────────────────
    state = {"mode": "slices"}
    mode_actor = plotter.add_text(
        "Mode: SLICES — drag planes to cut  |  T: switch to FENCE",
        position="lower_left", font_size=9, color="dimgray",
    )
    profile_actor = [None]

    # ── Toggle T: SLICES ↔ FENCE diagram ─────────────────────────────────────
    def toggle_mode():
        if state["mode"] == "slices":
            # Hide shell, show solid fence panels
            shell_actor.visibility = False
            for a in fence_actors:
                a.visibility = True
            state["mode"] = "fence"
            mode_actor.SetInput(
                "Mode: FENCE — solid panels per profile  |  T: switch to SLICES"
            )
        else:
            # Show shell, hide fence panels
            shell_actor.visibility = True
            for a in fence_actors:
                a.visibility = False
            state["mode"] = "slices"
            mode_actor.SetInput(
                "Mode: SLICES — drag planes to cut  |  T: switch to FENCE"
            )
        plotter.render()

    plotter.add_key_event("t", toggle_mode)

    # ── Right-click: identify nearest profile ─────────────────────────────────
    # Build a Y→profile-number lookup
    y_map = {n: (n - Y_REF) * Y_SPACING for n in valid_nums}

    def on_right_click(pos_screen):
        # Unproject screen (x,y) to world using the hardware picker
        picker = plotter.iren.interactor.GetPicker()
        picker.Pick(pos_screen[0], pos_screen[1], 0, plotter.renderer)
        world = picker.GetPickPosition()
        if world == (0.0, 0.0, 0.0):
            return                         # missed the mesh
        y_world = world[1]
        nearest = min(y_map, key=lambda k: abs(y_map[k] - y_world))
        dist    = abs(y_map[nearest] - y_world)
        if dist > Y_SPACING:
            return                         # too far from any profile
        # Update overlay
        if profile_actor[0] is not None:
            plotter.remove_actor(profile_actor[0])
        profile_actor[0] = plotter.add_text(
            f"◄  Profile {nearest}  (Y = {y_map[nearest]:.0f} m)",
            position="upper_right", font_size=14, color="navy",
        )
        plotter.render()

    plotter.track_click_position(on_right_click, side="right")

    # ── Camera & axes ─────────────────────────────────────────────────────────
    plotter.add_axes(
        xlabel="Distance (m)",
        ylabel="Profile offset (m)",
        zlabel=f"Depth ×{VE} (m)",
        line_width=2,
    )
    plotter.show_grid()
    plotter.camera_position = "iso"
    plotter.camera.azimuth   = -30
    plotter.camera.elevation =  25

    print("\nControls:")
    print("  T                  : toggle Slices / Volume mode")
    print("  Right-click        : identify nearest profile")
    print("  Left-click + drag  : rotate")
    print("  Scroll             : zoom")
    print("  Right-click + drag : pan")
    print("  Drag plane handles : move cut planes (Slices mode)")
    plotter.show()


if __name__ == "__main__":
    main()
