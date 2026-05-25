"""
Mapa Coroplético — Medellín (comunas por PM2.5 + zonas verdes superpuestas)
Generado por matplotlib — se guarda como PNG en el dashboard
"""
import sys, io, os, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.colors import Normalize

# ─────────────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RUTA_GEO_COMUNAS = os.path.join(BASE, "bases_de_datos", "base_datos_comunas", "geojson_limite_catastral_de_comun", "limite_catastral_de_comun.geojson")
RUTA_GEO_VERDES  = os.path.join(BASE, "bases_de_datos", "base_datos_zonas_verdes", "geojson_inventario_zonas_verdes", "inventario_zonas_verdes.geojson")
RUTA_PM25        = os.path.join(BASE, "scripts", "bloque_1", "relaciones_v2_bloque2.csv")
SALIDA           = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mapa_coropletico_cache.png")

# ─────────────────────────────────────────────────────────────────────────────
# 1. CARGA
# ─────────────────────────────────────────────────────────────────────────────
gdf_comunas = gpd.read_file(RUTA_GEO_COMUNAS).to_crs(epsg=4326)
gdf_verdes  = gpd.read_file(RUTA_GEO_VERDES).to_crs(epsg=4326)
df_pm25     = pd.read_csv(RUTA_PM25)

GEOJSON_MAP = {
    "ALTAMISTA": "Altamista", "ALTAVISTA": "Altavista",
    "ARANJUEZ": "Aranjuez", "BELEN": "Belen", "BUENOS AIRES": "Buenos Aires",
    "CASTILLA": "Castilla", "DOCE DE OCTUBRE": "Doce de Octubre",
    "EL POBLADO": "El Poblado", "GUAYABAL": "Guayabal",
    "LA AMERICA": "La America", "LA CANDELARIA": "La Candelaria",
    "LAURELES": "Laureles Estadio", "MANRIQUE": "Manrique",
    "PALMITAS": "Corregimiento de San Sebastian de Palmitas",
    "POPULAR": "Popular", "ROBLEDO": "Robledo",
    "SAN ANTONIO DE PRADO": "Corregimiento de San Antonio de Prado",
    "SAN CRISTOBAL": "Corregimiento de San Cristobal",
    "SAN JAVIER": "San Javier", "SANTA CRUZ": "Santa Cruz",
    "SANTA ELENA": "Corregimiento de Santa Elena", "VILLA HERMOSA": "Villa Hermosa",
}
gdf_comunas["comuna_nombre"] = gdf_comunas["nombre"].map(GEOJSON_MAP)

# ─────────────────────────────────────────────────────────────────────────────
# 2. MERGE DE PM2.5 (año 2024)
# ─────────────────────────────────────────────────────────────────────────────
df_sel = df_pm25[df_pm25["año"] == 2024][["comuna", "pm25_promedio_anual"]].copy()

gdf = gdf_comunas.merge(
    df_sel, left_on="comuna_nombre", right_on="comuna", how="left"
)

top5_names = (gdf.dropna(subset=["pm25_promedio_anual"])
                 .nlargest(5, "pm25_promedio_anual")["comuna_nombre"].tolist())
gdf["es_top5"] = gdf["comuna_nombre"].isin(top5_names)

# ─────────────────────────────────────────────────────────────────────────────
# 3. ESCALA DE COLORES
# ─────────────────────────────────────────────────────────────────────────────
COLOR_BORDE  = "#2D4059"
COLOR_TOPO5  = "#5B2C2B"
escala_pm25 = mcolors.LinearSegmentedColormap.from_list(
    "pm25", ["#27AE60", "#F1C40F", "#E74C3C"]
)

gdf_otras = gdf[~gdf["es_top5"]]
vmin, vmax = gdf_otras["pm25_promedio_anual"].min(), gdf_otras["pm25_promedio_anual"].max()
norm = Normalize(vmin=vmin, vmax=vmax)

def color_por_fila(row):
    if row["es_top5"]:
        return "#922B21"
    val = row.get("pm25_promedio_anual", np.nan)
    if pd.isna(val):
        return "#ECEFF1"
    rgba = escala_pm25(norm(val))
    return rgba

gdf["color_fill"] = gdf.apply(color_por_fila, axis=1)

# ─────────────────────────────────────────────────────────────────────────────
# 4. DIBUJAR MAPA
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 1, figsize=(11, 13), facecolor="#F5F9F7")
ax.set_facecolor("#DCEFEA")

# Zonas verdes (capa inferior, muy delgada)
gdf_verdes.plot(ax=ax, color="#2ECC71", edgecolor="none",
                linewidth=0, alpha=0.35, zorder=1)

# Todas las comunas coloreadas por PM2.5
for _, row in gdf.iterrows():
    gdf[gdf.index == row.name].plot(
        ax=ax, color=row["color_fill"],
        edgecolor=COLOR_BORDE, linewidth=0.85,
        zorder=2,
    )

# Top 5 — resaltar con borde grueso rojo
for nombre in top5_names:
    sub = gdf[gdf["comuna_nombre"] == nombre]
    if not sub.empty:
        val = sub["pm25_promedio_anual"].values[0]
        sub.plot(ax=ax, color="#922B21", edgecolor=COLOR_TOPO5,
                 linewidth=2.8, zorder=3)

# Etiquetas top 5
for nombre in top5_names:
    sub = gdf[gdf["comuna_nombre"] == nombre]
    if not sub.empty:
        c = sub.geometry.centroid.values[0]
        val = sub["pm25_promedio_anual"].values[0]
        ax.annotate(
            f"{nombre}\n{val:.1f} ug/m3",
            xy=(c.x, c.y), xytext=(0, 0), textcoords="offset points",
            ha="center", va="center", fontsize=7.5, fontweight="bold",
            color="white",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#922B21",
                      edgecolor="white", linewidth=0.9, alpha=0.92),
            zorder=4,
        )

# ── Leyenda ──
legend_items = [
    mpatches.Patch(fc="#922B21", ec=COLOR_TOPO5, lw=1.0,
                   label="Top 5 mayor PM2.5"),
    mpatches.Patch(fc="#E74C3C", ec=COLOR_BORDE, lw=0.8,
                   label=f"PM2.5 alto (~{vmax:.0f} ug/m3)"),
    mpatches.Patch(fc="#F1C40F", ec=COLOR_BORDE, lw=0.8,
                   label=f"PM2.5 medio (~{(vmin+vmax)/2:.0f} ug/m3)"),
    mpatches.Patch(fc="#27AE60", ec=COLOR_BORDE, lw=0.8,
                   label=f"PM2.5 bajo (~{vmin:.0f} ug/m3)"),
    mpatches.Patch(fc="#2ECC71", ec="#1E8449", lw=0.6, alpha=0.6,
                   label="Zonas verdes (inventario)"),
    mpatches.Patch(fc="#ECEFF1", ec=COLOR_BORDE, lw=0.8,
                   label="Comunas sin datos PM2.5"),
]

ax.legend(handles=legend_items, loc="lower left", fontsize=8.2,
          title="PM2.5 promedio anual 2024",
          title_fontsize=9.5, framealpha=0.95, edgecolor=COLOR_BORDE)

ax.set_title(
    "Mapa Coroplético — Concentracion de PM2.5 por Comuna (Medellín 2024)\n"
    "Top 5 con mayor PM2.5 resaltadas en rojo oscuro  ·  "
    "Zonas verdes superpuestas semitransparentes",
    fontsize=12, fontweight="bold", color=COLOR_BORDE, pad=10,
)
ax.set_axis_off()
plt.tight_layout(pad=0.3)
fig.savefig(SALIDA, dpi=160, bbox_inches="tight",
            facecolor=fig.get_facecolor(), format="png")
plt.close(fig)

print(f"Mapa guardado: {SALIDA}")
print("Top 5 comunas con mayor PM2.5 (2024):")
for i, n in enumerate(top5_names, 1):
    v = gdf.loc[gdf["comuna_nombre"] == n, "pm25_promedio_anual"].values[0]
    print(f"  {i}. {n}: {v:.2f} ug/m3")
