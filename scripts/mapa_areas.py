#!/usr/bin/env python3
"""El mapa de las areas de /rutas/: une las comunidades autonomas de cada area
y saca un trazo SVG por area, ya proyectado y simplificado, para pegarlo en
app/rutas/index.html (const MAPA). Se corre una vez; la pagina no lo necesita.

Fuente: spain-communities.geojson de codeforgermany/click_that_hood
(https://github.com/codeforgermany/click_that_hood, public/data/).

    pip install shapely
    python3 scripts/mapa_areas.py spain-communities.geojson
"""
import json
import math
import sys

from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import polylabel, unary_union

# Las comunidades de cada area, por donde caen sus delegaciones. Canarias,
# Ceuta y Melilla no tienen delegacion y no se pintan.
AREAS = {
    "Norte": ["Galicia", "Asturias", "Cantabria", "Pais Vasco", "Navarra", "La Rioja", "Castilla-Leon"],
    "Centro": ["Madrid", "Castilla-La Mancha", "Extremadura", "Aragon"],
    "Cataluña": ["Cataluña"],
    "Levante": ["Valencia", "Murcia", "Baleares"],
    "Sur": ["Andalucia"],
}
ANCHO = 1000          # el viewBox mide 1000 de ancho
LAT0 = 40.0           # paralelo de la proyeccion (equirrectangular)
TOLERANCIA = 0.025    # grados: lo que se simplifica la costa
MIN_ISLA = 0.004      # grados cuadrados: las islas mas pequenas no se pintan
SEPARA = 7            # lo que se apartan las areas del centro, en el viewBox
# Donde va el porcentaje cuando el punto mas hondo del area no es el que se
# espera (el de Centro caeria en Extremadura): lon, lat.
ETIQUETA = {"Centro": (-3.9, 39.9), "Levante": (-0.95, 38.35), "Cataluña": (1.6, 41.75)}


def poligonos(g):
    return list(g.geoms) if isinstance(g, MultiPolygon) else [g]


def main(ruta):
    com = {f["properties"]["name"]: shape(f["geometry"]).buffer(0)
           for f in json.load(open(ruta, encoding="utf-8"))["features"]}
    union = {a: unary_union([com[c] for c in cs]).buffer(0.002).buffer(-0.002) for a, cs in AREAS.items()}
    # Fuera las islas pequenas y los huecos (enclaves y restos de la union).
    union = {a: MultiPolygon([Polygon(p.exterior) for p in poligonos(g) if p.area >= MIN_ISLA]).simplify(TOLERANCIA)
             for a, g in union.items()}
    todo = unary_union(list(union.values()))
    x0, y0, x1, y1 = todo.bounds
    k = math.cos(math.radians(LAT0))
    esc = ANCHO / ((x1 - x0) * k)
    alto = (y1 - y0) * esc
    cx, cy = todo.centroid.x, todo.centroid.y

    def xy(lon, lat):
        return ((lon - x0) * k * esc, (y1 - lat) * esc)

    salida = {}
    for a, g in union.items():
        # Cada area se aparta un poco del centro, como un puzle levantado.
        c = g.centroid
        dx, dy = (c.x - cx) * k, (c.y - cy)
        n = math.hypot(dx, dy) or 1
        ox, oy = SEPARA * dx / n, -SEPARA * dy / n
        trozos = []
        for p in poligonos(g):
            pts = [xy(lon, lat) for lon, lat in p.exterior.coords[:-1]]
            trozos.append("M" + "L".join(f"{x + ox:.0f} {y + oy:.0f}" for x, y in pts) + "Z")
        if a in ETIQUETA:
            lx, ly = xy(*ETIQUETA[a])
        else:
            e = polylabel(max(poligonos(g), key=lambda p: p.area), tolerance=0.01)
            lx, ly = xy(e.x, e.y)
        salida[a] = {"d": "".join(trozos), "x": round(lx + ox), "y": round(ly + oy)}
    print(json.dumps({"ancho": ANCHO, "alto": round(alto), "areas": salida}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
