# Diccionario de variables

Archivo: `datos_procesados/datos_procesados_2024200535B.csv`
Unidad de observación: producto + mes · Periodo: 2012-01 a 2025-12 · Filas: 1680

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
