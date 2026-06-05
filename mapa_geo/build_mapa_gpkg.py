"""
build_mapa_gpkg.py
==================
Construye el GeoPackage de la red troncal de TransMilenio para ArcGIS Pro / QGIS,
con la paleta OFICIAL por zona (A-M) y los campos auxiliares necesarios para un
mapa publicable (etiquetas de portales, tamano de punto y ancho de linea).

Entrada : data/soporte/catalogo_estaciones_troncales.geojson  (catalogo oficial, 150 estaciones)
Salida  : mapa_troncal.gpkg
    - capa 'estaciones' (puntos):
        num_est, nom_est, id_trazado, zona, corredor, color_hex,
        es_portal, tipo, metro_l1,
        etiqueta   -> nombre SOLO en portales ('' en el resto): etiquetar este campo
                      en ArcGIS /QGIS muestra unicamente los portales, sin filtros.
        tamano_pt  -> tamano sugerido del punto (portal=11, estacion=5.5) para
                      'Vary symbology by attribute > Size'.
    - capa 'corredores' (lineas):
        id_trazado, zona, corredor, color_hex, n_est,
        ancho_linea -> ancho sugerido (pt).

Uso:
    python build_mapa_gpkg.py
Las rutas se resuelven relativas a la raiz del repo (igual que en los cuadernos),
por lo que el script es reproducible desde cualquier ubicacion del proyecto.

"""
import os
import numpy as np
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString

# --- rutas (raiz del repo) ---
RAIZ = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(RAIZ) in ('scripts', 'arcgis'):
    RAIZ = os.path.dirname(RAIZ)
GEOJSON = os.path.normpath(os.path.join(RAIZ, '..', 'data', 'soporte', 'catalogo_estaciones_troncales.geojson'))
OUT_DIR = os.path.join(RAIZ)
os.makedirs(OUT_DIR, exist_ok=True)
GPKG = os.path.join(OUT_DIR, 'mapa_troncal.gpkg')

# ============================================================
# 1) Mapeo id_trazado -> (zona, corredor, color oficial)
#    OJO (verificar con conocimiento del sistema):
#      - TZ014 (Portal Tunal, Parque, Biblioteca): ramal Tunal, empata en Sta. Lucia.
#      - TZ007 (Guatoque-Veraguas, Tygua-San Jose): conector Comuneros/Cra 50.
# ============================================================
TRAZADO_ZONA = {
    'TZ001': ('A', 'Caracas',            '#00529B'),  # azul
    'TZ002': ('B', 'Autopista Norte',    '#6DB043'),  # verde
    'TZ003': ('C', 'Suba',               '#FFD100'),  # amarillo
    'TZ005': ('D', 'Calle 80',           '#713A84'),  # morado
    'TZ008': ('E', 'NQS Central',        '#7A4B21'),  # cafe
    'TZ009': ('F', 'Americas',           '#E31837'),  # rojo
    'TZ010': ('G', 'NQS Sur',            '#009CDE'),  # celeste
    'TZ011': ('G', 'NQS Sur (Soacha)',   '#009CDE'),  # celeste (ext.)
    'TZ012': ('H', 'Caracas Sur',        '#F37021'),  # naranja
    'TZ013': ('H', 'Caracas Sur (Usme)', '#F37021'),  # naranja (ext.)
    'TZ014': ('H', 'Tunal',              '#F37021'),  # naranja  [VERIFICAR]
    'TZ015': ('J', 'Eje Ambiental',      '#E482AE'),  # rosado
    'TZ016': ('K', 'Calle 26',           '#C49A45'),  # dorado
    'TZ018': ('L', 'Carrera 10',         '#00A39F'),  # turquesa
    'TZ019': ('M', 'Carrera 7',          '#C20078'),  # magenta
    'TZ007': ('E', 'Conector Comuneros', '#7A4B21'),  # cafe     [VERIFICAR]
}

# --- estado por obras del Metro L1 (a corte 2025, nombres exactos del catalogo) ---
CERRADAS = {'Tercer Milenio', 'Calle 19', 'Calle 26', 'AV. 39',
            'Calle 63', 'Calle 72', 'Hospital', 'SENA'}
PROVISIONALES = {'Temporal Calle 22', 'Temporal Calle 34', 'Temporal Calle 57',
                 'Temporal Marly', 'Flores \u2013 Areandina'}

def estado_metro(nom):
    if nom in CERRADAS:       return 'Cerrada por obras Metro L1'
    if nom in PROVISIONALES:  return 'Provisional (contingencia Metro L1)'
    return 'Operativa'

# ============================================================
# 2) Capa de estaciones
# ============================================================
gj = gpd.read_file(GEOJSON)
gj['num_est'] = gj['num_est'].astype(str).str.strip().str.zfill(5)   # 9005 -> 09005

reg = []
for _, r in gj.iterrows():
    tz = r.get('id_trazado')
    zona, corredor, color = TRAZADO_ZONA.get(tz, ('?', 'Sin asignar', '#BBBBBB'))
    nom = str(r.get('nom_est', '')).strip()
    es_portal = int('portal' in nom.lower())
    reg.append({
        'num_est'   : r['num_est'],
        'nom_est'   : nom,
        'id_trazado': tz,
        'zona'      : zona,
        'corredor'  : corredor,
        'color_hex' : color,
        'es_portal' : es_portal,
        'tipo'      : 'Portal' if es_portal else 'Estacion troncal',
        'metro_l1'  : estado_metro(nom),
        'etiqueta'  : nom if es_portal else '',      # <- etiquetar este campo = solo portales
        'tamano_pt' : 11.0 if es_portal else 5.5,    # <- size-by-attribute
        'geometry'  : Point(float(r['longitud']), float(r['latitud'])),
    })
estaciones = gpd.GeoDataFrame(reg, geometry='geometry', crs='EPSG:4326')

# ============================================================
# 3) Capa de corredores (lineas) — ordena estaciones por el eje principal
# ============================================================
def ordenar_por_eje(sub):
    """Ordena los puntos de un corredor a lo largo de su eje principal (PCA 1D),
    corrigiendo la longitud por cos(lat) para aproximar distancias reales."""
    xy = np.column_stack([sub.geometry.x.values, sub.geometry.y.values])
    lat0 = np.deg2rad(xy[:, 1].mean())
    m = xy.copy()
    m[:, 0] = m[:, 0] * np.cos(lat0)
    m = m - m.mean(axis=0)
    _, _, vh = np.linalg.svd(m, full_matrices=False)
    t = m @ vh[0]
    return sub.iloc[np.argsort(t)]

lineas = []
for tz, sub in estaciones.groupby('id_trazado'):
    if len(sub) < 2:
        continue                                  # trazados de 1 estacion no generan linea
    sub_ord = ordenar_por_eje(sub)
    zona, corredor, color = TRAZADO_ZONA.get(tz, ('?', 'Sin asignar', '#BBBBBB'))
    lineas.append({
        'id_trazado': tz, 'zona': zona, 'corredor': corredor,
        'color_hex': color, 'n_est': len(sub), 'ancho_linea': 2.4,
        'geometry': LineString(list(sub_ord.geometry)),
    })
corredores = gpd.GeoDataFrame(lineas, geometry='geometry', crs='EPSG:4326')

# ============================================================
# 4) Escritura
# ============================================================
if os.path.exists(GPKG):
    os.remove(GPKG)                               # evita duplicar capas en re-runs
estaciones.to_file(GPKG, layer='estaciones', driver='GPKG')
corredores.to_file(GPKG, layer='corredores', driver='GPKG')

print(f'GeoPackage: {GPKG}')
print(f'  estaciones : {len(estaciones)}  (portales: {estaciones.es_portal.sum()})')
print(f'  corredores : {len(corredores)} lineas')
print(f'  con etiqueta (portales): {(estaciones.etiqueta != "").sum()}')
print('\nPortales etiquetados:')
print(estaciones.loc[estaciones.es_portal == 1, ['nom_est', 'zona', 'color_hex']].to_string(index=False))
