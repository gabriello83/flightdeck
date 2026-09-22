#!/usr/bin/env python3
"""Analisis exploratorio de las tablas consolidadas: que da de si el dato."""
import csv
import datetime as dt
import gzip
import statistics
from collections import Counter, defaultdict
from pathlib import Path

DATOS = Path(__file__).resolve().parent.parent / "data" / "processed"
FESTIVOS = set()  # sin calendario laboral de Airbus; los findes salen del propio dato


def leer(nombre):
    ruta = DATOS / nombre
    abrir = gzip.open if ruta.suffix == ".gz" else open
    with abrir(ruta, "rt", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def titulo(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


ventas = leer("ventas.csv.gz")
visitas = leer("visitas.csv.gz")
averias = leer("averias.csv.gz")
preventivos = leer("preventivos.csv.gz")

for v in ventas:
    v["importe"] = float(v["importe"])
    v["d"] = dt.date.fromisoformat(v["fecha"])
for v in visitas:
    v["d"] = dt.date.fromisoformat(v["fecha"])

titulo("1. VOLUMEN GLOBAL")
total = sum(v["importe"] for v in ventas)
maquinas = {(v["centro"], v["maquina"]) for v in ventas}
dias = sorted({v["d"] for v in ventas})
print(f"{len(ventas):,} lineas | {total:,.2f} EUR | {len(maquinas)} maquinas | "
      f"{len({v['articulo'] for v in ventas})} articulos")
print(f"periodo {dias[0]} -> {dias[-1]} ({len(dias)} dias con venta)")
print(f"precio medio por unidad: {total / len(ventas):.3f} EUR")

titulo("2. PATRON SEMANAL (el dia de la semana manda)")
dsem = defaultdict(float)
ndias = defaultdict(set)
for v in ventas:
    dsem[v["d"].weekday()] += v["importe"]
    ndias[v["d"].weekday()].add(v["d"])
nombres = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
for i in range(7):
    print(f"  {nombres[i]:10s} {dsem[i]:12,.0f} EUR  media/dia {dsem[i]/len(ndias[i]):9,.0f} EUR")
laborables = {d for d in dias if d.weekday() < 5}
print(f"  -> {len(laborables)} dias laborables, {len(dias)-len(laborables)} findes")

titulo("3. CONCENTRACION DE SURTIDO (Pareto de articulos)")
art = Counter()
for v in ventas:
    art[v["articulo"]] += v["importe"]
acum = 0
for i, (a, imp) in enumerate(art.most_common(), 1):
    acum += imp
    if i in (10, 20, 50, 100):
        print(f"  top {i:3d} articulos = {acum/total*100:5.1f}% de la venta")
print("  mas vendidos:", ", ".join(f"{a} ({imp:,.0f})" for a, imp in art.most_common(5)))
cola = [a for a, imp in art.items() if imp < 100]
print(f"  articulos con menos de 100 EUR en 4 meses: {len(cola)} de {len(art)}")

titulo("4. RENDIMIENTO POR MAQUINA")
pm = defaultdict(float)
pmd = defaultdict(set)
for v in ventas:
    pm[(v["centro"], v["maquina"])] += v["importe"]
    pmd[(v["centro"], v["maquina"])].add(v["d"])
rend = sorted(((imp / max(len([d for d in pmd[k] if d.weekday() < 5]), 1), k, imp) for k, imp in pm.items()), reverse=True)
print("  mejores (EUR por dia laborable con venta):")
for r, k, imp in rend[:5]:
    print(f"    {k[1]:10s} {k[0]:24s} {r:8.1f} EUR/dia  total {imp:9,.0f}")
print("  peores:")
for r, k, imp in rend[-5:]:
    print(f"    {k[1]:10s} {k[0]:24s} {r:8.1f} EUR/dia  total {imp:9,.0f}")
valores = [r for r, _, _ in rend]
print(f"  mediana {statistics.median(valores):.1f} EUR/dia | "
      f"el 20% mejor concentra {sum(sorted((imp for imp in pm.values()), reverse=True)[:len(pm)//5])/total*100:.0f}% de la venta")

titulo("5. MAQUINAS MUDAS (dias laborables sin una sola venta)")
mudas = []
for k, ds in pmd.items():
    activos = sorted(d for d in ds if d.weekday() < 5)
    if len(activos) < 5:
        continue
    huecos, racha, anterior = [], 0, None
    d = activos[0]
    while d <= activos[-1]:
        if d.weekday() < 5:
            if d in ds:
                if racha >= 3:
                    huecos.append((racha, anterior))
                racha = 0
            else:
                racha += 1
                anterior = d
        d += dt.timedelta(days=1)
    if huecos:
        mudas.append((max(huecos)[0], k, len(huecos), sum(h for h, _ in huecos)))
mudas.sort(reverse=True)
print(f"  {len(mudas)} maquinas con al menos un paron de 3+ dias laborables seguidos")
print(f"  dias laborables mudos acumulados: {sum(m[3] for m in mudas)}")
for m in mudas[:8]:
    print(f"    {m[1][1]:10s} {m[1][0]:24s} parada mas larga {m[0]:3d} dias | {m[2]} parones")

titulo("6. VISITAS DE REPOSICION")
vis = Counter((v["centro"], v["maquina"]) for v in visitas)
print(f"  {len(visitas):,} visitas | {len(vis)} maquinas visitadas | "
      f"{len({v['empleado'] for v in visitas})} reponedores | {len({v['ruta'] for v in visitas})} rutas")
con_venta = [k for k in vis if k in pm]
print(f"  maquinas visitadas que ademas tienen ventas: {len(con_venta)}")
eur_visita = sorted(((pm[k] / vis[k], k, vis[k], pm[k]) for k in con_venta))
print("  MENOS rentables por visita (candidatas a espaciar ruta):")
for r, k, nv, imp in eur_visita[:6]:
    print(f"    {k[1]:10s} {k[0]:22s} {nv:4d} visitas  {imp:8,.0f} EUR  -> {r:7.1f} EUR/visita")
print("  MAS exigidas (candidatas a mas frecuencia o mas capacidad):")
for r, k, nv, imp in eur_visita[-6:]:
    print(f"    {k[1]:10s} {k[0]:22s} {nv:4d} visitas  {imp:8,.0f} EUR  -> {r:7.1f} EUR/visita")
solo_visita = [k for k in vis if k not in pm]
print(f"  visitadas SIN ninguna venta en el periodo: {len(solo_visita)} maquinas, "
      f"{sum(vis[k] for k in solo_visita)} visitas")

titulo("7. AVERIAS")
print(f"  {len(averias)} incidencias")
for c, n in Counter(a["categoria"] for a in averias).most_common():
    print(f"    {c:28s} {n:4d}")
print("  operaciones mas frecuentes:")
for o, n in Counter(a["operacion"] for a in averias).most_common(8):
    print(f"    {o[:50]:52s} {n:4d}")
dur = [float(a["horas_resolucion"]) for a in averias
       if a["horas_resolucion"] and a["cierre_por_lotes"] == "no" and float(a["horas_resolucion"]) >= 0]
if dur:
    dur.sort()
    print(f"  resolucion real (excluyendo cierres por lotes a las 00:00): n={len(dur)}")
    print(f"    mediana {statistics.median(dur):6.1f} h | media {statistics.mean(dur):6.1f} h | "
          f"p90 {dur[int(len(dur)*.9)]:6.1f} h | max {dur[-1]:,.0f} h")
    print(f"    resueltas en <4h {sum(1 for x in dur if x<4)/len(dur)*100:4.0f}% | "
          f"<24h {sum(1 for x in dur if x<24)/len(dur)*100:4.0f}% | "
          f"<48h {sum(1 for x in dur if x<48)/len(dur)*100:4.0f}%")
lotes = sum(1 for a in averias if a["cierre_por_lotes"] == "si")
abiertas = sum(1 for a in averias if not a["fecha_cierre"])
print(f"  cierres administrativos a las 00:00: {lotes} | sin fecha de cierre: {abiertas}")
reinc = Counter((a["centro"], a["maquina"]) for a in averias)
print("  maquinas reincidentes:")
for k, n in reinc.most_common(6):
    print(f"    {k[1]:10s} {k[0]:24s} {n:3d} averias | venta del periodo {pm.get(k,0):8,.0f} EUR")
print("  averias por modelo (top):")
for m, n in Counter(a["modelo"] for a in averias if a["modelo"]).most_common(6):
    print(f"    {m[:36]:38s} {n:4d}")

titulo("8. IMPACTO MEDIBLE DE LAS AVERIAS EN LA VENTA")
vent_dia = defaultdict(float)
for v in ventas:
    vent_dia[(v["centro"], v["maquina"], v["d"])] += v["importe"]
base = {}
for k in pm:
    dd = [vent_dia[(k[0], k[1], d)] for d in laborables]
    dd = [x for x in dd if x > 0]
    base[k] = statistics.median(dd) if dd else 0
perdida = 0.0
casos = 0
for a in averias:
    k = (a["centro"], a["maquina"])
    if k not in base or not a["fecha_alta"] or not a["fecha_cierre"]:
        continue
    d0 = dt.date.fromisoformat(a["fecha_alta"])
    d1 = dt.date.fromisoformat(a["fecha_cierre"])
    if d1 < d0 or (d1 - d0).days > 30:
        continue
    dias_lab = [d0 + dt.timedelta(days=i) for i in range((d1 - d0).days + 1)]
    dias_lab = [d for d in dias_lab if d.weekday() < 5]
    if not dias_lab:
        continue
    real = sum(vent_dia[(k[0], k[1], d)] for d in dias_lab)
    esperado = base[k] * len(dias_lab)
    if esperado > real:
        perdida += esperado - real
        casos += 1
print(f"  ventana de incidencia analizada en {casos} averias")
print(f"  venta por debajo de lo normal durante la incidencia: {perdida:,.0f} EUR "
      f"({perdida/total*100:.2f}% de la venta del periodo)")

titulo("9. PREVENTIVOS")
prev = Counter((p["centro"], p["maquina"]) for p in preventivos)
print(f"  {len(preventivos)} preventivos sobre {len(prev)} maquinas distintas")
print(f"  cobertura: {len([k for k in prev if k in pm])} de {len(pm)} maquinas con venta "
      f"({len([k for k in prev if k in pm])/len(pm)*100:.0f}%)")
con, sin = [], []
for k in pm:
    (con if k in prev else sin).append(reinc.get(k, 0))
print(f"  averias/maquina CON preventivo: {statistics.mean(con):.2f} (n={len(con)})")
print(f"  averias/maquina SIN preventivo: {statistics.mean(sin):.2f} (n={len(sin)})")

titulo("10. PRECIOS: EL MISMO ARTICULO A DISTINTO PRECIO SEGUN CENTRO")
prec = defaultdict(set)
for v in ventas:
    prec[v["articulo"]].add((v["centro"], round(v["importe"], 2)))
dif = []
for a, s in prec.items():
    porc = defaultdict(set)
    for c, p in s:
        porc[c].add(p)
    precios = {c: max(ps) for c, ps in porc.items()}
    if len(set(precios.values())) > 1 and len(precios) > 1:
        dif.append((max(precios.values()) - min(precios.values()), a, precios))
dif.sort(reverse=True)
print(f"  {len(dif)} articulos con precio distinto entre centros")
for d, a, precios in dif[:6]:
    rango = ", ".join(f"{c.replace('AIRBUS ','')}:{p:.2f}" for c, p in sorted(precios.items(), key=lambda x: -x[1])[:4])
    print(f"    {a[:30]:32s} dif {d:.2f} EUR  {rango}")
