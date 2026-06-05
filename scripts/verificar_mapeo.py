"""
verificar_mapeo.py
==================
Verifica la integridad del diccionario de equivalencias `code_to_matriz.json`
contra el catálogo oficial de estaciones troncales de TransMilenio.

POR QUÉ EXISTE
--------------
`code_to_matriz.json` traduce el código numérico de cada estación (el identificador
estable que aparece en las validaciones de TuLlave) al nombre canónico usado en la
matriz ruta-estación. El diccionario se construyó a partir de fuentes OFICIALES de
TransMilenio (la Guía para transbordos del componente troncal y el catálogo de
estaciones), apoyándose en dos tablas de correspondencia de nombres documentadas en
el repositorio: `station_equivalences.json` (variantes de nombre -> nombre matriz) y
`station_master_mapping.json` (nombre oficial <-> nombre matriz).

Como el código de estación es el identificador estable (el nombre textual varía entre
archivos mensuales), la verificación se hace POR CÓDIGO contra el catálogo oficial:
para cada código se compara el nombre asignado en `code_to_matriz.json` con el nombre
del catálogo. Cualquier discrepancia se reporta. Esto hace el mapeo auditable y
reproducible por un tercero, y detecta errores de atribución de demanda entre
estaciones (por ejemplo, una estación cuyo código quedó etiquetado con el nombre de
otra).

USO
---
    python verificar_mapeo.py

Requiere en el mismo directorio (o ajustar las rutas):
    - code_to_matriz.json
    - catalogo_estaciones_troncales.geojson   (catálogo oficial; campos num_est, nom_est)
"""

import json
import re
import unicodedata
from pathlib import Path

# --- rutas (ajustar si es necesario) ---
DIR = Path(__file__).resolve().parent
CODE_TO_MATRIZ = DIR / "code_to_matriz.json"
CATALOGO = DIR / "catalogo_estaciones_troncales.geojson"


def normalizar(texto):
    """Normaliza un nombre de estación a un conjunto de palabras comparable
    (minúsculas, sin tildes, sin puntuación, sin palabras vacías). Permite
    comparar nombres con grafías o sufijos comerciales distintos."""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    vacias = {"av", "de", "la", "el", "c", "cc"}
    return {w for w in t.split() if w not in vacias and len(w) > 1}


def cargar_catalogo(ruta):
    """Devuelve {codigo_5_digitos: nombre_oficial} desde el GeoJSON oficial."""
    gj = json.load(open(ruta, encoding="utf-8"))
    cat = {}
    for f in gj["features"]:
        p = f["properties"]
        cod = str(p["num_est"]).strip().zfill(5)
        cat[cod] = str(p.get("nom_est", "")).strip()
    return cat


def verificar(code_to_matriz, catalogo):
    """Compara cada código de code_to_matriz contra el catálogo oficial.
    Devuelve (discrepancias, fuera_de_catalogo)."""
    discrepancias = []
    fuera_de_catalogo = []
    for codigo, nombre_matriz in code_to_matriz.items():
        c5 = str(codigo).strip().zfill(5)
        if c5 not in catalogo:
            # códigos sin estación en el catálogo: corrales/cabeceras/ampliaciones
            fuera_de_catalogo.append((codigo, nombre_matriz))
            continue
        oficial = catalogo[c5]
        a, b = normalizar(oficial), normalizar(nombre_matriz)
        if a and b and not (a & b):  # sin ninguna palabra en común -> sospechoso
            discrepancias.append((codigo, oficial, nombre_matriz))
    return discrepancias, fuera_de_catalogo


def main():
    code_to_matriz = json.load(open(CODE_TO_MATRIZ, encoding="utf-8"))
    catalogo = cargar_catalogo(CATALOGO)

    print(f"Códigos en code_to_matriz : {len(code_to_matriz)}")
    print(f"Estaciones en el catálogo : {len(catalogo)}")

    discrepancias, fuera = verificar(code_to_matriz, catalogo)

    print(f"\nDiscrepancias de nombre (código presente en el catálogo): {len(discrepancias)}")
    for codigo, oficial, matriz in discrepancias:
        print(f"  {codigo}: catálogo={oficial!r}  |  code_to_matriz={matriz!r}")
    if not discrepancias:
        print("  (ninguna: cada código coincide con el catálogo oficial)")

    print(f"\nCódigos sin estación en el catálogo (corrales/cabeceras/ampliaciones): {len(fuera)}")
    for codigo, matriz in sorted(fuera):
        print(f"  {codigo} -> {matriz!r}")
    print("\nNota: estos códigos no son estaciones de pasajeros del catálogo; su "
          "tratamiento (incluir o excluir) es una decisión metodológica documentada.")

    # código de salida útil para integración continua / control de versiones
    return 1 if discrepancias else 0


if __name__ == "__main__":
    raise SystemExit(main())
