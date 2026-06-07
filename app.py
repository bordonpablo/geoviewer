"""GeoViewer — Visualizador interactivo de datos geofísicos."""

import os
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="GeoViewer", page_icon="🌍", layout="wide")

DATA_ROOT = "data"

LINE_COLORS  = {"ERT": "#2166ac", "EM": "#1a9641", "Borehole": "#d94801"}
FILL_COLORS  = {"ERT": "#6baed6", "EM": "#74c476", "Borehole": "#fd8d3c"}
TYPE_LABELS  = {"ERT": "ERT", "EM": "EM", "Borehole": "Sondeo"}

# ── Data loading ──────────────────────────────────────────────────────────────

def list_zones() -> list[str]:
    if not os.path.isdir(DATA_ROOT):
        return []
    return sorted(d for d in os.listdir(DATA_ROOT)
                  if os.path.isdir(os.path.join(DATA_ROOT, d)))


def load_inventory(zone: str) -> pd.DataFrame:
    path = os.path.join(DATA_ROOT, zone, "inventory.csv")
    if not os.path.isfile(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    for col in ["start_lat", "start_lon", "end_lat", "end_lon",
                "image_path", "data_path", "description"]:
        if col not in df.columns:
            df[col] = ""
    df = df.fillna("")
    return df


def _has_line(row: pd.Series) -> bool:
    """True if the row has valid start/end line coordinates."""
    try:
        return (row["start_lat"] != "" and float(row["start_lat"]) != 0)
    except (ValueError, KeyError):
        return False


# ── Map building ──────────────────────────────────────────────────────────────

def build_map(df: pd.DataFrame, show_types: set[str]) -> folium.Map:
    visible = df[df["type"].isin(show_types)]
    if visible.empty:
        center = [51.752, 14.325]
        zoom = 13
    else:
        center = [visible["lat"].mean(), visible["lon"].mean()]
        zoom = 14

    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")

    # Draw one line (or marker) per unique profile name × type combination
    seen = set()
    for _, row in df.iterrows():
        if row["type"] not in show_types:
            continue

        key = (row["name"], row["type"])
        if key in seen:
            continue
        seen.add(key)

        color  = LINE_COLORS.get(row["type"], "#555")
        fcolor = FILL_COLORS.get(row["type"], "#aaa")
        label  = TYPE_LABELS.get(row["type"], row["type"])
        popup_html = (
            f"<b>{row['name']}</b><br>"
            f"Tipo: {label}<br>"
            f"{row['description']}"
        )

        if _has_line(row):
            coords = [
                [float(row["start_lat"]), float(row["start_lon"])],
                [float(row["end_lat"]),   float(row["end_lon"])],
            ]
            folium.PolyLine(
                locations=coords,
                color=color,
                weight=4,
                opacity=0.9,
                tooltip=f"{row['name']} ({label})",
                popup=folium.Popup(popup_html, max_width=220),
            ).add_to(m)
            # Small dot at midpoint for easier clicking
            folium.CircleMarker(
                location=[float(row["lat"]), float(row["lon"])],
                radius=5,
                color=color,
                fill=True,
                fill_color=fcolor,
                fill_opacity=1.0,
                tooltip=f"{row['name']} ({label})",
            ).add_to(m)
        else:
            folium.CircleMarker(
                location=[float(row["lat"]), float(row["lon"])],
                radius=10,
                color=color,
                fill=True,
                fill_color=fcolor,
                fill_opacity=0.9,
                popup=folium.Popup(popup_html, max_width=220),
                tooltip=f"{row['name']} ({label})",
            ).add_to(m)

    return m


# ── Results panel ─────────────────────────────────────────────────────────────

def show_em_chart(csv_path: str, name: str) -> None:
    if not os.path.isfile(csv_path):
        st.warning(f"CSV no encontrado: {csv_path}")
        return
    df = pd.read_csv(csv_path)
    fig = go.Figure()
    if "HL" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["x"], y=df["HL"], name="HL (Horizontal)",
            mode="lines", line=dict(color="#1a9641", width=2),
        ))
    if "VL" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["x"], y=df["VL"], name="VL (Vertical)",
            mode="lines", line=dict(color="#9b59b6", width=2),
        ))
    fig.update_layout(
        title=f"Conductividad aparente — {name}",
        xaxis_title="Distancia (m)",
        yaxis_title="Conductividad (mS/m)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=320,
        margin=dict(l=40, r=20, t=55, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def show_results(df_zone: pd.DataFrame, profile_name: str, clicked_type: str) -> None:
    """Show all available data for the selected profile."""
    profile_rows = df_zone[df_zone["name"] == profile_name]
    if profile_rows.empty:
        st.info("Sin datos para este perfil.")
        return

    # Use any row for metadata
    meta = profile_rows.iloc[0]
    label = TYPE_LABELS.get(clicked_type, clicked_type)
    st.subheader(f"{profile_name}  ·  {meta['zone']}")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Zona:** {meta['zone']}")
    with c2:
        st.markdown(f"**Coord. central:** {float(meta['lat']):.5f}, {float(meta['lon']):.5f}")

    # Description per type
    for _, row in profile_rows.iterrows():
        if row["description"]:
            t = TYPE_LABELS.get(row["type"], row["type"])
            st.caption(f"{t}: {row['description']}")

    st.divider()

    # --- ERT image ---
    ert_row = profile_rows[profile_rows["type"] == "ERT"]
    if not ert_row.empty:
        img_path = ert_row.iloc[0]["image_path"]
        if img_path and os.path.isfile(img_path):
            st.markdown("#### Imagen de inversión ERT")
            img = Image.open(img_path)
            st.image(img, use_container_width=True)
        elif img_path:
            st.info(f"Imagen ERT no encontrada: {img_path}")

    # --- EM chart ---
    em_row = profile_rows[profile_rows["type"] == "EM"]
    if not em_row.empty:
        data_path = em_row.iloc[0]["data_path"]
        if data_path:
            st.markdown("#### Conductividad EM (HL / VL)")
            show_em_chart(data_path, profile_name)

    # --- Borehole ---
    bh_row = profile_rows[profile_rows["type"] == "Borehole"]
    if not bh_row.empty:
        img_path = bh_row.iloc[0]["image_path"]
        if img_path and os.path.isfile(img_path):
            st.markdown("#### Log de sondeo")
            img = Image.open(img_path)
            st.image(img, use_container_width=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar(zones: list[str]) -> tuple[str, set[str]]:
    st.sidebar.title("GeoViewer")
    st.sidebar.markdown("Visualizador de datos geofísicos")
    st.sidebar.divider()

    if not zones:
        st.sidebar.error("No se encontraron zonas en la carpeta 'data/'.")
        return "", set()

    zone = st.sidebar.selectbox("Zona de estudio", zones)

    st.sidebar.markdown("#### Mostrar en mapa")
    show_ert = st.sidebar.checkbox("ERT", value=True)
    show_em  = st.sidebar.checkbox("EM",  value=True)
    show_bh  = st.sidebar.checkbox("Sondeos", value=True)

    visible: set[str] = set()
    if show_ert: visible.add("ERT")
    if show_em:  visible.add("EM")
    if show_bh:  visible.add("Borehole")

    st.sidebar.divider()
    st.sidebar.markdown(
        "**Leyenda**\n"
        "🔵 ERT  \n"
        "🟢 EM  \n"
        "🟠 Sondeos"
    )
    return zone, visible


# ── Click-to-select helper ────────────────────────────────────────────────────

def find_nearest_profile(df: pd.DataFrame, lat: float, lon: float,
                         visible_types: set[str],
                         tol: float = 0.005) -> tuple[str, str] | tuple[None, None]:
    """Return (profile_name, type) of closest visible profile, or (None, None)."""
    sub = df[df["type"].isin(visible_types)].copy()
    if sub.empty:
        return None, None
    sub["dist"] = ((sub["lat"] - lat) ** 2 + (sub["lon"] - lon) ** 2) ** 0.5
    best = sub.loc[sub["dist"].idxmin()]
    if best["dist"] < tol:
        return best["name"], best["type"]
    return None, None


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
        st.caption("Haz clic sobre una línea o marcador para ver los resultados.")
        fmap = build_map(df, visible_types)
        map_data = st_folium(fmap, width=None, height=540,
                             returned_objects=["last_clicked"])

    clicked = map_data.get("last_clicked") if map_data else None
    if clicked:
        name, ctype = find_nearest_profile(
            df, clicked["lat"], clicked["lng"], visible_types
        )
        if name:
            st.session_state["selected_name"] = name
            st.session_state["selected_type"] = ctype

    with col_panel:
        sel_name = st.session_state.get("selected_name")
        if sel_name:
            sel_type = st.session_state.get("selected_type", "ERT")
            show_results(df, sel_name, sel_type)
        else:
            st.markdown("#### Panel de resultados")
            st.info("Selecciona un perfil en el mapa para ver sus resultados.")
            if not df.empty:
                st.markdown("##### Inventario de la zona")
                uniq = (
                    df.drop_duplicates(subset=["name", "type"])[["name", "type", "description"]]
                    .rename(columns={"name": "Nombre", "type": "Tipo",
                                     "description": "Descripción"})
                )
                st.dataframe(uniq, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
