"""
La pagina de incidencias: las cuentas de cada fila (docs/56).

Cada caso de aqui sale del dato de verdad: la operacion con el tipo de maquina
delante, la nota que dice «caducado» en una tarea de otra cosa, el cierre sin
hora, el preventivo que no es una incidencia, la devolucion con datos del
cliente en la nota.

    python3 infra/test_incidencias.py
"""

import datetime
import sys

AQUI = __file__.rsplit("/", 1)[0]
sys.path.insert(0, AQUI)

import incidencias as IN  # noqa: E402

fallos = []


def comprueba(que, dado, esperado):
    ok = dado == esperado
    print(f"  {'ok   ' if ok else 'FALLO'} {que}" + ("" if ok else f": {dado!r} != {esperado!r}"))
    if not ok:
        fallos.append(que)


HOY = datetime.date(2026, 10, 16)


def tarea(ident, op="CAFÉ - Distribuidor fuera de servicio", cod="T08", **kw):
    t = {"id": ident, "serie": "A", "numero": 70000 + ident, "fecha_alta": "2026-10-10",
         "tipo_tarea": "A", "tipo_estado": 1, "estado": 1, "cod_operacion": cod, "operacion": op,
         "categoria": "AVERIAS TECNICAS", "matricula": "24CE4820", "num_centro": 500073,
         "centro": "INDUSTRIA DEL CURTIDO, S.A.", "cod_cliente": 32072, "cliente": "INDUSTRIAS DEL CURTIDO",
         "delegacion": "Levante - Valencia", "tecnico_asignado": "Javier", "titulo": "",
         "apertura": "2026-10-10 08:00:00", "cierre": None}
    t.update(kw)
    return t


def m(t, texto=""):
    return IN.marcas(t, texto)


print("Las marcas, por la operacion y por el texto")
comprueba("fuera de servicio: tecnica y bloqueante", m(tarea(1)), IN.TECNICA | IN.BLOQUEANTE)
comprueba("con el tipo de maquina delante tambien",
          m(tarea(1, "SNACK/BEBIDA - Distribuidor fuera de servicio", "C06")) & IN.BLOQUEANTE, IN.BLOQUEANTE)
comprueba("grupo de cafe: tecnica, no bloqueante", m(tarea(1, "CAFÉ - Grupo café averiado", "T31")),
          IN.TECNICA)
comprueba("devolucion por transferencia", m(tarea(1, "DEVOLUCION - Transferencia Bancaria", "D01")),
          IN.DEVOLUCION)
comprueba("reponer", m(tarea(1, "Reponer distribuidor automatico", "S010")) & IN.REPOSICION, IN.REPOSICION)
comprueba("caducado por la operacion", m(tarea(1, "SNACK/BEBIDA - Producto caducado", "C16")) & IN.CADUCADO,
          IN.CADUCADO)
comprueba("caducado por la nota", m(tarea(1, "OTRO", "S012"), "el yogur está CADUCADO") & IN.CADUCADO,
          IN.CADUCADO)
comprueba("insectos por la operacion", m(tarea(1, "LIMPIEZA - Insectos", "C20")) & IN.HIGIENE, IN.HIGIENE)
comprueba("hormigas por la nota", m(tarea(1, "OTRO", "S012"), "hay hormigas") & IN.HIGIENE, IN.HIGIENE)
comprueba("serie E: solicitud especial", m(tarea(1, tipo_tarea="E")) & IN.ESPECIAL, IN.ESPECIAL)

print("\nLa zona sale del nombre de la delegacion")
comprueba("Madrid es Centro", IN.zona_de("Madrid - Leganes"), "Centro")
comprueba("Andalucia con y sin acento es Sur", (IN.zona_de("Andalucia - Sevilla"), IN.zona_de("Andalucía - Cádiz")),
          ("Sur", "Sur"))
comprueba("Cataluña", IN.zona_de("Cataluña - Cornella"), "Cataluña")
comprueba("la central no es ninguna", IN.zona_de("Serunion Vending - CENTRAL"), IN.OTRA_ZONA)

print("\nCon la foto (M13): el estado de hoy")
inc = IN.Incidencias()
inc.come_foto([
    tarea(1, tipo_estado=9, estado=99, cierre="2026-10-10 20:00:00"),
    tarea(2, tipo_estado=9, estado=99, cierre=None, fecha_fin="2026-10-12"),
    tarea(3, titulo="no sale café", ultima_nota="vuelve a fallar", ubicacion="Comedor", cod_pdv="C01502"),
    tarea(4, "DEVOLUCION - Transferencia Bancaria", "D01", titulo="IBAN ES00 0000"),
    tarea(5, "Preventivo Electrodomésticos Airbus (Interno)", "8888888"),
    tarea(6, matricula="00SE0000"),
])
f = inc.fichero("interno", HOY)
por = {x["n"]: x for x in f["incidencias"]}
comprueba("al dia", f["estado_al_dia"], True)
comprueba("sin el preventivo ni la ficticia", sorted(por), ["A-70001", "A-70002", "A-70003", "A-70004"])
comprueba("cerrada con hora: 12 horas", (por["A-70001"]["x"], por["A-70001"]["h"]), ("2026-10-10 20:00", 12.0))
comprueba("cerrada sin evento: la fecha, sin horas", (por["A-70002"]["x"], "h" in por["A-70002"]),
          ("2026-10-12", False))
comprueba("abierta: sin cierre, con texto, ubicacion y punto de venta",
          ("x" in por["A-70003"], por["A-70003"]["tx"], por["A-70003"]["u"], por["A-70003"]["p"]),
          (False, "no sale café · vuelve a fallar", "Comedor", "C01502"))
comprueba("la devolucion abierta no lleva el texto", "tx" in por["A-70004"], False)
comprueba("el centro va por indice", f["centros"][por["A-70003"]["c"]][:2], ["500073", "INDUSTRIA DEL CURTIDO, S.A."])
comprueba("la zona de cada delegacion viaja", f["zonas"], {"Levante - Valencia": "Levante"})
comprueba("arranca en ayer", f["ultimo_dia"], "2026-10-15")

print("\nLos eventos que la foto le pasa al cuadrado del informe general")
ev = inc.eventos_de_la_foto()
comprueba("apertura y cierre de la 1", [e for e in ev if e["averia_id"] == 1],
          [{"averia_id": 1, "fecha": "2026-10-10 08:00:00", "estado": 0},
           {"averia_id": 1, "fecha": "2026-10-10 20:00:00", "estado": 99}])

print("\nSin la foto: lo que entro, sin estado, y se dice")
inc = IN.Incidencias()
inc.come_tareas([tarea(7, apertura=None), tarea(8, apertura=None, fecha_alta="2026-10-14")])
inc.come_eventos([{"averia_id": 7, "fecha": "2026-10-10 09:30:00", "estado": 0},
                  {"averia_id": 7, "fecha": "2026-10-10 11:00:00", "estado": 99}])
f = inc.fichero("interno", HOY)
por = {x["n"]: x for x in f["incidencias"]}
comprueba("no esta al dia, y dice por que", (f["estado_al_dia"], "M13" in f["sin_estado"]), (False, True))
comprueba("la apertura, del primer evento", por["A-70007"]["a"], "2026-10-10 09:30")
comprueba("sin eventos, la fecha de alta", por["A-70008"]["a"], "2026-10-14")
comprueba("y ninguna lleva cierre: no se sabe", any("x" in x for x in f["incidencias"]), False)

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("Las incidencias salen bien.")
