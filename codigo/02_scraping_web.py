# Autora: TURIN MERMA, Xiomara Milagros
# Código de matrícula: 2024200535B
# Tema 52: Flujo de caja y VAN de un proyecto agroexportador peruano
# Fecha de extracción: 2026-11-20
"""
02_scraping_web.py
------------------
Descarga programática de los cuadros estadísticos de exportación de SUNAT
(portal "Estadísticas y Estudios"), que se publican como archivos Excel:

  - Cuadro G7: Exportación definitiva, principales subpartidas nacionales,
               valor FOB MENSUAL (una hoja por año).
  - Cuadro G9: Exportaciones definitivas según subpartida nacional,
               valor FOB y PESO NETO ANUAL (una hoja por año).

Pasos:
  1) Revisa el robots.txt de SUNAT antes de descargar.
  2) Lee la página de exportaciones y ubica los enlaces de los cuadros.
  3) Descarga cada archivo SIN MODIFICARLO en /datos_crudos.
  4) Registra fecha, URL, código HTTP, tamaño, fecha de publicación del
     archivo y años disponibles en log_ejecucion.txt.
"""

import io
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests
import pandas as pd

# ------------------------------------------------------------------
# 0. Rutas y configuración
# ------------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent
CRUDOS = BASE / "datos_crudos"
LOG = BASE / "log_ejecucion.txt"
INCIDENCIAS = BASE / "incidencias_fuente.md"
CRUDOS.mkdir(exist_ok=True)

PAUSA = 1.5
CABECERAS = {"User-Agent": "Mozilla/5.0 (proyecto academico UNCP - Finanzas I; "
                           "contacto: 2024200535B)"}
PAGINA = "https://www.sunat.gob.pe/estadisticasestudios/exportaciones.html"
CUADROS = {"G7": "valor FOB mensual por subpartida",
           "G9": "valor FOB y peso neto anual por subpartida"}


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def registrar(fuente, url, http, registros, nota=""):
    linea = f"{ahora()} | {fuente} | HTTP {http} | registros: {registros} | {url}"
    if nota:
        linea += f" | {nota}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")
    print(linea)


def anotar_incidencia(url, http, detalle):
    texto = INCIDENCIAS.read_text(encoding="utf-8") if INCIDENCIAS.exists() else ""
    if detalle in texto:
        return
    with open(INCIDENCIAS, "a", encoding="utf-8") as f:
        f.write(f"| {ahora()} | {url} | {http} | {detalle} | -- |\n")


with open(LOG, "a", encoding="utf-8") as f:
    f.write(f"\n# Ejecución de 02_scraping_web.py - {ahora()}\n")

# ------------------------------------------------------------------
# 1. robots.txt
# ------------------------------------------------------------------
robots = RobotFileParser("https://www.sunat.gob.pe/robots.txt")
try:
    robots.read()
    permitido = robots.can_fetch(CABECERAS["User-Agent"], PAGINA)
except Exception as e:
    permitido = True
    anotar_incidencia("https://www.sunat.gob.pe/robots.txt", "ERROR",
                      f"No se pudo leer el robots.txt de SUNAT ({e}); se continuó con pausas.")
registrar("SUNAT robots.txt", "https://www.sunat.gob.pe/robots.txt", "-", "-",
          f"lectura permitida: {permitido}")
if not permitido:
    raise SystemExit("El robots.txt de SUNAT no permite la descarga. Se detiene el script.")

# ------------------------------------------------------------------
# 2. Buscar los enlaces de los cuadros en la página de SUNAT
# ------------------------------------------------------------------
enlaces = {}
try:
    r = requests.get(PAGINA, headers=CABECERAS, timeout=60)
    for cuadro in CUADROS:
        m = re.search(r'href="([^"]*cdro_%s\.xlsx)"' % cuadro, r.text)
        if m:
            enlaces[cuadro] = urljoin(PAGINA, m.group(1))
    registrar("SUNAT página", PAGINA, r.status_code, len(enlaces), "enlaces de cuadros encontrados")
except Exception as e:
    registrar("SUNAT página", PAGINA, "ERROR", 0, str(e))
time.sleep(PAUSA)

# Si la página cambió, se usa la ruta oficial conocida de cada cuadro
for cuadro in CUADROS:
    if cuadro not in enlaces:
        enlaces[cuadro] = ("https://www.sunat.gob.pe/estadisticasestudios/"
                           f"nota_tributaria/cdro_{cuadro}.xlsx")
        anotar_incidencia(PAGINA, "-", f"No se encontró el enlace del cuadro {cuadro} en la "
                                       "página; se usó la ruta oficial directa.")

# ------------------------------------------------------------------
# 3. Descargar cada cuadro sin modificarlo
# ------------------------------------------------------------------
for cuadro, descripcion in CUADROS.items():
    url = enlaces[cuadro]
    try:
        r = requests.get(url, headers=CABECERAS, timeout=180)
        destino = CRUDOS / f"sunat_cdro_{cuadro}.xlsx"
        destino.write_bytes(r.content)
        publicado = r.headers.get("Last-Modified", "sin dato")
        hojas = pd.ExcelFile(io.BytesIO(r.content)).sheet_names
        anios = [h for h in hojas if h.strip().isdigit()]
        registrar(f"SUNAT {cuadro}", url, r.status_code, f"{len(r.content) // 1024} KB",
                  f"{descripcion}; años {anios[0]}-{anios[-1]}; publicado: {publicado}")
        faltan = [a for a in range(2012, 2026) if str(a) not in anios]
        if faltan:
            anotar_incidencia(url, r.status_code,
                              f"El cuadro {cuadro} no tiene hojas para los años {faltan}.")
    except Exception as e:
        registrar(f"SUNAT {cuadro}", url, "ERROR", 0, str(e))
        anotar_incidencia(url, "ERROR", f"Falla al descargar el cuadro {cuadro}: {e}")
    time.sleep(PAUSA)

print("\nListo. Revisa la carpeta datos_crudos (sunat_cdro_G7.xlsx y sunat_cdro_G9.xlsx).")
