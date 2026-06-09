# GeoViewer — ERT profiles from Brandenburg peatlands

![3D ERT view](docs/screenshots/Weisses%20Lauch%203d%20view.png)

This project visualizes electrical resistivity tomography (ERT) data from two small lakes in the Cottbus–Brandenburg area of northeastern Germany: **Weißes Lauch** and **Kleinsee**.

## Why ERT near peat-bearing lakes?

Brandenburg sits on a glacial landscape shaped during the last ice age — layers of sand, gravel, and clay left behind by retreating glaciers, often with lakes and wetlands in between. Peat forms in these wet depressions over thousands of years and is ecologically important because it stores large amounts of carbon.

ERT is useful here because the different materials have very different electrical resistivities:

- **Peat**: very low resistivity — it's wet and organic
- **Clay**: low resistivity — fine-grained and holds water
- **Sand and gravel**: high resistivity — dry or well-drained
- **Water-saturated sand**: intermediate

By measuring how electrical current flows through the ground, ERT profiles let us see the shape and depth of peat layers, the thickness of glacial sediments, and the transition between different geological units — without drilling.

---

## Two ways to explore the data

**1. Streamlit web app** — no installation needed, runs in the browser

> 🔗 **[geoviewer-ghwnbvhsbfwvkvxflu2msr.streamlit.app](https://geoviewer-ghwnbvhsbfwvkvxflu2msr.streamlit.app)**

Click on any profile line on the map to see the ERT inversion image for that transect.

**2. Local 3D viewer** — runs on your own machine

All profiles from a survey zone stacked into an interpolated 3D resistivity block. Needs Python and a clone of this repo.

![Kleinsee](docs/images/Kleinsee.jpg)

---

## Setup (for the 3D viewer)

```bash
git clone https://github.com/bordonpablo/geoviewer.git
cd geoviewer

python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements_dev.txt
```

---

## Running things

**Web app (local):**
```bash
pip install -r requirements.txt
streamlit run app.py
```

**3D viewer:**
```bash
python view3d_ert.py weisseslauch
python view3d_ert.py kleinsee
```

Controls once the 3D window opens:

| Key / action | Effect |
|---|---|
| `T` | Switch between interactive cut planes and fence diagram |
| Right-click | Show nearest profile name |
| Left-click drag | Rotate |
| Scroll | Zoom |
| `R` | Reset camera |
| `P` | Save screenshot |

---

## Color scale

Matches the Surfer output from the field reports. Log scale, 15–2000 Ω·m:

`dark blue` → `cyan` → `green` → `yellow` → `brown` → `orange` → `red` → `dark purple`

---

## Adding a new zone

**Web app** — create `data/<zone>/inventory.csv`:

| Column | What it is |
|---|---|
| `name` | Profile name |
| `type` | `ERT` |
| `zone` | Zone name |
| `lat`, `lon` | Center point (WGS84) |
| `start_lat/lon`, `end_lat/lon` | Line endpoints |
| `image_path` | Path to inversion image |
| `description` | Any notes |

The zone appears automatically in the app on next restart.

**3D viewer** — add an entry to `ZONES` at the top of `view3d_ert.py`:

```python
"mynewzone": {
    "title":     "My New Zone",
    "xyz_dir":   r"data\MyNewZone\xyz",
    "y_ref":     1,
    "y_spacing": 15.0,
    "ve":        5,
    "clim":      [15.0, 2000.0],
    "res":       (2.0, 2.0, 1.0),
    "profiles":  {1: "profile1.xyz", 2: "profile2.xyz"},
},
```

---

## Project structure

```
geoviewer/
├── app.py                 ← web map viewer
├── view3d_ert.py          ← 3D viewer
├── requirements.txt       ← web app only
├── requirements_dev.txt   ← full local setup (includes PyVista)
└── data/
    ├── Weisses Lauch/
    │   ├── inventory.csv
    │   ├── ERT images/
    │   ├── coordinates/
    │   └── xyz/
    └── Kleinsee/
        ├── inventory.csv
        ├── ERT values/
        ├── coordinates/
        └── xyz/
```

---

## Stack

[Streamlit](https://streamlit.io) · [Folium](https://python-visualization.github.io/folium/) · [PyVista](https://pyvista.org) · [SciPy](https://scipy.org) · [pyproj](https://pyproj4.github.io/pyproj/) · [Pillow](https://pillow.readthedocs.io)
