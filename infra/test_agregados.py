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
    [{"empleadoid": 0, "empleado": "SYSTEM", "tipo_parte": 2, "centro": "AIRBUS GETAFE",
      "matricula": "A1", "minutos": 0, "fecha_ini": str(AYER)}] * 200
    + [{"empleadoid": 7, "empleado": "Ana", "tipo_parte": 0, "centro": "AIRBUS GETAFE",
        "matricula": "A1", "minutos": 7, "fecha_ini": str(AYER)}] * 100
    + [{"empleadoid": 7, "empleado": "Ana", "tipo_parte": 0, "centro": "CONSUM MURCIA",
        "matricula": "C1", "minutos": 400, "fecha_ini": str(AYER)}] * 10)

pon("crudo/visita_reposiciones", "visita_reposiciones", AYER,
    [{"tipo_linea": "CM", "cantidad": 10, "precio_coste": 1.0, "etiq_canal": "44", "centro": "AIRBUS GETAFE"}] * 50
    + [{"tipo_linea": "CM", "cantidad": 100, "precio_coste": 0.004, "etiq_canal": "", "centro": "AIRBUS GETAFE"}] * 50)

pon("crudo/stock_maquina", "stock_maquina", AYER,
    [{"motivo": "RC", "cantidad": -2, "puc": 0.60, "centro": "AIRBUS GETAFE"}] * 10
    + [{"motivo": "CM", "cantidad": 10, "puc": 0.60, "centro": "AIRBUS GETAFE"}] * 10)

pon("crudo/recaudacion", "recaudacion", AYER,
    [{"anho": HOY.year, "mes": HOY.month, "imp_recaudado": 100, "imp_pago_bancario": 0,
      "tipo_telemetria": 40, "criterio_calculo": 3, "centro": "AIRBUS GETAFE"}] * 3
    + [{"anho": 2026, "mes": 1, "imp_recaudado": 100, "imp_pago_bancario": 120,
        "tipo_telemetria": 0, "criterio_calculo": 3, "centro": "AIRBUS GETAFE"}] * 2)

pon("crudo/sat_averias", "sat_averias", AYER,
    [{"matricula": "00SE0000", "categoria": "ATENCION AL CLIENTE", "tipo_tarea": "A", "centro": "AIRBUS GETAFE"}] * 40
    + [{"matricula": "A1", "categoria": "AVERIAS TECNICAS", "tipo_tarea": "A", "centro": "AIRBUS GETAFE"}] * 12
    + [{"matricula": "A1", "categoria": "AVERIAS TECNICAS", "tipo_tarea": "E", "centro": "AIRBUS GETAFE"}] * 3)

pon("crudo/sat_eventos", "sat_eventos", AYER,
    [{"averia_id": 1, "estado": 0, "fecha": f"{AYER}T08:00:00", "centro": "AIRBUS GETAFE"},
     {"averia_id": 1, "estado": 99, "fecha": f"{AYER}T14:00:00", "centro": "AIRBUS GETAFE"}])

pon("crudo/jornadas", "jornadas", AYER,
    [{"temperaturaini": 2.0, "kminiciales": 100, "kmfinales": 150, "maplatitudini": 37.4, "centro": "AIRBUS GETAFE"}] * 9
    + [{"temperaturaini": 26.0, "kminiciales": 100, "kmfinales": 160, "maplatitudini": 0, "centro": "AIRBUS GETAFE"}])

pon("crudo/stock_balance", "stock_balance", AYER,
    [{"tipo_elemento": "M", "valor_total": 1000, "fecha_ult_inventario": str(HOY), "centro": "AIRBUS GETAFE"}] * 2
    + [{"tipo_elemento": "M", "valor_total": 500, "fecha_ult_inventario": "1900-01-01", "centro": "AIRBUS GETAFE"}] * 2
    + [{"tipo_elemento": "A", "valor_total": 9000, "fecha_ult_inventario": str(HOY), "centro": "AIRBUS GETAFE"}])

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
comprueba("10 lineas de caducidad", airbus["servicio"]["merma"]["caducidad"]["lineas"], 10)
comprueba("12 EUR", airbus["servicio"]["merma"]["caducidad"]["euros"], 12.0)

print("\nEl mes en curso sale marcado como provisional")
actual = [p for p in airbus["dinero"]["periodos"] if p["periodo"] == f"{HOY.year}-{HOY.month:02d}"][0]
comprueba("provisional", actual["provisional"], True)
comprueba("lleva su aviso", "tarjeta" in actual.get("_nota", ""), True)
enero = [p for p in airbus["dinero"]["periodos"] if p["periodo"] == "2026-01"][0]
comprueba("enero ya esta cerrado", enero["provisional"], False)
comprueba("efectivo ciego de enero", enero["efectivo_sin_telemetria"], 200.0)
comprueba("100 % ciego", enero["pct_ciego"], 100.0)

print("\nSAT: fuera la matricula ficticia")
comprueba("55 tareas leidas", airbus["sat"]["tareas_con_ficticia"], 55)
comprueba("15 sobre maquinas reales", airbus["sat"]["tareas"], 15)
comprueba("12 averias tecnicas", airbus["sat"]["averias_tecnicas"], 12)
comprueba("3 preventivos", airbus["sat"]["preventivos"], 3)
comprueba("6 h de cierre", airbus["sat"]["horas_cierre"]["mediana"], 6.0)

print("\nJornadas: temperatura, km y GPS")
comprueba("10 jornadas", airbus["jornadas"]["jornadas"], 10)
comprueba("1 fuera de temperatura", airbus["jornadas"]["temperatura_fuera"], 1)
comprueba("510 km", airbus["jornadas"]["km_total"], 510)
comprueba("90 % con GPS", airbus["jornadas"]["gps"]["pct"], 90.0)

print("\nInventario y existencias")
comprueba("4 maquinas", airbus["inventario"]["cumplimiento"]["maquinas"], 4)
comprueba("2 nunca inventariadas", airbus["inventario"]["cumplimiento"]["nunca"], 2)
comprueba("50 % en norma", airbus["inventario"]["cumplimiento"]["pct_en_norma"], 50.0)
comprueba("existencias en almacen", airbus["inventario"]["existencias"]["A"], 9000.0)

print("\nUn informe que falta no rompe la carga")
comprueba("sin stock_vehiculo, sigue habiendo panel", "servicio" in airbus, True)

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("Los agregados salen bien.")
