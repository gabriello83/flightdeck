"""
Revision de clientes (docs/59): sin planograma, sin tarifa por maquina, precio
distinto por maquina y los planogramas creados de una noche a otra.

    python3 infra/test_revision.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import revision as RV  # noqa: E402

fallos = 0


def comprueba(que, obtenido, esperado):
    global fallos
    ok = obtenido == esperado
    print(f"  {'ok   ' if ok else 'FALLO'} {que}" + ("" if ok else f": {obtenido!r} != {esperado!r}"))
    if not ok:
        fallos += 1


HOY = datetime.date(2026, 10, 19)


def maquina(mat, centro="500", canales=10, marcada=0, cliente="10", pdv=None, **extra):
    f = {"cod_cliente": cliente, "cliente": f"CLIENTE {cliente}", "cliente_activo": True,
         "num_centro": centro, "centro": f"CENTRO {centro}", "centro_activo": True,
         "delegacion": "Andalucía - Sevilla", "cod_pdv": pdv or f"P{mat}", "ubicacion": "Planta 1",
         "estado_pdv": 1, "matricula": mat, "estado_maquina": 1,
         "sin_planograma": marcada, "canales_con_articulo": canales,
         "tarifa_vending_cliente": 7, "telemetria": 0}
    f.update(extra)
    return f


print("Sin planograma: la regla del bloque de instalaciones")
censo = [maquina("A1"), maquina("A2", canales=0), maquina("A3", marcada=1),
         maquina("A3", marcada=1, pdv="PA3b"),
         maquina("A4", canales=0, centro_activo=False)]
sin = RV.sin_planograma(censo, HOY)
comprueba("sin canales con articulo y marcada; una vez cada maquina; la de baja no",
          sorted(sin), ["A2", "A3"])
comprueba("dice por que", (sin["A2"]["marcada"], sin["A3"]["marcada"]), (False, True))

print("\nPlanogramas creados, de una noche a otra")
e1 = RV.planogramas(None, censo, HOY - datetime.timedelta(days=1))
comprueba("la primera noche no hay con que comparar", e1["creados"], [])
censo2 = [maquina("A1"), maquina("A2", canales=14), maquina("A3", marcada=1)]
e2 = RV.planogramas(e1, censo2, HOY, usuarios={"A2": {"usuario": "mgarcia"}})
comprueba("la A2 tiene planograma hoy: creado ayer",
          [(c["matricula"], c["dia"], c["canales"], c.get("usuario")) for c in e2["creados"]],
          [("A2", "2026-10-18", 14, "mgarcia")])
e2b = RV.planogramas(e2, censo2, HOY)
comprueba("una segunda ejecucion el mismo dia compara con la noche de antes, no consigo misma",
          [c["matricula"] for c in e2b["creados"]], ["A2"])
censo3 = [maquina("A1"), maquina("A2", canales=14)]
e3 = RV.planogramas(e2b, censo3, HOY + datetime.timedelta(days=1))
comprueba("la que se retira sin planograma no es un planograma creado",
          [c["matricula"] for c in e3["creados"]], ["A2"])
e4 = RV.planogramas(e3, censo3, HOY + datetime.timedelta(days=RV.DIAS_CREADOS + 2))
comprueba("lo de hace mas de dos meses se olvida", e4["creados"], [])

print("\nEl usuario, del registro de actividad de VenCloud (M14)")
m14 = [{"origen": "maquina", "matricula": "A2", "accion": "U", "usuario": "jefe", "cambios": 9,
        "primera": "2026-10-18 08:00:00", "ultima": "2026-10-18 08:05:00"},
       {"origen": "canal", "matricula": "A2", "accion": "U", "usuario": "mgarcia", "cambios": 24,
        "primera": "2026-10-18 09:00:00", "ultima": "2026-10-18 09:40:00"},
       {"origen": "canal", "matricula": "A2", "accion": "U", "usuario": "antiguo", "cambios": 90,
        "primera": "2026-10-12 09:00:00", "ultima": "2026-10-12 09:40:00"}]
u = RV.usuarios_de(m14, "2026-10-18")
comprueba("manda quien toco los canales desde la noche anterior, no la ficha ni otro dia",
          u, {"A2": {"usuario": "mgarcia", "fecha": "2026-10-18 09:40:00"}})
e2u = RV.planogramas(e1, censo2, HOY, usuarios=m14)
comprueba("y llega al planograma creado",
          [(c["matricula"], c.get("usuario"), c.get("fecha")) for c in e2u["creados"]],
          [("A2", "mgarcia", "2026-10-18 09:40:00")])
comprueba("sin el informe, sin usuario",
          [c.get("usuario") for c in RV.planogramas(e1, censo2, HOY)["creados"]], [None])

print("\nSin tarifa y precio distinto, maquina a maquina")


def fila(mat, art, estado, nivel=None, tarifa="", asignada="", medios=None):
    return {"matricula": mat, "cod_pdv": "P" + mat, "ubicacion": "Planta 1", "cod_articulo": art,
            "articulo": "ART " + art, "ultima_carga": "2026-10-10", "nivel": nivel,
            "origen": None, "tarifa": tarifa, "asignada": asignada, "cambio_tarifa": "",
            "subvencion": False, "desde": "", "medios": medios or {}, "estado": estado}


mal = {"ef": {"tarifa": 1.0, "venta": {"precio": 1.2, "fecha": "2026-10-15", "fuente": "telemetria"}, "ok": False},
       "tc": {"tarifa": 1.1, "venta": {"precio": 0.8, "fecha": "2026-10-15", "fuente": "telemetria"}, "ok": False}}
bien = {"ef": {"tarifa": 1.0, "venta": {"precio": 1.0, "fecha": "2026-10-15", "fuente": "audit"}, "ok": True}}
detalle = {"500": {"num_centro": "500", "centro": "CENTRO 500", "cliente": "CLIENTE 10",
                   "cod_cliente": "10", "delegacion": "Andalucía - Sevilla",
                   "filas": [fila("A1", "1", "sin_tarifa", medios={"ef": {"venta": {"precio": 1.5}}}),
                             fila("A1", "2", "coincide", "estandar", "AIRBUS", "cliente", bien),
                             fila("A1", "3", "no_coincide", "estandar", "AIRBUS", "cliente", mal),
                             fila("A1", "4", "coincide", "pdv", medios=bien),
                             fila("A2", "1", "coincide", "centro", medios=bien),
                             fila("A2", "5", "sin_dato", "centro")]}}
fich = RV.calcula(censo2, detalle, e2, HOY)
st = fich["sin_tarifa"]
comprueba("solo la maquina con algun producto sin tarifa", [m["matricula"] for m in st], ["A1"])
comprueba("con cuantos le faltan, de cuantos", (st[0]["sin_tarifa"], st[0]["productos_total"]), (1, 4))
comprueba("el nivel que mas usa, y la tarifa estandar señalada con a quien esta asignada",
          (st[0]["nivel"], st[0]["estandar"]),
          ("estandar", [{"tarifa": "AIRBUS", "asignada": "cliente", "productos": 2}]))
comprueba("los productos sin tarifa con lo que cobra hoy",
          [(p["cod_articulo"], p["medios"]["ef"]["venta"]["precio"]) for p in st[0]["productos"]], [("1", 1.5)])
pd = fich["precio_distinto"]
comprueba("precio distinto: la A1, un producto de tres comprobados",
          [(m["matricula"], m["distintos"], m["comprobados"]) for m in pd], [("A1", 1, 3)])
comprueba("la diferencia maxima en valor absoluto, con su signo", pd[0]["max_diferencia"], -0.3)
comprueba("los creados de la pagina son los del perfil", [c["matricula"] for c in fich["creados"]], ["A2"])
comprueba("con usuario no se dice que falta", "sin_usuario" in fich, False)
comprueba("sin planograma del perfil", [m["matricula"] for m in fich["sin_planograma"]], ["A3"])
comprueba("el cuadrado: maquinas sin planograma y lo demas al lado",
          RV.cuadrado(fich, HOY), {"sin_planograma": 1, "creados_ayer": 1, "sin_tarifa": 1, "precio_distinto": 1})

print("\nSin maestro de tarifas se dice, no se enseña un cero")
fich = RV.calcula(censo2, None, None, HOY)
comprueba("sin tarifa dice por que no hay dato", "M10" in fich["sin_tarifa"]["sin_dato"], True)
comprueba("el cuadrado no lleva la cuenta de tarifas", RV.cuadrado(fich, HOY),
          {"sin_planograma": 1, "creados_ayer": 0})
comprueba("y sin el informe del usuario, se dice", "M14" in fich["sin_usuario"], True)

print("\nOtro perfil no ve los creados de una maquina que no es suya")
fich = RV.calcula([maquina("Z9")], {}, e2, HOY)
comprueba("ninguno", fich["creados"], [])

if fallos:
    print(f"\n{fallos} PRUEBAS FALLIDAS")
    sys.exit(1)
print("\nTodo pasa.")
