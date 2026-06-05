# Desbalance Oferta-Demanda en el Componente Troncal de TransMilenio Mediante Ciencia de Datos

Trabajo de grado — **Ciencia de Datos, Universidad Externado de Colombia**
Autor: **Iván Ramiro Pinzón Pinto** · Directora: **Yessica Velásquez**

Análisis del desbalance entre la **cobertura de servicio asignada** y la **demanda de pasajeros** en las estaciones del componente troncal de TransMilenio, a partir de 24 meses de validaciones de la tarjeta TuLlave (enero 2024 – diciembre 2025).

> **Pregunta de investigación.** ¿En qué estaciones y franjas horarias del componente troncal de TransMilenio existe un desbalance entre la cobertura de servicio asignada y la demanda de pasajeros durante el periodo 2024–2025?

## Indicadores

- **ICP — Índice de Cobertura Ponderada.** Cuantifica la cobertura de servicio asignada a cada estación integrando el número de rutas, el tipo de bus (biarticulado = 250, articulado = 160, padrón dual = 80 pasajeros) y una ponderación en forma de V según la posición de la estación dentro de cada ruta.
- **IPD — Índice de Presión de Demanda.** Cociente entre las validaciones observadas y el ICP (`IPD = validaciones / ICP`); señala dónde y cuándo la demanda iguala o supera la cobertura asignada.

## Estructura del repositorio

```
tesis-transmilenio/
├── README.md
├── requirements.txt
├── .gitignore
├── notebooks/                       # se corren EN ORDEN; cada uno carga lo del anterior
│   ├── 00_preparacion_datos.ipynb       # §3.1–3.3  consolida 24 meses + mapeo por código
│   ├── 01_OE1_patrones.ipynb            # OE1  patrones espaciotemporales
│   ├── 02_OE2-OE3_ICP_IPD.ipynb         # OE2/OE3  ICP, IPD y sensibilidad del piso V
│   ├── 03_OE4_conglomerados.ipynb       # OE4  conglomerados + validación
│   └── 04_OE5_modelo_XGBoost.ipynb      # OE5  modelo y anticipación de picos
├── scripts/
│   ├── generar_code_to_matriz.py        # reconstruye el mapeo código→estación
|   └── verificar_mapeo.py               # verifica que los códigos y las estaciones en la matriz estén correctos 
├── data/
│   ├── raw/                         # 24 .xlsx de validaciones (NO versionado — ver README interno)
│   ├── soporte/                     # matriz de paradas, servicios, catálogo, diccionarios
│   └── intermedia/                  # .parquet generados al correr (NO versionado)
├── outputs/
│   ├── figuras/                     # figuras exportadas (.png)
│   └── tablas/                      # icp_estaciones, conglomerados_estaciones, metricas_modelo
└── mapa_geo/                          # capa geográfica de estaciones/corredores (.gpkg, .geojson)
```

## Orden de ejecución

Los cuadernos se ejecutan **en secuencia**: cada uno guarda un `.parquet` en `data/intermedia/` que el siguiente carga, de modo que la consolidación pesada de los 24 meses se corre **una sola vez**.

| # | Cuaderno | Objetivo | Carga | Guarda |
|---|----------|----------|-------|--------|
| 00 | `00_preparacion_datos` | §3.1–3.3 | Excel de validaciones + CSV de soporte | `validaciones_consolidadas`, `matriz_estandarizada`, `troncal_serv` |
| 01 | `01_OE1_patrones` | OE1 | `validaciones_consolidadas` | figuras |
| 02 | `02_OE2-OE3_ICP_IPD` | OE2, OE3 | `matriz_estandarizada`, `troncal_serv`, `validaciones_consolidadas` | `panel_icp_ipd`, `icp` |
| 03 | `03_OE4_conglomerados` | OE4 | `panel_icp_ipd` | `panel_con_clusters`, `cluster_df` |
| 04 | `04_OE5_modelo_XGBoost` | OE5 | `panel_con_clusters`, `cluster_df`, `icp` | métricas + tablas finales |

## Datos

Por tamaño, **no se versionan** las validaciones mensuales (`data/raw/*.xlsx`, ~330 MB) ni el panel completo `outputs/tablas/ipd_completo.csv` (~590 MB, supera el límite de GitHub). Se obtienen así:

- **Validaciones:** portal de datos abiertos de TransMilenio (`datosabiertos-transmilenio.hub.arcgis.com`), conjunto *Resumen de Validaciones Troncales* (intervalo 15 min), 24 archivos de ene-2024 a dic-2025. Instrucciones en `data/raw/README.md`.
- **`ipd_completo.csv`:** se regenera corriendo `02_OE2-OE3_ICP_IPD`.

Los **datos de soporte** (matriz de paradas, catálogo de servicios y de estaciones, y diccionarios de equivalencia código→estación) sí están versionados en `data/soporte/`, de modo que el pipeline es reproducible una vez descargadas las validaciones.

## Reproducibilidad

```bash
pip install -r requirements.txt
```

- Semilla fija (`random_state=42`) en conglomerados y modelo.
- Ajustar las rutas en la celda de configuración de `00_preparacion_datos`.
- Probado con Python 3.11.

## Calendario de entregas (hallazgos)

| Fecha | Entrega |
|-------|---------|
| 12 jun | 00 + 01 + 02 — OE1, OE2, OE3 |
| 19 jun | 03 — OE4 (conglomerados + robustez) |
| 26 jun | 04 — OE5 (validación cruzada, hiperparámetros, métricas desagregadas) |
