"""
Mapa Coropletico Combinado — Zonas Verdes + PM2.5 por Comuna (Medellin)
Muestra:   capa de comunas por PM2.5,  top-5 resaltadas en rojo
           capa de zonas verdes en verde transparente
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
from matplotlib.colors import Normalize
import matplotlib.lines as mlines

# ─────────────────────────────────────────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_GEO_COMUNAS = os.path.join(BASE, "bases_de_datos", "base_datos_comunas", "geojson_limite_catastral_de_comun", "limite_catastral_de_comun.geojson")
RUTA_GEO_VERDES  = os.path.join(BASE, "bases_de_datos", "base_datos_zonas_verdes", "geojson_inventario_zonas_verdes", "inventario_zonas_verdes.geojson")
RUTA_PM25        = os.path.join(BASE, "scripts", "bloque_1", "relaciones_v2_bloque2.csv")
SALIDA           = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mapa_coropletico_pm25_zonas_verdes.png")
SALIDA_ALTA      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mapa_coropletico_pm25_zonas_verdes_alta.png")

# ─────────────────────────────────────────────────────────────────────────────
# 1. Cargar comunas y reproyectar a WGS84
# ─────────────────────────────────────────────────────────────────────────────
gdf_comunas = gpd.read_file(RUTA_GEO_COMUNAS)
gdf_comunas = gdf_comunas.to_crs(epsg=4326)

GEOJSON_MAP = {
    "BELEN":                "Belen",
    "POPULAR":              "Popular",
    "ROBLEDO":              "Robledo",
    "ARANJUEZ":             "Aranjuez",
    "CASTILLA":             "Castilla",
    "GUAYABAL":             "Guayabal",
    "LAURELES":             "Laureles Estadio",
    "MANRIQUE":             "Manrique",
    "PALMITAS":             "Corregimiento de San Sebastian de Palmitas",
    "ALTAVISTA":            "Corregimiento de Altavista",
    "EL POBLADO":           "El Poblado",
    "LA AMERICA":           "La America",
    "SAN JAVIER":           "San Javier",
    "SANTA CRUZ":           "Santa Cruz",
    "SANTA ELENA":          "Corregimiento de Santa Elena",
    "BUENOS AIRES":         "Buenos Aires",
    "LA CANDELARIA":        "La Candelaria",
    "SAN CRISTOBAL":        "Corregimiento de San Cristobal",
    "VILLA HERMOSA":        "Villa Hermosa",
    "DOCE DE OCTUBRE":      "Doce de Octubre",
    "SAN ANTONIO DE PRADO": "Corregimiento de San Antonio de Prado",
}
gdf_comunas["comuna_nombre"] = gdf_comunas["nombre"].map(GEOJSON_MAP)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Cargar datos PM2.5 (anio 2024)
# ─────────────────────────────────────────────────────────────────────────────
df = pd.read_csv(RUTA_PM25)
df_2024 = df[df["año"] == 2024].copy()

gdf_comunas = gdf_comunas.merge(
    df_2024[["comuna", "pm25_promedio_anual"]],
    left_on="comuna_nombre",
    right_on="comuna",
    how="left"
)

# Identificar top 5 (sin duplicados, orden descendente)
top5_df = (gdf_comunas.dropna(subset=["pm25_promedio_anual"])
                     .nlargest(5, "pm25_promedio_anual")
                     .reset_index(drop=True))
top5_nombres = top5_df["comuna_nombre"].tolist()
gdf_comunas["es_top5"] = gdf_comunas["comuna_nombre"].isin(top5_nombres)

print("\nTop 5 PM2.5 2024:")
print(top5_df[["comuna_nombre","pm25_promedio_anual"]].to_string(index=False))

# ── Construir DataFrames por categoria ──
gdf_con_dato = gdf_comunas[gdf_comunas["pm25_promedio_anual"].notna()]
gdf_sin_dato = gdf_comunas[gdf_comunas["pm25_promedio_anual"].isna()]
gdf_top5     = gdf_comunas[gdf_comunas["es_top5"]]
gdf_no_top5  = gdf_comunas[~gdf_comunas["es_top5"] & gdf_comunas["pm25_promedio_anual"].notna()]

# ─────────────────────────────────────────────────────────────────────────────
# 3. Cargar zonas verdes y reproyectar a WGS84
# ─────────────────────────────────────────────────────────────────────────────
gdf_verdes = gpd.read_file(RUTA_GEO_VERDES)
gdf_verdes = gdf_verdes.to_crs(epsg=4326)

print(f"Zonas verdes cargadas: {len(gdf_verdes)} registros")

# ─────────────────────────────────────────────────────────────────────────────
# 4. Escala de color por nivel de PM2.5 (solo para las que tienen datos y no son top-5)
# ─────────────────────────────────────────────────────────────────────────────
valores_no_top5 = gdf_no_top5["pm25_promedio_anual"].dropna()
vmin = valores_no_top5.min()
vmax = valores_no_top5.max()
norm  = Normalize(vmin=vmin, vmax=vmax)
escala = plt.cm.RdYlGn_r  # rojo = alto PM2.5, verde = bajo PM2.5

def color_por_valor(val):
    if pd.isna(val):
        return "#B0BEC5"
    return mcolors.to_hex(escala(norm(val)))

gdf_no_top5 = gdf_no_top5.copy()
gdf_no_top5["color"] = gdf_no_top5["pm25_promedio_anual"].apply(color_por_valor)

# ─────────────────────────────────────────────────────────────────────────────
# 5. DIBUJAR EL MAPA (dos versiones: normal y alta resolucion)
# ─────────────────────────────────────────────────────────────────────────────
COLOR_BORDE      = "#2D4059"
COLOR_BORDE_TOP5 = "#922B21"
COLOR_SIN_DATO   = "#B0BEC5"
ALPHA_VERDES     = 0.55

def dibujar_mapa(figsize=(12, 14), dpi=100, salida="mapa.png"):
    fig, ax = plt.subplots(1, 1, figsize=figsize, facecolor="#F0F4F3")
    ax.set_facecolor("#D6E6DF")

    # ── Zonas verdes (capa base inferior) ──
    gdf_verdes.plot(
        ax=ax, color="#2ECC71", edgecolor="#1E8449",
        linewidth=0.4, alpha=ALPHA_VERDES, zorder=1,
        label="Zonas verdes (inventario)",
    )

    # ── Comunas sin dato PM2.5 ──
    gdf_sin_dato.plot(
        ax=ax, color=COLOR_SIN_DATO,
        edgecolor=COLOR_BORDE, linewidth=0.8, zorder=2,
    )

    # ── Comunas con dato PM2.5 (no top-5) — escala gradual ──
    for _, row in gdf_no_top5.iterrows():
        gdf_no_top5[gdf_no_top5.index == row.name].plot(
            ax=ax,
            color=row["color"],
            edgecolor=COLOR_BORDE, linewidth=0.8,
            zorder=3,
        )

    # ── Comunas sin dato ── re-etiquetadas sin superponer
    gdf_sin_dato.plot(
        ax=ax, color=COLOR_SIN_DATO,
        edgecolor=COLOR_BORDE, linewidth=0.8, zorder=2,
    )

    # ── Top 5 comunas (rojo oscuro) ──
    gdf_top5.plot(
        ax=ax,
        color="#C0392B", edgecolor=COLOR_BORDE_TOP5,
        linewidth=2.2, zorder=4,
        label="Top 5 mayor PM2.5",
    )

    # ── Bordes de comunas (todas, linea delgada) ──
    gdf_comunas.plot(
        ax=ax, facecolor="none",
        edgecolor=COLOR_BORDE, linewidth=0.5,
        zorder=5, alpha=0.9,
    )

    # ── Etiquetas top 5 ──
    for _, row in gdf_top5.iterrows():
        centroid = row.geometry.centroid
        ax.annotate(
            f"{row['comuna_nombre']}\n{row['pm25_promedio_anual']:.1f} ug/m3",
            xy=(centroid.x, centroid.y),
            xytext=(0, 0), textcoords="offset points",
            ha="center", va="center",
            fontsize=7.5, fontweight="bold", color="white",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="#922B21", edgecolor="white",
                linewidth=0.8, alpha=0.92,
            ),
            zorder=6,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Leyenda
    # ─────────────────────────────────────────────────────────────────────────
    # Parches de color por rango PM2.5
    verde_patch = mpatches.Patch(fc="#27AE60", ec=COLOR_BORDE, lw=0.8,
                                  label=f"PM2.5 bajo (~{vmin:.0f} ug/m3)")
    amar_patch  = mpatches.Patch(fc="#F1C40F", ec=COLOR_BORDE, lw=0.8,
                                  label=f"PM2.5 medio (~{(vmin+vmax)/2:.0f} ug/m3)")
    rojo_patch  = mpatches.Patch(fc="#E74C3C", ec=COLOR_BORDE, lw=0.8,
                                  label=f"PM2.5 alto (~{vmax:.0f} ug/m3)")
    t5_patch    = mpatches.Patch(fc="#922B21", ec=COLOR_BORDE_TOP5, lw=1.2,
                                  label="Top 5 comunas con mayor PM2.5")
    verde2_patch = mpatches.Patch(fc="#2ECC71", ec="#1E8449", lw=0.8, alpha=ALPHA_VERDES,
                                   label="Zonas verdes (inventario)")
    gris_patch  = mpatches.Patch(fc=COLOR_SIN_DATO, ec=COLOR_BORDE, lw=0.8,
                                  label="Comunas sin dato PM2.5")

    ax.legend(
        handles=[t5_patch, rojo_patch, amar_patch, verde_patch, verde2_patch, gris_patch],
        loc="lower left", fontsize=8.2,
        title="Mapa coropletico — Medellin",
        title_fontsize=9.5,
        framealpha=0.95, edgecolor=COLOR_BORDE,
    )

    # ── Título ──
    ax.set_title(
        "Mapa Coropletico de Medellin\n"
        "Zonas Verdes superpuesto sobre concentracion de PM2.5 por Comuna (2024)\n"
        "Las 5 comunas con mayor PM2.5 estan resaltadas en rojo oscuro",
        fontsize=12, fontweight="bold", color=COLOR_BORDE, pad=10,
    )

    ax.set_axis_off()
    plt.tight_layout(pad=0.3)
    fig.savefig(salida, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"Mapa guardado en: {salida}")
    plt.close(fig)

# ── Version normal ──
print("\n=== Generando mapa normal ===")
dibujar_mapa(figsize=(12, 14), dpi=120, salida=SALIDA)

# ── Version alta resolucion ──
print("\n=== Generando mapa alta resolucion ===")
dibujar_mapa(figsize=(16, 18), dpi=200, salida=SALIDA_ALTA)

# ── Resumen ──
print("\nTop 5 comunas con mayor PM2.5 (2024):")
for i, (_, row) in enumerate(top5_df.iterrows(), 1):
    print(f"  {i}. {row['comuna_nombre']} — {row['pm25_promedio_anual']:.2f} ug/m3")
