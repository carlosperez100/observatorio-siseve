"""
Construye docs/index.html (GitHub Pages) a partir de template/index.html y data/*.json.

    python scripts/build.py
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def cargar(nombre):
    p = ROOT / "data" / nombre
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def fraccion(mensual, corte):
    """Fracción del año registrada entre enero y el mes de corte, en los años completos."""
    mes, anio = int(corte[5:7]), int(corte[:4])
    fr = {}
    for a in range(anio - 3, anio):
        tot = [v for k, v in mensual["nac"].items() if int(k[:4]) == a]
        if len(tot) == 12:
            fr[a] = sum(v for k, v in mensual["nac"].items() if int(k[:4]) == a and int(k[5:]) <= mes) / sum(tot)
    if not fr:
        raise SystemExit("mensual.json no tiene ningún año completo para calcular la fracción")
    return round(sum(fr.values()) / len(fr), 2), fr, mes


def main():
    base, est, aud = cargar("base.json"), cargar("estado.json"), cargar("auditoria.json")
    if aud is None or aud["criticos_fallidos"]:
        raise SystemExit("La auditoría no pasó (o no se corrió): no se construye. Ejecuta scripts/auditar.py")
    js = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")  # noqa: E731
    html = (ROOT / "template" / "index.html").read_text(encoding="utf-8")
    for marca, valor in (("/*__DATA__*/null", js(base)), ("/*__ESTADO__*/null", js({"U": est["U"], "MAT": est["MAT"]})),
                         ("/*__AUDIT__*/null", js(aud))):
        if marca not in html:
            raise SystemExit(f"Falta la marca {marca} en la plantilla")
        html = html.replace(marca, valor, 1)
    frac, fr_an, mes = fraccion(cargar("mensual.json"), est["corte"])
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "setiembre", "octubre", "noviembre", "diciembre"]
    an_txt = " y ".join(f"{v:.3f} en {a}" for a, v in fr_an.items())
    html = html.replace("__FRAC_TXT__", (
        f"La fracción por defecto ({frac:.2f}) sale del calendario mensual real del portal SíseVe: "
        f"de enero a {meses[mes - 1]} se registró {an_txt}. Es decir, "
        f"de {meses[mes] if mes < 12 else 'diciembre'} a diciembre llega cerca del {round((1 - frac) * 100)} % del año. "
        "Se recalcula cada semana."))
    html = html.replace("__FRAC_AN__", an_txt).replace("__FRAC__", f"{frac:.2f}")
    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    (ROOT / "docs" / ".nojekyll").write_text("")
    print(f"docs/index.html · {len(html) / 1e6:.1f} MB · corte colegios {base['meta']['corte']} · estado {est.get('corte')}")


if __name__ == "__main__":
    main()
