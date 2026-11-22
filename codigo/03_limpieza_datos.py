# Autora: TURIN MERMA, Xiomara Milagros
# Código de matrícula: 2024200535B
# Tema 52: Flujo de caja y VAN de un proyecto agroexportador peruano
# Fecha de extracción: 2026-11-20
"""
03_limpieza_datos.py
--------------------
Lee los archivos de /datos_crudos (sin modificarlos), los limpia y los une con
la llave PRODUCTO + MES. El resultado es una sola tabla:

    /datos_procesados/datos_procesados_2024200535B.csv
    (10 productos x 168 meses, enero 2012 - diciembre 2025)

Fuentes que se unen:
  - BCRP (API): valor FOB mensual por producto y tipo de cambio.
  - SUNAT cuadro G7: valor FOB mensual por subpartida (validación cruzada).
  - SUNAT cuadro G9: valor FOB y peso neto anual por subpartida
                     -> precio FOB unitario (US$/kg) por producto y año.
  - Banco Mundial (Pink Sheet): precios internacionales mensuales.

Supuesto declarado: SUNAT no publica el peso neto mensual por subpartida; el
volumen mensual se estima como  valor FOB del mes / precio FOB unitario del año.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ------------------------------------------------------------------
# 0. Rutas
# ------------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent
CRUDOS = BASE / "datos_crudos"
PROCESADOS = BASE / "datos_procesados"
LOG = BASE / "log_ejecucion.txt"
INCIDENCIAS = BASE / "incidencias_fuente.md"
DICCIONARIO = BASE / "diccionario_variables.md"
PROCESADOS.mkdir(exist_ok=True)
SALIDA = PROCESADOS / "datos_procesados_2024200535B.csv"

# Periodo de estudio (parámetros congelados, iguales a los de 01 y 02)
FECHA_INICIO = "2012-01"
FECHA_CORTE = "2025-12"
ANIOS = range(int(FECHA_INICIO[:4]), int(FECHA_CORTE[:4]) + 1)
N_MESES = len(pd.period_range(FECHA_INICIO, FECHA_CORTE, freq="M"))
CRUDO_CSV = CRUDOS / "datos_crudos_2024200535B.csv"
crudos = []   # aquí se juntan los valores tal como vienen de cada fuente
MESES_ES = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Ago": 8, "Sep": 9, "Set": 9, "Oct": 10, "Nov": 11, "Dic": 12}

# Producto -> código BCRP y subpartidas SUNAT (prefijos de 10 dígitos).
# Las subpartidas se eligieron para que el FOB anual de SUNAT coincida con el BCRP.
PRODUCTOS = {
    "arandanos":   {"bcrp": "PN43443BM", "sunat": ["0810400000"]},
    "uvas":        {"bcrp": "PN43444BM", "sunat": ["0806100000"]},
    "cafe":        {"bcrp": "PN43445BM", "sunat": ["090111"]},
    "paltas":      {"bcrp": "PN43446BM", "sunat": ["0804400000"]},
    "cacao":       {"bcrp": "PN43447BM", "sunat": ["1801001900"]},
    "esparragos":  {"bcrp": "PN43448BM", "sunat": ["0709200000"]},
    "mangos":      {"bcrp": "PN43449BM", "sunat": ["0804502000"]},
    "mandarinas":  {"bcrp": "PN43450BM", "sunat": ["08052"], "excluir": ["0805291000"]},
    "conservas_frutas_hortalizas": {"bcrp": "PN43453BM",
                                    "sunat": ["2001", "2002", "2003", "2004",
                                              "2005", "2006", "2007", "2008"]},
    "frutas_congeladas": {"bcrp": "PN43455BM", "sunat": ["0811"]},
}

# Producto -> columna de precio internacional en el Pink Sheet del Banco Mundial
PRECIO_BM = {"cafe": "Coffee, Arabica", "cacao": "Cocoa", "mandarinas": "Orange"}


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(texto):
    linea = f"{ahora()} | LIMPIEZA | {texto}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")
    print(linea)


def anotar_incidencia(detalle):
    texto = INCIDENCIAS.read_text(encoding="utf-8") if INCIDENCIAS.exists() else ""
    if detalle in texto:
        return
    with open(INCIDENCIAS, "a", encoding="utf-8") as f:
        f.write(f"| {ahora()} | (archivo en datos_crudos) | - | {detalle} | -- |\n")


def pertenece(codigo, info):
    if codigo in info.get("excluir", []):
        return False
    return any(codigo.startswith(p) for p in info["sunat"])


with open(LOG, "a", encoding="utf-8") as f:
    f.write(f"\n# Ejecución de 03_limpieza_datos.py - {ahora()}\n")

# ------------------------------------------------------------------
# 1. BCRP: valor FOB mensual por producto y tipo de cambio
# ------------------------------------------------------------------
def leer_bcrp(archivo):
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    filas = []
    for p in datos["periods"]:
        mes_txt, anio = p["name"].split(".")
        valor = pd.to_numeric(p["values"][0], errors="coerce")   # "n.d." -> NaN
        filas.append({"anio": int(anio), "mes": MESES_ES[mes_txt], "valor": valor})
        crudos.append({"fuente": "BCRP (API)", "archivo": archivo.name, "hoja": "-",
                       "serie": datos["config"]["series"][0]["name"], "codigo": archivo.name.split("_")[1],
                       "periodo": p["name"], "variable": "valor", "valor_original": p["values"][0]})
    return pd.DataFrame(filas)


bloques = []
for producto, info in PRODUCTOS.items():
    archivo = next(CRUDOS.glob(f"bcrp_{info['bcrp']}_*.json"))
    df = leer_bcrp(archivo).rename(columns={"valor": "fob_bcrp_musd"})
    df.insert(0, "producto", producto)
    df.insert(1, "codigo_bcrp", info["bcrp"])
    bloques.append(df)
panel = pd.concat(bloques, ignore_index=True)

tc = leer_bcrp(next(CRUDOS.glob("bcrp_PN01207PM_*.json"))).rename(columns={"valor": "tipo_cambio"})
panel = panel.merge(tc, on=["anio", "mes"], how="left")
log(f"BCRP leído: {len(panel)} filas producto-mes; {panel['fob_bcrp_musd'].isna().sum()} valores n.d.")

# ------------------------------------------------------------------
# 2. SUNAT G7: valor FOB mensual por subpartida -> suma por producto
#    (los valores del cuadro están en US$; se pasan a millones de US$)
# ------------------------------------------------------------------
filas_g7 = []
for anio in ANIOS:
    g7 = pd.read_excel(CRUDOS / "sunat_cdro_G7.xlsx", sheet_name=str(anio), header=None)
    g7 = g7[pd.to_numeric(g7[3], errors="coerce").notna()].copy()
    g7["codigo"] = g7[3].astype("int64").astype(str).str.zfill(10)
    for producto, info in PRODUCTOS.items():
        sub = g7[g7["codigo"].apply(lambda c: pertenece(c, info))]
        for _, fila in sub.iterrows():
            for mes in range(1, 13):
                crudos.append({"fuente": "SUNAT (cuadro G7)", "archivo": "sunat_cdro_G7.xlsx", "hoja": str(anio),
                               "serie": str(fila[4]), "codigo": fila["codigo"], "periodo": f"{anio}-{mes:02d}",
                               "variable": "valor FOB", "valor_original": fila[4 + mes]})
        for mes in range(1, 13):
            valor = pd.to_numeric(sub[4 + mes], errors="coerce").sum() / 1e6 if len(sub) else np.nan
            filas_g7.append({"producto": producto, "anio": anio, "mes": mes,
                             "fob_sunat_musd": valor, "partidas_g7": len(sub)})
g7_panel = pd.DataFrame(filas_g7)
g7_panel.loc[g7_panel["partidas_g7"] == 0, "fob_sunat_musd"] = np.nan
panel = panel.merge(g7_panel.drop(columns="partidas_g7"), on=["producto", "anio", "mes"], how="left")
faltan_g7 = panel["fob_sunat_musd"].isna().sum()
log(f"SUNAT G7 unido: {faltan_g7} meses sin dato (producto fuera de las principales 500 subpartidas)")
if faltan_g7:
    anotar_incidencia(f"El cuadro G7 de SUNAT solo incluye las ~500 principales subpartidas; "
                      f"{faltan_g7} producto-mes quedan sin FOB de SUNAT (se usa el FOB del BCRP).")

# ------------------------------------------------------------------
# 3. SUNAT G9: precio FOB unitario anual (US$/kg) por producto
#    El encabezado dice "miles de US$" y "toneladas", pero las cifras están
#    en US$ y kg (comprobado: el FOB anual coincide con el BCRP).
# ------------------------------------------------------------------
filas_g9 = []
for anio in ANIOS:
    g9 = pd.read_excel(CRUDOS / "sunat_cdro_G9.xlsx", sheet_name=str(anio), header=None)
    g9 = g9[pd.to_numeric(g9[3], errors="coerce").notna()].copy()
    g9["codigo"] = g9[3].astype("int64").astype(str).str.zfill(10)
    for producto, info in PRODUCTOS.items():
        sub = g9[g9["codigo"].apply(lambda c: pertenece(c, info))]
        for _, fila in sub.iterrows():
            for col, variable in [(7, "valor FOB"), (8, "peso neto")]:
                crudos.append({"fuente": "SUNAT (cuadro G9)", "archivo": "sunat_cdro_G9.xlsx", "hoja": str(anio),
                               "serie": str(fila[4]), "codigo": fila["codigo"], "periodo": str(anio),
                               "variable": variable, "valor_original": fila[col]})
        fob = pd.to_numeric(sub[7], errors="coerce").sum()
        kg = pd.to_numeric(sub[8], errors="coerce").sum()
        filas_g9.append({"producto": producto, "anio": anio,
                         "fob_anual_sunat_musd": fob / 1e6,
                         "peso_anual_sunat_t": kg / 1000,
                         "precio_fob_usd_kg": fob / kg if kg > 0 else np.nan,
                         "n_subpartidas": len(sub)})
g9_panel = pd.DataFrame(filas_g9)
anotar_incidencia("En los cuadros G7 y G9 de SUNAT el encabezado indica 'miles de US$' y "
                  "'toneladas', pero las cifras están en US$ y kg (el FOB anual coincide con el "
                  "BCRP); se convirtieron a millones de US$ y toneladas.")

# Validación: FOB anual SUNAT (G9) vs BCRP
anual_bcrp = panel.groupby(["producto", "anio"], as_index=False)["fob_bcrp_musd"].sum()
valid = g9_panel.merge(anual_bcrp, on=["producto", "anio"])
valid["diferencia_pct"] = 100 * (valid["fob_anual_sunat_musd"] / valid["fob_bcrp_musd"] - 1)
log("Diferencia media |SUNAT G9 vs BCRP| por producto (%): " +
    ", ".join(f"{p}={v:.1f}" for p, v in valid.groupby("producto")["diferencia_pct"]
              .apply(lambda s: s.abs().mean()).items()))

dif = valid.groupby("producto")["diferencia_pct"].apply(lambda s: s.abs().mean())
for producto, d in dif[dif > 5].items():
    anotar_incidencia(f"Producto '{producto}': el BCRP agrupa varias subpartidas y el FOB anual de "
                      f"SUNAT difiere en promedio {d:.1f}% del BCRP; su precio FOB unitario es una "
                      "aproximación del grupo.")

panel = panel.merge(g9_panel[["producto", "anio", "precio_fob_usd_kg", "n_subpartidas"]],
                    on=["producto", "anio"], how="left")

# ------------------------------------------------------------------
# 4. Banco Mundial (Pink Sheet): precios internacionales e índice agrícola
# ------------------------------------------------------------------
pink = CRUDOS / "bancomundial_CMO_Historical_Data_Monthly.xlsx"
precios = pd.read_excel(pink, sheet_name="Monthly Prices", header=None)
encab = precios.iloc[4].tolist()
precios = precios.iloc[6:].copy()
precios["fecha"] = precios[0].astype(str)
precios = precios[precios["fecha"].str.match(r"^\d{4}M\d{2}$")]
precios["anio"] = precios["fecha"].str[:4].astype(int)
precios["mes"] = precios["fecha"].str[5:].astype(int)

filas_bm = []
for producto, columna in PRECIO_BM.items():
    j = encab.index(columna)
    tmp = precios[["anio", "mes"]].copy()
    tmp["precio_int_usd_kg"] = pd.to_numeric(precios[j], errors="coerce")
    for fecha, valor in zip(precios["fecha"], precios[j]):
        if int(fecha[:4]) in ANIOS:
            crudos.append({"fuente": "Banco Mundial (Pink Sheet)", "archivo": pink.name, "hoja": "Monthly Prices",
                           "serie": columna, "codigo": "-", "periodo": fecha, "variable": "precio",
                           "valor_original": valor})
    tmp["producto"] = producto
    filas_bm.append(tmp)
bm = pd.concat(filas_bm)
panel = panel.merge(bm, on=["producto", "anio", "mes"], how="left")

indices = pd.read_excel(pink, sheet_name="Monthly Indices", header=None)
col_agro = next(j for j in indices.columns
                if any(str(indices.iat[i, j]).strip().startswith("Agriculture") for i in range(4, 9)))
indices = indices[indices[0].astype(str).str.match(r"^\d{4}M\d{2}$")]
agro = pd.DataFrame({"anio": indices[0].astype(str).str[:4].astype(int),
                     "mes": indices[0].astype(str).str[5:].astype(int),
                     "indice_agricola_bm": pd.to_numeric(indices[col_agro], errors="coerce")})
panel = panel.merge(agro, on=["anio", "mes"], how="left")
for fecha, valor in zip(indices[0].astype(str), indices[col_agro]):
    if int(fecha[:4]) in ANIOS:
        crudos.append({"fuente": "Banco Mundial (Pink Sheet)", "archivo": pink.name, "hoja": "Monthly Indices",
                       "serie": "Agriculture", "codigo": "-", "periodo": fecha, "variable": "índice",
                       "valor_original": valor})
log("Banco Mundial unido: precio internacional para café, cacao y mandarinas (naranja) "
    "e índice agrícola para todos los productos")

# ------------------------------------------------------------------
# 5. Variables calculadas y orden final
# ------------------------------------------------------------------
panel["fecha"] = pd.to_datetime(dict(year=panel["anio"], month=panel["mes"], day=1)).dt.strftime("%Y-%m")
panel["fob_bcrp_msoles"] = panel["fob_bcrp_musd"] * panel["tipo_cambio"]
# Volumen estimado (toneladas) = FOB del mes (US$) / precio unitario del año (US$/kg) / 1000
panel["volumen_estimado_t"] = panel["fob_bcrp_musd"] * 1e6 / panel["precio_fob_usd_kg"] / 1000

columnas = ["producto", "codigo_bcrp", "fecha", "anio", "mes",
            "fob_bcrp_musd", "fob_sunat_musd", "tipo_cambio", "fob_bcrp_msoles",
            "precio_fob_usd_kg", "volumen_estimado_t", "n_subpartidas",
            "precio_int_usd_kg", "indice_agricola_bm"]
panel = panel[columnas].sort_values(["producto", "fecha"]).reset_index(drop=True)

# Controles de calidad
assert not panel.duplicated(["producto", "fecha"]).any(), "Hay filas duplicadas producto-mes"
assert len(panel) == len(PRODUCTOS) * N_MESES, f"El panel no tiene {len(PRODUCTOS)} x {N_MESES} filas"
negativos = (panel[["fob_bcrp_musd", "volumen_estimado_t"]] < 0).sum().sum()
log(f"Controles: sin duplicados; {len(panel)} filas; valores negativos: {negativos}")
corr = panel[["fob_bcrp_musd", "fob_sunat_musd"]].corr().iloc[0, 1]
log(f"Correlación FOB mensual BCRP vs SUNAT G7: {corr:.4f}")

# ------------------------------------------------------------------
# 6. Guardar, calcular hash y escribir el diccionario de variables
# ------------------------------------------------------------------
# Archivo de datos crudos: todos los valores usados, tal como vienen de cada fuente (sin editar)
crudo = pd.DataFrame(crudos)
crudo["valor_original"] = crudo["valor_original"].astype(str)
crudo.to_csv(CRUDO_CSV, index=False, encoding="utf-8", lineterminator="\n")
log(f"Archivo guardado: datos_crudos/{CRUDO_CSV.name} ({len(crudo)} valores originales de "
    f"{crudo['fuente'].nunique()} fuentes)")

panel.to_csv(SALIDA, index=False, encoding="utf-8", lineterminator="\n")  # "\n": mismo hash en Windows y en GitHub
sha = hashlib.sha256(SALIDA.read_bytes()).hexdigest()
log(f"Archivo guardado: {SALIDA.name} ({len(panel)} filas x {panel.shape[1]} columnas)")
log(f"SHA-256: {sha}")

DICCIONARIO.write_text(f"""# Diccionario de variables

Archivo: `datos_procesados/datos_procesados_2024200535B.csv`
Unidad de observación: producto + mes · Periodo: {FECHA_INICIO} a {FECHA_CORTE} · Filas: {len(panel)}

| Variable | Definición | Unidad | Frecuencia | Fuente | URL o endpoint |
|---|---|---|---|---|---|
| producto | Producto agroexportador (10 productos) | texto | -- | BCRP | -- |
| codigo_bcrp | Código de la serie en BCRPData | texto | -- | BCRP | https://estadisticas.bcrp.gob.pe/estadisticas/series/api/ |
| fecha | Año y mes (AAAA-MM) | fecha | mensual | -- | -- |
| anio | Año | número | mensual | -- | -- |
| mes | Mes (1 a 12) | número | mensual | -- | -- |
| fob_bcrp_musd | Valor FOB exportado | millones de US$ | mensual | BCRP (API) | .../api/<codigo>/json/2012-1/2025-12/esp |
| fob_sunat_musd | Valor FOB exportado según subpartidas SUNAT (validación) | millones de US$ | mensual | SUNAT, cuadro G7 | https://www.sunat.gob.pe/estadisticasestudios/nota_tributaria/cdro_G7.xlsx |
| tipo_cambio | Tipo de cambio interbancario promedio (PN01207PM) | S/ por US$ | mensual | BCRP (API) | .../api/PN01207PM/json/2012-1/2025-12/esp |
| fob_bcrp_msoles | Valor FOB en soles = fob_bcrp_musd x tipo_cambio | millones de S/ | mensual | Cálculo propio | -- |
| precio_fob_usd_kg | Precio FOB unitario = FOB anual / peso neto anual | US$/kg | anual | SUNAT, cuadro G9 | https://www.sunat.gob.pe/estadisticasestudios/nota_tributaria/cdro_G9.xlsx |
| volumen_estimado_t | Volumen exportado estimado = FOB del mes / precio FOB del año | toneladas | mensual | Cálculo propio | -- |
| n_subpartidas | Número de subpartidas SUNAT que forman el producto | número | anual | SUNAT, cuadro G9 | -- |
| precio_int_usd_kg | Precio internacional (café arábica, cacao, naranja para mandarinas) | US$/kg | mensual | Banco Mundial, Pink Sheet | https://thedocs.worldbank.org/.../CMO-Historical-Data-Monthly.xlsx |
| indice_agricola_bm | Índice de precios agrícolas del Banco Mundial | 2010 = 100 | mensual | Banco Mundial, Pink Sheet | idem |

## Archivo de datos crudos

Archivo: `datos_crudos/datos_crudos_2024200535B.csv` · formato largo · un valor por fila, tal como viene de la fuente (sin editar)

| Variable | Definición |
|---|---|
| fuente | BCRP (API), SUNAT (cuadro G7 o G9) o Banco Mundial (Pink Sheet) |
| archivo | Archivo descargado en /datos_crudos del que sale el valor |
| hoja | Hoja del Excel (año en SUNAT; nombre de la hoja en el Pink Sheet) |
| serie | Nombre de la serie, descripción de la subpartida o columna del Pink Sheet |
| codigo | Código de la serie BCRP o de la subpartida SUNAT |
| periodo | Periodo tal como lo escribe la fuente (p. ej., Ene.2012, 2012-01, 2012M01) |
| variable | Qué mide el valor (valor FOB, peso neto, precio, índice) |
| valor_original | Valor sin transformar, guardado como texto |
""", encoding="utf-8")
log("Diccionario de variables actualizado")

print("\nResumen por producto (promedios 2012-2025):")
print(panel.groupby("producto")[["fob_bcrp_musd", "precio_fob_usd_kg", "volumen_estimado_t"]]
      .mean().round(2).to_string())
