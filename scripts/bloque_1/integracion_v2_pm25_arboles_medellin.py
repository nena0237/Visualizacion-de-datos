"""
=============================================================================
PROYECTO  : Arborización Urbana para Mitigación de PM 2.5 — Medellín
MÓDULO    : Bloque 1 v2 — Limpieza, Geolocalización e Integración
CORRECCIONES v2:
  1. Comunas asignadas por spatial join (coordenadas GPS → polígono catastral)
     en lugar de mapeo manual propenso a errores.
  2. Inventario arbóreo reconstruido desde los 19 archivos oficiales por comuna.
  3. Correlaciones explicadas paso a paso con múltiples métricas.
=============================================================================
SALIDAS:
  integracion_v2_pm25_arboles_medellin.csv  → dataset principal integrado
  relaciones_v2_bloque2.csv                 → indicadores para Bloque 2
  auditoria_estaciones_comunas.csv          → trazabilidad del spatial join
=============================================================================
"""

import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import warnings
import os

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────────────────────────────────────────
BASE       = "../../bases_de_datos/base_datos_arboles/ARBOLES/Data_Raw/ARBOLES_TOTALES/"
BASE_PM25 = "../../bases_de_datos/base_datos_siata/siata/"
RUTA_PM25  = f"{BASE_PM25}/Solicitud_PM25_DP1763941.csv"
RUTA_META  = f"{BASE_PM25}/MetadatosEstacionesPM25Historico.csv"
RUTA_GEO   = f"../../bases_de_datos/base_datos_comunas/geojson_limite_catastral_de_comun/limite_catastral_de_comun.geojson"
RUTA_MITG  = f"../../bases_de_datos/base_datos_arboles/ARBOLES/Data_Clean/ARBOLES.xlsx"   # hoja ESPECIE_REDUCEN: lista de especies mitigadoras

# Archivos de inventario arbóreo por comuna (19 archivos oficiales)
ARCHIVOS_COMUNAS = {
    "Aranjuez":                                    f"{BASE}/ARANJUEZ.xlsx",
    "Belén":                                        f"{BASE}/BELEN.xlsx",
    "Buenos Aires":                                f"{BASE}/BUENOS_AIRES.xlsx",
    "Castilla":                                    f"{BASE}/CASTILLA.xlsx",
    "Corregimiento de Santa Elena":                f"{BASE}/CORRE_SANTA_ELENA.xlsx",
    "Corregimiento de San Cristóbal":              f"{BASE}/CORRE_SAN_CRISTOBAL.xlsx",
    "Corregimiento de San Sebastián de Palmitas":  f"{BASE}/CORRE_SAN_SEBASTIAN.xlsx",
    "Doce de Octubre":                             f"{BASE}/DOCE_OCTUBRE.xlsx",
    "Guayabal":                                    f"{BASE}/GUAYABAL.xlsx",
    "Laureles Estadio":                            f"{BASE}/LAURELES_ESTADIO.xlsx",
    "La América":                                  f"{BASE}/LA_AMERICA.xlsx",
    "La Candelaria":                               f"{BASE}/LA_CANDELARIA.xlsx",
    "Manrique":                                    f"{BASE}/MANRIQUE.xlsx",
    "El Poblado":                                  f"{BASE}/POBLADO.xlsx",
    "Popular":                                     f"{BASE}/POPULAR.xlsx",
    "Robledo":                                     f"{BASE}/ROBLEDO.xlsx",
    "Santa Cruz":                                  f"{BASE}/SANTA_CRUZ.xlsx",
    "San Javier":                                  f"{BASE}/SAN_JAVIER.xlsx",
    "Villa Hermosa":                               f"{BASE}/VILLA_HERMOSA.xlsx",
}

RUTA_SALIDA      = "integracion_v2_pm25_arboles_medellin.csv"
RUTA_RELACIONES  = "relaciones_v2_bloque2.csv"
RUTA_AUDITORIA   = "auditoria_estaciones_comunas.csv"

print("=" * 70)
print("  BLOQUE 1 v2 — INTEGRACIÓN CORREGIDA: PM2.5 + ARBORIZACIÓN")
print("=" * 70)

# ─────────────────────────────────────────────────────────────────────────────
# PASO 1: CARGAR POLÍGONOS CATASTRALES Y REPROJECTAR A WGS84
# ─────────────────────────────────────────────────────────────────────────────
print("\n[1/7] Cargando polígonos catastrales de comunas...")

gdf_comunas = gpd.read_file(RUTA_GEO)

# El GeoJSON está en EPSG:9377 (Colombia Magna-Sirgas Origen Nacional)
# Las coordenadas de las estaciones están en WGS84 (EPSG:4326)
# → Reprojectamos los polígonos a WGS84 para poder hacer el spatial join
gdf_comunas = gdf_comunas.to_crs(epsg=4326)

# Normalizar nombres de comunas desde el GeoJSON
GEOJSON_NOMBRE_MAP = {
    "BELEN":                 "Belén",
    "POPULAR":               "Popular",
    "ROBLEDO":               "Robledo",
    "ARANJUEZ":              "Aranjuez",
    "CASTILLA":              "Castilla",
    "GUAYABAL":              "Guayabal",
    "LAURELES":              "Laureles Estadio",
    "MANRIQUE":              "Manrique",
    "PALMITAS":              "Corregimiento de San Sebastián de Palmitas",
    "ALTAVISTA":             "Corregimiento de Altavista",
    "EL POBLADO":            "El Poblado",
    "LA AMERICA":            "La América",
    "SAN JAVIER":            "San Javier",
    "SANTA CRUZ":            "Santa Cruz",
    "SANTA ELENA":           "Corregimiento de Santa Elena",
    "BUENOS AIRES":          "Buenos Aires",
    "LA CANDELARIA":         "La Candelaria",
    "SAN CRISTOBAL":         "Corregimiento de San Cristóbal",
    "VILLA HERMOSA":         "Villa Hermosa",
    "DOCE DE OCTUBRE":       "Doce de Octubre",
    "SAN ANTONIO DE PRADO":  "Corregimiento de San Antonio de Prado",
}
gdf_comunas["comuna_nombre"] = gdf_comunas["nombre"].map(GEOJSON_NOMBRE_MAP)

print(f"   ✔ {len(gdf_comunas)} polígonos de comunas cargados y reproyectados a WGS84")
print(f"   ✔ Comunas: {sorted(gdf_comunas['comuna_nombre'].dropna().tolist())}")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 2: GEOLOCALIZAR ESTACIONES → SPATIAL JOIN CON POLÍGONOS
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2/7] Geolocalizando estaciones con spatial join (coordenadas → polígono)...")

df_meta = pd.read_csv(RUTA_META, sep=";")

# Las coordenadas vienen con coma decimal (formato colombiano) → convertir
df_meta["lat"] = df_meta["Latitud"].str.replace(",", ".").astype(float)
df_meta["lon"] = df_meta["Longitud"].str.replace(",", ".").astype(float)

# Crear GeoDataFrame de puntos con estaciones
gdf_estaciones = gpd.GeoDataFrame(
    df_meta,
    geometry=gpd.points_from_xy(df_meta["lon"], df_meta["lat"]),
    crs="EPSG:4326"
)

# Spatial join: cada punto → polígono de comuna que lo contiene
gdf_join = gpd.sjoin(
    gdf_estaciones,
    gdf_comunas[["comuna_nombre", "geometry"]],
    how="left",
    predicate="within"
)

# Construir tabla de auditoría: estación → comuna asignada por GIS
df_estacion_comuna = gdf_join[[
    "Nombre", "Nombre_Estacion", "lat", "lon",
    "Municipio", "Estado actual", "comuna_nombre"
]].copy()
df_estacion_comuna.rename(columns={
    "Nombre":           "codigo_estacion",
    "Nombre_Estacion":  "nombre_estacion",
    "lat":              "latitud",
    "lon":              "longitud",
    "Estado actual":    "estado",
    "comuna_nombre":    "comuna_por_gis",
}, inplace=True)

# Guardar auditoría
df_estacion_comuna.to_csv(RUTA_AUDITORIA, index=False, encoding="utf-8-sig")

print(f"\n   RESULTADO DEL SPATIAL JOIN (Corrección de comunas):")
print(f"   {'Estación':<12} {'Nombre':<45} {'Lat':>9} {'Lon':>12}  {'Comuna asignada por GIS'}")
print(f"   {'-'*105}")
for _, r in df_estacion_comuna.iterrows():
    estado_str = f"[{r['estado']}]" if pd.notna(r['estado']) else ""
    print(f"   {r['codigo_estacion']:<12} {r['nombre_estacion']:<45} "
          f"{r['latitud']:>9.4f} {r['longitud']:>12.4f}  "
          f"{str(r['comuna_por_gis']):<30} {estado_str}")

# Diccionario código → comuna (para usar en el pipeline de PM2.5)
ESTACION_COMUNA_GIS = dict(zip(
    df_estacion_comuna["codigo_estacion"],
    df_estacion_comuna["comuna_por_gis"]
))

# Nombre largo de la estación
ESTACION_NOMBRE_LARGO = dict(zip(
    df_estacion_comuna["codigo_estacion"],
    df_estacion_comuna["nombre_estacion"]
))

# ─────────────────────────────────────────────────────────────────────────────
# PASO 3: CARGA Y LIMPIEZA DEL PM2.5 (2023-2025)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3/7] Procesando series de tiempo PM2.5 (SIATA 2023-2025)...")

df_pm = pd.read_csv(RUTA_PM25)
df_pm["Fecha"] = pd.to_datetime(df_pm["Fecha"])
df_pm = df_pm[df_pm["Fecha"].dt.year.isin([2023, 2024, 2025])].copy()
df_pm = df_pm.sort_values("Fecha").reset_index(drop=True)

# Excluir MED-UNNV (inactiva, 0% cobertura en el período)
estaciones_activas = [
    c for c in df_pm.columns
    if c != "Fecha" and c != "MED-UNNV"
]

# Limpieza de valores físicamente imposibles
for col in estaciones_activas:
    df_pm[col] = pd.to_numeric(df_pm[col], errors="coerce")
    df_pm.loc[(df_pm[col] < 0) | (df_pm[col] > 500), col] = np.nan

# Período cuatrimestral
df_pm["año"]  = df_pm["Fecha"].dt.year
df_pm["mes"]  = df_pm["Fecha"].dt.month

def asignar_cuatrimestre(mes):
    if mes <= 4:   return "T1_Ene-Abr"
    elif mes <= 8: return "T2_May-Ago"
    else:          return "T3_Sep-Dic"

df_pm["cuatrimestre"] = df_pm["mes"].apply(asignar_cuatrimestre)
df_pm["periodo"]      = df_pm["año"].astype(str) + "_" + df_pm["cuatrimestre"]

print(f"   ✔ Registros horarios 2023-2025 : {len(df_pm):,}")
print(f"   ✔ Estaciones con datos          : {len(estaciones_activas)}")

# Clasificación OMS
def cat_oms(v):
    if pd.isna(v):  return "Sin datos"
    if v <= 5:      return "Buena (OMS)"
    if v <= 15:     return "Aceptable"
    if v <= 25:     return "Moderada"
    if v <= 35:     return "Dañina sensibles"
    if v <= 45:     return "Dañina general"
    return                  "Muy dañina"

# ─────────────────────────────────────────────────────────────────────────────
# PASO 4: AGREGACIÓN PM2.5 POR ESTACIÓN Y PERÍODO
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4/7] Agregando PM2.5 por estación y cuatrimestre...")

df_long = df_pm.melt(
    id_vars=["Fecha", "año", "mes", "cuatrimestre", "periodo"],
    value_vars=estaciones_activas,
    var_name="codigo_estacion",
    value_name="pm25_ug_m3"
).dropna(subset=["pm25_ug_m3"])

# Agregar estadísticos por estación y período
df_agg = df_long.groupby(
    ["año", "cuatrimestre", "periodo", "codigo_estacion"]
).agg(
    pm25_promedio     = ("pm25_ug_m3", "mean"),
    pm25_maximo       = ("pm25_ug_m3", "max"),
    pm25_p95          = ("pm25_ug_m3", lambda x: x.quantile(0.95)),
    pm25_mediana      = ("pm25_ug_m3", "median"),
    horas_validas     = ("pm25_ug_m3", "count"),
).reset_index()

# Asignar comunas via GIS
df_agg["comuna"]         = df_agg["codigo_estacion"].map(ESTACION_COMUNA_GIS)
df_agg["nombre_estacion"]= df_agg["codigo_estacion"].map(ESTACION_NOMBRE_LARGO)

for col in ["pm25_promedio","pm25_maximo","pm25_p95","pm25_mediana"]:
    df_agg[col] = df_agg[col].round(2)

# Consolidar a nivel COMUNA-PERÍODO (promedio entre estaciones que comparten comuna)
df_pm_comuna = df_agg.groupby(
    ["año", "cuatrimestre", "periodo", "comuna"]
).agg(
    pm25_promedio_comuna  = ("pm25_promedio", "mean"),
    pm25_maximo_comuna    = ("pm25_maximo",   "max"),
    pm25_p95_comuna       = ("pm25_p95",      "mean"),
    pm25_mediana_comuna   = ("pm25_mediana",  "mean"),
    horas_validas_total   = ("horas_validas", "sum"),
    estaciones_nombres    = ("nombre_estacion", lambda x: " | ".join(sorted(set(x.dropna())))),
    codigos_estacion      = ("codigo_estacion", lambda x: " | ".join(sorted(set(x.dropna())))),
    num_estaciones        = ("codigo_estacion", "nunique"),
).reset_index()

for col in ["pm25_promedio_comuna","pm25_maximo_comuna","pm25_p95_comuna","pm25_mediana_comuna"]:
    df_pm_comuna[col] = df_pm_comuna[col].round(2)

df_pm_comuna["categoria_oms"] = df_pm_comuna["pm25_promedio_comuna"].apply(cat_oms)

print(f"   ✔ Estación-período registros    : {len(df_agg)}")
print(f"   ✔ Comuna-período registros      : {len(df_pm_comuna)}")
print(f"   ✔ Comunas con PM2.5 medido      : {df_pm_comuna['comuna'].nunique()}")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 5: INVENTARIO ARBÓREO POR COMUNA (fuente: 19 archivos oficiales)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[5/7] Consolidando inventario arbóreo desde archivos por comuna...")

# Lista de especies mitigadoras de PM2.5 (extraída del ARBOLES.xlsx hoja ESPECIE_REDUCEN)
df_mit_ref = pd.read_excel(RUTA_MITG, sheet_name="ESPECIE_REDUCEN ")
ESPECIES_MITIGADORAS = set(df_mit_ref["ESPECIE"].dropna().str.strip().unique())
print(f"   ✔ Especies mitigadoras PM2.5 en el catálogo: {len(ESPECIES_MITIGADORAS)}")
for e in sorted(ESPECIES_MITIGADORAS):
    print(f"     · {e}")

registros_comunas = []

for comuna, ruta in ARCHIVOS_COMUNAS.items():
    df_c = pd.read_excel(ruta, sheet_name="Datos")
    total = len(df_c)

    # Identificar árboles mitigadores PM2.5 cruzando con lista de especies
    df_c["es_mitigador"] = df_c["ESPECIE"].str.strip().isin(ESPECIES_MITIGADORAS)
    mitigadores = df_c["es_mitigador"].sum()

    # Especies mitigadoras presentes
    especies_presentes = sorted(
        df_c.loc[df_c["es_mitigador"], "NOMBRE COMUN"]
        .dropna().str.strip().unique()
    )
    especies_str = " | ".join(especies_presentes) if especies_presentes else "Ninguna"

    registros_comunas.append({
        "comuna":                              comuna,
        "cantidad_arboles_totales":            total,
        "cantidad_arboles_mitigadores_pm25":   int(mitigadores),
        "ratio_mitigadores_pct":               round(100 * mitigadores / total, 2) if total > 0 else 0.0,
        "especies_mitigadoras_presentes":      especies_str,
    })

df_arboles = pd.DataFrame(registros_comunas)
print(f"\n   INVENTARIO ARBÓREO POR COMUNA:")
print(f"   {'Comuna':<45} {'Total':>7} {'Mitgdrs':>8} {'%':>7}")
print(f"   {'-'*72}")
for _, r in df_arboles.sort_values("cantidad_arboles_totales", ascending=False).iterrows():
    print(f"   {r['comuna']:<45} {r['cantidad_arboles_totales']:>7,} "
          f"{r['cantidad_arboles_mitigadores_pm25']:>8,} "
          f"{r['ratio_mitigadores_pct']:>6.1f}%")

print(f"\n   ✔ Total árboles en inventario   : {df_arboles['cantidad_arboles_totales'].sum():,}")
print(f"   ✔ Total mitigadores PM2.5       : {df_arboles['cantidad_arboles_mitigadores_pm25'].sum():,}")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 6: INTEGRACIÓN FINAL (PM2.5 × COMUNAS × INVENTARIO)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[6/7] Construyendo dataset integrado final...")

df_final = df_pm_comuna.merge(
    df_arboles[[
        "comuna", "cantidad_arboles_totales",
        "cantidad_arboles_mitigadores_pm25",
        "ratio_mitigadores_pct",
        "especies_mitigadoras_presentes"
    ]],
    on="comuna", how="left"
)

# Ordenar columnas
cols = [
    "año", "cuatrimestre", "periodo",
    "comuna", "num_estaciones", "codigos_estacion", "estaciones_nombres",
    "pm25_promedio_comuna", "pm25_mediana_comuna",
    "pm25_maximo_comuna", "pm25_p95_comuna",
    "horas_validas_total", "categoria_oms",
    "cantidad_arboles_totales",
    "cantidad_arboles_mitigadores_pm25",
    "ratio_mitigadores_pct",
    "especies_mitigadoras_presentes",
]
df_final = df_final[cols].sort_values(["año", "cuatrimestre", "comuna"]).reset_index(drop=True)

df_final.rename(columns={
    "pm25_promedio_comuna": "pm25_promedio_ug_m3",
    "pm25_mediana_comuna":  "pm25_mediana_ug_m3",
    "pm25_maximo_comuna":   "pm25_maximo_ug_m3",
    "pm25_p95_comuna":      "pm25_p95_ug_m3",
}, inplace=True)

df_final.to_csv(RUTA_SALIDA, index=False, encoding="utf-8-sig")
print(f"   ✔ Filas dataset final : {len(df_final)}")
print(f"   ✔ Columnas           : {len(df_final.columns)}")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 7: RELACIONES PARA BLOQUE 2 (con explicación de cada fórmula)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[7/7] Calculando relaciones para Bloque 2...")
print("""
  ┌─────────────────────────────────────────────────────────────────────┐
  │  EXPLICACIÓN DE CADA MÉTRICA DE RELACIÓN                           │
  │                                                                     │
  │  A) Correlación de Pearson (r)                                      │
  │     Mide si dos variables numéricas se mueven juntas.              │
  │     Fórmula:                                                        │
  │       r = Σ[(xi - x̄)(yi - ȳ)] / √[Σ(xi-x̄)² · Σ(yi-ȳ)²]         │
  │     Resultado entre -1 y +1.                                        │
  │       +1 = se mueven igual  |  -1 = se mueven opuesto              │
  │       0  = ninguna relación lineal                                  │
  │     Usada para: PM2.5 vs árboles mitigadores, PM2.5 vs ratio       │
  │                                                                     │
  │  B) Score de Vulnerabilidad (compuesto)                             │
  │     Combina ranking de PM2.5 alto + ranking de bajo ratio           │
  │     de mitigadores.                                                 │
  │     Fórmula:                                                        │
  │       score = rank_desc(PM2.5) + rank_asc(arboles_mitigadores)     │
  │     A mayor score → la comuna es más urgente de intervenir.        │
  │     NO es lineal, es ordinal: importa el orden, no el valor.       │
  │                                                                     │
  │  C) Déficit de mitigadores                                          │
  │     ¿Cuántos árboles mitigadores le faltan a cada comuna           │
  │     para llegar a un benchmark del 30%?                             │
  │     Fórmula:                                                        │
  │       déficit = max(0, (0.30 - ratio_actual) × total_arboles)      │
  │     Si el ratio ya es ≥30%, déficit = 0.                            │
  │     El 30% es una meta orientativa; se puede ajustar.             │
  │                                                                     │
  │  D) Ratio mitigadores/km² (densidad espacial)                      │
  │     Cuántos mitigadores hay por cada km² de la comuna.             │
  │     Útil para comparar comunas grandes vs pequeñas.                │
  │     Fórmula:                                                        │
  │       densidad = arboles_mitigadores / area_km2                     │
  │                                                                     │
  │  IMPORTANTE: La correlación entre PM2.5 y árboles es una           │
  │  correlación ECOLÓGICA (entre comunas), no causal.                 │
  │  No significa que los árboles causen PM2.5 ni viceversa.          │
  │  Hay variables de confusión: tráfico, industria, altitud,          │
  │  densidad poblacional, topografía del valle.                        │
  └─────────────────────────────────────────────────────────────────────┘
""")

# Promedio anual por comuna para correlaciones
df_anual = df_final.groupby(["año", "comuna"]).agg(
    pm25_promedio_anual  = ("pm25_promedio_ug_m3", "mean"),
    pm25_maximo_anual    = ("pm25_maximo_ug_m3",   "max"),
    pm25_p95_anual       = ("pm25_p95_ug_m3",      "mean"),
    arb_totales          = ("cantidad_arboles_totales",          "first"),
    arb_mitigadores      = ("cantidad_arboles_mitigadores_pm25", "first"),
    ratio_mitigadores    = ("ratio_mitigadores_pct",             "first"),
).reset_index()

for col in ["pm25_promedio_anual","pm25_maximo_anual","pm25_p95_anual"]:
    df_anual[col] = df_anual[col].round(2)

# A) Correlaciones de Pearson
validos = df_anual.dropna(subset=["pm25_promedio_anual","arb_mitigadores","ratio_mitigadores"])
print(f"  A) CORRELACIONES DE PEARSON (n comunas = {validos['comuna'].nunique()}):")
r_mit = validos["pm25_promedio_anual"].corr(validos["arb_mitigadores"])
r_rat = validos["pm25_promedio_anual"].corr(validos["ratio_mitigadores"])
r_tot = validos["pm25_promedio_anual"].corr(validos["arb_totales"])
print(f"     PM2.5 vs Cantidad árboles mitigadores : r = {r_mit:+.3f}")
print(f"     PM2.5 vs % ratio mitigadores          : r = {r_rat:+.3f}")
print(f"     PM2.5 vs Total árboles                : r = {r_tot:+.3f}")

def interpretar_r(r):
    a = abs(r)
    if a < 0.1:   return "negligible"
    elif a < 0.3: return "débil"
    elif a < 0.5: return "moderada"
    elif a < 0.7: return "fuerte"
    else:         return "muy fuerte"

print(f"\n     Interpretación:")
print(f"     · PM2.5 vs mitigadores ({r_mit:+.3f}, {interpretar_r(r_mit)}): "
      + ("Más contaminada → más árboles sembrados ahí (siembra reactiva)" if r_mit > 0
         else "Más mitigadores → menos PM2.5 (efecto esperado de la arborización)"))
print(f"     · PM2.5 vs ratio       ({r_rat:+.3f}, {interpretar_r(r_rat)}): "
      + ("Mayor % mitigadores no reduce PM2.5 aún" if r_rat > 0
         else "Mayor % mitigadores asociado a menor PM2.5"))

# B) Score de vulnerabilidad
df_anual["rank_pm25"]     = df_anual["pm25_promedio_anual"].rank(ascending=False)
df_anual["rank_deficit"]  = df_anual["ratio_mitigadores"].rank(ascending=True)
df_anual["score_vulnerabilidad"] = (df_anual["rank_pm25"] + df_anual["rank_deficit"]).round(1)
df_anual["ranking_vulnerabilidad"] = df_anual["score_vulnerabilidad"].rank(ascending=False).round(0).astype("Int64")

# C) Déficit de mitigadores (benchmark: 30%)
BENCHMARK = 30.0
df_anual["deficit_pct_mitigadores"] = (BENCHMARK - df_anual["ratio_mitigadores"]).clip(lower=0).round(2)
df_anual["arboles_mitigadores_adicionales"] = (
    (df_anual["deficit_pct_mitigadores"] / 100) * df_anual["arb_totales"]
).fillna(0).round(0).astype(int)

# D) Prioridad de intervención
def prioridad(row):
    pm  = row["pm25_promedio_anual"]
    def_ = row["deficit_pct_mitigadores"]
    if pd.isna(pm): return "⬜ Sin datos PM2.5"
    if pm > 20 and def_ > 15: return "🔴 ALTA – Intervención Urgente"
    if pm > 15 and def_ > 10: return "🟠 MEDIA-ALTA – Prioridad Elevada"
    if pm > 12 or def_ > 10:  return "🟡 MEDIA – Monitoreo Activo"
    return                           "🟢 BAJA – Mantenimiento"

df_anual["prioridad_intervencion"] = df_anual.apply(prioridad, axis=1)

df_anual = df_anual.sort_values(["año","ranking_vulnerabilidad"])
df_anual.to_csv(RUTA_RELACIONES, index=False, encoding="utf-8-sig")

# ─────────────────────────────────────────────────────────────────────────────
# REPORTE FINAL
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  DATASET FINAL — MUESTRA POR PERÍODO")
print("=" * 70)

for periodo in sorted(df_final["periodo"].unique()):
    sub = df_final[df_final["periodo"] == periodo]
    print(f"\n  ── {periodo} ──")
    print(sub[[
        "comuna","pm25_promedio_ug_m3","categoria_oms",
        "cantidad_arboles_totales","cantidad_arboles_mitigadores_pm25","ratio_mitigadores_pct"
    ]].to_string(index=False))

print("\n" + "=" * 70)
print("  RANKING DE PRIORIDAD PARA EL BLOQUE 2 (promedio 2023-2025)")
print("=" * 70)
df_resumen = df_anual.groupby("comuna").agg(
    pm25_prom      = ("pm25_promedio_anual",          "mean"),
    arb_mit        = ("arb_mitigadores",               "first"),
    ratio          = ("ratio_mitigadores",             "first"),
    deficit        = ("deficit_pct_mitigadores",       "mean"),
    adicionales    = ("arboles_mitigadores_adicionales","first"),
    prioridad      = ("prioridad_intervencion",         "last"),
).round(2).reset_index().sort_values("pm25_prom", ascending=False)

print(f"\n  {'Prioridad':<32} {'Comuna':<35} {'PM2.5':>6} {'%Mitg':>6} {'Déficit':>8} {'Adicionales':>12}")
print(f"  {'-'*105}")
for _, r in df_resumen.iterrows():
    arb = int(r["arb_mit"]) if not pd.isna(r["arb_mit"]) else "N/D"
    add = int(r["adicionales"]) if not pd.isna(r["adicionales"]) else "N/D"
    print(f"  {str(r['prioridad']):<32} {r['comuna']:<35} "
          f"{r['pm25_prom']:>6.1f} {r['ratio']:>5.1f}% "
          f"{r['deficit']:>7.1f}% {str(add):>12}")

print("\n" + "=" * 70)
print("  RECOMENDACIONES METODOLÓGICAS PARA BLOQUE 2")
print("=" * 70)
print("""
  Con el dataset integrado ya disponible, el Bloque 2 debe:

  1. CRUZAR con capa de zonas verdes (suelo disponible para siembra):
       → Unión espacial: polígono de zona verde ∩ polígono de comuna
       → Filtrar: zonas con cobertura grama/tierra sin saturación arbórea
       → Variable resultante: "m² disponibles para siembra por comuna"

  2. MODELO DE PRIORIZACIÓN multicriteria (AHP o ponderación simple):
       w1 · PM2.5_promedio  +  w2 · déficit_mitigadores  +  w3 · m²_disponibles
       Pesos sugeridos: w1=0.45, w2=0.35, w3=0.20
       (Ajustables según política pública de la Secretaría)

  3. VARIABLES DE CONTROL a incorporar si se tienen datos:
       · Densidad poblacional (personas expuestas, DANE 2018/2022)
       · Altitud promedio de la comuna (confunde la comparación con C. Santa Elena)
       · Flujo vehicular (SIATA o Secretaría de Movilidad)
       · Índice de masa forestal existente (cobertura, no solo conteo)

  4. VALIDACIÓN DEL BENCHMARK 30%:
       El 30% de mitigadores es orientativo. Para justificarlo técnicamente,
       se necesita literatura de eficiencia de captura de PM2.5 por especie
       en clima tropical urbano (Zygia, Calliandra, Inga, Bauhinia, Retrophyllum).
""")

print("=" * 70)
print("  ARCHIVOS GENERADOS")
print("=" * 70)
print(f"  ✅ Dataset integrado v2   : {RUTA_SALIDA}")
print(f"  ✅ Relaciones Bloque 2    : {RUTA_RELACIONES}")
print(f"  ✅ Auditoría estaciones   : {RUTA_AUDITORIA}")
print("=" * 70)
print("  Pipeline v2 completado.\n")
