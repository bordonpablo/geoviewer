# GeoViewer

Visualizador interactivo de datos geofísicos (ERT, EM, sondeos) construido con Streamlit y Folium.

## Requisitos

- Python 3.10 o superior

## Instalación

```bash
# 1. Crear entorno virtual
python -m venv .venv

# 2. Activarlo (Windows)
.\.venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

## Uso

```bash
streamlit run app.py
```

El navegador abre automáticamente en `http://localhost:8501`.

## Agregar datos reales

1. Coloca tus archivos bajo `data/<zona>/` (ej. `data/austria/`)
2. Crea un `inventory.csv` con esta estructura:

| Campo | Descripción |
|---|---|
| `name` | Identificador del perfil o sondeo |
| `type` | `ERT`, `EM` o `Borehole` |
| `zone` | Nombre de la zona (coincide con la subcarpeta) |
| `lat` / `lon` | Coordenadas WGS84 del punto central |
| `image_path` | Ruta relativa a la imagen de inversión (PNG/JPG) |
| `data_path` | Ruta relativa al CSV de valores EM (columnas `x`, `HL`, `VL`) |
| `description` | Texto libre |

3. Reinicia la app — la zona aparece automáticamente en el selector del sidebar.

## Estructura del proyecto

```
geoviewer/
├── app.py
├── requirements.txt
└── data/
    └── cottbus/               ← zona de ejemplo con datos dummy
        ├── inventory.csv
        ├── ert/
        ├── em/
        ├── em_values/
        └── boreholes/
```

## Stack

- [Streamlit](https://streamlit.io) — interfaz web
- [Folium](https://python-visualization.github.io/folium/) + streamlit-folium — mapa interactivo
- [Plotly](https://plotly.com/python/) — gráficos de perfiles EM
- [Pillow](https://pillow.readthedocs.io) — visualización de imágenes
