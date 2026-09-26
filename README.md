# P34 · Observatorio SíseVe — Modelo GEMSES

Tablero público de reportes de violencia escolar (SíseVe – MINEDU, 2013–2026) por región, UGEL, distrito y colegio. Replica el artefacto `claude.ai/artifact/BecocUezQLSBGmE35sdXrs` y le agrega la sección **Colegio a colegio**:

- los 15 colegios de la zona con más reportes, por tipo de violencia (2024, 2025 o 2026 ene–ago); al tocar una barra se abre el colegio
- un mapa de calor con 25 colegios × años 2016–2026
- la radiografía del colegio elegido: su serie frente al promedio y al percentil 90 de colegios comparables (misma UGEL y nivel), su composición por tipo y su posición en la UGEL por tasa 2024

## Flujo

```
data/base.json      base por colegio (transparencia, corte 2026-08-31)
data/estado.json    estado de atención por UGEL + curva de cierre
scripts/auditar.py  13 controles -> data/auditoria.json (falla = no se publica)
scripts/build.py    template/index.html + data -> docs/index.html (GitHub Pages)
.github/workflows/semanal.yml   lunes 06:00 Lima
```

```bash
python scripts/auditar.py && python scripts/build.py
```

## Actualización semanal

Cada lunes a las 06:00 (hora de Lima), GitHub Actions ejecuta:

1. `scripts/siseve_portal.py`: descarga el Excel público del portal y lo agrega (estado por UGEL, curva de cierre y serie mensual).
2. `scripts/auditar.py`: corre 15 controles; si falla uno crítico, no se publica.
3. `scripts/build.py`: calcula la fracción del año con la serie mensual y arma `docs/index.html`.

El Excel del portal llega hasta UGEL. La base por colegio solo cambia con un nuevo corte por transparencia.

## Corrección del 26-09-2026

El tablero anterior suponía que a fines de agosto ya se registró el 70 % del año. En el calendario real del portal esa fracción fue 0.550 en 2024 y 0.536 en 2025. Con la fracción corregida (0.54), el cierre 2026 proyectado a nivel nacional pasa de 16,902 a 21,789 reportes (80 %: 20,387–23,455).

## Datos personales

Solo se publican conteos agregados por colegio y año. El Excel crudo del portal (data/raw/) está excluido por .gitignore y nunca se versiona.

© 2026 Mg. Carlos Pérez Pérez · CIIDEG SAC · Modelo GEMSES (WIPO PE324096539).
