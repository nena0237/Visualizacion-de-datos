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
import folium
from streamlit_folium import st_folium

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
    "data",
    "clean",
    "integracion_v2_pm25_arboles_medellin.csv"
)

RUTA_GEO_COMUNAS = os.path.join(
    BASE_DIR,
    "..",
    "data",
    "raw",
    "base_datos_comunas",
    "geojson_limite_catastral_de_comun",
    "limite_catastral_de_comun.geojson"
)

RUTA_GEO_VERDES = os.path.join(
    BASE_DIR,
    "..",
    "data",
    "raw",
    "base_datos_zonas_verdes",
    "geojson_inventario_zonas_verdes",
    "inventario_zonas_verdes.geojson"
)

RUTA_RESUMEN_B2 = os.path.join(
    BASE_DIR,
    "..",
    "data",
    "clean",
    "resumen_recomendacion_por_comuna.csv"
)

RUTA_GEO_B2 = os.path.join(
    BASE_DIR,
    "..",
    "data",
    "clean",
    "zonas_priorizadas_siembra.geojson"
)

RUTA_LOGO = os.path.join(BASE_DIR, "logo_alcaldia.png")

# ─────────────────────────────────────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Cargando datos...")
def cargar_datos():

    df = pd.read_csv(RUTA_CSV)
    df_resumen = pd.read_csv(RUTA_RESUMEN_B2)

    gdf_comunas = gpd.read_file(RUTA_GEO_COMUNAS).to_crs(epsg=4326)
    gdf_verdes = gpd.read_file(RUTA_GEO_VERDES).to_crs(epsg=4326)
    gdf_b2 = gpd.read_file(RUTA_GEO_B2).to_crs(epsg=4326)

    # limpiar geometrías
    gdf_b2 = gdf_b2[gdf_b2.geometry.notnull()]
    gdf_b2 = gdf_b2[gdf_b2.is_valid]

    # PM2.5 anual
    df_pm25_anual = (
        df.groupby(["año", "comuna"])["pm25_promedio_ug_m3"]
        .mean()
        .reset_index()
        .rename(columns={"pm25_promedio_ug_m3": "pm25_promedio_anual"})
    )

    df_pm25_anual["pm25_promedio_anual"] = (
        df_pm25_anual["pm25_promedio_anual"]
        .round(2)
    )

    # dataframe mapa
    df_mapa = df.groupby(["año", "comuna"]).agg({
        "pm25_promedio_ug_m3": "mean",
        "cantidad_arboles_totales": "sum",
        "cantidad_arboles_mitigadores_pm25": "sum"
    }).reset_index()

    df_mapa["otros_arboles"] = (
        df_mapa["cantidad_arboles_totales"]
        - df_mapa["cantidad_arboles_mitigadores_pm25"]
    )

    return (
        df,
        gdf_comunas,
        gdf_verdes,
        df_pm25_anual,
        df_mapa,
        df_resumen,
        gdf_b2
    )


(
    df,
    gdf_comunas,
    gdf_verdes,
    df_pm25_anual,
    df_mapa,
    df_resumen,
    gdf_b2
) = cargar_datos()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.title("Filtros")

anio = st.sidebar.selectbox(
    "Selecciona el año",
    sorted(df["año"].unique())
)


if os.path.exists(RUTA_LOGO):
    st.sidebar.image(RUTA_LOGO, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# FILTROS
# ─────────────────────────────────────────────────────────────────────────────
df_filtrado = df[df["año"] == anio].copy()

# ─────────────────────────────────────────────────────────────────────────────
# TÍTULO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
    <h1 style='text-align: center; color: #00904C;'>EcoData Lab</h1>
    <h3 style='text-align: center;'> El futuro se siembra en verde</h3>
""", unsafe_allow_html=True)

# Añade un poco de espacio después de los títulos
st.write("---")

# título del dashboard
st.header("🌿 Dashboard de Infraestructura Verde — Medellín")


# ─────────────────────────────────────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Indicadores principales")

# Definimos el estilo de las tarjetas con sombra y borde verde (Efecto 3D)
st.markdown("""
<style>
.kpi-card {
    background-color: #ffffff;
    border-left: 5px solid #00904C;
    border-radius: 10px;
    padding: 20px;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15); /* Sombra para efecto 3D */
    text-align: center;
    margin: 10px;
}
.kpi-title {
    color: #555555;
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    margin-bottom: 10px;
}
.kpi-value {
    color: #00904C;
    font-size: 26px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# Creamos las tres columnas
c1, c2, c3 = st.columns(3)

# Llenamos cada columna con el HTML de la tarjeta
with c1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">PM2.5 promedio</div>
        <div class="kpi-value">{round(df_filtrado['pm25_promedio_ug_m3'].mean(), 2)} <span style="font-size:14px; color:black;">µg/m³</span></div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Árboles mitigadores</div>
        <div class="kpi-value">{int(df_filtrado['cantidad_arboles_mitigadores_pm25'].sum()):,}</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Comunas monitoreadas</div>
        <div class="kpi-value">{df_filtrado['comuna'].nunique()}</div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TABLA
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Datos integrados")

st.dataframe(df_filtrado, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# ALERTA
# ─────────────────────────────────────────────────────────────────────────────
NIVEL_ALERTA = 15

# ─────────────────────────────────────────────────────────────────────────────
# GRÁFICO BARRAS
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Top 5 comunas con mayor contaminación PM2.5")

top5 = (
    df_pm25_anual[df_pm25_anual["año"] == anio]
    .nlargest(5, "pm25_promedio_anual")
    .copy()
)

top5 = top5.sort_values(
    by="pm25_promedio_anual",
    ascending=False
)

top5["color"] = [
    '#FF4B4B' if i < 2 else "#FFD700"
    for i in range(len(top5))
]

fig_top5 = go.Figure(go.Bar(
    x=top5["comuna"],
    y=top5["pm25_promedio_anual"],
    text=top5["pm25_promedio_anual"],
    textposition="outside",
    marker_color=top5["color"]
))

fig_top5.add_shape(
    type="line",
    x0=-0.5,
    y0=NIVEL_ALERTA,
    x1=4.5,
    y1=NIVEL_ALERTA,
    line=dict(color="red", width=2, dash="dash")
)

fig_top5.update_layout(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font_color="black"
)

st.plotly_chart(fig_top5, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# SCATTER
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Relación entre árboles mitigadores y PM2.5")

fig_scatter = px.scatter(
    df_filtrado,
    x="ratio_mitigadores_pct",
    y="pm25_promedio_ug_m3",
    size="cantidad_arboles_totales",
    color="comuna",
    trendline="ols",
    hover_data=["periodo"]
)

fig_scatter.add_hline(
    y=NIVEL_ALERTA,
    line_dash="dash",
    line_color="red",
    annotation_text=f"Límite {NIVEL_ALERTA} µg/m³",
    annotation_position="top right"
)

fig_scatter.update_layout(
    plot_bgcolor="#EAF7F1",
    paper_bgcolor="#EAF7F1",
    height=650
)

st.plotly_chart(fig_scatter, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# MAPA ESTRATÉGICO DE PRIORIZACIÓN
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("🌳 Mapa Estratégico de Prioridad de Reforestación")

st.markdown("""
Este mapa identifica las zonas donde la Secretaría de Medio Ambiente
debería priorizar la siembra de árboles mitigadores de PM2.5,
considerando:

- contaminación PM2.5
- Cuantos árboles mitigadores necesita cada zona verde
- área disponible para siembra
- capacidad estimada de intervención
- y eficiencia de captura de PM2.5
""")

m = folium.Map(
    location=[6.2442, -75.5812],
    zoom_start=11,
    tiles="CartoDB positron"
)

# función colores
def color_prioridad(score):

    if score >= 0.50:
        return "#8B0000"

    elif score >= 0.30:
        return "#FF8C00"

    else:
        return "#228B22"

# dibujar polígonos
for _, row in gdf_b2.iterrows():

    score = row["score_multicriteria"]
    arboles = row["arboles_cupo_estimado"]

    popup_html = f"""
    <div style="font-size:14px;">
    <b>Comuna:</b> {row['comuna']}<br>
    <b>Ranking:</b> #{row['ranking_prioridad_comuna']}<br>
    <b>Score:</b> {score:.2f}<br>
    <b>Especie:</b> {row['nombre_comun_especie']}<br>
    <b>Árboles estimados:</b> {arboles}<br>
    <b>Eficiencia PM2.5:</b> {row['eficiencia_pm25']}<br>
    </div>
    """

    geo_j = folium.GeoJson(
        row["geometry"],
        style_function=lambda x, score=score: {
            "fillColor": color_prioridad(score),
            "color": "black",
            "weight": 0.5,
            "fillOpacity": 0.7,
        },
        tooltip=folium.Tooltip(popup_html),
    )

    geo_j.add_to(m)

# leyenda
legend_html = """
<div style="
position: fixed;
bottom: 50px;
left: 50px;
width: 230px;
height: 170px;
background-color: white;
border:2px solid grey;
z-index:9999;
font-size:14px;
padding: 10px;
border-radius:10px;
">

<b>Prioridad de intervención</b><br><br>

<i style="background:#8B0000;
width:15px;
height:15px;
float:left;
margin-right:8px;"></i>
Alta prioridad<br><br>

<i style="background:#FF8C00;
width:15px;
height:15px;
float:left;
margin-right:8px;"></i>
Media-Alta<br><br>

<i style="background:#FFD700;
width:15px;
height:15px;
float:left;
margin-right:8px;"></i>
Media<br><br>

<i style="background:#228B22;
width:15px;
height:15px;
float:left;
margin-right:8px;"></i>
Baja<br>

</div>
"""

m.get_root().html.add_child(
    folium.Element(legend_html)
)

st_folium(
    m,
    width=1400,
    height=750
)


# ─────────────────────────────────────────────────────────────────────────────
# SIMULACIÓN DINÁMICA
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("Simulación de Impacto por Comuna")

comuna_seleccionada = st.selectbox(
    "Selecciona una comuna:",
    df_resumen["comuna"].unique()
)

datos = df_resumen[
    df_resumen["comuna"] == comuna_seleccionada
].iloc[0]

nivel_actual = datos["pm25_promedio"]

total_a_plantar = st.number_input(
    "Cantidad de árboles a plantar:",
    min_value=1,
    value=int(datos["arboles_a_plantar_total"])
)

resultado = total_a_plantar * 0.007

st.write(
    f"Proyectamos una reducción de "
    f"**{resultado:.2f} µg/m³** de material particulado."
)

# ─────────────────────────────────────────────────────────────────────────────
# GRÁFICO IMPACTO
# ─────────────────────────────────────────────────────────────────────────────
fig = go.Figure(data=[

    go.Bar(
        name='Situación Actual',
        x=['PM2.5'],
        y=[nivel_actual],
        marker_color='#FF4B4B'
    ),

    go.Bar(
        name='Escenario con Proyecto',
        x=['PM2.5'],
        y=[max(0, nivel_actual - resultado)],
        marker_color='rgb(75, 192, 192)'
    )

])

fig.update_layout(
    title=f"Impacto de Especies Mitigadoras en {comuna_seleccionada}",
    yaxis_title="Concentración PM2.5 (µg/m³)",
    barmode='group'
)

fig.add_hline(
    y=NIVEL_ALERTA,
    line_dash="dash",
    line_color="red",
    annotation_text=f"Límite {NIVEL_ALERTA} µg/m³",
    annotation_position="top right"
)

st.plotly_chart(fig, use_container_width=True)
