"""
Agregados de la cabina.

Lee el crudo que dejo la extraccion, aplica las reglas de `reglas.py` y escribe
los ficheros que leen los paneles. La pagina no consulta nada: abre un JSON.

POR QUE VA POR TROZOS. La primera version juntaba en listas de Python todas las
filas de la ventana y luego contaba. Con tres dias cabia de sobra; con los 120
que necesita la cabina, no cabe en ninguna Lambda:

    stock_maquina   25.858 filas/dia  x120 = 3,1 M filas =  5,9 GB
    todos juntos    83.470 filas/dia  x120 =  10 M filas =   19 GB

(una fila como diccionario de Python ocupa 1.896 bytes, medido). El maximo de
una Lambda son 10 GB, asi que no era cuestion de subir la memoria: el diseno no
servia en cuanto entrara la historia.

Ahora se lee UN informe de UN dia cada vez y se suman los parciales. Todas las
reglas son cuentas y sumas, asi que aplicarlas por trozos da lo mismo que
aplicarlas de golpe —y siguen siendo las mismas funciones probadas de
`reglas.py`, no una copia. La memoria pasa a depender del numero de maquinas y
centros, que son miles, y no del de filas, que son millones.

Lo unico que crece con las filas son las duraciones que necesitan las medianas,
y son flotantes sueltos: medido, 33 bytes por visita, asi que las 140.000
visitas de 120 dias ocupan unos 5 MB. El resto depende de cuantas maquinas y
centros hay, no de cuantas filas se han leido.

Y el filtrado por ambito no duplica nada: una lista por comprension guarda
REFERENCIAS a las mismas filas, 8 bytes cada una, no copias.

LA HISTORIA NO SE RECALCULA CADA NOCHE. El panel sigue siendo la foto de los
ultimos DIAS dias, y eso no cambia. Lo que se guarda ademas es la SERIE DIARIA
(`serie.py`): una fila por dia y por perfil, hecha de contadores y de
histogramas, para que cualquiera pueda pedir hoy, ayer, este mes, el mes pasado
o un intervalo cualquiera desde el 1 de enero de 2025 y la cuenta sea una suma.

La serie vive en `cabina/<perfil>/serie/<AAAA-MM>.json.gz`, un fichero por mes,
y cada noche se FUSIONAN los dias que esta ejecucion ha leido dejando los demas
como estaban. Por eso la noche no se encarece con la historia: lee los mismos
120 dias de siempre. La historia anterior se rellena una vez, con el evento
{"desde": ..., "hasta": ...}, que solo escribe serie y meses del cuadro —ni
panel ni censo— y para a tiempo diciendo por donde seguir, igual que la
extraccion.

Eventos que entiende:
  {}                                      la noche: panel, cuadro y serie de la ventana
  {"desde": "2025-01-01",
   "hasta": "2025-03-31"}                 relleno historico: solo serie y cuadro
  {"dias": 7}                             (opcional) una ventana mas corta, para probar

Variables de entorno:
  BUCKET       el mismo de la extraccion
  DIAS         (opcional) dias hacia atras que se agregan; por defecto 120
  PERFILES     (opcional) clave del fichero de perfiles; por defecto config/perfiles.json
  TABLA        (opcional) la tabla de la plataforma, donde la consola guarda los
               perfiles; si no esta, <prefijo>-plataforma, sacado del nombre de
               esta funcion (digivend-agregados -> digivend-plataforma)
"""

import datetime
import gzip
import json
import os
from collections import defaultdict

import boto3

import reglas as R
import serie as S
import cuadro as CU
from cuadro import Cuadro

s3 = boto3.client("s3")
BUCKET = os.environ["BUCKET"]
DIAS = int(os.environ.get("DIAS", "120"))
CLAVE_PERFILES = os.environ.get("PERFILES", "config/perfiles.json")
# La funcion se llama <prefijo>-agregados y la tabla <prefijo>-plataforma. Se
# saca del nombre y no de una variable de la plantilla porque tocar la Lambda en
# la plantilla haria que actualizar la pila le pisara el codigo con el marcador.
_PREFIJO = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "digivend-agregados").rsplit("-", 1)[0]
TABLA = os.environ.get("TABLA", f"{_PREFIJO}-plataforma")
# El censo de la instalacion: un maestro, no una ventana de dias.
CLAVE_CENSO = os.environ.get("CENSO", "maestros/instalaciones/m_instalaciones.json.gz")
# Donde se guarda el censo de la ultima ejecucion, para saber que es nuevo.
CLAVE_CENSO_ANTERIOR = "cabina/_censo/anterior.json"

# Que informe alimenta que bloque, y EN QUE ORDEN SE LEE.
#
# Aqui el orden si importa, y por una razon que costo ver: solo tres de los ocho
# informes traen columna `centro`. Los otros cinco traen `matricula`, y nada mas.
# Como el ambito de un perfil de cliente se declara por nombre de centro
# («AIRBUS»), las filas sin centro NO ENCAJABAN EN NINGUN AMBITO y se caian
# enteras: el panel de AIRBUS salia con 0 EUR de recaudacion y 0 unidades
# cargadas. Las cifras que si tenia eran buenas, asi que no parecia roto.
#
# La solucion es el mapa de matricula -> centro que se construye leyendo, y por
# eso los tres informes CON centro van primero: cuando llega el primero sin
# centro, el mapa ya conoce las maquinas. Todo lo que hacen los `come_*` son
# cuentas y sumas, asi que reordenarlos no cambia ningun resultado —lo prueba
# `test_agregados.py`.
#
# Anadir un informe aqui sigue siendo lo unico que hace falta para que entre en
# la cabina; si no trae `centro`, va despues de los que si.
#
# La quinta columna es lo que hace con esas filas el cuadro de mando de los
# perfiles de cliente (cuadro.py). Las dos fuentes de venta solo las usa el
# cuadro: si ningun perfil lo calcula, ni se leen.
FUENTES = [
    # con columna `centro`: ademas de sumar, ensenan el mapa
    ("partes",      "crudo/visita_cabecera",      "visita_cabecera",      "come_partes",      "come_partes"),
    ("mov_maquina", "crudo/stock_maquina",        "stock_maquina",        "come_mov_maquina", None),
    ("sat",         "crudo/sat_averias",          "sat_averias",          "come_sat",         "come_sat"),
    # La telemetria trae centro, y va ANTES que la venta del parte: el dia que
    # hay telemetria, la del parte no se usa (serian las mismas ventas dos veces).
    ("telemetria",  "crudo/telemetria_ventas",    "telemetria_ventas",    None,               "come_ventas_telemetria"),
    # sin columna `centro`: dependen del mapa para saber de quien son
    ("lineas",      "crudo/visita_reposiciones",  "visita_reposiciones",  "come_lineas",      None),
    ("ventas_parte", "crudo/visita_ventas",       "visita_ventas",        None,               "come_ventas_visita"),
    ("recaudacion", "crudo/recaudacion",          "recaudacion",          "come_recaudacion", None),
    ("sat_eventos", "crudo/sat_eventos",          "sat_eventos",          "come_sat_eventos", None),
    ("jornadas",    "crudo/jornadas",             "jornadas",             "come_jornadas",    None),
    ("balance",     "crudo/stock_balance",        "stock_balance",        "come_balance",     None),
]


# ----------------------------------------------------------------------
# lectura del crudo
# ----------------------------------------------------------------------
def _json_de(clave):
    try:
        cuerpo = s3.get_object(Bucket=BUCKET, Key=clave)["Body"].read()
    except Exception:
        # Un dia que falta no es un error: puede no haberse cargado todavia.
        return None
    if clave.endswith(".gz"):
        cuerpo = gzip.decompress(cuerpo)
    return json.loads(cuerpo)


def _filas(dato):
    """Saca la lista de filas sea cual sea la envoltura que use el informe."""
    if dato is None:
        return []
    if isinstance(dato, list):
        return dato
    if isinstance(dato, dict):
        for k in ("Rows", "rows", "Data", "data", "Table", "Result", "d"):
            v = dato.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                for k2 in ("Rows", "rows", "Table", "results"):
                    if isinstance(v.get(k2), list):
                        return v[k2]
    return []


def lee_dia(destino, id_informe, dia):
    """UN informe de UN dia. Lo que se lee se suelta antes de leer el siguiente."""
    clave = (f"{destino}/anio={dia.year}/mes={dia.month:02d}/dia={dia.day:02d}/"
             f"{id_informe}.json.gz")
    return _filas(_json_de(clave))


def escribe(clave, obj):
    s3.put_object(
        Bucket=BUCKET,
        Key=clave,
        Body=json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        ContentType="application/json",
        CacheControl="max-age=300",
        ServerSideEncryption="AES256",
    )
    return clave


def escribe_comprimido(clave, obj):
    """Igual, pero comprimido. Para los ficheros de un mes, que son MB.

    Un mes de venta de AIRBUS son unos tres megas de JSON y se queda en unos
    cuatrocientos kilos. La API lo descomprime al servirlo —igual que ya hacia
    con el panel—, asi que el navegador recibe lo mismo de siempre.
    """
    s3.put_object(
        Bucket=BUCKET,
        Key=clave,
        Body=gzip.compress(
            json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
        ContentType="application/gzip",
        CacheControl="max-age=300",
        ServerSideEncryption="AES256",
    )
    return clave


# ----------------------------------------------------------------------
# filtrado por ambito
# ----------------------------------------------------------------------
class DeQuien:
    """A quien pertenece una fila: centro y cliente, por nombre y por numero.

    Los cuatro, porque los cuatro se usan para cosas distintas: los NOMBRES son
    lo que se lee en un panel, y los NUMEROS son lo que no se mueve. Un centro
    se renombra —«AIRBUS SAN PABLO» se partio en NORTE y SUR el 4 de octubre de
    2026—, y un ambito escrito con nombres se entera; uno escrito con numeros,
    no.
    """

    __slots__ = ("centro", "cliente", "num_centro", "cod_cliente")

    def __init__(self, centro="", cliente="", num_centro="", cod_cliente=""):
        self.centro, self.cliente = centro, cliente
        self.num_centro, self.cod_cliente = num_centro, cod_cliente

    def completo(self):
        return bool(self.centro and self.cliente and self.num_centro and self.cod_cliente)

    def completado_con(self, otro):
        """Lo que la fila no diga, lo pone el mapa. Lo que diga, manda."""
        return DeQuien(self.centro or otro.centro,
                       self.cliente or otro.cliente,
                       self.num_centro or otro.num_centro,
                       self.cod_cliente or otro.cod_cliente)


def _quien(fila):
    return DeQuien(str(R.v(fila, "centro", "")), str(R.v(fila, "cliente", "")),
                   str(R.v(fila, "num_centro", "")), str(R.v(fila, "cod_cliente", "")))


class MapaCentros:
    """De que centro —y de que cliente— es cada maquina. Se aprende leyendo.

    Cinco de los ocho informes no traen columna `centro` —recaudacion, lineas de
    reposicion, eventos de SAT, jornadas y balance—, pero los cinco traen
    `matricula`. Y tres informes si traen las dos cosas. Asi que el mapa sale
    gratis de lo que ya se esta leyendo: ningun informe extra, ninguna consulta.

    No se cachea entre ejecuciones a proposito: una maquina se mueve de centro, y
    un mapa viejo le atribuiria la recaudacion al cliente equivocado. Vale lo que
    diga la ventana que se esta agregando y nada mas.
    """

    def __init__(self):
        self.por_matricula = {}
        self.por_pdv = {}
        self.aprendidas = 0
        self.clientes = set()
        self.centros = {}       # num_centro -> nombre, para poder listarlos

    def aprende(self, filas):
        """Se llama con las filas CRUDAS, antes de filtrar por ambito.

        Antes de filtrar: si se llamara despues, un perfil solo aprenderia las
        maquinas que ya sabe que son suyas, que es justo lo que no sirve.
        """
        for f in filas:
            # La fila centinela de VenCloud —cliente 0 «Ventas Contado», centro
            # -1, punto de venta -99— no es un cliente, igual que 00SE0000 no es
            # una maquina. Si entrara en el mapa saldria en la lista de clientes
            # del parque y podria atribuir filas a un centro que no existe.
            if R.es_centinela(f):
                continue
            quien = _quien(f)
            if not quien.centro and not quien.cliente and not quien.num_centro:
                continue
            if quien.cliente:
                self.clientes.add(quien.cliente)
            if quien.num_centro:
                self.centros.setdefault(quien.num_centro, quien.centro)
            m = R.v(f, "matricula", "")
            if m and m not in self.por_matricula:
                self.por_matricula[m] = quien
                self.aprendidas += 1
            pdv = R.v(f, "cod_pdv", "")
            if pdv and pdv not in self.por_pdv:
                self.por_pdv[pdv] = quien

    def de_quien_es(self, fila):
        """De quien es la fila: lo que traiga ella, y lo que falte, de su maquina."""
        quien = _quien(fila)
        if quien.completo():
            return quien
        for clave, tabla in ((R.v(fila, "matricula", ""), self.por_matricula),
                             (R.v(fila, "cod_pdv", ""), self.por_pdv)):
            if clave and clave in tabla:
                return quien.completado_con(tabla[clave])
        return quien

    def centro_de(self, fila):
        return self.de_quien_es(fila).centro


# ----------------------------------------------------------------------
# los perfiles: el fichero y la consola
# ----------------------------------------------------------------------
def perfiles_de_la_consola():
    """Los perfiles que el administrador ha dado de alta en la consola.

    La consola guarda en DynamoDB, para cada perfil, su ambito (clientes,
    centros, delegaciones). Leerlo aqui es lo que hace que dar de alta un
    cliente en la consola baste para que esa noche se le calcule su panel, sin
    tocar `perfiles.json`.

    Si la tabla no se puede leer (falta el permiso, la pila web no esta) se
    sigue con el fichero solo, como antes, y se dice en el registro: un fallo
    aqui no puede dejar a nadie sin su panel de ayer.
    """
    try:
        ddb = boto3.client("dynamodb")
        out, arranque = [], None
        while True:
            kw = {"TableName": TABLA,
                  "FilterExpression": "begins_with(pk, :p) AND sk = :s",
                  "ExpressionAttributeValues": {":p": {"S": "PERFIL#"}, ":s": {"S": "FICHA"}}}
            if arranque:
                kw["ExclusiveStartKey"] = arranque
            res = ddb.scan(**kw)
            for it in res.get("Items", []):
                d = json.loads(it.get("dato", {}).get("S", "{}"))
                p = {"id": it["pk"]["S"].split("#", 1)[-1],
                     "nombre": d.get("nombre", ""),
                     "tipo": d.get("tipo", "cliente"),
                     "ambito": d.get("ambito") or {}}
                if "cuadro" in d:
                    p["cuadro"] = bool(d["cuadro"])
                out.append(p)
            arranque = res.get("LastEvaluatedKey")
            if not arranque:
                return out, None
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"[:300]


def junta_perfiles(del_fichero, de_la_consola):
    """Una lista de perfiles a calcular, con las dos fuentes.

    - Un perfil que esta en los dos sitios suma los ambitos: lo que diga la
      consola se ANADE a lo del fichero, nunca lo quita. Asi el dia que se
      despliega esto nadie pierde un centro porque la ficha de la consola
      estuviera a medias.
    - Un perfil que solo esta en la consola entra si tiene ambito. SIN ambito
      NO entra: un ambito vacio es «todo el parque», y eso solo se declara en el
      fichero, a proposito y a mano. Un perfil de cliente creado con el ambito
      sin rellenar veria entonces los datos de todos los clientes.
    - Un perfil que solo esta en el fichero se queda como esta.

    Devuelve la lista y los que se han dejado fuera, para el resumen.
    """
    por_id = {}
    for p in del_fichero:
        por_id[p.get("id")] = dict(p, ambito=dict(p.get("ambito") or {}))
    fuera = []
    for c in de_la_consola:
        amb_c = c.get("ambito") or {}
        if c["id"] in por_id:
            p = por_id[c["id"]]
            if not tiene_ambito(p["ambito"]):
                # El interno del fichero es «todo»: sumarle algo lo recortaria.
                continue
            for k in ("clientes", "centros", "delegaciones"):
                ya = [str(x) for x in p["ambito"].get(k, [])]
                ya += [str(x) for x in amb_c.get(k, []) if str(x) not in ya]
                p["ambito"][k] = ya
            if "cuadro" in c and "cuadro" not in p:
                p["cuadro"] = c["cuadro"]
        elif tiene_ambito(amb_c):
            por_id[c["id"]] = c
        else:
            fuera.append(c["id"])
    return list(por_id.values()), fuera


def tiene_ambito(ambito):
    """Un perfil con ambito es un perfil de cliente; sin ambito, el interno."""
    return bool(ambito.get("clientes") or ambito.get("centros") or ambito.get("delegaciones"))


def en_ambito(fila, ambito, mapa=None):
    """El ambito es aditivo: basta con encajar en uno de los tres.

    Un ambito vacio es "todo", y eso solo lo tienen los perfiles internos.

    El `mapa` es lo que hace que una fila de recaudacion, que no sabe de que
    centro es, acabe en el panel del cliente al que pertenece.

    SE ADMITE EL NUMERO Y EL NOMBRE, Y ESA ES LA PIEZA QUE IMPORTA. En VenCloud
    cada centro tiene su numero y cada cliente el suyo, y los numeros no se
    mueven: los nombres si. El 4 de octubre de 2026 «AIRBUS SAN PABLO» se partio
    en NORTE y SUR, y aparecieron CBC e ITC. Un ambito escrito con numeros no se
    habria enterado; uno escrito con nombres depende de que nadie los toque.

    Asi que `centros` admite el numero de centro o su nombre exacto, y
    `clientes` admite el codigo de cliente o un trozo de su nombre —o del nombre
    del centro, que es donde estaba el cliente de verdad antes de la mudanza, y
    donde sigue estando mientras VenCloud no reasigne ese centro—.

    Lo escrito con numeros se prefiere siempre. Lo escrito con nombres se deja
    porque funciona y porque no todos los perfiles van a reescribirse a la vez,
    no porque sea igual de bueno.
    """
    if not tiene_ambito(ambito):
        return True
    q = mapa.de_quien_es(fila) if mapa is not None else _quien(fila)
    deleg = str(R.v(fila, "delegacion", ""))

    for c in ambito.get("clientes", []):
        c = str(c)
        if q.cod_cliente and c == q.cod_cliente:
            return True
        aguja = c.upper()
        if aguja and (aguja in q.centro.upper() or aguja in q.cliente.upper()):
            return True

    for c in ambito.get("centros", []):
        c = str(c)
        if (q.num_centro and c == q.num_centro) or (q.centro and c == q.centro):
            return True

    return deleg in [str(d) for d in ambito.get("delegaciones", [])]


# ----------------------------------------------------------------------
# el acumulador
# ----------------------------------------------------------------------
class Acumulador:
    """Un perfil, y lo que lleva sumado hasta ahora.

    Cada `come_*` recibe las filas de un informe de un dia, ya filtradas por el
    ambito, y suma. Nada guarda las filas.
    """

    def __init__(self, perfil, hoy=None):
        self.perfil = perfil
        self.ambito = perfil.get("ambito", {})
        self.hoy = hoy or datetime.date.today()
        # El cuadro de mando de David se calcula para TODO perfil de cliente
        # (con ambito), y quien lo ve lo decide la sesion «cuadro», que se marca
        # en la consola al editar el perfil: asi activarlo no pide tocar este
        # fichero. El interno (ambito vacio, todo el parque) no lo calcula: no lo
        # necesita y su venta no cabria. `"cuadro": false` lo apaga a mano.
        self.cuadro = Cuadro() if perfil.get("cuadro", tiene_ambito(self.ambito)) else None
        # Cuantas filas le han tocado. Es la cifra que delata un panel vacio
        # antes de que lo vea el cliente: un perfil a cero no es un mes flojo,
        # es un ambito que ha dejado de encajar.
        self.filas_en_ambito = 0

        # servicio
        self.partes_totales = 0
        self.visitas = 0
        self.maquinas = set()
        self.centros = set()
        self.duraciones = []
        self.visitas_por_dia = defaultdict(int)
        # Por centro. Lo primero que pregunta un cliente con nueve centros no es
        # cuantas visitas hubo, sino en cual de los nueve. Se guardan cuentas y
        # un conjunto de matriculas por centro, nunca filas: son miles de
        # centros como mucho, no millones.
        self.por_centro = defaultdict(lambda: {"visitas": 0, "maquinas": set(),
                                               "minutos": 0.0, "tareas_sat": 0})

        # carga
        self.carga_valor = 0.0
        self.carga_unidades = 0.0
        self.carga_vendibles = 0.0

        # merma
        self.merma = {m: {"lineas": 0, "unidades": 0.0, "euros": 0.0}
                      for m in ("caducidad", "rotura", "retirada")}
        # Por articulo, porque el total en euros no se entiende sin esto: un
        # envase de cafe cuesta 23 EUR y un snack 0,63. Treinta y cinco veces.
        # Sin el desglose, un mes con cafe retirado parece un desastre y un mes
        # sin el, un exito, cuando pueden ser las mismas lineas.
        self.merma_articulo = defaultdict(lambda: {"lineas": 0, "unidades": 0.0, "euros": 0.0})

        # dinero, por periodo contable
        self.periodos = defaultdict(lambda: {"registros": 0, "efectivo": 0.0,
                                             "banco": 0.0, "ciego": 0.0,
                                             "imposibles": 0})

        # SAT
        self.sat_leidas = 0
        self.sat_tareas = 0
        self.sat_averias = 0
        self.sat_preventivos = 0
        self.sat_fallos_tecnicos = 0
        self.sat_por_maquina = defaultdict(int)
        self.sat_centro = {}
        # Una averia abierta un dia y cerrada otro tiene sus eventos en ficheros
        # distintos: hay que recordarla entre dias.
        self.sat_apertura = {}
        self.sat_cierre = {}

        # jornadas
        self.jornadas = 0
        self.temperaturas = []
        self.km = []
        self.con_gps = 0

        # balance: solo cabe una foto, pero no se sabe cual es la ultima hasta
        # el final, asi que se guardan por periodo. Son 3.500 filas al mes.
        self.balance = defaultdict(list)

        # instalaciones: el censo de lo que esta puesto y lo que esta puesto a
        # medias. No es una ventana de dias: es la foto de hoy.
        self.censo = {"clientes": set(), "centros": set(), "pdvs": set(), "maquinas": set()}
        self.incidencias = defaultdict(list)
        # Por centro, para la pega que no se ve en una sola fila: un centro con
        # puntos de venta y ni una maquina. Hay que recorrerlo entero para
        # saberlo, asi que se cuenta aqui y se decide al final.
        self.centros_inst = defaultdict(
            lambda: {"pdvs": 0, "maquinas": 0, "cliente": "", "centro": "", "delegacion": ""})
        # Altas con su fecha de verdad, leida de VenCloud. La maquina no tiene
        # fecha de instalacion, asi que esa se ve apareciendo (ver `nuevos`).
        self.altas = {"clientes": {}, "centros": {}, "pdvs": {}}

    # ---------------------------------------------------------------- servicio
    def come_partes(self, filas):
        self.partes_totales += len(filas)
        reales = R.visitas_reales(filas)
        self.visitas += len(reales)
        for p in reales:
            self.maquinas.add(R.v(p, "matricula"))
            self.centros.add(R.v(p, "centro"))
            m = R.v(p, "minutos", None)
            if m is not None:
                self.duraciones.append(float(m))
            self.visitas_por_dia[str(R.v(p, "fecha_ini", ""))[:10]] += 1
            c = self.por_centro[str(R.v(p, "centro", "(sin centro)"))]
            c["visitas"] += 1
            c["maquinas"].add(R.v(p, "matricula"))
            if m is not None:
                c["minutos"] += float(m)

    def come_lineas(self, filas):
        self.carga_valor += R.valor_cargado(filas)
        self.carga_unidades += R.unidades_cargadas(filas)
        self.carga_vendibles += R.unidades_cargadas(
            [l for l in filas if not R.es_consumible_de_cafe(l)])

    def come_mov_maquina(self, filas):
        parcial = R.merma(filas)
        for motivo, datos in parcial.items():
            acum = self.merma[motivo]
            acum["lineas"] += datos["lineas"]
            acum["unidades"] += datos["unidades"]
            acum["euros"] += datos["euros"]
        for l in filas:
            if R.v(l, "motivo") != "RC":          # solo caducidad
                continue
            a = self.merma_articulo[str(R.v(l, "articulo", "(sin nombre)"))[:70]]
            unidades = abs(float(R.v(l, "cantidad")))
            a["lineas"] += 1
            a["unidades"] += unidades
            a["euros"] += unidades * float(R.v(l, "puc"))

    # ---------------------------------------------------------------- dinero
    def come_recaudacion(self, filas):
        periodos = {(int(R.v(x, "anho")), int(R.v(x, "mes"))) for x in filas}
        for anio, mes in periodos:
            r = R.recaudacion_del_periodo(filas, anio, mes)
            acum = self.periodos[(anio, mes)]
            acum["registros"] += r["registros"]
            acum["efectivo"] += r["efectivo"]
            acum["banco"] += r["banco"]
            acum["ciego"] += r["efectivo_sin_telemetria"]
            acum["imposibles"] += r.get("filas_imposibles", 0)

    # ---------------------------------------------------------------- SAT
    def come_sat(self, filas):
        self.sat_leidas += len(filas)
        reales = R.tareas_de_maquina(filas)
        self.sat_tareas += len(reales)
        for t in reales:
            matricula = R.v(t, "matricula")
            centro = str(R.v(t, "centro", "(sin centro)"))
            self.sat_por_maquina[matricula] += 1
            # De que centro es la maquina reincidente. Una matricula sola no le
            # dice nada a nadie; con el centro delante se sabe a quien llamar.
            self.sat_centro.setdefault(matricula, centro)
            self.por_centro[centro]["tareas_sat"] += 1
            if R.es_preventivo(t):
                self.sat_preventivos += 1
            elif R.es_averia_tecnica(t):
                self.sat_averias += 1
            if R.es_fallo_tecnico(t) and not R.es_preventivo(t):
                self.sat_fallos_tecnicos += 1

    def come_sat_eventos(self, filas):
        for e in filas:
            ident = R.v(e, "averia_id")
            cuando = str(R.v(e, "fecha", ""))[:19]
            if not cuando:
                continue
            if ident not in self.sat_apertura or cuando < self.sat_apertura[ident]:
                self.sat_apertura[ident] = cuando
            if int(R.v(e, "estado", -1)) == 99:
                if ident not in self.sat_cierre or cuando < self.sat_cierre[ident]:
                    self.sat_cierre[ident] = cuando

    # ---------------------------------------------------------------- jornadas
    def come_jornadas(self, filas):
        self.jornadas += len(filas)
        for j in filas:
            t = R.v(j, "temperaturaini", None)
            if t is not None:
                self.temperaturas.append(float(t))
            a, b = float(R.v(j, "kminiciales")), float(R.v(j, "kmfinales"))
            if b > a > 0:
                self.km.append(b - a)
            if R.v(j, "maplatitudini", 0):
                self.con_gps += 1

    def come_instalaciones(self, filas):
        """El censo de hoy, con sus pegas. Una fila por cliente/centro/pdv/maquina.

        No se guarda la fila: se guardan los identificadores —para saber que hay
        y que es nuevo— y, de lo que tiene alguna pega, lo justo para ponerlo en
        una tabla y poder ir a arreglarlo.
        """
        for f in filas:
            cliente = str(R.v(f, "cod_cliente", ""))
            centro = str(R.v(f, "num_centro", ""))
            pdv = str(R.v(f, "cod_pdv", ""))
            maquina = str(R.v(f, "matricula", ""))
            if cliente:
                self.censo["clientes"].add(cliente)
            if centro:
                self.censo["centros"].add(centro)
            if pdv:
                self.censo["pdvs"].add(pdv)
            if maquina:
                self.censo["maquinas"].add(maquina)
            if (centro and pdv and not R.es_centinela(f)
                    and R.cliente_vivo(f) and R.centro_vivo(f) and R.pdv_vivo(f)):
                d = self.centros_inst[centro]
                d["pdvs"] += 1
                d["maquinas"] += 1 if maquina else 0
                d["cliente"] = str(R.v(f, "cliente", ""))[:60]
                d["centro"] = str(R.v(f, "centro", ""))[:60]
                d["delegacion"] = str(R.v(f, "delegacion", ""))[:40]
            for que, cuando in R.altas_de(f, self.hoy).items():
                nombre = {"clientes": str(R.v(f, "cliente", "")) or cliente,
                          "centros": str(R.v(f, "centro", "")) or centro,
                          "pdvs": str(R.v(f, "ubicacion", "")) or pdv}[que]
                clave = {"clientes": cliente, "centros": centro, "pdvs": pdv}[que]
                if clave:
                    self.altas[que][clave] = {"cuando": cuando, "nombre": nombre[:60]}
            for cual in R.incidencias_de(f, self.hoy):
                self.incidencias[cual].append({
                    "cliente": str(R.v(f, "cliente", ""))[:60],
                    "centro": str(R.v(f, "centro", ""))[:60],
                    "num_centro": centro,
                    "pdv": pdv,
                    "ubicacion": str(R.v(f, "ubicacion", ""))[:60],
                    "m": maquina,
                    "delegacion": str(R.v(f, "delegacion", ""))[:40],
                    "alta": str(R.v(f, "alta_pdv", ""))[:10],
                })

    def come_balance(self, filas):
        for b in filas:
            periodo = (int(R.v(b, "anho", 0) or 0), int(R.v(b, "mes", 0) or 0))
            self.balance[periodo].append(b)

    # ---------------------------------------------------------------- salida
    def horas_de_cierre(self):
        horas = []
        for ident, cierre in self.sat_cierre.items():
            apertura = self.sat_apertura.get(ident)
            if not apertura:
                continue
            try:
                a = datetime.datetime.fromisoformat(apertura)
                b = datetime.datetime.fromisoformat(cierre)
            except ValueError:
                continue
            horas.append((b - a).total_seconds() / 3600)
        return horas

    def panel(self, hoy, periodo, nuevos=None):
        balance, periodo_balance = self._ultimo_balance()
        maquinas_balance = [b for b in balance if R.v(b, "tipo_elemento") == "M"]
        return {
            "generado": datetime.datetime.utcnow().isoformat() + "Z",
            "perfil": self.perfil.get("id"),
            "periodo": periodo,
            "servicio": {
                "visitas": self.visitas,
                "partes_totales": self.partes_totales,
                "_nota_partes": "La diferencia son partes automaticos: leen maquina, no son visitas.",
                "maquinas": len(self.maquinas),
                "centros": len(self.centros),
                "coste_servicio": {
                    "visitas": self.visitas,
                    "coste": round(self.visitas * 8.0, 2),
                    "coste_unitario": 8.0,
                },
                "duracion_min": R.resumen_tiempos(self.duraciones),
                "visitas_por_dia": [{"f": f, "v": n}
                                    for f, n in sorted(self.visitas_por_dia.items()) if f],
                "por_centro": sorted(
                    ({"centro": c, "visitas": d["visitas"], "maquinas": len(d["maquinas"]),
                      "min_medio": round(d["minutos"] / d["visitas"], 1) if d["visitas"] else 0,
                      "tareas_sat": d["tareas_sat"]}
                     for c, d in self.por_centro.items()),
                    key=lambda x: -x["visitas"])[:60],
                "_nota_centros": ("Visitas, maquinas y tareas de SAT por centro. El minuto "
                                  "medio aqui es media, no mediana: por centro hay pocas "
                                  "visitas y la mediana de treinta valores no dice mas."),
                "carga": {
                    "valor": round(self.carga_valor, 2),
                    "unidades_total": self.carga_unidades,
                    "unidades_vendibles": self.carga_vendibles,
                    "_nota": "Dos de cada tres unidades son consumibles de cafe: azucar, vasos y paletinas.",
                },
                "merma": dict(
                    {m: {"lineas": d["lineas"],
                         "unidades": d["unidades"],
                         "euros": round(d["euros"], 2)}
                     for m, d in self.merma.items()},
                    caducidad_por_articulo=sorted(
                        ({"articulo": a, "lineas": d["lineas"], "unidades": d["unidades"],
                          "euros": round(d["euros"], 2),
                          "eur_unidad": round(d["euros"] / d["unidades"], 3) if d["unidades"] else 0}
                         for a, d in self.merma_articulo.items()),
                        key=lambda x: -x["euros"])[:25],
                    _nota_articulos=("El total en euros no se lee sin esto: un envase de cafe "
                                     "cuesta 23 EUR y un snack 0,63. Un mes con cafe retirado "
                                     "parece un desastre con las mismas lineas que uno sin el."),
                ),
            },
            "dinero": {"periodos": self._bloque_dinero(hoy)},
            "sat": {
                "tareas": self.sat_tareas,
                "tareas_con_ficticia": self.sat_leidas,
                "_nota_ficticia": f"{R.MATRICULA_FICTICIA} no es una maquina: se excluye.",
                "averias_tecnicas": self.sat_averias,
                "fallos_tecnicos": self.sat_fallos_tecnicos,
                "_nota_fallos": ("«averias_tecnicas» cuenta por categoria y se deja fuera "
                                 "los fallos archivados en atencion al cliente. "
                                 "«fallos_tecnicos» cuenta por operacion, que es lo correcto."),
                "preventivos": self.sat_preventivos,
                "horas_cierre": R.resumen_tiempos(self.horas_de_cierre()),
                "reincidentes": sorted(
                    [{"m": m, "c": self.sat_centro.get(m, ""), "n": n}
                     for m, n in self.sat_por_maquina.items() if n >= 5],
                    key=lambda x: -x["n"])[:25],
            },
            "jornadas": {
                "jornadas": self.jornadas,
                "temperatura": R.resumen_tiempos(self.temperaturas),
                "temperatura_fuera": sum(1 for t in self.temperaturas if t > 8),
                "_nota_temp": "Frigorifico del vehiculo al arrancar. Por encima de 8 °C es cadena de frio.",
                "km": R.resumen_tiempos(self.km),
                "km_total": round(sum(self.km)),
                "gps": {"con": self.con_gps,
                        "pct": round(100 * self.con_gps / self.jornadas, 1) if self.jornadas else 0},
            },
            "instalaciones": self.bloque_instalaciones(nuevos),
            "inventario": {
                "periodo_balance": periodo_balance,
                "_nota_balance": ("El balance es un cierre mensual. Esto es la ultima foto, "
                                  "no un acumulado: sumar varios cierres multiplicaria las "
                                  "existencias."),
                "cumplimiento": R.cumplimiento_inventario(
                    [{"ultimo_inventario": R.v(b, "fecha_ult_inventario", "")}
                     for b in maquinas_balance], hoy),
                "existencias": {
                    t: round(sum(float(R.v(b, "valor_total")) for b in balance
                                 if R.v(b, "tipo_elemento") == t), 2)
                    for t in ("A", "M", "V")
                },
            },
        }

    def bloque_instalaciones(self, nuevos=None):
        """Lo que esta puesto, lo que acaba de ponerse y lo que esta a medias.

        `nuevos` lo pone el handler: sale de comparar el censo de hoy con el que
        se guardo la ultima vez, y por eso no puede salir de aqui.
        """
        nuevos = nuevos or {}
        # La pega que no cabe en una fila: el centro entero vacio.
        vacios = sorted(((num, d) for num, d in self.centros_inst.items()
                         if d["pdvs"] and not d["maquinas"]),
                        key=lambda x: -x[1]["pdvs"])
        incidencias = dict(self.incidencias)
        if vacios:
            incidencias["centro_sin_maquinas"] = [
                {"cliente": d["cliente"], "centro": d["centro"], "num_centro": num,
                 "pdv": f"{d['pdvs']} puntos de venta", "ubicacion": "", "m": "",
                 "delegacion": d["delegacion"], "alta": "", "peso": d["pdvs"]}
                for num, d in vacios]
        return {
            "censo": {k: len(v_) for k, v_ in self.censo.items()},
            "altas_recientes": {
                que: sorted(({"id": k, **d} for k, d in dic.items()),
                            key=lambda x: x["cuando"], reverse=True)[:100]
                for que, dic in self.altas.items()
            },
            "_nota_altas": (f"Dadas de alta en VenCloud en los ultimos {R.DIAS_ALTA_RECIENTE} dias, "
                            "con su fecha de verdad. La maquina no tiene fecha de instalacion, "
                            "asi que esa solo sale en «nuevos»."),
            "nuevos": nuevos,
            "_nota_nuevos": ("«Nuevo» es lo que no estaba en el censo de la ejecucion anterior. "
                             "La primera vez no hay con que comparar, asi que sale vacio: no "
                             "quiere decir que no haya altas."),
            "catalogo": {k: {"titulo": t, "porque": p}
                         for k, (t, p) in R.CATALOGO_INCIDENCIAS.items()},
            "incidencias": {
                # Lo gordo primero donde el tamano es la gravedad —un centro con 22
                # puntos de venta vacios no es lo mismo que uno con uno—, y por
                # cliente y centro donde todas las lineas pesan igual.
                cual: {"n": len(filas), "casos": sorted(
                    filas, key=lambda x: (-x.get("peso", 0), x["cliente"],
                                          x["centro"], x["pdv"]))[:100]}
                for cual, filas in sorted(incidencias.items())
            },
            "_nota_tarifa": ("«Sin tarifa» mira la del punto de venta y la del cliente. Faltan las "
                             "tarifas de PRODUCTOS del cliente y del centro, que el informe 10 de "
                             "VenCloud si tiene: lo que marca, lo esta de verdad, pero puede haber "
                             "mas."),
        }

    def _ultimo_balance(self):
        """Solo la foto MAS RECIENTE, nunca la suma de varias.

        En una ventana de 120 dias caben tres o cuatro cierres mensuales.
        Sumarlos multiplicaria las existencias y contaria cada maquina una vez
        por cierre en el cumplimiento de inventario.
        """
        periodos = [p for p in self.balance if p != (0, 0)] or list(self.balance)
        if not periodos:
            return [], None
        ultimo = max(periodos)
        return self.balance[ultimo], f"{ultimo[0]}-{ultimo[1]:02d}"

    def _bloque_dinero(self, hoy):
        out = []
        for (anio, mes) in sorted(self.periodos)[-13:]:
            a = self.periodos[(anio, mes)]
            ef = round(a["efectivo"], 2)
            bk = round(a["banco"], 2)
            ciego = round(a["ciego"], 2)
            fila = {
                "periodo": f"{anio}-{mes:02d}",
                "registros": a["registros"],
                "efectivo": ef,
                "banco": bk,
                "total": round(ef + bk, 2),
                "efectivo_sin_telemetria": ciego,
                "pct_ciego": round(100 * ciego / ef, 1) if ef > 0 else 0.0,
                "provisional": R.mes_provisional(anio, mes, hoy),
            }
            if a["imposibles"]:
                fila["filas_imposibles"] = a["imposibles"]
                fila["_nota_imposibles"] = (
                    f"{a['imposibles']} fila(s) con importes imposibles apartadas: son "
                    "contadores rotos, no recaudacion. El mes es bueno sin ellas, pero "
                    "conviene mirarlas en el crudo.")
            if fila["provisional"]:
                fila["_nota"] = ("Mes sin cerrar: le falta el cobro por tarjeta, que se escribe "
                                 "al mes siguiente y es el 55 % de la facturacion. No comparar "
                                 "con un mes cerrado.")
            out.append(fila)
        return out


# ----------------------------------------------------------------------
# estado de la carga, para el panel de administracion
# ----------------------------------------------------------------------
def estado_de_la_carga(hoy):
    """Resume la ultima extraccion en cabina/, donde la web si puede leer.

    La API solo tiene permiso sobre cabina/, a proposito: no se le abre el
    registro entero para ensenar cuatro cifras. Se le deja aqui lo justo.
    """
    for atras in range(0, 4):
        d = hoy - datetime.timedelta(days=atras)
        clave = (f"registro/extraccion/anio={d.year}/mes={d.month:02d}/"
                 f"{d.isoformat()}.json")
        reg = _json_de(clave)
        if not reg:
            continue
        return {
            "ultima_carga": reg.get("ejecucion"),
            "dias_pedidos": reg.get("dias", []),
            "descargas_ok": reg.get("resumen", {}).get("descargas_ok"),
            "descargas_fallidas": reg.get("resumen", {}).get("descargas_fallidas"),
            "bytes": reg.get("resumen", {}).get("bytes"),
            "filas_por_informe": {x["id"]: x.get("filas") for x in reg.get("ok", [])},
            "errores": reg.get("errores", [])[:20],
            "retraso_dias": atras,
            "_nota": ("Si retraso_dias es mayor que 0, la carga de esta noche no "
                      "ha corrido y lo que se ve es de una noche anterior."),
        }
    return {"_nota": "No hay ningun registro de extraccion de los ultimos cuatro dias.",
            "retraso_dias": None}


# ----------------------------------------------------------------------
# ejecucion
# ----------------------------------------------------------------------
def lo_que_coge(ambito, mapa):
    """Que centros y que clientes de VERDAD coge este ambito.

    Se saca del mapa —miles de maquinas— y no de las filas —millones—. Sirve
    para dos cosas que, sin esto, solo se descubren cuando llama el cliente:

      · Un perfil que se ha quedado a cero: si no coge NINGUN centro, el nombre
        que declara ya no existe en VenCloud y hay que cambiarlo.
      · Un perfil que funciona pero es fragil: si coge centros y el cliente de
        esos centros no se parece a lo que declara, el ambito esta viviendo del
        nombre del centro, y un renombrado se lo lleva por delante. Con los
        numeros de centro en `perfiles.json`, deja de depender de eso.
    """
    # Un mismo centro llega con numero desde unos informes y sin el desde otros
    # —el diario de maquina, por ejemplo, trae el nombre y nada mas—. Sin esto
    # saldria dos veces, una con numero y otra sin el.
    num_por_nombre = {nombre: num for num, nombre in mapa.centros.items() if nombre}
    centros, clientes = {}, set()
    for q in mapa.por_matricula.values():
        if not en_ambito({"centro": q.centro, "cliente": q.cliente,
                          "num_centro": q.num_centro, "cod_cliente": q.cod_cliente},
                         ambito, None):
            continue
        clave = q.num_centro or num_por_nombre.get(q.centro, q.centro)
        if clave:
            # El nombre que se queda es el que venga con numero, si alguno lo trae.
            centros[clave] = q.centro or centros.get(clave, "")
        if q.cliente:
            clientes.add(q.cliente)
    return centros, clientes


def altas_desde_el_censo_anterior(acumuladores):
    """Que hay hoy que no estuviera la ultima vez, y deja escrito el de hoy.

    VenCloud no dice cuando se dio de alta un cliente ni un centro, y el maestro
    se sobrescribe cada noche: no hay historia que mirar. Asi que la historia se
    la guarda esta Lambda, que es la unica que necesita saberlo.

    La PRIMERA vez no hay con que comparar y no sale ninguna alta. Es lo
    correcto: lo contrario seria dar de alta hoy las 3.168 maquinas del parque y
    que nadie volviera a mirar este panel.
    """
    anterior = _json_de(CLAVE_CENSO_ANTERIOR) or {}
    nuevos, ahora = {}, {}
    for acu in acumuladores:
        pid = acu.perfil["id"]
        ahora[pid] = {k: sorted(v_) for k, v_ in acu.censo.items()}
        antes = anterior.get(pid)
        if antes is None:          # primera vez: no se inventa ninguna alta
            nuevos[pid] = {}
            continue
        nuevos[pid] = {k: sorted(set(ahora[pid][k]) - set(antes.get(k, [])))[:200]
                       for k in acu.censo}
    # Solo se guarda si hay censo: una noche sin maestro no debe borrar la
    # memoria y hacer que manana parezca que todo es nuevo.
    if any(any(v_.values()) for v_ in ahora.values()):
        escribe(CLAVE_CENSO_ANTERIOR, {"generado": datetime.date.today().isoformat(), **ahora})
    return nuevos


def escribe_cuadro(acu, periodo, dias_leidos):
    """Escribe el cuadro de un perfil: los meses leidos, fusionados, y el indice.

    Solo se tocan los meses que el periodo leido alcanza. Los anteriores ya
    estan en S3 de otra ejecucion y el indice los sigue citando con el resumen
    que ya tenian: asi la historia se acumula sin releerla cada noche.
    """
    base = f"cabina/{acu.perfil['id']}/cuadro/"
    anterior = _json_de(base + "indice.json") or {}
    lineas = {m["mes"]: m for m in anterior.get("meses", []) if m.get("mes")}
    sin_sitio = []
    for mes, nuevo in acu.cuadro.meses(periodo).items():
        viejo = _json_de(f"{base}mes-{mes}.json.gz")
        fichero = CU.fusiona_mes(viejo, nuevo, dias=dias_leidos)
        if not CU.cabe_en_una_respuesta(fichero):
            # Se escribe igual —el dato no se tira— y se dice: un mes que no
            # cabe en una respuesta se ve en el indice, no con un 500.
            sin_sitio.append(mes)
        escribe_comprimido(f"{base}mes-{mes}.json.gz", fichero)
        lineas[mes] = CU.resumen_mes(fichero)
    indice = acu.cuadro.indice(acu.perfil, periodo, list(lineas.values()))
    indice["rangos"] = {k: S.NOMBRES_RANGO[k] for k in S.RANGOS}
    indice["primer_dia"] = S.PRIMER_DIA
    if sin_sitio:
        indice["_aviso_tamano"] = (
            "Estos meses pasan del limite de una respuesta y la pagina puede no poder "
            "bajarlos: " + ", ".join(sin_sitio))
    escribe(base + "indice.json", indice)
    v = indice["ventas"]
    return {"fuente": v["fuente"], "meses": len(lineas),
            "meses_escritos": sorted(acu.cuadro.meses(periodo)),
            "maquinas_censo": v["maquinas_censo"],
            "maquinas_censo_con_venta": v["maquinas_censo_con_venta"],
            "sin_sitio": sin_sitio}


def escribe_serie(perfil_id, filas, dias_leidos):
    """Fusiona las filas de esta ejecucion en los meses de la serie, y el indice.

    Un dia recalculado sustituye al que hubiera; los dias que esta ejecucion no
    ha leido se quedan. El indice lleva la lista de meses con sus totales, los
    tramos de los histogramas y los rangos con nombre, para que la pagina no
    lleve ninguna copia de eso.
    """
    base = f"cabina/{perfil_id}/serie/"
    anterior = _json_de(base + "indice.json") or {}
    lineas = {m["mes"]: m for m in anterior.get("meses", []) if m.get("mes")}

    por_mes = defaultdict(list)
    for f in filas:
        por_mes[f["f"][:7]].append(f)
    for mes, nuevas in sorted(por_mes.items()):
        viejo = _json_de(f"{base}{mes}.json.gz") or {}
        fusion = S.fusiona_mes(viejo.get("filas"), nuevas)
        escribe_comprimido(f"{base}{mes}.json.gz", {"mes": mes, "filas": fusion})
        lineas[mes] = S.resumen_mes(mes, fusion)

    indice = {
        "generado": datetime.datetime.utcnow().isoformat() + "Z",
        "perfil": perfil_id,
        "primer_dia": S.PRIMER_DIA,
        "meses": sorted(lineas.values(), key=lambda x: x["mes"]),
        "bordes": S.BORDES,
        "rangos": {k: S.NOMBRES_RANGO[k] for k in S.RANGOS},
        "_nota": ("Un fichero por mes en serie/<AAAA-MM>.json. Cada fila es un dia y se "
                  "suma; las medianas de un rango salen de los histogramas, con los "
                  "tramos de «bordes»."),
    }
    escribe(base + "indice.json", indice)
    return {"meses": len(lineas), "meses_escritos": sorted(por_mes), "dias": len(filas)}


# Que hace la serie diaria con las filas de cada fuente. El balance no esta a
# proposito: es un cierre mensual, una foto, y una foto no se suma —el panel ya
# se queda solo con la ultima—.
SERIE_COME = {
    "partes": "come_partes",
    "lineas": "come_lineas",
    "mov_maquina": "come_mov_maquina",
    "recaudacion": "come_recaudacion",
    "sat": "come_sat",
    "sat_eventos": "come_sat_eventos",
    "jornadas": "come_jornadas",
    "telemetria": "come_ventas_telemetria",
    "ventas_parte": "come_ventas_visita",
}


def come_serie(dia, nombre, filas):
    metodo = SERIE_COME.get(nombre)
    if metodo:
        getattr(dia, metodo)(filas)


def dias_a_agregar(hoy, event):
    """Los dias de esta ejecucion, y si es un relleno historico.

    De noche, la ventana de siempre hacia atras desde ayer. Con
    {"desde": "2025-01-01", "hasta": "2025-03-31"}, ese rango del mas antiguo
    al mas nuevo: si se acaba el tiempo, lo escrito queda seguido y basta con
    continuar por donde se quedo.
    """
    e = event or {}
    if e.get("desde"):
        d0 = datetime.date.fromisoformat(str(e["desde"])[:10])
        d1 = datetime.date.fromisoformat(str(e.get("hasta") or e["desde"])[:10])
        if d1 < d0:
            raise ValueError("'hasta' es anterior a 'desde'")
        if d0 < datetime.date.fromisoformat(S.PRIMER_DIA):
            raise ValueError(f"La historia empieza el {S.PRIMER_DIA} (serie.PRIMER_DIA)")
        return [d0 + datetime.timedelta(days=i) for i in range((d1 - d0).days + 1)], True
    n = int(e.get("dias") or DIAS)
    return [hoy - datetime.timedelta(days=d) for d in range(1, n + 1)], False


def _queda_tiempo(context, margen=60_000):
    """Si da tiempo a leer otro dia y escribir lo que lleve.

    El margen es generoso a proposito: lo que no puede pasar es morir DESPUES de
    leer y ANTES de escribir, porque entonces el relleno no avanza y no se sabe.
    """
    if context is None or not hasattr(context, "get_remaining_time_in_millis"):
        return True
    return context.get_remaining_time_in_millis() > margen


def lambda_handler(event, context):
    event = event or {}
    hoy = datetime.date.today()
    dias, historico = dias_a_agregar(hoy, event)

    del_fichero = (_json_de(CLAVE_PERFILES) or {"perfiles": [{"id": "interno", "ambito": {}}]})["perfiles"]
    de_la_consola, fallo_consola = perfiles_de_la_consola()
    if fallo_consola:
        print(f"AVISO: no se han podido leer los perfiles de la consola ({fallo_consola}). "
              f"Se calculan solo los de {CLAVE_PERFILES}.")
    perfiles, sin_ambito = junta_perfiles(del_fichero, de_la_consola)
    for pid in sin_ambito:
        print(f"AVISO: el perfil {pid} de la consola no tiene ambito y no se calcula. "
              f"Ponle sus clientes o centros en la consola.")
    acumuladores = [Acumulador(p, hoy) for p in perfiles]

    leidas = defaultdict(int)
    mapa = MapaCentros()

    # El censo va PRIMERO, y no solo porque sea un maestro: trae cliente, centro,
    # pdv y matricula de TODO el parque, asi que el mapa arranca completo en vez
    # de ir aprendiendo maquina a maquina segun aparecen en la ventana. Una
    # maquina que no ha tenido ni una visita en 120 dias tambien queda situada.
    censo = _filas(_json_de(CLAVE_CENSO))
    if censo:
        leidas["instalaciones"] = len(censo)
        mapa.aprende(censo)
        for acu in acumuladores:
            propias = [f for f in censo if en_ambito(f, acu.ambito, mapa)]
            # El bloque de instalaciones del panel es la foto de HOY: en un
            # relleno historico no se calcula, porque no se escribe panel.
            if not historico:
                acu.come_instalaciones(propias)
            if acu.cuadro:
                acu.cuadro.come_instalaciones(propias)
    del censo

    # EL RECORRIDO VA POR DIAS, Y DENTRO DE CADA DIA POR INFORMES. Antes era al
    # contrario. Se cambio para poder cerrar la fila de la serie de un dia en
    # cuanto se acaba ese dia, en vez de tener los 120 dias de todos los
    # informes a medias a la vez.
    #
    # El orden de FUENTES sigue mandando DENTRO de un dia, que es donde
    # importaba: los tres informes con columna `centro` van antes que los que
    # solo traen matricula, asi que el mapa ya conoce las maquinas cuando llegan
    # las filas sin centro. Y la telemetria de un dia se lee antes que la venta
    # del parte de ese dia, que es lo que evita contar la venta dos veces.
    con_cuadro = any(acu.cuadro for acu in acumuladores)
    fuentes = [f for f in FUENTES if f[3] is not None or con_cuadro]
    series = defaultdict(list)
    leidos, parado_en = [], None
    for dia in dias:
        if not _queda_tiempo(context):
            parado_en = dia.isoformat()
            print(f"PARO por tiempo antes de {parado_en}.")
            break
        del_dia = {acu.perfil["id"]: S.Dia(dia) for acu in acumuladores}
        for nombre, destino, id_informe, metodo, metodo_cuadro in fuentes:
            filas = lee_dia(destino, id_informe, dia)
            if not filas:
                continue
            leidas[nombre] += len(filas)
            # Primero aprender, luego repartir: el mapa se alimenta de las filas
            # de todos, porque una maquina de AIRBUS se conoce igual leyendo el
            # informe completo.
            mapa.aprende(filas)
            if nombre == "telemetria":
                # Con el fichero ENTERO, antes de filtrar, y por lo mismo que en
                # el cuadro: si solo se marcara cuando al perfil le tocan filas,
                # un dia con telemetria pero sin venta suya se rellenaria con la
                # venta del parte, que es parcial y se fecha otro dia.
                for d in del_dia.values():
                    d.hay_telemetria()
            for acu in acumuladores:
                if nombre == "telemetria" and acu.cuadro:
                    acu.cuadro.hay_telemetria(dia)
                propias = [f for f in filas if en_ambito(f, acu.ambito, mapa)]
                acu.filas_en_ambito += len(propias)
                if propias and metodo and not historico:
                    getattr(acu, metodo)(propias)
                if propias:
                    come_serie(del_dia[acu.perfil["id"]], nombre, propias)
                if acu.cuadro and metodo_cuadro:
                    getattr(acu.cuadro, metodo_cuadro)(
                        *((propias, dia) if metodo_cuadro.startswith("come_ventas") else (propias,)))
            # El trozo se suelta aqui: en ningun momento hay mas de un informe
            # de un dia en memoria.
            del filas
        leidos.append(dia)
        for pid, d in del_dia.items():
            # Un dia sin una sola fila no se escribe: ocuparia sitio y no dice
            # nada que no diga su ausencia.
            if not d.vacio():
                series[pid].append(d.fila())

    dias_leidos = [d.isoformat() for d in leidos]
    if not leidos:
        leidos = [dias[0]]
    periodo = {"desde": min(leidos).isoformat(), "hasta": max(leidos).isoformat(),
               "dias": len(dias_leidos)}

    escritos, cuadros = [], {}
    if not historico:
        nuevos = altas_desde_el_censo_anterior(acumuladores)
        escritos = [escribe(f"cabina/{acu.perfil['id']}/panel.json",
                            acu.panel(hoy, dict(periodo, dias=DIAS),
                                      nuevos.get(acu.perfil["id"], {})))
                    for acu in acumuladores]
    for acu in acumuladores:
        if acu.cuadro:
            cuadros[acu.perfil["id"]] = escribe_cuadro(acu, periodo, dias_leidos)
    series_escritas = {pid: escribe_serie(pid, filas, dias_leidos)
                       for pid, filas in series.items()}

    if not historico:
        escribe("cabina/_estado/carga.json", estado_de_la_carga(hoy))
    _cogidos = {acu.perfil.get("id"): lo_que_coge(acu.ambito, mapa) for acu in acumuladores}
    resumen = {
        "ejecucion": datetime.datetime.utcnow().isoformat() + "Z",
        "modo": "historico" if historico else "nocturna",
        "dias": len(dias_leidos),
        "periodo": periodo,
        "filas_leidas": dict(leidas),
        "maquinas_con_centro": mapa.aprendidas,
        # Un solo cliente significa que VenCloud todavia cuelga todos los centros
        # de «Serunion» y que el ambito se resuelve por el nombre del centro.
        # Varios, que la reasignacion ya entro y el campo `cliente` manda.
        "clientes": {"total": len(mapa.clientes), "muestra": sorted(mapa.clientes)[:20]},
        # LO PRIMERO QUE HAY QUE MIRAR. Un perfil a cero filas no es un mes
        # flojo: es un ambito que ha dejado de encajar, y si no se dice aqui se
        # descubre cuando llama el cliente. `coincide` dice si lo que el perfil
        # declara aparece en algun nombre de cliente o de centro de los leidos:
        # un ambito que no coincide con nada es casi siempre un nombre que
        # cambio en VenCloud.
        "perfiles": [
            {"id": acu.perfil.get("id"),
             "filas": acu.filas_en_ambito,
             "centros": len(acu.centros),
             "declara": acu.ambito.get("clientes", []),
             # Lo que coge de verdad, con el numero delante: es lo que hay que
             # copiar a `ambito.centros` en perfiles.json para que un renombrado
             # deje de importar.
             "coge_centros": [{"num": k, "nombre": v}
                              for k, v in sorted(_cogidos[acu.perfil.get("id")][0].items())][:25],
             # Y bajo que cliente cuelgan esos centros en VenCloud. Si no se
             # parece a lo que el perfil declara, el ambito esta viviendo del
             # nombre del centro.
             "clientes_de_verdad": sorted(_cogidos[acu.perfil.get("id")][1])[:10]}
            for acu in acumuladores
        ],
        # De donde ha salido la lista de perfiles. `consola.error` dice por que
        # no se ha podido leer la tabla; `sin_ambito`, los perfiles de la
        # consola que no se calculan porque no dicen de que cliente son.
        "consola": {"leidos": len(de_la_consola), "error": fallo_consola,
                    "sin_ambito": sin_ambito},
        "ficheros": escritos,
        # Que fuente de venta uso el cuadro y cuantas maquinas del censo tienen
        # venta. «visita_ventas» es la parcial: falta el informe de telemetria.
        "cuadros": cuadros,
        # Los meses de la serie diaria que ha tocado esta ejecucion, por perfil.
        "serie": series_escritas,
    }
    if parado_en:
        # Esto tiene que verse en la RESPUESTA, no solo en el registro: es la
        # instruccion de como seguir, y quien lanza un relleno mira la respuesta.
        resumen["incompleto"] = True
        resumen["continuar_desde"] = parado_en
        resumen["_siguiente"] = f'Relanza con {{"desde": "{parado_en}", "hasta": "..."}}'
    for p_ in resumen["perfiles"]:
        if p_["filas"] == 0 and p_["declara"]:
            print(f"AVISO: el perfil {p_['id']} se ha quedado SIN NINGUNA FILA. "
                  f"Declara {p_['declara']} y no encaja con ningun cliente ni centro leido.")
    if historico:
        clave_registro = (f"registro/agregados/historico/"
                          f"{periodo['desde']}_{periodo['hasta']}.json")
    else:
        clave_registro = (f"registro/agregados/anio={hoy.year}/mes={hoy.month:02d}/"
                          f"{hoy.isoformat()}.json")
    escribe(clave_registro, resumen)
    print(json.dumps(resumen, ensure_ascii=False))
    return resumen
