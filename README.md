# Código — Tesis TransMilenio ICP/IPD
# Iván Ramiro Pinzón Pinto
# Universidad Externado de Colombia — Ciencia de Datos
# Marzo 2026

## Archivos incluidos

### Notebook principal
- `tesis_transmilenio_icp_v2.ipynb` — Notebook completo con 9 secciones.
  Para ejecutar: ajustar DATA_DIR y SUPPORT_DIR en la celda de configuración.

### Archivos de soporte (poner en la carpeta SUPPORT_DIR)
- `code_to_matriz.json` — Mapeo de 154 códigos de estación al nombre estandarizado
  en la matriz ruta-estación. Este es el archivo clave para el merge.
- `code_to_matriz.csv` — Versión legible del mapeo para revisión.

### Archivos de referencia (no necesarios para ejecutar, pero documentan el proceso)
- `station_master_mapping.json` — Mapeo triple: nombre en validaciones -> nombre oficial -> nombre en matriz.
- `station_master_mapping.csv` — Versión legible del mapeo triple.

## Datos necesarios (NO incluidos, descargar de datosabiertos-transmilenio.hub.arcgis.com)

### En DATA_DIR (carpeta de validaciones):
- 24 archivos .xlsx de "Resumen de Validaciones Troncales" (enero 2024 - diciembre 2025)

### En SUPPORT_DIR (carpeta de soporte):
- `matriz_paradas_troncales_dic2025.csv` — Matriz ruta-estación
- `Servicios__Rutas_Troncales_y_Zonales_.csv` — Catálogo de servicios con tipo de bus
- `Estaciones_Troncales_de_TRANSMILENIO.csv` — Catálogo oficial de estaciones
- `code_to_matriz.json` — (incluido en este zip, copiar aquí)

## Terminología
- **Cobertura de servicio asignada**: capacidad estructural que el sistema asigna a cada
  estación a través de las rutas, tipos de bus y posición en el recorrido.
- **ICP (Índice de Cobertura Ponderada)**: cuantifica la cobertura de servicio asignada.
- **IPD (Índice de Presión de Demanda)**: razón validaciones / ICP.

## Dependencias
pip install pandas numpy matplotlib seaborn scikit-learn xgboost openpyxl
