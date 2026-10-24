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

print("\nLa pagina de furgonetas (docs/58): la flota, sus visitas y sus km")


def ficha(i, mat, nombre="CRAFTER", deleg="Madrid", activo=True, obsoleto=False, cod=1):
    return {"id": i, "cod_vehiculo": cod, "denominacion": nombre, "matricula": mat,
            "activo": activo, "obsoleto": obsoleto, "delegacion": deleg}


def jornada(vid, ini, fin, cierre="2026-10-09T14:00:00"):
    return {"vehiculoid": vid, "kminiciales": ini, "kmfinales": fin, "fechafin": cierre}


MAESTRO = [ficha(1, "1111AAA", "CRAFTER - Ana"),
           ficha(2, "1111AAA", "MASTER - Ruta 1"),             # dos fichas, una furgoneta
           ficha(3, "2222BBB", "CADDY", "Sevilla"),
           ficha(4, "3333CCC", "CRAFTER vieja", activo=False),  # de baja
           ficha(5, "4444DDD", "Ficticio RTVE"),                # ficticio de un sitio fijo
           ficha(6, "xxxx-xxx", "Sin vehiculo"),
           ficha(7, "", "Nuevo operador"),
           ficha(8, "SYSTEM", "SYSTEM", cod=-99),
           ficha(9, "1234XXX", "Vehiculo Test"),
           ficha(10, "5555EEE", "JUMPER", "Sevilla"),
           ficha(11, "2222BBB", "CADDY antigua", "Sevilla", activo=False)]
comprueba("que es una furgoneta del maestro",
          [OP.es_furgoneta(f) for f in MAESTRO],
          [True, True, True, False, False, False, False, False, False, True, False])
comprueba("los km de un dia: se suman las jornadas bien anotadas",
          OP.km_del_dia([(1000, 1040, True), (2000, 2010, True)]), [50, 2, ""])
comprueba("cuentakilometros de 1 o 2: no hay km, y se dice por que",
          OP.km_del_dia([(1, 2, True)]), [None, 1, "sin anotar"])
comprueba("jornada abierta y final por debajo del inicio",
          OP.km_del_dia([(5000, 0, False), (9000, 100, True)]), [None, 2, "mal anotado · sin cerrar"])
comprueba("una bien y otra abierta: los km de la buena, y lo que falta",
          OP.km_del_dia([(1000, 1100, True), (1100, 0, False)]), [100, 2, "sin cerrar"])
comprueba("cero km es un dato, no un hueco", OP.km_del_dia([(1000, 1000, True)]), [0, 1, ""])
comprueba("la misma jornada dos veces (dos rutas) cuenta una",
          OP.km_del_dia([(43794, 43836, True, 1), (43794, 43836, True, 2)]), [42, 2, ""])
comprueba("tramos que se pisan se juntan; dos cuentakilometros distintos se suman",
          OP.km_del_dia([(100, 150, True), (140, 160, True), (9000, 9010, True)]), [70, 3, ""])
comprueba("el area sale de la delegacion",
          [OP.zona_de(d) for d in ("Andalucía - Cádiz", "Madrid - Hospital La Paz", "Cataluña - Cornella",
                                   "Serunion Vending - CENTRAL")], ["Sur", "Centro", "Cataluña", "Otra zona"])

op = OP.Operativo([DIA])
op.desde = "2026-10-01"
d = op.dia(DIA)
partes = [dict(parte("P1", "Madrid", "R1"), vehiculo="1111AAA"),
          dict(parte("S1", "Sevilla", "S", "Luis"), vehiculo="2222BBB "),
          dict(parte("S2", "Sevilla", "S", "Rosa"), vehiculo="xxxx-xxx"),
          dict(parte("R1", "Madrid", "R"), vehiculo="4444DDD"),
          sistema("MX")]
d.come_partes(partes)
op.come_visitas_vehiculo(DIA, partes)
op.come_visitas_vehiculo("2026-10-03", [dict(parte("S1", "Sevilla", "S"), vehiculo="5555EEE")])
# La SAT: el fichero va por la fecha de la averia; el dia es el de `inicio`.
op.come_visitas_sat([{"vehiculo": "2222BBB", "inicio": "2026-10-07 10:00:00"},
                     {"vehiculo": "", "inicio": "2026-10-07 11:00:00"},
                     {"vehiculo": "2222BBB", "inicio": "1900-01-01 00:00:00"}])
op.come_jornadas(DIA, [jornada(1, 1000, 1005), jornada(2, 2000, 2010),   # dos fichas de 1111AAA
                       jornada(11, 7000, 7500),                           # la ficha de baja de 2222BBB
                       jornada(5, 1, 1),                                  # ficticio: fuera
                       jornada(10, 1, 2)])
op.come_jornadas("2026-10-08", [jornada(1, 900, 1000, "1900-01-01T00:00:00")])
fu = op.detalle_furgonetas("interno", None, MAESTRO, {})
comprueba("la flota: activas, una por matricula, sin ficticias ni de baja",
          [(x["m"], x["n"], x["d"]) for x in fu["flota"]],
          [("1111AAA", "CRAFTER - Ana · MASTER - Ruta 1", "Madrid"),
           ("2222BBB", "CADDY", "Sevilla"), ("5555EEE", "JUMPER", "Sevilla")])
comprueba("los dias con visita de cada una, tambien de la SAT, sin el ficticio",
          fu["visitas"], {"1111AAA": [DIA], "2222BBB": ["2026-10-07", DIA], "5555EEE": ["2026-10-03"]})
comprueba("los km del dia, juntando las fichas de una matricula",
          fu["km"][DIA], {"1111AAA": [15, 2, ""], "2222BBB": [500, 1, ""], "5555EEE": [None, 1, "sin anotar"]})
comprueba("la jornada abierta de otro dia", fu["km"]["2026-10-08"], {"1111AAA": [None, 1, "sin cerrar"]})
comprueba("los umbrales viajan en el fichero", fu["umbrales_km"], {"min": 10, "max": 400})
comprueba("los dias: desde el primero leido hasta el ultimo publicado",
          (fu["dias"][0], fu["dias"][-1], fu["desde"], fu["ultimo_dia"]), ("2026-10-01", DIA, "2026-10-01", DIA))
comprueba("el cuadrado no cambia: furgonetas distintas con visita, sin las de relleno",
          op.fichero("interno")["dias"][DIA]["furgonetas"],
          {"activas": 3, "visitas": 4, "visitas_sin_vehiculo": 1,
           # Y la lista, para contar las distintas de varios dias (docs/66).
           "vehiculos": ["1111AAA", "2222BBB", "4444DDD"]})

fm = op.furgonetas_por_mes({"dias": ["2026-09-30"], "km": {"2026-09-30": {"1111AAA": [5, 1, ""]}},
                            "visitas": {"1111AAA": ["2026-09-30"]}}, lambda mes: None, MAESTRO, {},
                           {"2026-10-09": {"3": [[1, 2, True]]}})
comprueba("la historia de furgonetas (docs/75): los km y las que visitaron, por dia",
          (fm["2026-10"]["dias"][DIA]["km"]["2222BBB"], fm["2026-10"]["dias"][DIA]["v"]),
          ([500, 1, ""], ["1111AAA", "2222BBB"]))
comprueba("los dias del fichero de la pagina pasan a su mes",
          fm["2026-09"]["dias"]["2026-09-30"], {"km": {"1111AAA": [5, 1, ""]}, "v": ["1111AAA"]})
comprueba("sin maestro de vehiculos no se escribe nada",
          op.furgonetas_por_mes(None, lambda mes: None, None), {})
op_h = OP.Operativo(["2025-01-02"], historico=True)
fm = op_h.furgonetas_por_mes(None, lambda mes: None, MAESTRO, {},
                             {"2025-01-02": {"1": [[1000, 1100, True, 7]]}})
comprueba("en un relleno, los km salen de la historia de jornadas",
          fm["2025-01"]["dias"]["2025-01-02"], {"km": {"1111AAA": [100, 1, ""]}, "v": []})

op_sev = OP.Operativo([DIA])
op_sev.dia(DIA)
fa = op_sev.detalle_furgonetas("ope-sevilla", None, MAESTRO, {"delegaciones": ["Sevilla"]})
comprueba("un perfil de delegacion ve las suyas", [x["m"] for x in fa["flota"]], ["2222BBB", "5555EEE"])
op_cli = OP.Operativo([DIA])
op_cli.come_visitas_vehiculo(DIA, [dict(parte("P1", "Madrid", "R1"), vehiculo="1111AAA")])
op_cli.come_jornadas(DIA, [jornada(1, 1000, 1005), jornada(3, 100, 200)])
op_cli.dia(DIA)
fc = op_cli.detalle_furgonetas("cli", None, MAESTRO, {"clientes": ["AIRBUS"]})
comprueba("uno acotado por clientes, las que visitaron su ambito",
          ([x["m"] for x in fc["flota"]], list(fc["km"][DIA])), (["1111AAA"], ["1111AAA"]))

HISTORIA = {"2024-12-31": {"1": [[100, 900, True, 7]]},                 # antes de KM_DESDE
            "2025-01-02": {"1": [[1000, 1100, True, 7]], "2": [[2000, 2050, True, 8]]},
            "2025-06-01": {"1": [[1, 2, True, 9]], "4": [[100, 200, True, 9]]},  # sin anotar; 4 es de baja
            "2026-10-08": {"10": [[500, 530, True, 9]]},
            "2026-10-10": {"10": [[530, 999, True, 9]]}}                    # despues del ultimo dia
RUTAS = [{"ruta": "Ruta 1", "vehiculo": "1111AAA", "reponedor_titular": "Ana", "activa": True},
         {"ruta": "Ruta vieja", "vehiculo": "1111AAA", "reponedor_titular": "Pepe", "activa": False}]
EMPLEADOS = [{"id": 9, "empleado": "Luis Técnico"}]
fh = op.detalle_furgonetas("interno", None, MAESTRO, {}, HISTORIA, RUTAS, EMPLEADOS)
por = {x["m"]: x for x in fh["flota"]}
comprueba("km acumulados desde KM_DESDE hasta el ultimo dia, juntando fichas",
          ({m: por[m]["km"] for m in por}, fh["km_desde"]),
          ({"1111AAA": 150, "2222BBB": 0, "5555EEE": 30}, "2025-01-01"))
comprueba("y las jornadas sin km de ese tiempo", por["1111AAA"]["skm"], 1)
comprueba("la persona: el titular de la ruta activa con esa furgoneta",
          (por["1111AAA"]["p"], por["1111AAA"]["pr"], por["1111AAA"]["r"]), ("Ana", "ruta", "Ruta 1"))
comprueba("sin ruta, quien la llevo en su ultima jornada, y se dice",
          (por["5555EEE"]["p"], por["5555EEE"]["pr"]), ("Luis Técnico", "jornada"))
comprueba("sin nada, vacia", (por["2222BBB"]["p"], por["2222BBB"]["pr"]), ("", ""))
comprueba("sin historia, los km acumulados no son un cero", (fu["flota"][0]["km"], fu["km_desde"]), (None, None))

sinm = op.detalle_furgonetas("interno", None, None, {})
comprueba("sin maestro de vehiculos se dice, no sale una flota vacia",
          (sinm["sin_dato"] == OP.SIN_VEHICULOS, sinm["flota"]), (True, []))

viejo = {"ultimo_dia": "2026-10-08", "desde": "2026-06-01",
         "visitas": {"2222BBB": ["2026-04-01", "2026-09-20"], "9999ZZZ": ["2026-09-01"]},
         "km": {"2026-07-01": {"1111AAA": [5, 1, ""]}, "2026-10-02": {"1111AAA": [80, 1, ""]},
                DIA: {"1111AAA": [1, 1, ""]}},
         "dias": {"2026-10-08": {"activas": 5, "vehiculos": []}}}      # el fichero de antes
op2 = OP.Operativo([DIA])
op2.desde = "2026-10-05"
op2.dia(DIA)
op2.come_jornadas(DIA, [jornada(1, 1000, 1005)])
fu = op2.detalle_furgonetas("interno", viejo, MAESTRO, {})
comprueba("acumula las visitas de antes, hasta DIAS_VISITAS",
          fu["visitas"]["2222BBB"], ["2026-09-20"])
comprueba("y las de una furgoneta que ya no esta en la flota se sueltan", "9999ZZZ" in fu["visitas"], False)
comprueba("desde el primer dia que se llego a leer", fu["desde"], "2026-06-01")
comprueba("los km de antes se quedan, y el dia recalculado sustituye",
          (fu["km"]["2026-10-02"], fu["km"][DIA]), ({"1111AAA": [80, 1, ""]}, {"1111AAA": [5, 1, ""]}))
comprueba("hasta DIAS_GUARDADOS dias", ("2026-07-01" in fu["km"], len(fu["dias"])),
          (False, OP.DIAS_GUARDADOS))

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

print("\nPor delegacion (docs/66): cifras que se suman, para el filtro de area y delegacion")
op = OP.Operativo([DIA])
op.come_censo([
    {"cod_pdv": "P1", "estado_pdv": 1, "matricula": "M1", "telemetria": 40, "delegacion": "Madrid"},
    {"cod_pdv": "P2", "estado_pdv": 1, "matricula": "M2", "telemetria": 40, "delegacion": "Sur - Sevilla"},
])
op.come_sat([{"id": 1, "matricula": "M1", "cod_operacion": "A01", "tipo_tarea": "A", "delegacion": "Madrid"}])
op.come_sat_eventos([{"averia_id": 1, "estado": 0, "fecha": f"{DIA} 08:00:00"},
                     {"averia_id": 1, "estado": 99, "fecha": f"{DIA} 09:00:00"}])
d = op.dia(DIA)
d.come_partes([dict(visita("P1", "1111AAA", "M1"), delegacion="Madrid"),
               dict(visita("P2", "1111AAA", "M2"), delegacion="Sur - Sevilla"),
               dict(visita("P2", "2222BBB", "M2"), delegacion="Sur - Sevilla"),
               sistema("M2")])
d.come_plan([{"cod_pdv": "P1", "delegacion": "Madrid"}, {"cod_pdv": "P3", "delegacion": "Madrid"},
             {"cod_pdv": "P2", "delegacion": "Sur - Sevilla"}])
d.come_lineas([{"tipo_linea": "CM", "cantidad": 4, "etiq_canal": "11", "matricula": "M1",
                "delegacion": "Madrid"}], {"M1": 9})
c = op.cuadrados_del_dia(d)
por = c["por_delegacion"]
comprueba("rutas de Madrid: 1 de 2", (por["rutas"]["Madrid"]["previstas"], por["rutas"]["Madrid"]["hechas"]), (2, 1))
comprueba("la furgoneta que paso por dos delegaciones sale en las dos",
          (por["furgonetas"]["Madrid"]["vehiculos"], por["furgonetas"]["Sur - Sevilla"]["vehiculos"]),
          (["1111AAA"], ["1111AAA", "2222BBB"]))
comprueba("y en el total, una vez", c["furgonetas"]["vehiculos"], ["1111AAA", "2222BBB"])
comprueba("la averia, en su delegacion", por["averias"], {"Madrid": {"cerradas": 1, "a_tiempo": 1}})
comprueba("telemetria: la de Sevilla mando su lectura",
          por["telemetria"], {"Madrid": {"auditables": 1, "con_dex": 0},
                              "Sur - Sevilla": {"auditables": 1, "con_dex": 1}})
comprueba("reposicion de Madrid", por["reposiciones"]["Madrid"]["unidades"], 4.0)
comprueba("puntos de venta por delegacion en la foto",
          op.foto["pdvs"]["por_delegacion"]["Madrid"], {"activos": 1, "maquinas": 1})
f = op.fichero("interno")
comprueba("el fichero lleva el area de cada delegacion", f["zonas"], {"Madrid": "Centro", "Sur - Sevilla": "Otra zona"})

print("\nEl relleno historico cierra cada dia y no pisa lo que sabe mejor la noche")
op = OP.Operativo([DIA], historico=True)
op.dia(DIA).come_partes([visita("P1")])
op.cierra(DIA)
comprueba("el dia cerrado ya no se abre", op.dia(DIA), None)
f = op.fichero("interno", {"generado": "antes", "foto": {"pdvs": {"activos": 7}},
                           "dias": {DIA: {"telemetria": {"pct": 50.0}}, "2025-01-02": {"x": 1}}})
comprueba("la telemetria de la noche se queda", f["dias"][DIA]["telemetria"], {"pct": 50.0})
comprueba("la foto de la noche se queda", f["foto"], {"pdvs": {"activos": 7}})
comprueba("los dias viejos salen del fichero y quedan en su mes",
          (f["primer_dia"], "2025-01-02" in f["dias"], f["meses_dias"]["2025-01"]), ("2025-01-02", False, [2]))

print("\nLa historia, un fichero por mes (docs/75): un mes cerrado no se reescribe")
op = OP.Operativo(["2025-03-04"], historico=True)
op.dia("2025-03-04").come_partes([visita("P1")])
op.cierra("2025-03-04")
leidos = []
def leer(mes):
    leidos.append(mes)
    return {"2025-03": {"mes": "2025-03", "dias": {"2025-03-03": {"x": 1},
                                                   "2025-03-04": {"telemetria": {"pct": 9.0}}}},
            "2026-10": {"mes": "2026-10", "dias": {"2026-10-01": {"y": 1}}}}.get(mes)
anterior = {"dias": {"2026-10-01": {"y": 1}, "2026-10-02": {"y": 2}, "2026-09-30": {"z": 1}}}
h = op.dias_por_mes(anterior, leer)
comprueba("el mes del relleno, con el dia nuevo y el que ya tenia",
          sorted(h["2025-03"]["dias"]), ["2025-03-03", "2025-03-04"])
comprueba("sin pisar la telemetria que escribio la noche",
          h["2025-03"]["dias"]["2025-03-04"]["telemetria"], {"pct": 9.0})
comprueba("los dias del fichero que faltan en su mes pasan a el",
          (sorted(h["2026-10"]["dias"]), sorted(h["2026-09"]["dias"])),
          (["2026-10-01", "2026-10-02"], ["2026-09-30"]))
leidos.clear()
h = OP.Operativo([]).dias_por_mes({"dias": {"2026-10-01": {"y": 1}}}, leer)
comprueba("un mes que ya lo tiene todo no se vuelve a escribir", (h, leidos), ({}, ["2026-10"]))
f = op.fichero("interno", anterior, None, op.dias_por_mes(anterior, leer))
comprueba("el fichero dice que dias tiene cada mes",
          (f["meses_dias"]["2025-03"], f["meses_dias"]["2026-10"], f["primer_dia"], f["ultimo_dia"]),
          ([3, 4], [1, 2], "2025-03-03", "2026-10-02"))
comprueba("y solo lleva los ultimos dias", sorted(f["dias"]), ["2026-09-30", "2026-10-01", "2026-10-02"])
comprueba("sin censo, la telemetria dice por que",
          OP.Operativo([DIA], historico=True).telemetria_vencloud(OP.DiaOperativo(DIA))["sin_dato"],
          OP.SIN_CENSO_HISTORICO)

print("\nPor centro (docs/72): el filtro de cliente y centro, un fichero por mes")
op = OP.Operativo([DIA])
op.ficha_de = {"100": {"nombre": "Getafe", "cliente": "AIRBUS", "delegacion": "Madrid"}}.get
op.come_censo([
    {"cod_pdv": "P1", "estado_pdv": 1, "matricula": "M1", "telemetria": 40, "num_centro": "100"},
    {"cod_pdv": "P2", "estado_pdv": 1, "matricula": "M2", "telemetria": 40, "num_centro": "200"},
])
op.come_sat([{"id": 1, "matricula": "M1", "cod_operacion": "A01", "tipo_tarea": "A", "num_centro": "100"}])
op.come_sat_eventos([{"averia_id": 1, "estado": 0, "fecha": f"{DIA} 08:00:00"},
                     {"averia_id": 1, "estado": 99, "fecha": f"{DIA} 09:00:00"}])
d = op.dia(DIA)
d.come_partes([dict(visita("P1", "1111AAA", "M1"), num_centro="100"),
               dict(visita("P2", "1111AAA", "M2"), num_centro="200"),
               dict(visita("P9", "xxxx-xxx", "M2"), num_centro="200"),
               sistema("M2")])
d.come_plan([{"cod_pdv": "P1", "num_centro": "100"}, {"cod_pdv": "P3", "num_centro": "100"}])
d.come_lineas([{"tipo_linea": "CM", "cantidad": 4, "etiq_canal": "11", "matricula": "M1",
                "num_centro": "100"}], {"M1": 9})


class _Serie:  # lo que pon_venta lee de un dia de la serie partido por centro
    venta_importe, venta_unidades, venta_maquinas, venta_fuente, venta_imposibles = 30.0, 20.0, {"M1", "M2"}, "telemetria", 0

    class por_centro:
        c = {"100": type("C", (), {"venta_importe": 10.0, "venta_unidades": 8.0, "venta_maquinas": {"M1"}})(),
             "200": type("C", (), {"venta_importe": 20.0, "venta_unidades": 12.0, "venta_maquinas": {"M2"}})()}


d.pon_venta(_Serie)
pc = op.centros_del_dia(DIA, op.por_centro(d))
comprueba("rutas por centro: previstas, hechas, fuera, visitas",
          pc["rutas"], {"100": [2, 1, 0, 1], "200": [0, 0, 2, 2]})
comprueba("furgonetas por centro, con sus matriculas", pc["furgonetas"]["200"], [2, 1, ["1111AAA"]])
comprueba("venta por centro: importe, unidades, maquinas", pc["ventas"], {"100": [10.0, 8.0, 1], "200": [20.0, 12.0, 1]})
comprueba("sin la funcion de delegacion, la venta por centro sale igual", d.venta_deleg, None)
comprueba("reposicion por centro", pc["reposiciones"], {"100": [4.0, 0.0, {"Snack": 4.0}]})
comprueba("telemetria por centro: auditables y con lectura", pc["telemetria"], {"100": [1, 0], "200": [1, 1]})
comprueba("la averia, en su centro", pc["averias"], {"100": [1, 1]})
comprueba("puntos de venta por centro en la foto", op.foto["pdvs"]["por_centro"], {"100": [1, 1], "200": [1, 1]})
_suma = lambda k, i: sum(x[i] for x in pc[k].values())
comprueba("los centros suman lo mismo que el dia",
          (_suma("rutas", 0), _suma("rutas", 1), _suma("ventas", 0), _suma("telemetria", 1)),
          (2, 1, 30.0, 1))
meses = op.centros_por_mes(lambda mes: {"mes": mes, "dias": {"2026-10-01": {"rutas": {"100": [1, 1, 0, 1]}}}})
comprueba("un fichero por mes, con los dias de antes", (list(meses), sorted(meses["2026-10"]["dias"])),
          (["2026-10"], ["2026-10-01", DIA]))
f = op.fichero("interno", None, meses)
comprueba("el informe dice que meses tienen reparto", f["meses_centros"], ["2026-10"])
comprueba("y la ficha de cada centro; el que no esta en el mapa, por su numero",
          f["centros"], {"100": {"n": "Getafe", "c": "AIRBUS", "d": "Madrid"}, "200": {"n": "200", "c": "", "d": ""}})
comprueba("sin meses, se queda con las fichas y los meses de antes",
          (lambda x: (x["centros"], x["meses_centros"]))(
              op.fichero("interno", {"centros": {"9": {"n": "X"}}, "meses_centros": ["2026-09"]})),
          ({"9": {"n": "X"}}, ["2026-09"]))

op = OP.Operativo([DIA], historico=True)
op.dia(DIA).come_partes([dict(visita("P1"), num_centro="100")])
op.cierra(DIA)
meses = op.centros_por_mes(lambda mes: {"dias": {DIA: {"telemetria": {"100": [3, 3]}}}})
comprueba("el relleno no pisa la telemetria por centro de la noche",
          (meses["2026-10"]["dias"][DIA]["telemetria"], meses["2026-10"]["dias"][DIA]["furgonetas"]["100"][0]),
          ({"100": [3, 3]}, 1))

# Las areas del navegador (app/comun/areas.js, docs/70) son las mismas que zona_de.
import json as _json, os, re
_txt = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "comun", "areas.js"), encoding="utf-8").read()
_zonas = _json.loads(re.search(r"const ZONAS = (\[.*?\]);", _txt, re.S).group(1))
comprueba("las areas de la web son las de zona_de", [tuple(z) for z in _zonas], [tuple(z) for z in OP.ZONAS])

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("Todo pasa.")
