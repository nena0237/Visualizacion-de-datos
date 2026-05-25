import warnings
warnings.filterwarnings("ignore")

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.colors import Normalize

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ecodata Lab - Medellín",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.main {
    background-color: white;
}

h1, h2, h3 {
    color: #00904C;
}

[data-testid="stMetricValue"] {
    color: #000000;
}

section[data-testid="stSidebar"] {
    background-color: #F4F7F5;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RUTA_CSV = os.path.join(
    BASE_DIR,
    "..",
    "scripts",
    "bloque_1",
    "integracion_v2_pm25_arboles_medellin.csv"
)

RUTA_GEO_COMUNAS = os.path.join(
    BASE_DIR,
    "..",
    "bases_de_datos",
    "base_datos_comunas",
    "geojson_limite_catastral_de_comun",
    "limite_catastral_de_comun.geojson"
)

RUTA_GEO_VERDES = os.path.join(
    BASE_DIR,
    "..",
    "bases_de_datos",
    "base_datos_zonas_verdes",
    "geojson_inventario_zonas_verdes",
    "inventario_zonas_verdes.geojson"
)

RUTA_LOGO = os.path.join(BASE_DIR, "logo_alcaldia.png")

# ─────────────────────────────────────────────────────────────────────────────
# CARGA DE DATOS 
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Cargando datos...")
def cargar_datos():
    df = pd.read_csv(RUTA_CSV)
    gdf_comunas = gpd.read_file(RUTA_GEO_COMUNAS).to_crs(epsg=4326)
    gdf_verdes = gpd.read_file(RUTA_GEO_VERDES).to_crs(epsg=4326)

    # 1. PM2.5 Anual
    df_pm25_anual = (
        df.groupby(["año", "comuna"])["pm25_promedio_ug_m3"]
        .mean()
        .reset_index()
        .rename(columns={"pm25_promedio_ug_m3": "pm25_promedio_anual"})
    )
    df_pm25_anual["pm25_promedio_anual"] = df_pm25_anual["pm25_promedio_anual"].round(2)

    # 2. Definición y cálculo de df_mapa
    df_mapa = df.groupby(["año", "comuna"]).agg({
        "pm25_promedio_ug_m3": "mean",
        "cantidad_arboles_totales": "sum",
        "cantidad_arboles_mitigadores_pm25": "sum"
    }).reset_index()
    
    # Columna calculada para la idea de tu compañero
    df_mapa["otros_arboles"] = df_mapa["cantidad_arboles_totales"] - df_mapa["cantidad_arboles_mitigadores_pm25"]

    # Retornamos los 5 elementos
    return df, gdf_comunas, gdf_verdes, df_pm25_anual, df_mapa

# Asegúrate de capturar los 5 elementos al llamar a la función
df, gdf_comunas, gdf_verdes, df_pm25_anual, df_mapa = cargar_datos()

# ─────────────────────────────────────────────────────────────────────────────
# MAPEO DE NOMBRES
# ─────────────────────────────────────────────────────────────────────────────
GEOJSON_MAP = {
    "ALTAVISTA": "Altavista",
    "ARANJUEZ": "Aranjuez",
    "BELEN": "Belen",
    "BUENOS AIRES": "Buenos Aires",
    "CASTILLA": "Castilla",
    "DOCE DE OCTUBRE": "Doce de Octubre",
    "EL POBLADO": "El Poblado",
    "GUAYABAL": "Guayabal",
    "LA AMERICA": "La America",
    "LA CANDELARIA": "La Candelaria",
    "LAURELES": "Laureles Estadio",
    "MANRIQUE": "Manrique",
    "PALMITAS": "Corregimiento de San Sebastian de Palmitas",
    "POPULAR": "Popular",
    "ROBLEDO": "Robledo",
    "SAN ANTONIO DE PRADO": "Corregimiento de San Antonio de Prado",
    "SAN CRISTOBAL": "Corregimiento de San Cristobal",
    "SAN JAVIER": "San Javier",
    "SANTA CRUZ": "Santa Cruz",
    "SANTA ELENA": "Corregimiento de Santa Elena",
    "VILLA HERMOSA": "Villa Hermosa",
}

COMUNA_NORMALIZE = {
    "Belén": "Belen",
    "La América": "La America",
    "San Cristóbal": "Corregimiento de San Cristobal",
}

gdf_comunas["comuna_nombre"] = (
    gdf_comunas["nombre"].map(GEOJSON_MAP)
)

df_pm25_anual["comuna_normalizada"] = (
    df_pm25_anual["comuna"].replace(COMUNA_NORMALIZE)
)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.title("Filtros")

anio = st.sidebar.selectbox(
    "Selecciona el año",
    sorted(df["año"].unique())
)

comuna = st.sidebar.selectbox(
    "Selecciona comuna",
    ["Todas"] + sorted(df["comuna"].dropna().unique())
)

if os.path.exists(RUTA_LOGO):
    st.sidebar.image(RUTA_LOGO, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# FILTROS
# ─────────────────────────────────────────────────────────────────────────────
df_filtrado = df[df["año"] == anio].copy()

if comuna != "Todas":
    df_filtrado = df_filtrado[df_filtrado["comuna"] == comuna]

# ─────────────────────────────────────────────────────────────────────────────
# TÍTULO
# ─────────────────────────────────────────────────────────────────────────────
st.title("🌿 Dashboard de Infraestructura Verde — Medellín")

st.markdown("""
Análisis de contaminación PM2.5, arborización urbana y zonas verdes
para apoyar la planeación ambiental de Medellín.
""")

# ─────────────────────────────────────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Indicadores principales")

c1, c2, c3 = st.columns(3)

c1.metric(
    "PM2.5 promedio",
    f"{round(df_filtrado['pm25_promedio_ug_m3'].mean(), 2)} µg/m³"
)

c2.metric(
    "Árboles mitigadores",
    f"{int(df_filtrado['cantidad_arboles_mitigadores_pm25'].sum()):,}"
)

c3.metric(
    "Comunas monitoreadas",
    df_filtrado["comuna"].nunique()
)

# ─────────────────────────────────────────────────────────────────────────────
# TABLA
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Datos integrados")

st.dataframe(
    df_filtrado,
    use_container_width=True
)

# ─────────────────────────────────────────────────────────────────────────────
# TOP 5 COMUNAS
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Top 5 comunas con mayor contaminación PM2.5")

top5 = (
    df_pm25_anual[df_pm25_anual["año"] == anio]
    .nlargest(5, "pm25_promedio_anual")
)

fig_top5 = go.Figure(go.Bar(
    x=top5["comuna"],
    y=top5["pm25_promedio_anual"],
    text=top5["pm25_promedio_anual"],
    textposition="outside",
    marker_color=[
        "#FFD700",
        "#FFD700",
        "#00904C",
        "#00904C",
        "#00904C"
    ]
))

fig_top5.update_layout(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font_color="black",
    xaxis_title="Comuna",
    yaxis_title="PM2.5 (µg/m³)"
)

# Línea de exceso ajustada a 15 µg/m³
fig_top5.add_hline(
    y=15, 
    line_dash="dash", 
    line_color="red", 
    annotation_text="Límite de exceso (15 µg/m³)", 
    annotation_position="bottom right"
)

st.plotly_chart(fig_top5, use_container_width=True)

import folium
from streamlit_folium import st_folium
# ─────────────────────────────────────────────────────────────
# MAPA INTERACTIVO — PM2.5 + ESTACIONES SIATA
# ─────────────────────────────────────────────────────────────

st.divider()
st.subheader("Mapa interactivo de contaminación PM2.5 en Medellín")

# Filtrar datos del año seleccionado
df_mapa = df_pm25_anual[df_pm25_anual["año"] == anio]

# Unir PM2.5 con geometrías
gdf_mapa = gdf_comunas.merge(
    df_mapa,
    left_on="comuna_nombre",
    right_on="comuna_normalizada",
    how="left"
)

# Centro Medellín
mapa = folium.Map(
    location=[6.2442, -75.5812],
    zoom_start=11,
    tiles="cartodbpositron"
)

# Escala de colores
def color_pm25(valor):
    if pd.isna(valor):
        return "#d3d3d3"

    elif valor < 12:
        return "#2ECC71"  # verde

    elif valor < 20:
        return "#F1C40F"  # amarillo

    else:
        return "#E74C3C"  # rojo


# CAPA COMUNAS
folium.GeoJson(
    gdf_mapa,
    style_function=lambda feature: {
        "fillColor": color_pm25(
            feature["properties"]["pm25_promedio_anual"]
        ),
        "color": "black",
        "weight": 1,
        "fillOpacity": 0.7,
    },

    tooltip=folium.GeoJsonTooltip(
        fields=[
            "comuna_nombre",
            "pm25_promedio_anual"
        ],

        aliases=[
            "Comuna:",
            "PM2.5 promedio:"
        ],

        localize=True
    )
).add_to(mapa)

# ─────────────────────────────────────────────────────────────
# ESTACIONES SIATA
# ─────────────────────────────────────────────────────────────

# Coordenadas aproximadas estaciones
estaciones = pd.DataFrame({
    "nombre": [
        "MED-LAYE",
        "MED-ARAN",
        "MED-PJIC",
        "MED-BEME",
        "MED-ALTA"
    ],

    "lat": [
        6.2518,
        6.2760,
        6.1685,
        6.2309,
        6.2000
    ],

    "lon": [
        -75.5636,
        -75.5660,
        -75.6380,
        -75.5971,
        -75.5000
    ]
})

# Agregar marcadores
for _, row in estaciones.iterrows():

    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=7,
        color="black",
        fill=True,
        fill_color="#00904C",
        fill_opacity=1,

        popup=f"""
        <b>Estación:</b> {row['nombre']}
        """
    ).add_to(mapa)

# Mostrar mapa en Streamlit
st_folium(
    mapa,
    width=1200,
    height=650
)

# LEYENDA
st.markdown("""
🟢 Baja contaminación PM2.5  
🟡 Contaminación media  
🔴 Alta contaminación  
⚫ Estaciones SIATA
""")

# ─────────────────────────────────────────────────────────────────────────────
# SCATTER PLOT 
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Relación entre árboles mitigadores y PM2.5")

fig_scatter = px.scatter(
    df_filtrado,
    x="ratio_mitigadores_pct",
    y="pm25_promedio_ug_m3",
    size="cantidad_arboles_totales",
    color="comuna",
    hover_name="comuna",
    # Usamos 'cuatrimestre' porque es la columna que existe en tu dataset
    hover_data={"año": True, "cuatrimestre": True},            
    trendline="ols",
    opacity=0.8,
    labels={
        "ratio_mitigadores_pct": "% árboles mitigadores",
        "pm25_promedio_ug_m3": "PM2.5",
        "cantidad_arboles_totales": "Total árboles",
        "año": "Año",
        "cuatrimestre": "Cuatrimestre"
    }
)

fig_scatter.update_layout(
    plot_bgcolor="#EAF7F1",
    paper_bgcolor="#EAF7F1",
    font_color="black",
    height=650
)

# Línea de exceso ajustada a 15 µg/m³
fig_scatter.add_hline(
    y=15, 
    line_dash="dash", 
    line_color="red", 
    annotation_text="Límite de exceso (15 µg/m³)", 
    annotation_position="bottom right"
)

st.plotly_chart(
    fig_scatter,
    use_container_width=True
)

