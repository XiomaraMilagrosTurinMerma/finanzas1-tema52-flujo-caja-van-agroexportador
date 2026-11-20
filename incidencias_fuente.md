# Incidencias de la fuente

| Fecha y hora | URL | Código HTTP | Detalle (robots.txt / mensaje) | Captura |
|---|---|---|---|---|
| 2026-11-20 11:09:44 | https://api.worldbank.org/v2/sources/15/indicators?format=json&per_page=2000 | 200 | La API del Banco Mundial (fuente 15, GEM) tiene 36 indicadores y ninguno es un precio agrícola; se usa el archivo oficial Pink Sheet con descarga programática. | -- |
| 2026-11-20 11:12:56 | https://www.worldbank.org/robots.txt | - | El robots.txt del Banco Mundial no permite leer la página de Commodity Markets con un programa; se respetó y se usó el enlace directo oficial del archivo mensual (thedocs.worldbank.org). | -- |
| 2026-11-20 11:28:41 | (archivo en datos_crudos) | - | El cuadro G7 de SUNAT solo incluye las ~500 principales subpartidas; 12 producto-mes quedan sin FOB de SUNAT (se usa el FOB del BCRP). | -- |
| 2026-11-20 11:28:48 | (archivo en datos_crudos) | - | En los cuadros G7 y G9 de SUNAT el encabezado indica 'miles de US$' y 'toneladas', pero las cifras están en US$ y kg (el FOB anual coincide con el BCRP); se convirtieron a millones de US$ y toneladas. | -- |
| 2026-11-20 11:28:48 | (archivo en datos_crudos) | - | Producto 'conservas_frutas_hortalizas': el BCRP agrupa varias subpartidas y el FOB anual de SUNAT difiere en promedio 14.5% del BCRP; su precio FOB unitario es una aproximación del grupo. | -- |
