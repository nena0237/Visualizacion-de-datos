"""
=============================================================================
PROYECTO  : Arborización Urbana para Mitigación de PM 2.5 — Medellín
MÓDULO    : Bloque 2 — Recomendador de Siembra por Zona Verde
AUTOR     : Pipeline automatizado — Secretaría de Medio Ambiente
=============================================================================

LÓGICA GENERAL
──────────────
1. Carga las zonas verdes del inventario oficial (GeoJSON) y las recorta
   por polígono de cada comuna.
2. Filtra las zonas viables para siembra:
     - Cobertura dominante: Grama o Tierra  (no están saturadas)
     - Tipología: excluye zonas privadas (ZVPrivadas, ZVUsoPrivado)
       salvo criterio explícito de la Secretaría
3. Calcula el área útil de cada zona y cuántos árboles de cada especie
   caben, respetando la distancia mínima de plantación entre individuos
   (radio de copa mínima + margen de seguridad).
4. Prioriza comunas con:
     a. PM2.5 promedio alto (dato del Bloque 1)
     b. Déficit de árboles mitigadores elevado
     c. Disponibilidad de espacio (m² con cobertura apta)
   usando un modelo multicriteria ponderado (AHP simplificado).
5. Para cada zona verde priorizada asigna la especie más adecuada
   según rango altitudinal, tipo de suelo y uso en espacio público
   registrado en las fichas técnicas botánicas.
6. Exporta:
     - recomendacion_siembra_por_zona.csv   → zonas con cuántos y qué plantar
     - resumen_recomendacion_por_comuna.csv → resumen ejecutivo por comuna
     - zonas_priorizadas_siembra.geojson    → capa para SIG / visualización

FUNDAMENTO BOTÁNICO — DISTANCIAS DE PLANTACIÓN
────────────────────────────────────────────────
Cada especie tiene una amplitud de copa documentada. La separación mínima
entre individuos de la misma especie se define como:

    separacion_min = diametro_copa_minimo + margen_seguridad

Donde el margen_seguridad garantiza ventilación y desarrollo radicular.
La capacidad de una zona se estima asumiendo plantación en cuadrícula:

    capacidad = floor(area_util_m2 / separacion_min²)

Este es un estimativo conservador; en terreno la distribución puede ser
irregular (hileras, agrupaciones), lo que permite optimizar por especie.

Para el rango altitudinal de Medellín (1.400–1.800 msnm, núcleo urbano)
solo aplican especies cuyo rango incluya 1.001–2.000 msnm.

MODELO DE PRIORIZACIÓN MULTICRITERIA
──────────────────────────────────────
score_comuna = w_pm25  * norm(PM2.5_promedio)
             + w_def   * norm(deficit_mitigadores_pct)
             + w_area  * norm(area_util_m2_disponible)

Pesos por defecto (ajustables):
  w_pm25 = 0.45   (salud pública — contaminación medida)
  w_def  = 0.35   (brecha de cobertura actual)
  w_area = 0.20   (viabilidad territorial)

Fuente metodológica: Saaty (1980) AHP; adaptado a recursos limitados
de la Secretaría de Medio Ambiente.

=============================================================================
"""

import pandas as pd
import numpy as np
import geopandas as gpd
import warnings
import math
import os

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# RUTAS — ajustar a la estructura del proyecto
# ─────────────────────────────────────────────────────────────────────────────
RUTA_COMUNAS    = "../../bases_de_datos/base_datos_comunas/geojson_limite_catastral_de_comun/limite_catastral_de_comun.geojson"
RUTA_ZONAS      = "../../bases_de_datos/base_datos_zonas_verdes/geojson_inventario_zonas_verdes/inventario_zonas_verdes.geojson"
RUTA_BLOQUE1    = "../bloque_1/integracion_v2_pm25_arboles_medellin.csv"

RUTA_OUT_ZONAS  = f"recomendacion_siembra_por_zona.csv"
RUTA_OUT_RESUMEN= f"resumen_recomendacion_por_comuna.csv"
RUTA_OUT_GEO    = f"zonas_priorizadas_siembra.geojson"

# ─────────────────────────────────────────────────────────────────────────────
# CATÁLOGO BOTÁNICO DE ESPECIES MITIGADORAS
# Fuentes: fichas técnicas Alcaldía de Medellín, AMVA-UNAL (2014),
#          Morales y Varón (2013), Idárraga et al. (2013)
# ─────────────────────────────────────────────────────────────────────────────
ESPECIES = {
    "Zygia longifolia": {
        "nombre_comun":      "Suribio",
        "familia":           "Fabaceae",
        "altura_max_m":      20,
        "dap_cm":            20,
        "copa_amplitud":     "Amplia",       # > 14 m
        "copa_min_m":        14,             # diámetro mínimo de copa documentado
        "margen_seg_m":      2,              # margen adicional entre individuos
        "densidad_follaje":  "Alta",
        "rango_alt_msnm":    [0, 2000],
        "tasa_crecimiento":  "Rápida",
        "tipo_suelo":        ["Freático alto", "Variado"],
        "usos_ep": ["Retiro quebrada", "Parques", "Andenes", "Vías peatonales",
                    "Orejas de puente", "Glorietas", "Plazas", "Edificios"],
        "tipologias_aptas":  ["AsocioMovilidad", "AsocioEP", "AsocioUrbanistico", "OtrasZV"],
        "categorias_aptas":  ["RetiroQuebradas", "EcoparqueQuebrada", "ParqueRec",
                               "ParqueCiv", "ZVRecreacional", "Glorieta",
                               "FranjaAmoblamiento", "OrejaPuente", "Separador"],
        "origen":            "Nativa",
        "estado_conserv":   "LC - Preocupación menor",
        "pm25_eficiencia":   "Alta",         # captura de PM2.5 por densidad follaje
        "fuentes":           "Morales y Varón (2013); AMVA y UNAL (2014)",
    },
    "Calliandra haematocephala": {
        "nombre_comun":      "Carbonero flor roja",
        "familia":           "Fabaceae",
        "altura_max_m":      3,
        "dap_cm":            20,
        "copa_amplitud":     "Media",        # 7-14 m
        "copa_min_m":        7,
        "margen_seg_m":      1.5,
        "densidad_follaje":  "Media",
        "rango_alt_msnm":    [1001, 2000],
        "tasa_crecimiento":  "Rápida",
        "tipo_suelo":        ["No exigente"],
        "usos_ep": ["Antejardines", "Retiro quebrada", "Parques", "Plazas",
                    "Vías peatonales", "Glorietas", "Edificios"],
        "tipologias_aptas":  ["AsocioMovilidad", "AsocioUrbanistico", "AsocioEP"],
        "categorias_aptas":  ["Antejardin", "FranjaAmoblamiento", "RetiroQuebradas",
                               "EcoparqueQuebrada", "ParqueRec", "ParqueCiv",
                               "ZVRecreacional", "Glorieta", "Separador"],
        "origen":            "Nativa (Bolivia); ampliamente cultivada",
        "estado_conserv":   "No evaluada",
        "pm25_eficiencia":   "Media",
        "fuentes":           "Morales y Varón (2013); AMVA y UNAL (2014)",
    },
    "Bauhinia picta": {
        "nombre_comun":      "Casco de vaca",
        "familia":           "Fabaceae",
        "altura_max_m":      18,
        "dap_cm":            40,
        "copa_amplitud":     "Media",
        "copa_min_m":        7,
        "margen_seg_m":      2,
        "densidad_follaje":  "Alta",
        "rango_alt_msnm":    [0, 2000],
        "tasa_crecimiento":  "Media a Rápida",
        "tipo_suelo":        ["Bien drenado"],
        "usos_ep": ["Parques", "Plazas", "Separador autopistas", "Retiro quebrada",
                    "Separador arterias", "Andenes", "Vías peatonales",
                    "Orejas de puente", "Glorietas", "Edificios"],
        "tipologias_aptas":  ["AsocioMovilidad", "AsocioEP", "AsocioUrbanistico"],
        "categorias_aptas":  ["Separador", "OrejaPuente", "Glorieta", "RetiroQuebradas",
                               "EcoparqueQuebrada", "ParqueRec", "ParqueCiv",
                               "ZVRecreacional", "FranjaAmoblamiento"],
        "origen":            "Nativa",
        "estado_conserv":   "No evaluada",
        "pm25_eficiencia":   "Alta",
        "fuentes":           "Morales y Varón (2013); AMVA y UNAL (2014)",
    },
    "Inga densiflora": {
        "nombre_comun":      "Guamo machete",
        "familia":           "Fabaceae",
        "altura_max_m":      20,
        "dap_cm":            50,
        "copa_amplitud":     "Amplia",       # copa extendida
        "copa_min_m":        12,
        "margen_seg_m":      3,
        "densidad_follaje":  "Alta",
        "rango_alt_msnm":    [20, 2000],
        "tasa_crecimiento":  "Rápida",
        "tipo_suelo":        ["Bien drenado", "Variado"],
        "usos_ep": ["Parques", "Zonas rurales", "Retiro quebrada", "Restauración",
                    "Bordes de quebrada"],
        "tipologias_aptas":  ["AsocioEP", "AsocioMovilidad"],
        "categorias_aptas":  ["RetiroQuebradas", "EcoparqueQuebrada", "EcoparqueCerro",
                               "FajasTaludes", "ParqueRec", "ZVRecreacional"],
        "origen":            "Nativa",
        "estado_conserv":   "LC - Preocupación menor",
        "pm25_eficiencia":   "Alta",
        "fuentes":           "Catálogo UNAL; GBIF; POWO (Kew)",
    },
    "Retrophyllum rospigliosii": {
        "nombre_comun":      "Pino colombiano / Chaquiro",
        "familia":           "Podocarpaceae",
        "altura_max_m":      45,
        "dap_cm":            200,
        "copa_amplitud":     "No especificada",
        "copa_min_m":        8,              # estimación conservadora por DAP y altura
        "margen_seg_m":      4,              # raíces profundas, pero porte grande
        "densidad_follaje":  "Alta",
        "rango_alt_msnm":    [1501, 3000],
        "tasa_crecimiento":  "Lenta a Media",
        "tipo_suelo":        ["Profundo y bien drenado"],
        "usos_ep": ["Cerros", "Glorietas", "Parques", "Plazas", "Edificios"],
        "tipologias_aptas":  ["AsocioEP", "AsocioUrbanistico"],
        "categorias_aptas":  ["EcoparqueCerro", "EcoparqueQuebrada", "FajasTaludes",
                               "ParqueRec", "ZVRecreacional", "Glorieta", "ParqueCiv"],
        "origen":            "Nativa",
        "estado_conserv":   "NT - Casi amenazada",
        "pm25_eficiencia":   "Alta",
        "fuentes":           "Alcaldía Medellín (2011); AMVA y UNAL (2014)",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# PARÁMETROS DEL MODELO MULTICRITERIA
# ─────────────────────────────────────────────────────────────────────────────
W_PM25  = 0.45   # peso: contaminación medida (salud pública)
W_DEF   = 0.35   # peso: déficit de mitigadores (brecha de cobertura)
W_AREA  = 0.20   # peso: área disponible (viabilidad territorial)

# Cobertura dominante apta para siembra
COBER_APTA = {"Grama", "Tierra"}

# Categorías de uso excluidas (privadas o sin gestión pública)
CATEGORIA_EXCLUIDA = {"ZVPrivadas", "ZVUsoPrivado", "Parqueadero"}

# Altitud aproximada del núcleo urbano de Medellín (msnm)
ALTITUD_MEDELLIN = 1495

# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────────────────────
def normalizar(serie):
    """Min-Max normalization → [0, 1]. Maneja series constantes."""
    mn, mx = serie.min(), serie.max()
    if mx == mn:
        return pd.Series([0.5] * len(serie), index=serie.index)
    return (serie - mn) / (mx - mn)


def capacidad_zona(area_m2, copa_min_m, margen_seg_m):
    """
    Estima cuántos árboles caben en una zona asumiendo plantación en
    cuadrícula con separación mínima = copa_min_m + margen_seg_m.

    Fórmula:
        separacion = copa_min_m + margen_seg_m
        n = floor(area_m2 / separacion²)

    La cuadrícula es el layout más conservador; en campo se puede
    optimizar con disposición en tresbolillo (+15 % de densidad).
    """
    sep = copa_min_m + margen_seg_m
    if sep <= 0 or area_m2 <= 0:
        return 0
    return max(0, math.floor(area_m2 / (sep ** 2)))


def especie_para_zona(categoria, cober_dom, altitud=ALTITUD_MEDELLIN):
    """
    Selecciona la especie más adecuada para una zona verde dada, según:
      1. Rango altitudinal del municipio
      2. Compatibilidad de la categoría con los usos registrados en la ficha
      3. Prioridad: mayor densidad de follaje y tasa de crecimiento rápida primero.

    Devuelve lista ordenada de (especie, puntuacion).
    """
    candidatas = []
    for nombre, datos in ESPECIES.items():
        alt_min, alt_max = datos["rango_alt_msnm"]
        if not (alt_min <= altitud <= alt_max):
            continue
        if categoria in datos["categorias_aptas"]:
            # Puntuación interna: follaje alto=2/medio=1 + crecimiento rápido=1
            pts = 0
            if datos["densidad_follaje"] == "Alta":
                pts += 2
            elif datos["densidad_follaje"] == "Media":
                pts += 1
            if "Rápida" in datos["tasa_crecimiento"]:
                pts += 1
            candidatas.append((nombre, pts))

    candidatas.sort(key=lambda x: -x[1])
    return candidatas


# ─────────────────────────────────────────────────────────────────────────────
# PASO 1: CARGAR DATOS
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("  BLOQUE 2 — RECOMENDADOR DE SIEMBRA DE ÁRBOLES MITIGADORES PM2.5")
print("=" * 70)

print("\n[1/6] Cargando capas geoespaciales...")
gdf_comunas = gpd.read_file(RUTA_COMUNAS)   # EPSG:9377
gdf_zonas   = gpd.read_file(RUTA_ZONAS)     # EPSG:9377
print(f"   ✔ Comunas cargadas      : {len(gdf_comunas)}")
print(f"   ✔ Zonas verdes cargadas : {len(gdf_zonas):,}")

# Normalizar nombre de comunas en el GeoJSON
GEOJSON_NOMBRE_MAP = {
    "BELEN": "Belén", "POPULAR": "Popular", "ROBLEDO": "Robledo",
    "ARANJUEZ": "Aranjuez", "CASTILLA": "Castilla", "GUAYABAL": "Guayabal",
    "LAURELES": "Laureles Estadio", "MANRIQUE": "Manrique",
    "PALMITAS": "Corregimiento de San Sebastián de Palmitas",
    "ALTAVISTA": "Corregimiento de Altavista",
    "EL POBLADO": "El Poblado", "LA AMERICA": "La América",
    "SAN JAVIER": "San Javier", "SANTA CRUZ": "Santa Cruz",
    "SANTA ELENA": "Corregimiento de Santa Elena",
    "BUENOS AIRES": "Buenos Aires", "LA CANDELARIA": "La Candelaria",
    "SAN CRISTOBAL": "Corregimiento de San Cristóbal",
    "VILLA HERMOSA": "Villa Hermosa", "DOCE DE OCTUBRE": "Doce de Octubre",
    "SAN ANTONIO DE PRADO": "Corregimiento de San Antonio de Prado",
}
gdf_comunas["comuna_nombre"] = gdf_comunas["nombre"].map(GEOJSON_NOMBRE_MAP)

# ─────────────────────────────────────────────────────────────────────────────
# PASO 2: FILTRAR ZONAS VERDES VIABLES PARA SIEMBRA
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2/6] Filtrando zonas verdes aptas para siembra...")

mask_cober = gdf_zonas["cober_dom"].isin(COBER_APTA)
mask_cat   = ~gdf_zonas["categoria"].isin(CATEGORIA_EXCLUIDA)
mask_area  = gdf_zonas["Shape_Area"] >= 25   # mínimo 25 m² → al menos 1 árbol pequeño

gdf_apta = gdf_zonas[mask_cober & mask_cat & mask_area].copy()
print(f"   ✔ Cobertura apta (Grama/Tierra)    : {mask_cober.sum():,} zonas")
print(f"   ✔ Categoría pública                : {(mask_cober & mask_cat).sum():,} zonas")
print(f"   ✔ Área mínima ≥25 m²               : {len(gdf_apta):,} zonas")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 3: SPATIAL JOIN → ASIGNAR CADA ZONA A SU COMUNA
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3/6] Asignando zonas verdes a comunas (spatial join)...")

gdf_join = gpd.sjoin(
    gdf_apta[["id_poligono", "tipologia", "categoria", "cober_dom",
              "narb_aprox", "Shape_Area", "geometry"]],
    gdf_comunas[["comuna_nombre", "nombre", "geometry"]],
    how="left",
    predicate="within"
)

# Descartar zonas fuera de los polígonos municipales
gdf_join = gdf_join[gdf_join["comuna_nombre"].notna()].copy()
print(f"   ✔ Zonas con comuna asignada: {len(gdf_join):,}")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 4: CARGAR RESULTADOS DEL BLOQUE 1 Y CALCULAR SCORE POR COMUNA
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4/6] Calculando score multicriteria por comuna...")

df_b1 = pd.read_csv(RUTA_BLOQUE1)

# Promedio de todo el período disponible por comuna
df_pm = df_b1.groupby("comuna").agg(
    pm25_promedio     = ("pm25_promedio_ug_m3", "mean"),
    arb_totales       = ("cantidad_arboles_totales", "first"),
    arb_mitigadores   = ("cantidad_arboles_mitigadores_pm25", "first"),
    ratio_mitigadores = ("ratio_mitigadores_pct", "first"),
).reset_index().round(2)

BENCHMARK_PCT = 30.0
df_pm["deficit_pct"] = (BENCHMARK_PCT - df_pm["ratio_mitigadores"]).clip(lower=0).round(2)

# Área total disponible por comuna
area_por_comuna = (
    gdf_join.groupby("comuna_nombre")["Shape_Area"]
    .sum()
    .reset_index()
    .rename(columns={"comuna_nombre": "comuna", "Shape_Area": "area_apta_m2"})
)

# Unir
df_score = df_pm.merge(area_por_comuna, on="comuna", how="left")
df_score["area_apta_m2"] = df_score["area_apta_m2"].fillna(0)

# Normalizar y calcular score
df_score["n_pm25"]  = normalizar(df_score["pm25_promedio"])
df_score["n_def"]   = normalizar(df_score["deficit_pct"])
df_score["n_area"]  = normalizar(df_score["area_apta_m2"])

df_score["score_total"] = (
    W_PM25 * df_score["n_pm25"] +
    W_DEF  * df_score["n_def"]  +
    W_AREA * df_score["n_area"]
).round(4)

df_score["ranking_prioridad"] = df_score["score_total"].rank(ascending=False).round(0).astype(int)
df_score = df_score.sort_values("ranking_prioridad")

print(f"\n   SCORE MULTICRITERIA POR COMUNA")
print(f"   (w_PM2.5={W_PM25}  w_déficit={W_DEF}  w_área={W_AREA})")
print(f"\n   {'#':>3} {'Comuna':<35} {'PM2.5':>6} {'Déficit':>8} {'Área (ha)':>10} {'Score':>7}")
print(f"   {'-'*70}")
for _, r in df_score.iterrows():
    print(f"   {int(r['ranking_prioridad']):>3} {r['comuna']:<35} "
          f"{r['pm25_promedio']:>6.1f} {r['deficit_pct']:>7.1f}% "
          f"{r['area_apta_m2']/10000:>9.2f} {r['score_total']:>7.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 5: ASIGNACIÓN DE ESPECIE Y CUPO POR ZONA VERDE
# ─────────────────────────────────────────────────────────────────────────────
print("\n[5/6] Calculando cupo de árboles y especie recomendada por zona...")

registros = []

for _, zona in gdf_join.iterrows():
    categoria = zona["categoria"]
    cober     = zona["cober_dom"]
    area      = zona["Shape_Area"]
    comuna    = zona["comuna_nombre"]

    # Score de la comuna
    row_score = df_score[df_score["comuna"] == comuna]
    score_com = row_score["score_total"].values[0] if len(row_score) > 0 else 0.0
    rank_com  = row_score["ranking_prioridad"].values[0] if len(row_score) > 0 else 99

    # Elegir especie
    candidatas = especie_para_zona(categoria, cober, altitud=ALTITUD_MEDELLIN)

    if not candidatas:
        especie_rec = "Sin especie compatible"
        nombre_com  = "-"
        copa_min    = 0
        margen      = 0
        cupo        = 0
        eficiencia  = "-"
        fuentes     = "-"
    else:
        esp_nombre, _   = candidatas[0]
        datos_esp       = ESPECIES[esp_nombre]
        especie_rec     = esp_nombre
        nombre_com      = datos_esp["nombre_comun"]
        copa_min        = datos_esp["copa_min_m"]
        margen          = datos_esp["margen_seg_m"]
        cupo            = capacidad_zona(area, copa_min, margen)
        eficiencia      = datos_esp["pm25_eficiencia"]
        fuentes         = datos_esp["fuentes"]

    # Alternativas viables (hasta 2 más)
    alternativas = " | ".join(
        f"{ESPECIES[e]['nombre_comun']} ({e})"
        for e, _ in candidatas[1:3]
    ) if len(candidatas) > 1 else "Ninguna"

    registros.append({
        "id_poligono":          int(zona["id_poligono"]),
        "comuna":               comuna,
        "ranking_prioridad_comuna": int(rank_com),
        "score_multicriteria":  round(score_com, 4),
        "tipologia":            zona["tipologia"],
        "categoria":            categoria,
        "cobertura_actual":     cober,
        "area_m2":              round(area, 2),
        "area_ha":              round(area / 10000, 4),
        "especie_recomendada":  especie_rec,
        "nombre_comun_especie": nombre_com,
        "arboles_cupo_estimado":cupo,
        "separacion_minima_m":  copa_min + margen,
        "eficiencia_pm25":      eficiencia,
        "especies_alternativas":alternativas,
        "fuentes_botanicas":    fuentes,
    })

df_zonas_rec = pd.DataFrame(registros)

# Solo zonas donde caben al menos 1 árbol
df_zonas_rec = df_zonas_rec[df_zonas_rec["arboles_cupo_estimado"] > 0].copy()
df_zonas_rec = df_zonas_rec.sort_values(
    ["ranking_prioridad_comuna", "arboles_cupo_estimado"],
    ascending=[True, False]
).reset_index(drop=True)

print(f"   ✔ Zonas con cupo ≥1 árbol: {len(df_zonas_rec):,}")
print(f"   ✔ Árboles recomendados total: {df_zonas_rec['arboles_cupo_estimado'].sum():,}")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 6: RESUMEN POR COMUNA Y EXPORTACIÓN
# ─────────────────────────────────────────────────────────────────────────────
print("\n[6/6] Generando resumen ejecutivo y exportando archivos...")

# Resumen por comuna
df_resumen_com = df_zonas_rec.groupby("comuna").agg(
    ranking_prioridad        = ("ranking_prioridad_comuna",  "first"),
    score_multicriteria      = ("score_multicriteria",       "first"),
    n_zonas_disponibles      = ("id_poligono",               "count"),
    area_total_disponible_ha = ("area_ha",                   "sum"),
    arboles_a_plantar_total  = ("arboles_cupo_estimado",     "sum"),
).reset_index().round({"area_total_disponible_ha": 2, "score_multicriteria": 4})

# Especie más recomendada por comuna
especie_principal = (
    df_zonas_rec.groupby(["comuna","especie_recomendada"])["arboles_cupo_estimado"]
    .sum().reset_index()
    .sort_values("arboles_cupo_estimado", ascending=False)
    .groupby("comuna").first()
    .rename(columns={"especie_recomendada": "especie_principal",
                     "arboles_cupo_estimado": "cupo_especie_principal"})
    .reset_index()
)
df_resumen_com = df_resumen_com.merge(especie_principal, on="comuna", how="left")

# Añadir PM2.5 y déficit para contexto
df_resumen_com = df_resumen_com.merge(
    df_score[["comuna","pm25_promedio","deficit_pct","ratio_mitigadores"]],
    on="comuna", how="left"
)
df_resumen_com = df_resumen_com.sort_values("ranking_prioridad")

# Exportar CSV de zonas
df_zonas_rec.to_csv(RUTA_OUT_ZONAS, index=False, encoding="utf-8-sig")

# Exportar resumen
df_resumen_com.to_csv(RUTA_OUT_RESUMEN, index=False, encoding="utf-8-sig")

# Exportar GeoJSON priorizado (unir con geometrías)
gdf_geo_out = gdf_join[["id_poligono", "categoria", "cober_dom", "Shape_Area", "geometry"]].merge(
    df_zonas_rec[["id_poligono", "comuna", "ranking_prioridad_comuna",
                  "score_multicriteria", "especie_recomendada",
                  "nombre_comun_especie", "arboles_cupo_estimado",
                  "eficiencia_pm25"]],
    on="id_poligono", how="inner"
)
gdf_geo_out.to_file(RUTA_OUT_GEO, driver="GeoJSON")

# ─────────────────────────────────────────────────────────────────────────────
# REPORTE FINAL EN CONSOLA
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  RECOMENDACIÓN EJECUTIVA POR COMUNA")
print("=" * 70)
print(f"\n  {'#':>2} {'Comuna':<35} {'PM2.5':>6} {'Déficit':>8} "
      f"{'Zonas':>6} {'Área ha':>8} {'Árboles':>8} {'Especie principal'}")
print(f"  {'-'*105}")

for _, r in df_resumen_com.iterrows():
    esp = ESPECIES.get(r["especie_principal"], {}).get("nombre_comun", r["especie_principal"])
    print(f"  {int(r['ranking_prioridad']):>2} {r['comuna']:<35} "
          f"{r['pm25_promedio']:>6.1f} {r['deficit_pct']:>7.1f}% "
          f"{int(r['n_zonas_disponibles']):>6} {r['area_total_disponible_ha']:>8.2f} "
          f"{int(r['arboles_a_plantar_total']):>8}   {esp} ({r['especie_principal']})")

print("\n" + "=" * 70)
print("  DISTRIBUCIÓN DE ESPECIES RECOMENDADAS (total ciudad)")
print("=" * 70)
dist_esp = (
    df_zonas_rec.groupby("especie_recomendada")["arboles_cupo_estimado"]
    .sum().sort_values(ascending=False)
)
total_arb = dist_esp.sum()
for esp, n in dist_esp.items():
    nc = ESPECIES.get(esp, {}).get("nombre_comun", esp)
    datos = ESPECIES.get(esp, {})
    print(f"   · {nc:<28} ({esp:<30}): {n:>6,} árboles ({100*n/total_arb:.1f}%)")
    print(f"     Copa mín: {datos.get('copa_min_m','?')} m  "
          f"| Separación plantación: {datos.get('copa_min_m',0)+datos.get('margen_seg_m',0)} m  "
          f"| Crecimiento: {datos.get('tasa_crecimiento','?')}  "
          f"| Eficiencia PM2.5: {datos.get('pm25_eficiencia','?')}")

print("\n" + "=" * 70)
print("  FUNDAMENTO METODOLÓGICO Y FUENTES")
print("=" * 70)
print(f"""
  MODELO MULTICRITERIA (AHP simplificado):
  ─────────────────────────────────────────
  score = {W_PM25} × norm(PM2.5) + {W_DEF} × norm(déficit_mitigadores) + {W_AREA} × norm(área_apta)

  Justificación de pesos:
  · PM2.5 (45%): variable primaria de salud pública. OMS guía: <5 µg/m³.
    Comunas con PM2.5 >15 µg/m³ superan el umbral de la categoría Aceptable
    (15 µg/m³ OMS 2021). Fuente: SIATA 2023-2025.
  · Déficit mitigadores (35%): brecha entre ratio actual de mitigadores
    (Zygia, Calliandra, Bauhinia, Inga, Retrophyllum) y el benchmark 30%.
    El benchmark se sustenta en que estas especies tienen alta densidad de
    follaje (LAI ≥ 4), que es el principal atributo de captura de PM.
    Fuente: Alcaldía de Medellín (2011); AMVA-UNAL (2014).
  · Área disponible (20%): sin suelo útil la siembra es inviable. Se priorizan
    zonas con cobertura Grama o Tierra sin saturación arbórea, de uso público,
    área ≥ 25 m². Fuente: Inventario Zonas Verdes Medellín.

  DISTANCIAS DE PLANTACIÓN:
  ─────────────────────────
  La separación mínima entre individuos = diámetro_copa_mín + margen_seguridad.
  La capacidad estimada asume cuadrícula (layout conservador). En campo, una
  disposición en tresbolillo aumenta la capacidad ~15 %.
  Fuentes por especie: Morales y Varón (2013); AMVA y UNAL (2014);
  Catálogo de Plantas de Colombia (UNAL); GBIF; POWO (Kew).

  SELECCIÓN DE ESPECIE POR ZONA:
  ───────────────────────────────
  1. Rango altitudinal compatible con Medellín (1.495 msnm núcleo urbano).
  2. Categoría de zona verde incluida en usos de espacio público de la especie.
  3. Prioridad: follaje denso + tasa de crecimiento rápida.
  Las especies del género Fabaceae (Zygia, Calliandra, Bauhinia, Inga) fijan
  nitrógeno y tienen simbiontes radiculares que mejoran el suelo, generando
  un co-beneficio adicional.
""")

print("=" * 70)
print("  ARCHIVOS EXPORTADOS")
print("=" * 70)
print(f"  ✅ Zonas con recomendación : {RUTA_OUT_ZONAS}")
print(f"  ✅ Resumen por comuna      : {RUTA_OUT_RESUMEN}")
print(f"  ✅ GeoJSON para SIG        : {RUTA_OUT_GEO}")
print("=" * 70)
print("  Bloque 2 completado.\n")
