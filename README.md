# Desbalance oferta-demanda en el componente troncal de TransMilenio mediante ciencia de datos

Trabajo de grado — **Ciencia de Datos, Universidad Externado de Colombia**
Autor: **Iván Ramiro Pinzón Pinto** · Directora: **Yessica Velásquez**

Análisis del desbalance entre la **cobertura de servicio asignada** y la **demanda de pasajeros** en las estaciones del componente troncal de TransMilenio, a partir de 24 meses de validaciones de la tarjeta TuLlave (enero 2024 – diciembre 2025).

> **Pregunta de investigación.** ¿En qué estaciones y franjas horarias del componente troncal de TransMilenio existe un desbalance entre la cobertura de servicio asignada y la demanda de pasajeros durante el periodo 2024–2025?

## Indicadores

- **ICP — Índice de Cobertura Ponderada (sección 3.4).** Cuantifica la cobertura de servicio asignada a cada estación integrando el número de rutas, el tipo de bus (biarticulado = 250, articulado = 160, padrón dual = 80 pasajeros, según la información de flota troncal de TransMilenio S.A.; el TCQSM aporta el marco conceptual de capacidad) y una ponderación en forma de V (piso 0,30) según la posición de la estación dentro de cada ruta. Es **estático** (no varía por hora ni tipo de día): limitación explícita derivada de que TransMilenio no publica frecuencias del troncal.
- **IPD — Índice de Presión de Demanda (sección 3.5).** Cociente entre las validaciones observadas y el ICP (`IPD = validaciones / ICP`); señala dónde y cuándo la demanda iguala o supera la cobertura asignada. Se interpreta como **presión relativa**, no como saturación física, y el análisis se restringe a días hábiles no festivos.

## Correspondencia notebooks ↔ capítulo 3 (metodología)

Los cuadernos documentan en celdas markdown **el porqué de cada decisión metodológica**, con referencia a la sección del capítulo 3 que la define:

| # | Cuaderno | Secciones | Decisiones que implementa |
|---|----------|-----------|---------------------------|
| 00 | `00_preparacion_datos` | sección 3.1–3.3 | Fuentes; mapeo por **código** (no por nombre); formato ancho→largo; agregación de accesos; calendario de festivos; exclusión de cierres por obras del Metro (ausencia de filas en los archivos fuente) |
| 01 | `01_OE1_patrones` | sección 3.6 | EDA en dos niveles; Lorenz/Gini; outliers IQR (se conservan); Shapiro-Wilk → estadística no paramétrica (Spearman, Kruskal-Wallis); verificación lectivo vs. receso (no se excluyen meses) |
| 02 | `02_OE2-OE3_ICP_IPD` | sección 3.4–3.5 | ICP con ponderación en V (piso 0,30) y capacidades de flota troncal (TransMilenio S.A.); IPD y su sesgo por ICP estático; **sensibilidad del piso** (0,10–0,50 y ponderación plana, con ARI) |
| 03 | `03_OE4_conglomerados` | sección 3.7 | K-Means (justificado frente a DBSCAN/jerárquico); z-score; K=4 por codo+silueta; validación (silueta por estación, estabilidad ARI, contraste jerárquico Ward); Kruskal-Wallis + Mann-Whitney/Bonferroni |
| 04 | `04_OE5_modelo_XGBoost` | sección 3.8 | Especificaciones anidadas M0–M2 + M3 (rezago 7 días); partición temporal 80/20; búsqueda con TimeSeriesSplit; objetivo Poisson (contraste log1p); gain+SHAP; bootstrap por estación; umbrales de presión 1,0/1,5 con sensibilidad |

## Estructura del repositorio

```
tesis-transmilenio/
├── README.md
├── requirements.txt
├── notebooks/                       # se corren EN ORDEN; cada uno carga lo del anterior
│   ├── 00_preparacion_datos.ipynb
│   ├── 01_OE1_patrones.ipynb
│   ├── 02_OE2-OE3_ICP_IPD.ipynb
│   ├── 03_OE4_conglomerados.ipynb
│   └── 04_OE5_modelo_XGBoost.ipynb
├── scripts/
│   ├── generar_code_to_matriz.py        # reconstruye el diccionario código→estación (--check para auditar)
│   ├── verificar_mapeo.py               # audita el diccionario contra el catálogo oficial (por código)
│   └── construir_matriz_ruta_estacion.py  # construye/audita la matriz ruta-estación (--check)
├── data/
│   ├── raw/                         # 24 .xlsx de validaciones (NO versionados — ver README interno)
│   ├── soporte/                     # insumos versionados (ver diccionario de datos abajo)
│   └── intermedia/                  # .parquet generados al correr (NO versionados)
├── outputs/
│   ├── figuras/                     # figuras exportadas (.png)
│   └── tablas/                      # icp_por_estacion, conglomerados_por_estacion, validacion_conglomerados, metricas_modelo, oe1_*
├── mapa_geo/                        # capa QGIS de estaciones/corredores; se genera con build_mapa_gpkg.py
├── presentacion/                    # presentación y guion de sustentación (no son parte del pipeline)
└── _archivo/                        # versiones viejas y archivos no usados (NO versionado)
```

### Diccionario de datos — `data/soporte/`

| Archivo | Qué es | Quién lo usa |
|---|---|---|
| `matriz_ruta_estacion_troncal.csv` | Secuencia ordenada de paradas por servicio troncal (102 rutas, 1.460 paradas), con tipo de bus, capacidad y corredor. Corte dic-2025 | 00 |
| `Servicios__Rutas_Troncales_y_Zonales_.csv` | Catálogo oficial de servicios (tipo de bus por ruta) | 00 |
| `code_to_matriz.json` | Diccionario código→estación (155 códigos → 148 estaciones). **Reconstruible**: `generar_code_to_matriz.py` | 00, 01, 02 |
| `correspondencia_oficial_matriz.json` | Tabla curada nombre oficial → nombre matriz (solo los casos que difieren) | `generar_code_to_matriz.py` |
| `catalogo_estaciones_troncales.geojson` | Catálogo oficial georreferenciado (150 estaciones, atributos de infraestructura). Fuente autoritativa código→estación | 00, 01, 02 |
| `transmilenio_troncal_estaciones.csv` | Versión tabular del catálogo; **referencial** (los notebooks usan el geojson) | — |

Los archivos de soporte que no participan en el pipeline (tablas de trabajo del proceso de curaduría, insumos de enfoques descartados) se movieron a `_archivo/soporte_no_usado/` para no confundir la reproducción.

## Reproducción (para el jurado)

```bash
pip install -r requirements.txt          # Python 3.11
```

1. **Descargar las validaciones** (no versionadas por tamaño, ~330 MB): portal de datos abiertos de TransMilenio (`datosabiertos-transmilenio.hub.arcgis.com`), conjunto *Resumen de Validaciones Troncales* (intervalo 15 min), 24 archivos de ene-2024 a dic-2025, guardados en `data/raw/`. Instrucciones detalladas en `data/raw/README.md`.
2. **Correr los cuadernos en orden** (00 → 01 → 02 → 03 → 04). Cada uno guarda `.parquet` en `data/intermedia/` que el siguiente carga; la consolidación pesada de los 24 meses se corre una sola vez (cuaderno 00). El cuaderno 04 incluye la búsqueda de hiperparámetros y el bootstrap: es el más costoso (decenas de minutos según la máquina).
3. **Verificar los insumos construidos** (opcional, recomendado):
   - `python scripts/verificar_mapeo.py` — audita el diccionario código→estación contra el catálogo oficial.
   - `python scripts/generar_code_to_matriz.py --check` — confirma que el diccionario versionado coincide con el reconstruido.
   - `python scripts/construir_matriz_ruta_estacion.py --check` — confirma que la matriz ruta-estación versionada coincide con la generada desde las fuentes oficiales.

| # | Carga | Guarda |
|---|-------|--------|
| 00 | Excel de validaciones + CSV/JSON de soporte | `validaciones_consolidadas`, `matriz_estandarizada`, `troncal_serv` |
| 01 | `validaciones_consolidadas` | figuras + tablas `oe1_*` |
| 02 | `matriz_estandarizada`, `troncal_serv`, `validaciones_consolidadas` | `panel_icp_ipd`, `icp`, `icp_por_estacion.csv` |
| 03 | `panel_icp_ipd` | `panel_con_clusters`, `cluster_df`, `conglomerados_por_estacion.csv`, `validacion_conglomerados.json` |
| 04 | `panel_con_clusters`, `cluster_df`, `icp` | `metricas_modelo.csv`, `ipd_completo.csv` |

**Garantías de reproducibilidad:**
- Semilla fija (`random_state=42`) en muestreos, conglomerados, búsqueda de hiperparámetros y bootstrap.
- Particiones y validación cruzada **temporales** (sin filtración de información futura).
- Las rutas se resuelven automáticamente desde la raíz del repo (los cuadernos funcionan ejecutados desde `notebooks/` o desde la raíz).
- `outputs/tablas/ipd_completo.csv` (~590 MB) no se versiona: se regenera corriendo el cuaderno 04.