# Validaciones troncales (no versionadas)

Los 24 archivos mensuales de validaciones de la tarjeta TuLlave **no se incluyen** en el
repositorio por tamaño (~13–14 MB c/u, ~330 MB en total). Descárgalos del portal de datos
abiertos de TransMilenio y colócalos en esta carpeta (`data/raw/`).

- **Fuente:** https://datosabiertos-transmilenio.hub.arcgis.com
- **Conjunto:** *Resumen de Validaciones Troncales* (intervalo de 15 minutos)
- **Periodo:** enero 2024 – diciembre 2025 (24 archivos)

Archivos esperados (nombres tal como los entrega el portal):

```
01 TM Resumen de Validaciones Troncales al 31 Ene 2024 Intervalo 15 Mint.xlsx
02 TM Resumen de Validaciones Troncales al 29 Feb 2024 Intervalo 15 Mint.xlsx
...
12 TM Resumen de Validaciones Troncales al 31 de Dic 2024 Intervalo 15 Mint.xlsx
01 TM Resumen de Validaciones Troncales al 31 de Enero 2025 Intervalo 15 Mint.xlsx
...
12 TM Resumen de Validaciones Troncales al 31 de Diciembre del 2025 Intervalo 15 Mint.xlsx
```

El cuaderno `00_preparacion_datos` consolida automáticamente **todos** los `.xlsx`
que encuentre en esta carpeta, así que basta con dejarlos aquí.
