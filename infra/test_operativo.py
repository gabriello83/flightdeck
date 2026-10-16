"""
El informe general operativo: las cuentas de cada cuadrado (docs/51).

Cada caso de aqui es una trampa que se ve en el dato de verdad: el vehiculo
«xxxx-xxx», el punto de venta planificado por dos rutas, la avería que se
abrio antes de la ventana, el azucar contado como reposicion.

    python3 infra/test_operativo.py
"""

import sys

AQUI = __file__.rsplit("/", 1)[0]
sys.path.insert(0, AQUI)

import operativo as OP  # noqa: E402

fallos = []


def comprueba(que, dado, esperado):
    ok = dado == esperado
    print(f"  {'ok   ' if ok else 'FALLO'} {que}" + ("" if ok else f": {dado!r} != {esperado!r}"))
    if not ok:
        fallos.append(que)


DIA = "2026-10-09"


def visita(pdv, vehiculo="1234ABC", matricula="M1"):
    return {"empleadoid": 7, "tipo_parte": 0, "cod_pdv": pdv, "vehiculo": vehiculo,
            "matricula": matricula, "minutos": 6}


def sistema(matricula, lectura=2):
    return {"empleadoid": 0, "empleado": "SYSTEM", "tipo_parte": 2, "origen": 2,
            "estado_lectura": lectura, "matricula": matricula, "cod_pdv": "X"}


print("El semaforo: verde por encima de 95, rojo por debajo de 75")
comprueba("95,1 es verde", OP.semaforo(95.1), "verde")
comprueba("95 justo es amarillo", OP.semaforo(95.0), "amarillo")
comprueba("75 justo es amarillo", OP.semaforo(75.0), "amarillo")
comprueba("74,9 es rojo", OP.semaforo(74.9), "rojo")
comprueba("sin porcentaje no hay color", OP.semaforo(None), None)

print("\nRutas: visitas hechas contra el plan del dia")
op = OP.Operativo([DIA])
d = op.dia(DIA)
d.come_partes([visita("P1"), visita("P2"), visita("P2"), visita("P9")])
d.come_plan([{"cod_pdv": "P1"}, {"cod_pdv": "P2"}, {"cod_pdv": "P2"},  # P2 en dos rutas
             {"cod_pdv": "P3"}, {"cod_pdv": "P4"}])
c = op.cuadrados_del_dia(d)["rutas"]
comprueba("un punto de venta en dos rutas es UNA visita prevista", c["previstas"], 4)
comprueba("hechas: P1 y P2", c["hechas"], 2)
comprueba("50 %", c["pct"], 50.0)
comprueba("rojo", c["color"], "rojo")
comprueba("P9 se visito sin estar en el plan", c["fuera_de_plan"], 1)

print("\nSin el informe del plan, se dice; no sale un cero")
op = OP.Operativo([DIA])
d = op.dia(DIA)
d.come_partes([visita("P1")])
c = op.cuadrados_del_dia(d)["rutas"]
comprueba("sin dato", "sin_dato" in c, True)
comprueba("y sin porcentaje", "pct" in c, False)

print("\nFurgonetas: distintas ese dia, sin las matriculas de relleno")
op = OP.Operativo([DIA])
d = op.dia(DIA)
d.come_partes([visita("P1", "1234ABC"), visita("P2", "1234ABC"), visita("P3", "9999XYZ"),
               visita("P4", "xxxx-xxx"), visita("P5", "xxxxxxx"), visita("P6", "")])
c = op.cuadrados_del_dia(d)["furgonetas"]
comprueba("dos furgonetas", c["activas"], 2)
comprueba("tres visitas sin vehiculo de verdad", c["visitas_sin_vehiculo"], 3)

print("\nTelemetria: lecturas remotas sobre las maquinas que se pueden auditar")
op = OP.Operativo([DIA])
op.come_censo([
    {"cod_pdv": "P1", "matricula": "M1", "telemetria": 40, "estado_pdv": 1},
    {"cod_pdv": "P2", "matricula": "M2", "telemetria": 40, "estado_pdv": 1},
    {"cod_pdv": "P3", "matricula": "M3", "telemetria": 0, "estado_pdv": 1},
    {"cod_pdv": "P4", "matricula": "M4", "telemetria": 40, "estado_pdv": 1},
    {"cod_pdv": "P5", "matricula": "M5", "telemetria": 40, "estado_pdv": 1},
])
d = op.dia(DIA)
d.come_partes([sistema("M1"), sistema("M2"), sistema("M3"),
               sistema("M4", lectura=1),           # parte sin lectura
               visita("P5", matricula="M5")])      # una visita de reponedor no es remota
c = op.cuadrados_del_dia(d)["telemetria"]
comprueba("cuatro maquinas auditables en remoto", c["auditables"], 4)
comprueba("dos con lectura (M3 no tiene telemetria)", c["con_dex"], 2)
comprueba("50 %", c["pct"], 50.0)
comprueba("cinco puntos de venta activos", op.foto["pdvs"]["activos"], 5)

print("\nAverias: cerradas ese dia en menos de 24 horas")
op = OP.Operativo([DIA])
op.come_sat([
    {"id": 1, "matricula": "M1", "cod_operacion": "A01", "tipo_tarea": "A"},
    {"id": 2, "matricula": "M1", "cod_operacion": "A01", "tipo_tarea": "A"},
    {"id": 3, "matricula": "M1", "cod_operacion": "A01", "tipo_tarea": "E"},   # solicitud especial
    {"id": 4, "matricula": "00SE0000", "cod_operacion": "A01", "tipo_tarea": "A"},  # ficticia
])
op.come_sat_eventos([
    {"averia_id": 1, "estado": 0, "fecha": "2026-10-09 08:00:00"},
    {"averia_id": 1, "estado": 99, "fecha": "2026-10-09 14:00:00"},     # 6 h
    {"averia_id": 2, "estado": 0, "fecha": "2026-10-08T06:00:00"},
    {"averia_id": 2, "estado": 99, "fecha": "2026-10-09T12:00:00"},     # 30 h
    {"averia_id": 3, "estado": 99, "fecha": "2026-10-09 10:00:00"},
    {"averia_id": 4, "estado": 99, "fecha": "2026-10-09 10:00:00"},
    {"averia_id": 9, "estado": 99, "fecha": "2026-10-09 11:00:00"},     # abierta antes de la ventana
])
c = op.cuadrados_del_dia(op.dia(DIA))["averias"]
comprueba("dos averias cerradas", c["cerradas"], 2)
comprueba("una a tiempo", c["a_tiempo"], 1)
comprueba("50 %", c["pct"], 50.0)
comprueba("la que no tiene tarea en la ventana se cuenta aparte", c["sin_tarea"], 2)

print("\nReposiciones: por clase de maquina, sin azucar ni vasos")
op = OP.Operativo([DIA])
d = op.dia(DIA)
d.come_lineas([
    {"tipo_linea": "CM", "cantidad": 10, "precio_coste": 1, "etiq_canal": "11", "matricula": "M1"},
    {"tipo_linea": "CM", "cantidad": 5, "precio_coste": 1, "etiq_canal": "12", "matricula": "M2"},
    {"tipo_linea": "CM", "cantidad": 200, "precio_coste": 0.01, "etiq_canal": "", "matricula": "M2"},
    {"tipo_linea": "RC", "cantidad": 3, "precio_coste": 1, "etiq_canal": "11", "matricula": "M1"},
], {"M1": 9, "M2": 2})
c = op.cuadrados_del_dia(d)["reposiciones"]
comprueba("quince unidades de producto", c["unidades"], 15.0)
comprueba("el consumible va aparte", c["consumibles"], 200.0)
comprueba("snack primero", c["por_clase"][0], {"clase": "Snack", "unidades": 10.0})

print("\nAlmacenes: el ultimo cierre, y solo los de sus delegaciones")
balance = {
    (2026, 8): [{"tipo_elemento": "A", "almacen": "Alm Sevilla", "valor_total": 10}],
    (2026, 9): [{"tipo_elemento": "A", "almacen": "Alm Sevilla", "valor_total": 100.5},
                {"tipo_elemento": "A", "almacen": "Alm Madrid", "valor_total": 200},
                {"tipo_elemento": "M", "valor_total": 9999}],
}
rutas = [{"almacen": "Alm Sevilla", "delegacion": "Andalucía - Sevilla"},
         {"almacen": "Alm Madrid", "delegacion": "Madrid - Leganes"}]
a = OP.almacenes(balance, rutas, {})
comprueba("el interno ve los dos, del cierre de septiembre", (a["valor"], a["periodo"]), (300.5, "2026-09"))
a = OP.almacenes(balance, rutas, {"delegaciones": ["Madrid - Leganes"]})
comprueba("una delegacion ve su almacen", a["valor"], 200.0)
a = OP.almacenes(balance, rutas, {"clientes": ["AIRBUS"], "centros": [], "delegaciones": []})
comprueba("un perfil de clientes no tiene almacenes: se dice", "sin_dato" in a, True)
comprueba("sin cierres, se dice", "sin_dato" in OP.almacenes({}, rutas, {}), True)

print("\nEl fichero acumula dias y se queda con los ultimos")
op = OP.Operativo(["2026-10-09"])
op.dia("2026-10-09").come_partes([visita("P1")])
viejo = {"dias": {"2026-10-01": {"rutas": {"sin_dato": "x"}},
                  "2026-10-09": {"rutas": {"sin_dato": "viejo"}}}}
f = op.fichero("interno", viejo)
comprueba("el dia viejo se queda", "2026-10-01" in f["dias"], True)
comprueba("el dia recalculado sustituye", f["dias"]["2026-10-09"]["furgonetas"]["activas"], 1)
comprueba("ultimo dia", f["ultimo_dia"], "2026-10-09")
comprueba("los umbrales viajan en el fichero", f["umbrales"], {"verde": 95.0, "amarillo": 75.0})

print("\nLa pagina de rutas: delegaciones, rutas y puntos de venta (docs/55)")


def parte(pdv, deleg, ruta="R1", quien="Ana", pid=None, ini="2026-10-09 09:30:00"):
    return dict(visita(pdv, matricula="M" + pdv), delegacion=deleg, ruta=ruta, empleado=quien,
                centro="C " + pdv, num_centro="9" + pdv[-1], parte_id=pid or "id" + pdv, fecha_ini=ini)


def plan(pdv, deleg, ruta):
    return {"cod_pdv": pdv, "delegacion": deleg, "ruta": ruta, "centro": "C " + pdv,
            "num_centro": "9" + pdv[-1], "matricula": "M" + pdv}


def linea(pid):
    return {"parte_id": pid, "tipo_linea": "CM", "cantidad": 3, "matricula": "M"}


op = OP.Operativo([DIA])
d = op.dia(DIA)
d.come_partes([parte("P1", "Madrid", "R1", ini="2026-10-09 11:00:00"),
               parte("P1", "Madrid", "R1", "Pepe", pid="idP1b", ini="2026-10-09T08:05:00"),
               parte("P2", "Madrid", "R2"), parte("P9", "Madrid", "R2", "Luis"),
               parte("S1", "Sevilla", "S")])
d.come_plan([plan("P1", "Madrid", "R1"), plan("P2", "Madrid", "R1"), plan("P2", "Madrid", "R2"),
             plan("P3", "Madrid", "R2"), plan("S1", "Sevilla", "S"), plan("S2", "Sevilla", "S")])
# P1: su segundo parte tiene lineas -> no es pasaje vacio. P2 y P9 no tienen
# ninguna -> pasaje vacio. S1 tiene una linea de retirada: tampoco.
d.come_lineas([linea("idP1b"), dict(linea("idS1"), tipo_linea="RC")], {})
r = op.detalle_rutas("interno", ubicaciones={"MP3": "Planta 8"})["dias"][DIA]
comprueba("el total cuenta por punto de venta", (r["total"]["previstas"], r["total"]["hechas"]), (5, 3))
dl = {x["delegacion"]: x for x in r["delegaciones"]}
comprueba("Madrid: 2 de 3 y una fuera de plan", (dl["Madrid"]["hechas"], dl["Madrid"]["previstas"],
                                                 dl["Madrid"]["fuera"], dl["Madrid"]["pct"]), (2, 3, 1, 66.7))
comprueba("la peor delegacion primero", [x["delegacion"] for x in r["delegaciones"]], ["Sevilla", "Madrid"])
rt = {x["ruta"]: x for x in r["rutas"]}
comprueba("P2 en dos rutas cuenta en las dos", (rt["R1"]["previstas"], rt["R2"]["previstas"]), (2, 2))
comprueba("la visita fuera de plan va a la ruta del parte", (rt["R2"]["fuera"], rt["R1"]["fuera"]), (1, 0))
comprueba("pasaje vacio: visitas sin ninguna linea, en hechas y fuera de ruta",
          (r["total"]["vacio"], dl["Madrid"]["vacio"], dl["Sevilla"]["vacio"]), (2, 2, 0))
comprueba("pasaje vacio por ruta: P2 en R1 y R2, P9 en R2", (rt["R1"]["vacio"], rt["R2"]["vacio"]), (1, 2))
comprueba("la lista, pendientes primero, con matricula, ubicacion, hora y reponedor", r["visitas"], [
    ["PENDIENTE", "P3", "MP3", "Madrid", "R2", "93", "C P3", "Planta 8", "", "", None],
    ["PENDIENTE", "S2", "MS2", "Sevilla", "S", "92", "C S2", "", "", "", None],
    ["HECHA", "P1", "MP1", "Madrid", "R1", "91", "C P1", "", "08:05", "Pepe", 0],
    ["HECHA", "P2", "MP2", "Madrid", "R1 / R2", "92", "C P2", "", "09:30", "Ana", 1],
    ["HECHA", "S1", "MS1", "Sevilla", "S", "91", "C S1", "", "09:30", "Ana", 0],
    ["FUERA DE RUTA", "P9", "MP9", "Madrid", "R2", "99", "C P9", "", "09:30", "Luis", 1],
])
comprueba("con lineas no se avisa de nada", "sin_vacio" in r, False)

op = OP.Operativo([DIA])
op.dia(DIA).come_partes([parte("P1", "Madrid")])
op.dia(DIA).come_plan([plan("P1", "Madrid", "R1")])
r = op.detalle_rutas("interno")["dias"][DIA]
comprueba("sin ninguna linea ese dia, el pasaje vacio no se sabe y se dice",
          (r["total"]["vacio"], r["delegaciones"][0]["vacio"], r["visitas"][0][10], "sin_vacio" in r),
          (None, None, None, True))

op = OP.Operativo([DIA])
op.dia(DIA).come_partes([parte("P1", "Madrid")])
r = op.detalle_rutas("interno")["dias"][DIA]
comprueba("sin plan se dice, y quedan las visitas por delegacion",
          ("sin_dato" in r, r["visitas_deleg"], "pct" in r["total"]), (True, {"Madrid": 1}, False))

comprueba("la hora del parte", (OP.hora("2026-10-09 07:41:12"), OP.hora("2026-10-09T18:02"),
                                OP.hora("2026-10-09"), OP.hora(None)), ("07:41", "18:02", "", ""))

print("\nEl fichero de rutas guarda las cifras y solo una semana de listas")
viejo = {"dias": {"2026-08-01": {"total": {}, "visitas": [["X"]]},
                  "2026-08-02": {"total": {}, "no_visitados": [["X"]], "fuera": []}}}
fechas = [f"2026-10-{n:02d}" for n in range(1, 10)]
op = OP.Operativo(fechas)
for f in fechas:
    op.dia(f).come_plan([plan("P1", "Madrid", "R1")])
fr = op.detalle_rutas("interno", viejo)
comprueba("el dia viejo se queda", "2026-08-01" in fr["dias"], True)
comprueba("pero sin sus listas", "visitas" in fr["dias"]["2026-08-01"], False)
comprueba("ni las de antes, con su nombre viejo",
          ("no_visitados" in fr["dias"]["2026-08-02"], "fuera" in fr["dias"]["2026-08-02"]), (False, False))
comprueba("las listas, de los ultimos siete", sum("visitas" in v for v in fr["dias"].values()), 7)

print("\nFestivos: que tengan muchas menos visitas que un dia normal")
FEST = {"nacional": ["2026-10-12"], "delegaciones": {"Sevilla": ["2026-10-13"]}}
dias = {}
for f, mad, sev in [("2026-10-05", 100, 40), ("2026-10-06", 110, 42), ("2026-10-07", 90, 38),
                    ("2026-10-08", 100, 41), ("2026-10-09", 30, 40), ("2026-10-10", 5, 2),
                    ("2026-10-12", 10, 39), ("2026-10-13", 100, 3)]:
    dias[f] = {"visitas_deleg": {"Madrid": mad, "Sevilla": sev},
               "delegaciones": [{"delegacion": "Madrid", "previstas": 100},
                                {"delegacion": "Sevilla", "previstas": 40 if f != "2026-10-13" else 5}]}
c = {(x["fecha"], x["delegacion"]): x for x in OP.control_festivos(dias, FEST)}
comprueba("el nacional en Madrid, bien: 10 contra un normal de 100",
          (c[("2026-10-12", "Madrid")]["estado"], c[("2026-10-12", "Madrid")]["normal"]), ("bien", 100))
comprueba("pero con el plan entero: sin descontar", c[("2026-10-12", "Madrid")]["plan_sin_descontar"], True)
comprueba("Sevilla trabajo el nacional como un dia normal", c[("2026-10-12", "Sevilla")]["estado"],
          "festivo_con_visitas")
comprueba("el local de Sevilla, bien y con el plan descontado",
          (c[("2026-10-13", "Sevilla")]["estado"], c[("2026-10-13", "Sevilla")]["plan_sin_descontar"]),
          ("bien", False))
comprueba("el local de Sevilla no es festivo en Madrid", ("2026-10-13", "Madrid") in c, False)
comprueba("un laborable flojo sin festivo apuntado se ensena", c[("2026-10-09", "Madrid")]["estado"],
          "pocas_sin_festivo")
comprueba("el sabado no se mira", ("2026-10-10", "Madrid") in c, False)
comprueba("sin calendario, solo los laborables flojos",
          [x["estado"] for x in OP.control_festivos(dias, None)], ["pocas_sin_festivo", "pocas_sin_festivo", "pocas_sin_festivo"])
comprueba("con menos de tres dias normales no hay normal",
          OP.control_festivos({"2026-10-12": dias["2026-10-12"]}, FEST)[0]["estado"], "sin_normal")

print("\nFestivos: autonomicos por comunidad y locales por ciudad")
F2 = {"nacional": ["2026-10-12"],
      "autonomicos": {"Andalucía": ["2026-12-07"], "Cataluña": ["2026-09-11"]},
      "delegaciones": {"Andalucía - Cádiz": {"ciudad": "Cádiz", "comunidad": "Andalucía", "locales": ["2026-10-07"]},
                       "Cataluña - Cornella": {"ciudad": "Cornellà", "comunidad": "Cataluña", "locales": []},
                       "Viejo": ["2026-10-13"]}}
comprueba("nacional, autonomico y local de Cadiz",
          [OP.es_festivo(f, "Andalucía - Cádiz", F2) for f in ("2026-10-12", "2026-12-07", "2026-10-07", "2026-09-11")],
          ["nacional", "autonómico", "local", None])
comprueba("el de Cataluña, en Cornella", OP.es_festivo("2026-09-11", "Cataluña - Cornella", F2), "autonómico")
comprueba("la lista sola de antes sigue valiendo", OP.es_festivo("2026-10-13", "Viejo", F2), "local")
r = OP.resumen_festivos(F2)
comprueba("el resumen da a la pagina los dos por delegacion", r["delegaciones"]["Andalucía - Cádiz"],
          {"ciudad": "Cádiz", "comunidad": "Andalucía", "autonomico": ["2026-12-07"], "local": ["2026-10-07"]})
comprueba("una delegacion solo con autonomicos tambien sale", r["delegaciones"]["Cataluña - Cornella"]["autonomico"],
          ["2026-09-11"])

import datetime, json as _json, os as _os
REAL = _json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "festivos.json"), encoding="utf-8"))
todas = [f for v in REAL["autonomicos"].values() for f in v] + REAL["nacional"] + \
        [f for d in REAL["delegaciones"].values() for f in d["locales"]]
comprueba("config/festivos.json: todas las fechas son fechas", all(datetime.date.fromisoformat(f) for f in todas), True)
comprueba("cada delegacion con ciudad tiene su comunidad en autonomicos",
          [k for k, d in REAL["delegaciones"].items() if d["ciudad"] and d["comunidad"] not in REAL["autonomicos"]], [])
comprueba("cada delegacion con ciudad tiene sus dos locales",
          [k for k, d in REAL["delegaciones"].items() if d["ciudad"] and len(d["locales"]) != 2], [])
comprueba("cada comunidad, 12 dias con los 8 nacionales de entre semana o sabado",
          {c: len(set(v) | {f for f in REAL["nacional"] if datetime.date.fromisoformat(f).weekday() < 6})
           for c, v in REAL["autonomicos"].items()}, {c: 12 for c in REAL["autonomicos"]})

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("Todo pasa.")
