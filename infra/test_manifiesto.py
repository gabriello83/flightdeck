"""
Valida el manifiesto antes de que lo haga la noche.

Este fichero se edita a mano, y a veces directamente en GitHub. Un numero de
informe mal copiado no se nota al guardarlo: se nota a las 3:15 de la manana,
cuando la extraccion baja el informe equivocado o se niega a arrancar. Esto lo
caza antes.

    python3 infra/test_manifiesto.py
"""

import json
import sys
from collections import Counter

AQUI = __file__.rsplit("/", 1)[0]
M = json.load(open(f"{AQUI}/manifiesto.json"))
INFS = M["informes"]

CLAVES_FECHA = {"propia", "madre", "escritura", "ninguna"}
PREFIJOS = ("crudo/", "maestros/", "restringido/")

fallos = []


def comprueba(que, obtenido, esperado):
    if obtenido == esperado:
        print(f"  ok    {que}")
    else:
        print(f"  FALLO {que}: {obtenido!r} != {esperado!r}")
        fallos.append(que)


# ----------------------------------------------------------------------
print("\nForma del manifiesto")
comprueba("31 informes", len(INFS), 31)
comprueba("ventana de reproceso de 3 dias", M["ventana_reproceso_dias"], 3)
comprueba("ids sin repetir", len({i["id"] for i in INFS}), 31)
comprueba("nombres sin repetir", len({i["nombre"] for i in INFS}), 31)
comprueba("destinos sin repetir", len({i["destino"] for i in INFS}), 31)
comprueba("todos los nombres empiezan por EXT_",
          all(i["nombre"].startswith("EXT_") for i in INFS), True)

print("\nLos numeros de informe")
sin = [i["nombre"] for i in INFS if not i.get("informe")]
comprueba("ninguno sin numero", sin, [])
nums = [i["informe"] for i in INFS if i.get("informe")]
rep = sorted(n for n, c in Counter(nums).items() if c > 1)
# Dos informes con el mismo numero significa que uno baja los datos del otro, y
# cuadra todo menos la realidad: es el fallo mas caro de detectar despues.
comprueba("ninguno repetido", rep, [])
comprueba("todos son enteros", all(isinstance(n, int) for n in nums), True)
comprueba("todos positivos", all(n > 0 for n in nums), True)

print("\nLas claves de fecha")
malas = [(i["id"], i["clave_fecha"]) for i in INFS if i["clave_fecha"] not in CLAVES_FECHA]
comprueba("todas del vocabulario", malas, [])

print("\nMaestro y fecha van juntos o no van")
# Un maestro no lleva fechas y vive en maestros/. Si una de las dos cosas no
# cuadra, la extraccion le pasaria parametros a un informe que no los espera,
# o lo particionaria por un dia que no significa nada.
incoherentes = [i["id"] for i in INFS
                if (i["clave_fecha"] == "ninguna") != i["destino"].startswith("maestros/")]
comprueba("coherentes", incoherentes, [])
comprueba("9 maestros", sum(1 for i in INFS if i["clave_fecha"] == "ninguna"), 9)
comprueba("22 incrementales", sum(1 for i in INFS if i["clave_fecha"] != "ninguna"), 22)

print("\nLos destinos")
raros = [i["destino"] for i in INFS if not i["destino"].startswith(PREFIJOS)]
comprueba("todos con prefijo conocido", raros, [])

print("\nEl dato con nombre y DNI va aparte, y solo el")
restr = [i for i in INFS if i["destino"].startswith("restringido/")]
comprueba("un solo informe restringido", len(restr), 1)
comprueba("y es el de devoluciones", restr[0]["id"], "visita_devoluciones")
comprueba("lleva la marca", restr[0].get("restringido"), True)
comprueba("y lo explica", "DNI" in restr[0].get("_nota", ""), True)
marcados = [i["id"] for i in INFS if i.get("restringido")]
comprueba("nadie mas la lleva", marcados, ["visita_devoluciones"])

print("\nLas tablas muertas no se cuelan entre las vivas")
muertas = set(M["descartados"]["lista"])
comprueba("10 descartadas", len(muertas), 10)
vivas = {i["id"] for i in INFS}
comprueba("sin solape", sorted(muertas & vivas), [])

print("\nfilas_mes")
mal = [i["id"] for i in INFS
       if i.get("filas_mes") is not None and not (isinstance(i["filas_mes"], int) and i["filas_mes"] >= 0)]
comprueba("entero no negativo o nulo", mal, [])

print("\nLa extraccion arrancaria")
# Es la misma condicion que mira lambda_extraccion.manifiesto(): si falta un
# numero, se niega a empezar en vez de bajar el informe equivocado en silencio.
comprueba("no hay nada que la detenga", len(sin), 0)
print(f"        30 informes, numeros {min(nums)}–{max(nums)}, "
      f"{sum(i.get('filas_mes') or 0 for i in INFS):,} filas al mes")

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("El manifiesto esta bien.")
