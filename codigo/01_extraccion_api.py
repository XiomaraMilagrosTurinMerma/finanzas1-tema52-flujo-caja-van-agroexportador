# Autora: TURIN MERMA, Xiomara Milagros
# Código de matrícula: 2024200535B
# Tema 52: Flujo de caja y VAN de un proyecto agroexportador peruano
# Fecha de extracción: 2026-11-20
"""
01_extraccion_api.py
--------------------
Descarga los datos crudos de las fuentes oficiales y los guarda SIN MODIFICAR
en la carpeta /datos_crudos:

  1) BCRPData (API REST): valor FOB mensual de exportación de 8 productos
     agropecuarios (8 productos primarios + 2 manufacturas de origen agrícola)
     y el tipo de cambio interbancario promedio (2012-2025).
  2) Banco Mundial: precios internacionales mensuales ("Pink Sheet").
     La API del Banco Mundial (fuente 15, Global Economic Monitor) no incluye
     precios agrícolas, por eso el archivo oficial se descarga con código
     desde la página de Commodity Markets (ver incidencias_fuente.md).

Cada consulta queda registrada en log_ejecucion.txt (fecha, URL, código HTTP
y número de registros).
"""

import re
import time
from datetime import datetime
from pathlib import Path
from urllib.robotparser import RobotFileParser

import requests

# ------------------------------------------------------------------
# 0. Rutas y configuración
# ------------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent          # carpeta 03_BASE_DATOS...
CRUDOS = BASE / "datos_crudos"
LOG = BASE / "log_ejecucion.txt"
INCIDENCIAS = BASE / "incidencias_fuente.md"
CRUDOS.mkdir(exist_ok=True)

INICIO, FIN = "2012-1", "2025-12"                      # periodo de estudio
PAUSA = 1.5                                            # segundos entre consultas
CABECERAS = {"User-Agent": "Mozilla/5.0 (proyecto academico UNCP - Finanzas I; "
                           "contacto: 2024200535B)"}

# Series del BCRP: valores FOB mensuales (millones US$) por producto
# (10 productos x 168 meses = 1 680 observaciones producto-mes)
SERIES_BCRP = {
    "PN43443BM": "arandanos",
    "PN43444BM": "uvas",
    "PN43445BM": "cafe",
    "PN43446BM": "paltas",
    "PN43447BM": "cacao",
    "PN43448BM": "esparragos",
    "PN43449BM": "mangos",
    "PN43450BM": "mandarinas",
    "PN43453BM": "conservas_frutas_hortalizas",
    "PN43455BM": "frutas_congeladas",
    "PN01207PM": "tipo_cambio",                         # S/ por US$, interbancario promedio
}

URL_BM_PAGINA = "https://www.worldbank.org/en/research/commodity-markets"
URL_BM_RESPALDO = ("https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-"
                   "0050012026/related/CMO-Historical-Data-Monthly.xlsx")


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def registrar(fuente, url, http, registros, nota=""):
    """Agrega una línea al log de ejecución."""
    linea = f"{ahora()} | {fuente} | HTTP {http} | registros: {registros} | {url}"
    if nota:
        linea += f" | {nota}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")
    print(linea)


def anotar_incidencia(url, http, detalle):
    """Agrega una fila a incidencias_fuente.md (sin repetir la misma incidencia)."""
    texto = INCIDENCIAS.read_text(encoding="utf-8") if INCIDENCIAS.exists() else ""
    if detalle in texto:
        return
    with open(INCIDENCIAS, "a", encoding="utf-8") as f:
        f.write(f"| {ahora()} | {url} | {http} | {detalle} | -- |\n")


# ------------------------------------------------------------------
# 1. BCRPData - API REST
# ------------------------------------------------------------------
print("\n=== 1) BCRPData ===")
with open(LOG, "a", encoding="utf-8") as f:
    f.write(f"\n# Ejecución de 01_extraccion_api.py - {ahora()}\n")

obs_productos = 0
for codigo, nombre in SERIES_BCRP.items():
    url = (f"https://estadisticas.bcrp.gob.pe/estadisticas/series/api/"
           f"{codigo}/json/{INICIO}/{FIN}/esp")
    try:
        r = requests.get(url, headers=CABECERAS, timeout=60)
        datos = r.json()
        n = len(datos.get("periods", []))
        # Se guarda la respuesta original, tal cual llegó
        archivo = CRUDOS / f"bcrp_{codigo}_{nombre}.json"
        archivo.write_text(r.text, encoding="utf-8")
        registrar("BCRP", url, r.status_code, n, datos["config"]["series"][0]["name"])
        if nombre != "tipo_cambio":
            obs_productos += n
        if n != 168:
            anotar_incidencia(url, r.status_code,
                              f"La serie {codigo} devolvió {n} meses (se esperaban 168).")
    except Exception as e:
        registrar("BCRP", url, "ERROR", 0, str(e))
        anotar_incidencia(url, "ERROR", f"Falla al descargar {codigo}: {e}")
    time.sleep(PAUSA)

resumen = f"Observaciones producto-mes descargadas del BCRP: {obs_productos}"
print("\n" + resumen)
with open(LOG, "a", encoding="utf-8") as f:
    f.write(f"{ahora()} | RESUMEN | {resumen}\n")

# ------------------------------------------------------------------
# 2. Banco Mundial - precios internacionales (Pink Sheet)
# ------------------------------------------------------------------
print("\n=== 2) Banco Mundial ===")

# 2.1 Verificación de la API (fuente 15) -> se documenta que no trae precios agrícolas
url_api = "https://api.worldbank.org/v2/sources/15/indicators?format=json&per_page=2000"
try:
    r = requests.get(url_api, headers=CABECERAS, timeout=60)
    indicadores = r.json()[1]
    (CRUDOS / "bancomundial_api_fuente15_indicadores.json").write_text(r.text, encoding="utf-8")
    registrar("Banco Mundial API", url_api, r.status_code, len(indicadores),
              "fuente 15 (Global Economic Monitor)")
    anotar_incidencia(url_api, r.status_code,
                      f"La API del Banco Mundial (fuente 15, GEM) tiene {len(indicadores)} "
                      "indicadores y ninguno es un precio agrícola; se usa el archivo oficial "
                      "Pink Sheet con descarga programática.")
except Exception as e:
    registrar("Banco Mundial API", url_api, "ERROR", 0, str(e))
time.sleep(PAUSA)

# 2.2 Revisión de robots.txt antes de leer la página
robots = RobotFileParser("https://www.worldbank.org/robots.txt")
try:
    robots.read()
    permitido = robots.can_fetch(CABECERAS["User-Agent"], URL_BM_PAGINA)
except Exception:
    permitido = True
registrar("Banco Mundial robots.txt", "https://www.worldbank.org/robots.txt", "-", "-",
          f"lectura permitida: {permitido}")
if not permitido:
    anotar_incidencia("https://www.worldbank.org/robots.txt", "-",
                      "El robots.txt del Banco Mundial no permite leer la página de Commodity "
                      "Markets con un programa; se respetó y se usó el enlace directo oficial "
                      "del archivo mensual (thedocs.worldbank.org).")

# 2.3 Buscar en la página el enlace vigente del archivo mensual
url_xlsx = URL_BM_RESPALDO
if permitido:
    try:
        r = requests.get(URL_BM_PAGINA, headers=CABECERAS, timeout=60)
        enlaces = re.findall(r'href="([^"]*CMO-Historical-Data-Monthly\.xlsx)"', r.text)
        if enlaces:
            url_xlsx = enlaces[0]
        registrar("Banco Mundial página", URL_BM_PAGINA, r.status_code, len(enlaces),
                  "enlaces al archivo mensual encontrados")
    except Exception as e:
        registrar("Banco Mundial página", URL_BM_PAGINA, "ERROR", 0, str(e))
    time.sleep(PAUSA)

# 2.4 Descarga del archivo Excel (sin modificarlo)
try:
    r = requests.get(url_xlsx, headers=CABECERAS, timeout=120)
    destino = CRUDOS / "bancomundial_CMO_Historical_Data_Monthly.xlsx"
    destino.write_bytes(r.content)
    registrar("Banco Mundial Pink Sheet", url_xlsx, r.status_code,
              f"{len(r.content) / 1024:.0f} KB", "archivo mensual guardado")
except Exception as e:
    registrar("Banco Mundial Pink Sheet", url_xlsx, "ERROR", 0, str(e))
    anotar_incidencia(url_xlsx, "ERROR", f"No se pudo descargar el Pink Sheet: {e}")

print("\nListo. Revisa la carpeta datos_crudos y el archivo log_ejecucion.txt")
