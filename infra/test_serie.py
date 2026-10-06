"""
La serie diaria (serie.py), y el relleno historico de la Lambda de agregados.

    python3 infra/test_serie.py
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
ESCRITAS = []


class _S3Falso:
    def get_object(self, Bucket, Key):
        if Key not in ALMACEN:
            raise KeyError(Key)
        cuerpo = ALMACEN[Key]
        return {"Body": types.SimpleNamespace(read=lambda: cuerpo)}

    def put_object(self, Bucket, Key, Body, **kw):
        ALMACEN[Key] = Body
        ESCRITAS.append(Key)
        return {}


class _DdbFalso:
    def scan(self, **kw):
        raise PermissionError("AccessDeniedException")


sys.modules["boto3"] = types.SimpleNamespace(
    client=lambda servicio, *a, **k: _DdbFalso() if servicio == "dynamodb" else _S3Falso())
os.environ.setdefault("BUCKET", "prueba")
os.environ["DIAS"] = "3"

import serie as S  # noqa: E402
import lambda_agregados as L  # noqa: E402

fallos = []


def comprueba(que, obtenido, esperado):
    if obtenido == esperado:
        print(f"  ok    {que}")
    else:
        print(f"  FALLO {que}: {obtenido!r} != {esperado!r}")
        fallos.append(que)


def casi(que, obtenido, esperado, margen=0.01):
    ok = obtenido is not None and abs(obtenido - esperado) <= margen
    comprueba(f"{que} ({obtenido} ~ {esperado})", ok, True)


HOY = datetime.date.today()
AYER = HOY - datetime.timedelta(days=1)
ANTEAYER = HOY - datetime.timedelta(days=2)


def parte(matricula, cuando, minutos=7, real=True):
    return {"matricula": matricula, "fecha_ini": cuando, "centro": "AIRBUS SAN PABLO SUR",
            "num_centro": 500092, "minutos": minutos,
            "tipo_parte": 0 if real else 2, "empleado": "Ana" if real else "SYSTEM",
            "empleadoid": 7 if real else 0}


# ----------------------------------------------------------------------
print("\nUn dia: contadores que se suman")
d = S.Dia(AYER)
d.come_partes([parte("M1", f"{AYER} 08:00:00", 5), parte("M1", f"{AYER} 12:00:00", 9),
               parte("M2", f"{AYER} 09:00:00", 40),
               parte("M3", f"{AYER} 00:00:09", 0, real=False)])
f = d.fila()
comprueba("la fecha", f["f"], AYER.isoformat())
comprueba("tres visitas de persona, cuatro partes",
          (f["servicio"]["visitas"], f["servicio"]["partes"]), (3, 4))
comprueba("maquinas distintas de ESE dia", f["servicio"]["maquinas_dia"], 2)
comprueba("el histograma de minutos lleva los tres valores y su suma",
          (f["servicio"]["min"]["n"], f["servicio"]["min"]["suma"]), (3, 54.0))
comprueba("y el maximo, que la cola necesita", f["servicio"]["min"]["max"], 40.0)
comprueba("el coste de servicio va aparte, que es interno",
          f["servicio"]["coste_servicio"], 24.0)

print("\nEl dinero va por periodo contable, no por el dia del fichero")
d.come_recaudacion([
    {"anho": 2025, "mes": 2, "imp_recaudado": 100.0, "imp_pago_bancario": 50.0,
     "tipo_telemetria": 0, "criterio_calculo": 3},
    {"anho": 2025, "mes": 3, "imp_recaudado": 10.0, "imp_pago_bancario": 0.0,
     "tipo_telemetria": 40, "criterio_calculo": 3},
    # Un contador roto: se aparta y se cuenta, nunca se tira en silencio.
    {"anho": 2025, "mes": 3, "imp_recaudado": 9_000_000.0, "imp_pago_bancario": 0.0,
     "tipo_telemetria": 40, "criterio_calculo": 3},
])
per = d.fila()["dinero"]["periodos"]
comprueba("dos periodos escritos el mismo dia", sorted(per), ["2025-02", "2025-03"])
comprueba("con su efectivo y su banco",
          (per["2025-02"]["efectivo"], per["2025-02"]["banco"]), (100.0, 50.0))
comprueba("el ciego solo cuenta lo que no tiene telemetria", per["2025-02"]["ciego"], 100.0)
comprueba("y la fila imposible se aparta y se cuenta",
          (per["2025-03"]["efectivo"], per["2025-03"]["imposibles"]), (10.0, 1))

print("\nUn dia sin una sola fila no se escribe")
comprueba("vacio", S.Dia(AYER).vacio(), True)
comprueba("con algo, no", d.vacio(), False)

print("\nSumar dias: los contadores se suman y las medianas salen del histograma")
dias = []
for i, (visitas, minutos) in enumerate([(2, [5, 7]), (3, [6, 6, 60]), (1, [7])]):
    x = S.Dia(datetime.date(2025, 3, i + 1))
    x.come_partes([parte(f"M{j}", f"2025-03-0{i + 1} 08:00:00", m)
                   for j, m in enumerate(minutos)])
    dias.append(x.fila())
t = S.suma_filas(dias)
comprueba("tres dias, del primero al ultimo",
          (t["dias"], t["desde"], t["hasta"]), (3, "2025-03-01", "2025-03-03"))
comprueba("las visitas se suman", t["servicio"]["visitas"], 6)
casi("la media de minutos es exacta", t["servicio"]["duracion_min"]["media"], 91 / 6)
casi("la mediana cae donde esta el dato", t["servicio"]["duracion_min"]["mediana"], 6.5, 1.0)
comprueba("y se dice que es aproximada", t["servicio"]["duracion_min"]["aprox"], True)
comprueba("las maquinas distintas NO se suman: se da el maximo de un dia",
          t["servicio"]["maquinas_dia_max"], 3)
comprueba("y se dice por que", "sumar los dias" in t["_nota_distintas"], True)
comprueba("hay una linea por dia para la grafica",
          [x["f"] for x in t["por_dia"]], ["2025-03-01", "2025-03-02", "2025-03-03"])
comprueba("un rango sin ninguna fila no inventa nada", S.suma_filas([])["dias"], 0)

print("\nEl dinero de varios dias se junta por periodo")
a, b = S.Dia(datetime.date(2025, 3, 1)), S.Dia(datetime.date(2025, 3, 2))
for x in (a, b):
    x.come_recaudacion([{"anho": 2025, "mes": 2, "imp_recaudado": 100.0,
                         "imp_pago_bancario": 0.0, "tipo_telemetria": 40,
                         "criterio_calculo": 3}])
t2 = S.suma_filas([a.fila(), b.fila()])
comprueba("dos dias del mismo periodo suman", t2["dinero"]["periodos"]["2025-02"]["efectivo"], 200.0)

print("\nLa venta: la telemetria de un dia tapa la del parte")
v = S.Dia(AYER)
v.hay_telemetria()
v.come_ventas_visita([{"matricula": "M1", "num_total": 50, "imp_total": 30.0}])
comprueba("un dia con telemetria no coge la venta del parte", v.fila()["venta"]["importe"], 0.0)
v2 = S.Dia(AYER)
v2.come_ventas_visita([{"matricula": "M1", "num_total": 50, "imp_total": 30.0},
                       {"matricula": "00SE0000", "num_total": 9, "imp_total": 9.0}])
comprueba("sin telemetria si, y sin la matricula ficticia",
          (v2.fila()["venta"]["importe"], v2.fila()["venta"]["maquinas_dia"]), (30.0, 1))
comprueba("y dice de donde sale", v2.fila()["venta"]["fuente"], "visita_ventas")

print("\nLos rangos con nombre")
HOY_FIJO = datetime.date(2026, 3, 15)
comprueba("hoy", S.rango("hoy", HOY_FIJO), ("2026-03-15", "2026-03-15"))
comprueba("ayer", S.rango("ayer", HOY_FIJO), ("2026-03-14", "2026-03-14"))
comprueba("este mes", S.rango("mes", HOY_FIJO), ("2026-03-01", "2026-03-15"))
comprueba("el mes pasado, entero", S.rango("mes_pasado", HOY_FIJO), ("2026-02-01", "2026-02-28"))
comprueba("esta semana empieza el lunes", S.rango("semana", HOY_FIJO), ("2026-03-09", "2026-03-15"))
comprueba("ultimos 30 dias", S.rango("30dias", HOY_FIJO), ("2026-02-14", "2026-03-15"))
comprueba("este anio", S.rango("anio", HOY_FIJO), ("2026-01-01", "2026-03-15"))
comprueba("todo arranca el 1 de enero de 2025", S.rango("todo", HOY_FIJO)[0], "2025-01-01")
comprueba("el mes pasado de enero es diciembre del anterior",
          S.rango("mes_pasado", datetime.date(2026, 1, 10)), ("2025-12-01", "2025-12-31"))
comprueba("cada rango tiene nombre para leer", sorted(S.NOMBRES_RANGO), sorted(S.RANGOS))
try:
    S.rango("la semana que viene")
    comprueba("un rango que no existe se niega", False, True)
except ValueError:
    comprueba("un rango que no existe se niega", True, True)

print("\nLos meses que toca un intervalo")
comprueba("de marzo a mayo", S.meses_entre("2025-03-04", "2025-05-30"),
          ["2025-03", "2025-04", "2025-05"])
comprueba("cruzando el ano", S.meses_entre("2025-12-20", "2026-01-02"), ["2025-12", "2026-01"])
comprueba("un solo dia, un mes", S.meses_entre("2025-07-07", "2025-07-07"), ["2025-07"])

print("\nFusionar un mes: el dia releido sustituye, los demas se quedan")
viejas = [{"f": "2025-03-01", "servicio": {"visitas": 1}},
          {"f": "2025-03-02", "servicio": {"visitas": 2}}]
nuevas = [{"f": "2025-03-02", "servicio": {"visitas": 9}},
          {"f": "2025-03-03", "servicio": {"visitas": 3}}]
F = S.fusiona_mes(viejas, nuevas)
comprueba("tres dias, en orden", [x["f"] for x in F],
          ["2025-03-01", "2025-03-02", "2025-03-03"])
comprueba("el dia repetido vale lo nuevo, no la suma",
          [x["servicio"]["visitas"] for x in F], [1, 9, 3])
comprueba("el resumen del mes suma lo fusionado", S.resumen_mes("2025-03", F)["visitas"], 13)

# ----------------------------------------------------------------------
print("\nLa Lambda: la noche escribe panel, cuadro y serie")


def pon(destino, id_informe, dia, filas):
    clave = (f"{destino}/anio={dia.year}/mes={dia.month:02d}/dia={dia.day:02d}/"
             f"{id_informe}.json.gz")
    ALMACEN[clave] = gzip.compress(json.dumps(filas).encode())


def censo(matricula):
    return {"cod_cliente": 10002, "cliente": "SERUNION, SA", "num_centro": 500092,
            "centro": "AIRBUS SAN PABLO SUR", "cod_pdv": "P" + matricula,
            "ubicacion": "Comedor", "matricula": matricula,
            "baja_pdv": "1900-01-01 00:00:00", "estado_pdv": 0,
            "baja_centro": "1900-01-01", "baja_cliente": "1900-01-01 00:00:00",
            "delegacion": "SEVILLA"}


ALMACEN["maestros/instalaciones/m_instalaciones.json.gz"] = gzip.compress(
    json.dumps([censo("M1"), censo("M2")]).encode())
ALMACEN["config/perfiles.json"] = json.dumps({"perfiles": [
    {"id": "interno", "ambito": {}},
    {"id": "cli-x", "nombre": "AIRBUS", "ambito": {"centros": ["500092"]}}]}).encode()
pon("crudo/visita_cabecera", "visita_cabecera", AYER, [parte("M1", f"{AYER} 08:00:00", 5)])
pon("crudo/visita_cabecera", "visita_cabecera", ANTEAYER, [parte("M2", f"{ANTEAYER} 09:00:00", 11)])
pon("crudo/visita_ventas", "visita_ventas", AYER,
    [{"matricula": "M1", "fecha_visita": f"{AYER} 08:00:00", "articulo": "AGUA",
      "num_total": 3, "imp_total": 1.8}])

res = L.lambda_handler({}, None)
MES = AYER.isoformat()[:7]


def serie_de(pid, mes):
    return json.loads(gzip.decompress(ALMACEN[f"cabina/{pid}/serie/{mes}.json.gz"]))["filas"]


comprueba("el modo es nocturna", res["modo"], "nocturna")
comprueba("hay panel", "cabina/cli-x/panel.json" in ALMACEN, True)
comprueba("y serie de los dos perfiles",
          sorted(res["serie"]), ["cli-x", "interno"])
_filas = serie_de("cli-x", MES)
comprueba("una fila por dia con dato", sorted(x["f"] for x in _filas),
          sorted({AYER.isoformat(), ANTEAYER.isoformat()} & {x["f"] for x in _filas}))
comprueba("con sus visitas", sum(x["servicio"]["visitas"] for x in _filas), 2)
comprueba("y su venta del dia que la tuvo",
          [x["venta"]["importe"] for x in _filas if x["f"] == AYER.isoformat()], [1.8])
_ix = json.loads(ALMACEN["cabina/cli-x/serie/indice.json"])
comprueba("el indice dice el primer dia de la historia", _ix["primer_dia"], "2025-01-01")
comprueba("lleva los tramos de los histogramas", sorted(_ix["bordes"]),
          ["horas_cierre", "km", "minutos", "temperatura"])
comprueba("y los rangos con nombre", _ix["rangos"]["mes_pasado"], "Mes pasado")
comprueba("con su linea por mes", [m["mes"] for m in _ix["meses"]], [MES])

print("\nEl mismo dia, partido por centro, para filtrar por delegacion, cliente y centro")
_cen = json.loads(gzip.decompress(ALMACEN[f"cabina/interno/serie/centros-{MES}.json.gz"]))["filas"]
comprueba("hay fichero de centros del mes", len(_cen) > 0, True)
comprueba("con la clave del numero de centro", sorted({c for x in _cen for c in x["centros"]}),
          ["500092"])
_todas = S.suma_filas(S.filas_de_centros(_cen))
_dia = S.suma_filas(serie_de("interno", MES))
comprueba("todos los centros juntos dan las visitas del dia",
          _todas["servicio"]["visitas"], _dia["servicio"]["visitas"])
comprueba("y la venta", _todas["venta"]["importe"], _dia["venta"]["importe"])
casi("y la media de minutos", _todas["servicio"]["duracion_min"]["media"],
     _dia["servicio"]["duracion_min"]["media"])
comprueba("un centro que no esta no suma nada",
          S.filas_de_centros(_cen, {"999"}), [])
comprueba("las jornadas no se parten por centro",
          any("jornadas" in c for x in _cen for c in x["centros"].values()), False)
_ixi = json.loads(ALMACEN["cabina/interno/serie/indice.json"])
comprueba("el indice cita el mes con centros", _ixi["meses_centros"], [MES])
comprueba("y la ficha del centro lleva su cliente y su delegacion",
          {k: _ixi["centros"]["500092"][k] for k in ("nombre", "cliente", "delegacion")},
          {"nombre": "AIRBUS SAN PABLO SUR", "cliente": "SERUNION, SA", "delegacion": "SEVILLA"})
_tabla = S.suma_centros(_cen)
comprueba("la tabla por centro cuenta sus visitas", _tabla["500092"]["visitas"],
          _dia["servicio"]["visitas"])

print("\nUn relleno historico: solo serie y cuadro, ni panel ni censo")
pon("crudo/visita_cabecera", "visita_cabecera", datetime.date(2025, 3, 11),
    [parte("M1", "2025-03-11 08:00:00", 5), parte("M2", "2025-03-11 09:00:00", 25)])
pon("crudo/visita_ventas", "visita_ventas", datetime.date(2025, 3, 11),
    [{"matricula": "M1", "fecha_visita": "2025-03-11 08:00:00", "articulo": "AGUA",
      "num_total": 10, "imp_total": 7.0}])
ESCRITAS.clear()
res_h = L.lambda_handler({"desde": "2025-03-10", "hasta": "2025-03-12"}, None)
comprueba("el modo es historico", res_h["modo"], "historico")
comprueba("no se ha reescrito ningun panel", [k for k in ESCRITAS if k.endswith("panel.json")], [])
comprueba("ni el censo anterior", [k for k in ESCRITAS if "_censo" in k], [])
comprueba("ni el estado de la carga", [k for k in ESCRITAS if "_estado" in k], [])
comprueba("se ha escrito el mes de 2025 de la serie",
          "cabina/cli-x/serie/2025-03.json.gz" in ESCRITAS, True)
_marzo = serie_de("cli-x", "2025-03")
comprueba("con el dia que tenia dato", [x["f"] for x in _marzo], ["2025-03-11"])
comprueba("y sus dos visitas", _marzo[0]["servicio"]["visitas"], 2)
comprueba("el mes de octubre sigue intacto", len(serie_de("cli-x", MES)), len(_filas))
_ix = json.loads(ALMACEN["cabina/cli-x/serie/indice.json"])
comprueba("el indice cita los dos meses", sorted(m["mes"] for m in _ix["meses"]),
          sorted(["2025-03", MES]))
comprueba("el registro del relleno va aparte del de la noche",
          any(k.startswith("registro/agregados/historico/") for k in ESCRITAS), True)
comprueba("y el cuadro tiene su mes de 2025",
          "cabina/cli-x/cuadro/mes-2025-03.json.gz" in ESCRITAS, True)

print("\nRellenar dos veces el mismo dia no lo cuenta dos veces")
L.lambda_handler({"desde": "2025-03-11", "hasta": "2025-03-11"}, None)
comprueba("siguen siendo dos visitas", serie_de("cli-x", "2025-03")[0]["servicio"]["visitas"], 2)

print("\nAntes del 1 de enero de 2025 no se rellena")
try:
    L.lambda_handler({"desde": "2024-12-31", "hasta": "2024-12-31"}, None)
    comprueba("se niega", False, True)
except ValueError as e:
    comprueba("se niega y dice desde cuando", "2025-01-01" in str(e), True)

print("\nSi se acaba el tiempo, dice por donde seguir")


class _ContextoCorto:
    """Da tiempo a un dia y a escribir; al segundo, ya no."""

    def __init__(self):
        self.llamadas = 0

    def get_remaining_time_in_millis(self):
        self.llamadas += 1
        return 900_000 if self.llamadas == 1 else 1_000


res_c = L.lambda_handler({"desde": "2025-03-10", "hasta": "2025-03-31"}, _ContextoCorto())
comprueba("lo dice en la respuesta", res_c.get("incompleto"), True)
comprueba("y por donde seguir", res_c["continuar_desde"], "2025-03-11")
comprueba("con la instruccion escrita", "desde" in res_c["_siguiente"], True)

print("\nLa serie suma lo mismo que el panel cuenta de golpe")
_panel = json.loads(ALMACEN["cabina/cli-x/panel.json"])
_t = S.suma_filas(serie_de("cli-x", MES))
comprueba("las visitas de la ventana cuadran",
          _t["servicio"]["visitas"], _panel["servicio"]["visitas"])
comprueba("y el valor cargado",
          _t["servicio"]["carga"]["valor"], _panel["servicio"]["carga"]["valor"])

# ----------------------------------------------------------------------
# La misma cuenta, en el navegador
# ----------------------------------------------------------------------
# app/comun/periodos.js suma las mismas filas en el navegador. Si las dos
# cuentas no dan lo mismo, el numero que lee el cliente no es el que decimos
# nosotros, y eso no se ve mirando ninguno de los dos ficheros por separado.
# Asi que se comparan de verdad, con node. Sin node, se dice y se salta.
print("\nEl navegador suma lo mismo que Python")
import shutil
import subprocess
import tempfile

if not shutil.which("node"):
    print("  (saltado: no hay node en esta maquina)")
else:
    _dias_js = []
    for i, (minutos, importe) in enumerate([([5, 7, 60], 10.0), ([6], 0.0), ([8, 9], 2.5)]):
        x = S.Dia(datetime.date(2025, 4, i + 1))
        x.come_partes([parte(f"M{j}", f"2025-04-0{i + 1} 08:00:00", m)
                       for j, m in enumerate(minutos)])
        x.come_recaudacion([{"anho": 2025, "mes": 3, "imp_recaudado": importe,
                             "imp_pago_bancario": 1.0, "tipo_telemetria": 40,
                             "criterio_calculo": 3}])
        x.come_jornadas([{"temperaturaini": 9.5, "kminiciales": 100, "kmfinales": 180,
                          "maplatitudini": 1}])
        _dias_js.append(x.fila())
    _py = S.suma_filas(_dias_js)
    _guion = f"""
      global.window = undefined;
      require({json.dumps(AQUI + '/../app/comun/periodos.js')});
      const P = globalThis.Periodos;
      const t = P.sumaFilas({json.dumps(_dias_js)}, {json.dumps(S.BORDES)});
      console.log(JSON.stringify({{
        visitas: t.servicio.visitas,
        carga: t.servicio.carga.valor,
        mediana: t.servicio.duracion_min.mediana,
        media: t.servicio.duracion_min.media,
        p90: t.servicio.duracion_min.p90,
        efectivo: t.dinero.periodos["2025-03"].efectivo,
        km: t.jornadas.km_total,
        temp_fuera: t.jornadas.temperatura_fuera,
        dias: t.dias,
        rango_mes: P.rango("mes", new Date(2026, 2, 15)),
        rango_pasado: P.rango("mes_pasado", new Date(2026, 0, 10)),
        rango_semana: P.rango("semana", new Date(2026, 2, 15)),
        meses: P.meses("2025-12-20", "2026-01-02")
      }}));
    """
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(_guion)
        _ruta = fh.name
    _js = json.loads(subprocess.run(["node", _ruta], capture_output=True, text=True,
                                    check=True).stdout)
    os.unlink(_ruta)
    comprueba("las visitas", _js["visitas"], _py["servicio"]["visitas"])
    casi("la mediana de minutos", _js["mediana"], _py["servicio"]["duracion_min"]["mediana"])
    casi("la media de minutos", _js["media"], _py["servicio"]["duracion_min"]["media"])
    casi("el p90", _js["p90"], _py["servicio"]["duracion_min"]["p90"])
    casi("el efectivo del periodo", _js["efectivo"], _py["dinero"]["periodos"]["2025-03"]["efectivo"])
    casi("los kilometros", _js["km"], _py["jornadas"]["km_total"])
    comprueba("las temperaturas fuera de rango", _js["temp_fuera"],
              _py["jornadas"]["temperatura_fuera"])
    comprueba("y los dias", _js["dias"], _py["dias"])
    comprueba("este mes", tuple(_js["rango_mes"]), S.rango("mes", datetime.date(2026, 3, 15)))
    comprueba("el mes pasado de enero", tuple(_js["rango_pasado"]),
              S.rango("mes_pasado", datetime.date(2026, 1, 10)))
    comprueba("esta semana empieza el lunes tambien en el navegador",
              tuple(_js["rango_semana"]), S.rango("semana", datetime.date(2026, 3, 15)))
    comprueba("y los meses de un intervalo", _js["meses"], S.meses_entre("2025-12-20", "2026-01-02"))


print("\nY filtra por centro igual que Python")
if shutil.which("node"):
    _fc = []
    for i in range(3):
        pc = S.PorCentro(lambda f: f.get("num_centro"))
        pc.come_partes([dict(parte(f"M{j}", f"2025-05-0{i + 1} 08:00:00", 4 + j + i),
                             num_centro=c)
                        for j, c in enumerate(["1", "1", "2", "3"])])
        pc.come_ventas_visita([{"matricula": "M1", "num_total": 2, "imp_total": 1.35 + i,
                                "num_centro": c} for c in ("1", "2")])
        pc.come_recaudacion([{"anho": 2025, "mes": 4, "imp_recaudado": 10.1, "imp_pago_bancario": 2,
                              "tipo_telemetria": 0, "criterio_calculo": 3, "num_centro": "3"}])
        _fc.append(pc.fila(f"2025-05-0{i + 1}"))
    _quiere = {"1", "3"}
    _py = S.suma_filas(S.filas_de_centros(_fc, _quiere))
    _pyc = S.suma_centros(_fc, _quiere)
    _guion = f"""
      require({json.dumps(AQUI + '/../app/comun/periodos.js')});
      const P = globalThis.Periodos;
      const q = new Set({json.dumps(sorted(_quiere))});
      const t = P.sumaFilas(P.filasDeCentros({json.dumps(_fc)}, q), {json.dumps(S.BORDES)});
      const c = P.sumaCentros({json.dumps(_fc)}, q);
      const fichas = {{"1": {{"cliente": "A", "delegacion": "D1"}}, "2": {{"cliente": "B", "delegacion": "D1"}},
                      "3": {{"cliente": "A", "delegacion": "D2"}}}};
      console.log(JSON.stringify({{
        visitas: t.servicio.visitas, media: t.servicio.duracion_min.media,
        mediana: t.servicio.duracion_min.mediana, importe: t.venta.importe,
        efectivo: (t.dinero.periodos["2025-04"] || {{}}).efectivo, dias: t.dias,
        c1: c["1"].visitas, c3: c["3"].min_medio, c2: c["2"] === undefined,
        porCliente: [...P.centrosElegidos(fichas, {{cliente: "A"}})].sort(),
        porDeleg: [...P.centrosElegidos(fichas, {{delegacion: "D1"}})].sort(),
        nada: P.centrosElegidos(fichas, {{}})
      }}));
    """
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(_guion)
        _ruta = fh.name
    _js = json.loads(subprocess.run(["node", _ruta], capture_output=True, text=True,
                                    check=True).stdout)
    os.unlink(_ruta)
    comprueba("las visitas de los centros elegidos", _js["visitas"], _py["servicio"]["visitas"])
    casi("la media de minutos", _js["media"], _py["servicio"]["duracion_min"]["media"])
    casi("la mediana", _js["mediana"], _py["servicio"]["duracion_min"]["mediana"])
    casi("la venta", _js["importe"], _py["venta"]["importe"])
    casi("el efectivo", _js["efectivo"], _py["dinero"]["periodos"]["2025-04"]["efectivo"])
    comprueba("los dias", _js["dias"], _py["dias"])
    comprueba("la tabla por centro", (_js["c1"], _js["c3"]), (_pyc["1"]["visitas"], _pyc["3"]["min_medio"]))
    comprueba("un centro no elegido no sale", _js["c2"], "2" not in _pyc)
    comprueba("un cliente son sus centros", _js["porCliente"], ["1", "3"])
    comprueba("una delegacion, los suyos", _js["porDeleg"], ["1", "2"])
    comprueba("sin elegir nada, sin filtro", _js["nada"], None)

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("La serie esta bien.")
