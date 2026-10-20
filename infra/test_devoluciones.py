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


def tarea(ident, op="DEVOLUCION - IN SITU", cod="D01", alta="2026-10-10 08:00:00", cierre=None, **kw):
    t = {"id": ident, "serie": "A", "numero": 80000 + ident, "fecha_alta": alta[:10],
         "tipo_tarea": "A", "tipo_estado": 9 if cierre else 1, "estado": 99 if cierre else 1,
         "cod_operacion": cod, "operacion": op, "categoria": "ATENCION AL CLIENTE",
         "matricula": "24CE4820", "num_centro": 1001, "centro": "AIRBUS GETAFE", "cod_cliente": 7,
         "cliente": "AIRBUS", "delegacion": "Madrid - Leganes", "tecnico_asignado": "Javier",
         "titulo": "ES00 1234 5678 · Ana", "ultima_nota": "llamar al 600 000 000",
         "apertura": alta, "cierre": cierre}
    t.update(kw)
    return t


print("El canal, por la operacion")
comprueba("in situ, con los dos codigos",
          (DV.canal_de("DEVOLUCION - IN SITU"), DV.canal_de("Devolución dinero IN SITU")),
          ("En el sitio", "En el sitio"))
comprueba("transferencia, bien y mal escrita",
          (DV.canal_de("DEVOLUCION - Transferencia Bancaria"), DV.canal_de("TRASFERENCIA BANCARIA")),
          ("Transferencia", "Transferencia"))
comprueba("las dos tarjetas",
          (DV.canal_de("DEVOLUCION - TARJETA DE CREDITO"), DV.canal_de("DEVOLUCION - Tarjeta Empleado")),
          ("Tarjeta de crédito", "Tarjeta de empleado"))
comprueba("lo demas, otra", DV.canal_de("No devuelve cambio"), "Otra")

print("\nSolo devoluciones, sin la ficticia y sin datos del cliente")
dv = DV.Devoluciones()
dv.come_foto([
    tarea(1, cierre="2026-10-10 12:00:00"),
    tarea(2, "DEVOLUCION - Transferencia Bancaria", "D03", alta="2026-10-14 09:00:00"),
    tarea(3, "CAFÉ - Distribuidor fuera de servicio", "T08"),
    tarea(4, matricula="00SE0000"),
    tarea(5, alta="2026-09-12 10:00:00", cierre="2026-09-12 11:00:00"),
    tarea(6, "Devolución dinero IN SITU", "DEV01", alta="2026-09-15 10:00:00", cierre="2026-09-15 11:00:00",
          tipo_tarea="E", serie="A", categoria="Devolución dinero"),
    tarea(7, alta="2026-09-16 10:00:00", cierre="2026-09-16 11:00:00"),
    tarea(8, alta="2025-01-10 10:00:00", cierre="2025-01-10 11:00:00"),
    tarea(9, alta="2024-07-05 10:00:00"),
])
f = dv.fichero("interno", HOY)
por = {x["n"]: x for x in f["devoluciones"]}
comprueba("ni la averia ni la ficticia ni la cerrada de hace mas de 13 meses",
          sorted(por), ["A-80001", "A-80002", "A-80005", "A-80006", "A-80007", "A-80009"])
comprueba("la que sigue sin cerrar va aunque sea vieja", "x" in por["A-80009"], False)
comprueba("la cerrada, con sus horas", (por["A-80001"]["x"], por["A-80001"]["h"]), ("2026-10-10 12:00", 4.0))
comprueba("el canal por indice", f["canales"][por["A-80002"]["k"]], "Transferencia")
comprueba("solo la de la serie E va marcada como solicitud especial",
          sorted(n for n, x in por.items() if x.get("e")), ["A-80006"])
comprueba("y su nombre viaja", f["origenes"][1], "Solicitud especial")
comprueba_texto = any(k in x for x in f["devoluciones"] for k in ("tx", "titulo", "ultima_nota"))
comprueba("ni titulo ni notas: llevan el IBAN y el telefono", comprueba_texto, False)
comprueba("tampoco escondido en otra columna", "ES00" in str(f) or "600 000" in str(f), False)

print("\nEl cuadrado: el mes de ayer hasta ayer, contra los mismos dias del anterior")
c = dv.cuadrado(HOY)
comprueba("octubre, hasta el 15", (c["mes"], c["hasta"]), ("2026-10", "2026-10-15"))
comprueba("dos en octubre, una sin cerrar", (c["total"], c["sin_cerrar"]), (2, 1))
comprueba("del 1 al 15 de septiembre, dos (la del 16 no)", c["mes_anterior"], 2)
comprueba("ninguna especial en octubre", c["especiales"], 0)
comprueba("por canal", c["por_canal"], [["En el sitio", 1], ["Transferencia", 1]])
comprueba("el dia 1 cuenta el mes anterior entero",
          dv.cuadrado(datetime.date(2026, 10, 1))["mes"], "2026-09")
d2 = DV.Devoluciones()
d2.come_foto([tarea(1, alta="2026-02-28 10:00:00"), tarea(2, alta="2026-03-01 10:00:00"),
              tarea(3, alta="2026-03-31 10:00:00")])
c2 = d2.cuadrado(datetime.date(2026, 4, 1))
comprueba("el 31 de marzo se compara con febrero entero", (c2["total"], c2["mes_anterior"]), (2, 1))

print("\nEl importe, leido de la cifra del titulo y de nada mas")
for titulo, euros in (
        ("Devolución = 1,40 € PRODUCTO NO ENTREGADO DEVOLUCIÓN EN SITU TICKET: 123456", 1.4),
        ("Devolución = 0.65 € PRODUCTO NO ENTREGADO TRASFERENCIA BANCARIA TICKET: 1", 0.65),
        ("Devolución = 1'22 € PRODUCTO NO ENTREGADO", 1.22),
        ("Devolución = 0’70 € PRODUCTO NO ENTREGADO", 0.7),
        ("Devolución = 3€ € NO DEVUELVE CAMBIO", 3.0),
        ("Devolución = 5 EUR € NO DEVUELVE CAMBIO", 5.0),
        ("Devolución = 4 euros € PRODUCTO NO ENTREGADO", 4.0),
        ("Devolución = 50 cnt € PRODUCTO NO ENTREGADO", 0.5),
        ("Devolución = 90centimos € PRODUCTO NO ENTREGADO", 0.9),
        ("Devolución = 75 cèntims € PRODUCTO NO ENTREGADO", 0.75),
        ("Devolución = ,50 € PRODUCTO NO ENTREGADO", 0.5),
        ("23.09 Devolución = 1.30 EUR € PRODUCTO NO ENTREGADO", 1.3),
        ("DEV. 0,50 ", 0.5),
        ("DEV, 1€", 1.0),
        # Lo que no es una cifra limpia se queda sin importe: no se adivina.
        ("OTRO TICKET: 123456", None),
        ("Devolución = Cinco euros € PRODUCTO NO ENTREGADO", None),
        ("Devolución = 5+5 (17/11 Y 19/11) € PRODUCTO NO ENTREGADO", None),
        ("Devolución = 2 cafés € PRODUCTO NO ENTREGADO", None),
        ("Devolución = 1, 70 EUROS € PRODUCTO NO ENTREGADO", None),
        ("Devolución = O,40 € PRODUCTO NO ENTREGADO", None),
        ("Devolución = 0,5 cnt € PRODUCTO NO ENTREGADO", None),
        ("ES00 1234 5678 · Ana", None),
):
    comprueba(f"{titulo[:40]!r}", DV.importe_de(titulo), euros)

di = DV.Devoluciones()
di.come_foto([
    tarea(1, titulo="Devolución = 1,40 € PRODUCTO NO ENTREGADO TRASFERENCIA BANCARIA TICKET: ES00 1234"),
    tarea(2, titulo="Devolución = 85 € PRODUCTO NO ENTREGADO DEVOLUCIÓN EN SITU TICKET: 1"),
    tarea(3, titulo="OTRO TICKET: 1"),
    tarea(4, titulo="Devolución = 2 € PRODUCTO NO ENTREGADO", alta="2026-09-10 08:00:00"),
])
fi = {x["n"]: x for x in di.fichero("interno", HOY)["devoluciones"]}
comprueba("la cifra viaja en i, el titulo no",
          (fi["A-80001"].get("i"), "ES00" in json.dumps(fi)), (1.4, False))
comprueba(f"por encima de {DV.IMPORTE_MAX:g} € va aparte, en g", (fi["A-80002"].get("i"), fi["A-80002"].get("g")), (None, 85.0))
comprueba("sin cifra, ni i ni g", ("i" in fi["A-80003"], "g" in fi["A-80003"]), (False, False))
ci = di.cuadrado(HOY)
comprueba("el cuadrado suma solo lo que se lee y dice cuantas no",
          (ci["importe"], ci["sin_importe"], ci["importe_anterior"]), (1.4, 2, 2.0))

print("\nSin la foto, se dice")
vacio = DV.Devoluciones()
comprueba("el cuadrado dice que falta M13", "M13" in vacio.cuadrado(HOY).get("sin_dato", ""), True)
comprueba("y la pagina tambien, sin filas", ("M13" in vacio.fichero("interno", HOY)["sin_dato"],
                                             vacio.fichero("interno", HOY)["devoluciones"]), (True, []))

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("Las devoluciones salen bien.")
