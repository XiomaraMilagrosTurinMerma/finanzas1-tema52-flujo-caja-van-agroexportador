# Autora: TURIN MERMA, Xiomara Milagros
# Código de matrícula: 2024200535B
# Tema 52: Flujo de caja y VAN de un proyecto agroexportador peruano
# Fecha de extracción: 2026-11-20
"""
04_analisis.py
--------------
Lee /datos_procesados/datos_procesados_2024200535B.csv y produce TODAS las
tablas y figuras del artículo en /salidas:

  Parte A. Análisis descriptivo de los 10 productos agroexportadores (2012-2025)
  Parte B. Volatilidad del precio FOB y del tipo de cambio
  Parte B2. Precios FOB frente a precios internacionales del Banco Mundial
  Parte C. Flujo de caja, VAN y TIR de un proyecto de 10 ha de arándano
  Parte D. Sensibilidad del VAN al precio FOB y al tipo de cambio
  Parte E. Simulación de Monte Carlo con la volatilidad histórica

Cada tabla se guarda en .csv y en .tex (para pegarla en LaTeX) y cada figura
en .png (300 dpi). Al final se guarda resultados_resumen.json (para el README
y el dashboard).
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")                       # guarda figuras sin abrir ventanas
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm, LinearSegmentedColormap

# ------------------------------------------------------------------
# 0. Rutas y funciones de apoyo
# ------------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent
DATOS = BASE / "datos_procesados" / "datos_procesados_2024200535B.csv"
SALIDAS = BASE / "salidas"
SALIDAS.mkdir(exist_ok=True)
for viejo in list(SALIDAS.glob("*.png")) + list(SALIDAS.glob("*.csv")) + list(SALIDAS.glob("*.tex")) + \
        list(SALIDAS.glob("*.json")):
    viejo.unlink()                          # /salidas se regenera completa en cada ejecución
LOG = BASE / "log_ejecucion.txt"


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(texto):
    print(texto)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{ahora()} | {texto}\n")


def a_latex(df, titulo, etiqueta, nota):
    """Convierte una tabla en código LaTeX (tabla APA con booktabs)."""
    cols = "l" + "r" * (df.shape[1] - 1)
    filas = []
    for _, fila in df.iterrows():
        celdas = [str(v).replace("%", r"\%").replace("_", r"\_").replace("&", r"\&").replace("$", r"\$")
                  for v in fila]
        filas.append(" & ".join(celdas) + r" \\")
    encab = " & ".join(str(c).replace("%", r"\%").replace("_", r"\_").replace("$", r"\$")
                       for c in df.columns) + r" \\"
    return "\n".join([
        r"\begin{table}[H]", r"\centering", r"\small",
        rf"\caption{{{titulo}}}", rf"\label{{{etiqueta}}}",
        rf"\begin{{tabular}}{{{cols}}}", r"\toprule", encab, r"\midrule",
        *filas, r"\bottomrule", r"\end{tabular}",
        rf"\par\vspace{{2pt}}\parbox{{\linewidth}}{{\footnotesize\textit{{Nota.}} {nota}}}",
        r"\end{table}", ""])


def guardar_tabla(df, nombre, titulo, nota):
    df.to_csv(SALIDAS / f"{nombre}.csv", index=False, encoding="utf-8", lineterminator="\n")
    (SALIDAS / f"{nombre}.tex").write_text(a_latex(df, titulo, f"tab:{nombre}", nota), encoding="utf-8")
    log(f"Tabla guardada: salidas/{nombre}.csv y .tex")


def guardar_figura(fig, nombre):
    fig.savefig(SALIDAS / f"{nombre}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    log(f"Figura guardada: salidas/{nombre}.png")


def miles(x, dec=0):
    """Formato 12,345.6 para las tablas (sin '-0')."""
    if round(x, dec) == 0:
        x = 0.0
    return f"{x:,.{dec}f}"


# Estilo de las figuras: ejes y grilla discretos, colores fijos
AZUL, NARANJA, AQUA, AMARILLO, VIOLETA, ROJO = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#6250d6", "#e34948"
GRIS = "#8a8984"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#b5b4ad", "axes.grid": True, "grid.color": "#e6e5e0",
    "grid.linewidth": 0.6, "axes.axisbelow": True, "xtick.color": "#52514e",
    "ytick.color": "#52514e", "axes.labelcolor": "#52514e", "legend.frameon": False,
})

NOMBRES = {
    "arandanos": "Arándanos", "uvas": "Uvas", "cafe": "Café", "paltas": "Paltas",
    "cacao": "Cacao", "esparragos": "Espárragos", "mangos": "Mangos",
    "mandarinas": "Mandarinas", "conservas_frutas_hortalizas": "Conservas de frutas y hortalizas",
    "frutas_congeladas": "Frutas congeladas",
}

# Periodo de análisis (parámetros congelados, iguales a los de 01, 02 y 03)
FECHA_INICIO = "2012-01"
FECHA_CORTE = "2025-12"

with open(LOG, "a", encoding="utf-8") as f:
    f.write(f"\n# Ejecución de 04_analisis.py - {ahora()}\n")

datos = pd.read_csv(DATOS)
datos = datos[(datos["fecha"] >= FECHA_INICIO) & (datos["fecha"] <= FECHA_CORTE)].copy()
datos["nombre"] = datos["producto"].map(NOMBRES)
log(f"Datos leídos: {len(datos)} filas x {datos.shape[1] - 1} columnas")

# Serie anual por producto (el precio FOB por kg es anual en SUNAT G9)
anual = (datos.groupby(["producto", "nombre", "anio"], as_index=False)
              .agg(fob_musd=("fob_bcrp_musd", "sum"),
                   precio_usd_kg=("precio_fob_usd_kg", "mean"),
                   volumen_t=("volumen_estimado_t", "sum")))
tc_anual = datos.groupby("anio")["tipo_cambio"].mean()
tc_mensual = datos.drop_duplicates("fecha").set_index("fecha")["tipo_cambio"]
orden = anual.groupby("nombre")["fob_musd"].sum().sort_values(ascending=False).index

# ==================================================================
# PARTE A. Análisis descriptivo
# ==================================================================
filas = []
for nom in orden:
    a = anual[anual["nombre"] == nom].set_index("anio")
    A0, A1 = int(FECHA_INICIO[:4]), int(FECHA_CORTE[:4])
    ini, fin = a.loc[A0, "fob_musd"], a.loc[A1, "fob_musd"]
    tcac = ((fin / ini) ** (1 / (A1 - A0)) - 1) * 100
    filas.append([nom, miles(a["fob_musd"].sum(), 1), miles(ini, 1), miles(fin, 1),
                  f"{tcac:.1f}", f"{a['precio_usd_kg'].mean():.2f}", miles(a["volumen_t"].sum() / 1000, 1)])
t1 = pd.DataFrame(filas, columns=["Producto", "FOB acumulado (mill. US$)", "FOB 2012", "FOB 2025",
                                  "TCAC 2012-2025 (%)", "Precio medio (US$/kg)", "Volumen acumulado (miles t)"])
guardar_tabla(t1, "tabla1_descriptivos_productos",
              "Exportaciones de los diez productos agroexportadores, 2012--2025",
              "FOB en millones de US\\$. TCAC = tasa de crecimiento anual compuesta. "
              "Volumen estimado como FOB / precio FOB unitario anual. Fuente: BCRP y SUNAT; elaboración propia.")

# Figura 1: evolución del FOB anual (un panel por producto, misma escala de tiempo)
fig, ejes = plt.subplots(2, 5, figsize=(12, 4.6), sharex=True)
for ax, nom in zip(ejes.flat, orden):
    a = anual[anual["nombre"] == nom]
    color = AZUL if nom == "Arándanos" else GRIS
    ax.bar(a["anio"], a["fob_musd"], color=color, width=0.75)
    ax.set_title(nom if len(nom) < 20 else "Conservas frutas/hort.", fontsize=9)
    ax.tick_params(labelsize=7)
fig.supylabel("FOB anual (millones de US$)", fontsize=9)
fig.tight_layout()
guardar_figura(fig, "figura1_fob_anual_productos")

# Figura 2: precio FOB del arándano y tipo de cambio (dos paneles, no doble eje)
aran = anual[anual["producto"] == "arandanos"].set_index("anio")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.4))
ax1.plot(aran.index, aran["precio_usd_kg"], color=AZUL, lw=2, marker="o", ms=4)
ax1.set_title("Precio FOB del arándano (US$/kg)")
ax2.plot(tc_mensual.index.str[:4].astype(int) + (tc_mensual.index.str[5:].astype(int) - 0.5) / 12,
         tc_mensual.values, color=NARANJA, lw=1.6)
ax2.set_title("Tipo de cambio interbancario (S/ por US$)")
for ax in (ax1, ax2):
    ax.set_xlim(2011.5, 2026)
fig.tight_layout()
guardar_figura(fig, "figura2_precio_arandano_tc")

# ==================================================================
# PARTE B. Volatilidad
# ==================================================================
def volat(serie):
    cambios = np.log(serie).diff().dropna()           # variación anual (log)
    return serie.mean(), serie.std(), serie.std() / serie.mean() * 100, cambios.std() * 100

filas, graf = [], []
for nom in orden:
    s = anual[anual["nombre"] == nom].set_index("anio")["precio_usd_kg"]
    m, d, cv, vol = volat(s)
    filas.append([nom, f"{m:.2f}", f"{d:.2f}", f"{cv:.1f}", f"{vol:.1f}", f"{s.min():.2f}", f"{s.max():.2f}"])
    graf.append((nom, vol))
m, d, cv, vol_tc = volat(tc_anual)
filas.append(["Tipo de cambio (S/ por US$)", f"{m:.3f}", f"{d:.3f}", f"{cv:.1f}", f"{vol_tc:.1f}",
              f"{tc_anual.min():.3f}", f"{tc_anual.max():.3f}"])
graf.append(("Tipo de cambio", vol_tc))
t2 = pd.DataFrame(filas, columns=["Variable", "Media", "Desv. est.", "CV (%)",
                                  "Volatilidad anual (%)", "Mínimo", "Máximo"])
guardar_tabla(t2, "tabla2_volatilidad",
              "Volatilidad del precio FOB unitario (US\\$/kg) y del tipo de cambio, 2012--2025",
              "CV = coeficiente de variación. Volatilidad anual = desviación estándar de la variación "
              "logarítmica anual. Fuente: SUNAT (cuadro G9) y BCRP; elaboración propia.")

graf.sort(key=lambda x: x[1])
fig, ax = plt.subplots(figsize=(7, 4))
colores = [AZUL if n == "Arándanos" else (NARANJA if n == "Tipo de cambio" else GRIS) for n, _ in graf]
ax.barh([n if len(n) < 25 else "Conservas frutas/hort." for n, _ in graf], [v for _, v in graf],
        color=colores, height=0.65)
for i, (_, v) in enumerate(graf):
    ax.text(v + 0.4, i, f"{v:.1f}%", va="center", fontsize=8, color="#52514e")
ax.set_xlabel("Volatilidad anual del precio (%)")
ax.grid(axis="y", visible=False)
guardar_figura(fig, "figura3_volatilidad")

# ==================================================================
# PARTE B2. Precios FOB peruanos frente a precios internacionales (Banco Mundial)
# ==================================================================
# El Pink Sheet trae precios internacionales de café arábica, cacao y naranja
# (referencia para mandarinas) y el índice de precios agrícolas (2010 = 100).
anual_bm = (datos.groupby(["producto", "nombre", "anio"], as_index=False)
                 .agg(precio_fob=("precio_fob_usd_kg", "mean"), precio_int=("precio_int_usd_kg", "mean"),
                      indice_agro=("indice_agricola_bm", "mean")))
REFERENCIA_BM = {"Café": "Café arábica", "Cacao": "Cacao", "Mandarinas": "Naranja"}
filas = []
for nom, ref in REFERENCIA_BM.items():
    a = anual_bm[anual_bm["nombre"] == nom].dropna(subset=["precio_int"])
    r_niv = np.corrcoef(a["precio_fob"], a["precio_int"])[0, 1]
    r_var = np.corrcoef(np.log(a["precio_fob"]).diff().dropna(), np.log(a["precio_int"]).diff().dropna())[0, 1]
    filas.append([nom, ref, f"{a['precio_fob'].mean():.2f}", f"{a['precio_int'].mean():.2f}",
                  f"{(a['precio_fob'] / a['precio_int']).mean():.2f}", f"{r_niv:.2f}", f"{r_var:.2f}"])
for nom in ["Arándanos", "Paltas", "Uvas"]:
    a = anual_bm[anual_bm["nombre"] == nom]
    r_niv = np.corrcoef(a["precio_fob"], a["indice_agro"])[0, 1]
    r_var = np.corrcoef(np.log(a["precio_fob"]).diff().dropna(), np.log(a["indice_agro"]).diff().dropna())[0, 1]
    filas.append([nom, "Índice agrícola BM", f"{a['precio_fob'].mean():.2f}", f"{a['indice_agro'].mean():.1f}",
                  "--", f"{r_niv:.2f}", f"{r_var:.2f}"])
t3 = pd.DataFrame(filas, columns=["Producto", "Referencia internacional", "Precio FOB medio (US$/kg)",
                                  "Referencia media", "Ratio FOB / internacional", "Correlación (niveles)",
                                  "Correlación (variaciones)"])
guardar_tabla(t3, "tabla3_precios_internacionales",
              "Precio FOB peruano frente a precios internacionales del Banco Mundial, 2012--2025",
              "Promedios anuales. Precios internacionales en US\\$/kg; índice agrícola con base 2010 = 100. "
              "Correlación de Pearson entre series anuales (niveles) y entre sus variaciones logarítmicas. "
              "Fuente: SUNAT (cuadro G9) y Banco Mundial (Pink Sheet); elaboración propia.")

fig, ejes = plt.subplots(1, 4, figsize=(13, 3.3))
for ax, (nom, ref) in zip(ejes[:3], REFERENCIA_BM.items()):
    a = anual_bm[anual_bm["nombre"] == nom]
    ax.plot(a["anio"], a["precio_fob"], color=AZUL, lw=2, marker="o", ms=3.5, label="FOB Perú (SUNAT)")
    ax.plot(a["anio"], a["precio_int"], color=NARANJA, lw=2, marker="o", ms=3.5, label=f"{ref} (Banco Mundial)")
    ax.set_title(f"{nom} (US$/kg)")
    ax.legend(fontsize=7, loc="upper left")
a = anual_bm[anual_bm["nombre"] == "Arándanos"].set_index("anio")
ejes[3].plot(a.index, a["precio_fob"] / a["precio_fob"].iloc[0] * 100, color=AZUL, lw=2, marker="o", ms=3.5,
             label="Precio FOB arándano")
ejes[3].plot(a.index, a["indice_agro"] / a["indice_agro"].iloc[0] * 100, color=NARANJA, lw=2, marker="o",
             ms=3.5, label="Índice agrícola BM")
ejes[3].axhline(100, color=GRIS, lw=0.8)
ejes[3].set_title(f"Arándano e índice agrícola ({FECHA_INICIO[:4]} = 100)")
ejes[3].legend(fontsize=7, loc="lower left")
for ax in ejes:
    ax.tick_params(labelsize=7)
fig.tight_layout()
guardar_figura(fig, "figura4_precios_internacionales")

# ==================================================================
# PARTE C. Flujo de caja del proyecto de arándano
# ==================================================================
# --- Supuestos tomados de los datos propios (BCRP y SUNAT) ---
P_BASE = aran.loc[2021:2025, "precio_usd_kg"].mean()     # precio FOB base: promedio 2021-2025
P_MIN, P_MAX = aran["precio_usd_kg"].min(), aran["precio_usd_kg"].max()
TC_BASE = tc_anual.loc[2021:2025].mean()                  # TC base: promedio 2021-2025
TC_MIN, TC_MAX = tc_anual.min(), tc_anual.max()
VOL_P = np.log(aran["precio_usd_kg"]).diff().std()        # volatilidad histórica del precio
VOL_TC = np.log(tc_anual).diff().std()
CORR = np.corrcoef(np.log(aran["precio_usd_kg"]).diff().dropna(),
                   np.log(tc_anual).diff().dropna())[0, 1]

# --- Supuestos técnicos (fuentes citadas en el artículo) ---
HA = 10                               # hectáreas del proyecto
RENDIMIENTO_T_HA = 20                 # rendimiento maduro en maceta: 20-35 t/ha (USDA FAS, 2024)
# Curva de producción (fracción del rendimiento maduro, años 0..10). La cosecha empieza
# alrededor del segundo año (Flores et al., 2023); el año 2 al 50 % es un supuesto propio.
CURVA = [0, 0, 0.5] + [1.0] * 8
INV_USD_HA = 65_000                   # inversión promedio por ha (USDA FAS, 2024)
EXPORTABLE = 0.90                     # supuesto; rango 76 %-95 % según Chang (2026)
# Costos de operación de Chang (2026): costo fijo de US$ 1.30 por kg exportado con 21 t/ha y 95 %
# exportable, y utilidad de US$ 3.87/kg con precio de US$ 7.50/kg.
FIJO_USD_HA = 1.30 * 21_000 * 0.95    # costo fijo anual por ha (= US$ 25,935)
VAR_USD_KG = 7.50 - 3.87 - 1.30       # costo variable por kg exportado: cosecha, packing y logística (= US$ 2.33)
COK = 0.12                            # costo de oportunidad del capital (sensibilidad 8 %-16 %)
ANIO_INICIO = 2026                    # año 0 = 2026; campañas 2027-2036
HORIZONTE = 10


def tasa_ir(anio):
    """Ley 32434: tasa de 15 % para empresas agrarias de 2026 a 2035; régimen general (29.5 %) desde 2036."""
    return 0.15 if anio <= 2035 else 0.295


def flujo_caja(precio=None, tc=None, rend=1.0, inv=1.0, fijo=1.0, var=1.0, exportable=EXPORTABLE,
               precios_anuales=None, tcs_anuales=None):
    """Flujo de caja económico en soles. Los ingresos se cobran en US$ (se convierten con el TC);
    la inversión y los costos se pagan en soles (convertidos una sola vez con el TC base)."""
    precio = P_BASE if precio is None else precio
    tc = TC_BASE if tc is None else tc
    inversion = INV_USD_HA * HA * TC_BASE * inv
    dep = inversion / HORIZONTE
    filas = [{"anio": 0, "anio_cal": ANIO_INICIO, "produccion_t": 0, "exportado_t": 0, "precio_usd_kg": 0,
              "tc": 0, "ingresos": 0, "costo_variable": 0, "costo_fijo": 0, "depreciacion": 0,
              "utilidad_ai": 0, "impuesto": 0, "inversion": -inversion, "flujo_neto": -inversion}]
    for t in range(1, HORIZONTE + 1):
        p = precios_anuales[t - 1] if precios_anuales is not None else precio
        e = tcs_anuales[t - 1] if tcs_anuales is not None else tc
        prod_t = RENDIMIENTO_T_HA * HA * CURVA[t] * rend
        exp_kg = prod_t * 1000 * exportable
        ingresos = exp_kg * p * e
        c_var = exp_kg * VAR_USD_KG * TC_BASE * var
        c_fijo = FIJO_USD_HA * HA * TC_BASE * fijo
        uai = ingresos - c_var - c_fijo - dep
        imp = tasa_ir(ANIO_INICIO + t) * max(uai, 0)
        filas.append({"anio": t, "anio_cal": ANIO_INICIO + t, "produccion_t": prod_t,
                      "exportado_t": exp_kg / 1000, "precio_usd_kg": p, "tc": e, "ingresos": ingresos,
                      "costo_variable": -c_var, "costo_fijo": -c_fijo, "depreciacion": -dep,
                      "utilidad_ai": uai, "impuesto": -imp, "inversion": 0,
                      "flujo_neto": uai - imp + dep})
    return pd.DataFrame(filas)


def van(flujos, tasa=COK):
    t = np.arange(len(flujos))
    return float(np.sum(np.asarray(flujos) / (1 + tasa) ** t))


def tir(flujos):
    """TIR por bisección (la tasa que hace VAN = 0)."""
    bajo, alto = -0.99, 5.0
    if van(flujos, bajo) * van(flujos, alto) > 0:
        return np.nan
    for _ in range(200):
        medio = (bajo + alto) / 2
        if van(flujos, bajo) * van(flujos, medio) <= 0:
            alto = medio
        else:
            bajo = medio
    return medio


def periodo_recuperacion(flujos, tasa=0.0):
    acum = np.cumsum(np.asarray(flujos) / (1 + tasa) ** np.arange(len(flujos)))
    for t in range(1, len(acum)):
        if acum[t] >= 0:
            return t - 1 + (-acum[t - 1]) / (acum[t] - acum[t - 1])
    return np.nan


def punto_equilibrio(funcion, bajo, alto):
    """Valor de la variable que hace VAN = 0 (bisección)."""
    for _ in range(200):
        medio = (bajo + alto) / 2
        if funcion(bajo) * funcion(medio) <= 0:
            alto = medio
        else:
            bajo = medio
    return medio


# Tabla 4: supuestos del proyecto
t3 = pd.DataFrame([
    ["Superficie", f"{HA} ha", "Supuesto del proyecto"],
    ["Horizonte de evaluación", f"{HORIZONTE} años (2027-2036)", "Supuesto del proyecto"],
    ["Rendimiento maduro", f"{RENDIMIENTO_T_HA} t/ha (desde el año 3)", "USDA FAS (2024)"],
    ["Curva de producción", "0 % / 50 % / 100 % (años 1 / 2 / 3-10)", "Flores et al. (2023); supuesto propio"],
    ["Inversión (instalación)", f"US$ {INV_USD_HA:,.0f} por ha", "USDA FAS (2024)"],
    ["Costo fijo de operación", f"US$ {FIJO_USD_HA:,.0f} por ha/año", "Chang (2026)"],
    ["Costo variable (cosecha, packing, logística)", f"US$ {VAR_USD_KG:.2f} por kg exportado", "Chang (2026)"],
    ["Fracción exportable", f"{EXPORTABLE:.0%}", "Supuesto; rango de Chang (2026)"],
    ["Precio FOB base", f"US$ {P_BASE:.2f} por kg (prom. 2021-2025)", "SUNAT, cuadro G9"],
    ["Tipo de cambio base", f"S/ {TC_BASE:.3f} por US$ (prom. 2021-2025)", "BCRP (PN01207PM)"],
    ["Impuesto a la renta", "15 % (2027-2035); 29.5 % (2036)", "Ley 32434"],
    ["Costo de oportunidad (COK)", f"{COK:.0%} (sensibilidad 8 %-16 %)", "MEF (2024); Damodaran (2026)"],
], columns=["Variable", "Valor", "Fuente"])
guardar_tabla(t3, "tabla4_supuestos_proyecto", "Supuestos del proyecto de 10 ha de arándano",
              "La inversión y los costos se convierten a soles con el tipo de cambio base. Elaboración propia.")

base = flujo_caja()
VAN_BASE, TIR_BASE = van(base["flujo_neto"]), tir(base["flujo_neto"])
PRI = periodo_recuperacion(base["flujo_neto"])
PRID = periodo_recuperacion(base["flujo_neto"], COK)
va_ing = van(base["ingresos"])
va_cos = -van(base["costo_variable"] + base["costo_fijo"] + base["impuesto"] + base["inversion"])
BC = va_ing / va_cos

# Tabla 5: flujo de caja (miles de soles)
conceptos = [("Producción (t)", "produccion_t", 1), ("Volumen exportado (t)", "exportado_t", 1),
             ("Ingresos por exportación", "ingresos", 1e3), ("Costo variable", "costo_variable", 1e3),
             ("Costo fijo", "costo_fijo", 1e3), ("Depreciación", "depreciacion", 1e3),
             ("Utilidad antes de impuestos", "utilidad_ai", 1e3), ("Impuesto a la renta", "impuesto", 1e3),
             ("(+) Depreciación", "depreciacion", -1e3), ("Inversión", "inversion", 1e3),
             ("Flujo de caja neto", "flujo_neto", 1e3)]
t4 = pd.DataFrame({"Concepto": [c for c, _, _ in conceptos]})
for _, fila in base.iterrows():
    t4[f"Año {int(fila['anio'])}"] = [miles(fila[col] / div, 0) for _, col, div in conceptos]
guardar_tabla(t4, "tabla5_flujo_caja",
              "Flujo de caja económico del proyecto de arándano (miles de soles)",
              "Producción y volumen en toneladas; el resto en miles de S/. Escenario base: precio FOB "
              f"US\\$ {P_BASE:.2f}/kg y TC S/ {TC_BASE:.3f}. Elaboración propia.")

# Tabla 6: indicadores
t5 = pd.DataFrame([
    ["VAN al 12 %", f"S/ {miles(VAN_BASE)}"], ["TIR", f"{TIR_BASE * 100:.1f} %"],
    ["Relación beneficio/costo", f"{BC:.2f}"], ["Periodo de recuperación simple", f"{PRI:.1f} años"],
    ["Periodo de recuperación descontado", f"{PRID:.1f} años"],
    ["VAN al 8 %", f"S/ {miles(van(base['flujo_neto'], 0.08))}"],
    ["VAN al 16 %", f"S/ {miles(van(base['flujo_neto'], 0.16))}"],
], columns=["Indicador", "Valor"])
guardar_tabla(t5, "tabla6_indicadores", "Indicadores de rentabilidad del escenario base",
              "VAN = valor actual neto; TIR = tasa interna de retorno. Elaboración propia.")

# Figura 5: flujo de caja neto y flujo acumulado descontado
acum_desc = np.cumsum(base["flujo_neto"] / (1 + COK) ** base["anio"])
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.bar(base["anio"], base["flujo_neto"] / 1e6, color=[ROJO if v < 0 else AZUL for v in base["flujo_neto"]],
       width=0.7)
ax.add_patch(plt.Rectangle((0, 0), 0, 0, color=AZUL, label="Flujo de caja neto (rojo si es negativo)"))
ax.plot(base["anio"], acum_desc / 1e6, color=NARANJA, lw=2, marker="o", ms=5,
        label="Flujo acumulado descontado al 12 %")
ax.axhline(0, color="#52514e", lw=0.8)
ax.set_xticks(base["anio"])
ax.set_xlabel("Año del proyecto")
ax.set_ylabel("Millones de S/")
ax.legend(loc="upper left")
ax.annotate(f"VAN = S/ {VAN_BASE / 1e6:.2f} mill.", (10, acum_desc.iloc[-1] / 1e6),
            textcoords="offset points", xytext=(-10, 4), ha="right", fontsize=8)
guardar_figura(fig, "figura5_flujo_caja")

# ==================================================================
# PARTE D. Sensibilidad al precio FOB y al tipo de cambio
# ==================================================================
P_EQ = punto_equilibrio(lambda p: van(flujo_caja(precio=p)["flujo_neto"]), 0.5, 20)
TC_EQ = punto_equilibrio(lambda e: van(flujo_caja(tc=e)["flujo_neto"]), 0.5, 10)

# Tabla 7: sensibilidad al precio FOB
filas = []
for cambio in [-0.30, -0.20, -0.10, 0, 0.10, 0.20, 0.30]:
    f = flujo_caja(precio=P_BASE * (1 + cambio))["flujo_neto"]
    v = van(f)
    filas.append([f"{cambio:+.0%}" if cambio else "Base", f"{P_BASE * (1 + cambio):.2f}", miles(v),
                  f"{tir(f) * 100:.1f}", f"{(v / VAN_BASE - 1) * 100:+.1f}"])
t6 = pd.DataFrame(filas, columns=["Variación del precio", "Precio (US$/kg)", "VAN (S/)", "TIR (%)",
                                  "Cambio del VAN (%)"])
guardar_tabla(t6, "tabla7_sensibilidad_precio", "Sensibilidad del VAN al precio FOB del arándano",
              f"Tipo de cambio fijo en S/ {TC_BASE:.3f}. Precio de equilibrio (VAN = 0): "
              f"US\\$ {P_EQ:.2f}/kg. Elaboración propia.")

# Tabla 8: sensibilidad al tipo de cambio
filas = []
for etiqueta, e in [("Mínimo 2012-2025", TC_MIN), ("-10 %", TC_BASE * 0.9), ("Base", TC_BASE),
                    ("+10 %", TC_BASE * 1.1), ("Máximo 2012-2025", TC_MAX)]:
    f = flujo_caja(tc=e)["flujo_neto"]
    v = van(f)
    filas.append([etiqueta, f"{e:.3f}", miles(v), f"{tir(f) * 100:.1f}", f"{(v / VAN_BASE - 1) * 100:+.1f}"])
t7 = pd.DataFrame(filas, columns=["Escenario", "TC (S/ por US$)", "VAN (S/)", "TIR (%)", "Cambio del VAN (%)"])
guardar_tabla(t7, "tabla8_sensibilidad_tc", "Sensibilidad del VAN al tipo de cambio",
              f"Precio FOB fijo en US\\$ {P_BASE:.2f}/kg. TC de equilibrio (VAN = 0): S/ {TC_EQ:.3f}. "
              "Elaboración propia.")

# Figura 6: VAN frente al precio y frente al TC (dos paneles)
precios = np.linspace(3, 12, 61)
tcs = np.linspace(2.4, 4.2, 61)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.6))
ax1.plot(precios, [van(flujo_caja(precio=p)["flujo_neto"]) / 1e6 for p in precios], color=AZUL, lw=2)
ax1.axhline(0, color="#52514e", lw=0.8)
ax1.axvline(P_BASE, color=GRIS, lw=0.8, ls="--")
ax1.plot([P_EQ], [0], "o", color=ROJO, ms=7)
ax1.annotate(f"Equilibrio: US$ {P_EQ:.2f}", (P_EQ, 0), textcoords="offset points", xytext=(8, -14), fontsize=8)
ax1.annotate(f"Base: US$ {P_BASE:.2f}", (P_BASE, ax1.get_ylim()[1]), textcoords="offset points",
             xytext=(4, -12), fontsize=8, color="#52514e")
ax1.set_xlabel("Precio FOB (US$/kg)")
ax1.set_ylabel("VAN (millones de S/)")
ax1.set_title("VAN según el precio FOB")
ax2.plot(tcs, [van(flujo_caja(tc=e)["flujo_neto"]) / 1e6 for e in tcs], color=NARANJA, lw=2)
ax2.axhline(0, color="#52514e", lw=0.8)
ax2.axvspan(TC_MIN, TC_MAX, color=NARANJA, alpha=0.08)
ax2.axvline(TC_BASE, color=GRIS, lw=0.8, ls="--")
ax2.annotate("Rango histórico 2012–2025", (TC_MIN, ax2.get_ylim()[0]), textcoords="offset points",
             xytext=(4, 6), fontsize=8, color="#52514e")
ax2.set_xlabel("Tipo de cambio (S/ por US$)")
ax2.set_title("VAN según el tipo de cambio")
fig.tight_layout()
guardar_figura(fig, "figura6_sensibilidad_precio_tc")

# Figura 7: mapa de calor del VAN (precio x TC)
rejilla_p = np.round(np.arange(4.0, 11.51, 0.5), 2)
rejilla_tc = np.round(np.arange(2.6, 4.01, 0.1), 2)
matriz = np.array([[van(flujo_caja(precio=p, tc=e)["flujo_neto"]) / 1e6 for p in rejilla_p] for e in rejilla_tc])
pd.DataFrame(matriz, index=rejilla_tc, columns=rejilla_p).round(3).to_csv(
    SALIDAS / "matriz_van_precio_tc.csv", index_label="tc/precio", lineterminator="\n")
divergente = LinearSegmentedColormap.from_list("rojo_gris_azul", [ROJO, "#f2f1ed", AZUL])
fig, ax = plt.subplots(figsize=(9, 4.6))
lim = np.abs(matriz).max()
im = ax.imshow(matriz, origin="lower", aspect="auto", cmap=divergente, norm=TwoSlopeNorm(0, -lim, lim),
               extent=[rejilla_p[0] - 0.25, rejilla_p[-1] + 0.25, rejilla_tc[0] - 0.05, rejilla_tc[-1] + 0.05])
ax.contour(rejilla_p, rejilla_tc, matriz, levels=[0], colors="#0b0b0b", linewidths=1.2)
ax.plot(P_BASE, TC_BASE, marker="*", color="#0b0b0b", ms=11)
ax.annotate("Escenario base", (P_BASE, TC_BASE), textcoords="offset points", xytext=(8, 4), fontsize=8)
ax.set_xlabel("Precio FOB (US$/kg)")
ax.set_ylabel("Tipo de cambio (S/ por US$)")
ax.grid(False)
barra = fig.colorbar(im, ax=ax)
barra.set_label("VAN (millones de S/)")
guardar_figura(fig, "figura7_mapa_calor_van")

# Tabla 9 y Figura 8: análisis tornado (cada variable ±20 %; COK 8 %-16 %; exportable 76 %-95 %)
casos = [
    ("Precio FOB", lambda: van(flujo_caja(precio=P_BASE * 0.8)["flujo_neto"]),
     lambda: van(flujo_caja(precio=P_BASE * 1.2)["flujo_neto"]), "-20 % / +20 %"),
    ("Tipo de cambio", lambda: van(flujo_caja(tc=TC_BASE * 0.8)["flujo_neto"]),
     lambda: van(flujo_caja(tc=TC_BASE * 1.2)["flujo_neto"]), "-20 % / +20 %"),
    ("Rendimiento", lambda: van(flujo_caja(rend=0.8)["flujo_neto"]),
     lambda: van(flujo_caja(rend=1.2)["flujo_neto"]), "-20 % / +20 %"),
    ("Fracción exportable", lambda: van(flujo_caja(exportable=0.76)["flujo_neto"]),
     lambda: van(flujo_caja(exportable=0.95)["flujo_neto"]), "76 % / 95 %"),
    ("Inversión", lambda: van(flujo_caja(inv=1.2)["flujo_neto"]),
     lambda: van(flujo_caja(inv=0.8)["flujo_neto"]), "+20 % / -20 %"),
    ("Costo fijo", lambda: van(flujo_caja(fijo=1.2)["flujo_neto"]),
     lambda: van(flujo_caja(fijo=0.8)["flujo_neto"]), "+20 % / -20 %"),
    ("Costo variable", lambda: van(flujo_caja(var=1.2)["flujo_neto"]),
     lambda: van(flujo_caja(var=0.8)["flujo_neto"]), "+20 % / -20 %"),
    ("COK", lambda: van(base["flujo_neto"], 0.16), lambda: van(base["flujo_neto"], 0.08), "16 % / 8 %"),
]
tornado = sorted([(n, bajo(), alto(), r) for n, bajo, alto, r in casos], key=lambda x: x[2] - x[1])
t8 = pd.DataFrame([[n, r, miles(b), miles(a), miles(a - b)] for n, b, a, r in reversed(tornado)],
                  columns=["Variable", "Rango evaluado", "VAN desfavorable (S/)", "VAN favorable (S/)",
                           "Amplitud (S/)"])
guardar_tabla(t8, "tabla9_tornado", "Análisis tornado: impacto de cada variable en el VAN",
              f"VAN base = S/ {miles(VAN_BASE)}. Elaboración propia.")
fig, ax = plt.subplots(figsize=(8, 3.8))
for i, (n, b, a, r) in enumerate(tornado):
    ax.barh(i, (b - VAN_BASE) / 1e6, left=VAN_BASE / 1e6, color=ROJO, height=0.6)
    ax.barh(i, (a - VAN_BASE) / 1e6, left=VAN_BASE / 1e6, color=AZUL, height=0.6)
    ax.text(min(a, b) / 1e6, i, f"{r}  ", va="center", ha="right", fontsize=7, color="#52514e")
ax.set_yticks(range(len(tornado)))
ax.set_yticklabels([n for n, *_ in tornado])
ax.axvline(VAN_BASE / 1e6, color="#0b0b0b", lw=1)
ax.set_xlabel("VAN (millones de S/)")
ax.grid(axis="y", visible=False)
ax.set_xlim(min(min(b, a) for _, b, a, _ in tornado) / 1e6 - 2.2, None)
ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=ROJO), plt.Rectangle((0, 0), 1, 1, color=AZUL)],
          labels=["Escenario desfavorable", "Escenario favorable"], loc="upper center",
          bbox_to_anchor=(0.5, 1.12), ncol=2)
guardar_figura(fig, "figura8_tornado")

# Tabla 10: escenarios con valores históricos de precio y TC
filas = []
for nombre, p, e in [("Pesimista (mínimos históricos)", P_MIN, TC_MIN), ("Base (promedio 2021-2025)", P_BASE, TC_BASE),
                     ("Optimista (máximos históricos)", P_MAX, TC_MAX)]:
    f = flujo_caja(precio=p, tc=e)["flujo_neto"]
    filas.append([nombre, f"{p:.2f}", f"{e:.3f}", miles(van(f)), f"{tir(f) * 100:.1f}" if not np.isnan(tir(f)) else "n.d."])
t9 = pd.DataFrame(filas, columns=["Escenario", "Precio (US$/kg)", "TC (S/ por US$)", "VAN (S/)", "TIR (%)"])
guardar_tabla(t9, "tabla10_escenarios", "VAN y TIR en escenarios históricos de precio FOB y tipo de cambio",
              "Valores anuales mínimos y máximos de 2012--2025. Fuente: SUNAT y BCRP; elaboración propia.")

# ==================================================================
# PARTE E. Simulación de Monte Carlo (10 000 escenarios)
# ==================================================================
# El precio y el TC siguen un paseo aleatorio lognormal (movimiento browniano
# geométrico sin tendencia): cada año reciben un choque con la volatilidad y la
# correlación históricas, y el choque se acumula. Semilla = código de matrícula.
rng = np.random.default_rng(2024200535)
N = 10_000
cov = np.array([[VOL_P ** 2, CORR * VOL_P * VOL_TC], [CORR * VOL_P * VOL_TC, VOL_TC ** 2]])
vans = np.empty(N)
for i in range(N):
    z = rng.multivariate_normal([0, 0], cov, size=HORIZONTE)
    t = np.arange(1, HORIZONTE + 1)
    p = P_BASE * np.exp(np.cumsum(z[:, 0]) - t * VOL_P ** 2 / 2)
    e = TC_BASE * np.exp(np.cumsum(z[:, 1]) - t * VOL_TC ** 2 / 2)
    vans[i] = van(flujo_caja(precios_anuales=p, tcs_anuales=e)["flujo_neto"])
PROB_NEG = (vans < 0).mean()
t10 = pd.DataFrame([
    ["Número de simulaciones", f"{N:,}"],
    ["Volatilidad anual del precio FOB", f"{VOL_P * 100:.1f} %"],
    ["Volatilidad anual del tipo de cambio", f"{VOL_TC * 100:.1f} %"],
    ["Correlación precio - tipo de cambio", f"{CORR:.2f}"],
    ["VAN promedio", f"S/ {miles(vans.mean())}"],
    ["VAN mediano", f"S/ {miles(np.median(vans))}"],
    ["Percentil 5 del VAN", f"S/ {miles(np.percentile(vans, 5))}"],
    ["Percentil 95 del VAN", f"S/ {miles(np.percentile(vans, 95))}"],
    ["Probabilidad de VAN negativo", f"{PROB_NEG * 100:.2f} %"],
], columns=["Indicador", "Valor"])
guardar_tabla(t10, "tabla11_montecarlo", "Resultados de la simulación de Monte Carlo",
              "Precio y TC simulados como paseo aleatorio lognormal; volatilidades y correlación estimadas con las "
              "variaciones logarítmicas anuales 2012--2025. "
              "Semilla aleatoria: 2024200535. Elaboración propia.")
fig, ax = plt.subplots(figsize=(8, 3.6))
lim_inf, lim_sup = np.percentile(vans / 1e6, [0.5, 99.5])
ax.hist(np.clip(vans / 1e6, lim_inf, lim_sup), bins=60, color=AZUL, edgecolor="white", linewidth=0.4)
ax.axvline(0, color=ROJO, lw=1.2)
ax.axvline(VAN_BASE / 1e6, color="#0b0b0b", lw=1, ls="--")
ax.annotate("VAN = 0", (0, ax.get_ylim()[1]), textcoords="offset points", xytext=(-4, -12), ha="right",
            fontsize=8, color=ROJO)
ax.annotate(f"VAN base (S/ {VAN_BASE / 1e6:.2f} mill.)", (VAN_BASE / 1e6, ax.get_ylim()[1]),
            textcoords="offset points", xytext=(4, -12), fontsize=8)
ax.set_xlabel("VAN (millones de S/); los extremos (0.5 % de cada cola) se agrupan en los bordes")
ax.set_ylabel("Número de simulaciones")
ax.grid(axis="x", visible=False)
guardar_figura(fig, "figura9_montecarlo")

# ==================================================================
# Resumen para el README y el dashboard
# ==================================================================
resumen = {
    "fecha_ejecucion": ahora(), "precio_base_usd_kg": round(P_BASE, 4), "tc_base": round(TC_BASE, 4),
    "van_base_soles": round(VAN_BASE, 2), "tir_base": round(TIR_BASE, 4), "beneficio_costo": round(BC, 4),
    "periodo_recuperacion_anios": round(PRI, 2), "periodo_recuperacion_descontado_anios": round(PRID, 2),
    "precio_equilibrio_usd_kg": round(P_EQ, 4), "tc_equilibrio": round(TC_EQ, 4),
    "volatilidad_precio": round(VOL_P, 4), "volatilidad_tc": round(VOL_TC, 4), "correlacion": round(CORR, 4),
    "montecarlo_prob_van_negativo": round(PROB_NEG, 4),
    "montecarlo_van_p5": round(float(np.percentile(vans, 5)), 2),
    "montecarlo_van_p95": round(float(np.percentile(vans, 95)), 2),
}
(SALIDAS / "resultados_resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
base.round(2).to_csv(SALIDAS / "flujo_caja_base_detalle.csv", index=False, lineterminator="\n")
log(f"VAN base = S/ {VAN_BASE:,.0f} | TIR = {TIR_BASE:.1%} | B/C = {BC:.2f} | PRI = {PRI:.1f} años")
log(f"Precio de equilibrio = US$ {P_EQ:.2f}/kg | TC de equilibrio = S/ {TC_EQ:.3f}")
log(f"Monte Carlo: P(VAN<0) = {PROB_NEG:.2%}")
log("04_analisis.py terminado: 11 tablas y 9 figuras en /salidas")
