"""
Las devoluciones de dinero: el cuadrado y las filas de su pagina (docs/57).

    python3 infra/test_devoluciones.py
"""

import datetime
import json
import sys

AQUI = __file__.rsplit("/", 1)[0]
sys.path.insert(0, AQUI)

import devoluciones as DV  # noqa: E402

fallos = []


def comprueba(que, dado, esperado):
    ok = dado == esperado
    print(f"  {'ok   ' if ok else 'FALLO'} {que}" + ("" if ok else f": {dado!r} != {esperado!r}"))
    if not ok:
        fallos.append(que)


HOY = datetime.date(2026, 10, 16)


def dev(numero, fecha="2026-10-10 08:00:00", estado=3, importe=1.4, tipo="Transferencia", **kw):
    """Una fila de M16 · EXT_DEVOLUCIONES, como la baja la extraccion."""
    f = {"id": numero, "numero": numero, "fecha": fecha, "tipo": 0, "estado": 1 if estado in (3, 4) else 0,
         "estado_devolucion": estado, "tipo_devolucion": 4, "tipo_devolucion_nombre": tipo,
         "importe": importe, "transaccion_fallida": False, "motivo": "No da producto", "resolucion": None,
         "origen": 1, "registrado_por": "Ana", "resuelto_por": "", "matricula": "24CE4820", "cod_pdv": "S01",
         "num_centro": 1001, "centro": "AIRBUS GETAFE", "cod_cliente": 7, "cliente": "AIRBUS",
         "delegacion": "Madrid - Leganes", "ticket": None, "tareas_sat": None}
    f.update(kw)
    return f


print("El estado, como lo ensena VenCloud")
comprueba("1 en estudio, 3 abonada, 4 rechazada",
          [DV.estado_de({"estado_devolucion": e}) for e in (1, 3, 4)], ["En estudio", "Abonada", "Rechazada"])
comprueba("lo que no se conoce, sin estado", DV.estado_de({"estado_devolucion": 0}), "Sin estado")

print("\nLas filas: sin la ficticia, sin datos del cliente")
d = DV.Devoluciones()
d.come_foto([
    dev(1, importe=1.4),
    dev(2, fecha="2026-10-14 09:00:00", estado=1, importe=2, tipo="Sin devolución"),
    dev(3, importe=0.5, matricula="00SE0000"),
    dev(4, fecha="2026-10-09 13:59:11", importe=44504),
    dev(5, fecha="2026-10-11 10:00:00", estado=4, importe=3),
    dev(6, fecha="2026-09-12 10:00:00", importe=1.0),
    dev(7, fecha="2026-09-15 10:00:00", importe=2.5, tipo="Monyx"),
    dev(8, fecha="2026-09-16 10:00:00", importe=9.0),
    dev(9, fecha="2025-01-10 10:00:00", importe=1.0),
    dev(10, fecha="2024-07-05 10:00:00", estado=1, importe=1.0),
])
f = d.fichero("interno", HOY)
por = {x["n"]: x for x in f["devoluciones"]}
comprueba("ni la ficticia ni la resuelta de hace mas de 13 meses",
          sorted(por, key=int), ["1", "2", "4", "5", "6", "7", "8", "10"])
comprueba("la que sigue en estudio va aunque sea vieja", f["estados"][por["10"]["s"]], "En estudio")
comprueba("el importe, del campo", por["1"].get("i"), 1.4)
comprueba(f"por encima de {DV.IMPORTE_MAX:g} € va aparte, en g", (por["4"].get("i"), por["4"].get("g")), (None, 44504.0))
comprueba("el tipo por indice", f["tipos"][por["7"]["k"]], "Monyx")
comprueba("sin el nombre de quien lo registra ni datos del cliente",
          any(k in json.dumps(f) for k in ("Ana", "registrado_por", "nomcontacto")), False)

print("\nEl cuadrado: el dinero abonado del mes de ayer hasta ayer, contra los mismos dias del anterior")
c = d.cuadrado(HOY)
comprueba("octubre, hasta el 15", (c["mes"], c["hasta"]), ("2026-10", "2026-10-15"))
comprueba("cuatro en octubre", c["total"], 4)
comprueba("el dinero, solo de las abonadas y sin la de 44.504", c["importe"], 1.4)
comprueba("y la de 44.504 se cuenta", c["fuera_de_tope"], 1)
comprueba("una en estudio, con su dinero aparte", (c["sin_resolver"], c["importe_sin_resolver"]), (1, 2.0))
comprueba("una rechazada", c["rechazadas"], 1)
comprueba("del 1 al 15 de septiembre, 3,50 € (la del 16 no)", (c["mes_anterior"], c["importe_anterior"]), (2, 3.5))
comprueba("el dia 1 cuenta el mes anterior entero",
          d.cuadrado(datetime.date(2026, 10, 1))["mes"], "2026-09")
d2 = DV.Devoluciones()
d2.come_foto([dev(1, fecha="2026-02-28 10:00:00"), dev(2, fecha="2026-03-01 10:00:00"),
              dev(3, fecha="2026-03-31 10:00:00")])
c2 = d2.cuadrado(datetime.date(2026, 4, 1))
comprueba("el 31 de marzo se compara con febrero entero", (c2["total"], c2["mes_anterior"]), (2, 1))

print("\nSin la foto, se dice; con la foto vacia, es un cero")
vacio = DV.Devoluciones()
comprueba("el cuadrado dice que falta M16", "M16" in vacio.cuadrado(HOY).get("sin_dato", ""), True)
comprueba("y la pagina tambien, sin filas", ("M16" in vacio.fichero("interno", HOY)["sin_dato"],
                                             vacio.fichero("interno", HOY)["devoluciones"]), (True, []))
cero = DV.Devoluciones()
cero.come_foto([])
comprueba("un perfil sin devoluciones no es un «falta»", (cero.cuadrado(HOY).get("sin_dato"), cero.cuadrado(HOY)["importe"]),
          (None, 0))

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("Las devoluciones salen bien.")
