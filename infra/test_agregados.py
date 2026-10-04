"""
Prueba de la Lambda de agregados con un S3 falso.

Monta en memoria el crudo de un dia, ejecuta el handler y comprueba que el panel
que sale lleva las cifras buenas y las notas que avisan de las trampas.

    python3 infra/test_agregados.py
"""

import datetime
import gzip
import json
import os
import sys
import types

AQUI = __file__.rsplit("/", 1)[0]
sys.path.insert(0, AQUI)

# ---------------------------------------------------------------- S3 falso
ALMACEN = {}


class _NoSuchKey(Exception):
    pass


class _S3Falso:
    exceptions = types.SimpleNamespace(NoSuchKey=_NoSuchKey)

    def get_object(self, Bucket, Key):
        if Key not in ALMACEN:
            raise _NoSuchKey(Key)
        cuerpo = ALMACEN[Key]
        return {"Body": types.SimpleNamespace(read=lambda: cuerpo)}

    def put_object(self, Bucket, Key, Body, **kw):
        ALMACEN[Key] = Body
        return {}


sys.modules["boto3"] = types.SimpleNamespace(client=lambda *a, **k: _S3Falso())
os.environ.setdefault("BUCKET", "prueba")
os.environ["DIAS"] = "3"

import lambda_agregados as L  # noqa: E402

HOY = datetime.date.today()
AYER = HOY - datetime.timedelta(days=1)


def pon(destino, id_informe, dia, filas):
    clave = (f"{destino}/anio={dia.year}/mes={dia.month:02d}/dia={dia.day:02d}/"
             f"{id_informe}.json.gz")
    ALMACEN[clave] = gzip.compress(json.dumps(filas).encode())


# ---------------------------------------------------------------- datos
pon("crudo/visita_cabecera", "visita_cabecera", AYER,
    [{"empleadoid": 0, "empleado": "SYSTEM", "tipo_parte": 2, "centro": "AIRBUS GETAFE", "num_centro": "1001",
      "cliente": "AIRBUS OPERATIONS SL", "cod_cliente": "C7",
      "matricula": "A1", "minutos": 0, "fecha_ini": str(AYER)}] * 200
    + [{"empleadoid": 7, "empleado": "Ana", "tipo_parte": 0, "centro": "AIRBUS GETAFE", "num_centro": "1001",
        "cliente": "AIRBUS OPERATIONS SL", "cod_cliente": "C7",
        "matricula": "A1", "minutos": 7, "fecha_ini": str(AYER)}] * 100
    + [{"empleadoid": 7, "empleado": "Ana", "tipo_parte": 0, "centro": "CONSUM MURCIA", "num_centro": "2002",
        "cliente": "CONSUM S COOP V", "cod_cliente": "C9",
        "matricula": "C1", "minutos": 400, "fecha_ini": str(AYER)}] * 10)

# OJO: los informes de aqui abajo van SIN columna `centro`, porque el de verdad
# no la trae. La primera version de esta prueba se la inventaba, y por eso no
# descubrio que el panel de AIRBUS salia con 0 EUR de recaudacion y 0 unidades
# cargadas: las filas sin centro no encajaban en ningun ambito y se caian.
# Lo que si traen es `matricula`, y de ahi sale el centro por el mapa.
pon("crudo/visita_reposiciones", "visita_reposiciones", AYER,
    [{"tipo_linea": "CM", "cantidad": 10, "precio_coste": 1.0, "etiq_canal": "44", "matricula": "A1"}] * 50
    + [{"tipo_linea": "CM", "cantidad": 100, "precio_coste": 0.004, "etiq_canal": "", "matricula": "A1"}] * 50
    # Y una maquina de Consum, que a AIRBUS no le toca.
    + [{"tipo_linea": "CM", "cantidad": 7, "precio_coste": 1.0, "etiq_canal": "44", "matricula": "C1"}] * 20)

pon("crudo/stock_maquina", "stock_maquina", AYER,
    [{"motivo": "RC", "cantidad": -2, "puc": 0.60, "articulo": "DONETTES CLASICO",
      "centro": "AIRBUS GETAFE"}] * 10
    # Un solo envase de cafe pesa mas en euros que diez lineas de snack.
    + [{"motivo": "RC", "cantidad": -1, "puc": 23.32,
        "articulo": "CAFE SOLUBLE LIOFILIZADO DESCAFEINADO", "centro": "AIRBUS GETAFE"}]
    + [{"motivo": "CM", "cantidad": 10, "puc": 0.60, "centro": "AIRBUS GETAFE"}] * 10)

pon("crudo/recaudacion", "recaudacion", AYER,
    [{"anho": HOY.year, "mes": HOY.month, "imp_recaudado": 100, "imp_pago_bancario": 0,
      "tipo_telemetria": 40, "criterio_calculo": 3, "matricula": "A1"}] * 3
    + [{"anho": 2026, "mes": 1, "imp_recaudado": 100, "imp_pago_bancario": 120,
        "tipo_telemetria": 0, "criterio_calculo": 3, "matricula": "A1"}] * 2
    # La fila rota de junio, como la de verdad
    + [{"anho": 2026, "mes": 6, "imp_recaudado": -7_521_760_075.56, "imp_pago_bancario": 0,
        "tipo_telemetria": 40, "criterio_calculo": 3, "matricula": "A1"}]
    + [{"anho": 2026, "mes": 6, "imp_recaudado": 50, "imp_pago_bancario": 10,
        "tipo_telemetria": 40, "criterio_calculo": 3, "matricula": "A1"}] * 4
    # De Consum, para que se vea que el ambito sigue filtrando con el mapa puesto.
    + [{"anho": 2026, "mes": 1, "imp_recaudado": 9_999, "imp_pago_bancario": 0,
        "tipo_telemetria": 40, "criterio_calculo": 3, "matricula": "C1"}])

pon("crudo/sat_averias", "sat_averias", AYER,
    [{"matricula": "00SE0000", "categoria": "ATENCION AL CLIENTE", "tipo_tarea": "A", "centro": "AIRBUS GETAFE"}] * 40
    + [{"matricula": "A1", "categoria": "AVERIAS TECNICAS", "tipo_tarea": "A", "centro": "AIRBUS GETAFE"}] * 12
    + [{"matricula": "A1", "categoria": "AVERIAS TECNICAS", "tipo_tarea": "E", "centro": "AIRBUS GETAFE"}] * 3)

pon("crudo/sat_eventos", "sat_eventos", AYER,
    [{"averia_id": 1, "estado": 0, "fecha": f"{AYER}T08:00:00", "matricula": "A1"},
     {"averia_id": 1, "estado": 99, "fecha": f"{AYER}T14:00:00", "matricula": "A1"}])

# Las jornadas son de una RUTA y un vehiculo, no de un centro, y el informe no
# trae matricula: no hay forma de atribuirlas a un cliente, asi que solo salen en
# el panel interno. Tampoco hace falta: el bloque de jornadas no llega a un
# perfil de cliente (autorizacion.SESIONES lo pide a partir de «operaciones»).
pon("crudo/jornadas", "jornadas", AYER,
    [{"temperaturaini": 2.0, "kminiciales": 100, "kmfinales": 150, "maplatitudini": 37.4}] * 9
    + [{"temperaturaini": 26.0, "kminiciales": 100, "kmfinales": 160, "maplatitudini": 0}])

# DOS cierres mensuales dentro de la ventana: el de agosto y el de septiembre.
# Es lo normal con 120 dias, y sumarlos multiplicaria las existencias.
pon("crudo/stock_balance", "stock_balance", AYER,
    [{"anho": 2026, "mes": 9, "tipo_elemento": "M", "valor_total": 1000,
      "fecha_ult_inventario": str(HOY), "matricula": "A1"}] * 2
    + [{"anho": 2026, "mes": 9, "tipo_elemento": "M", "valor_total": 500,
        "fecha_ult_inventario": "1900-01-01", "matricula": "A1"}] * 2
    + [{"anho": 2026, "mes": 9, "tipo_elemento": "A", "valor_total": 9000,
        "fecha_ult_inventario": str(HOY), "matricula": "A1"}]
    + [{"anho": 2026, "mes": 8, "tipo_elemento": "M", "valor_total": 7777,
        "fecha_ult_inventario": str(HOY), "matricula": "A1"}] * 6
    + [{"anho": 2026, "mes": 8, "tipo_elemento": "A", "valor_total": 123456,
        "fecha_ult_inventario": str(HOY), "matricula": "A1"}])

ALMACEN["config/perfiles.json"] = json.dumps({"perfiles": [
    {"id": "interno", "ambito": {}},
    {"id": "cli-airbus", "ambito": {"clientes": ["AIRBUS"], "centros": [], "delegaciones": []}},
]}).encode()

# ---------------------------------------------------------------- ejecucion
fallos = []


def comprueba(que, obtenido, esperado):
    if obtenido == esperado:
        print(f"  ok    {que}")
    else:
        print(f"  FALLO {que}: {obtenido!r} != {esperado!r}")
        fallos.append(que)


res = L.lambda_handler({}, None)
interno = json.loads(ALMACEN["cabina/interno/panel.json"])
airbus = json.loads(ALMACEN["cabina/cli-airbus/panel.json"])

print("\nSe escriben los dos paneles")
comprueba("dos ficheros", len(res["ficheros"]), 2)

print("\nInterno: ve los dos centros")
comprueba("310 partes leidos", interno["servicio"]["partes_totales"], 310)
comprueba("110 visitas reales", interno["servicio"]["visitas"], 110)
comprueba("coste de servicio", interno["servicio"]["coste_servicio"]["coste"], 880.0)
comprueba("mediana de duracion, no media", interno["servicio"]["duracion_min"]["mediana"], 7.0)

print("\nAIRBUS: el ambito filtra Consum fuera")
comprueba("100 visitas", airbus["servicio"]["visitas"], 100)
comprueba("un solo centro", airbus["servicio"]["centros"], 1)

print("\nLa carga separa consumibles de producto vendible")
comprueba("valor cargado", airbus["servicio"]["carga"]["valor"], 520.0)
comprueba("unidades totales", airbus["servicio"]["carga"]["unidades_total"], 5500)
comprueba("unidades vendibles", airbus["servicio"]["carga"]["unidades_vendibles"], 500)

print("\nLa merma se valora con puc")
comprueba("11 lineas de caducidad", airbus["servicio"]["merma"]["caducidad"]["lineas"], 11)
comprueba("12 EUR de snack mas 23,32 de cafe",
          airbus["servicio"]["merma"]["caducidad"]["euros"], 35.32)

print("\nY el desglose explica por que: un envase de cafe pesa mas que 10 de snack")
art = airbus["servicio"]["merma"]["caducidad_por_articulo"]
comprueba("dos articulos", len(art), 2)
comprueba("el cafe manda en euros", art[0]["articulo"], "CAFE SOLUBLE LIOFILIZADO DESCAFEINADO")
comprueba("con UNA sola linea", art[0]["lineas"], 1)
comprueba("y 23,32 EUR", art[0]["euros"], 23.32)
comprueba("mientras el snack lleva 10 lineas", art[1]["lineas"], 10)
comprueba("y solo 12 EUR", art[1]["euros"], 12.0)
comprueba("el euro por unidad lo deja claro", art[0]["eur_unidad"], 23.32)
comprueba("contra el del snack", art[1]["eur_unidad"], 0.6)

print("\nEl mes en curso sale marcado como provisional")
actual = [p for p in airbus["dinero"]["periodos"] if p["periodo"] == f"{HOY.year}-{HOY.month:02d}"][0]
comprueba("provisional", actual["provisional"], True)
comprueba("lleva su aviso", "tarjeta" in actual.get("_nota", ""), True)
junio = [p for p in airbus["dinero"]["periodos"] if p["periodo"] == "2026-06"][0]
comprueba("junio sobrevive a la fila rota", junio["efectivo"], 200.0)
comprueba("y dice que aparto una", junio["filas_imposibles"], 1)
comprueba("sin dejar el porcentaje en negativo", junio["pct_ciego"], 0.0)

enero = [p for p in airbus["dinero"]["periodos"] if p["periodo"] == "2026-01"][0]
comprueba("un mes limpio no lleva la marca", "filas_imposibles" in enero, False)
comprueba("enero ya esta cerrado", enero["provisional"], False)
comprueba("efectivo ciego de enero", enero["efectivo_sin_telemetria"], 200.0)
comprueba("100 % ciego", enero["pct_ciego"], 100.0)

print("\nSAT: fuera la matricula ficticia")
comprueba("55 tareas leidas", airbus["sat"]["tareas_con_ficticia"], 55)
comprueba("15 sobre maquinas reales", airbus["sat"]["tareas"], 15)
comprueba("12 averias tecnicas", airbus["sat"]["averias_tecnicas"], 12)
comprueba("3 preventivos", airbus["sat"]["preventivos"], 3)
comprueba("6 h de cierre", airbus["sat"]["horas_cierre"]["mediana"], 6.0)

print("\nJornadas: temperatura, km y GPS (solo en el panel interno)")
comprueba("10 jornadas", interno["jornadas"]["jornadas"], 10)
comprueba("1 fuera de temperatura", interno["jornadas"]["temperatura_fuera"], 1)
comprueba("510 km", interno["jornadas"]["km_total"], 510)
comprueba("90 % con GPS", interno["jornadas"]["gps"]["pct"], 90.0)
comprueba("y a un cliente no se le atribuye ninguna", airbus["jornadas"]["jornadas"], 0)

print("\nEl mapa de centros: una fila sin centro acaba en el panel de su cliente")
# Esto es lo que estaba roto. Las tres comprobaciones de arriba —carga 520 EUR,
# 5.500 unidades y la recaudacion de enero— ya pasan por el mapa: sus informes no
# traen centro. Aqui se mira el mapa de frente.
comprueba("aprende las matriculas", res["maquinas_con_centro"] >= 2, True)
_m = L.MapaCentros()
_m.aprende([{"matricula": "A1", "centro": "AIRBUS GETAFE", "cod_pdv": "P1"}])
comprueba("resuelve por matricula", _m.centro_de({"matricula": "A1"}), "AIRBUS GETAFE")
comprueba("resuelve por pdv", _m.centro_de({"cod_pdv": "P1"}), "AIRBUS GETAFE")
comprueba("respeta el centro que ya trae la fila",
          _m.centro_de({"matricula": "A1", "centro": "OTRO"}), "OTRO")
comprueba("y una maquina que no conoce no se la inventa",
          _m.centro_de({"matricula": "ZZ"}), "")
comprueba("con mapa, la fila de recaudacion entra en el ambito",
          L.en_ambito({"matricula": "A1"}, {"clientes": ["AIRBUS"]}, _m), True)
comprueba("y la de otro cliente, no",
          L.en_ambito({"matricula": "ZZ"}, {"clientes": ["AIRBUS"]}, _m), False)
comprueba("un ambito vacio sigue cogiendolo todo",
          L.en_ambito({"matricula": "ZZ"}, {}, _m), True)

print("\nLa mudanza de VenCloud: el cliente de verdad en vez del nombre del centro")
# Hasta octubre de 2026 todos los centros colgaban del cliente «Serunion» y el
# cliente real solo estaba en el nombre del centro. VenCloud los reasigna. Lo
# que sigue prueba que el ambito acierta ANTES, DURANTE y DESPUES, sin que haya
# que cambiar nada un dia concreto.
AMB = {"clientes": ["AIRBUS"]}
_m2 = L.MapaCentros()
# ANTES: cliente SERUNION para todos, el nombre del centro es lo unico que distingue
_m2.aprende([{"matricula": "A9", "centro": "AIRBUS GETAFE", "cliente": "SERUNION"},
             {"matricula": "C9", "centro": "CONSUM MURCIA", "cliente": "SERUNION"}])
comprueba("antes: entra por el nombre del centro",
          L.en_ambito({"matricula": "A9"}, AMB, _m2), True)
comprueba("antes: y Consum sigue fuera",
          L.en_ambito({"matricula": "C9"}, AMB, _m2), False)
# DESPUES: el centro ya no lleva el nombre del cliente delante, pero el campo si
_m3 = L.MapaCentros()
_m3.aprende([{"matricula": "A9", "centro": "GETAFE", "cliente": "AIRBUS OPERATIONS SL"},
             {"matricula": "C9", "centro": "MURCIA", "cliente": "CONSUM COOP V"}])
comprueba("despues: entra por el campo cliente",
          L.en_ambito({"matricula": "A9"}, AMB, _m3), True)
comprueba("despues: y Consum sigue fuera",
          L.en_ambito({"matricula": "C9"}, AMB, _m3), False)
comprueba("una fila que ya trae el cliente no necesita mapa",
          L.en_ambito({"cliente": "AIRBUS OPERATIONS SL"}, AMB, _m3), True)
comprueba("la lista de clientes vistos delata si la mudanza ha entrado",
          sorted(_m3.clientes), ["AIRBUS OPERATIONS SL", "CONSUM COOP V"])
comprueba("mientras no ha entrado, sale un solo nombre",
          sorted(_m2.clientes), ["SERUNION"])

print("\nEl resumen delata un perfil que se ha quedado sin filas")
# Es la forma de enterarse ANTES de que llame el cliente. Un ambito que deja de
# encajar —porque en VenCloud le cambiaron el nombre— no da ningun error: da un
# panel vacio, que parece un mes flojo.
porp = {p["id"]: p for p in res["perfiles"]}
comprueba("AIRBUS trae filas", porp["cli-airbus"]["filas"] > 0, True)
comprueba("y dice que declara AIRBUS", porp["cli-airbus"]["declara"], ["AIRBUS"])
comprueba("y que centros coge, con su numero delante",
          [c["nombre"] for c in porp["cli-airbus"]["coge_centros"]], ["AIRBUS GETAFE"])
comprueba("el numero es el que hay que copiar a perfiles.json",
          porp["cli-airbus"]["coge_centros"][0]["num"], "1001")
comprueba("el interno coge todo", porp["interno"]["filas"] > porp["cli-airbus"]["filas"], True)
# Y bajo que cliente de VenCloud cuelgan de verdad esos centros, que puede no
# parecerse a lo que el perfil declara.
comprueba("dice el cliente de verdad de los centros de AIRBUS",
          porp["cli-airbus"]["clientes_de_verdad"], ["AIRBUS OPERATIONS SL"])
comprueba("se cuentan los clientes leidos", res["clientes"]["total"], 2)
comprueba("y salen con su nombre de verdad",
          res["clientes"]["muestra"], ["AIRBUS OPERATIONS SL", "CONSUM S COOP V"])

# Y un perfil cuyo nombre ya no existe: cero filas y ninguna coincidencia.
ALMACEN["config/perfiles.json"] = json.dumps({"perfiles": [
    {"id": "cli-fantasma", "ambito": {"clientes": ["EMPRESA QUE YA NO SE LLAMA ASI"]}},
]}).encode()
_r2 = L.lambda_handler({}, None)
comprueba("un perfil que ya no encaja sale a cero", _r2["perfiles"][0]["filas"], 0)
comprueba("y dice que no coge ningun centro", _r2["perfiles"][0]["coge_centros"], [])

print("\nEl numero de centro aguanta un renombrado; el nombre, no")
# Es lo que paso el 4 de octubre de 2026: «AIRBUS SAN PABLO» se partio en NORTE
# y SUR. Un ambito escrito con numeros no se habria enterado.
_m4 = L.MapaCentros()
_m4.aprende([{"matricula": "P1", "num_centro": "3003", "centro": "AIRBUS SAN PABLO",
              "cliente": "SERUNION", "cod_cliente": "S1"}])
_por_nombre = {"centros": ["AIRBUS SAN PABLO"]}
_por_numero = {"centros": ["3003"]}
comprueba("antes del renombrado, el nombre vale",
          L.en_ambito({"matricula": "P1"}, _por_nombre, _m4), True)
comprueba("y el numero tambien",
          L.en_ambito({"matricula": "P1"}, _por_numero, _m4), True)
# Lo renombran: misma maquina, mismo numero de centro, nombre nuevo.
_m5 = L.MapaCentros()
_m5.aprende([{"matricula": "P1", "num_centro": "3003", "centro": "AIRBUS SAN PABLO NORTE",
              "cliente": "SERUNION", "cod_cliente": "S1"}])
comprueba("despues del renombrado, el nombre exacto ya no encaja",
          L.en_ambito({"matricula": "P1"}, _por_nombre, _m5), False)
comprueba("pero el numero sigue encajando",
          L.en_ambito({"matricula": "P1"}, _por_numero, _m5), True)
comprueba("y el codigo de cliente tambien vale como ambito",
          L.en_ambito({"matricula": "P1"}, {"clientes": ["S1"]}, _m5), True)
comprueba("un codigo que no es el suyo, no",
          L.en_ambito({"matricula": "P1"}, {"clientes": ["S9"]}, _m5), False)

print("\nEl perfiles.json de verdad coge lo que tiene que coger")
# Con los datos como los devolvio VenCloud el 4 de octubre de 2026, y con el
# fichero tal cual se despliega: si alguien le cambia un numero, esto lo dice.
import json as _json  # noqa: E402
_amb = [x for x in _json.load(open(AQUI + "/perfiles.json"))["perfiles"]
        if x["id"] == "cli-airbus"][0]["ambito"]
_m6 = L.MapaCentros()
_m6.aprende([
    {"matricula": "MG", "num_centro": "500088", "centro": "AIRBUS GETAFE",
     "cliente": "SERUNION, SA", "cod_cliente": "S1"},
    {"matricula": "MN", "num_centro": "500093", "centro": "AIRBUS SAN PABLO NORTE",
     "cliente": "SERUNION, SA", "cod_cliente": "S1"},
    {"matricula": "MX", "num_centro": "2277", "centro": "SULO IBERICA SA",
     "cliente": "SULO IBERICA SA", "cod_cliente": "S9"},
])
comprueba("coge Getafe", L.en_ambito({"matricula": "MG"}, _amb, _m6), True)
comprueba("coge San Pablo Norte, que es de despues de la mudanza",
          L.en_ambito({"matricula": "MN"}, _amb, _m6), True)
comprueba("y no coge lo que no es suyo", L.en_ambito({"matricula": "MX"}, _amb, _m6), False)
comprueba("una fila de recaudacion entra por su matricula",
          L.en_ambito({"matricula": "MG", "anho": 2026, "mes": 9}, _amb, _m6), True)
# Lo que da sentido a haber puesto numeros: que un renombrado no se lo lleve.
_m7 = L.MapaCentros()
_m7.aprende([{"matricula": "MG", "num_centro": "500088",
              "centro": "AIRBUS GETAFE (EDIFICIO NUEVO)", "cliente": "SERUNION, SA"}])
comprueba("y si manana renombran el centro, el numero aguanta",
          L.en_ambito({"matricula": "MG"}, _amb, _m7), True)
comprueba("los diez centros siguen declarados", len(_amb["centros"]), 10)

print("\nPor centro: en cual de los centros pasa")
pc = airbus["servicio"]["por_centro"]
comprueba("un centro", len(pc), 1)
comprueba("se llama como en VenCloud", pc[0]["centro"], "AIRBUS GETAFE")
comprueba("con sus 100 visitas", pc[0]["visitas"], 100)
comprueba("y una maquina", pc[0]["maquinas"], 1)
comprueba("15 tareas de SAT", pc[0]["tareas_sat"], 15)
comprueba("7 minutos de media", pc[0]["min_medio"], 7.0)
comprueba("el interno ve los dos centros", len(interno["servicio"]["por_centro"]), 2)
comprueba("ordenados por visitas", interno["servicio"]["por_centro"][0]["visitas"], 100)

print("\nUna maquina reincidente dice de que centro es")
rein = airbus["sat"]["reincidentes"]
comprueba("A1 reincide", rein[0]["m"], "A1")
comprueba("con 15 tareas", rein[0]["n"], 15)
comprueba("y su centro delante", rein[0]["c"], "AIRBUS GETAFE")

print("\nInventario y existencias: solo el ultimo cierre, nunca la suma")
comprueba("se queda con septiembre", airbus["inventario"]["periodo_balance"], "2026-09")
comprueba("4 maquinas", airbus["inventario"]["cumplimiento"]["maquinas"], 4)
comprueba("2 nunca inventariadas", airbus["inventario"]["cumplimiento"]["nunca"], 2)
comprueba("50 % en norma", airbus["inventario"]["cumplimiento"]["pct_en_norma"], 50.0)
comprueba("existencias de septiembre, no 132.456", airbus["inventario"]["existencias"]["A"], 9000.0)
comprueba("y no cuenta las 6 maquinas de agosto", airbus["inventario"]["cumplimiento"]["maquinas"], 4)

print("\nEl estado de la carga queda donde la web puede leerlo")
import datetime as _dt
_ayer = HOY - _dt.timedelta(days=1)
ALMACEN[f"registro/extraccion/anio={_ayer.year}/mes={_ayer.month:02d}/{_ayer.isoformat()}.json"] = \
    json.dumps({"ejecucion": f"{_ayer}T03:15:00Z", "dias": [str(_ayer)],
                "resumen": {"descargas_ok": 90, "descargas_fallidas": 0, "bytes": 1234},
                "ok": [{"id": "visita_cabecera", "filas": 3504}], "errores": []}).encode()
_est = L.estado_de_la_carga(HOY)
comprueba("encuentra la de ayer", _est["descargas_ok"], 90)
comprueba("y avisa de que lleva un dia de retraso", _est["retraso_dias"], 1)
comprueba("con las filas por informe", _est["filas_por_informe"]["visita_cabecera"], 3504)
comprueba("sin registro, lo dice", "retraso_dias" in L.estado_de_la_carga(HOY - _dt.timedelta(days=30)), True)

print("\nUn informe que falta no rompe la carga")
comprueba("sin stock_vehiculo, sigue habiendo panel", "servicio" in airbus, True)

# ----------------------------------------------------------------------
print("\nSumar por trozos da lo mismo que sumar de golpe")
# Es LA propiedad en la que se apoya el rediseno: si trocear cambiara el
# resultado, el ahorro de memoria no valdria nada.
import random  # noqa: E402

random.seed(7)
PARTES = []
for i in range(3000):
    sistema = i % 3 != 0
    PARTES.append({
        "empleadoid": 0 if sistema else 7,
        "empleado": "SYSTEM" if sistema else "Ana",
        "tipo_parte": 2 if sistema else 0,
        "centro": "AIRBUS GETAFE",
        "matricula": f"M{i % 40:03d}",
        "minutos": 0 if sistema else random.choice([3, 5, 7, 9, 12, 45, 387]),
        "fecha_ini": f"2026-09-{(i % 28) + 1:02d}T08:00:00",
    })
LINEAS = [{"tipo_linea": random.choice(["CM", "CM", "RC", "RM"]),
           "cantidad": random.randint(1, 40),
           "precio_coste": round(random.uniform(0.2, 2.5), 3),
           "etiq_canal": random.choice(["", "11", "V58", "A12"]),
           "centro": "AIRBUS GETAFE"} for _ in range(5000)]
MOV = [{"motivo": random.choice(["RC", "RR", "RM", "CM"]),
        "cantidad": -random.randint(1, 5),
        "puc": round(random.uniform(0.1, 1.5), 3),
        "centro": "AIRBUS GETAFE"} for _ in range(4000)]


def panel_de(trozos_partes, trozos_lineas, trozos_mov):
    acu = L.Acumulador({"id": "x", "ambito": {}})
    for c in trozos_partes:
        acu.come_partes(c)
    for c in trozos_lineas:
        acu.come_lineas(c)
    for c in trozos_mov:
        acu.come_mov_maquina(c)
    return acu.panel(HOY, {})


def trocea(lista, n):
    tam = (len(lista) + n - 1) // n
    return [lista[i:i + tam] for i in range(0, len(lista), tam)]


entero = panel_de([PARTES], [LINEAS], [MOV])
troceado = panel_de(trocea(PARTES, 17), trocea(LINEAS, 23), trocea(MOV, 11))

for campo in ("visitas", "partes_totales", "maquinas", "centros"):
    comprueba(f"{campo} igual", troceado["servicio"][campo], entero["servicio"][campo])
comprueba("coste de servicio igual",
          troceado["servicio"]["coste_servicio"]["coste"], entero["servicio"]["coste_servicio"]["coste"])
comprueba("mediana de duracion igual",
          troceado["servicio"]["duracion_min"]["mediana"], entero["servicio"]["duracion_min"]["mediana"])
comprueba("visitas por dia iguales",
          troceado["servicio"]["visitas_por_dia"], entero["servicio"]["visitas_por_dia"])
comprueba("unidades cargadas iguales",
          troceado["servicio"]["carga"]["unidades_total"], entero["servicio"]["carga"]["unidades_total"])
comprueba("unidades vendibles iguales",
          troceado["servicio"]["carga"]["unidades_vendibles"], entero["servicio"]["carga"]["unidades_vendibles"])
# El valor cargado se redondea en cada trozo, asi que puede bailar centimos:
# se compara con tolerancia, que es lo honesto, en vez de fingir que es exacto.
dif = abs(troceado["servicio"]["carga"]["valor"] - entero["servicio"]["carga"]["valor"])
comprueba(f"valor cargado igual al centimo (dif {dif:.4f})", dif < 0.05, True)
for motivo in ("caducidad", "rotura", "retirada"):
    comprueba(f"merma {motivo}: lineas",
              troceado["servicio"]["merma"][motivo]["lineas"], entero["servicio"]["merma"][motivo]["lineas"])
    d = abs(troceado["servicio"]["merma"][motivo]["euros"] - entero["servicio"]["merma"][motivo]["euros"])
    comprueba(f"merma {motivo}: euros al centimo", d < 0.05, True)

# ----------------------------------------------------------------------
print("\nEl acumulador no guarda las filas: por eso cabe la historia")
import sys  # noqa: E402


def hondo(o, vistos=None):
    vistos = vistos if vistos is not None else set()
    if id(o) in vistos:
        return 0
    vistos.add(id(o))
    t = sys.getsizeof(o)
    if isinstance(o, dict):
        t += sum(hondo(k, vistos) + hondo(v, vistos) for k, v in o.items())
    elif isinstance(o, (list, tuple, set)):
        t += sum(hondo(x, vistos) for x in o)
    return t


acu = L.Acumulador({"id": "x", "ambito": {}})
for _ in range(20):          # 60.000 partes, como dos semanas de verdad
    acu.come_partes(PARTES)
crudo_en_memoria = hondo(PARTES) * 20
acumulado = hondo(acu.__dict__)
print(f"        60.000 filas ocupan {crudo_en_memoria/1e6:.1f} MB; "
      f"el acumulador, {acumulado/1e6:.2f} MB")
comprueba("suma las 20.000 visitas", acu.visitas, 20000)
comprueba("y ocupa menos de la vigesima parte de las filas",
          acumulado < crudo_en_memoria / 20, True)

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("Los agregados salen bien.")
