"""
Mapa Coropletico — Comunas de Medellin por PM2.5 promedio anual
Destaca las 5 comunas con mayor concentracion de PM2.5
"""

import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import warnings
warnings.filterwarnings("ignore")
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import numpy as np
import warnings

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_GEO  = os.path.join(BASE_DIR, "..", "bases_de_datos", "base_datos_comunas", "geojson_limite_catastral_de_comun", "limite_catastral_de_comun.geojson")
RUTA_PM25 = os.path.join(BASE_DIR, "..", "scripts", "bloque_1", "relaciones_v2_bloque2.csv")
SALIDA    = os.path.join(BASE_DIR, "mapa_coropletico_pm25.png")

# ─────────────────────────────────────────────────────────────────────────────
# 1. Cargar GeoJSON de comunas
# ─────────────────────────────────────────────────────────────────────────────
gdf = gpd.read_file(RUTA_GEO)
gdf = gdf.to_crs(epsg=4326)

# Mapeo de nombres del GeoJSON → nombres del CSV
GEOJSON_NOMBRE_MAP = {
    "BELEN":                "Belén",
    "POPULAR":              "Popular",
    "ROBLEDO":              "Robledo",
    "ARANJUEZ":             "Aranjuez",
    "CASTILLA":             "Castilla",
    "GUAYABAL":             "Guayabal",
    "LAURELES":             "Laureles Estadio",
    "MANRIQUE":             "Manrique",
    "PALMITAS":             "Corregimiento de San Sebastián de Palmitas",
    "ALTAVISTA":            "Corregimiento de Altavista",
    "EL POBLADO":           "El Poblado",
    "LA AMERICA":           "La América",
    "SAN JAVIER":           "San Javier",
    "SANTA CRUZ":           "Santa Cruz",
    "SANTA ELENA":          "Corregimiento de Santa Elena",
    "BUENOS AIRES":         "Buenos Aires",
    "LA CANDELARIA":        "La Candelaria",
    "SAN CRISTOBAL":        "Corregimiento de San Cristóbal",
    "VILLA HERMOSA":        "Villa Hermosa",
    "DOCE DE OCTUBRE":      "Doce de Octubre",
    "SAN ANTONIO DE PRADO": "Corregimiento de San Antonio de Prado",
}
gdf["comuna_nombre"] = gdf["nombre"].map(GEOJSON_NOMBRE_MAP)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Cargar datos PM2.5 y filtrar año 2024 (año más completo)
# ─────────────────────────────────────────────────────────────────────────────
df = pd.read_csv(RUTA_PM25)
df_2024 = df[df["año"] == 2024].copy()

# ─────────────────────────────────────────────────────────────────────────────
# 3. Combinar GeoDataFrame con datos PM2.5
# ─────────────────────────────────────────────────────────────────────────────
gdf = gdf.merge(
    df_2024[["comuna", "pm25_promedio_anual"]],
    left_on="comuna_nombre",
    right_on="comuna",
    how="left"
)
gdf = gdf.dropna(subset=["pm25_promedio_anual"])

# ─────────────────────────────────────────────────────────────────────────────
# 4. Identificar las 5 comunas con mayor PM2.5
# ─────────────────────────────────────────────────────────────────────────────
top5 = gdf.nlargest(5, "pm25_promedio_anual")[["comuna_nombre", "pm25_promedio_anual"]].reset_index(drop=True)
print("Top 5 comunas con mayor PM2.5 (anual 2024):")
for i, row in top5.iterrows():
    print(f"  {i+1}. {row['comuna_nombre']} — {row['pm25_promedio_anual']:.2f} µg/m³")

# ─────────────────────────────────────────────────────────────────────────────
# 5. Crear clasificación de colores
#    - Top 5 comunas: rojo oscuro
#    - Otras comunas: escala de verdes
# ─────────────────────────────────────────────────────────────────────────────
gdf["es_top5"] = gdf["comuna_nombre"].isin(top5["comuna_nombre"])

# Copia para visualización
gdf_plot = gdf.copy()

# ─────────────────────────────────────────────────────────────────────────────
# 6. Dibujar el mapa
# ─────────────────────────────────────────────────────────────────────────────
# Colores
COLOR_FONDO_MAPA   = "#7FCDBB"   # verde pastel para comunas sin datos
COLOR_BORDE        = "#2D4059"
COLOR_BORDE_TOP5   = "#C0392B"
COLOR_FONDO_TOP5   = "#E74C3C"

fig, ax = plt.subplots(1, 1, figsize=(12, 14), facecolor="#F0F4F3")
ax.set_facecolor("#D6E6DF")

# ── Capa 1: todas las comunas con color de fondo verde pastel ──
gdf_plot[~gdf_plot["es_top5"]].plot(
    ax=ax,
    color=COLOR_FONDO_MAPA,
    edgecolor=COLOR_BORDE,
    linewidth=0.8,
    zorder=1,
)

# ── Capa 2: las 5 comunas con mayor PM2.5 coloreadas de rojo ──
gdf_plot[gdf_plot["es_top5"]].plot(
    ax=ax,
    color=COLOR_FONDO_TOP5,
    edgecolor=COLOR_BORDE_TOP5,
    linewidth=2.0,
    zorder=2,
)

# ── Rellenar comunas sin datos PM2.5 (que no aparecen en el CSV) ──
# Las comunas sin dato también aparecen en color gris claro
gdf_sin_dato = gdf_plot[gdf_plot["pm25_promedio_anual"].isna()]
if not gdf_sin_dato.empty:
    gdf_sin_dato.plot(
        ax=ax,
        color="#B0BEC5",
        edgecolor=COLOR_BORDE,
        linewidth=0.8,
        zorder=0,
    )

# ── Etiquetas de las 5 comunas ──
for _, row in gdf_plot[gdf_plot["es_top5"]].iterrows():
    centroid = row.geometry.centroid
    ax.annotate(
        f"{row['comuna_nombre']}\n{row['pm25_promedio_anual']:.1f} µg/m³",
        xy=(centroid.x, centroid.y),
        xytext=(0, 0),
        textcoords="offset points",
        ha="center", va="center",
        fontsize=7.5,
        fontweight="bold",
        color="white",
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor=COLOR_FONDO_TOP5,
            edgecolor="white",
            linewidth=0.8,
            alpha=0.92,
        ),
        zorder=3,
    )

# ─────────────────────────────────────────────────────────────────────────────
# 7. Leyenda
# ─────────────────────────────────────────────────────────────────────────────
top5_label   = "Top 5 comunas con mayor PM2.5"
otras_label  = "Otras comunas con datos"
sin_dato_label = "Comunas sin datos PM2.5"

legend_handles = [
    mpatches.Patch(facecolor=COLOR_FONDO_TOP5,    edgecolor=COLOR_BORDE_TOP5,  linewidth=1.0, label=top5_label),
    mpatches.Patch(facecolor=COLOR_FONDO_MAPA,    edgecolor=COLOR_BORDE,       linewidth=1.0, label=otras_label),
    mpatches.Patch(facecolor="#B0BEC5",           edgecolor=COLOR_BORDE,       linewidth=1.0, label=sin_dato_label),
]

ax.legend(
    handles=legend_handles,
    loc="lower left",
    fontsize=9,
    title="PM2.5 promedio anual 2024",
    title_fontsize=10,
    framealpha=0.9,
    edgecolor=COLOR_BORDE,
)

# ─────────────────────────────────────────────────────────────────────────────
# 8. Título y formato final
# ─────────────────────────────────────────────────────────────────────────────
ax.set_title(
    "Mapa Coroplético — Concentración de PM2.5 por Comuna (Medellín, 2024)\n"
    "Las 5 comunas con mayor PM2.5 promedio anual están resaltadas en rojo",
    fontsize=13,
    fontweight="bold",
    color=COLOR_BORDE,
    pad=12,
)

# Quitar ejes
ax.set_axis_off()

plt.tight_layout(pad=0)
fig.savefig(SALIDA, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"\n✔ Mapa guardado en: {SALIDA}")
