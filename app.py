"""GeoViewer — Visualizador interactivo de datos geofísicos."""

import os
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from PIL import Image

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GeoViewer",
    page_icon="🌍",
    layout="wide",
)

# ── Constants ─────────────────────────────────────────────────────────────────
DATA_ROOT = "data"
MARKER_COLORS = {"ERT": "blue", "EM": "green", "Borehole": "orange"}
TYPE_LABELS = {"ERT": "ERT", "EM": "EM", "Borehole": "Sondeo"}

# ── Data loading ──────────────────────────────────────────────────────────────

def list_zones() -> list[str]:
    """Return sorted list of zone folders found under DATA_ROOT."""
    if not os.path.isdir(DATA_ROOT):
        return []
    return sorted(
        d for d in os.listdir(DATA_ROOT)
        if os.path.isdir(os.path.join(DATA_ROOT, d))
    )


def load_inventory(zone: str) -> pd.DataFrame:
    """Load inventory.csv for the given zone; return empty df on error."""
    path = os.path.join(DATA_ROOT, zone, "inventory.csv")
    if not os.path.isfile(path):
        return pd.DataFrame(columns=["name", "type", "zone", "lat", "lon",
                                     "image_path", "data_path", "description"])
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    df = df.fillna("")
    return df


# ── Map building ──────────────────────────────────────────────────────────────

def build_map(df: pd.DataFrame, show_types: set[str]) -> folium.Map:
    """Build a Folium map with markers for each row in df."""
    if df.empty:
        center = [51.752, 14.325]
        zoom = 13
    else:
        center = [df["lat"].mean(), df["lon"].mean()]
        zoom = 13

    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")

    for _, row in df.iterrows():
        if row["type"] not in show_types:
            continue

        color = MARKER_COLORS.get(row["type"], "gray")
        label = TYPE_LABELS.get(row["type"], row["type"])

        popup_html = (
            f"<b>{row['name']}</b><br>"
            f"Tipo: {label}<br>"
            f"Zona: {row['zone']}<br>"
            f"{row['description']}"
        )

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=10,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=row["name"],
        ).add_to(m)

    return m


# ── Results panel ─────────────────────────────────────────────────────────────

def show_em_chart(csv_path: str, name: str) -> None:
    """Render a Plotly line chart for EM conductivity data."""
    if not os.path.isfile(csv_path):
        st.warning(f"Archivo CSV no encontrado: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    fig = go.Figure()

    if "HL" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["x"], y=df["HL"],
            name="HL (Horizontal)", mode="lines+markers",
            line=dict(color="#2ecc71", width=2),
        ))
    if "VL" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["x"], y=df["VL"],
            name="VL (Vertical)", mode="lines+markers",
            line=dict(color="#9b59b6", width=2),
        ))

    fig.update_layout(
        title=f"Conductividad aparente — {name}",
        xaxis_title="Distancia (m)",
        yaxis_title="Conductividad (mS/m)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=350,
        margin=dict(l=40, r=20, t=60, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def show_results(row: pd.Series) -> None:
    """Render the results panel for the selected element."""
    st.subheader(f"{TYPE_LABELS.get(row['type'], row['type'])} — {row['name']}")

    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        st.markdown(f"**Zona:** {row['zone']}")
        st.markdown(f"**Tipo:** {TYPE_LABELS.get(row['type'], row['type'])}")
    with col_meta2:
        st.markdown(f"**Coordenadas:** {row['lat']:.4f}, {row['lon']:.4f}")
        st.markdown(f"**Descripción:** {row['description']}")

    st.divider()

    # Image (ERT, EM, or borehole)
    if row["image_path"] and os.path.isfile(row["image_path"]):
        img = Image.open(row["image_path"])
        st.image(img, use_container_width=True,
                 caption=f"Imagen de inversión — {row['name']}")
    elif row["image_path"]:
        st.info(f"Imagen no disponible en: {row['image_path']}")

    # EM conductivity chart
    if row["type"] == "EM" and row["data_path"]:
        st.markdown("#### Perfil de conductividad")
        show_em_chart(row["data_path"], row["name"])


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar(zones: list[str]) -> tuple[str, set[str]]:
    """Render sidebar controls; return (selected_zone, visible_types)."""
    st.sidebar.title("GeoViewer")
    st.sidebar.markdown("Visualizador de datos geofísicos")
    st.sidebar.divider()

    if not zones:
        st.sidebar.error("No se encontraron zonas en la carpeta 'data/'.")
        return "", set()

    zone = st.sidebar.selectbox("Zona de estudio", zones)

    st.sidebar.markdown("#### Filtrar por tipo")
    show_ert = st.sidebar.checkbox("ERT", value=True)
    show_em = st.sidebar.checkbox("EM", value=True)
    show_bh = st.sidebar.checkbox("Sondeos", value=True)

    visible: set[str] = set()
    if show_ert:
        visible.add("ERT")
    if show_em:
        visible.add("EM")
    if show_bh:
        visible.add("Borehole")

    st.sidebar.divider()
    st.sidebar.markdown(
        "**Leyenda**\n"
        "🔵 ERT  \n"
        "🟢 EM  \n"
        "🟠 Sondeos"
    )

    return zone, visible


# ── Click-to-select helper ────────────────────────────────────────────────────

def find_nearest(df: pd.DataFrame, lat: float, lon: float,
                 visible_types: set[str], tol: float = 0.003) -> pd.Series | None:
    """Return the closest row to (lat, lon) within tol degrees, or None."""
    sub = df[df["type"].isin(visible_types)].copy()
    if sub.empty:
        return None
    sub["dist"] = ((sub["lat"] - lat) ** 2 + (sub["lon"] - lon) ** 2) ** 0.5
    best = sub.loc[sub["dist"].idxmin()]
    return best if best["dist"] < tol else None


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    zones = list_zones()
    zone, visible_types = render_sidebar(zones)

    if not zone:
        st.info("Agrega zonas bajo la carpeta `data/` para comenzar.")
        return

    df = load_inventory(zone)

    st.title(f"Zona: {zone}")

    col_map, col_panel = st.columns([3, 2], gap="medium")

    with col_map:
        st.markdown("#### Mapa interactivo")
        st.caption("Haz clic en un marcador para ver sus resultados.")
        fmap = build_map(df, visible_types)
        map_data = st_folium(fmap, width=None, height=520, returned_objects=["last_clicked"])

    # Detect click
    clicked = map_data.get("last_clicked") if map_data else None

    if clicked:
        hit = find_nearest(df, clicked["lat"], clicked["lng"], visible_types)
        if hit is not None:
            st.session_state["selected"] = hit.to_dict()

    with col_panel:
        if "selected" in st.session_state and st.session_state["selected"]:
            selected = pd.Series(st.session_state["selected"])
            show_results(selected)
        else:
            st.markdown("#### Panel de resultados")
            st.info("Selecciona un elemento en el mapa para ver sus resultados.")

            # Summary table
            if not df.empty:
                st.markdown("##### Inventario de la zona")
                display_df = df[["name", "type", "description"]].copy()
                display_df.columns = ["Nombre", "Tipo", "Descripción"]
                st.dataframe(display_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
