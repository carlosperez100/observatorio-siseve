"""
Auditoría automática de los datos del observatorio SíseVe.

Corre antes de cada publicación. Escribe data/auditoria.json y sale con código 1
si falla un control crítico (en ese caso el flujo semanal no publica).

    python scripts/auditar.py
"""
import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PROHIBIDOS = re.compile(r"\b(dni|edad|sexo|grado|turno|nombre_estudiante|agresor_nombre|direccion|telefono|correo)\b", re.I)


def main():
    base = json.loads((DATA / "base.json").read_text(encoding="utf-8"))
    est = json.loads((DATA / "estado.json").read_text(encoding="utf-8"))
    years = [int(y) for y in base["years"]]
    tyy = [int(y) for y in base["typeYears"]]
    types = base["types"]
    S = base["s"]
    # La serie por año viene recortada: los ceros finales se omiten (el tablero los asume)
    for r in S:
        if len(r) > 10 and len(r[10]) < len(years):
            r[10] = r[10] + [0] * (len(years) - len(r[10]))
    D = base["dict"]
    C = []

    def ctrl(nombre, ok, detalle, critico=True):
        C.append({"control": nombre, "ok": bool(ok), "critico": critico, "detalle": detalle})

    # 1. Estructura de cada fila de colegio
    malas = [r for r in S if len(r) != 12 or len(r[10]) != len(years)
             or (r[11] and len(r[11]) != len(tyy) * len(types))]
    ctrl("Estructura de filas", not malas, f"{len(S):,} colegios; {len(malas)} filas con longitud inesperada")

    # 2. Índices de diccionario válidos
    campos = [(2, "r"), (3, "p"), (4, "d"), (5, "u"), (7, "n")]
    fuera = sum(1 for r in S for i, k in campos if not 0 <= r[i] < len(D[k]))
    ctrl("Índices territoriales válidos", fuera == 0, f"{fuera} referencias fuera de rango en región/provincia/distrito/UGEL/nivel")

    # 3. Código modular
    malos = [r[1] for r in S if not re.fullmatch(r"\d{7}", str(r[1]))]
    dup = len(S) - len({(r[1], r[7]) for r in S})
    ctrl("Código modular de 7 dígitos y sin duplicados", not malos and dup == 0,
         f"{len(malos)} códigos mal formados; {dup} duplicados código+nivel")

    # 4. Total de reportes = suma por colegio
    suma = sum(sum(r[10]) for r in S)
    ctrl("Total de reportes cuadra con la suma por colegio", suma == base["meta"]["reportes"],
         f"suma por colegio {suma:,} frente a meta {base['meta']['reportes']:,}")

    # 5. Física + psicológica + sexual = total, cada año con tipos
    desc = 0
    for r in S:
        if not r[11]:
            continue
        for j, y in enumerate(tyy):
            t = r[10][years.index(y)]
            v = r[11][j * len(types):(j + 1) * len(types)]
            if v[0] + v[1] + v[2] != t:
                desc += 1
    ctrl("Tipos suman el total (2022–2026)", desc == 0, f"{desc} colegio-año con descuadre")

    # 6. Sin negativos
    neg = sum(1 for r in S for v in r[10] + (r[11] or []) if v < 0)
    ctrl("Sin valores negativos", neg == 0, f"{neg} valores negativos")

    # 7. Estado por UGEL consistente
    U = est["U"]
    m1 = [u[0] for u in U if u[2] + u[3] + u[4] != u[1]]
    m2 = [u[0] for u in U if u[5] + u[6] + u[7] != u[1]]
    ctrl("Estado por UGEL: años y estados suman el total", not m1 and not m2,
         f"{len(U)} UGEL; {len(m1)} con descuadre por año, {len(m2)} por estado")

    # 8. Curva de cierre = mismo universo que el estado
    tU, tM = sum(u[1] for u in U), sum(m[1] for m in est["MAT"])
    ctrl("Curva de cierre y estado usan el mismo universo", tU == tM, f"estado {tU:,} frente a curva {tM:,}")

    # 9. Coherencia entre fuentes: 2026 por colegio frente a Excel del portal
    i26 = years.index(2026)
    col26, por26 = sum(r[10][i26] for r in S), sum(u[4] for u in U)
    dif = abs(col26 - por26) / max(por26, 1) * 100
    ctrl("2026: base por colegio frente a Excel del portal", dif <= 2,
         f"{col26:,} frente a {por26:,} ({dif:.1f} %); las fechas de extracción difieren", critico=False)

    # 10. Privacidad: ningún campo ni texto personal en lo que se publica
    txt = json.dumps({k: v for k, v in base.items() if k != "s"}, ensure_ascii=False) + json.dumps(est, ensure_ascii=False)
    hall = sorted(set(m.group(0).lower() for m in PROHIBIDOS.finditer(txt)))
    ctrl("Sin campos de datos personales", not hall, "ninguno" if not hall else "aparecen: " + ", ".join(hall))
    ctrl("Solo datos agregados por colegio y año", all(isinstance(v, int) for r in S for v in r[10]),
         "cada valor es un conteo; no hay filas por caso")

    # 10b. Serie mensual del portal frente a base por colegio (años completos)
    mp = DATA / "mensual.json"
    if mp.exists():
        mn = json.loads(mp.read_text(encoding="utf-8"))["nac"]
        difs = []
        for a in (2024, 2025):
            m_a = sum(v for k, v in mn.items() if int(k[:4]) == a)
            b_a = sum(r[10][years.index(a)] for r in S)
            difs.append(f"{a}: portal {m_a:,} frente a colegios {b_a:,}")
        ctrl("Serie mensual del portal cuadra con la base por colegio", all(
            sum(v for k, v in mn.items() if int(k[:4]) == a) == sum(r[10][years.index(a)] for r in S) for a in (2024, 2025)),
            "; ".join(difs))
        mes = int(est["corte"][5:7])
        fr = [sum(v for k, v in mn.items() if int(k[:4]) == a and int(k[5:]) <= mes) /
              sum(v for k, v in mn.items() if int(k[:4]) == a) for a in (2024, 2025)]
        f = sum(fr) / len(fr)
        ctrl("Fracción del año dentro del rango del control (0.45–0.75)", 0.45 <= f <= 0.75,
             f"enero–mes {mes}: {fr[0]:.3f} (2024), {fr[1]:.3f} (2025); se usa {f:.2f}")
    else:
        ctrl("Serie mensual del portal disponible", False, "falta data/mensual.json", critico=False)

    # 11. Frescura
    corte = dt.date.fromisoformat(est.get("corte", base["meta"]["corte"]))
    dias = (dt.date.today() - corte).days
    ctrl("Frescura del estado de atención", dias <= 45, f"corte {corte}, hace {dias} días", critico=False)
    ccol = dt.date.fromisoformat(base["meta"]["corte"])
    ctrl("Frescura de la base por colegio", (dt.date.today() - ccol).days <= 120,
         f"corte {ccol}; solo cambia con un nuevo pedido de transparencia", critico=False)

    out = {"fecha": dt.date.today().isoformat(), "controles": C,
           "criticos_fallidos": sum(1 for c in C if c["critico"] and not c["ok"])}
    (DATA / "auditoria.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in C:
        mark = "OK " if c["ok"] else ("XX " if c["critico"] else "!! ")
        print(f"{mark}{c['control']}: {c['detalle']}")
    print(f"\n{sum(c['ok'] for c in C)}/{len(C)} controles cumplen; {out['criticos_fallidos']} críticos fallidos.")
    return 1 if out["criticos_fallidos"] else 0


if __name__ == "__main__":
    sys.exit(main())
