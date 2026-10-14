"""
Tarifas contra venta real (docs/52).

Cada caso es una regla que fijo Gabriele el 14-oct-2026 o una trampa del dato:
el precio exacto por medio de pago, la venta anterior al cambio de tarifa, el
producto que no se ha repuesto en seis meses, el producto sin tarifa, el audit
que da una media, la telemetria sin articulo.

    python3 infra/test_tarifas.py
"""

import datetime
import sys

AQUI = __file__.rsplit("/", 1)[0]
sys.path.insert(0, AQUI)

import operativo as OP  # noqa: E402
import tarifas as TA  # noqa: E402

fallos = []


def comprueba(que, dado, esperado):
    ok = dado == esperado
    print(f"  {'ok   ' if ok else 'FALLO'} {que}" + ("" if ok else f": {dado!r} != {esperado!r}"))
    if not ok:
        fallos.append(que)


HOY = datetime.date(2026, 10, 14)


def censo(mat, pdv, centro=500, cliente=10002, deleg="Madrid - Leganés", t_pdv=None,
          t_centro=None, t_cliente=None):
    return {"cod_cliente": cliente, "cliente": "CLIENTE", "cliente_activo": True,
            "baja_cliente": "1900-01-01 00:00:00", "num_centro": centro, "centro": f"CENTRO {centro}",
            "centro_activo": True, "baja_centro": "1900-01-01", "delegacion": deleg,
            "cod_pdv": pdv, "ubicacion": "Planta 1", "estado_pdv": 1, "baja_pdv": "1900-01-01 00:00:00",
            "matricula": mat, "tarifa_vending_pdv": t_pdv, "tarifa_vending_centro": t_centro,
            "tarifa_vending_cliente": t_cliente}


def carga(mat, art, fecha, canal="11"):
    return {"tipo_linea": "CM", "matricula": mat, "cod_articulo": art, "fecha": fecha,
            "cantidad": 5, "etiq_canal": canal}


def tele(mat, art, precio, linea=2, cuando="2026-10-13 10:00:00"):
    return {"matricula": mat, "cod_articulo": art, "precio": precio, "linea_precio": linea,
            "fecha_venta": cuando}


def linea(origen, nivel="", art="", ef=None, tp=None, tc=None, tpdto=None, fecha="",
          tarifa_id=None, tarifa="", pdv="", centro="", cliente="", grupo=None, cat=""):
    return {"origen": origen, "nivel": nivel, "cod_articulo": art, "precio_ef": ef,
            "precio_tp": tp, "precio_tc": tc, "precio_tpdto": tpdto, "fecha_cambio": fecha,
            "tarifa_id": tarifa_id, "tarifa": tarifa, "cod_pdv": pdv, "num_centro": centro,
            "cod_cliente": cliente, "grupo_id": grupo, "cod_categoria": cat}


print("El observador: ultima carga y ultimo precio por medio de pago")
ob = TA.Observador()
ob.come_cargas([carga("M1", "100", "2026-09-01"), carga("M1", "100", "2026-10-01"),
                carga("M1", "200", "2026-03-01"),      # hace mas de seis meses
                {"tipo_linea": "CM", "matricula": "M1", "cod_articulo": "AZUCAR",
                 "fecha": "2026-10-01", "etiq_canal": ""},  # carril de caliente
                {"tipo_linea": "RC", "matricula": "M1", "cod_articulo": "300", "fecha": "2026-10-01",
                 "etiq_canal": "12"}])
comprueba("se queda la ultima carga", ob.ultima_carga("M1", "100"), "2026-10-01")
comprueba("el azucar del carril no es un producto", ob.ultima_carga("M1", "AZUCAR"), "")
comprueba("una retirada no es una carga", ob.ultima_carga("M1", "300"), "")
corte = (HOY - datetime.timedelta(days=TA.DIAS_VENTANA)).isoformat()
comprueba("solo lo repuesto en seis meses", ob.productos_de("M1", corte), ["100"])
ob.come_telemetria([tele("M1", "100", 1.0, 2, "2026-10-10 09:00:00"),
                    tele("M1", "100", 1.1, 2, "2026-10-12 09:00:00"),
                    tele("M1", "100", 1.0, 2, "2026-10-11 09:00:00"),   # llega desordenada
                    tele("M1", "", 1.0, 2), tele("M1", "100", 1.0, 11)])
comprueba("el ultimo precio, aunque las ventas lleguen desordenadas",
          ob.ultimo_precio("M1", "100", "ef", corte)["precio"], 1.1)
comprueba("la venta sin articulo se cuenta aparte", ob.sin_articulo, 1)
comprueba("el medio 11 no se sabe que es y no se compara", ob.medio_desconocido, 1)
comprueba("nada antes de `desde`", ob.ultimo_precio("M1", "100", "ef", "2026-10-13"), None)
ob.come_audit([{"matricula": "M2", "cod_articulo": "100", "fecha_visita": "2026-10-12 08:00:00",
                "num_efectivo": 3, "imp_efectivo": 2.85, "num_t_privada": 0, "imp_t_privada": 0,
                "num_t_credito": 2, "imp_t_credito": 1.9, "num_total": 5}])
comprueba("el audit da el precio unitario", ob.ultimo_precio("M2", "100", "ef", corte)["precio"], 0.95)
comprueba("y dice que es del audit", ob.ultimo_precio("M2", "100", "ef", corte)["fuente"], "audit")
ob.come_telemetria([tele("M2", "100", 1.0, 2, "2026-10-01 09:00:00")])
comprueba("la telemetria manda sobre el audit aunque el audit sea mas nuevo",
          ob.ultimo_precio("M2", "100", "ef", corte)["fuente"], "telemetria")
ob.come_telemetria([tele("M3", "R10", 0.35, 2, "2026-10-12 09:00:00")])
comprueba("una receta vendida cuenta como producto de la maquina",
          ob.productos_de("M3", corte), ["R10"])

print("\nEl estado se guarda y se recupera igual, y se poda a seis meses")
ob2 = TA.Observador(ob.estado())
comprueba("mismas cargas", ob2.cargas, ob.cargas)
comprueba("mismos precios", ob2.ultimo_precio("M1", "100", "ef", corte),
          ob.ultimo_precio("M1", "100", "ef", corte))
ob2.poda(HOY)
comprueba("la carga de marzo se va", ob2.ultima_carga("M1", "200"), "")

print("\nTrocear da lo mismo que de golpe: dos noches = una")
a = TA.Observador()
a.come_cargas([carga("M1", "100", "2026-10-01")])
a.come_telemetria([tele("M1", "100", 1.0, 2, "2026-10-02 09:00:00")])
b = TA.Observador(a.estado())
b.come_cargas([carga("M1", "100", "2026-09-01")])          # una noche que relee lo viejo
b.come_telemetria([tele("M1", "100", 0.9, 2, "2026-09-02 09:00:00")])
c = TA.Observador()
c.come_cargas([carga("M1", "100", "2026-09-01"), carga("M1", "100", "2026-10-01")])
c.come_telemetria([tele("M1", "100", 0.9, 2, "2026-09-02 09:00:00"),
                   tele("M1", "100", 1.0, 2, "2026-10-02 09:00:00")])
comprueba("mismo estado", b.estado(), c.estado())

print("\nQue precio rige: lo mas concreto manda")
ta = TA.Tarifas([
    linea("tarifa", "tarifa", "100", 1.0, 0.9, 1.0, tarifa_id=7, tarifa="ESTANDAR 2024", fecha="2026-01-01"),
    linea("tarifa", "tarifa", "200", 1.5, 1.5, 1.5, tarifa_id=7, tarifa="ESTANDAR 2024", fecha="2026-01-01"),
    linea("productos", "centro", "100", 1.2, 1.2, 1.2, centro="500", fecha="2026-10-05"),
    linea("productos", "pdv", "200", 1.4, 1.4, 1.4, pdv="P2", fecha="2026-02-01"),
    linea("articulo", "articulo", "300", cat="SNACK"),
    linea("categorias", "cliente", "", 0.8, 0.8, 0.8, cliente="10002", cat="SNACK"),
    linea("productos", "global", "400", 2.0, 2.0, 2.0),
    linea("productos", "grupo", "500", 3.0, 3.0, 3.0, grupo=9),
    {"origen": "cliente_grupo", "nivel": "grupo", "cod_cliente": "10002", "grupo_id": 9},
])
sitio = {"pdv": "P1", "centro": "500", "cliente": "10002", "tarifa_pdv": "", "tarifa_centro": "",
         "tarifa_cliente": "7"}
comprueba("el precio suelto del centro gana a la tarifa del cliente",
          (ta.precio("100", sitio)["nivel"], ta.precio("100", sitio)["ef"]), ("centro", 1.2))
comprueba("sin precio en el centro, la tarifa estandar asignada al cliente",
          tuple(ta.precio("200", sitio)[k] for k in ("nivel", "asignada", "tarifa")),
          ("estandar", "cliente", "ESTANDAR 2024"))
comprueba("el del punto de venta gana a todo",
          ta.precio("200", dict(sitio, pdv="P2"))["nivel"], "pdv")
comprueba("por categoria, si el articulo no tiene precio propio",
          (ta.precio("300", sitio)["origen"], ta.precio("300", sitio)["ef"]), ("categorias", 0.8))
comprueba("el grupo del cliente", ta.precio("500", sitio)["nivel"], "grupo")
comprueba("el precio general, sin asignar, al final", ta.precio("400", sitio)["nivel"], "general")
comprueba("un articulo sin precio en ningun sitio", ta.precio("999", sitio), None)
comprueba("un codigo numerico del censo casa con el texto del maestro",
          ta.precio("100", dict(sitio, centro=TA._s(500.0)))["nivel"], "centro")

print("\nCoincide: exacto, medio a medio, desde el ultimo cambio")
ob = TA.Observador()
ob.come_telemetria([tele("M1", "100", 1.2, 2, "2026-10-10 09:00:00"),
                    tele("M1", "100", 1.2, 1, "2026-10-10 09:00:00")])
L = {"ef": 1.2, "tp": 1.2, "tc": 1.2, "tpdto": None, "fecha": "2026-10-05"}
comprueba("efectivo y credito iguales: coincide", TA.compara(L, ob, "M1", "100", HOY)[0], "coincide")
comprueba("un medio sin venta no estropea los demas", "ok" in TA.compara(L, ob, "M1", "100", HOY)[1]["tp"], False)
ob.come_telemetria([tele("M1", "100", 1.25, 1, "2026-10-11 09:00:00")])
comprueba("cinco centimos de mas en credito: no coincide",
          TA.compara(L, ob, "M1", "100", HOY)[0], "no_coincide")
comprueba("no hay tolerancia: un centimo tambien es no",
          TA.compara(dict(L, tc=1.24), ob, "M1", "100", HOY)[0], "no_coincide")
comprueba("venta anterior al cambio de tarifa: sin dato",
          TA.compara(dict(L, fecha="2026-10-12"), ob, "M1", "100", HOY)[0], "sin_dato")
comprueba("la tarjeta privada vale tambien con el precio de descuento",
          TA.compara({"ef": None, "tp": 1.0, "tc": None, "tpdto": 0.8, "fecha": ""},
                     _o := TA.Observador(), "M1", "100", HOY)[0], "sin_dato")
_o.come_telemetria([tele("M1", "100", 0.8, 3)])
comprueba("0,80 con descuento de empleado coincide",
          TA.compara({"ef": None, "tp": 1.0, "tc": None, "tpdto": 0.8, "fecha": ""},
                     _o, "M1", "100", HOY)[0], "coincide")
comprueba("sin tarifa (todo a cero) es sin_tarifa, no un no",
          TA.compara({"ef": None, "tp": None, "tc": None}, ob, "M1", "100", HOY)[0], "sin_tarifa")
comprueba("sin linea de tarifa", TA.compara(None, ob, "M1", "100", HOY)[0], "sin_tarifa")
comprueba("sin tarifa se ensena lo que cobra para rellenarla",
          TA.compara(None, ob, "M1", "100", HOY)[1]["ef"]["venta"]["precio"], 1.2)
comprueba("tarifa vieja (2025): solo cuentan seis meses",
          TA.compara(dict(L, fecha="2025-01-01"), ob, "M1", "100", HOY)[2],
          (HOY - datetime.timedelta(days=TA.DIAS_VENTANA)).isoformat())

print("\nUn perfil: centros, delegaciones y el cuadrado")
ob = TA.Observador()
ob.come_cargas([carga("M1", "100", "2026-10-01"), carga("M1", "200", "2026-10-01"),
                carga("M1", "999", "2026-10-01"), carga("M2", "100", "2026-10-01"),
                carga("M9", "100", "2026-10-01")])
ob.come_telemetria([tele("M1", "100", 1.2), tele("M1", "200", 1.6), tele("M2", "100", 1.0)])
cen = [censo("M1", "P1", t_cliente=7), censo("M2", "P2", centro=600, deleg="Cádiz", t_cliente=7),
       censo("M9", "P9", centro=700)]
cen[2]["baja_pdv"] = "2026-09-01 00:00:00"      # dado de baja: no cuenta
res, det = TA.calcula(cen, ta, ob, HOY, OP.semaforo)
comprueba("dos centros vivos", sorted(det), ["500", "600"])
comprueba("M1: 100 coincide, 200 no (1,60 contra 1,50), 999 sin tarifa",
          sorted((r["cod_articulo"], r["estado"]) for r in det["500"]["filas"]),
          [("100", "coincide"), ("200", "no_coincide"), ("999", "sin_tarifa")])
comprueba("M2 en el centro 600: tarifa 1,00 del cliente, cobra 1,00",
          [r["estado"] for r in det["600"]["filas"]], ["coincide"])
comprueba("el porcentaje no cuenta lo sin tarifa: 2 de 3", res["total"]["pct"], 66.7)
comprueba("lo sin tarifa se dice", res["total"]["sin_tarifa"], 1)
comprueba("dos delegaciones", [d["delegacion"] for d in res["delegaciones"]], ["Cádiz", "Madrid - Leganés"])
comprueba("Cádiz al 100 %, verde", (res["delegaciones"][0]["pct"], res["delegaciones"][0]["color"]),
          (100.0, "verde"))
comprueba("el nivel del centro 500: centro (precio suelto) y estandar, uno cada uno",
          det["500"]["resumen"]["niveles"], {"centro": 1, "estandar": 1})
comprueba("la tarifa asignada del centro", det["500"]["resumen"]["tarifas"],
          [{"tarifa": "ESTANDAR 2024 (asignada al cliente)", "maquinas": 1}])
cu = TA.cuadrado(res, OP.semaforo)
comprueba("el cuadrado: 66,7 % en rojo", (cu["pct"], cu["color"]), (66.7, "rojo"))
res0, _ = TA.calcula([], ta, ob, HOY, OP.semaforo)
comprueba("sin nada que controlar, sin_dato y no un cero", "sin_dato" in TA.cuadrado(res0, OP.semaforo), True)

print()
if fallos:
    print(f"{len(fallos)} FALLOS")
    sys.exit(1)
print("Todo bien.")
