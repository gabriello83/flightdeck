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

Variables de entorno:
  BUCKET       el mismo de la extraccion
  DIAS         (opcional) dias hacia atras que se agregan; por defecto 120
  PERFILES     (opcional) clave del fichero de perfiles; por defecto config/perfiles.json
"""

import datetime
import gzip
import json
import os
from collections import defaultdict

import boto3

import reglas as R

s3 = boto3.client("s3")
BUCKET = os.environ["BUCKET"]
DIAS = int(os.environ.get("DIAS", "120"))
CLAVE_PERFILES = os.environ.get("PERFILES", "config/perfiles.json")

# Que informe alimenta que bloque. El orden importa poco; la lista, mucho:
# anadir un informe aqui es lo unico que hace falta para que entre en la cabina.
FUENTES = [
    ("partes",      "crudo/visita_cabecera",      "visita_cabecera",      "come_partes"),
    ("lineas",      "crudo/visita_reposiciones",  "visita_reposiciones",  "come_lineas"),
    ("mov_maquina", "crudo/stock_maquina",        "stock_maquina",        "come_mov_maquina"),
    ("recaudacion", "crudo/recaudacion",          "recaudacion",          "come_recaudacion"),
    ("sat",         "crudo/sat_averias",          "sat_averias",          "come_sat"),
    ("sat_eventos", "crudo/sat_eventos",          "sat_eventos",          "come_sat_eventos"),
    ("jornadas",    "crudo/jornadas",             "jornadas",             "come_jornadas"),
    ("balance",     "crudo/stock_balance",        "stock_balance",        "come_balance"),
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


# ----------------------------------------------------------------------
# filtrado por ambito
# ----------------------------------------------------------------------
def en_ambito(fila, ambito):
    """El ambito es aditivo: basta con encajar en uno de los tres.

    Un ambito vacio es "todo", y eso solo lo tienen los perfiles internos.
    """
    if not (ambito.get("clientes") or ambito.get("centros") or ambito.get("delegaciones")):
        return True
    centro = str(R.v(fila, "centro", ""))
    deleg = str(R.v(fila, "delegacion", ""))
    for c in ambito.get("clientes", []):
        if c.upper() in centro.upper():
            return True
    return centro in ambito.get("centros", []) or deleg in ambito.get("delegaciones", [])


# ----------------------------------------------------------------------
# el acumulador
# ----------------------------------------------------------------------
class Acumulador:
    """Un perfil, y lo que lleva sumado hasta ahora.

    Cada `come_*` recibe las filas de un informe de un dia, ya filtradas por el
    ambito, y suma. Nada guarda las filas.
    """

    def __init__(self, perfil):
        self.perfil = perfil
        self.ambito = perfil.get("ambito", {})

        # servicio
        self.partes_totales = 0
        self.visitas = 0
        self.maquinas = set()
        self.centros = set()
        self.duraciones = []
        self.visitas_por_dia = defaultdict(int)

        # carga
        self.carga_valor = 0.0
        self.carga_unidades = 0.0
        self.carga_vendibles = 0.0

        # merma
        self.merma = {m: {"lineas": 0, "unidades": 0.0, "euros": 0.0}
                      for m in ("caducidad", "rotura", "retirada")}

        # dinero, por periodo contable
        self.periodos = defaultdict(lambda: {"registros": 0, "efectivo": 0.0,
                                             "banco": 0.0, "ciego": 0.0})

        # SAT
        self.sat_leidas = 0
        self.sat_tareas = 0
        self.sat_averias = 0
        self.sat_preventivos = 0
        self.sat_fallos_tecnicos = 0
        self.sat_por_maquina = defaultdict(int)
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

    # ---------------------------------------------------------------- SAT
    def come_sat(self, filas):
        self.sat_leidas += len(filas)
        reales = R.tareas_de_maquina(filas)
        self.sat_tareas += len(reales)
        for t in reales:
            self.sat_por_maquina[R.v(t, "matricula")] += 1
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

    def panel(self, hoy, periodo):
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
                "carga": {
                    "valor": round(self.carga_valor, 2),
                    "unidades_total": self.carga_unidades,
                    "unidades_vendibles": self.carga_vendibles,
                    "_nota": "Dos de cada tres unidades son consumibles de cafe: azucar, vasos y paletinas.",
                },
                "merma": {m: {"lineas": d["lineas"],
                              "unidades": d["unidades"],
                              "euros": round(d["euros"], 2)}
                          for m, d in self.merma.items()},
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
                    [{"m": m, "n": n} for m, n in self.sat_por_maquina.items() if n >= 5],
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
                "pct_ciego": round(100 * ciego / ef, 1) if ef else 0.0,
                "provisional": R.mes_provisional(anio, mes, hoy),
            }
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
def lambda_handler(event, context):
    hoy = datetime.date.today()
    dias = [hoy - datetime.timedelta(days=d) for d in range(1, DIAS + 1)]

    perfiles = _json_de(CLAVE_PERFILES) or {"perfiles": [{"id": "interno", "ambito": {}}]}
    acumuladores = [Acumulador(p) for p in perfiles["perfiles"]]

    leidas = defaultdict(int)
    for nombre, destino, id_informe, metodo in FUENTES:
        for dia in dias:
            filas = lee_dia(destino, id_informe, dia)
            if not filas:
                continue
            leidas[nombre] += len(filas)
            for acu in acumuladores:
                propias = [f for f in filas if en_ambito(f, acu.ambito)]
                if propias:
                    getattr(acu, metodo)(propias)
            # El trozo se suelta aqui: en ningun momento hay mas de un informe
            # de un dia en memoria.
            del filas

    periodo = {"desde": dias[-1].isoformat(), "hasta": dias[0].isoformat(), "dias": DIAS}
    escritos = [escribe(f"cabina/{acu.perfil['id']}/panel.json", acu.panel(hoy, periodo))
                for acu in acumuladores]

    escribe("cabina/_estado/carga.json", estado_de_la_carga(hoy))
    resumen = {
        "ejecucion": datetime.datetime.utcnow().isoformat() + "Z",
        "dias": DIAS,
        "filas_leidas": dict(leidas),
        "ficheros": escritos,
    }
    escribe(f"registro/agregados/anio={hoy.year}/mes={hoy.month:02d}/{hoy.isoformat()}.json", resumen)
    print(json.dumps(resumen, ensure_ascii=False))
    return resumen
