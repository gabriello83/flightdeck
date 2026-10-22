"""
La pagina de rutas por areas: maquinas por recaudar, sin reponer, llamadas de
maquina vacia y quien hizo cada ruta (docs/67).

Cada caso es una trampa del dato de verdad: la recaudacion oficial que llega a
tandas, el parte de SYSTEM que no es visita, el festivo que no es laborable, el
mes sin recaudar que cuenta como cero.

    python3 infra/test_rutas.py
"""

import datetime
import sys

AQUI = __file__.rsplit("/", 1)[0]
sys.path.insert(0, AQUI)

import incidencias as IN  # noqa: E402
import rutas as RT  # noqa: E402

fallos = []


def comprueba(que, dado, esperado):
    ok = dado == esperado
    print(f"  {'ok   ' if ok else 'FALLO'} {que}" + ("" if ok else f": {dado!r} != {esperado!r}"))
    if not ok:
        fallos.append(que)


HOY = datetime.date(2026, 10, 20)          # ayer = lunes 19-oct
DL = "Madrid - Leganés"
FESTIVOS = {"nacional": ["2026-10-12"]}


def ficha(pdv, matricula, estado=1, delegacion=DL, clase=9):
    return {"cod_pdv": pdv, "matricula": matricula, "estado_pdv": estado, "delegacion": delegacion,
            "num_centro": "10", "centro": "CENTRO " + pdv, "cod_cliente": "C1", "clase_pdv": clase,
            "ubicacion": "Planta 1"}


def parte(pdv, recauda=0, empleado="ANA", ruta="R1", sistema=False):
    if sistema:
        return {"empleadoid": 0, "empleado": "SYSTEM", "tipo_parte": 2, "cod_pdv": pdv,
                "ruta": "SYSTEM", "hay_recaudacion": recauda, "delegacion": DL}
    return {"empleadoid": 7, "empleado": empleado, "tipo_parte": 0, "cod_pdv": pdv, "ruta": ruta,
            "hay_recaudacion": recauda, "delegacion": DL}


def carga(matricula, tipo="CM"):
    return {"matricula": matricula, "tipo_linea": tipo, "cantidad": 5}


def oficial(pdv, anio, mes, dia, euros, criterio=3):
    return {"cod_pdv": pdv, "anho": anio, "mes": mes, "dia": dia, "criterio_calculo": criterio,
            "imp_recaudado": euros, "imp_pago_bancario": 0}


print("\nLos meses y los laborables")
comprueba("los tres meses completos antes de enero", RT.meses_anteriores("2026-01"),
          ["2025-10", "2025-11", "2025-12"])
comprueba("los tres antes de octubre", RT.meses_anteriores("2026-10"), ["2026-07", "2026-08", "2026-09"])
# Despues del jueves 1 y hasta el lunes 19 de octubre: el 2, del 5 al 9, del 13
# al 16 y el 19 = 11 laborables. El 12 es festivo nacional: sin calendario, 12.
comprueba("sin fines de semana ni el festivo", RT.laborables_entre("2026-10-01", "2026-10-19", DL, FESTIVOS), 11)
comprueba("sin calendario, el 12 cuenta", RT.laborables_entre("2026-10-01", "2026-10-19", DL, None), 12)

print("\nRecaudar en el mes")
m = RT.Maquinas()
m.come("partes", [parte("A", recauda=1)], datetime.date(2026, 9, 10))
m.come("partes", [parte("B", recauda="1")], datetime.date(2026, 9, 11))
m.come("partes", [parte("B", recauda="1")], datetime.date(2026, 10, 6))
# Un parte de SYSTEM no es visita, aunque lleve la marca.
m.come("partes", [parte("C", recauda=1, sistema=True)], datetime.date(2026, 9, 12))
# D solo en la oficial, criterio 3, en julio: llega a tandas en octubre.
m.come("recaudacion", [oficial("A", 2026, 7, 8, 90.0), oficial("A", 2026, 9, 10, 60.0),
                       oficial("A", 2026, 9, 1, 3.0, criterio=1),
                       oficial("D", 2026, 7, 15, 30.0),
                       oficial("E", 2026, 8, 2, 5_000_000.0)], datetime.date(2026, 10, 2))
censo = [ficha("A", "MA"), ficha("B", "MB"), ficha("C", "MC"), ficha("D", "MD"),
         ficha("E", "ME"), ficha("Z", "MZ", estado=0)]
b = m.bloque(censo, None, FESTIVOS, HOY)
pr = {x["p"]: x for x in b["por_recaudar"]}
comprueba("faltan las recaudadas antes y no este mes", sorted(pr), ["A", "D"])
comprueba("de las que recaudan, una ya este mes", (b["control_maquinas"]["recaudan"], b["control_maquinas"]["recaudadas_mes"]), (3, 1))
comprueba("promedio: (90 + 0 + 60) / 3, sin el cobro diario", pr["A"]["pm"], 50.0)
comprueba("dos de los tres meses recaudada", pr["A"]["mr"], 2)
comprueba("la ultima recaudacion es la del parte", pr["A"]["rc"], "2026-09-10")
comprueba("D, solo con la oficial: 30 / 3", pr["D"]["pm"], 10.0)
comprueba("primero la que mas se espera", [x["p"] for x in b["por_recaudar"]], ["A", "D"])
comprueba("con oficial no hay aviso", b["control_maquinas"]["sin_oficial"], None)
comprueba("la del contador roto no recauda nada", "E" in pr, False)

print("\nSin reponer")
m = RT.Maquinas()
m.come("lineas", [carga("MA"), carga("MB", tipo="RC")], datetime.date(2026, 9, 29))
m.come("lineas", [carga("MC")], datetime.date(2026, 9, 30))
m.come("lineas", [carga("MD")], datetime.date(2026, 10, 2))
b = m.bloque([ficha("A", "MA"), ficha("B", "MB"), ficha("C", "MC"), ficha("D", "MD")], None, FESTIVOS, HOY)
sr = {x["p"]: x["lab"] for x in b["sin_reponer"]}
comprueba("mas de 12 laborables: desde el 29-sep son 13, desde el 30-sep 12", sr, {"A": 13})
comprueba("una retirada no es reponer: B nunca repuesta",
          [x["p"] for x in b["nunca_repuestas"]], ["B"])
comprueba("la ultima carga viaja", b["sin_reponer"][0]["rp"], "2026-09-29")
comprueba("sin partes se dice", b["control_maquinas"]["sin_partes"] is not None, True)
comprueba("con lineas no hay aviso", b["control_maquinas"]["sin_lineas"], None)

print("\nLlamadas de maquina vacia")
inc = IN.Incidencias()
base = {"tipo_estado": 1, "estado": 1, "matricula": "MA", "delegacion": DL, "centro": "X", "serie": "S"}
inc.come_foto([
    dict(base, id=1, numero=1, cod_operacion="S010", operacion="Reponer distribuidor automatico",
         apertura="2026-10-15 09:00:00"),
    dict(base, id=2, numero=2, cod_operacion="C016", operacion="SNACK/BEBIDA - SELECCIONES VACIAS",
         apertura="2026-10-16 10:00:00", tipo_estado=9, estado=99),
    dict(base, id=3, numero=3, cod_operacion="T04", operacion="CAFÉ - No sale producto",
         apertura="2026-10-16 11:00:00"),
    dict(base, id=4, numero=4, cod_operacion="S010", operacion="Reponer distribuidor automatico",
         apertura="2026-10-20 08:00:00"),
    dict(base, id=5, numero=5, cod_operacion="S010", operacion="Reponer", matricula="00SE0000",
         apertura="2026-10-15 08:00:00"),
])
b = RT.Maquinas().bloque([], inc, FESTIVOS, HOY)
comprueba("S010 y C016, hasta ayer, sin la ficticia", [x["x"] for x in b["llamadas"]], ["S-2", "S-1"])
comprueba("abierta y cerrada, de la foto", [x["a"] for x in b["llamadas"]], [0, 1])
comprueba("la fuente es M13", b["llamadas_fuente"].startswith("M13"), True)
inc = IN.Incidencias()
inc.come_tareas([dict(base, id=1, numero=1, cod_operacion="S010", operacion="Reponer distribuidor automatico",
                      fecha_alta="2026-10-14 00:00:00")])
b = RT.Maquinas().bloque([], inc, FESTIVOS, HOY)
comprueba("sin M13 no se sabe si sigue abierta", [(x["f"], x["a"]) for x in b["llamadas"]], [("2026-10-14", None)])

print("\nQuien hizo cada ruta, y las areas")
m = RT.Maquinas()
m.come("partes", [parte("A", empleado="ANA"), parte("B", empleado="LUIS"), parte("C", empleado="ana b", ruta=""),
                  parte("D", sistema=True)], datetime.date(2026, 10, 19))
b = m.bloque([], None, FESTIVOS, HOY)
comprueba("los reponedores de cada ruta, sin SYSTEM",
          b["quien"]["2026-10-19"], {f"{DL}\u0001R1": ["ANA", "LUIS"], f"{DL}\u0001Sin ruta": ["ana b"]})
comprueba("la zona de la delegacion", b["zonas"], {DL: "Centro"})
m.come("partes", [parte("A")], datetime.date(2026, 6, 1))
comprueba("solo los dias que se guardan", sorted(m.bloque([], None, FESTIVOS, HOY)["quien"]), ["2026-10-19"])

print()
if fallos:
    print(f"{len(fallos)} fallo(s).")
    sys.exit(1)
print("Todo bien.")
