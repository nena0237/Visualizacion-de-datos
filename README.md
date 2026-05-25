# Proyecto de Visualización de Datos

Este proyecto contiene herramientas para visualizar datos geoespaciales y estadísticos de Bogotá, Colombia.

## Estructura del Proyecto

```
.
├── main_proyecto/
│   ├── bases_de_datos/         # Carpetas con las bases de datos utilizadas
│   ├── dashboard/              # Aplicación web de Streamlit
│   │   ├── app.py              # Aplicación principal de Streamlit
│   │   ├── generar_mapa_coropletico.py  # Script para generar mapas coropléticos
│   │   ├── mapa_coropletico_pm25.py     # Script para mapas de PM2.5
│   │   ├── mapa_coropletico_pm25_zonas_verdes.py  # Script para mapas de PM2.5 y zonas verdes
│   │   ├── style.css           # Estilos personalizados
│   │   └── ...                 # Otros archivos de apoyo
│   ├── scripts/                # Scripts adicionales de procesamiento
│   ├── venv/                   # Entorno virtual de Python
│   └── requirements.txt        # Dependencias del proyecto
```

## Requisitos

- Python 3.9 o superior
- Las dependencias listadas en `requirements.txt`

## Instalación

1. Clonar o descargar este repositorio
2. Navegar al directorio del proyecto:
   ```bash
   cd "C:\Users\jimen\OneDrive\Documentos\VISUALIZACIÓN DE DATOS\Proyecto de visualización de datos"
   ```

## Activar el Entorno Virtual

El proyecto ya incluye un entorno virtual configurado. Para activarlo:

### En Windows PowerShell:
```powershell
# Primero, si es necesario, ajuste la política de ejecución:
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# Luego active el entorno virtual:
# Parados desde main_proyecto
.\venv\Scripts\Activate.ps1

# Luego para correr
streamlit run app.py
```

### En Command Prompt (cmd):
```cmd
.\main_proyecto\venv\Scripts\activate.bat
```

### En Git Bash o Linux/Mac Terminal:
```bash
source main_proyecto/venv/bin/activate
```

Una vez activado, verá el nombre del entorno virtual al inicio de la línea de comandos, algo como:
```
(venv) C:\Users\jimen\OneDrive\Documentos\VISUALIZACIÓN DE DATOS\Proyecto de visualización de datos>
```

## Instalar Dependencias

Si necesita reinstalar o actualizar las dependencias:
```bash
pip install -r main_proyecto\requirements.txt
```

## Ejecutar la Aplicación

La aplicación principal es un dashboard de Streamlit ubicado en `main_proyecto\dashboard\app.py`.

Para ejecutarlo:
```bash
streamlit run main_proyecto\dashboard\app.py
```

Esto abrirá automáticamente la aplicación en su navegador web predeterminado en la dirección:
```
http://localhost:8501
```

## Scripts Adicionales

El proyecto incluye varios scripts para generar visualizaciones específicas:

1. `generar_mapa_coropletico.py` - Genera mapas coropléticos básicos
2. `mapa_coropletico_pm25.py` - Genera mapas de concentración de PM2.5
3. `mapa_coropletico_pm25_zonas_verdes.py` - Genera mapas combinando PM2.5 y zonas verdes

Para ejecutar cualquiera de estos scripts:
```bash
python main_proyecto\dashboard\nombre_del_script.py
```

## Notas importantes

- Asegúrese de que el entorno virtual esté activado antes de instalar dependencias o ejecutar cualquier script
- Algunas funcionalidades pueden requerir acceso a internet para descargar tiles de mapas o datos externos
- Los archivos de datos están ubicados en las subcarpetas de `main_proyecto\bases_de_datos`

## Solución de Problemas

### Problema: Error de ejecución de scripts en PowerShell
Si recibe un error sobre la política de ejecución al intentar activar el entorno virtual, ejecute primero:
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
```

### Problema: Módulos no encontrados
Asegúrese de haber activado el entorno virtual y de haber instalado las dependencias con:
```bash
pip install -r main_proyecto\requirements.txt
```

### Problema: Puerto ya en uso
Si el puerto 8501 está ocupado, puede especificar otro puerto:
```bash
streamlit run main_proyecto\dashboard\app.py --server.port=8502
```