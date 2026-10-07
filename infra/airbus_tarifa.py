"""
Contrasta el planograma de AIRBUS Sevilla con la tarifa definitiva.

La tarifa es una sola (data/tarifa_airbus.csv) y vale para los tres centros:
Tablada, San Pablo Norte y San Pablo Sur. Aqui se mira, centro a centro, que
canales no la cumplen.

  python3 infra/airbus_tarifa.py planograma.csv [bebidas.csv] [--ventas telemetria.csv]

  planograma.csv  M7 · EXT_MAESTRO_PLANOGRAMA (de S3, maestros/planograma); aqui
                  se queda con los tres centros de AIRBUS Sevilla
  bebidas.csv     (opcional) resultado de M2 · EXT_MAESTRO_RECETAS; sus cafes
                  (R01, R04...) se contrastan por `precio_venta`

  --ventas        (opcional) la telemetria (el DEX), A12 · EXT_TELEMETRIA_VENTAS: lo que
                  la maquina cobro de verdad, contra la tarifa

Salida: una linea por canal con problema, y el resumen por centro. Si un dato
no esta, se dice: un articulo sin tarifa no se da por bueno ni por cero.
"""

import csv
import os
import sys
from collections import defaultdict
from decimal import Decimal

AQUI = os.path.dirname(os.path.abspath(__file__))
TARIFA = os.path.join(AQUI, "..", "data", "tarifa_airbus.csv")
CENTROS = ("AIRBUS TABLADA", "AIRBUS SAN PABLO NORTE", "AIRBUS SAN PABLO SUR")


def dec(txt):
    """Un precio de VenCloud o del CSV, con punto o con coma; None si no hay."""
    txt = (txt or "").strip().replace(",", ".")
    return Decimal(txt) if txt else None


def lee_tarifa(ruta=TARIFA):
    t = {}
    for f in csv.DictReader(open(ruta, encoding="utf-8")):
        t[f["cod_articulo"].strip()] = dec(f["precio_ef"])
    return t


def contrasta(canales, tarifa):
    """
    canales: filas con centro, matricula, canal, cod_articulo, articulo, precio_canal_ef.
    Devuelve (problemas, resumen): problemas = lista de (centro, matricula, canal,
    cod, articulo, motivo, precio_canal, tarifa); resumen = {centro: {...}}.
    """
    problemas = []
    resumen = defaultdict(lambda: {"canales": 0, "ok": 0, "distinto": 0, "a_cero": 0, "sin_tarifa": 0, "sin_articulo": 0})
    usados = defaultdict(set)
    for c in canales:
        centro = c["centro"].strip().upper()
        if centro not in CENTROS:
            continue
        cod = (c.get("cod_articulo") or "").strip()
        precio = dec(c.get("precio_canal_ef"))
        r = resumen[centro]
        r["canales"] += 1
        fila = (centro, c.get("matricula", ""), c.get("canal", ""), cod, c.get("articulo", ""))
        if not cod:
            r["sin_articulo"] += 1
            problemas.append(fila + ("canal activo sin articulo", precio, None))
            continue
        usados[centro].add(cod)
        if cod not in tarifa:
            r["sin_tarifa"] += 1
            problemas.append(fila + ("el articulo no esta en la tarifa de AIRBUS", precio, None))
        elif not precio:
            r["a_cero"] += 1
            problemas.append(fila + ("el canal no guarda precio (0)", precio, tarifa[cod]))
        elif precio != tarifa[cod]:
            r["distinto"] += 1
            problemas.append(fila + ("precio del canal distinto de la tarifa", precio, tarifa[cod]))
        else:
            r["ok"] += 1
    return problemas, dict(resumen)


def contrasta_bebidas(recetas, tarifa):
    """Los cafes de la tarifa (R01...) contra el precio de venta de M2."""
    problemas = []
    vistos = set()
    for r in recetas:
        cod = (r.get("cod_bebida") or "").strip()
        if cod not in tarifa or cod in vistos:
            continue
        vistos.add(cod)
        precio = dec(r.get("precio_venta"))
        if precio != tarifa[cod]:
            problemas.append((cod, r.get("bebida", ""), precio, tarifa[cod]))
    faltan = sorted(c for c in tarifa if c.startswith("R") and c not in vistos)
    return problemas, faltan


def contrasta_ventas(ventas, tarifa):
    """
    La telemetria (DEX) contra la tarifa: lo cobrado, no lo guardado en el canal.
    Devuelve (problemas, resumen). problemas = (centro, matricula, cod, articulo,
    precio_cobrado, tarifa, ventas, motivo), una fila por precio distinto cobrado.
    La venta sin articulo no se puede contrastar: se cuenta aparte, no se adivina.
    """
    grupos = defaultdict(int)
    resumen = defaultdict(lambda: {"ventas": 0, "ok": 0, "distinto": 0, "sin_tarifa": 0, "sin_articulo": 0})
    nombres = {}
    for v in ventas:
        centro = v["centro"].strip().upper()
        if centro not in CENTROS:
            continue
        r = resumen[centro]
        r["ventas"] += 1
        cod = (v.get("cod_articulo") or "").strip()
        if not cod:
            r["sin_articulo"] += 1
            continue
        precio = dec(v.get("precio"))
        nombres[cod] = v.get("articulo", "")
        if cod not in tarifa:
            r["sin_tarifa"] += 1
            grupos[(centro, v.get("matricula", ""), cod, precio, "el articulo no esta en la tarifa")] += 1
        elif precio != tarifa[cod]:
            r["distinto"] += 1
            grupos[(centro, v.get("matricula", ""), cod, precio, "cobrado distinto de la tarifa")] += 1
        else:
            r["ok"] += 1
    problemas = [(c, m, cod, nombres[cod], precio, tarifa.get(cod), n, motivo)
                 for (c, m, cod, precio, motivo), n in sorted(grupos.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2]))]
    return problemas, dict(resumen)


def main(argv):
    ventas = None
    if "--ventas" in argv:
        i = argv.index("--ventas")
        ventas = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    if len(argv) < 2:
        print(__doc__)
        return 2
    tarifa = lee_tarifa()
    canales = list(csv.DictReader(open(argv[1], encoding="utf-8-sig")))
    problemas, resumen = contrasta(canales, tarifa)
    print("centro;maquina;canal;cod_articulo;articulo;motivo;precio_canal;tarifa")
    for p in problemas:
        print(";".join("" if x is None else str(x) for x in p))
    print()
    for centro, r in sorted(resumen.items()):
        print(f"{centro}: {r['canales']} canales · {r['ok']} bien · {r['distinto']} con otro precio · {r['a_cero']} a cero · "
              f"{r['sin_tarifa']} sin tarifa · {r['sin_articulo']} sin articulo")
    if len(argv) > 2:
        recetas = list(csv.DictReader(open(argv[2], encoding="utf-8-sig")))
        pb, faltan = contrasta_bebidas(recetas, tarifa)
        print("\nCafes (precio de venta, M2):")
        for cod, nombre, precio, t in pb:
            print(f"  {cod} {nombre}: {precio} y la tarifa dice {t}")
        if faltan:
            print(f"  sin precio en M2: {', '.join(faltan)}")
        if not pb and not faltan:
            print("  todos coinciden con la tarifa")
    if ventas:
        vp, vr = contrasta_ventas(list(csv.DictReader(open(ventas, encoding="utf-8-sig"))), tarifa)
        print("\nTelemetria (DEX) contra la tarifa:")
        print("centro;maquina;cod_articulo;articulo;precio_cobrado;tarifa;ventas;motivo")
        for p in vp:
            print(";".join("" if x is None else str(x) for x in p))
        for centro, r in sorted(vr.items()):
            print(f"{centro}: {r['ventas']} ventas · {r['ok']} al precio de la tarifa · {r['distinto']} a otro precio · "
                  f"{r['sin_tarifa']} sin tarifa · {r['sin_articulo']} sin articulo (no se pueden contrastar)")
        problemas = problemas or vp
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
