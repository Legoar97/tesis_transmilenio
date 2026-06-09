# -*- coding: utf-8 -*-
"""
fix_notebooks.py — Aplica dos reemplazos a los cuadernos del proyecto editando
el JSON de nbformat con json puro (sin dependencias externas).

  1) notebooks/02_OE2-OE3_ICP_IPD.ipynb
     La celda que recalculaba la capacidad por tipo de bus desde el catálogo de
     servicios (CAPACIDAD / MANUAL_CAPACIDAD / asignar_capacidad) se reemplaza:
     la capacidad ya viene como columna en matriz_ruta_estacion_troncal.csv.

  2) notebooks/00_preparacion_datos.ipynb
     La celda UNIFICAR_MATRIZ (renombres pensados para la matriz vieja) se
     reemplaza por una verificación de los nombres de la matriz contra
     code_to_matriz.json.

Antes de escribir cada cuaderno se crea un backup <nombre>.ipynb.bak.
No toca "outputs" ni "execution_count" (solo el campo "source" de la celda
afectada). Es idempotente: si el reemplazo ya está aplicado, no escribe nada.

Uso:
    python scripts/fix_notebooks.py
"""

import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NB_DIR = RAIZ / "notebooks"

# ---------------------------------------------------------------------------
# Bloques de 02_OE2-OE3_ICP_IPD.ipynb
# (la primera línea "# ====" de la celda no se toca: el bloque empieza después)
# ---------------------------------------------------------------------------
OLD_02 = r'''# ASIGNACIÓN DE CAPACIDAD POR TIPO DE BUS
# =============================================

CAPACIDAD = {1.0: 250, 2.0: 160, 3.0: 80}

# Asignación manual para rutas sin match en catálogo de servicios
MANUAL_CAPACIDAD = {
    '1': 250,  # biarticulado — confirmado, no está en catálogo
}

troncal_serv['ruta_norm'] = (troncal_serv['cod_ruta']
    .str.replace(' ', '').str.replace('-', '').str.upper().str.strip())
ruta_tipbus = dict(zip(troncal_serv['ruta_norm'], troncal_serv['tip_bus']))

def asignar_capacidad(ruta, tipo):
    """Asigna capacidad según tipo de bus de la ruta."""
    rn = str(ruta).replace(' ', '').replace('-', '').upper().strip()
    # 1. Buscar en catálogo de servicios
    if rn in ruta_tipbus:
        return CAPACIDAD.get(ruta_tipbus[rn], 160)
    # 2. Buscar en asignación manual
    if rn in MANUAL_CAPACIDAD:
        return MANUAL_CAPACIDAD[rn]
    # 3. Fallback por tipo de ruta
    if tipo == 'RF':
        return 160
    elif tipo == 'DU':
        return 80
    else:
        return 160

matriz['capacidad'] = matriz.apply(lambda r: asignar_capacidad(r['ruta'], r['tipo']), axis=1)

print("Distribución de capacidades asignadas:")
print(matriz.groupby('capacidad')['ruta'].nunique().to_frame('n_rutas'))'''

NEW_02 = r'''# CAPACIDAD POR TIPO DE BUS — VIENE EN LA MATRIZ
# =============================================

# La matriz ruta-estación (matriz_ruta_estacion_troncal.csv) ya trae la capacidad
# nominal oficial por ruta según el tipo de bus del GIS de TransMilenio
# (capa consulta_rutas_troncales): biarticulado=250, articulado=160, padrón dual=80.
# NO se recalcula desde el catálogo de servicios: su campo tip_bus está desactualizado
# y los fallbacks anteriores usaban los códigos de la matriz vieja ('RF'/'DU'),
# que en la matriz vigente son 'Fácil'/'Expreso'/'Dual' (dejaba M85/P85 en 160 y no 80).

assert matriz['capacidad'].isin([250, 160, 80]).all(), 'Capacidad fuera de {250, 160, 80}'
assert matriz.groupby('ruta')['capacidad'].nunique().eq(1).all(), 'Hay rutas con capacidad mixta'

print("Distribución de capacidades (columna de la matriz):")
print(matriz.groupby('capacidad')['ruta'].nunique().to_frame('n_rutas'))
print("\nRutas por tipo y capacidad:")
print(matriz.drop_duplicates('ruta').groupby(['tipo', 'capacidad'])['ruta'].count().to_frame('n_rutas'))'''

# ---------------------------------------------------------------------------
# Bloques de 00_preparacion_datos.ipynb
# (la primera línea "# ====" de la celda no se toca: el bloque empieza después)
# ---------------------------------------------------------------------------
OLD_00 = r'''# CORRECCIÓN: Unificar nombres duplicados en la matriz
# =============================================

UNIFICAR_MATRIZ = {
    'AV 1° de Mayo': 'AV. 1° de Mayo',
    'AV. 1° Mayo': 'AV. 1° de Mayo',
    'Alcalá - Col S. Tomás Dominicos': 'Alcalá - Col. S. Tomás Dominicos',
    'Calle 40 Sur': 'Calle 40 S.',
    'Calle 40S.': 'Calle 40 S.',
    'Castellana': 'La Castellana',
    'Guatoque-Veraguas': 'Guatoque - Veraguas',
    'KR. 90': 'KR 90',
    'Las Aguas - C. Col. Americano': 'Las Aguas - C. Col Americano',
    'NQS - Calle 30 Sur': 'NQS - Calle 30 S.',
    'NQS - Calle 30S.': 'NQS - Calle 30 S.',
    'NQS - Calle 38A Sur': 'NQS - Calle 38A S.',
    'Portal Eldorado- C.C. NUESTRO BOGOTÁ': 'Portal Eldorado - C.C. NUESTRO BOGOTÁ',
    'Suba - TV. 91': 'Suba - TV 91',
    'Tygua-San José': 'Tygua - San José',
    'Terreros Hsp. C.V.': 'Terreros - Hospital C.V.',
}

antes = matriz['estacion'].nunique()
matriz['estacion'] = matriz['estacion'].replace(UNIFICAR_MATRIZ)
despues = matriz['estacion'].nunique()

print(f"Estaciones antes: {antes}")
print(f"Estaciones después: {despues}")
print(f"Duplicados unificados: {antes - despues}")'''

NEW_00 = r'''# VERIFICACIÓN: nombres de la matriz vs. mapeo por código
# =============================================
# La matriz nueva (matriz_ruta_estacion_troncal.csv) ya usa exactamente los nombres
# canónicos de code_to_matriz.json, así que NO se renombra nada. (La antigua celda
# UNIFICAR_MATRIZ era para la matriz vieja: renombraba 4 estaciones a la grafía
# antigua —AV. 1° Mayo, Calle 40 Sur, Tygua-San José, Guatoque-Veraguas— y eso
# las desconectaba de las validaciones: el IPD quedaba con 144 de 148 estaciones.)

nombres_canon = set(code_to_matriz.values())
fuera = sorted(set(matriz['estacion']) - nombres_canon)
print(f"Estaciones de la matriz: {matriz['estacion'].nunique()}")
print(f"Fuera del canon code_to_matriz: {len(fuera)}")
if fuera:
    print("  ->", fuera)
    raise ValueError("Hay nombres de la matriz que no cruzarán con las validaciones")'''

REEMPLAZOS = [
    (NB_DIR / "02_OE2-OE3_ICP_IPD.ipynb", OLD_02, NEW_02),
    (NB_DIR / "00_preparacion_datos.ipynb", OLD_00, NEW_00),
]


def aplicar(path: Path, old: str, new: str) -> bool:
    """Reemplaza old->new en la única celda de código que lo contiene."""
    nb = json.loads(path.read_text(encoding="utf-8-sig"))

    encontradas = []
    ya_estaba = False
    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", [])
        s = src if isinstance(src, str) else "".join(src)
        if new in s:
            ya_estaba = True
        if old in s:
            encontradas.append((i, cell, s, isinstance(src, str)))

    if not encontradas:
        if ya_estaba:
            print(f"  [OK] {path.name}: el reemplazo ya estaba aplicado; no se modifica.")
            return True
        print(f"  [ERROR] {path.name}: no se encontro el bloque original "
              f"(la celda pudo haber cambiado); no se escribe nada.")
        return False
    if len(encontradas) > 1:
        print(f"  [ERROR] {path.name}: el bloque aparece en {len(encontradas)} "
              f"celdas; se esperaba 1. No se escribe nada.")
        return False

    i, cell, s, era_str = encontradas[0]
    s_nuevo = s.replace(old, new, 1)
    # Solo se toca "source"; "outputs" y "execution_count" quedan intactos.
    cell["source"] = s_nuevo if era_str else s_nuevo.splitlines(keepends=True)

    bak = Path(str(path) + ".bak")
    shutil.copy2(path, bak)

    texto = json.dumps(nb, ensure_ascii=False, indent=1) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(texto)

    # Verificacion: el archivo escrito es JSON valido, contiene el bloque nuevo
    # y ya no contiene el viejo.
    nb_check = json.loads(path.read_text(encoding="utf-8"))
    fuentes = []
    for c in nb_check.get("cells", []):
        sc = c.get("source", [])
        fuentes.append(sc if isinstance(sc, str) else "".join(sc))
    todo = "\n".join(fuentes)
    if new not in todo or old in todo:
        print(f"  [ERROR] {path.name}: la verificacion post-escritura fallo. "
              f"Restaura desde {bak.name}.")
        return False

    print(f"  [OK] {path.name}: celda {i} reemplazada. Backup: {bak.name}")
    return True


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print(f"Raiz del proyecto: {RAIZ}")
    exito = True
    for path, old, new in REEMPLAZOS:
        print(f"\n-> {path.name}")
        if not path.exists():
            print(f"  [ERROR] No existe: {path}")
            exito = False
            continue
        try:
            if not aplicar(path, old, new):
                exito = False
        except Exception as exc:
            print(f"  [ERROR] {path.name}: {exc}")
            exito = False

    print()
    if exito:
        print("Listo: ambos cuadernos quedaron actualizados (o ya lo estaban).")
    else:
        print("Termino con errores; revisa los mensajes de arriba. "
              "Los .bak conservan la version previa de lo que si se escribio.")
    return 0 if exito else 1


if __name__ == "__main__":
    sys.exit(main())
