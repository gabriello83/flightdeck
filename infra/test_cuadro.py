"""
El cuadro de mando de David (cuadro.py), y como lo escribe la Lambda.

    python3 infra/test_cuadro.py
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
LEIDAS = []


class _S3Falso:
    def get_object(self, Bucket, Key):
        LEIDAS.append(Key)
        if Key not in ALMACEN:
            raise KeyError(Key)
        cuerpo = ALMACEN[Key]
        return {"Body": types.SimpleNamespace(read=lambda: cuerpo)}

    def put_object(self, Bucket, Key, Body, **kw):
        ALMACEN[Key] = Body
        return {}


# La tabla de la consola. None = la Lambda no tiene permiso para leerla.
CONSOLA = {"fichas": None}


class _DdbFalso:
    """Devuelve las fichas de dos en dos, para que se vea que pagina."""

    def scan(self, TableName, FilterExpression, ExpressionAttributeValues, ExclusiveStartKey=None):
        if CONSOLA["fichas"] is None:
            raise PermissionError("AccessDeniedException: not authorized to perform dynamodb:Scan")
        items = [{"pk": {"S": f"PERFIL#{pid}"}, "sk": {"S": "FICHA"},
                  "dato": {"S": json.dumps(d)}} for pid, d in CONSOLA["fichas"]]
        items.append({"pk": {"S": "USUARIO#ana@x.com"}, "sk": {"S": "FICHA"}, "dato": {"S": "{}"}})
        p = ExpressionAttributeValues[":p"]["S"]
        items = [i for i in items if i["pk"]["S"].startswith(p)]
        ini = ExclusiveStartKey["n"] if ExclusiveStartKey else 0
        res = {"Items": items[ini:ini + 2]}
        if ini + 2 < len(items):
            res["LastEvaluatedKey"] = {"n": ini + 2}
        return res


sys.modules["boto3"] = types.SimpleNamespace(
    client=lambda servicio, *a, **k: _DdbFalso() if servicio == "dynamodb" else _S3Falso())
os.environ.setdefault("BUCKET", "prueba")
os.environ["DIAS"] = "3"

import cuadro as C  # noqa: E402
import lambda_agregados as L  # noqa: E402

fallos = []


def comprueba(que, obtenido, esperado):
    if obtenido == esperado:
        print(f"  ok    {que}")
    else:
        print(f"  FALLO {que}: {obtenido!r} != {esperado!r}")
        fallos.append(que)


HOY = datetime.date.today()
AYER = HOY - datetime.timedelta(days=1)
ANTEAYER = HOY - datetime.timedelta(days=2)
PERIODO = {"desde": (HOY - datetime.timedelta(days=3)).isoformat(), "hasta": AYER.isoformat(), "dias": 3}
PERFIL = {"id": "cli-x", "nombre": "AIRBUS", "ambito": {"centros": ["500092"]}}


def censo(matricula, ubicacion="Comedor", **extra):
    fila = {"cod_cliente": 10002, "cliente": "SERUNION, SA", "num_centro": 500092,
            "centro": "AIRBUS SAN PABLO SUR", "cod_pdv": "P" + matricula, "ubicacion": ubicacion,
            "matricula": matricula, "baja_pdv": "1900-01-01 00:00:00", "estado_pdv": 0,
            "baja_centro": "1900-01-01", "baja_cliente": "1900-01-01 00:00:00"}
    fila.update(extra)
    return fila


def parte(matricula, cuando, real=True):
    return {"matricula": matricula, "fecha_ini": cuando, "centro": "AIRBUS SAN PABLO SUR",
            "num_centro": 500092, "cod_pdv": "P" + matricula,
            "tipo_parte": 0 if real else 2, "empleado": "Ana" if real else "SYSTEM",
            "empleadoid": 7 if real else 0}


def tarea(numero, matricula, serie="A", tipo_estado=9, fin=None, operacion="TECNICO - No enfría"):
    return {"serie": serie, "numero": numero, "fecha_alta": AYER.isoformat(),
            "fecha_fin": fin or AYER.isoformat(), "tipo_estado": tipo_estado,
            "matricula": matricula, "centro": "AIRBUS SAN PABLO SUR", "num_centro": 500092,
            "categoria": "AVERIAS TECNICAS", "operacion": operacion, "ubicacion": "Comedor"}


# ----------------------------------------------------------------------
print("\nEl censo: la poblacion de maquinas")
c = C.Cuadro()
c.come_instalaciones([
    censo("M1"), censo("M2", "Hangar"),
    censo("M3", baja_pdv="2026-05-01 00:00:00"),           # punto de venta dado de baja
    censo("", cod_pdv="P0"),                               # punto de venta sin maquina
    dict(censo("M9"), cod_cliente=0, num_centro=-1, cod_pdv="-99"),  # la centinela
])
comprueba("solo las vivas, con maquina y sin centinela", sorted(c.censo), ["M1", "M2"])
comprueba("con su ubicacion", c.censo["M2"]["ubicacion"], "Hangar")

print("\nVisitas: solo las de persona")
c.come_partes([parte("M1", f"{AYER} 08:15:00"), parte("M1", f"{AYER} 00:00:09", real=False),
               parte("M2", f"{ANTEAYER} 10:00:00")])
comprueba("dos visitas, sin el parte automatico", len(c.visitas), 2)

print("\nIncidencias: series A y E, una por numero, con su estado")
c.come_sat([tarea(1, "M1"), tarea(2, "M1", serie="E", operacion="Reponer distribuidor automatico"),
            tarea(3, "00SE0000"),
            tarea(4, "M2", tipo_estado=1, fin="1900-01-01")])
c.come_sat([tarea(4, "M2", tipo_estado=9)])              # la misma, cerrada la noche siguiente
comprueba("tres: fuera la matricula ficticia", len(c.incidencias), 3)
comprueba("la serie E tambien entra (David la mete)", "E-2" in c.incidencias, True)
comprueba("se queda el estado mas nuevo", c.incidencias["A-4"][6], "Finalizado")
c5 = C.Cuadro()
c5.come_sat([tarea(5, "M1", tipo_estado=1, fin="1900-01-01")])
comprueba("fin vacio y estado Pendiente", (c5.incidencias["A-5"][1], c5.incidencias["A-5"][6]),
          ("", "Pendiente"))

print("\nVenta: la telemetria manda sobre la del parte")
c.hay_telemetria(AYER)
c.come_ventas_telemetria([{"matricula": "M1", "fecha_venta": f"{AYER} 10:00:01", "articulo": "AGUA",
                           "precio": 0.6, "centro": "AIRBUS SAN PABLO SUR"}] * 3, AYER)
c.come_ventas_visita([{"matricula": "M1", "fecha_visita": f"{AYER} 08:00:00", "articulo": "AGUA",
                       "num_total": 50, "imp_total": 30.0}], AYER)
c.come_ventas_visita([{"matricula": "M2", "fecha_visita": f"{ANTEAYER} 09:00:00", "articulo": "CAFE",
                       "num_total": 4, "imp_total": 2.0}], ANTEAYER)
comprueba("el dia con telemetria no suma la del parte",
          c.ventas[(AYER.isoformat(), "M1", "AGUA")], [3, 1.7999999999999998])
comprueba("el dia sin telemetria si", c.ventas[(ANTEAYER.isoformat(), "M2", "CAFE")], [4.0, 2.0])
comprueba("la fuente sale mixta", c.fuente_ventas(), "mixta")

print("\nLos ficheros")
F = c.ficheros(PERFIL, PERIODO, generado="x")
I = F["indice.json"]
comprueba("indice y un trozo por mes con venta",
          sorted(F), sorted(["indice.json"] + [f"ventas-{m}.json" for m in
                                               sorted({AYER.isoformat()[:7], ANTEAYER.isoformat()[:7]})]))
comprueba("el censo va primero y marcado", [m[0] for m in I["maquinas"] if m[4]], ["M1", "M2"])
nombre_de = {i: m[0] for i, m in enumerate(I["maquinas"])}
filas = [f for k, t in F.items() if k != "indice.json" for f in t["filas"]]
comprueba("cada fila de venta cita maquina y articulo por posicion",
          sorted((nombre_de[f[1]], I["articulos"][f[2]], f[3]) for f in filas),
          [("M1", "AGUA", 3), ("M2", "CAFE", 4.0)])
comprueba("la venta dice cuantas maquinas del censo tienen venta",
          (I["ventas"]["maquinas_censo"], I["ventas"]["maquinas_censo_con_venta"]), (2, 2))
comprueba("los preventivos dicen que no hay fuente", (I["preventivos"], "preventivos" in I["_preventivos"]),
          (None, True))
comprueba("la nota de la fuente avisa de que es parcial", "PARCIAL" in C.NOTA_FUENTE["visita_ventas"], True)

print("\nFuera de la ventana no sale")
c.come_partes([parte("M1", "2020-01-01 08:00:00")])
comprueba("una visita de 2020 no entra", len(c.ficheros(PERFIL, PERIODO)["indice.json"]["visitas"]), 2)

print("\nUn mes que no cabe en una respuesta se parte por dias")
viejo = C.MAX_BYTES_TROZO
C.MAX_BYTES_TROZO = 60
grande = C.Cuadro()
for d in range(1, 11):
    grande.ventas[(f"2026-09-{d:02d}", "M1", "AGUA")] = [1, 0.6]
G = grande.ficheros(PERFIL, {"desde": "2026-09-01", "hasta": "2026-09-30", "dias": 30})
C.MAX_BYTES_TROZO = viejo
partes = [k for k in G if k.startswith("ventas-")]
comprueba("mas de un trozo", len(partes) > 1, True)
comprueba("el indice los cita todos", sorted("ventas-" + t + ".json" for t in G["indice.json"]["trozos"]),
          sorted(partes))
comprueba("sin perder ni repetir un dia",
          sorted(f[0] for k in partes for f in G[k]["filas"]), list(range(1, 11)))
comprueba("y ningun dia partido entre dos trozos",
          sum(len({f[0] for f in G[k]["filas"]}) for k in partes), 10)

# ----------------------------------------------------------------------
print("\nLa Lambda: el cuadro es de los perfiles de cliente")


def pon(destino, id_informe, dia, filas):
    clave = (f"{destino}/anio={dia.year}/mes={dia.month:02d}/dia={dia.day:02d}/"
             f"{id_informe}.json.gz")
    ALMACEN[clave] = gzip.compress(json.dumps(filas).encode())


ALMACEN["maestros/instalaciones/m_instalaciones.json.gz"] = gzip.compress(json.dumps(
    [censo("M1"), censo("M2", "Hangar"),
     dict(censo("C1"), num_centro=2002, centro="CONSUM MURCIA", cliente="CONSUM")]).encode())
pon("crudo/visita_cabecera", "visita_cabecera", AYER,
    [parte("M1", f"{AYER} 08:15:00"), dict(parte("C1", f"{AYER} 09:00:00"), num_centro=2002,
                                          centro="CONSUM MURCIA")])
pon("crudo/visita_ventas", "visita_ventas", AYER,
    [{"matricula": "M1", "fecha_visita": f"{AYER} 08:15:00", "articulo": "AGUA", "num_total": 2,
      "imp_total": 1.2},
     {"matricula": "C1", "fecha_visita": f"{AYER} 09:00:00", "articulo": "AGUA", "num_total": 9,
      "imp_total": 9.0}])
pon("crudo/sat_averias", "sat_averias", AYER, [tarea(1, "M1")])
# Un trozo de un mes que ya salio de la ventana.
ALMACEN["cabina/cli-x/cuadro/ventas-2020-01.json"] = b"{}"

ALMACEN["config/perfiles.json"] = json.dumps({"perfiles": [
    {"id": "interno", "ambito": {}}, PERFIL]}).encode()
res = L.lambda_handler({}, None)
ix = json.loads(ALMACEN["cabina/cli-x/cuadro/indice.json"])
comprueba("el perfil con cuadro tiene su indice", ix["perfil"], "cli-x")
comprueba("con su venta y nada de la de Consum",
          sum(f[4] for t in ix["trozos"]
              for f in json.loads(ALMACEN[f"cabina/cli-x/cuadro/ventas-{t}.json"])["filas"]), 1.2)
comprueba("y la venta del parte, sin centro, sabe de que centro es",
          ix["centros"][ix["maquinas"][0][1]], "AIRBUS SAN PABLO SUR")
comprueba("visitas e incidencias del perfil", (len(ix["visitas"]), len(ix["incidencias"])), (1, 1))
comprueba("el indice no cita el trozo viejo (la API solo sirve los que cita)",
          "2020-01" in ix["trozos"], False)
comprueba("el interno no tiene cuadro",
          [k for k in ALMACEN if k.startswith("cabina/interno/cuadro/")], [])
comprueba("el resumen dice que fuente uso", res["cuadros"]["cli-x"]["fuente"], "visita_ventas")
comprueba("el panel sigue saliendo igual", json.loads(ALMACEN["cabina/cli-x/panel.json"])["perfil"], "cli-x")

print("\nSe puede apagar a mano con «cuadro»: false")
ALMACEN["config/perfiles.json"] = json.dumps({"perfiles": [
    {"id": "interno", "ambito": {}}, dict(PERFIL, id="cli-y", cuadro=False)]}).encode()
L.lambda_handler({}, None)
comprueba("cli-y no tiene cuadro", [k for k in ALMACEN if k.startswith("cabina/cli-y/cuadro/")], [])

print("\nSin ningun perfil de cliente, las fuentes de venta ni se leen")
ALMACEN["config/perfiles.json"] = json.dumps({"perfiles": [{"id": "interno", "ambito": {}}]}).encode()
LEIDAS.clear()
L.lambda_handler({}, None)
comprueba("no se lee visita_ventas", [k for k in LEIDAS if "visita_ventas" in k], [])
comprueba("ni la telemetria", [k for k in LEIDAS if "telemetria_ventas" in k], [])

print("\nEl perfiles.json de verdad: AIRBUS lo calcula sin ninguna marca, el interno no")
_p = {x["id"]: x for x in json.load(open(AQUI + "/perfiles.json"))["perfiles"]}
comprueba("AIRBUS lo calcula", L.Acumulador(_p["cli-airbus"]).cuadro is not None, True)
comprueba("el interno no", L.Acumulador(_p["interno"]).cuadro is None, True)
comprueba("y no hace falta ninguna marca en el fichero", "cuadro" in _p["cli-airbus"], False)

print("\nUn cliente nuevo se da de alta en la consola, sin tocar perfiles.json")
ALMACEN["config/perfiles.json"] = json.dumps({"perfiles": [{"id": "interno", "ambito": {}}, PERFIL]}).encode()
CONSOLA["fichas"] = [
    ("cli-consum", {"nombre": "CONSUM", "tipo": "cliente", "sesiones": ["cuadro"],
                    "ambito": {"clientes": ["CONSUM"], "centros": [], "delegaciones": []}}),
    ("cli-vacio", {"nombre": "A medias", "tipo": "cliente",
                   "ambito": {"clientes": [], "centros": [], "delegaciones": []}}),
    ("cli-x", {"nombre": "AIRBUS", "tipo": "cliente", "ambito": {"centros": ["2002"]}}),
    ("interno", {"nombre": "Serunion", "tipo": "direccion", "ambito": {"centros": ["500092"]}}),
]
for k in [k for k in ALMACEN if k.startswith("cabina/")]:
    del ALMACEN[k]
res = L.lambda_handler({}, None)
comprueba("el de la consola tiene su panel", json.loads(ALMACEN["cabina/cli-consum/panel.json"])["perfil"],
          "cli-consum")
_ix = json.loads(ALMACEN["cabina/cli-consum/cuadro/indice.json"])
comprueba("y su cuadro, con su venta y solo la suya",
          sum(f[4] for t in _ix["trozos"]
              for f in json.loads(ALMACEN[f"cabina/cli-consum/cuadro/ventas-{t}.json"])["filas"]), 9.0)
comprueba("uno sin ambito NO se calcula (veria todo el parque)",
          [k for k in ALMACEN if k.startswith("cabina/cli-vacio/")], [])
comprueba("y el resumen lo dice", res["consola"]["sin_ambito"], ["cli-vacio"])
comprueba("se han leido las cuatro fichas, por paginas", res["consola"]["leidos"], 4)
_ix = json.loads(ALMACEN["cabina/cli-x/cuadro/indice.json"])
comprueba("en un perfil de los dos sitios, la consola SUMA ambito al fichero",
          sum(f[4] for t in _ix["trozos"]
              for f in json.loads(ALMACEN[f"cabina/cli-x/cuadro/ventas-{t}.json"])["filas"]), 10.2)
comprueba("y el interno sigue siendo todo: la consola no lo recorta",
          json.loads(ALMACEN["cabina/interno/panel.json"])["perfil"], "interno")
_j, _ = L.junta_perfiles([{"id": "interno", "ambito": {}}], [CONSOLA["fichas"][3][1] | {"id": "interno"}])
comprueba("(el interno junto con la consola no gana ambito)", _j[0]["ambito"], {})
_j, _ = L.junta_perfiles([PERFIL], [{"id": "cli-x", "ambito": {"centros": ["500092", "2002"]}}])
comprueba("al sumar no se repite un centro", _j[0]["ambito"]["centros"], ["500092", "2002"])
_j, _ = L.junta_perfiles([PERFIL], [{"id": "cli-x", "ambito": {}}])
comprueba("y una ficha de consola vacia no le quita nada al fichero", _j[0]["ambito"]["centros"], ["500092"])

print("\nSi la Lambda no puede leer la consola, sigue con el fichero")
CONSOLA["fichas"] = None
res = L.lambda_handler({}, None)
comprueba("el resumen dice por que", "AccessDenied" in (res["consola"]["error"] or ""), True)
comprueba("y los perfiles del fichero salen igual", sorted(p["id"] for p in res["perfiles"]),
          ["cli-x", "interno"])

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("El cuadro esta bien.")
