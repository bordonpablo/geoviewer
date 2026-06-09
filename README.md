# GeoViewer

A Python tool to visualize ERT inversion results from two field sites in the Cottbus–Brandenburg region of Germany: **Weißes Lauch** (profiles 1–12) and **Kleinsee** (profiles 1–4).

There are two ways to explore the data:

- **Map viewer** — a Streamlit web app where you click profile lines on a map to see ERT inversion images
- **3D viewer** — a standalone PyVista window that stacks all ERT profiles into an interpolated 3D resistivity block

---

## Online deployment

The map viewer is deployed on Streamlit Community Cloud:

👉 **[geoviewer.streamlit.app](https://bordonpablo-geoviewer.streamlit.app)**

It updates automatically whenever changes are pushed to the `main` branch.

---

## Local setup

Python 3.10+ required.

**Map viewer only:**
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

**Map viewer + 3D viewer:**
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements_dev.txt
```

---

## Map viewer

```bash
streamlit run app.py
```

This opens `http://localhost:8501`. To open directly in Chrome:

```bash
.\launch.ps1
```

Pick a zone from the sidebar, then click any profile line on the map to see the ERT inversion image. Images can be opened full-screen. Basemap can be switched between OpenStreetMap, Google Satellite, and Google Hybrid.

---

## 3D ERT viewer

```bash
python view3d_ert.py weisseslauch
python view3d_ert.py kleinsee
```

Reads all Res2DInv XYZ exports for the zone, places each profile at its survey Y position, and interpolates onto a 2×2×1 m 3D grid. Depth is exaggerated 5× so the internal structure is readable.

**Controls:**

| Key / Action | Effect |
|---|---|
| `T` | Switch between cut-plane slices and fence diagram view |
| Right-click | Show nearest profile name |
| Left-click drag | Rotate |
| Scroll | Zoom |
| Right-click drag | Pan |
| `R` | Reset camera |
| `X` / `Y` / `Z` | Snap to axis |
| `P` | Save screenshot |

The colormap matches the Surfer output used in the field reports (log scale, 15–2000 Ω·m, dark blue → cyan → green → yellow → orange → red → dark purple).

---

## Adding a new zone

**Map viewer** — create `data/<zone>/` with an `inventory.csv`:

| Column | Description |
|---|---|
| `name` | Profile name |
| `type` | `ERT` |
| `zone` | Zone name |
| `lat`, `lon` | WGS84 center point |
| `start_lat/lon`, `end_lat/lon` | Line endpoints |
| `image_path` | Path to inversion image (PNG/JPG/BMP/TIF) |
| `description` | Any notes |

The zone appears automatically in the app on next restart.

**3D viewer** — add an entry to the `ZONES` dict at the top of `view3d_ert.py`:

```python
"mynewzone": {
    "title":     "My New Zone",
    "xyz_dir":   r"data\MyNewZone\xyz",
    "y_ref":     1,        # profile number at Y = 0
    "y_spacing": 15.0,     # metres between profiles
    "ve":        5,        # vertical exaggeration
    "clim":      [15.0, 2000.0],
    "res":       (2.0, 2.0, 1.0),
    "profiles": {
        1: "profile1.xyz",
        2: "profile2.xyz",
    },
},
```

---

## Project structure

```
geoviewer/
├── app.py                    ← map viewer
├── view3d_ert.py             ← 3D viewer
├── launch.ps1                ← opens map viewer in Chrome
├── requirements.txt
└── data/
    ├── Weißes Lauch/
    │   ├── inventory.csv
    │   ├── ERT images/
    │   ├── em_values/
    │   ├── coordinates/
    │   └── xyz/
    └── Kleinsee/
        ├── inventory.csv
        ├── ERT values/
        ├── coordinates/
        └── xyz/
```

---

## Dependencies

- [Streamlit](https://streamlit.io) — web app
- [Folium](https://python-visualization.github.io/folium/) + streamlit-folium — interactive map
- [Plotly](https://plotly.com/python/) — EM charts
- [Pillow](https://pillow.readthedocs.io) — image display
- [PyVista](https://pyvista.org) — 3D rendering
- [SciPy](https://scipy.org) — 3D interpolation
- [pyproj](https://pyproj4.github.io/pyproj/) — UTM to WGS84 conversion
