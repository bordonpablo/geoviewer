# GeoViewer

Interactive visualization tool for geophysical survey results from the **Cottbus–Brandenburg** area, Germany. Covers three study zones:

- **Cottbus** — reference zone with dummy data
- **Weisses Lauch** — ERT profiles (1–12) and DUALEM EM surveys
- **Kleinsee** — ERT profiles (1–4)

Two viewers are included:

| Viewer | How to run | What it shows |
|---|---|---|
| **Map viewer** (Streamlit) | `streamlit run app.py` | Interactive web map with ERT inversion images and EM conductivity charts |
| **3D viewer** (PyVista) | `python view3d_ert.py <zone>` | Interpolated 3D resistivity block with fence diagram and orthogonal slices |

---

## Requirements

- Python 3.10 or higher
- Windows (tested on Windows 11)

---

## Installation

```bash
# 1. Create virtual environment
python -m venv .venv

# 2. Activate (Windows)
.\.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Map viewer

```bash
streamlit run app.py
```

Opens automatically at `http://localhost:8501`. Or use the Chrome launcher:

```bash
.\launch.ps1
```

### Features
- Zone selector (auto-detects subfolders under `data/`)
- ERT and EM profile lines drawn on an interactive map (OpenStreetMap, Google Satellite, Google Hybrid)
- Click any profile line to view its ERT inversion image and EM conductivity chart (HL/VL)
- Full-screen image modal for ERT profiles
- Selected profile highlighted; others dimmed
- Profile name labels on the map

---

## 3D ERT viewer

```bash
python view3d_ert.py weisseslauch
python view3d_ert.py kleinsee
```

Reads Res2DInv XYZ exports, interpolates all profiles onto a regular 3D grid (scipy griddata, 2×2×1 m resolution), and renders an interactive PyVista scene.

### Controls

| Key / Action | Effect |
|---|---|
| `T` | Toggle between **Slices** mode (interactive cut planes) and **Fence** mode (solid panels per profile) |
| Right-click | Identify nearest profile (shown top-right) |
| Left-click + drag | Rotate |
| Scroll | Zoom |
| Right-click + drag | Pan |
| `R` | Reset camera |
| `X` / `Y` / `Z` | Snap to axis view |
| `P` | Save screenshot |
| Drag plane handles | Move orthogonal cut planes (Slices mode) |

### Color scale
Custom ERT colormap matching Surfer output, log scale 15–2000 Ω·m:

| Range (Ω·m) | Color |
|---|---|
| 15–25 | Dark blue |
| 25–35 | Blue |
| 35–55 | Cyan |
| 55–85 | Light green |
| 85–115 | Yellow-green |
| 115–155 | Yellow |
| 155–200 | Brown / tan |
| 200–300 | Orange |
| 300–500 | Red |
| 500–1000 | Dark red |
| 1000–2000 | Dark purple |

---

## Adding a new zone

### Map viewer
1. Create `data/<zone_name>/` with subfolders `ert/`, `em/`, `em_values/`
2. Add `inventory.csv`:

| Column | Description |
|---|---|
| `name` | Profile identifier |
| `type` | `ERT` or `EM` |
| `zone` | Zone name (matches subfolder) |
| `lat` / `lon` | WGS84 center coordinates |
| `start_lat/lon`, `end_lat/lon` | Line endpoints (for drawing on map) |
| `image_path` | Relative path to inversion image (PNG/JPG/BMP) |
| `data_path` | Relative path to EM CSV (columns `x`, `HL`, `VL`) |
| `description` | Free text |

3. Restart the app — the zone appears automatically in the sidebar selector.

### 3D viewer
Add a new entry to the `ZONES` dict at the top of `view3d_ert.py`:

```python
"mynewzone": {
    "title":     "My New Zone",
    "xyz_dir":   r"data\MyNewZone\xyz",
    "y_ref":     1,        # profile number placed at Y = 0
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

Then run: `python view3d_ert.py mynewzone`

---

## Project structure

```
geoviewer/
├── app.py                    ← Streamlit map viewer
├── view3d_ert.py             ← PyVista 3D viewer
├── launch.ps1                ← Chrome launcher for map viewer
├── requirements.txt
└── data/
    ├── cottbus/              ← dummy data (reference zone)
    ├── Weisses Lauch/
    │   ├── inventory.csv
    │   ├── ERT images/       ← inversion images (JPG/BMP)
    │   ├── em_values/        ← per-profile EM CSVs
    │   ├── coordinates/      ← UTM profile coordinates
    │   └── xyz/              ← Res2DInv XYZ exports for 3D viewer
    └── Kleinsee/
        ├── inventory.csv
        ├── ERT values/       ← inversion images (JPG/TIF)
        ├── coordinates/
        └── xyz/              ← Res2DInv XYZ exports for 3D viewer
```

---

## Stack

- [Streamlit](https://streamlit.io) — web app framework
- [Folium](https://python-visualization.github.io/folium/) + streamlit-folium — interactive map
- [Plotly](https://plotly.com/python/) — EM conductivity charts
- [Pillow](https://pillow.readthedocs.io) — image display
- [PyVista](https://pyvista.org) — 3D visualization
- [SciPy](https://scipy.org) — 3D grid interpolation
- [pyproj](https://pyproj4.github.io/pyproj/) — UTM → WGS84 coordinate conversion
