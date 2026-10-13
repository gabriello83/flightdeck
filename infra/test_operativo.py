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

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("Todo pasa.")
