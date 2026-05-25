# Proyecto de Visualización de Datos

Arborización Urbana para Mitigación de PM2.5 — Medellín

Proyecto enfocado en el análisis de calidad del aire (PM2.5), inventario arbóreo urbano y generación de recomendaciones de siembra estratégica para el Distrito de Medellín.

## Estructura del Proyecto

```
├── README.txt
├── dashboard
│   ├── app.py
│   ├── logo_alcaldia.png
│   └── style.css
│
├── data
│   ├── clean
│   │   ├── auditoria_estaciones_comunas.csv
│   │   ├── bloque2_recomendador_siembra.py
│   │   ├── integracion_v2_pm25_arboles_medellin.csv
│   │   ├── integracion_v2_pm25_arboles_medellin.py
│   │   ├── recomendacion_siembra_por_zona.csv
│   │   ├── relaciones_v2_bloque2.csv
│   │   ├── resumen_recomendacion_por_comuna.csv
│   │   └── zonas_priorizadas_siembra.geojson
│   │
│   └── raw
│       ├── base_datos_arboles
│       │   └── ARBOLES
│       │       ├── Data_Clean
│       │       │   └── ARBOLES.xlsx
│       │       ├── Data_Raw
│       │       │   ├── ARBOLES_TOTALES
│       │       │   │   ├── ARANJUEZ.xlsx
│       │       │   │   ├── BELEN.xlsx
│       │       │   │   ├── ...
│       │       │   └── ESPECIE_REDUCEN
│       │       │       ├── CARBONERO_FLOR_ROJA.xlsx
│       │       │       ├── CASCO_VACA.xlsx
│       │       │       ├── ...
│       │       └── Documentacion
│       │           ├── ETL ÁRBOLES QUE REDUCEN PM2.pdf
│       │           ├── Plan Distrital de Silvicultura Urbana.pdf
│       │           └── ...
│       │
│       ├── base_datos_comunas
│       │   └── geojson_limite_catastral_de_comun
│       │       └── limite_catastral_de_comun.geojson
│       │
│       ├── base_datos_siata
│       │   └── siata
│       │       ├── MetadatosEstacionesPM25Historico.csv
│       │       └── Solicitud_PM25_DP1763941.csv
│       │
│       └── base_datos_zonas_verdes
│           └── geojson_inventario_zonas_verdes
│               └── inventario_zonas_verdes.geojson
│
├── notebooks
│
├── presentacion
│   └── presentacion.pptx
│
└── requirements.txt
```

## Descripcion General

El proyecto integra información proveniente de:

Estaciones SIATA de monitoreo PM2.5
Inventario arbóreo urbano de Medellín
Límites geográficos de comunas
Inventario de zonas verdes

A partir de estos datos se construyen:

Integraciones espaciales y ambientales
Relaciones entre cobertura arbórea y PM2.5
Recomendaciones de siembra priorizada
Visualizaciones interactivas mediante Streamlit

## Requisitos Previos

Python 3.9 o superior
pip actualizado
Acceso completo a los datasets incluidos en data/raw

## Instalacion

1. Crear entorno virtual Windows
   ```bash
   python -m venv venv -> .\venv\Scripts\activate
   ```

 * Crear entorno virtual Linux / Mac
   ```bash
   -> python3 -m venv venv -> source venv/bin/activate
   ```

 * Instalacion de dependencias
   ```bash
   -> pip install -r requirements.txt
   ```

* Dependencias principales utilizadas
  pandas
  geopandas
  numpy
  shapely
  folium
  streamlit
  plotly
  streamlit-folium
   
## Ejecucion del proyecto

`Bloque 1 — Integración PM2.5 + Árboles`.

Script encargado de:

Integrar datos ambientales y arbóreos
Relacionar estaciones SIATA con comunas
Generar datasets integrados

Ejecutar:
```bash
-> python data/clean/integracion_v2_pm25_arboles_medellin.py
```

Outputs generados:
`integracion_v2_pm25_arboles_medellin.csv`
`relaciones_v2_bloque2.csv`
`auditoria_estaciones_comunas.csv`
`Bloque 2 — Recomendador de Siembra`

Script encargado de:

Analizar zonas prioritarias
Generar recomendaciones de arborización
Crear capas geográficas para visualización

Ejecutar:
```bash
-> python data/clean/bloque2_recomendador_siembra.py
```

Outputs generados:
`recomendacion_siembra_por_zona.csv`
`resumen_recomendacion_por_comuna.csv`
`zonas_priorizadas_siembra.geojson`
Dashboard Interactivo

Aplicación desarrollada con Streamlit para visualizar:

Indicadores de PM2.5
Cobertura arbórea
Comunas priorizadas
Mapas interactivos

Ejecutar Dashboard
```bash
-> streamlit run dashboard/app.py
```

Estructura de Datos
Datos Raw `(data/raw)`

Contiene:

Archivos originales Excel
GeoJSON oficiales
Bases SIATA
Documentación técnica
Datos Procesados `(data/clean)`

Contiene:

Scripts principales
Integraciones finales
Outputs analíticos
Capas geográficas generadas

Notas Importantes

Las rutas del proyecto son relativas.

Se recomienda ejecutar primero el `Bloque 1` y posteriormente el `Bloque 2`.

El `dashboard` depende de los outputs generados previamente.

Algunos archivos `GeoJSON` pueden requerir `geopandas` y `fiona` correctamente instalados.

Mantener la estructura de carpetas original para evitar errores de lectura.

Tecnologías Utilizadas

Python
Pandas
GeoPandas
Streamlit
Plotly
Folium
Shapely
Autoría

Proyecto académico y analítico orientado a estrategias de arborización urbana para mitigación de contaminación atmosférica en Medellín.

