# -*- coding: utf-8 -*-
"""
construir_matriz_ruta_estacion.py
=================================
Construye `data/soporte/matriz_ruta_estacion_troncal.csv` de forma reproducible
y auditable (columnas: ruta,tipo,corredor,orden,estacion,capacidad).

FUENTES
-------
1. PARADAS POR RUTA (el único insumo transcrito a mano, declarado abajo en
   `PARADAS`): "Guía General de viaje de TransMilenio a corte de diciembre 2025"
   (TransMilenio S.A.), que publica las estaciones donde para cada servicio
   troncal y dual, en el sentido impreso en la guía:
   https://www.transmilenio.gov.co/files/c263614f-6156-411a-95d7-2af0b734a938/a085d5c2-2128-44c6-965f-9cf66637ef3e/Guia-General-de-viaje-de-TransMilenio-a-corte-de-diciembre-2025.pdf

2. TIPO DE BUS POR RUTA -> CAPACIDAD NOMINAL (conjuntos `RUTAS_*` abajo): capa
   oficial "RUTAS TRONCALES" del GIS de TransMilenio, campo desc_tipo_bus_ruta_troncal
   (consultada 2026-06; biarticulado=250, articulado=160, padrón dual=80 pasajeros):
   https://gis.transmilenio.gov.co/arcgis/rest/services/Troncal/consulta_rutas_troncales/FeatureServer/0

3. CORREDOR DE CADA ESTACIÓN: se deriva del catálogo oficial
   `data/soporte/catalogo_estaciones_troncales.geojson` (campo id_trazado) y del
   nombre de troncal por trazado (`TRAZADO_A_TRONCAL`, tomado de la capa
   "Trazado troncal", campo nom_tronc):
   https://gis.transmilenio.gov.co/arcgis/rest/services/ConsultaSubgerenciaPlanificacionSITP/Consulta_Planificacion_SITP/FeatureServer/5

4. NOMBRES CANÓNICOS DE ESTACIÓN: `data/soporte/code_to_matriz.json`
   (código -> nombre canónico). La matriz usa EXACTAMENTE esos nombres, de modo
   que cruza 1:1 con las validaciones estandarizadas por código.

DECISIONES METODOLÓGICAS
------------------------
- Solo componente troncal: 8 rutas fáciles (paran en todas las estaciones de su
  recorrido), 82 expresos y 12 rutas duales. Total 102 rutas / 1.460 filas.
- De las rutas DUALES solo se incluyen sus paradas en estaciones troncales; los
  paraderos de calle de los corredores duales sin estación (AK 7, AK 68, AC 80
  occidental, extensión al aeropuerto) quedan excluidos.
- Variantes de refuerzo/parciales/ciclovía (G12Gs, B12Gs, F23B, J23B, L82R,
  L81 Ref, K86Acv y versiones "Cv") se fusionan con su servicio principal.
- M83/H83 se clasifican como Dual (par M de la Caracas Sur) pero operan con
  ARTICULADO según el GIS vigente -> capacidad 160 (no 80).
- `orden` es la secuencia de paradas en el sentido impreso en la Guía. Los pares
  direccionales (p. ej. B10/D10) son rutas distintas, cada una con su sentido.
- Dos nombres de estación existen en dos corredores distintos: "Ricaurte"
  (NQS Central y Américas) y "AV. Jiménez" (Caracas y Eje Ambiental). En esos
  casos la parada se declara con sufijo "@Corredor" para desambiguar; el resto
  de corredores se derivan automáticamente del catálogo.

USO
---
    python scripts/construir_matriz_ruta_estacion.py            # escribe el CSV
    python scripts/construir_matriz_ruta_estacion.py --check    # compara contra el existente
"""

import argparse
import csv
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SOPORTE = RAIZ / "data" / "soporte"
CATALOGO = SOPORTE / "catalogo_estaciones_troncales.geojson"
CODE_TO_MATRIZ = SOPORTE / "code_to_matriz.json"
SALIDA = SOPORTE / "matriz_ruta_estacion_troncal.csv"

# Nombre oficial de la troncal por id_trazado (capa "Trazado troncal", nom_tronc)
TRAZADO_A_TRONCAL = {
    "TZ001": "Caracas",
    "TZ002": "Autopista Norte",
    "TZ003": "Suba",
    "TZ004": "Suba",
    "TZ005": "Calle 80",
    "TZ006": "Calle 80",
    "TZ007": "NQS Central",
    "TZ008": "NQS Central",
    "TZ009": "Américas",
    "TZ010": "NQS Sur",
    "TZ011": "NQS Sur",
    "TZ012": "Caracas Sur",
    "TZ013": "Caracas Sur",
    "TZ014": "Caracas Sur",
    "TZ015": "Eje Ambiental",
    "TZ016": "Calle 26",
    "TZ017": "Calle 26",
    "TZ018": "Carrera 10",
    "TZ019": "Carrera 7",
    "TZ020": "Carrera 7",
}

# Clasificación de las rutas (Guía dic-2025 + tip_serv del GIS)
RUTAS_FACILES = {"1", "2", "3", "4", "5", "6", "7", "8"}
RUTAS_DUALES = {"C84", "D81", "H83", "K86", "L81", "L82",
                "M82", "M83", "M84", "M85", "M86", "P85"}

# Tipo de bus por ruta (GIS consulta_rutas_troncales, desc_tipo_bus_ruta_troncal)
RUTAS_BIARTICULADO = {  # 250 pasajeros (61 rutas)
    "1", "2",
    "A60", "A61", "B10", "B11", "B12", "B16", "B18", "B26", "B27", "B46",
    "C15", "C19", "C25", "C30", "C73", "D10", "D20", "D21", "D22", "D24",
    "E42", "E48", "F19", "F23", "F26", "F51", "F60", "F61",
    "G11", "G12", "G22", "G30", "G41", "G42", "G43", "G46", "G47", "G48",
    "H15", "H20", "H21", "H27", "H54", "H75", "H76",
    "J23", "J24", "J73", "J76", "K10", "K16", "K43", "K54",
    "L10", "L18", "L25", "L41", "M47", "M51",
}
RUTAS_ARTICULADO = {  # 160 pasajeros (31 rutas; incluye los duales M83/H83)
    "3", "4", "5", "6", "7", "8",
    "A52", "B13", "B23", "B28", "B50", "B55", "B72", "B74", "B75",
    "C17", "C50", "D55", "E32", "F28", "F32", "G45", "G52",
    "H13", "H17", "H72", "J70", "J74", "K23", "M83", "H83",
}
RUTAS_PADRON_DUAL = {  # 80 pasajeros (10 rutas)
    "C84", "D81", "K86", "L81", "L82", "M82", "M84", "M85", "M86", "P85",
}

# ---------------------------------------------------------------------------
# PARADAS POR RUTA (transcripción de la Guía General de viaje, dic-2025).
# Separador "|". Sufijo "@Corredor" solo donde el nombre existe en dos
# corredores (Ricaurte, AV. Jiménez). Orden = sentido impreso en la Guía.
# ---------------------------------------------------------------------------
PARADAS = {
    "1": "Universidades - CityU|Centro Memoria|Concejo de Bogotá|C. Universitaria - Lotería de Btá.|Corferias|Quinta Paredes|Gobernación|CAN - British Council|Salitre - El Greco|El Tiempo - CCB|AV. Rojas - UNISALESIANA|Normandía|Modelia|Portal Eldorado - C.C. NUESTRO BOGOTÁ",
    "2": "Museo Nacional - FNG|San Diego|Las Nieves|San Victorino|Bicentenario|San Bernardo|Policarpa|Ciudad Jardín - UAN|AV. 1° Mayo|Country Sur|Portal 20 de Julio",
    "3": "Portal Tunal|Parque|Biblioteca|Santa Lucía|Calle 40 Sur|Quiroga|Olaya|Restrepo|Fucha|Nariño|Hortúa|Hospital|Tercer Milenio|AV. Jiménez@Caracas|Calle 19|Temporal - Calle 22|Centro Memoria|Concejo de Bogotá|C. Universitaria - Lotería de Btá.|Corferias",
    "4": "Portal Sur - JFK Coop. financ.|Perdomo|Paseo Villa del Río - Madelena|Sevillana|Venecia|Alquería|Gral. Santander|NQS - Calle 38A S.|NQS - Calle 30 S.|SENA|Santa Isabel|Comuneros|Ricaurte@NQS Central|Paloquemao|CAD|AV. El Dorado|U. Nacional|Campín - UAN|Movistar Arena|7 de agosto|AV. Chile|NQS - Calle 75|Escuela Militar|Polo - FINCOMERCIO|Héroes",
    "5": "Portal Américas|Patio Bonito|Biblioteca Tintal|TV 86|Banderas|Mandalay|AV. Américas - AV. Boyacá|Marsella|Pradera - Plaza Central|Distrito Grafiti|Puente Aranda|KR 43 - COMAPAN|Zona Industrial|CDS - Cra. 32|Ricaurte@Américas|San Façon - KR 22|De la Sabana|AV. Jiménez@Caracas|Calle 19|Temporal - Calle 22",
    "6": "Universidades - CityU|Calle 26|Temporal - Calle 34|AV. 39|Calle 45 - American School Way|Temporal - Marly|Temporal - Calle 57|Calle 63|Temporal - Flores|Calle 72|Calle 76|Polo - FINCOMERCIO|Escuela Militar|KR 47|KR 53|AV. 68|Ferias|Boyacá|Minuto de Dios|Granja - KR 77|AV. Cali|KR 90|Quirigua|Portal 80",
    "7": "Polo - FINCOMERCIO|Escuela Militar|San Martín|Rionegro|Suba - Calle 95|Suba - Calle 100|Puentelargo|AV. Suba - Calle 116|Humedal Córdoba|Niza - Calle 127|Suba - AV. Boyacá|Gratamira|21 Ángeles|Suba - TV 91|La Campiña|Portal Suba",
    "8": "Terminal|Calle 187|Portal Norte|Toberín - Foundever|Calle 161|Mazurén|Calle 146|Calle 142|Alcalá - Col. S. Tomás Dominicos|Prado|Calle 127|Pepe Sierra|Calle 106|Calle 100 - Marketmedios|Virrey|Calle 85 - GATO DUMAS|Héroes|Calle 76|Calle 72|Temporal - Flores|Calle 63|Temporal - Calle 57|Temporal - Marly|Calle 45 - American School Way|AV. 39|Temporal - Calle 34|Calle 26|Temporal - Calle 22|Calle 19|AV. Jiménez@Caracas|Tercer Milenio|Tygua-San José|Guatoque-Veraguas",
    "A52": "Portal Sur - JFK Coop. financ.|Perdomo|Paseo Villa del Río - Madelena|Venecia|Alquería|Gral. Santander|NQS - Calle 30 S.|Santa Isabel|Calle 76|Temporal - Flores",
    "A60": "Portal Américas|TV 86|Banderas|Distrito Grafiti|KR 43 - COMAPAN|Ricaurte@Américas|De la Sabana|Calle 26|Temporal - Calle 34|Calle 45 - American School Way|Temporal - Marly|Calle 63|Calle 76",
    "A61": "Portal Américas|Patio Bonito|Biblioteca Tintal|Banderas|Marsella|Zona Industrial|Calle 19|Temporal - Calle 22|Temporal - Calle 34|AV. 39|Temporal - Calle 57|Temporal - Flores|Calle 72|Polo - FINCOMERCIO",
    "B10": "Portal 80|KR 90|AV. Cali|Granja - KR 77|Boyacá|AV. 68|KR 53|KR 47|Calle 85 - GATO DUMAS|Calle 100 - Marketmedios|Alcalá - Col. S. Tomás Dominicos|Calle 146|Mazurén|Toberín - Foundever|Portal Norte",
    "B11": "Portal Sur - JFK Coop. financ.|Paseo Villa del Río - Madelena|Alquería|NQS - Calle 30 S.|SENA|Santa Isabel|Ricaurte@NQS Central|Paloquemao|Campín - UAN|Escuela Militar|Héroes|Calle 85 - GATO DUMAS|Virrey|Calle 106|Calle 146|Toberín - Foundever|Calle 187|Terminal",
    "B12": "Portal Sur - JFK Coop. financ.|Perdomo|Gral. Santander|Comuneros|Ricaurte@NQS Central|AV. El Dorado|U. Nacional|7 de agosto|NQS - Calle 75|La Castellana|Calle 100 - Marketmedios|Calle 127|Prado|Calle 142|Toberín - Foundever|Portal Norte",
    "B13": "Portal Tunal|Biblioteca|Calle 40 Sur|Quiroga|Restrepo|Hortúa|Hospital|Tercer Milenio|Temporal - Calle 22|AV. 39|Calle 63|Temporal - Flores|Calle 72|Calle 76|Calle 85 - GATO DUMAS|Calle 106|Calle 127|Calle 142|Calle 146|Mazurén|Calle 161|Portal Norte",
    "B16": "Portal Eldorado - C.C. NUESTRO BOGOTÁ|Modelia|AV. Rojas - UNISALESIANA|El Tiempo - CCB|Salitre - El Greco|CAN - British Council|Quinta Paredes|Corferias|AV. El Dorado|AV. Chile|Pepe Sierra|Alcalá - Col. S. Tomás Dominicos|Mazurén|Toberín - Foundever|Calle 187|Terminal",
    "B18": "Portal 20 de Julio|Country Sur|AV. 1° Mayo|San Bernardo|Bicentenario|Tercer Milenio|AV. Jiménez@Caracas|Temporal - Calle 34|Calle 45 - American School Way|Calle 63|Calle 76|Virrey|Pepe Sierra|Calle 127|Alcalá - Col. S. Tomás Dominicos|Calle 187|Terminal",
    "B23": "Portal Eldorado - C.C. NUESTRO BOGOTÁ|AV. Rojas - UNISALESIANA|El Tiempo - CCB|Salitre - El Greco|CAN - British Council|Gobernación|C. Universitaria - Lotería de Btá.|Concejo de Bogotá|Calle 26|Temporal - Calle 34|Calle 45 - American School Way|Temporal - Marly|Temporal - Calle 57|Calle 85 - GATO DUMAS|Calle 127|Prado|Alcalá - Col. S. Tomás Dominicos",
    "B26": "Portal Américas|Patio Bonito|Biblioteca Tintal|TV 86|Banderas|Mandalay|AV. Américas - AV. Boyacá|Héroes|Calle 85 - GATO DUMAS|Virrey|Calle 100 - Marketmedios|Calle 127|Alcalá - Col. S. Tomás Dominicos",
    "B27": "Portal Tunal|Calle 40 Sur|AV. Jiménez@Caracas|Temporal - Calle 34|Calle 72|Héroes|Calle 85 - GATO DUMAS|Virrey|Calle 100 - Marketmedios|Toberín - Foundever|Portal Norte",
    "B28": "Portal Américas|Biblioteca Tintal|Banderas|Marsella|Zona Industrial|CDS - Cra. 32|La Castellana|Calle 106|Pepe Sierra|Prado|Calle 146|Calle 161|Portal Norte",
    "B46": "San Mateo|Terreros - Hospital C.V.|León XIII|La Despensa|Bosa|Calle 100 - Marketmedios|Alcalá - Col. S. Tomás Dominicos|Toberín - Foundever|Portal Norte",
    "B50": "Portal Suba|La Campiña|Suba - TV 91|21 Ángeles|AV. Suba - Calle 116|Puentelargo|Rionegro|Escuela Militar|Héroes|Calle 85 - GATO DUMAS|Virrey|Calle 142|Calle 161",
    "B55": "Portal 80|Quirigua|AV. Cali|Granja - KR 77|Minuto de Dios|Ferias|Polo - FINCOMERCIO|Héroes|Virrey|Calle 106|Pepe Sierra|Prado|Calle 142|Calle 161|Toberín - Foundever",
    "B72": "Portal Usme|Molinos|Socorro|Olaya|Fucha|Nariño|Hospital|Tygua-San José|Paloquemao|Movistar Arena|AV. Chile|La Castellana|Pepe Sierra|Alcalá - Col. S. Tomás Dominicos|Mazurén|Toberín - Foundever",
    "B74": "Universidades - CityU|Calle 19|Calle 26|AV. 39|Calle 45 - American School Way|Temporal - Calle 57|Héroes|Virrey|Prado|Calle 142|Calle 146|Mazurén|Toberín - Foundever|Portal Norte",
    "B75": "Portal Usme|Danubio|Molinos|Consuelo|Socorro|Santa Lucía|Fucha|Nariño|Hortúa|AV. Jiménez@Caracas|AV. 39|Temporal - Marly|Temporal - Calle 57|Calle 63|Calle 72|Calle 76|Héroes|Calle 100 - Marketmedios|Prado|Calle 142|Calle 146|Toberín - Foundever|Portal Norte",
    "C15": "Portal Tunal|Parque|Calle 40 Sur|Olaya|Nariño|Tercer Milenio|AV. Jiménez@Caracas|Calle 19|Temporal - Calle 22|Calle 45 - American School Way|Temporal - Marly|Temporal - Calle 57|Calle 76|Rionegro|AV. Suba - Calle 116|Humedal Córdoba|Niza - Calle 127|Gratamira|Suba - TV 91|La Campiña|Portal Suba",
    "C17": "Portal Usme|Danubio|Consuelo|Socorro|Santa Lucía|Quiroga|Restrepo|Hortúa|Guatoque-Veraguas|Paloquemao|AV. El Dorado|U. Nacional|7 de agosto|San Martín|Suba - Calle 95|Suba - Calle 100|Puentelargo|AV. Suba - Calle 116|Niza - Calle 127|Suba - TV 91|La Campiña|Portal Suba",
    "C19": "Banderas|Mandalay|Marsella|Distrito Grafiti|CDS - Cra. 32|Ricaurte@Américas|De la Sabana|Calle 19|Calle 26|Temporal - Calle 34|AV. 39|Calle 63|Temporal - Flores|Calle 72|Suba - Calle 95|Suba - Calle 100|Puentelargo|Suba - AV. Boyacá|21 Ángeles|Suba - TV 91|La Campiña|Portal Suba",
    "C25": "Portal 20 de Julio|Country Sur|AV. 1° Mayo|San Bernardo|Bicentenario|Tygua-San José|Guatoque-Veraguas|Ricaurte@NQS Central|Campín - UAN|Movistar Arena|AV. Chile|NQS - Calle 75|San Martín|Suba - Calle 95|Niza - Calle 127|Suba - AV. Boyacá|21 Ángeles|Suba - TV 91|La Campiña|Portal Suba",
    "C30": "Portal Sur - JFK Coop. financ.|Venecia|Gral. Santander|NQS - Calle 38A S.|Santa Isabel|CAD|U. Nacional|Movistar Arena|Rionegro|Puentelargo|AV. Suba - Calle 116|Suba - AV. Boyacá|Suba - TV 91|La Campiña|Portal Suba",
    "C50": "Calle 161|Calle 142|Virrey|Calle 85 - GATO DUMAS|Héroes|Escuela Militar|Rionegro|Puentelargo|AV. Suba - Calle 116|21 Ángeles|Suba - TV 91|La Campiña|Portal Suba",
    "C73": "Universidades - CityU|Centro Memoria|C. Universitaria - Lotería de Btá.|San Martín|Suba - Calle 100|Puentelargo|Niza - Calle 127|Suba - TV 91|La Campiña|Portal Suba",
    "D10": "Portal Norte|Toberín - Foundever|Mazurén|Calle 146|Alcalá - Col. S. Tomás Dominicos|Calle 100 - Marketmedios|Calle 85 - GATO DUMAS|KR 47|KR 53|AV. 68|Boyacá|Granja - KR 77|AV. Cali|KR 90|Portal 80",
    "D20": "Portal Usme|Molinos|Calle 40 Sur|Quiroga|Olaya|Restrepo|Calle 19|Temporal - Calle 22|Calle 26|Temporal - Calle 34|Calle 45 - American School Way|Calle 63|Temporal - Flores|Polo - FINCOMERCIO|AV. 68|Ferias|Boyacá|Granja - KR 77|Quirigua|Portal 80",
    "D21": "Portal Tunal|Santa Lucía|Calle 40 Sur|Quiroga|Fucha|Guatoque-Veraguas|Ricaurte@NQS Central|Campín - UAN|Movistar Arena|7 de agosto|AV. 68|Minuto de Dios|Granja - KR 77|AV. Cali|KR 90|Portal 80",
    "D22": "Portal Sur - JFK Coop. financ.|Sevillana|Gral. Santander|SENA|Santa Isabel|Paloquemao|AV. El Dorado|U. Nacional|AV. Chile|NQS - Calle 75|KR 47|AV. 68|Boyacá|Minuto de Dios|Granja - KR 77|Portal 80",
    "D24": "Universidades - CityU|AV. 39|Temporal - Marly|Temporal - Calle 57|Calle 72|Calle 76|Escuela Militar|KR 47|Minuto de Dios|Granja - KR 77|AV. Cali|KR 90|Portal 80",
    "D55": "Toberín - Foundever|Calle 161|Calle 142|Prado|Pepe Sierra|Calle 106|Virrey|Héroes|Polo - FINCOMERCIO|Ferias|Minuto de Dios|Granja - KR 77|AV. Cali|Quirigua|Portal 80",
    "E32": "Portal Américas|TV 86|Banderas|AV. Américas - AV. Boyacá|Puente Aranda|Zona Industrial|CAD|AV. El Dorado|U. Nacional|7 de agosto|AV. Chile|NQS - Calle 75",
    "E42": "San Mateo|Terreros - Hospital C.V.|León XIII|La Despensa|Bosa|Comuneros|Paloquemao|U. Nacional|Campín - UAN|7 de agosto",
    "E48": "San Mateo|Terreros - Hospital C.V.|León XIII|La Despensa|Bosa|Sevillana|Venecia|Gral. Santander|Santa Isabel|Ricaurte@NQS Central|CAD",
    "F19": "Portal Suba|La Campiña|Suba - TV 91|21 Ángeles|Suba - AV. Boyacá|Puentelargo|Suba - Calle 100|Suba - Calle 95|Calle 72|Temporal - Flores|Calle 63|AV. 39|Temporal - Calle 34|Calle 26|Calle 19|De la Sabana|Ricaurte@Américas|CDS - Cra. 32|Distrito Grafiti|Marsella|Mandalay|Banderas",
    "F23": "Las Aguas - C. Col Americano|Museo del Oro|AV. Jiménez@Eje Ambiental|San Façon - KR 22|Ricaurte@Américas|Puente Aranda|Pradera - Plaza Central|AV. Américas - AV. Boyacá|Banderas|Biblioteca Tintal|Patio Bonito|Portal Américas",
    "F26": "Alcalá - Col. S. Tomás Dominicos|Calle 127|Calle 100 - Marketmedios|Virrey|Calle 85 - GATO DUMAS|Héroes|AV. Américas - AV. Boyacá|Mandalay|Banderas|TV 86|Biblioteca Tintal|Patio Bonito|Portal Américas",
    "F28": "Portal Norte|Calle 161|Calle 146|Prado|Pepe Sierra|Calle 106|La Castellana|CDS - Cra. 32|Zona Industrial|Marsella|Banderas|Biblioteca Tintal|Portal Américas",
    "F32": "NQS - Calle 75|AV. Chile|7 de agosto|U. Nacional|AV. El Dorado|CAD|Zona Industrial|Puente Aranda|AV. Américas - AV. Boyacá|Banderas|TV 86|Portal Américas",
    "F51": "Museo Nacional - FNG|San Diego|Las Nieves|Ricaurte@Américas|Distrito Grafiti|Pradera - Plaza Central|Marsella|AV. Américas - AV. Boyacá|Mandalay|Banderas|Biblioteca Tintal|Patio Bonito|Portal Américas",
    "F60": "Calle 76|Calle 63|Temporal - Marly|Calle 45 - American School Way|Temporal - Calle 34|Calle 26|De la Sabana|Ricaurte@Américas|KR 43 - COMAPAN|Distrito Grafiti|Banderas|TV 86|Portal Américas",
    "F61": "Polo - FINCOMERCIO|Calle 72|Temporal - Flores|Temporal - Calle 57|AV. 39|Temporal - Calle 34|Temporal - Calle 22|Calle 19|Zona Industrial|Marsella|Banderas|Biblioteca Tintal|Patio Bonito|Portal Américas",
    "G11": "Terminal|Calle 187|Toberín - Foundever|Calle 146|Calle 106|Virrey|Calle 85 - GATO DUMAS|Héroes|Escuela Militar|Campín - UAN|Paloquemao|Ricaurte@NQS Central|Santa Isabel|SENA|NQS - Calle 30 S.|Alquería|Paseo Villa del Río - Madelena|Portal Sur - JFK Coop. financ.",
    "G12": "Portal Norte|Toberín - Foundever|Calle 142|Prado|Calle 127|Calle 100 - Marketmedios|La Castellana|NQS - Calle 75|7 de agosto|U. Nacional|AV. El Dorado|Ricaurte@NQS Central|Comuneros|Gral. Santander|Perdomo|Portal Sur - JFK Coop. financ.",
    "G22": "Portal 80|Granja - KR 77|Minuto de Dios|Boyacá|AV. 68|KR 47|NQS - Calle 75|AV. Chile|U. Nacional|AV. El Dorado|Paloquemao|Santa Isabel|SENA|Gral. Santander|Sevillana|Portal Sur - JFK Coop. financ.",
    "G30": "Portal Suba|La Campiña|Suba - TV 91|Suba - AV. Boyacá|AV. Suba - Calle 116|Puentelargo|Rionegro|Movistar Arena|U. Nacional|CAD|Santa Isabel|NQS - Calle 38A S.|Gral. Santander|Venecia|Portal Sur - JFK Coop. financ.",
    "G41": "Bicentenario|Tygua-San José|Guatoque-Veraguas|NQS - Calle 30 S.|Alquería|Bosa|Terreros - Hospital C.V.|San Mateo",
    "G42": "7 de agosto|Campín - UAN|U. Nacional|Paloquemao|Comuneros|Bosa|La Despensa|León XIII|Terreros - Hospital C.V.|San Mateo",
    "G43": "Portal Eldorado - C.C. NUESTRO BOGOTÁ|Modelia|Normandía|El Tiempo - CCB|Salitre - El Greco|Gobernación|Quinta Paredes|Corferias|CAD|Ricaurte@NQS Central|SENA|Gral. Santander|Venecia|La Despensa|León XIII|Terreros - Hospital C.V.|San Mateo",
    "G45": "San Mateo|Terreros - Hospital C.V.|León XIII|La Despensa|Bosa|Portal Sur - JFK Coop. financ.",
    "G46": "Portal Norte|Toberín - Foundever|Alcalá - Col. S. Tomás Dominicos|Calle 100 - Marketmedios|Bosa|La Despensa|León XIII|Terreros - Hospital C.V.|San Mateo",
    "G47": "Museo Nacional - FNG|San Diego|Las Nieves|San Victorino|Tygua-San José|Guatoque-Veraguas|Comuneros|NQS - Calle 38A S.|Sevillana|Paseo Villa del Río - Madelena|Perdomo|Portal Sur - JFK Coop. financ.",
    "G48": "CAD|Ricaurte@NQS Central|Santa Isabel|Gral. Santander|Venecia|Sevillana|Bosa|La Despensa|León XIII|Terreros - Hospital C.V.|San Mateo",
    "G52": "Temporal - Flores|Calle 76|Santa Isabel|NQS - Calle 30 S.|Gral. Santander|Alquería|Venecia|Paseo Villa del Río - Madelena|Perdomo|Portal Sur - JFK Coop. financ.",
    "H13": "Portal Norte|Calle 161|Mazurén|Calle 146|Calle 142|Calle 127|Calle 106|Calle 85 - GATO DUMAS|Calle 76|Calle 72|Temporal - Flores|Calle 63|AV. 39|Temporal - Calle 22|Tercer Milenio|Hospital|Hortúa|Restrepo|Quiroga|Calle 40 Sur|Biblioteca|Portal Tunal",
    "H15": "Portal Suba|La Campiña|Suba - TV 91|Gratamira|Niza - Calle 127|Humedal Córdoba|AV. Suba - Calle 116|Rionegro|Calle 76|Temporal - Calle 57|Temporal - Marly|Calle 45 - American School Way|Temporal - Calle 22|Calle 19|AV. Jiménez@Caracas|Tercer Milenio|Nariño|Olaya|Calle 40 Sur|Parque|Portal Tunal",
    "H17": "Portal Suba|La Campiña|Suba - TV 91|Niza - Calle 127|AV. Suba - Calle 116|Puentelargo|Suba - Calle 100|Suba - Calle 95|San Martín|7 de agosto|U. Nacional|AV. El Dorado|Paloquemao|Guatoque-Veraguas|Hortúa|Restrepo|Quiroga|Santa Lucía|Socorro|Consuelo|Danubio|Portal Usme",
    "H20": "Portal 80|Quirigua|Granja - KR 77|Boyacá|Ferias|AV. 68|Polo - FINCOMERCIO|Temporal - Flores|Calle 63|Calle 45 - American School Way|Temporal - Calle 34|Calle 26|Temporal - Calle 22|Calle 19|AV. Jiménez@Caracas|Restrepo|Olaya|Quiroga|Calle 40 Sur|Molinos|Portal Usme",
    "H21": "Portal 80|KR 90|AV. Cali|Granja - KR 77|Minuto de Dios|AV. 68|7 de agosto|Movistar Arena|Campín - UAN|Ricaurte@NQS Central|Guatoque-Veraguas|Fucha|Quiroga|Calle 40 Sur|Santa Lucía|Portal Tunal",
    "H27": "Portal Norte|Toberín - Foundever|Calle 100 - Marketmedios|Virrey|Calle 85 - GATO DUMAS|Héroes|Calle 72|Temporal - Calle 34|AV. Jiménez@Caracas|Calle 40 Sur|Portal Tunal",
    "H54": "Portal Eldorado - C.C. NUESTRO BOGOTÁ|Modelia|AV. Rojas - UNISALESIANA|El Tiempo - CCB|Salitre - El Greco|CAN - British Council|Quinta Paredes|Corferias|C. Universitaria - Lotería de Btá.|Concejo de Bogotá|AV. Jiménez@Caracas|Hortúa|Restrepo|Calle 40 Sur|Molinos|Danubio|Portal Usme",
    "H72": "Toberín - Foundever|Mazurén|Alcalá - Col. S. Tomás Dominicos|Pepe Sierra|La Castellana|AV. Chile|Movistar Arena|Paloquemao|Tygua-San José|Hospital|Nariño|Fucha|Olaya|Socorro|Molinos|Portal Usme",
    "H75": "Portal Norte|Toberín - Foundever|Calle 146|Calle 142|Prado|Calle 100 - Marketmedios|Héroes|Calle 76|Calle 72|Calle 63|Temporal - Calle 57|Temporal - Marly|AV. 39|AV. Jiménez@Caracas|Hortúa|Nariño|Fucha|Santa Lucía|Socorro|Consuelo|Molinos|Danubio|Portal Usme",
    "H76": "Universidades - CityU|Calle 19|AV. Jiménez@Caracas|Tercer Milenio|Restrepo|Calle 40 Sur|Santa Lucía|Socorro|Consuelo|Molinos|Danubio|Portal Usme",
    "J23": "Portal Américas|Patio Bonito|Biblioteca Tintal|Banderas|AV. Américas - AV. Boyacá|Pradera - Plaza Central|Puente Aranda|Ricaurte@Américas|San Façon - KR 22|AV. Jiménez@Eje Ambiental|Museo del Oro|Las Aguas - C. Col Americano",
    "J24": "Portal 80|KR 90|AV. Cali|Granja - KR 77|Minuto de Dios|KR 47|Escuela Militar|Calle 76|Calle 72|Temporal - Calle 57|Temporal - Marly|AV. 39|Universidades - CityU",
    "J70": "Portal Norte|Toberín - Foundever|Mazurén|Calle 146|Calle 142|Alcalá - Col. S. Tomás Dominicos|Prado|Calle 127|CAD|AV. Jiménez@Eje Ambiental|Museo del Oro|Las Aguas - C. Col Americano",
    "J73": "Portal Suba|La Campiña|Suba - TV 91|Niza - Calle 127|Puentelargo|Suba - Calle 100|San Martín|C. Universitaria - Lotería de Btá.|Centro Memoria|Universidades - CityU",
    "J74": "Portal Norte|Toberín - Foundever|Mazurén|Calle 146|Calle 142|Prado|Virrey|Héroes|Temporal - Calle 57|Calle 45 - American School Way|AV. 39|Calle 26|Calle 19|Universidades - CityU",
    "J76": "Portal Usme|Danubio|Consuelo|Socorro|Santa Lucía|Calle 40 Sur|Restrepo|Tercer Milenio|AV. Jiménez@Caracas|Calle 19|Universidades - CityU",
    "K10": "Portal 20 de Julio|AV. 1° Mayo|Ciudad Jardín - UAN|San Bernardo|Bicentenario|San Victorino|Las Nieves|Centro Memoria|C. Universitaria - Lotería de Btá.|Gobernación|CAN - British Council|Salitre - El Greco|Normandía|Modelia|Portal Eldorado - C.C. NUESTRO BOGOTÁ",
    "K16": "Terminal|Calle 187|Toberín - Foundever|Mazurén|Alcalá - Col. S. Tomás Dominicos|Pepe Sierra|AV. Chile|AV. El Dorado|Corferias|Quinta Paredes|CAN - British Council|Salitre - El Greco|El Tiempo - CCB|AV. Rojas - UNISALESIANA|Modelia|Portal Eldorado - C.C. NUESTRO BOGOTÁ",
    "K23": "Alcalá - Col. S. Tomás Dominicos|Prado|Calle 127|Calle 85 - GATO DUMAS|Temporal - Calle 57|Temporal - Marly|Calle 45 - American School Way|Temporal - Calle 34|Calle 26|Concejo de Bogotá|C. Universitaria - Lotería de Btá.|Gobernación|CAN - British Council|Salitre - El Greco|El Tiempo - CCB|AV. Rojas - UNISALESIANA|Portal Eldorado - C.C. NUESTRO BOGOTÁ",
    "K43": "San Mateo|Terreros - Hospital C.V.|León XIII|La Despensa|Venecia|Gral. Santander|SENA|Ricaurte@NQS Central|CAD|Corferias|Quinta Paredes|Gobernación|Salitre - El Greco|El Tiempo - CCB|Normandía|Modelia|Portal Eldorado - C.C. NUESTRO BOGOTÁ",
    "K54": "Portal Usme|Danubio|Molinos|Calle 40 Sur|Restrepo|Hortúa|AV. Jiménez@Caracas|Concejo de Bogotá|C. Universitaria - Lotería de Btá.|Corferias|Quinta Paredes|CAN - British Council|Salitre - El Greco|El Tiempo - CCB|AV. Rojas - UNISALESIANA|Modelia|Portal Eldorado - C.C. NUESTRO BOGOTÁ",
    "L10": "Portal Eldorado - C.C. NUESTRO BOGOTÁ|Modelia|Normandía|Salitre - El Greco|CAN - British Council|Gobernación|C. Universitaria - Lotería de Btá.|Centro Memoria|Las Nieves|San Victorino|Bicentenario|San Bernardo|Ciudad Jardín - UAN|AV. 1° Mayo|Portal 20 de Julio",
    "L18": "Terminal|Calle 187|Alcalá - Col. S. Tomás Dominicos|Calle 127|Pepe Sierra|Virrey|Calle 76|Calle 63|Calle 45 - American School Way|Temporal - Calle 34|AV. Jiménez@Caracas|Tercer Milenio|Bicentenario|San Bernardo|AV. 1° Mayo|Country Sur|Portal 20 de Julio",
    "L25": "Portal Suba|La Campiña|Suba - TV 91|21 Ángeles|Suba - AV. Boyacá|Niza - Calle 127|Suba - Calle 95|San Martín|NQS - Calle 75|AV. Chile|Movistar Arena|Campín - UAN|Ricaurte@NQS Central|Guatoque-Veraguas|Tygua-San José|Bicentenario|San Bernardo|AV. 1° Mayo|Country Sur|Portal 20 de Julio",
    "L41": "San Mateo|Terreros - Hospital C.V.|Bosa|Alquería|NQS - Calle 30 S.|Guatoque-Veraguas|Tygua-San José|Bicentenario",
    "M47": "Portal Sur - JFK Coop. financ.|Perdomo|Paseo Villa del Río - Madelena|Sevillana|NQS - Calle 38A S.|Comuneros|Guatoque-Veraguas|Tygua-San José|San Victorino|Las Nieves|San Diego|Museo Nacional - FNG",
    "M51": "Portal Américas|Patio Bonito|Biblioteca Tintal|Banderas|Mandalay|AV. Américas - AV. Boyacá|Marsella|Pradera - Plaza Central|Distrito Grafiti|Ricaurte@Américas|Las Nieves|San Diego|Museo Nacional - FNG",
    "C84": "Polo - FINCOMERCIO|Puentelargo|21 Ángeles",
    "D81": "Portal 20 de Julio|Country Sur|AV. 1° Mayo|Bicentenario|San Victorino|Museo Nacional - FNG|Polo - FINCOMERCIO|KR 47|AV. 68",
    "H83": "Museo Nacional - FNG|San Diego|San Victorino|Bicentenario|Policarpa|AV. 1° Mayo|Quiroga|Consuelo|Danubio|Portal Usme",
    "K86": "Museo Nacional - FNG|Concejo de Bogotá|Corferias|Gobernación|CAN - British Council|El Tiempo - CCB|AV. Rojas - UNISALESIANA|Portal Eldorado - C.C. NUESTRO BOGOTÁ",
    "L81": "AV. 68|KR 47|Polo - FINCOMERCIO|Museo Nacional - FNG|San Victorino|Bicentenario|AV. 1° Mayo|Country Sur|Portal 20 de Julio",
    "L82": "San Diego|Bicentenario|AV. 1° Mayo|Country Sur|Portal 20 de Julio",
    "M82": "Portal 20 de Julio|Country Sur|AV. 1° Mayo|Bicentenario|San Diego",
    "M83": "Portal Usme|Danubio|Consuelo|Quiroga|AV. 1° Mayo|Policarpa|Bicentenario|San Victorino|San Diego|Museo Nacional - FNG",
    "M84": "21 Ángeles|Puentelargo|Polo - FINCOMERCIO",
    "M85": "Salitre - El Greco|CAN - British Council|Quinta Paredes|Centro Memoria|Museo Nacional - FNG",
    "M86": "Portal Eldorado - C.C. NUESTRO BOGOTÁ|AV. Rojas - UNISALESIANA|El Tiempo - CCB|CAN - British Council|Gobernación|Corferias|Concejo de Bogotá|San Diego|Museo Nacional - FNG",
    "P85": "Museo Nacional - FNG|Centro Memoria|Quinta Paredes|CAN - British Council|Salitre - El Greco",
}


def z5(c):
    return str(c).strip().zfill(5)


def cargar_corredores():
    """{nombre_canónico: corredor} desde catálogo + code_to_matriz.
    Devuelve también el set de nombres con más de un corredor (ambiguos)."""
    gj = json.load(open(CATALOGO, encoding="utf-8"))
    code_a_trazado = {z5(f["properties"]["num_est"]): str(f["properties"].get("id_trazado", "")).strip()
                      for f in gj["features"]}
    code_to_matriz = json.load(open(CODE_TO_MATRIZ, encoding="utf-8"))

    nombre_a_corredores = {}
    for code, nombre in code_to_matriz.items():
        tz = code_a_trazado.get(z5(code))
        if not tz:
            continue  # códigos operacionales (corrales, etc.) sin estación de catálogo
        corredor = TRAZADO_A_TRONCAL.get(tz)
        if corredor is None:
            raise SystemExit(f"id_trazado sin troncal asignada: {tz} (código {code})")
        nombre_a_corredores.setdefault(nombre, set()).add(corredor)

    ambiguos = {n for n, cs in nombre_a_corredores.items() if len(cs) > 1}
    unicos = {n: next(iter(cs)) for n, cs in nombre_a_corredores.items() if len(cs) == 1}
    nombres_canon = set(code_to_matriz.values())
    return unicos, ambiguos, nombres_canon


def construir():
    unicos, ambiguos, nombres_canon = cargar_corredores()

    filas = []
    for ruta, cadena in PARADAS.items():
        if ruta in RUTAS_BIARTICULADO:
            capacidad = 250
        elif ruta in RUTAS_ARTICULADO:
            capacidad = 160
        elif ruta in RUTAS_PADRON_DUAL:
            capacidad = 80
        else:
            raise SystemExit(f"Ruta sin tipo de bus declarado: {ruta}")

        if ruta in RUTAS_FACILES:
            tipo = "Fácil"
        elif ruta in RUTAS_DUALES:
            tipo = "Dual"
        else:
            tipo = "Expreso"

        for orden, parada in enumerate(cadena.split("|"), start=1):
            if "@" in parada:
                estacion, corredor = parada.split("@", 1)
            else:
                estacion = parada
                if estacion in ambiguos:
                    raise SystemExit(f"{ruta}: '{estacion}' existe en varios corredores; "
                                     f"declárala con sufijo @Corredor en PARADAS")
                corredor = unicos.get(estacion)
                if corredor is None:
                    raise SystemExit(f"{ruta}: estación sin corredor derivable: '{estacion}'")
            if estacion not in nombres_canon:
                raise SystemExit(f"{ruta}: '{estacion}' no es un nombre canónico de code_to_matriz.json")
            filas.append((ruta, tipo, corredor, orden, estacion, capacidad))

    # Verificaciones globales
    rutas = {f[0] for f in filas}
    assert len(rutas) == 102, f"Se esperaban 102 rutas, hay {len(rutas)}"
    assert len(filas) == 1460, f"Se esperaban 1460 filas, hay {len(filas)}"
    por_cap = {}
    for f in filas:
        por_cap.setdefault(f[5], set()).add(f[0])
    print(f"Rutas: {len(rutas)} (Fácil {len(RUTAS_FACILES)}, "
          f"Dual {len(RUTAS_DUALES)}, Expreso {len(rutas) - len(RUTAS_FACILES) - len(RUTAS_DUALES)})")
    print("Rutas por capacidad: " + ", ".join(f"{c} -> {len(r)}" for c, r in sorted(por_cap.items())))
    print(f"Filas: {len(filas)}")
    return filas


def escribir(filas, ruta_salida):
    with open(ruta_salida, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["ruta", "tipo", "corredor", "orden", "estacion", "capacidad"])
        w.writerows(filas)
    print(f"Escrito: {ruta_salida}")


def comparar(filas, ruta_existente):
    with open(ruta_existente, encoding="utf-8") as fh:
        existentes = [tuple(r) for r in csv.reader(fh)][1:]
    generadas = [(r, t, c, str(o), e, str(cap)) for r, t, c, o, e, cap in filas]
    if existentes == generadas:
        print("OK: el CSV existente coincide exactamente con el generado.")
        return 0
    se, sg = set(existentes), set(generadas)
    for fila in sorted(sg - se)[:20]:
        print(f"  solo en el generado : {fila}")
    for fila in sorted(se - sg)[:20]:
        print(f"  solo en el existente: {fila}")
    print(f"Diferencias: {len(sg - se)} generadas / {len(se - sg)} existentes")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="comparar contra el CSV existente en vez de escribirlo")
    args = ap.parse_args()
    filas = construir()
    if args.check:
        return comparar(filas, SALIDA)
    escribir(filas, SALIDA)
    return 0


if __name__ == "__main__":
    sys.exit(main())
