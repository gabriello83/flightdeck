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
        "matricula": "A1", "minutos": 7, "fecha_ini": str(AYER), "vehiculo": "1111AAA"}] * 100
    + [{"empleadoid": 7, "empleado": "Ana", "tipo_parte": 0, "centro": "CONSUM MURCIA", "num_centro": "2002",
        "cliente": "CONSUM S COOP V", "cod_cliente": "C9",
        "matricula": "C1", "minutos": 400, "fecha_ini": str(AYER), "vehiculo": "2222BBB"}] * 10)

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
    + [{"matricula": "A1", "categoria": "AVERIAS TECNICAS", "tipo_tarea": "E", "centro": "AIRBUS GETAFE"}] * 3
    # El preventivo de verdad: serie E con operacion de preventivo (docs/50).
    + [{"matricula": "A1", "categoria": "Solicitudes internas", "tipo_tarea": "E", "centro": "AIRBUS GETAFE",
        "operacion": "Preventivo Electrodomésticos Airbus (Interno)"}] * 2)

pon("crudo/sat_eventos", "sat_eventos", AYER,
    [{"averia_id": 1, "estado": 0, "fecha": f"{AYER}T08:00:00", "matricula": "A1"},
     {"averia_id": 1, "estado": 99, "fecha": f"{AYER}T14:00:00", "matricula": "A1"}])

# Las jornadas son de una RUTA y un vehiculo, no de un centro, y el informe no
# trae matricula: no hay forma de atribuirlas a un cliente, asi que solo salen en
# el panel interno. Tampoco hace falta: el bloque de jornadas no llega a un
# perfil de cliente (autorizacion.SESIONES lo pide a partir de «operaciones»).
pon("crudo/jornadas", "jornadas", AYER,
    [{"temperaturaini": 2.0, "kminiciales": 100, "kmfinales": 150, "maplatitudini": 37.4,
      "vehiculoid": 1, "fechafin": f"{AYER}T14:00:00"}] * 9
    + [{"temperaturaini": 26.0, "kminiciales": 100, "kmfinales": 160, "maplatitudini": 0}])
# Las visitas de la SAT traen la furgoneta del tecnico y la maquina, no el centro.
pon("crudo/sat_visitas", "sat_visitas", AYER,
    [{"averia_id": 1, "matricula": "A1", "inicio": f"{AYER} 10:00:00", "vehiculo": "3333CCC"}])
# De quien es cada furgoneta lo dice el maestro de vehiculos (M12, docs/58).
ALMACEN["maestros/vehiculos/m_vehiculos.json.gz"] = gzip.compress(json.dumps([
    {"id": 1, "cod_vehiculo": 1, "denominacion": "CRAFTER", "matricula": "1111AAA",
     "activo": True, "obsoleto": False, "delegacion": "Madrid"},
    {"id": 2, "cod_vehiculo": 2, "denominacion": "CADDY", "matricula": "2222BBB",
     "activo": True, "obsoleto": False, "delegacion": "Levante - Murcia"},
    {"id": 3, "cod_vehiculo": 3, "denominacion": "JUMPER", "matricula": "3333CCC",
     "activo": True, "obsoleto": False, "delegacion": "Madrid"}]).encode())

# DOS cierres mensuales dentro de la ventana: el de agosto y el de septiembre.
# Es lo normal con 120 dias, y sumarlos multiplicaria las existencias.
pon("crudo/stock_balance", "stock_balance", AYER,
    [{"anho": 2026, "mes": 9, "tipo_elemento": "M", "valor_total": 1000,
      "fecha_ult_inventario": str(HOY), "matricula": "A1"}] * 2
    + [{"anho": 2026, "mes": 9, "tipo_elemento": "M", "valor_total": 500,
        "fecha_ult_inventario": "1900-01-01", "matricula": "A1"}] * 2
    + [{"id": 50, "anho": 2026, "mes": 9, "tipo_elemento": "A", "valor_total": 9000,
        "fecha": f"{AYER} 21:25:41", "almacen": "Sevilla CECO L0K071 ",
        "fecha_ult_inventario": str(HOY), "matricula": "A1"}]
    + [{"anho": 2026, "mes": 8, "tipo_elemento": "M", "valor_total": 7777,
        "fecha_ult_inventario": str(HOY), "matricula": "A1"}] * 6
    + [{"anho": 2026, "mes": 8, "tipo_elemento": "A", "valor_total": 123456,
        "fecha_ult_inventario": str(HOY), "matricula": "A1"}])

# Los almacenes por dentro (docs/54). El detalle del cierre de Sevilla: el agua
# y el azucar, que luego se mueven, y el cafe, que no se mueve en la ventana.
pon("crudo/stock_balance_prod", "stock_balance_prod", AYER,
    [{"elemento_id": 50, "cod_articulo": "5322", "articulo": "AGUA", "cantidad": 900.0},
     {"elemento_id": 50, "cod_articulo": "5961", "articulo": "AZUCAR", "cantidad": 40.0},
     {"elemento_id": 50, "cod_articulo": "119162", "articulo": "CAFE", "cantidad": 60.0},
     {"elemento_id": 999, "cod_articulo": "1", "articulo": "DE UNA MAQUINA", "cantidad": 5.0}])
_ANTEAYER = AYER - datetime.timedelta(days=1)
# El agua: se compran 600 anteayer y luego van saliendo hasta quedar 80 (13 %).
pon("crudo/stock_almacen", "stock_almacen", _ANTEAYER,
    [{"id": 1, "fecha": f"{_ANTEAYER} 06:00:00", "tipo_mov": "CO", "cantidad": 600.0,
      "existencia_resultante": 650.0, "almacen": "Sevilla CECO L0K071 ", "cod_articulo": "5322",
      "articulo": "AGUA", "origen_destino": "Proveedor: FONT VELLA",
      "documento": "Albarán de compra: 77-01/10/2026"}])
pon("crudo/stock_almacen", "stock_almacen", AYER,
    # Llegan desordenados: manda la fecha, no el orden del fichero.
    [{"id": 3, "fecha": f"{AYER} 23:00:00", "tipo_mov": "SV", "cantidad": -70.0,
      "existencia_resultante": 80.0, "almacen": "Sevilla CECO L0K071 ", "cod_articulo": "5322",
      "articulo": "AGUA"},
     {"id": 2, "fecha": f"{AYER} 08:00:00", "tipo_mov": "SV", "cantidad": -500.0,
      "existencia_resultante": 150.0, "almacen": "Sevilla CECO L0K071 ", "cod_articulo": "5322",
      "articulo": "AGUA"},
     # El azucar: 200 comprados y quedan 100, el 50 %.
     {"id": 4, "fecha": f"{AYER} 09:00:00", "tipo_mov": "CO", "cantidad": 200.0,
      "existencia_resultante": 240.0, "almacen": "Sevilla CECO L0K071 ", "cod_articulo": "5961",
      "articulo": "AZUCAR", "origen_destino": "Proveedor: AZUCARERA"},
     {"id": 5, "fecha": f"{AYER} 10:00:00", "tipo_mov": "SV", "cantidad": -140.0,
      "existencia_resultante": 100.0, "almacen": "Sevilla CECO L0K071 ", "cod_articulo": "5961",
      "articulo": "AZUCAR"}])
ALMACEN["maestros/articulos/m_articulos.json.gz"] = gzip.compress(json.dumps([
    {"cod_articulo": "5322", "articulo": "AGUA", "unid_pack": 24, "unid_caja": 24,
     "codigos_barras": "8410000000016|1|0;8410000000023|24|0"},
    # El azucar solo tiene el codigo de la caja: es el que hay que senalar.
    {"cod_articulo": "5961", "articulo": "AZUCAR", "unid_pack": 0, "unid_caja": 10,
     "codigos_barras": "8410000000030|10|0"},
    {"cod_articulo": "119162", "articulo": "CAFE", "unid_pack": 6, "unid_caja": 6,
     "codigos_barras": ""},
]).encode())
import base64 as _b64  # noqa: E402
ALMACEN["maestros/articulos_fotos/m_articulos_fotos.json.gz"] = gzip.compress(json.dumps([
    {"cod_articulo": "5322", "foto": _b64.b64encode(b"\xff\xd8\xff\xe0agua").decode()},
    # Lo que no es una imagen no se guarda.
    {"cod_articulo": "5961", "foto": _b64.b64encode(b"esto no es una foto").decode()},
    # Ni la foto de un articulo que no esta en ningun almacen.
    {"cod_articulo": "424242", "foto": _b64.b64encode(b"\x89PNG\r\n\x1a\nxx").decode()},
]).encode())

# El censo de la instalacion: un maestro, con una pega de cada clase.
ALMACEN["maestros/instalaciones/m_instalaciones.json.gz"] = gzip.compress(json.dumps([
    # bien puesta: tarifa, planograma y telemetria con su dispositivo
    {"cod_cliente": "C7", "cliente": "AIRBUS OPERATIONS SL", "num_centro": "1001", "centro": "AIRBUS GETAFE",
     "cod_pdv": "P1", "matricula": "A1", "estado_pdv": 1, "tarifa_vending_pdv": 9, "cliente_activo": 1, "centro_activo": 1,
     "canales_con_articulo": 12, "telemetria": 40, "dispositivo_telemetria": "NY-001",
     "delegacion": "Madrid", "ubicacion": "Hall"},
    # sin tarifa de ninguna clase
    {"cod_cliente": "C7", "cliente": "AIRBUS OPERATIONS SL", "num_centro": "1001", "centro": "AIRBUS GETAFE",
     "cod_pdv": "P2", "matricula": "A2", "estado_pdv": 1, "canales_con_articulo": 8,
     "telemetria": 0, "delegacion": "Madrid", "ubicacion": "Taller"},
    # con telemetria y sin dispositivo: vende y la venta no llega
    {"cod_cliente": "C7", "cliente": "AIRBUS OPERATIONS SL", "num_centro": "1001", "centro": "AIRBUS GETAFE",
     "cod_pdv": "P3", "matricula": "A3", "estado_pdv": 1, "tarifa_vending_pdv": 9,
     "canales_con_articulo": 6, "telemetria": 40, "dispositivo_telemetria": "",
     "delegacion": "Madrid", "ubicacion": "Cantina"},
    # sin planograma: ni un canal con articulo
    {"cod_cliente": "C7", "cliente": "AIRBUS OPERATIONS SL", "num_centro": "1001", "centro": "AIRBUS GETAFE",
     "cod_pdv": "P4", "matricula": "A4", "estado_pdv": 1, "tarifa_ocs_centro": 3,
     "canales_con_articulo": 0, "telemetria": 0, "delegacion": "Madrid"},
    # Dado de alta la semana pasada: sale como alta reciente, con su fecha.
    {"cod_cliente": "C7", "cliente": "AIRBUS OPERATIONS SL", "num_centro": "1001", "centro": "AIRBUS GETAFE",
     "cod_pdv": "P6", "matricula": "A6", "estado_pdv": 1, "tarifa_vending_pdv": 9,
     "canales_con_articulo": 10, "telemetria": 0, "ubicacion": "Nave 4",
     "alta_pdv": (HOY - datetime.timedelta(days=6)).isoformat()},
    # Un cliente dado de baja: no sale por ninguna parte, ni sus pegas.
    {"cod_cliente": "C0", "cliente": "CLIENTE QUE SE FUE", "cliente_activo": 0,
     "num_centro": "9999", "centro": "VIEJO", "cod_pdv": "Z1", "matricula": "Z1",
     "estado_pdv": 1, "canales_con_articulo": 0, "telemetria": 40,
     "dispositivo_telemetria": ""},
    # punto de venta dado de baja: NO es una incidencia
    {"cod_cliente": "C7", "cliente": "AIRBUS OPERATIONS SL", "num_centro": "1001", "centro": "AIRBUS GETAFE",
     "cod_pdv": "P5", "matricula": "", "estado_pdv": 9, "baja_pdv": "2026-01-15",
     "canales_con_articulo": 0, "telemetria": 0},
    # sitio de siempre y sin maquina: TAMPOCO. Son 1.946 en el parque real y
    # llenarian el panel de casos que nadie va a tocar.
    {"cod_cliente": "C7", "cliente": "AIRBUS OPERATIONS SL", "num_centro": "1001", "centro": "AIRBUS GETAFE",
     "cod_pdv": "P7", "matricula": "", "estado_pdv": 0, "alta_pdv": "1900-01-01"},
    # pero uno dado de alta hace un mes y todavia vacio, SI: eso es una
    # instalacion que no ha llegado.
    {"cod_cliente": "C7", "cliente": "AIRBUS OPERATIONS SL", "num_centro": "1001", "centro": "AIRBUS GETAFE",
     "cod_pdv": "P8", "matricula": "", "estado_pdv": 0, "ubicacion": "Nave 5",
     "alta_pdv": (HOY - datetime.timedelta(days=40)).isoformat()},
    # un centro entero con puntos de venta y ni una maquina: AIRBUS PUERTO REAL
    {"cod_cliente": "C7", "cliente": "AIRBUS OPERATIONS SL", "num_centro": "1010",
     "centro": "AIRBUS PUERTO REAL", "cod_pdv": "R1", "matricula": "", "estado_pdv": 0,
     "alta_pdv": "1900-01-01", "delegacion": "Cadiz"},
    {"cod_cliente": "C7", "cliente": "AIRBUS OPERATIONS SL", "num_centro": "1010",
     "centro": "AIRBUS PUERTO REAL", "cod_pdv": "R2", "matricula": "", "estado_pdv": 0,
     "alta_pdv": "1900-01-01", "delegacion": "Cadiz"},
    # y la fila centinela de VenCloud, que no es un cliente
    {"cod_cliente": "0", "cliente": "Ventas Contado", "num_centro": "-1", "centro": "Ventas Contado",
     "cod_pdv": "-99", "matricula": "", "estado_pdv": 0},
    # centro dado de alta y sin nada puesto
    {"cod_cliente": "C7", "cliente": "AIRBUS OPERATIONS SL", "num_centro": "1009", "centro": "AIRBUS NUEVO",
     "cod_pdv": "", "matricula": ""},
    # cliente nuevo sin un solo centro
    {"cod_cliente": "C8", "cliente": "CLIENTE RECIEN FIRMADO", "num_centro": "", "centro": ""},
    # y uno de Consum, que a AIRBUS no le toca
    {"cod_cliente": "C9", "cliente": "CONSUM S COOP V", "num_centro": "2002", "centro": "CONSUM MURCIA",
     "cod_pdv": "Q1", "matricula": "C1", "estado_pdv": 1, "canales_con_articulo": 0,
     "telemetria": 40, "dispositivo_telemetria": ""},
]).encode())

# El plan de visitas de ayer (D12): un punto de venta de AIRBUS y uno de Consum.
pon("crudo/rutas_plan_visitas", "rutas_plan_visitas", AYER,
    [{"cod_pdv": "P1", "matricula": "A1", "num_centro": "1001", "centro": "AIRBUS GETAFE", "cod_cliente": "C7",
      "cliente": "AIRBUS OPERATIONS SL", "delegacion": "Madrid"},
     {"cod_pdv": "Q1", "num_centro": "2002", "centro": "CONSUM MURCIA", "cod_cliente": "C9",
      "cliente": "CONSUM S COOP V", "delegacion": "Levante - Murcia"}])

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

print("\nEl informe general operativo: un fichero por perfil, con su ambito")
op_int = json.loads(gzip.decompress(ALMACEN["cabina/interno/operativo.json.gz"]))
op_air = json.loads(gzip.decompress(ALMACEN["cabina/cli-airbus/operativo.json.gz"]))
_ayer = AYER.isoformat()
comprueba("arranca en ayer", op_air["ultimo_dia"], _ayer)
comprueba("el interno tiene en el plan los dos puntos de venta",
          op_int["dias"][_ayer]["rutas"]["previstas"], 2)
comprueba("AIRBUS, solo el suyo", op_air["dias"][_ayer]["rutas"]["previstas"], 1)
comprueba("el dia sin plan lo dice, no da cero",
          "sin_dato" in op_air["dias"][(AYER - datetime.timedelta(days=1)).isoformat()]["rutas"], True)
comprueba("almacenes: el ultimo cierre, no la suma de dos",
          (op_int["foto"]["almacenes"]["valor"], op_int["foto"]["almacenes"]["periodo"]), (9000.0, "2026-09"))
comprueba("AIRBUS no tiene almacenes, y se dice", "sin_dato" in op_air["foto"]["almacenes"], True)
comprueba("AIRBUS no cuenta las maquinas de Consum como auditables",
          op_air["dias"][_ayer]["telemetria"]["auditables"]
          < op_int["dias"][_ayer]["telemetria"]["auditables"], True)
comprueba("la reposicion de AIRBUS no lleva la de Consum",
          op_air["dias"][_ayer]["reposiciones"]["unidades"]
          < op_int["dias"][_ayer]["reposiciones"]["unidades"], True)
comprueba("el resumen dice que cuadrados se quedaron sin dato",
          "almacenes" not in res["operativo"]["interno"]["sin_dato"], True)

print("\nEl informe general por delegacion (docs/66): el filtro de area y delegacion")
_por = op_int["dias"][_ayer].get("por_delegacion") or {}
comprueba("las previstas de cada delegacion suman las del dia",
          sum(x["previstas"] for x in _por.get("rutas", {}).values()),
          op_int["dias"][_ayer]["rutas"]["previstas"])
comprueba("la reposicion por delegacion suma la del dia",
          round(sum(x["unidades"] for x in _por.get("reposiciones", {}).values()), 2),
          op_int["dias"][_ayer]["reposiciones"]["unidades"])
comprueba("auditables por delegacion suman las del dia",
          sum(x["auditables"] for x in _por.get("telemetria", {}).values()),
          op_int["dias"][_ayer]["telemetria"]["auditables"])
comprueba("AIRBUS no tiene la delegacion de Consum",
          "Levante - Murcia" in (op_air["dias"][_ayer].get("por_delegacion") or {}).get("telemetria", {}),
          False)
comprueba("cada delegacion lleva su area", op_int["zonas"].get("Levante - Murcia"), "Levante")
comprueba("las furgonetas del dia llevan su lista, para contar distintas en varios dias",
          len(op_int["dias"][_ayer]["furgonetas"]["vehiculos"]),
          op_int["dias"][_ayer]["furgonetas"]["activas"])

print("\nEl informe general por centro (docs/72): el filtro de cliente y centro")
_mes = _ayer[:7]
_pc = json.loads(gzip.decompress(ALMACEN[f"cabina/interno/operativo/centros-{_mes}.json.gz"]))["dias"][_ayer]
_pca = json.loads(gzip.decompress(ALMACEN[f"cabina/cli-airbus/operativo/centros-{_mes}.json.gz"]))["dias"][_ayer]
comprueba("el informe dice que ese mes tiene reparto por centro", _mes in op_int["meses_centros"], True)
comprueba("las previstas de cada centro suman las del dia",
          sum(x[0] for x in _pc.get("rutas", {}).values()), op_int["dias"][_ayer]["rutas"]["previstas"])
comprueba("la reposicion por centro suma la del dia",
          round(sum(x[0] for x in _pc.get("reposiciones", {}).values()), 2),
          op_int["dias"][_ayer]["reposiciones"]["unidades"])
comprueba("la venta por centro suma la del dia",
          round(sum(x[0] for x in _pc.get("ventas", {}).values()), 2),
          op_int["dias"][_ayer]["ventas"].get("importe", 0))
comprueba("cada centro del reparto tiene su ficha, con su cliente",
          all(c in op_int["centros"] and op_int["centros"][c]["c"]
              for k in ("rutas", "ventas") for c in _pc.get(k, {}) if c), True)
comprueba("AIRBUS solo tiene centros de AIRBUS",
          {op_air["centros"][c]["c"] for k in _pca for c in _pca[k] if c}, {"AIRBUS OPERATIONS SL"})

print("\nLa pagina de rutas (docs/55): un fichero por perfil, con su ambito")
_ri = json.loads(gzip.decompress(ALMACEN["cabina/interno/rutas.json.gz"]))
_ra = json.loads(gzip.decompress(ALMACEN["cabina/cli-airbus/rutas.json.gz"]))
comprueba("el interno, los dos puntos de venta del plan", _ri["dias"][_ayer]["total"]["previstas"], 2)
comprueba("AIRBUS, solo el suyo, y en su lista no sale Consum",
          (_ra["dias"][_ayer]["total"]["previstas"],
           all("CONSUM" not in " ".join(map(str, x)).upper()
               for x in _ra["dias"][_ayer]["visitas"])), (1, True))
comprueba("cada maquina de la lista, con su ubicacion del censo",
          {x[2]: x[7] for x in _ra["dias"][_ayer]["visitas"]}.get("A1"), "Hall")
comprueba("sin calendario de festivos subido, se dice (null)", _ri["festivos"], None)
comprueba("lleva las listas de maquinas y quien hizo cada ruta (docs/67)",
          all(k in _ri for k in ("por_recaudar", "sin_reponer", "nunca_repuestas", "llamadas",
                                 "control_maquinas", "quien", "zonas")), True)
comprueba("y AIRBUS no ve maquinas de fuera de su ambito",
          {x["p"] for x in _ra["sin_reponer"] + _ra["nunca_repuestas"] + _ra["por_recaudar"]}
          <= {x["p"] for x in _ri["sin_reponer"] + _ri["nunca_repuestas"] + _ri["por_recaudar"]}
          and all("CONSUM" not in x["c"].upper() for x in _ra["nunca_repuestas"]) and bool(_ri["nunca_repuestas"]),
          True)

print("\nLa pagina de furgonetas (docs/58): un fichero por perfil, con su ambito")
_fi = json.loads(gzip.decompress(ALMACEN["cabina/interno/furgonetas.json.gz"]))
_fa = json.loads(gzip.decompress(ALMACEN["cabina/cli-airbus/furgonetas.json.gz"]))
comprueba("el interno: toda la flota activa del maestro, con o sin visitas",
          [x["m"] for x in _fi["flota"]], ["2222BBB", "1111AAA", "3333CCC"])
comprueba("AIRBUS: solo las que visitaron su ambito, tambien la del tecnico",
          [x["m"] for x in _fa["flota"]], ["1111AAA", "3333CCC"])
comprueba("los dias con visita, cada perfil los suyos",
          (_fi["visitas"], _fa["visitas"]),
          ({"1111AAA": [_ayer], "2222BBB": [_ayer], "3333CCC": [_ayer]},
           {"1111AAA": [_ayer], "3333CCC": [_ayer]}))
comprueba("los km del dia, de la jornada sin centro, con el maestro (las nueve repetidas cuentan una)",
          (_fi["km"][_ayer], _fa["km"][_ayer]), ({"1111AAA": [50, 9, ""]}, {"1111AAA": [50, 9, ""]}))
_hk = json.loads(gzip.decompress(ALMACEN["cabina/_furgonetas/jornadas.json.gz"]))
comprueba("la historia de jornadas, desde el 1-ene-2025 hasta ayer, tambien los dias vacios",
          (min(_hk), max(_hk), len(_hk[_ayer]["1"])), ("2025-01-01", _ayer, 9))
comprueba("los km acumulados y la persona, en la flota",
          {x["m"]: (x["km"], x["z"]) for x in _fi["flota"]},
          {"1111AAA": (50, "Centro"), "2222BBB": (0, "Levante"), "3333CCC": (0, "Centro")})
comprueba("desde el primer dia que leyo la noche", _fi["desde"], min(_fi["dias"]))

print("\nLos almacenes por dentro (docs/54)")
_al = json.loads(gzip.decompress(ALMACEN["cabina/interno/almacenes.json.gz"]))
_sev = {p["cod"]: p for p in _al["almacenes"][0]["productos"]}
comprueba("un almacen, con el nombre limpio", [a["almacen"] for a in _al["almacenes"]],
          ["Sevilla CECO L0K071"])
comprueba("la existencia es la del ultimo movimiento por fecha, no por orden del fichero",
          (_sev["5322"]["existencias"], _sev["5322"]["de"]), (80.0, "movimiento"))
comprueba("la ultima compra, con su proveedor",
          (_sev["5322"]["compra"]["cantidad"], _sev["5322"]["compra"]["proveedor"]), (600.0, "FONT VELLA"))
comprueba("80 de 600 es menos del 15 %: bajo minimo", (_sev["5322"]["pct"], _sev["5322"]["bajo"]),
          (13.3, True))
comprueba("100 de 200 no", _sev["5961"]["bajo"], False)
comprueba("el cafe no se movio: cantidad del cierre, sin compra",
          (_sev["119162"]["existencias"], _sev["119162"]["de"], "compra" in _sev["119162"]),
          (60.0, "cierre", False))
comprueba("lo de una maquina no entra", "1" in _sev, False)
comprueba("el bajo minimo va primero", _al["almacenes"][0]["productos"][0]["cod"], "5322")
comprueba("unidades por pack y caja del maestro", (_sev["5322"]["unid_pack"], _sev["5322"]["unid_caja"]),
          (24, 24))
comprueba("el pack a cero es que no esta", _sev["5961"]["unid_pack"], None)
comprueba("codigo de la unidad: el de cantidad 1", _sev["5322"]["ean_unidad"], ["8410000000016"])
comprueba("el azucar solo tiene el de la caja", (_sev["5961"]["ean_unidad"],
          _sev["5961"]["otros_codigos"]), ([], [{"codigo": "8410000000030", "cantidad": 10}]))
comprueba("el resumen los cuenta", (_al["total"]["bajo_minimo"], _al["total"]["sin_codigo_unidad"],
          _al["total"]["sin_pack"], _al["total"]["sin_foto"]), (1, 2, 1, 2))
comprueba("con maestro y fotos no hay avisos", _al["avisos"], [])
comprueba("la foto se guarda una vez, como imagen", ALMACEN.get("cabina/_articulos/fotos/5322"),
          b"\xff\xd8\xff\xe0agua")
comprueba("lo que no es imagen, no", "cabina/_articulos/fotos/5961" in ALMACEN, False)
comprueba("ni la de un articulo fuera de los almacenes", "cabina/_articulos/fotos/424242" in ALMACEN,
          False)
comprueba("AIRBUS no tiene almacenes: ni fichero", "cabina/cli-airbus/almacenes.json.gz" in ALMACEN,
          False)
comprueba("el cuadrado lleva cuantos estan bajo minimo", op_int["foto"]["almacenes"]["bajo_minimo"], 1)
comprueba("y la respuesta lo dice", res["almacenes"]["perfiles"]["interno"],
          {"productos": 3, "bajo_minimo": 1})

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
comprueba("57 tareas leidas", airbus["sat"]["tareas_con_ficticia"], 57)
comprueba("17 sobre maquinas reales", airbus["sat"]["tareas"], 17)
comprueba("12 averias tecnicas: la serie E no cuenta", airbus["sat"]["averias_tecnicas"], 12)
comprueba("2 preventivos: los de operacion de preventivo, no toda la serie E",
          airbus["sat"]["preventivos"], 2)
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
comprueba("se cuentan los clientes leidos", res["clientes"]["total"], 4)
comprueba("y salen con su nombre de verdad", res["clientes"]["muestra"],
          ["AIRBUS OPERATIONS SL", "CLIENTE QUE SE FUE", "CLIENTE RECIEN FIRMADO",
           "CONSUM S COOP V"])
comprueba("la fila centinela de VenCloud no cuenta como cliente",
          "Ventas Contado" not in str(res["clientes"]["muestra"]), True)

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

print("\nInstalaciones: el censo y lo que esta puesto a medias")
inst = airbus["instalaciones"]
comprueba("cuenta los clientes del ambito", inst["censo"]["clientes"], 1)
comprueba("y sus centros", inst["censo"]["centros"], 3)
comprueba("y sus puntos de venta", inst["censo"]["pdvs"], 10)
inc = inst["incidencias"]
comprueba("una sin tarifa", inc["sin_tarifa"]["n"], 1)
comprueba("y dice cual", inc["sin_tarifa"]["casos"][0]["pdv"], "P2")
comprueba("una sin planograma", inc["sin_planograma"]["n"], 1)
comprueba("una con telemetria y sin dispositivo", inc["telemetria_sin_dato"]["n"], 1)
comprueba("y dice cual", inc["telemetria_sin_dato"]["casos"][0]["m"], "A3")
comprueba("un centro sin puntos de venta", inc["centro_sin_pdv"]["n"], 1)
comprueba("una instalacion pendiente", inc["instalacion_pendiente"]["n"], 1)
# Un centro entero vacio no se ve en ninguna fila sola: hay que recorrerlo.
# Es lo que le paso a AIRBUS PUERTO REAL, con 22 puntos de venta y 0 maquinas.
comprueba("y un centro sin una sola maquina", inc["centro_sin_maquinas"]["n"], 1)
comprueba("con su numero", inc["centro_sin_maquinas"]["casos"][0]["num_centro"], "1010")
comprueba("y cuantos puntos de venta tiene",
          inc["centro_sin_maquinas"]["casos"][0]["pdv"], "2 puntos de venta")
comprueba("y es la de hace un mes", inc["instalacion_pendiente"]["casos"][0]["pdv"], "P8")
comprueba("el sitio de siempre sin maquina NO es una incidencia",
          any(c["pdv"] == "P7" for i in inc.values() for c in i["casos"]), False)
comprueba("ni la fila centinela de VenCloud", "Ventas Contado" not in str(inc), True)
comprueba("el punto de venta de baja NO es una incidencia",
          any(c["pdv"] == "P5" for i in inc.values() for c in i["casos"]), False)
comprueba("la de Consum no se cuela", "Q1" not in str(inc), True)
comprueba("el catalogo explica cada una", len(inst["catalogo"]), 7)
comprueba("y dice por que importa",
          "efectivo ciego" in inst["catalogo"]["telemetria_sin_dato"]["porque"], True)
# El cliente sin centros es del interno: AIRBUS no lo ve, y es correcto.
comprueba("el interno si ve el cliente sin centros",
          interno["instalaciones"]["incidencias"]["cliente_sin_centros"]["n"], 1)
comprueba("un cliente dado de baja no da ni una incidencia",
          "CLIENTE QUE SE FUE" not in str(interno["instalaciones"]["incidencias"]), True)

print("\nLas altas se leen de VenCloud, no se adivinan")
alt = inst["altas_recientes"]
comprueba("un punto de venta de alta esta semana", len(alt["pdvs"]), 1)
comprueba("con su codigo", alt["pdvs"][0]["id"], "P6")
comprueba("y su fecha de verdad", alt["pdvs"][0]["cuando"],
          (HOY - datetime.timedelta(days=6)).isoformat())
comprueba("y su ubicacion, que es lo que se lee", alt["pdvs"][0]["nombre"], "Nave 4")
comprueba("lo de hace anos no sale", len(alt["clientes"]), 0)

print("\nLa primera vez no se inventa ninguna alta")
comprueba("nuevos vacio", inst["nuevos"], {})
comprueba("y lo dice", "primera vez" in inst["_nota_nuevos"], True)

print("\nY a la siguiente, lo que haya aparecido sale como alta")
_censo = json.loads(gzip.decompress(ALMACEN["maestros/instalaciones/m_instalaciones.json.gz"]))
_censo.append({"cod_cliente": "C7", "cliente": "AIRBUS OPERATIONS SL", "num_centro": "1001",
               "centro": "AIRBUS GETAFE", "cod_pdv": "P9", "matricula": "A9",
               "estado_pdv": 1, "tarifa_vending_pdv": 9, "canales_con_articulo": 4,
               "telemetria": 40, "dispositivo_telemetria": "NY-009"})
ALMACEN["maestros/instalaciones/m_instalaciones.json.gz"] = gzip.compress(json.dumps(_censo).encode())
# La prueba del perfil fantasma dejo otro perfiles.json puesto: se devuelve el
# bueno, o esta ejecucion no calcularia el panel de AIRBUS.
ALMACEN["config/perfiles.json"] = json.dumps({"perfiles": [
    {"id": "interno", "ambito": {}},
    {"id": "cli-airbus", "ambito": {"clientes": ["AIRBUS"], "centros": [], "delegaciones": []}},
]}).encode()
L.lambda_handler({}, None)
_inst2 = json.loads(ALMACEN["cabina/cli-airbus/panel.json"])["instalaciones"]
comprueba("sale el punto de venta nuevo", _inst2["nuevos"]["pdvs"], ["P9"])
comprueba("y su maquina", _inst2["nuevos"]["maquinas"], ["A9"])
comprueba("y nada mas", _inst2["nuevos"]["clientes"], [])

print("\nTarifas (docs/52): sin maestro se dice; con maestro, resumen y un fichero por centro")
_op = json.loads(gzip.decompress(ALMACEN["cabina/interno/operativo.json.gz"]))
comprueba("sin el maestro, el cuadrado dice por que", "M10 · EXT_MAESTRO_TARIFAS" in _op["foto"]["tarifas"]["sin_dato"], True)
comprueba("y no se escribe ningun resumen que parezca bueno",
          [k for k in ALMACEN if "/tarifas/" in k and k.startswith("cabina/interno")], [])
comprueba("el estado de seis meses se guarda igual", "cabina/_tarifas/estado.json.gz" in ALMACEN, True)
_dia = AYER - datetime.timedelta(days=2)
pon("crudo/visita_reposiciones", "visita_reposiciones", _dia,
    [{"tipo_linea": "CM", "cantidad": 5, "etiq_canal": "11", "matricula": "A1",
      "cod_articulo": "9354", "fecha": f"{_dia} 09:00:00"},
     {"tipo_linea": "CM", "cantidad": 5, "etiq_canal": "12", "matricula": "A1",
      "cod_articulo": "7777", "fecha": f"{_dia} 09:00:00"},
     {"tipo_linea": "CM", "cantidad": 5, "etiq_canal": "11", "matricula": "C1",
      "cod_articulo": "9354", "fecha": f"{_dia} 09:00:00"}])
pon("crudo/telemetria_ventas", "telemetria_ventas", _dia,
    [{"matricula": "A1", "cod_articulo": "9354", "precio": 1.3, "linea_precio": 2,
      "fecha_venta": f"{_dia} 10:00:00", "num_centro": "1001", "centro": "AIRBUS GETAFE"},
     {"matricula": "A1", "cod_articulo": "7777", "precio": 2.0, "linea_precio": 2,
      "fecha_venta": f"{_dia} 10:00:00", "num_centro": "1001", "centro": "AIRBUS GETAFE"}])
ALMACEN["maestros/tarifas/m_tarifas.json.gz"] = gzip.compress(json.dumps([
    {"id": "T1", "origen": "tarifa", "nivel": "tarifa", "tarifa_id": 9, "tarifa": "AIRBUS 2026",
     "cod_articulo": "9354", "precio_ef": 1.2, "precio_tp": 1.2, "precio_tc": 1.2,
     "fecha_cambio": "2026-01-01 00:00:00"},
    {"id": "A1", "origen": "articulo", "nivel": "articulo", "cod_articulo": "9354",
     "articulo": "COCA COLA LATA 33CL"}]).encode())
L.lambda_handler({}, None)
_res = json.loads(gzip.decompress(ALMACEN["cabina/cli-airbus/tarifas/resumen.json.gz"]))
_cen = json.loads(gzip.decompress(ALMACEN["cabina/cli-airbus/tarifas/centros/1001.json.gz"]))
comprueba("AIRBUS: 9354 cobra 1,30 con tarifa de 1,20, y 7777 no tiene tarifa",
          sorted((f["cod_articulo"], f["estado"]) for f in _cen["filas"]),
          [("7777", "sin_tarifa"), ("9354", "no_coincide")])
comprueba("con el nombre del articulo, del maestro",
          [f["articulo"] for f in _cen["filas"] if f["cod_articulo"] == "9354"], ["COCA COLA LATA 33CL"])
comprueba("el resumen: 0 de 1, y uno sin tarifa",
          (_res["total"]["coincide"], _res["total"]["controlados"], _res["total"]["sin_tarifa"]), (0, 1, 1))
comprueba("la maquina de Consum no es de AIRBUS",
          [k for k in ALMACEN if k.startswith("cabina/cli-airbus/tarifas/centros/")],
          ["cabina/cli-airbus/tarifas/centros/1001.json.gz"])
_op = json.loads(gzip.decompress(ALMACEN["cabina/cli-airbus/operativo.json.gz"]))
comprueba("el cuadrado del informe operativo: 0 %, rojo",
          (_op["foto"]["tarifas"]["pct"], _op["foto"]["tarifas"]["color"]), (0.0, "rojo"))
del ALMACEN["maestros/tarifas/m_tarifas.json.gz"]

print("\nIncidencias (docs/56): sin M13, sin estado; con M13, la foto de hoy y con su ambito")
_inc = json.loads(gzip.decompress(ALMACEN["cabina/interno/incidencias.json.gz"]))
comprueba("sin M13 el fichero sale, pero dice que no tiene el estado",
          (_inc["estado_al_dia"], "M13" in _inc["sin_estado"]), (False, True))
_hace10 = (AYER - datetime.timedelta(days=10)).isoformat()
ALMACEN["maestros/sat_incidencias/m_sat_incidencias.json.gz"] = gzip.compress(json.dumps([
    # Abierta hace diez dias y cerrada ayer: en el crudo de la ventana seguiria abierta.
    {"id": 501, "serie": "A", "numero": 9001, "fecha_alta": _hace10, "tipo_estado": 9, "estado": 99,
     "apertura": f"{_hace10} 08:00:00", "cierre": f"{AYER} 09:00:00", "cod_operacion": "T08",
     "operacion": "CAFÉ - Distribuidor fuera de servicio", "categoria": "AVERIAS TECNICAS",
     "matricula": "A1", "num_centro": "1001", "centro": "AIRBUS GETAFE", "cod_cliente": "C7",
     "cliente": "AIRBUS OPERATIONS SL", "delegacion": "Madrid - Leganes", "titulo": "no sale cafe"},
    {"id": 502, "serie": "A", "numero": 9002, "fecha_alta": str(AYER), "tipo_estado": 1, "estado": 1,
     "apertura": f"{AYER} 10:00:00", "cierre": None, "cod_operacion": "T08",
     "operacion": "CAFÉ - Distribuidor fuera de servicio", "categoria": "AVERIAS TECNICAS",
     "matricula": "C1", "num_centro": "2002", "centro": "CONSUM MURCIA", "cod_cliente": "C9",
     "cliente": "CONSUM S COOP V", "delegacion": "Levante - Murcia", "titulo": "pantalla negra"},
    {"id": 503, "serie": "A", "numero": 9003, "fecha_alta": str(AYER), "tipo_estado": 1,
     "matricula": "00SE0000", "centro": "CENTRO TEST", "apertura": f"{AYER} 10:00:00"},
    # Una devolucion de AIRBUS, abierta: va a su pagina, no a la de incidencias (docs/57).
    {"id": 504, "serie": "A", "numero": 9004, "fecha_alta": str(AYER), "tipo_estado": 1, "estado": 1,
     "apertura": f"{AYER} 11:00:00", "cierre": None, "cod_operacion": "D03",
     "operacion": "DEVOLUCION - Transferencia Bancaria", "categoria": "ATENCION AL CLIENTE",
     "matricula": "A1", "num_centro": "1001", "centro": "AIRBUS GETAFE", "cod_cliente": "C7",
     "cliente": "AIRBUS OPERATIONS SL", "delegacion": "Madrid - Leganes", "titulo": "IBAN ES00 1111"},
]).encode())
# Las devoluciones, de la Gestion de Devoluciones (M16, docs/57): una de AIRBUS
# abonada y una de Consum en estudio.
ALMACEN["maestros/devoluciones/m_devoluciones.json.gz"] = gzip.compress(json.dumps([
    {"id": 1, "numero": 47001, "fecha": f"{AYER} 11:00:00", "estado_devolucion": 3,
     "tipo_devolucion_nombre": "Transferencia", "importe": 1.3, "motivo": "No da producto",
     "matricula": "A1", "num_centro": "1001", "centro": "AIRBUS GETAFE", "cod_cliente": "C7",
     "cliente": "AIRBUS OPERATIONS SL", "delegacion": "Madrid - Leganes"},
    {"id": 2, "numero": 47002, "fecha": f"{AYER} 12:00:00", "estado_devolucion": 1,
     "tipo_devolucion_nombre": "Sin devolución", "importe": 2, "motivo": "No da producto",
     "matricula": "C1", "num_centro": "2002", "centro": "CONSUM MURCIA", "cod_cliente": "C9",
     "cliente": "CONSUM S COOP V", "delegacion": "Levante - Murcia"},
]).encode())
L.lambda_handler({}, None)
_inc = json.loads(gzip.decompress(ALMACEN["cabina/interno/incidencias.json.gz"]))
_inc_air = json.loads(gzip.decompress(ALMACEN["cabina/cli-airbus/incidencias.json.gz"]))
comprueba("con M13, al dia", _inc["estado_al_dia"], True)
comprueba("el interno tiene las dos, sin la ficticia", sorted(x["n"] for x in _inc["incidencias"]),
          ["A-9001", "A-9002"])
comprueba("AIRBUS solo la suya", [x["n"] for x in _inc_air["incidencias"]], ["A-9001"])
comprueba("cerrada a las 241 horas", [x.get("h") for x in _inc_air["incidencias"]], [241.0])
comprueba("la abierta de Consum lleva su texto en el interno",
          [x.get("tx") for x in _inc["incidencias"] if x["n"] == "A-9002"], ["pantalla negra"])
_op = json.loads(gzip.decompress(ALMACEN["cabina/cli-airbus/operativo.json.gz"]))
comprueba("y el cuadrado de AIRBUS ve el cierre del decimo dia, fuera de 24 h",
          (_op["dias"][AYER.isoformat()]["averias"]["cerradas"],
           _op["dias"][AYER.isoformat()]["averias"]["a_tiempo"]), (1, 0))
_dev = json.loads(gzip.decompress(ALMACEN["cabina/cli-airbus/devoluciones.json.gz"]))
comprueba("AIRBUS solo ve su devolucion, de M16", [x["n"] for x in _dev["devoluciones"]], ["47001"])
comprueba("y el cuadrado de AIRBUS dice el dinero abonado",
          (_op["foto"]["devoluciones"]["total"], _op["foto"]["devoluciones"]["importe"]), (1, 1.3))
_op_int = json.loads(gzip.decompress(ALMACEN["cabina/interno/operativo.json.gz"]))
comprueba("el interno ve las dos, la de Consum sin resolver",
          (_op_int["foto"]["devoluciones"]["total"], _op_int["foto"]["devoluciones"]["sin_resolver"]), (2, 1))
comprueba("y no entra en las incidencias", "A-9004" in [x["n"] for x in _inc_air["incidencias"]], False)
del ALMACEN["maestros/sat_incidencias/m_sat_incidencias.json.gz"]
del ALMACEN["maestros/devoluciones/m_devoluciones.json.gz"]

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
comprueba("17 tareas de SAT", pc[0]["tareas_sat"], 17)
comprueba("7 minutos de media", pc[0]["min_medio"], 7.0)
comprueba("el interno ve los dos centros", len(interno["servicio"]["por_centro"]), 2)
comprueba("ordenados por visitas", interno["servicio"]["por_centro"][0]["visitas"], 100)

print("\nUna maquina reincidente dice de que centro es")
rein = airbus["sat"]["reincidentes"]
comprueba("A1 reincide", rein[0]["m"], "A1")
comprueba("con 17 tareas", rein[0]["n"], 17)
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

print("\nEl relleno historico escribe el informe general (docs/66) sin tocar la foto")
_antes = json.loads(gzip.decompress(ALMACEN["cabina/interno/operativo.json.gz"]))
_desde = (AYER - datetime.timedelta(days=2)).isoformat()
_rh = L.lambda_handler({"desde": _desde, "hasta": AYER.isoformat()}, None)
_desp = json.loads(gzip.decompress(ALMACEN["cabina/interno/operativo.json.gz"]))
comprueba("escribe los tres dias del tramo", _rh["operativo"]["interno"]["dias"], 3)
comprueba("la foto de la noche se queda", _desp["foto"].get("pdvs"), _antes["foto"].get("pdvs"))
comprueba("y la telemetria que ya tenia el dia, tambien",
          _desp["dias"][AYER.isoformat()]["telemetria"], _antes["dias"][AYER.isoformat()]["telemetria"])
comprueba("la reposicion del dia sale igual que de noche",
          _desp["dias"][AYER.isoformat()]["reposiciones"], _antes["dias"][AYER.isoformat()]["reposiciones"])
comprueba("y las averias que ya tenia el dia (con M13), tambien",
          _desp["dias"][AYER.isoformat()]["averias"], _antes["dias"][AYER.isoformat()]["averias"])
_mes = AYER.isoformat()[:7]
_hist = json.loads(gzip.decompress(ALMACEN[f"cabina/interno/operativo/dias-{_mes}.json.gz"]))
comprueba("la historia del informe va en un fichero por mes (docs/75)",
          AYER.isoformat() in _hist["dias"], True)
comprueba("y el fichero dice que dias tiene cada mes",
          AYER.day in _desp["meses_dias"][_mes], True)
_rut = json.loads(gzip.decompress(ALMACEN[f"cabina/interno/rutas/dias-{_mes}.json.gz"]))
comprueba("la de rutas tambien, sin la lista maquina a maquina",
          (AYER.isoformat() in _rut["dias"], "visitas" in _rut["dias"][AYER.isoformat()]), (True, False))
comprueba("y el fichero de rutas dice que dias tiene cada mes",
          AYER.day in json.loads(gzip.decompress(ALMACEN["cabina/interno/rutas.json.gz"]))["meses_dias"][_mes],
          True)
_fur = ALMACEN.get(f"cabina/interno/furgonetas/dias-{_mes}.json.gz")
comprueba("la de furgonetas tambien, con los km de cada dia",
          _fur is not None and AYER.isoformat() in json.loads(gzip.decompress(_fur))["dias"], True)
ALMACEN["cabina/nuevo/rutas/dias-2025-03.json.gz"] = gzip.compress(
    json.dumps({"dias": {"2025-03-04": {}, "2025-03-05": {}}}).encode())
_cg = L.con_los_meses_guardados("nuevo", "rutas", None, {_mes: {"dias": {AYER.isoformat(): {}}}}, AYER)
comprueba("un panel nuevo sin fichero de rutas ve los meses ya guardados",
          (sorted(_cg), sorted(L.OP.meses_dias(None, _cg, {})["2025-03"])), (["2025-03", _mes], [4, 5]))
comprueba("y si el fichero ya dice sus meses, no se lee nada mas",
          sorted(L.con_los_meses_guardados("nuevo", "rutas", {"meses_dias": {}}, {}, AYER)), [])
del ALMACEN["cabina/nuevo/rutas/dias-2025-03.json.gz"]
comprueba("la SAT de antes del tramo se lee, sin pasar del primer dia",
          (len(L.previos_averias(datetime.date(2026, 3, 1))),
           len(L.previos_averias(datetime.date(2025, 1, 10)))), (120, 9))

print("\nUtilizo (docs/60): los dias de M15 que se leen")
_h = datetime.date(2026, 10, 19)
comprueba("de noche, los cuatro anteriores a hoy",
          [d.isoformat() for d in L.dias_actividad(_h)],
          ["2026-10-15", "2026-10-16", "2026-10-17", "2026-10-18"])
_r = L.dias_actividad(_h, "2025-01-01")
comprueba("con utilizo_desde, desde esa fecha hasta ayer",
          (_r[0].isoformat(), _r[-1].isoformat(), len(_r)), ("2025-01-01", "2026-10-18", 656))

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("Los agregados salen bien.")
