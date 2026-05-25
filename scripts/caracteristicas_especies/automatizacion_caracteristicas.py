import requests
from bs4 import BeautifulSoup
import os

# =========================
# LISTA DE URLS
# =========================

urls = [
    "https://catalogofloravalleaburra.eia.edu.co/species/124",
    "https://catalogofloravalleaburra.eia.edu.co/species/27",
    "https://catalogofloravalleaburra.eia.edu.co/species/47",
    "https://catalogofloravalleaburra.eia.edu.co/species/307"
]

# =========================
# CREAR CARPETA DE SALIDA
# =========================

os.makedirs("especies_txt", exist_ok=True)

# =========================
# RECORRER CADA URL
# =========================

for url in urls:

    print(f"\nProcesando: {url}")

    try:

        # =========================
        # HACER REQUEST
        # =========================

        response = requests.get(url)

        if response.status_code != 200:
            print(f"Error al acceder: {url}")
            continue

        # =========================
        # PARSEAR HTML
        # =========================

        soup = BeautifulSoup(response.text, "html.parser")

        # =========================
        # BUSCAR TABLA
        # =========================

        tabla = soup.find("table", {"id": "tabla-especie"})

        if tabla is None:
            print("No se encontró la tabla.")
            continue

        # =========================
        # EXTRAER NOMBRE CIENTÍFICO
        # =========================

        nombre = "especie"

        filas = tabla.find_all("tr")

        for fila in filas:

            columnas = fila.find_all("td")

            if len(columnas) == 2:

                clave = columnas[0].get_text(strip=True)
                valor = columnas[1].get_text(" ", strip=True)

                if clave == "Nombre científico":
                    nombre = valor.replace(" ", "_")
                    break

        # =========================
        # CREAR ARCHIVO TXT
        # =========================

        ruta_archivo = f"{nombre}.txt"

        with open(ruta_archivo, "w", encoding="utf-8") as archivo:

            archivo.write(f"ESPECIE: {nombre}\n")
            archivo.write("=" * 50 + "\n\n")

            # =========================
            # EXTRAER CARACTERÍSTICAS
            # =========================

            for fila in filas:

                columnas = fila.find_all("td")

                if len(columnas) == 2:

                    caracteristica = columnas[0].get_text(strip=True)
                    valor = columnas[1].get_text(" ", strip=True)

                    linea = f"{caracteristica}: {valor}\n"

                    archivo.write(linea)

        print(f"Archivo guardado: {ruta_archivo}")

    except Exception as e:
        print(f"Error procesando {url}")
        print(e)

print("\nProceso finalizado.")
