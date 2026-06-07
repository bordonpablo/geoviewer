"""GeoViewer — Interactive geophysical data viewer."""

import os
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="GeoViewer", page_icon="🌍", layout="wide")

DATA_ROOT = "data"

LINE_COLORS = {"ERT": "#2166ac", "EM": "#1a9641", "Borehole": "#d94801"}
FILL_COLORS = {"ERT": "#6baed6", "EM": "#74c476", "Borehole": "#fd8d3c"}
TYPE_LABELS = {"ERT": "ERT", "EM": "EM", "Borehole": "Borehole"}

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
    return df.fillna("")


def _has_line(row: pd.Series) -> bool:
    try:
        return row["start_lat"] != "" and float(row["start_lat"]) != 0
    except (ValueError, KeyError):
        return False


# ── Map building ──────────────────────────────────────────────────────────────

def build_map(df: pd.DataFrame, show_types: set[str]) -> folium.Map:
    visible = df[df["type"].isin(show_types)]
    center = ([visible["lat"].mean(), visible["lon"].mean()]
              if not visible.empty else [51.752, 14.325])
    zoom = 14 if not visible.empty else 13

    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")

    seen: set[tuple] = set()
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
        tooltip = f"{row['name']} ({label})"
        popup_html = (
            f"<b>{row['name']}</b><br>"
            f"Type: {label}<br>"
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
                weight=5,
                opacity=0.9,
                tooltip=tooltip,
                popup=folium.Popup(popup_html, max_width=220),
            ).add_to(m)
            # Midpoint dot — gives a reliable click target
            folium.CircleMarker(
                location=[float(row["lat"]), float(row["lon"])],
                radius=6,
                color=color,
                fill=True,
                fill_color=fcolor,
                fill_opacity=1.0,
                tooltip=tooltip,
                popup=folium.Popup(popup_html, max_width=220),
            ).add_to(m)
        else:
            folium.CircleMarker(
                location=[float(row["lat"]), float(row["lon"])],
                radius=10,
                color=color,
                fill=True,
                fill_color=fcolor,
                fill_opacity=0.9,
                tooltip=tooltip,
                popup=folium.Popup(popup_html, max_width=220),
            ).add_to(m)

    return m


# ── Results panel ─────────────────────────────────────────────────────────────

def show_em_chart(csv_path: str, name: str) -> None:
    if not os.path.isfile(csv_path):
        st.warning(f"CSV not found: {csv_path}")
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
        title=f"Apparent conductivity — {name}",
        xaxis_title="Distance (m)",
        yaxis_title="Conductivity (mS/m)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=320,
        margin=dict(l=40, r=20, t=55, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def show_results(df_zone: pd.DataFrame, profile_name: str) -> None:
    profile_rows = df_zone[df_zone["name"] == profile_name]
    if profile_rows.empty:
        st.info("No data for this profile.")
        return

    meta = profile_rows.iloc[0]
    st.subheader(f"{profile_name}  ·  {meta['zone']}")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Zone:** {meta['zone']}")
    with c2:
        st.markdown(f"**Center coords:** {float(meta['lat']):.5f}, {float(meta['lon']):.5f}")

    for _, row in profile_rows.iterrows():
        if row["description"]:
            st.caption(f"{TYPE_LABELS.get(row['type'], row['type'])}: {row['description']}")

    st.divider()

    # ERT image
    ert_row = profile_rows[profile_rows["type"] == "ERT"]
    if not ert_row.empty:
        img_path = ert_row.iloc[0]["image_path"]
        if img_path and os.path.isfile(img_path):
            st.markdown("#### ERT inversion image")
            st.image(Image.open(img_path), use_container_width=True)
        elif img_path:
            st.warning(f"ERT image not found: {img_path}")

    # EM chart
    em_row = profile_rows[profile_rows["type"] == "EM"]
    if not em_row.empty:
        data_path = em_row.iloc[0]["data_path"]
        if data_path:
            st.markdown("#### EM conductivity (HL / VL)")
            show_em_chart(data_path, profile_name)

    # Borehole image
    bh_row = profile_rows[profile_rows["type"] == "Borehole"]
    if not bh_row.empty:
        img_path = bh_row.iloc[0]["image_path"]
        if img_path and os.path.isfile(img_path):
            st.markdown("#### Borehole log")
            st.image(Image.open(img_path), use_container_width=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar(zones: list[str]) -> tuple[str, set[str]]:
    st.sidebar.title("GeoViewer")
    st.sidebar.markdown("Geophysical data viewer")
    st.sidebar.divider()

    if not zones:
        st.sidebar.error("No zones found under 'data/'.")
        return "", set()

    zone = st.sidebar.selectbox("Study zone", zones)

    st.sidebar.markdown("#### Show on map")
    show_ert = st.sidebar.checkbox("ERT",       value=True)
    show_em  = st.sidebar.checkbox("EM",        value=True)
    show_bh  = st.sidebar.checkbox("Boreholes", value=True)

    visible: set[str] = set()
    if show_ert: visible.add("ERT")
    if show_em:  visible.add("EM")
    if show_bh:  visible.add("Borehole")

    st.sidebar.divider()
    st.sidebar.markdown(
        "**Legend**\n"
        "🔵 ERT  \n"
        "🟢 EM  \n"
        "🟠 Boreholes"
    )
    return zone, visible


# ── Click detection ───────────────────────────────────────────────────────────

def _name_from_tooltip(tooltip: str | None) -> str | None:
    """Parse profile name from tooltip string 'Profile 1 (ERT)' → 'Profile 1'."""
    if not tooltip:
        return None
    return tooltip.split(" (")[0].strip()


def find_nearest_profile(df: pd.DataFrame, lat: float, lon: float,
                         visible_types: set[str],
                         tol: float = 0.005) -> str | None:
    sub = df[df["type"].isin(visible_types)].copy()
    if sub.empty:
        return None
    sub["dist"] = ((sub["lat"] - lat) ** 2 + (sub["lon"] - lon) ** 2) ** 0.5
    best = sub.loc[sub["dist"].idxmin()]
    return best["name"] if best["dist"] < tol else None


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    zones = list_zones()
    zone, visible_types = render_sidebar(zones)

    if not zone:
        st.info("Add zone folders under `data/` to get started.")
        return

    df = load_inventory(zone)
    st.title(f"Zone: {zone}")

    col_map, col_panel = st.columns([3, 2], gap="medium")

    with col_map:
        st.markdown("#### Interactive map")
        st.caption("Click a line or marker to view results.")
        fmap = build_map(df, visible_types)
        map_data = st_folium(
            fmap,
            width=None,
            height=540,
            returned_objects=["last_clicked", "last_object_clicked_tooltip"],
        )

    # --- Detect selection ---
    # 1. Tooltip click (PolyLine or CircleMarker)
    tooltip_val = map_data.get("last_object_clicked_tooltip") if map_data else None
    name_from_tooltip = _name_from_tooltip(tooltip_val)

    # 2. Fallback: nearest-neighbour on raw map click
    clicked = map_data.get("last_clicked") if map_data else None
    name_from_click = None
    if clicked and not name_from_tooltip:
        name_from_click = find_nearest_profile(
            df, clicked["lat"], clicked["lng"], visible_types
        )

    selected_name = name_from_tooltip or name_from_click
    if selected_name:
        st.session_state["selected_name"] = selected_name

    with col_panel:
        sel_name = st.session_state.get("selected_name")
        if sel_name:
            show_results(df, sel_name)
        else:
            st.markdown("#### Results panel")
            st.info("Click a profile on the map to view its results.")
            if not df.empty:
                st.markdown("##### Zone inventory")
                uniq = (
                    df.drop_duplicates(subset=["name", "type"])[
                        ["name", "type", "description"]
                    ].rename(columns={
                        "name": "Name", "type": "Type", "description": "Description"
                    })
                )
                st.dataframe(uniq, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
