# Flujo de caja y VAN de un proyecto agroexportador peruano

**Sensibilidad al precio FOB y al tipo de cambio en el arándano, 2012–2025**

- **Autora:** TURIN MERMA, Xiomara Milagros
- **Código de matrícula:** 2024200535B
- **Curso:** Finanzas I (055D) · Escuela Profesional de Economía · UNCP · 2026-II · Unidad II
- **Docente:** Dr. Ciro Iván Machacuay Meza
- **Tema del temario:** N.º 52
- **Dashboard interactivo:** https://xiomaramilagrosturinmerma.github.io/finanzas1-tema52-flujo-caja-van-agroexportador/dashboard/

## Objetivo

Construir el flujo de caja de una campaña agroexportadora de arándano (10 ha, 10 años) y evaluar la
sensibilidad de su VAN al precio FOB y al tipo de cambio, con datos oficiales obtenidos por API y web scraping.

## Resultados principales (escenario base)

| Indicador | Valor |
|---|---|
| VAN (COK 12 %) | S/ 2,993,982 |
| TIR | 27.0 % |
| Relación beneficio/costo | 1.19 |
| Periodo de recuperación | 4.0 años (5.1 años descontado) |
| Precio FOB de equilibrio (VAN = 0) | US$ 5.18/kg (base: US$ 6.38/kg) |
| Tipo de cambio de equilibrio | S/ 3.051 por US$ (base: S/ 3.757) |
| Probabilidad de VAN negativo (Monte Carlo, 10 000 escenarios) | 37.3 % |

Todas las cifras salen de `codigo/04_analisis.py` y están en `salidas/resultados_resumen.json`.

## Estructura del repositorio

```
├── codigo/
│   ├── 01_extraccion_api.py      # API del BCRP y del Banco Mundial
│   ├── 02_scraping_web.py        # scraping de los cuadros de exportación de SUNAT
│   ├── 03_limpieza_datos.py      # limpieza, unión de fuentes y control de calidad
│   └── 04_analisis.py            # tablas, figuras, flujo de caja, VAN, sensibilidad y Monte Carlo
├── datos_crudos/                 # archivos tal como salen de cada fuente + datos_crudos_2024200535B.csv
├── datos_procesados/             # datos_procesados_2024200535B.csv (panel de 1680 filas x 14 columnas)
├── salidas/                      # 11 tablas (.csv y .tex) y 9 figuras (.png y .pdf) del artículo
├── dashboard/                    # dashboard interactivo (lee /datos_procesados y /salidas)
├── diccionario_variables.md
├── incidencias_fuente.md
├── log_ejecucion.txt
├── requirements.txt
└── .env.example
```

## Fuentes y endpoints

| Fuente | Vía | Endpoint | Variables |
|---|---|---|---|
| BCRP – BCRPData | API REST | `https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{código}/json/2012-1/2025-12/esp` | FOB mensual de 10 productos (PN43443BM, PN43444BM, PN43445BM, PN43446BM, PN43447BM, PN43448BM, PN43449BM, PN43450BM, PN43453BM, PN43455BM) y tipo de cambio interbancario (PN01207PM) |
| Banco Mundial | API REST | `https://api.worldbank.org/v2/sources/15/indicators?format=json&per_page=2000` | Revisión de la fuente 15 (GEM): no tiene precios agrícolas (ver incidencias) |
| Banco Mundial – Pink Sheet | Descarga programática | `https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx` | Precios internacionales de café arábica, cacao y naranja; índice de precios agrícolas |
| SUNAT – Estadísticas de exportación | Web scraping | `https://www.sunat.gob.pe/estadisticasestudios/exportaciones.html` → `cdro_G7.xlsx` y `cdro_G9.xlsx` | FOB mensual por subpartida (G7); FOB y peso neto anual por subpartida (G9) para el precio FOB unitario |

Buenas prácticas: se lee `robots.txt` antes del scraping, se usa un User-Agent identificado, se hace una pausa de 1.5 s
entre solicitudes y cada descarga queda registrada en `log_ejecucion.txt`. Las fuentes no requieren clave de API
(`.env.example` queda como plantilla).

## Fecha de corte

- **Periodo de estudio:** `FECHA_INICIO = 2012-01` y `FECHA_CORTE = 2025-12` (constantes declaradas en los cuatro scripts).
- **Fecha de extracción:** 20 de noviembre de 2026.
- **Versión de los archivos de SUNAT:** G7 publicado el 04/11/2026; G9 publicado el 28/09/2026 (fecha `Last-Modified` registrada en el log).

## Orden de ejecución

Desde Spyder (abrir cada archivo y presionar **F5**) o desde la terminal, en la carpeta del proyecto:

```bash
pip install -r requirements.txt
python codigo/01_extraccion_api.py
python codigo/02_scraping_web.py
python codigo/03_limpieza_datos.py
python codigo/04_analisis.py
```

`04_analisis.py` borra y vuelve a generar todo el contenido de `/salidas`. La simulación de Monte Carlo usa como
semilla el código de matrícula (`2024200535`), por lo que sus resultados son reproducibles.

> Si se vuelven a ejecutar 01 y 02 en otra fecha, las fuentes pueden haber actualizado o revisado sus cifras. Para
> reproducir exactamente los resultados del artículo, basta ejecutar 03 y 04 con los archivos de `/datos_crudos`.

## Dashboard

Abrir https://xiomaramilagrosturinmerma.github.io/finanzas1-tema52-flujo-caja-van-agroexportador/dashboard/.
Para verlo en la computadora: ejecutar `python -m http.server` en la carpeta del proyecto y entrar a
`http://localhost:8000/dashboard/`. El dashboard no tiene cifras escritas a mano: lee los archivos de
`/datos_procesados` y `/salidas`, y recalcula el VAN con el mismo modelo de `04_analisis.py`. Incluye un
simulador, una superficie 3D del VAN según el precio FOB y el tipo de cambio, y modo oscuro o claro.

## Versión de Python y librerías

Ver `requirements.txt` (Python 3.12, pandas, numpy, matplotlib, requests y openpyxl).

## Hash SHA-256 de `datos_procesados_2024200535B.csv`

```
dce94013e3dca12db9cb8fec04161354aeacb0df01f9c44eb01e6dda2d05bdbf
```

Para verificarlo en Windows: `certutil -hashfile datos_procesados\datos_procesados_2024200535B.csv SHA256`.

## Repositorio GitHub

https://github.com/XiomaraMilagrosTurinMerma/finanzas1-tema52-flujo-caja-van-agroexportador
