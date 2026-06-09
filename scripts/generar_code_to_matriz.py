"""
generar_code_to_matriz.py
=========================
Construye `code_to_matriz.json` de forma reproducible y auditable.

QUÉ PRODUCE
-----------
Un diccionario {código_de_estación -> nombre_de_estación_en_la_matriz}. El código
numérico (p. ej. "02000") es el identificador estable de cada estación en las
validaciones de TuLlave; el nombre textual, en cambio, varía entre archivos
mensuales, por lo que NO se usa como llave.

CÓMO LO CONSTRUYE (y por qué así)
---------------------------------
1. Ancla cada estación a su código en el CATÁLOGO OFICIAL de TransMilenio
   (`catalogo_estaciones_troncales.geojson`, campos num_est y nom_est). El catálogo
   es la fuente autoritativa código -> estación y es internamente consistente
   (sus coordenadas ordenan las estaciones a lo largo de cada corredor). Anclar por
   código —y no por coincidencia de nombres— evita los errores de atribución de
   demanda entre estaciones con nombres parecidos (p. ej. "Calle 187" vs "Calle 106").

2. Reconcilia el nombre oficial con el nombre operativo de la matriz ruta-estación
   mediante una tabla de correspondencia documentada
   (`correspondencia_oficial_matriz.json`, nombre_oficial -> nombre_matriz). Solo se
   listan los casos en que ambos nombres difieren; cuando coinciden, se usa el oficial.
   Esta tabla se curó a partir de la Guía para transbordos del componente troncal y
   de la propia matriz; es pequeña, legible y verificable.

3. Agrega los CÓDIGOS OPERACIONALES que aparecen en las validaciones pero no son
   estaciones de pasajeros del catálogo (patios/corrales, cabeceras y ampliaciones).
   Se declaran explícitamente abajo, con su justificación. Los corrales (50xxx) son
   patios de buses: si el estudio decide excluirlos como no-pasajeros, basta con
   quitarlos de este diccionario y volver a generar.

El resultado se valida después con `verificar_mapeo.py`, que vuelve a cruzar el
mapeo contra el catálogo oficial por código.

USO
---
    python generar_code_to_matriz.py            # escribe code_to_matriz.json
    python generar_code_to_matriz.py --check    # compara contra el code_to_matriz.json existente
"""

import argparse
import json
from pathlib import Path

# Rutas relativas a la raíz del repo (el script vive en scripts/; los datos en data/soporte/)
RAIZ = Path(__file__).resolve().parent.parent
SOPORTE = RAIZ / "data" / "soporte"
CATALOGO = SOPORTE / "catalogo_estaciones_troncales.geojson"
CORRESPONDENCIA = SOPORTE / "correspondencia_oficial_matriz.json"
SALIDA = SOPORTE / "code_to_matriz.json"

# Códigos presentes en las validaciones que NO son estaciones de pasajeros del
# catálogo. Se mapean a la estación operativamente asociada. Decisión metodológica:
# los corrales (prefijo 50) son patios de buses; pueden excluirse quitándolos de aquí.
CODIGOS_OPERACIONALES = {
    "04004": "Granja - KR 77",   # acceso/variante de La Granja
    "08100": "Portal Tunal",     # TransMiCable / acceso Tunal
    "50003": "Molinos",          # corral (patio de buses)
    "50004": "AV. Cali",         # corral (patio de buses)
    "57503": "San Mateo",        # ampliación San Mateo (Soacha)
}
# Nota: el corral 50008 (Portal Eldorado) NO hace parte del mapeo vigente
# (code_to_matriz.json tiene 155 códigos). Incluirlo sumaría validaciones de
# patio a esa estación y obligaría a re-correr todo el pipeline; si se decide
# incluirlo, agregarlo aquí y regenerar.


def cargar_catalogo(ruta):
    """{codigo_5_digitos: nombre_oficial} desde el GeoJSON oficial."""
    gj = json.load(open(ruta, encoding="utf-8"))
    return {
        str(f["properties"]["num_est"]).strip().zfill(5): str(f["properties"].get("nom_est", "")).strip()
        for f in gj["features"]
    }


def construir(catalogo, correspondencia):
    """Aplica: código -> nombre oficial (catálogo) -> nombre matriz (correspondencia)."""
    code_to_matriz = {}
    for codigo, oficial in catalogo.items():
        # si el oficial difiere del nombre de la matriz, se traduce; si no, se conserva
        code_to_matriz[codigo] = correspondencia.get(oficial, oficial)
    # códigos operacionales (no están en el catálogo de estaciones)
    code_to_matriz.update(CODIGOS_OPERACIONALES)
    return dict(sorted(code_to_matriz.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="comparar contra el code_to_matriz.json existente en vez de escribirlo")
    args = ap.parse_args()

    catalogo = cargar_catalogo(CATALOGO)
    correspondencia = json.load(open(CORRESPONDENCIA, encoding="utf-8"))
    code_to_matriz = construir(catalogo, correspondencia)

    print(f"Estaciones del catálogo : {len(catalogo)}")
    print(f"Códigos operacionales   : {len(CODIGOS_OPERACIONALES)}")
    print(f"Total en code_to_matriz : {len(code_to_matriz)}")

    if args.check:
        existente = json.load(open(SALIDA, encoding="utf-8"))
        comunes = set(existente) & set(code_to_matriz)
        difs = {c: (existente[c], code_to_matriz[c]) for c in comunes if existente[c] != code_to_matriz[c]}
        solo_gen = set(code_to_matriz) - set(existente)
        solo_exi = set(existente) - set(code_to_matriz)
        print(f"\nDiferencias en códigos comunes: {len(difs)}")
        for c, (a, b) in sorted(difs.items()):
            print(f"  {c}: existente={a!r} | generado={b!r}")
        if solo_gen:
            print(f"Solo en el generado (estaciones del catálogo sin validaciones en el periodo): {sorted(solo_gen)}")
        if solo_exi:
            print(f"Solo en el existente: {sorted(solo_exi)}")
        return 0 if not difs else 1

    json.dump(code_to_matriz, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nEscrito: {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
