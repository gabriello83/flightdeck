"""
El informe general operativo: ocho cuadrados con la cifra de un dia.

Lo pidio Gabriele el 13 de octubre de 2026: una pagina de cuadrados de colores,
cada uno con un dato principal, que abra la seccion operativa que le toca, con
los datos del perfil del usuario y arrancando en el dia de ayer (docs/51).

POR QUE ES UN FICHERO APARTE Y NO SALE DE LA SERIE. Tres de los ocho cuadrados
no se pueden sumar por dias ni se pueden reescribir hacia atras:

  · Las rutas se miden contra el PLAN de ese dia, y el plan de un dia pasado no
    se puede reconstruir con los maestros de hoy.
  · Las furgonetas activas son «distintas ese dia»: no se suman.
  · Los puntos de venta, la telemetria auditable y el valor de los almacenes
    son una FOTO de hoy, no un acumulado.

Asi que la noche escribe, para cada perfil, los ultimos dias con su cifra tal
cual, y la historia se acumula noche a noche: cada dia queda escrito con el plan
y el censo que habia cuando se cerro. Sin estimar nada. Lo que no esta se dice:
un cuadrado sin dato lleva `sin_dato` con el motivo, nunca un cero.

EL AMBITO SE APLICA AL ESCRIBIR, como en todo lo demas: las filas que llegan
aqui ya vienen filtradas por el perfil, y el fichero es uno por perfil.

Sin dependencias: se prueba con `python3 infra/test_operativo.py`.
"""

import datetime
import re
import unicodedata

import reglas as R

# Los colores que pidio Gabriele: verde por encima del 95 %, rojo por debajo
# del 75 %, amarillo entre medias. Viajan en el fichero para que la pagina no
# lleve una copia que se quede vieja el dia que se cambien.
VERDE = 95.0
AMARILLO = 75.0

# Cuantos dias se reescriben cada noche, y cuantos se guardan en el fichero.
# La extraccion vuelve a bajar los ultimos tres (ventana_reproceso_dias), asi
# que una semana cubre de sobra lo que pueda llegar tarde.
DIAS_NOCHE = 7
DIAS_GUARDADOS = 62
# El informe general guarda toda la historia (Gabriele, 19-oct: calendario,
# historico y varios dias). Desde el 1-ene-2025 son unos 660 dias; el tope solo
# esta para que el fichero no crezca sin fin. Va comprimido.
DIAS_HISTORIA = 1100

# En un relleno historico, cuantos dias antes del primero se leen las tareas de
# la SAT y sus eventos: una averia cerrada el 1 de marzo pudo abrirse en
# febrero, y sin su apertura no se mide. La misma ventana que la noche.
DIAS_PREVIOS_AVERIAS = 120

# Una fila sin delegacion (un punto de venta que no esta en el censo, una
# maquina sin centro) va con esta clave. Cuenta en el total y no en ninguna
# delegacion, y la pagina la ensena como «Sin delegación».
SIN_DELEGACION = ""

# Lo mismo por centro (David, 22-oct-2026: filtro de cliente y centro). Un
# punto de venta o una maquina sin centro va con esta clave: cuenta en el
# total y en ningun centro.
SIN_CENTRO = ""


def centro_de_la_fila(fila):
    """El centro que trae la propia fila, por su numero. La Lambda de agregados
    pasa una que, si la fila no lo trae, lo saca del centro de su maquina."""
    return str(R.v(fila, "num_centro", "") or "").strip()


# Lo que un relleno historico no sobrescribe de un dia que ya escribio la noche.
NO_PISA_EL_RELLENO = ("telemetria", "averias")

# El estado de un punto de venta en servicio (`pdv.estado`, docs/04, informe 20).
PDV_ACTIVO = 1

# Una averia se da por resuelta a tiempo si se cierra en menos de esto.
HORAS_A_TIEMPO = 24

# Las clases de maquina de VenCloud (`pdv.clase`, docs/04). Las que no estan
# aqui salen con su numero: mejor eso que inventarles un nombre.
CLASES = {
    0: "Bebida fría", 2: "Bebida caliente", 3: "Zumos", 4: "Combi", 7: "EPIs",
    8: "Tabaco", 9: "Snack", 10: "Fuente de agua", 11: "OCS / café cápsula",
    99: "Genérica", 100: "Compactadora", 101: "Máquina de cambio", 102: "Partner",
    200: "Kiosko",
}

# La pagina de furgonetas (docs/58). Gabriele, 19-oct-2026: los km de cada dia,
# en rojo si son menos de 10 o mas de 400. Viajan en el fichero, como los del
# semaforo.
KM_MIN, KM_MAX = 10, 400
# Un cuentakilometros por debajo de esto no se anoto: se teclea 1 o 2 en lugar
# de la lectura (docs/04, informe 46: 402 de 1.288 jornadas en septiembre).
KM_ANOTADO = 100
# Cuantos dias se recuerdan las visitas de cada furgoneta, para decir desde
# cuando no visita. La ventana de la noche son 120; lo de antes se acumula.
DIAS_VISITAS = 180
# Los km acumulados de cada furgoneta se cuentan desde aqui (Gabriele, 19-oct-2026:
# «desde 01/01/2025 hasta ayer»). Las jornadas de 2025 estan en el crudo.
KM_DESDE = "2025-01-01"
# Una furgoneta esta bien si se uso en la ultima semana y sus km de esos dias
# estan entre KM_MIN y KM_MAX.
SEMANA = 7
SIN_VEHICULOS = ("Falta el maestro de vehículos (M12, informe 191 de VenCloud) de esta "
                 "noche: sin él no se sabe qué furgonetas están activas.")

SIN_PLAN = ("No hay plan de visitas de este día: el informe D12 (VenCloud 184) "
            "no lo trae.")
SIN_CENSO_HISTORICO = ("En el relleno histórico no hay foto del censo de ese día: no se sabe "
                       "qué máquinas llevaban telemetría entonces.")


def delegacion_de_la_fila(fila):
    """La delegacion que trae la propia fila. La Lambda de agregados pasa una
    que, si la fila no la trae (las lineas de reposicion), la saca del centro
    de su maquina."""
    return str(R.v(fila, "delegacion", "") or "").strip()


def semaforo(pct):
    """verde, amarillo o rojo; None si no hay porcentaje que pintar."""
    if pct is None:
        return None
    if pct > VERDE:
        return "verde"
    if pct >= AMARILLO:
        return "amarillo"
    return "rojo"


def porcentaje(parte, total):
    return round(100.0 * parte / total, 1) if total else None


def hora(fecha):
    """«HH:MM» de una fecha de VenCloud («2026-10-15 08:12:31» o con T); «» si no trae."""
    s = str(fecha or "")
    if len(s) >= 16 and s[10] in " T" and s[13] == ":":
        return s[11:16]
    return ""


def nombre_clase(clase):
    try:
        c = int(clase)
    except (TypeError, ValueError):
        return "Sin clase"
    return CLASES.get(c, f"Clase {c}")


def vehiculo_real(v):
    """Una matricula de vehiculo de verdad. VenCloud rellena con «xxxx-xxx» o
    «xxxxxxx» el vehiculo que no se informo: eso no es una furgoneta."""
    s = str(v or "").strip()
    return bool(s) and not s.lower().startswith("xxx")


# La zona de cada delegacion: el nombre de VenCloud empieza por ella
# («Levante - Murcia»). Las mismas cinco del Power BI. La usan las paginas de
# incidencias (zonas) y de furgonetas (areas).
ZONAS = (("MADRID", "Centro"), ("ANDALUCIA", "Sur"), ("CATALUNA", "Cataluña"),
         ("LEVANTE", "Levante"), ("NORTE", "Norte"))
OTRA_ZONA = "Otra zona"


def sin_acentos(texto):
    t = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in t if unicodedata.category(c) != "Mn").upper()


def zona_de(delegacion):
    d = sin_acentos(delegacion).replace("Ñ", "N")
    for prefijo, zona in ZONAS:
        if d.startswith(prefijo):
            return zona
    return OTRA_ZONA


def es_furgoneta(ficha):
    """Una ficha del maestro de vehiculos (M12, informe 191) que es una
    furgoneta en servicio: activa, no obsoleta, con matricula, y que no es uno
    de los vehiculos ficticios que VenCloud usa para los sitios fijos
    («Ficticio RTVE TVE», «Ficticio La Paz»), ni SYSTEM, ni el de pruebas."""
    if not R.v(ficha, "activo", False) or R.v(ficha, "obsoleto", False):
        return False
    try:
        if int(R.v(ficha, "cod_vehiculo", 0) or 0) < 0:
            return False
    except (TypeError, ValueError):
        pass
    if not vehiculo_real(R.v(ficha, "matricula", "")):
        return False
    nombre = str(R.v(ficha, "denominacion", "") or "").strip().lower()
    return not (nombre.startswith("ficticio") or re.search(r"\btest\b", nombre))


def falta_en(jornada):
    """Lo que le falta a una jornada para tener km, o «» si los tiene."""
    a, b, cerrada = jornada[0], jornada[1], jornada[2]
    if not cerrada:
        return "sin cerrar"
    if a < KM_ANOTADO:
        return "sin anotar"
    if b < a:
        return "mal anotado"
    return ""


def km_del_dia(jornadas):
    """Los km de una furgoneta en un dia: [km, jornadas, lo que falta].

    `jornadas`: [(km iniciales, km finales, cerrada, ...)] del control de
    jornada (D5, informe 161). Los tramos de cuentakilometros bien anotados se
    juntan antes de sumar: VenCloud tiene la misma jornada dos veces en rutas
    distintas (3742KFL, 43.794 a 43.836, el 16-oct), y sumarlas daria el doble.
    km es None si ninguna esta bien, y entonces lo que falta dice por que:
    «sin cerrar» (la jornada sigue abierta), «sin anotar» (cuentakilometros de
    1 o 2) o «mal anotado» (el final por debajo del inicio). Nunca se rellena.
    """
    tramos, falta = [], set()
    for j in jornadas:
        f = falta_en(j)
        if f:
            falta.add(f)
        else:
            tramos.append((j[0], j[1]))
    km, hasta = 0.0, None
    for a, b in sorted(tramos):
        if hasta is None or a > hasta:
            km += b - a
            hasta = b
        elif b > hasta:
            km += b - hasta
            hasta = b
    return [round(km) if tramos else None, len(jornadas), " · ".join(sorted(falta))]


def jornadas_por_vehiculo(filas):
    """{vehiculoid: [[km ini, km fin, cerrada, empleado]]} de unas filas del
    control de jornada (D5). Una jornada abierta lleva el centinela de VenCloud
    (1900) en fechafin."""
    out = {}
    for j in filas:
        vid = R.v(j, "vehiculoid", None)
        if vid in (None, ""):
            continue
        try:
            a = float(R.v(j, "kminiciales", 0) or 0)
            b = float(R.v(j, "kmfinales", 0) or 0)
        except (TypeError, ValueError):
            a = b = 0.0
        cerrada = not str(R.v(j, "fechafin", "") or "1900").startswith("1900")
        out.setdefault(str(vid), []).append([a, b, cerrada, R.v(j, "empleadoid", None)])
    return out


def km_acumulados(historia, mat_de, flota, hasta):
    """Por matricula de la flota: [km desde KM_DESDE hasta `hasta`, jornadas sin
    km, empleado de la ultima jornada]. Dia a dia con km_del_dia, para que una
    jornada repetida no cuente dos veces."""
    out = {}
    for f in sorted(historia):
        if not (KM_DESDE <= f <= hasta):
            continue
        junto = {}
        for vid, js in historia[f].items():
            mat = mat_de.get(str(vid))
            if mat in flota:
                junto.setdefault(mat, []).extend(js)
        for mat, js in junto.items():
            x = out.setdefault(mat, [0, 0, None])
            km = km_del_dia(js)[0]
            x[0] += km or 0
            x[1] += sum(1 for j in js if falta_en(j))
            emp = [j[3] for j in js if len(j) > 3 and j[3] not in (None, "")]
            if emp:
                x[2] = emp[-1]
    return out


def es_lectura_remota(parte):
    """Un parte automatico (sin reponedor) que trae lectura de la maquina.

    Es el audit que la maquina manda sola por telemetria —el DEX—: parte de
    SYSTEM, que no es visita, con `estado_lectura` 2, que es como VenCloud marca
    la lectura capturada (docs/04, informe 33).
    """
    return not R.es_visita_real(parte) and int(R.v(parte, "estado_lectura", 0) or 0) == 2


def tiene_telemetria(fila):
    """Una maquina del censo que se puede auditar en remoto: lleva tipo de
    telemetria (40 en el parque de hoy). 0 o vacio es que no."""
    try:
        return int(R.v(fila, "telemetria", 0) or 0) != 0
    except (TypeError, ValueError):
        return False


# ----------------------------------------------------------------------
# un dia de un perfil
# ----------------------------------------------------------------------
class DiaOperativo:
    """Lo que un perfil acumula de UN dia para los cuadrados. Nada guarda filas."""

    def __init__(self, fecha, deleg_de=None, centro_de=None):
        self.fecha = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)[:10]
        # De que delegacion es una fila, para el filtro de area y delegacion.
        self.deleg_de = deleg_de or delegacion_de_la_fila
        # Y de que centro, para el de cliente y centro.
        self.centro_de = centro_de or centro_de_la_fila
        self.plan = None             # None = no hay informe del plan ese dia
        self.visitados = set()       # puntos de venta con visita real
        self.visitas = 0
        self.vehiculos = set()
        self.visitas_sin_vehiculo = 0
        self.dex = set()             # maquinas con lectura remota
        self.venta_tel = set()       # maquinas con venta por telemetria
        self.repo = {}               # clase -> unidades vendibles repuestas
        self.repo_consumibles = 0.0
        self.repo_valor = 0.0
        self.venta = None
        # Lo mismo, por delegacion: unidades por clase y carriles de cafe, y la
        # venta de los centros de cada una.
        self.repo_deleg = {}         # delegacion -> {clase: unidades}
        self.consumibles_deleg = {}  # delegacion -> unidades
        self.venta_deleg = None      # delegacion -> {"importe","unidades","maquinas"}
        self.vehiculos_deleg = {}    # delegacion -> {matriculas con visita}
        self.sin_vehiculo_deleg = {} # delegacion -> visitas sin vehiculo informado
        # Lo mismo, por centro (la clave del mapa de centros: el numero).
        self.repo_centro = {}
        self.consumibles_centro = {}
        self.venta_centro = None
        self.vehiculos_centro = {}
        self.sin_vehiculo_centro = {}
        self.visitas_centro = {}
        self.centro_pdv = {}         # pdv -> centro, del plan y de las visitas
        # Para la pagina de rutas (docs/55): de que delegacion, ruta y centro es
        # cada punto de venta del plan y cada uno visitado, y cuantas visitas
        # hizo cada delegacion. Un punto de venta, una entrada: no guarda filas.
        self.plan_de = {}            # pdv -> {"d","r":[rutas],"n","c","m"}
        self.visita_de = {}          # pdv -> {"d","r","e","n","c","m","h"}, la primera visita
        self.visitas_deleg = {}      # delegacion -> visitas reales
        # El pasaje vacio (informe 69 de VenCloud, docs/04): una visita sin
        # ninguna linea de reposicion. Que parte es de que punto de venta, y
        # que partes tienen alguna linea; se cruza al final, porque las lineas
        # llegan en otro informe y en cualquier orden.
        self.partes_pdv = {}         # parte_id -> pdv, solo visitas reales
        self.partes_con_lineas = set()

    def come_partes(self, filas):
        for p in filas:
            if R.es_visita_real(p):
                self.visitas += 1
                pdv = str(R.v(p, "cod_pdv", "") or "")
                deleg = str(R.v(p, "delegacion", "") or "")
                self.visitas_deleg[deleg] = self.visitas_deleg.get(deleg, 0) + 1
                centro = self.centro_de(p) or SIN_CENTRO
                self.visitas_centro[centro] = self.visitas_centro.get(centro, 0) + 1
                if pdv:
                    self.centro_pdv.setdefault(pdv, centro)
                    self.visitados.add(pdv)
                    pid = R.v(p, "parte_id", None)
                    if pid not in (None, ""):
                        self.partes_pdv[str(pid)] = pdv
                    x = {"d": deleg, "r": str(R.v(p, "ruta", "") or "").strip(),
                         "e": str(R.v(p, "empleado", "") or "").strip(),
                         "n": str(R.v(p, "num_centro", "") or ""),
                         "c": str(R.v(p, "centro", "") or "").strip(),
                         "m": str(R.v(p, "matricula", "") or "").strip(),
                         "h": hora(R.v(p, "fecha_ini", ""))}
                    # La primera visita del dia es la que se ensena.
                    antes = self.visita_de.get(pdv)
                    if antes is None or (x["h"] and (not antes["h"] or x["h"] < antes["h"])):
                        self.visita_de[pdv] = x
                v = R.v(p, "vehiculo", "")
                if vehiculo_real(v):
                    self.vehiculos.add(str(v).strip())
                    self.vehiculos_deleg.setdefault(deleg, set()).add(str(v).strip())
                    self.vehiculos_centro.setdefault(centro, set()).add(str(v).strip())
                else:
                    self.visitas_sin_vehiculo += 1
                    self.sin_vehiculo_deleg[deleg] = self.sin_vehiculo_deleg.get(deleg, 0) + 1
                    self.sin_vehiculo_centro[centro] = self.sin_vehiculo_centro.get(centro, 0) + 1
            elif es_lectura_remota(p):
                m = R.v(p, "matricula", "")
                if m:
                    self.dex.add(m)

    def come_telemetria(self, filas):
        """Las maquinas que mandaron venta por telemetria ese dia (informe 179)."""
        for f in filas:
            m = str(R.v(f, "matricula", "") or "").strip().upper()
            if m:
                self.venta_tel.add(m)

    def come_plan(self, filas):
        """El plan del dia: los puntos de venta que tocaba visitar.

        Se cuenta por punto de venta y no por fila: uno planificado por dos rutas
        es UNA visita prevista (docs/04, informe 69, el fallo de las filas dobles).
        """
        if self.plan is None:
            self.plan = set()
        for f in filas:
            pdv = str(R.v(f, "cod_pdv", "") or "")
            if pdv:
                self.plan.add(pdv)
                # El centro del plan manda sobre el de la visita: es el del dia.
                self.centro_pdv[pdv] = self.centro_de(f) or self.centro_pdv.get(pdv, SIN_CENTRO)
                ruta = str(R.v(f, "ruta", "") or "").strip()
                x = self.plan_de.setdefault(pdv, {
                    "d": str(R.v(f, "delegacion", "") or ""), "r": [],
                    "n": str(R.v(f, "num_centro", "") or ""),
                    "c": str(R.v(f, "centro", "") or "").strip(),
                    "m": str(R.v(f, "matricula", "") or "").strip()})
                if ruta and ruta not in x["r"]:
                    x["r"].append(ruta)

    def come_lineas(self, filas, clase_de):
        """Las unidades repuestas, por clase de maquina.

        Lo que se carga en los carriles de una maquina caliente (cafe, leche,
        azucar, vasos, paletinas) va aparte: son el 62 % de las unidades
        cargadas (reglas.es_consumible_de_cafe) y no se pueden sumar con una
        lata. Por eso la clase «Bebida caliente» sale casi a cero en producto:
        lo suyo esta en `consumibles`, y la pagina lo dice.
        """
        self.repo_valor += R.valor_cargado(filas)
        for l in filas:
            pid = R.v(l, "parte_id", None)
            if pid not in (None, ""):
                self.partes_con_lineas.add(str(pid))
            if R.v(l, "tipo_linea") != "CM":
                continue
            u = float(R.v(l, "cantidad", 0) or 0)
            deleg = self.deleg_de(l)
            centro = self.centro_de(l) or SIN_CENTRO
            if R.es_consumible_de_cafe(l):
                self.repo_consumibles += u
                self.consumibles_deleg[deleg] = self.consumibles_deleg.get(deleg, 0.0) + u
                self.consumibles_centro[centro] = self.consumibles_centro.get(centro, 0.0) + u
                continue
            clase = nombre_clase(clase_de.get(R.v(l, "matricula", "")))
            self.repo[clase] = self.repo.get(clase, 0.0) + u
            por = self.repo_deleg.setdefault(deleg, {})
            por[clase] = por.get(clase, 0.0) + u
            por = self.repo_centro.setdefault(centro, {})
            por[clase] = por.get(clase, 0.0) + u

    def pon_venta(self, dia_serie, deleg_del_centro=None):
        """La venta del dia, de la MISMA cuenta que la serie (serie.Dia): una
        sola regla de venta, no dos.

        Por delegacion, la de los centros de cada una: el mismo dia partido por
        centro que usa el filtro de la serie (serie.PorCentro), sumado por la
        delegacion de cada centro. `deleg_del_centro(clave)` dice cual es."""
        self.venta = {
            "importe": round(dia_serie.venta_importe, 2),
            "unidades": round(dia_serie.venta_unidades, 2),
            "maquinas": len(dia_serie.venta_maquinas),
            "fuente": dia_serie.venta_fuente,
            "imposibles": dia_serie.venta_imposibles,
        }
        por_centro = getattr(dia_serie, "por_centro", None)
        if por_centro is None:
            return
        # Por centro, tal cual lo parte la serie: es la misma clave.
        self.venta_centro = {}
        for clave, c in por_centro.c.items():
            if c.venta_unidades or c.venta_importe:
                self.venta_centro[str(clave)] = {"importe": c.venta_importe, "unidades": c.venta_unidades,
                                                 "maquinas": len(c.venta_maquinas)}
        if deleg_del_centro is None:
            return
        self.venta_deleg = {}
        for clave, c in self.venta_centro.items():
            x = self.venta_deleg.setdefault(deleg_del_centro(clave) or SIN_DELEGACION,
                                            {"importe": 0.0, "unidades": 0.0, "maquinas": 0})
            for k in x:
                x[k] += c[k]


# ----------------------------------------------------------------------
# un perfil, a lo largo de la ventana
# ----------------------------------------------------------------------
class Operativo:
    """Los cuadrados de un perfil.

    Los dias que se publican se llevan con su `DiaOperativo`. Las averias no:
    una averia cerrada ayer pudo abrirse hace un mes, asi que su apertura, su
    cierre y si es un fallo tecnico se recuerdan a lo largo de TODA la ventana,
    y se cuentan al final.
    """

    def __init__(self, publicar, historico=False, deleg_de=None, centro_de=None):
        self.dias = {d.isoformat() if hasattr(d, "isoformat") else str(d): None for d in publicar}
        # En un relleno historico no se escribe foto (el censo de hoy no es el
        # de enero de 2025) y cada dia se cierra en cuanto se ha leido, para no
        # tener meses de partes en memoria: queda solo su cifra (`cerrados`).
        self.historico = historico
        self.cerrados = {}
        self.cerrados_centro = {}
        self.deleg_de = deleg_de or delegacion_de_la_fila
        self.centro_de = centro_de or centro_de_la_fila
        self.deleg_tarea = {}    # id de tarea -> delegacion
        self.centro_tarea = {}   # id de tarea -> centro
        self._deleg_maquina = {} # matricula -> delegacion, del censo
        self._centro_maquina = {} # matricula -> centro, del censo
        # La ficha de cada centro (nombre, cliente, delegacion), para el filtro
        # de cliente y centro. La pone la Lambda de agregados con su mapa.
        self.ficha_de = lambda clave: None
        self.fallo = {}          # id de tarea -> es un fallo tecnico
        self.apertura = {}
        self.cierre = {}
        self.foto = {}
        # La telemetria segun los ficheros de los sistemas de cobro (docs/53):
        # None mientras no se haya subido ninguno.
        self.externa = None
        self.fuera = None
        # Los cierres de inventario de ALMACEN, por periodo. Solo las filas de
        # tipo A: son unas quince al mes.
        self.balance = {}
        # La pagina de furgonetas (docs/58), en TODA la ventana y no solo en los
        # dias que se publican: que dias visito cada vehiculo (partes de
        # reposicion y visitas de la SAT), para saber desde
        # cuando no visita, y las jornadas de cada dia, para sus km. `desde` es
        # el primer dia que se leyo: lo de antes no se sabe.
        self.visitas_de = {}     # matricula -> {fechas con visita real}
        self.jornadas = {}       # fecha -> {vehiculoid: [(km ini, km fin, cerrada, empleado)]}
        self.desde = None

    def dia(self, fecha):
        f = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)[:10]
        if f not in self.dias:
            return None
        if self.dias[f] is None:
            if f in self.cerrados:
                return None
            self.dias[f] = DiaOperativo(f, self.deleg_de, self.centro_de)
        return self.dias[f]

    def cierra(self, fecha):
        """Un dia del relleno historico ya leido: se queda su cifra y se suelta
        lo demas. Las averias se cuentan al final, con toda la ventana."""
        f = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)[:10]
        d = self.dias.get(f)
        if d is not None:
            self.cerrados[f] = self._del_dia(d)
            self.cerrados_centro[f] = self.por_centro(d)
            self.dias[f] = None

    # ------------------------------------------------------------- furgonetas
    def come_visitas_vehiculo(self, fecha, filas):
        """Los dias que visito cada vehiculo. Las filas ya vienen del ambito."""
        f = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)[:10]
        for p in filas:
            v = R.v(p, "vehiculo", "")
            if R.es_visita_real(p) and vehiculo_real(v):
                self.visitas_de.setdefault(str(v).strip(), set()).add(f)

    def come_visitas_sat(self, filas):
        """Los dias que visito cada furgoneta de un tecnico (informe 163).

        El fichero va por la fecha de la averia, no por la de la visita: una
        visita del dia 16 a una averia del 14 esta en el fichero del 14. Por eso
        el dia se saca de `inicio`.
        """
        for v in filas:
            veh = R.v(v, "vehiculo", "")
            f = str(R.v(v, "inicio", "") or "")[:10]
            if vehiculo_real(veh) and len(f) == 10 and not f.startswith("1900"):
                self.visitas_de.setdefault(str(veh).strip(), set()).add(f)

    def come_jornadas(self, fecha, filas):
        """El control de jornada de un dia (D5, informe 161), ENTERO: no trae
        centro ni delegacion, asi que de quien es cada furgoneta lo decide el
        maestro de vehiculos al escribir (detalle_furgonetas)."""
        f = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)[:10]
        dia = self.jornadas.setdefault(f, {})
        for vid, js in jornadas_por_vehiculo(filas).items():
            dia.setdefault(vid, []).extend(js)

    # ------------------------------------------------------------- averias
    def come_sat(self, filas):
        """Que tareas son averias. La misma regla que el panel y la serie: fallo
        tecnico por operacion, sin solicitudes especiales (serie E) y sin la
        matricula ficticia."""
        for t in R.tareas_de_maquina(filas):
            ident = R.v(t, "id", None)
            if ident is None:
                continue
            self.fallo[ident] = R.es_fallo_tecnico(t) and not R.es_solicitud_especial(t)
            if self.fallo[ident]:
                self.deleg_tarea[ident] = self.deleg_de(t)
                self.centro_tarea[ident] = self.centro_de(t) or SIN_CENTRO

    def come_sat_eventos(self, filas):
        for e in filas:
            ident = R.v(e, "averia_id")
            cuando = str(R.v(e, "fecha", ""))[:19].replace("T", " ")
            if not cuando:
                continue
            if ident not in self.apertura or cuando < self.apertura[ident]:
                self.apertura[ident] = cuando
            if int(R.v(e, "estado", -1)) == 99:
                if ident not in self.cierre or cuando < self.cierre[ident]:
                    self.cierre[ident] = cuando

    def averias_del_dia(self, fecha):
        """Las averias cerradas ese dia, y cuantas en menos de 24 horas.

        La tarea se baja por su fecha de alta, asi que solo se sabe que una
        tarea es una averia si se abrio dentro de la ventana (120 dias); y si se
        abrio dentro, todos sus eventos tambien estan, y su apertura es buena.
        Un cierre de una tarea abierta antes no se puede medir: no se cuenta, y
        se dice cuantos son (`sin_tarea`).
        """
        cerradas, a_tiempo, sin_tarea, _, _ = self._averias(fecha)
        return cerradas, a_tiempo, sin_tarea

    def _averias(self, fecha):
        """averias_del_dia, y ademas las mismas cuentas por delegacion y por centro."""
        cerradas = a_tiempo = sin_tarea = 0
        por, por_c = {}, {}
        for ident, cierre in self.cierre.items():
            if cierre[:10] != fecha:
                continue
            if ident not in self.fallo:
                sin_tarea += 1
                continue
            if not self.fallo[ident]:
                continue
            horas = (datetime.datetime.fromisoformat(cierre)
                     - datetime.datetime.fromisoformat(self.apertura[ident])).total_seconds() / 3600
            x = por.setdefault(self.deleg_tarea.get(ident, SIN_DELEGACION),
                               {"cerradas": 0, "a_tiempo": 0})
            y = por_c.setdefault(self.centro_tarea.get(ident, SIN_CENTRO),
                                 {"cerradas": 0, "a_tiempo": 0})
            cerradas += 1
            x["cerradas"] += 1
            y["cerradas"] += 1
            if horas < HORAS_A_TIEMPO:
                a_tiempo += 1
                x["a_tiempo"] += 1
                y["a_tiempo"] += 1
        return cerradas, a_tiempo, sin_tarea, por, por_c

    # ------------------------------------------------------------- la foto
    def come_censo(self, filas):
        """Lo que es foto de hoy: puntos de venta activos y maquinas que se
        pueden auditar en remoto. Las filas ya vienen del ambito del perfil."""
        pdvs, maquinas, auditables = set(), set(), set()
        por, por_c = {}, {}
        for f in filas:
            if (R.es_centinela(f) or not R.cliente_vivo(f) or not R.centro_vivo(f)
                    or not R.pdv_vivo(f)):
                continue
            pdv = str(R.v(f, "cod_pdv", "") or "")
            # Activo es el estado 1 de VenCloud, el mismo que usa su informe 20.
            # El estado 0 son sitios sin maquina puesta: 2.012 en el parque de
            # octubre de 2026, que no son puntos de venta que atender.
            deleg = delegacion_de_la_fila(f)
            centro = self.centro_de(f) or SIN_CENTRO
            x = por.setdefault(deleg, [set(), set()])
            y = por_c.setdefault(centro, [set(), set()])
            if pdv and str(R.v(f, "estado_pdv", "")) == str(PDV_ACTIVO):
                pdvs.add(pdv)
                x[0].add(pdv)
                y[0].add(pdv)
            m = R.v(f, "matricula", "")
            if m:
                maquinas.add(m)
                x[1].add(m)
                y[1].add(m)
                self._deleg_maquina.setdefault(m, deleg)
                self._centro_maquina.setdefault(m, centro)
                if tiene_telemetria(f):
                    auditables.add(m)
        self.foto["pdvs"] = {"activos": len(pdvs), "maquinas": len(maquinas),
                             "por_delegacion": {k: {"activos": len(a), "maquinas": len(b)}
                                                for k, (a, b) in sorted(por.items()) if a or b},
                             # Por centro, en listas [activos, maquinas]: son miles.
                             "por_centro": {k: [len(a), len(b)]
                                            for k, (a, b) in sorted(por_c.items()) if a or b}}
        self._auditables = auditables

    def pon_telemetria(self, cruce, propias, ficheros, fuera=None):
        """Las diferencias entre los sistemas de telemetria y VenCloud.

        Gabriele, 15-oct: el dato de telemetria sale SIEMPRE de VenCloud; los
        ficheros de Nayax, Prodelfi y Nebula solo sirven para ver en que no
        coinciden. Asi que esto no toca el cuadrado: alimenta la pagina de
        diferencias, con las maquinas que tiene algun sistema y las que VenCloud
        marca con telemetria aunque no las tenga ninguno.

        `cruce` es telemetria.cruza() sobre el censo ENTERO; `propias`, las filas
        del censo de este perfil: el ambito se aplica aqui, al escribir. Las que
        estan en un sistema y no en VenCloud no tienen centro, asi que no son de
        ningun perfil acotado: solo las ve el que no tiene ambito, y para los
        demas `fuera` llega None.
        """
        if cruce is None:
            return
        maquinas = {}
        for f in propias:
            mat = str(R.v(f, "matricula", "") or "").strip().upper()
            if not mat or mat in maquinas:
                continue
            x = cruce["maquinas"].get(mat)
            marcada = tiene_telemetria(f)
            if not x and not marcada:
                continue
            if not x:
                # VenCloud dice que lleva telemetria y no esta en ningun fichero.
                x = {"sistema": "solo_vencloud", "sistemas": []}
            maquinas[mat] = dict(x, vencloud=marcada, censo={
                    "delegacion": R.v(f, "delegacion", ""), "cliente": R.v(f, "cliente", ""),
                    "num_centro": R.v(f, "num_centro", ""), "centro": R.v(f, "centro", ""),
                    "cod_pdv": str(R.v(f, "cod_pdv", "") or ""), "ubicacion": R.v(f, "ubicacion", ""),
                    "modelo": str(R.v(f, "modelo", "") or "").strip()})
        self.externa = maquinas
        self.fuera = fuera
        self.foto["telemetria"] = ficheros

    def come_balance(self, filas):
        for b in filas:
            if R.v(b, "tipo_elemento") != "A":
                continue
            periodo = (int(R.v(b, "anho", 0) or 0), int(R.v(b, "mes", 0) or 0))
            self.balance.setdefault(periodo, []).append(b)

    def pon_almacenes(self, almacenes):
        self.foto["almacenes"] = almacenes

    # ------------------------------------------------------------- salida
    def cuadrados_del_dia(self, d):
        return self._con_averias(d.fecha, self._del_dia(d))

    def _con_averias(self, fecha, out):
        """Las averias van aparte del resto del dia: se cuentan con toda la
        ventana leida, asi que en un relleno historico se ponen al final."""
        out = dict(out)
        cerradas, a_tiempo, sin_tarea, por, _ = self._averias(fecha)
        pct = porcentaje(a_tiempo, cerradas)
        out["averias"] = ({"cerradas": cerradas, "a_tiempo": a_tiempo, "pct": pct,
                           "color": semaforo(pct), "horas": HORAS_A_TIEMPO,
                           "sin_tarea": sin_tarea}
                          if cerradas else
                          {"sin_dato": "Ese día no se cerró ninguna avería.",
                           "cerradas": 0, "sin_tarea": sin_tarea})
        out["por_delegacion"] = dict(out.get("por_delegacion") or {},
                                     averias=dict(sorted(por.items())))
        return out

    def _del_dia(self, d):
        """Los cuadrados de un dia menos las averias, cada uno con su reparto
        por delegacion en `por_delegacion` (el filtro de area y delegacion)."""
        out = {}
        if d.plan is None:
            out["rutas"] = {"sin_dato": SIN_PLAN, "visitas": d.visitas}
        elif not d.plan:
            out["rutas"] = {"sin_dato": "El plan de ese día no tiene ninguna visita prevista.",
                            "visitas": d.visitas}
        else:
            hechas = len(d.plan & d.visitados)
            pct = porcentaje(hechas, len(d.plan))
            out["rutas"] = {"previstas": len(d.plan), "hechas": hechas, "pct": pct,
                            "color": semaforo(pct), "visitas": d.visitas,
                            "fuera_de_plan": len(d.visitados - d.plan)}

        # La lista de matriculas va con la cifra: para varios dias, las
        # furgonetas son las distintas del rango, no la suma de cada dia.
        out["furgonetas"] = {"activas": len(d.vehiculos), "visitas": d.visitas,
                             "visitas_sin_vehiculo": d.visitas_sin_vehiculo,
                             "vehiculos": sorted(d.vehiculos)}

        out["ventas"] = (dict(d.venta) if d.venta and (d.venta["unidades"] or d.venta["fuente"])
                         else {"sin_dato": "Ese día no llegó venta ni por telemetría ni del parte."})

        total = sum(d.repo.values())
        out["reposiciones"] = {
            "unidades": round(total, 2),
            "por_clase": [{"clase": k, "unidades": round(v, 2)}
                          for k, v in sorted(d.repo.items(), key=lambda x: -x[1])],
            "consumibles": round(d.repo_consumibles, 2),
            "valor": round(d.repo_valor, 2),
        }

        out["telemetria"] = self.telemetria_vencloud(d)
        if self.externa is not None and "sin_dato" not in out["telemetria"]:
            out["telemetria"]["diferencias"] = self.diferencias()
        # Siempre, aunque vaya vacio: un dia sin `por_delegacion` es de antes de
        # que existiera el reparto, y la pagina lo dice en vez de sumar cero.
        out["por_delegacion"] = self.por_delegacion(d)
        return out

    def por_delegacion(self, d):
        """Las cifras de un dia por delegacion, cuadrado a cuadrado.

        Solo lo que se puede sumar y recalcular: previstas y hechas, cerradas y
        a tiempo, importe, unidades, auditables y con lectura. Un cuadrado que
        esta va aunque no tenga ninguna delegacion: es un cero de verdad; uno
        que falta es que ese dia no se pudo repartir. La pagina suma
        las delegaciones elegidas y saca el porcentaje del total, no la media de
        porcentajes. Las furgonetas llevan su lista: una que paso por dos
        delegaciones cuenta en las dos, y una sola vez en las dos juntas.
        El ambito ya esta aplicado: solo salen las delegaciones de este fichero.
        """
        out = {}
        if d.plan:
            rutas = {}
            for pdv in d.plan:
                dl = (d.plan_de.get(pdv) or {}).get("d", SIN_DELEGACION)
                x = rutas.setdefault(dl, {"previstas": 0, "hechas": 0, "fuera": 0, "visitas": 0})
                x["previstas"] += 1
                x["hechas"] += pdv in d.visitados
            for pdv in d.visitados - d.plan:
                dl = (d.visita_de.get(pdv) or {}).get("d", SIN_DELEGACION)
                rutas.setdefault(dl, {"previstas": 0, "hechas": 0, "fuera": 0, "visitas": 0})["fuera"] += 1
            for dl, n in d.visitas_deleg.items():
                rutas.setdefault(dl, {"previstas": 0, "hechas": 0, "fuera": 0, "visitas": 0})["visitas"] = n
            out["rutas"] = dict(sorted(rutas.items()))

        furgos = {}
        for dl in set(d.vehiculos_deleg) | set(d.visitas_deleg) | set(d.sin_vehiculo_deleg):
            furgos[dl] = {"vehiculos": sorted(d.vehiculos_deleg.get(dl, ())),
                          "visitas": d.visitas_deleg.get(dl, 0),
                          "visitas_sin_vehiculo": d.sin_vehiculo_deleg.get(dl, 0)}
        out["furgonetas"] = dict(sorted(furgos.items()))

        if d.venta_deleg is not None:
            out["ventas"] = {dl: {"importe": round(x["importe"], 2), "unidades": round(x["unidades"], 2),
                                  "maquinas": x["maquinas"]}
                             for dl, x in sorted(d.venta_deleg.items())}

        repo = {}
        for dl in set(d.repo_deleg) | set(d.consumibles_deleg):
            clases = d.repo_deleg.get(dl, {})
            repo[dl] = {"unidades": round(sum(clases.values()), 2),
                        "consumibles": round(d.consumibles_deleg.get(dl, 0.0), 2),
                        "por_clase": {k: round(u, 2) for k, u in sorted(clases.items(), key=lambda x: -x[1])}}
        out["reposiciones"] = dict(sorted(repo.items()))

        auditables = getattr(self, "_auditables", None)
        if auditables:
            tel = {}
            for m in auditables:
                x = tel.setdefault(self._deleg_maquina.get(m, SIN_DELEGACION), {"auditables": 0, "con_dex": 0})
                x["auditables"] += 1
                x["con_dex"] += m in d.dex
            out["telemetria"] = dict(sorted(tel.items()))
        return out

    def por_centro(self, d):
        """Las cifras de un dia por centro, para el filtro de cliente y centro
        (David, 22-oct-2026). Las mismas que `por_delegacion`, pero en listas,
        porque son miles de centros al dia y van a un fichero por mes:

          rutas        [previstas, hechas, fuera del plan, visitas]
          furgonetas   [visitas, visitas sin vehiculo, [matriculas]]
          ventas       [importe, unidades, maquinas]
          reposiciones [unidades, carriles de cafe, {clase: unidades}]
          telemetria   [auditables, con lectura]

        Las averias se ponen al escribir, con toda la ventana (centros_del_dia).
        Un centro sin nada ese dia no sale.
        """
        out = {}
        if d.plan:
            rutas = {}
            vacio = lambda: [0, 0, 0, 0]
            for pdv in d.plan:
                x = rutas.setdefault(d.centro_pdv.get(pdv, SIN_CENTRO), vacio())
                x[0] += 1
                x[1] += pdv in d.visitados
            for pdv in d.visitados - d.plan:
                rutas.setdefault(d.centro_pdv.get(pdv, SIN_CENTRO), vacio())[2] += 1
            for c, n in d.visitas_centro.items():
                rutas.setdefault(c, vacio())[3] = n
            out["rutas"] = dict(sorted(rutas.items()))

        out["furgonetas"] = {c: [d.visitas_centro.get(c, 0), d.sin_vehiculo_centro.get(c, 0),
                                 sorted(d.vehiculos_centro.get(c, ()))]
                             for c in sorted(set(d.vehiculos_centro) | set(d.visitas_centro)
                                             | set(d.sin_vehiculo_centro))}

        if d.venta_centro is not None:
            out["ventas"] = {c: [round(x["importe"], 2), round(x["unidades"], 2), x["maquinas"]]
                             for c, x in sorted(d.venta_centro.items())}

        repo = {}
        for c in set(d.repo_centro) | set(d.consumibles_centro):
            clases = d.repo_centro.get(c, {})
            repo[c] = [round(sum(clases.values()), 2), round(d.consumibles_centro.get(c, 0.0), 2),
                       {k: round(u, 2) for k, u in sorted(clases.items(), key=lambda x: -x[1])}]
        out["reposiciones"] = dict(sorted(repo.items()))

        auditables = getattr(self, "_auditables", None)
        if auditables:
            tel = {}
            for m in auditables:
                x = tel.setdefault(self._centro_maquina.get(m, SIN_CENTRO), [0, 0])
                x[0] += 1
                x[1] += m in d.dex
            out["telemetria"] = dict(sorted(tel.items()))
        return out

    def centros_del_dia(self, fecha, por):
        """El reparto por centro de un dia, con sus averias: van aparte porque
        se cuentan con toda la ventana leida."""
        por = dict(por)
        por["averias"] = {c: [x["cerradas"], x["a_tiempo"]]
                          for c, x in sorted(self._averias(fecha)[4].items())}
        return por

    def centros_por_mes(self, anteriores):
        """Los ficheros del reparto por centro, uno por mes: {"2026-10": {...}}.

        `anteriores(mes)` da el fichero de ese mes que ya habia, o None. Los
        dias de esta noche (o del relleno) sustituyen a los que hubiera; los
        demas se quedan. Como en el informe, un relleno no pisa la telemetria
        ni las averias de un dia que ya escribio la noche.
        """
        nuevos = {}
        for f, d in self.dias.items():
            if d is not None:
                nuevos[f] = self.centros_del_dia(f, self.por_centro(d))
        for f, x in self.cerrados_centro.items():
            nuevos[f] = self.centros_del_dia(f, x)
        meses = {}
        for f in sorted(nuevos):
            mes = f[:7]
            if mes not in meses:
                antes = anteriores(mes) or {}
                meses[mes] = {"mes": mes, "dias": dict(antes.get("dias") or {})}
            dias = meses[mes]["dias"]
            x = nuevos[f]
            if f in self.cerrados_centro:
                antes = dias.get(f) or {}
                for c in NO_PISA_EL_RELLENO:
                    if antes.get(c):
                        x[c] = antes[c]
            dias[f] = x
        for m in meses.values():
            m["dias"] = dict(sorted(m["dias"].items()))
        return meses

    def fichas_de_centros(self, meses, anterior=None):
        """Nombre, cliente y delegacion de cada centro que sale en el reparto o
        en la foto: lo que la pagina necesita para listar clientes y centros.
        Las fichas de antes se quedan: un centro que ya no aparece sigue en los
        dias viejos."""
        fichas = dict((anterior or {}).get("centros") or {})
        claves = set()
        for m in meses.values():
            for x in m["dias"].values():
                for por in x.values():
                    claves.update(por)
        claves.update((self.foto.get("pdvs") or {}).get("por_centro") or {})
        claves.discard(SIN_CENTRO)
        for c in claves:
            f = self.ficha_de(c)
            if f:
                fichas[c] = {"n": f.get("nombre") or c, "c": f.get("cliente") or "",
                             "d": f.get("delegacion") or ""}
            elif c not in fichas:
                fichas[c] = {"n": c, "c": "", "d": ""}
        return dict(sorted(fichas.items()))

    def telemetria_vencloud(self, d):
        """Sin ficheros de los sistemas: lo que VenCloud dice que lleva telemetria
        (40 maquinas en octubre de 2026) y cuantas mandaron su DEX."""
        auditables = getattr(self, "_auditables", None)
        if auditables:
            con = len(d.dex & auditables)
            pct = porcentaje(con, len(auditables))
            return {"auditables": len(auditables), "con_dex": con, "pct": pct,
                    "color": semaforo(pct)}
        if self.historico:
            return {"sin_dato": SIN_CENSO_HISTORICO}
        return {"sin_dato": "Ninguna máquina de este ámbito lleva telemetría."
                if auditables is not None else "No se ha podido leer el censo."}

    def diferencias(self):
        """Cuantas maquinas no cuadran entre los sistemas y VenCloud (docs/53).

        Solo lo que se ve sin mirar el dia: maquinas de un sistema que VenCloud
        no marca con telemetria, las que VenCloud marca y no tiene ningun
        sistema, y las de un sistema que no estan en VenCloud. Lo que pasa cada
        dia (si mandaron venta o DEX) esta en la pagina.
        """
        en_sistema = [x for x in self.externa.values() if x["sistema"] != "solo_vencloud"]
        return {"en_sistemas": len(en_sistema),
                "sin_marca": sum(1 for x in en_sistema if not x["vencloud"]),
                "solo_vencloud": sum(1 for x in self.externa.values()
                                     if x["sistema"] == "solo_vencloud"),
                "fuera": len(self.fuera) if self.fuera is not None else None}

    def detalle_telemetria(self, perfil_id, anterior=None):
        """El fichero de la pagina de telemetria: maquina a maquina, que dias de
        la semana mandaron venta y cuales DEX.

        Como el informe, acumula: los dias de esta noche sobre los que ya habia
        escritos, para que un dia que ya no se recalcula no se pierda. Cada dia
        guarda solo las maquinas que mandaron algo; el resto es lo que falta.
        """
        if self.externa is None:
            return None
        previos = (anterior or {}).get("dias") or {}
        dias = {}
        for f, d in self.dias.items():
            if d is not None:
                dias[f] = {"venta": sorted(m for m in self.externa if m in d.venta_tel),
                           "dex": sorted(m for m in self.externa if m in d.dex)}
        for f, v in previos.items():
            dias.setdefault(f, v)
        dias = dict(sorted(dias.items())[-DIAS_NOCHE:])
        maquinas = []
        for m, x in sorted(self.externa.items()):
            c = x["censo"]
            fila = {"matricula": m, "sistema": x["sistema"],
                    "tambien": [s for s in x["sistemas"] if s != x["sistema"]],
                    "vencloud": x["vencloud"],
                    "delegacion": c["delegacion"], "cliente": c["cliente"],
                    "num_centro": c["num_centro"], "centro": c["centro"],
                    "cod_pdv": c["cod_pdv"], "ubicacion": c["ubicacion"],
                    "modelo": c.get("modelo", "")}
            if "nayax" in x:
                fila["nayax"] = {"id": x["nayax"]["id"], "ultima": x["nayax"]["ultima"]}
            if "prodelfi" in x:
                p = x["prodelfi"]
                fila["prodelfi"] = {"codigo": p["codigo"], "grupo": p["grupo"],
                                    "descripcion": p["descripcion"], "como": p["como"]}
            if "nebula" in x:
                fila["nebula"] = dict(x["nebula"])
            maquinas.append(fila)
        # El area de cada delegacion (Gabriele, 19-oct): quien ve mas de un area
        # abre primero un cuadrado por area y, dentro, el listado. Las cinco del
        # Power BI, las mismas que incidencias, devoluciones y la revision.
        # (Aqui y no arriba: incidencias importa este modulo.)
        import incidencias as IN
        return {
            "generado": datetime.datetime.utcnow().isoformat() + "Z",
            "perfil": perfil_id,
            "ultimo_dia": max(dias) if dias else None,
            "dias": dias,
            "ficheros": self.foto.get("telemetria"),
            "maquinas": maquinas,
            "zonas": {d: IN.zona_de(d) for d in sorted({m["delegacion"] for m in maquinas})},
            "fuera": self.fuera,
            "_nota": ("Diferencias entre los sistemas de telemetría (ficheros de Nayax, Prodelfi y "
                      "Nebula subidos en la consola) y VenCloud: máquinas de un sistema, con "
                      "«vencloud» si el censo las marca con telemetría, y las que el censo marca "
                      "sin estar en ningún sistema (sistema «solo_vencloud»). Cada día lleva "
                      "las que mandaron venta por telemetría (informe 179) y las que mandaron "
                      "su lectura (DEX). «modelo» es el de VenCloud (vacío si el censo no lo "
                      "trae). «zonas» da el área de cada delegación. «fuera» son las de esos sistemas que no están en "
                      "VenCloud; null si el perfil está acotado (no tienen centro)."),
        }

    def detalle_rutas(self, perfil_id, anterior=None, festivos=None, ubicaciones=None):
        """El fichero de la pagina de rutas (docs/55).

        Cada dia, por delegacion y por ruta, lo previsto y lo hecho; y los puntos
        de venta que no se visitaron y las visitas fuera de plan, con su centro.
        Acumula como el informe: los dias de esta noche sobre los que ya habia.
        Las listas de puntos de venta solo se guardan de la ultima semana; las
        cifras, de DIAS_GUARDADOS, que es lo que necesita el control de festivos
        para saber como es un dia normal de cada delegacion.
        """
        dias = dict((anterior or {}).get("dias") or {})
        for f, d in self.dias.items():
            if d is not None:
                dias[f] = rutas_del_dia(d, ubicaciones)
        dias = dict(sorted(dias.items())[-DIAS_GUARDADOS:])
        recientes = set(sorted(dias)[-DIAS_NOCHE:])
        for f, v in dias.items():
            # Las listas de antes del 16-oct-2026 se llamaban no_visitados y
            # fuera: tambien se sueltan.
            v.pop("no_visitados", None)
            v.pop("fuera", None)
            if f not in recientes:
                v.pop("visitas", None)
        return {
            "generado": datetime.datetime.utcnow().isoformat() + "Z",
            "perfil": perfil_id,
            "ultimo_dia": max(dias) if dias else None,
            "umbrales": {"verde": VERDE, "amarillo": AMARILLO, "festivo_bajo": FESTIVO_BAJO},
            "festivos": resumen_festivos(festivos),
            "dias": dias,
            "control_festivos": control_festivos(dias, festivos),
            "_nota": ("Cada día, lo previsto en el plan de visitas (D12, informe 184) contra las "
                      "visitas reales, por delegación y por ruta, contando por punto de venta. "
                      "visitas: [estado (HECHA, PENDIENTE, FUERA DE RUTA), pdv, matrícula, "
                      "delegación, ruta(s), nº centro, centro, ubicación, hora, reponedor, "
                      "pasaje vacío (1, 0 o null)]. vacio: visitas sin ninguna línea de "
                      "reposición; null si no llegaron las líneas. control_festivos compara "
                      "cada festivo y cada día laborable flojo con el día normal de su delegación."),
        }

    def detalle_furgonetas(self, perfil_id, anterior=None, maestro=None, ambito=None,
                           historia=None, rutas=None, empleados=None):
        """El fichero de la pagina de furgonetas (docs/58).

        Gabriele, 19-oct-2026: el listado de todas las furgonetas activas, si
        hay alguna sin visitas y desde cuantos dias, y los km de cada dia.

        · flota: las furgonetas activas del maestro de vehiculos (M12), una
          por matricula aunque VenCloud tenga dos fichas. Un perfil acotado ve
          las de sus delegaciones y las que visitaron su ambito.
        · visitas: los dias con alguna visita real de cada una, de reposicion
          o de la SAT, DIAS_VISITAS hacia atras. La pagina saca de aqui la ultima visita de cualquier dia.
        · km: cada dia, los de cada furgoneta que hizo jornada (km_del_dia).
          Un dia sin entrada no se leyo; una furgoneta sin entrada ese dia no
          abrio jornada.

        19-oct, segunda vuelta: por area, el % de furgonetas bien, y en la
        tabla el modelo, los km acumulados desde KM_DESDE y la persona de la
        ruta. `historia` son las jornadas de todos los dias desde KM_DESDE
        ({fecha: {vehiculoid: [[km ini, km fin, cerrada, empleado]]}}); `rutas`
        y `empleados`, los maestros (M3 y M11).

        Acumula como el informe: lo de esta noche sobre lo que ya habia.
        """
        ant = anterior or {}
        ambito = ambito or {}
        publicados = [f for f, d in self.dias.items() if d is not None]
        if ant.get("ultimo_dia"):
            publicados.append(ant["ultimo_dia"])
        ultimo = max(publicados) if publicados else None
        if ultimo is None:
            return {"generado": datetime.datetime.utcnow().isoformat() + "Z", "perfil": perfil_id,
                    "ultimo_dia": None, "dias": [], "sin_dato": "Todavía no hay ningún día calculado."}
        u = datetime.date.fromisoformat(ultimo)
        limite = (u - datetime.timedelta(days=DIAS_VISITAS - 1)).isoformat()
        desdes = [x for x in (ant.get("desde"), self.desde) if x]
        # Sin saber que se leyo, lo unico seguro son los dias publicados.
        desde = max(min(desdes) if desdes else min(publicados), limite)

        visitas = {}
        for m, fs in (ant.get("visitas") or {}).items():
            visitas[m] = set(fs)
        for m, fs in self.visitas_de.items():
            visitas.setdefault(m, set()).update(fs)

        sin_dato = None
        flota = {}           # matricula -> {"n": nombres, "d": delegaciones}
        mat_de = {}          # id de ficha -> matricula, tambien las de baja
        if maestro is None:
            sin_dato = SIN_VEHICULOS
        else:
            for x in maestro:
                mat = str(R.v(x, "matricula", "") or "").strip()
                if not mat:
                    continue
                mat_de[str(R.v(x, "id", ""))] = mat
                if es_furgoneta(x):
                    g = flota.setdefault(mat, {"n": set(), "d": set(), "mod": set()})
                    for k, campo in (("n", "denominacion"), ("d", "delegacion"), ("mod", "modelo")):
                        valor = str(R.v(x, campo, "") or "").strip()
                        if valor:
                            g[k].add(valor)
            if any(ambito.get(k) for k in ("clientes", "centros", "delegaciones")):
                delegs = {str(d) for d in ambito.get("delegaciones") or []}
                flota = {m: g for m, g in flota.items() if g["d"] & delegs or m in visitas}

        km = {}
        for f, por in (ant.get("km") or {}).items():
            km[f] = dict(por)
        for f, por in self.jornadas.items():
            junto = {}
            for vid, js in por.items():
                mat = mat_de.get(vid)
                if mat in flota:
                    junto.setdefault(mat, []).extend(js)
            km[f] = {m: km_del_dia(js) for m, js in sorted(junto.items())}

        dias = [(u - datetime.timedelta(days=i)).isoformat() for i in range(DIAS_GUARDADOS)]
        dias = sorted(f for f in dias if f >= desde or f in km)
        if sin_dato is None:
            visitas = {m: fs for m, fs in visitas.items() if m in flota}
            km = {f: {m: x for m, x in por.items() if m in flota} for f, por in km.items()}
        junta = lambda xs: " · ".join(sorted(xs, key=lambda x: x.lower()))
        acum = km_acumulados(historia, mat_de, flota, ultimo) if historia is not None else {}
        de_ruta = {}
        for r in rutas or []:
            veh = str(R.v(r, "vehiculo", "") or "").strip()
            if veh in flota and R.v(r, "activa", False):
                x = de_ruta.setdefault(veh, {"p": set(), "r": set()})
                for k, campo in (("p", "reponedor_titular"), ("r", "ruta")):
                    valor = str(R.v(r, campo, "") or "").strip()
                    if valor:
                        x[k].add(valor)
        nombre_de = {str(R.v(e, "id", "")): str(R.v(e, "empleado", "") or "").strip()
                     for e in empleados or []}

        def fila(m, g):
            delegs = sorted(g["d"])
            x = {"m": m, "n": junta(g["n"]), "d": junta(g["d"]),
                 "z": zona_de(delegs[0]) if delegs else OTRA_ZONA,
                 "mod": junta(g["mod"]), "p": "", "pr": "", "r": "", "km": None, "skm": None}
            if de_ruta.get(m, {}).get("p"):
                x.update(p=junta(de_ruta[m]["p"]), pr="ruta", r=junta(de_ruta[m]["r"]))
            elif m in acum and nombre_de.get(str(acum[m][2])):
                # Sin ruta activa con esta furgoneta (los tecnicos): quien la
                # llevo en su ultima jornada, y se dice que es eso.
                x.update(p=nombre_de[str(acum[m][2])], pr="jornada")
            if historia is not None:
                x["km"], x["skm"] = acum.get(m, [0, 0])[:2]
            return x

        out = {
            "generado": datetime.datetime.utcnow().isoformat() + "Z",
            "perfil": perfil_id,
            "ultimo_dia": ultimo,
            "dias": dias,
            "desde": desde,
            "umbrales_km": {"min": KM_MIN, "max": KM_MAX},
            "flota": sorted((fila(m, g) for m, g in flota.items()), key=lambda x: (x["d"], x["m"])),
            "km_desde": KM_DESDE if historia is not None else None,
            "semana": SEMANA,
            "umbrales": {"verde": VERDE, "amarillo": AMARILLO},
            "visitas": {m: sorted(f for f in fs if limite <= f <= ultimo)
                        for m, fs in sorted(visitas.items())},
            "km": {f: km[f] for f in sorted(km) if f in dias},
            "_nota": ("flota: las furgonetas activas del maestro de vehículos (M12, informe 191), "
                      "{m: matrícula, n: nombre(s) en VenCloud, d: delegación(es), z: área, "
                      "mod: modelo, p: persona, pr: de dónde sale la persona («ruta»: reponedor "
                      "titular de una ruta activa con esta furgoneta; «jornada»: quien la llevó "
                      "en su última jornada), r: ruta(s), km: km acumulados desde km_desde hasta "
                      "ultimo_dia, skm: jornadas sin km en ese tiempo}, sin las fichas "
                      "ficticias ni las de baja. visitas: por matrícula, los días con alguna "
                      "visita real en los partes o de la SAT (informe 163); lo de antes de «desde» no se sabe. km: por día "
                      "y matrícula, [km, jornadas, lo que falta] del control de jornada (D5, "
                      "informe 161); km null si ninguna jornada trae el cuentakilómetros bien "
                      "(«sin cerrar», «sin anotar», «mal anotado»). Una furgoneta sin entrada "
                      "un día no abrió jornada; un día sin entrada no se leyó."),
        }
        if sin_dato:
            out["sin_dato"] = sin_dato
        return out

    def fichero(self, perfil_id, anterior=None, meses=None):
        """El fichero del perfil: los dias de esta noche sobre los que ya habia.

        Un dia recalculado sustituye al que hubiera; los demas se quedan, hasta
        DIAS_HISTORIA. Asi la historia se acumula sin releerla, como la serie.
        Un relleno historico escribe sus dias y deja la foto de la ultima noche.
        `meses` son los ficheros por centro que se escriben con este
        (centros_por_mes): el fichero dice que meses hay y lleva la ficha de
        cada centro.
        """
        # Aqui y no arriba: incidencias importa este modulo.
        import incidencias as IN
        anterior = anterior or {}
        dias = dict(anterior.get("dias") or {})
        for f, d in self.dias.items():
            if d is not None:
                dias[f] = self.cuadrados_del_dia(d)
        for f, x in self.cerrados.items():
            x = self._con_averias(f, x)
            # Un dia que ya escribio la noche sabe mas que el relleno: la
            # telemetria con el censo de entonces y las averias con el estado de
            # M13 (docs/56). Esas dos se quedan como estaban.
            antes = dias.get(f) or {}
            for c in NO_PISA_EL_RELLENO:
                if antes.get(c):
                    x[c] = antes[c]
                    por = dict(x.get("por_delegacion") or {})
                    por.pop(c, None)
                    if (antes.get("por_delegacion") or {}).get(c):
                        por[c] = antes["por_delegacion"][c]
                    x["por_delegacion"] = por
            dias[f] = x
        dias = dict(sorted(dias.items())[-DIAS_HISTORIA:])
        delegaciones = set()
        for x in dias.values():
            for por in (x.get("por_delegacion") or {}).values():
                delegaciones.update(por)
        delegaciones.update((self.foto.get("pdvs") or {}).get("por_delegacion") or {})
        delegaciones.discard(SIN_DELEGACION)
        historico = self.historico and anterior
        return {
            "generado": (anterior.get("generado") if historico else None)
            or datetime.datetime.utcnow().isoformat() + "Z",
            "perfil": perfil_id,
            "ultimo_dia": max(dias) if dias else None,
            "primer_dia": min(dias) if dias else None,
            "umbrales": {"verde": VERDE, "amarillo": AMARILLO},
            "dias": dias,
            # El area de cada delegacion, para el filtro (Gabriele, 19-oct). Las
            # cinco del Power BI, las mismas que incidencias y devoluciones.
            "zonas": {dl: IN.zona_de(dl) for dl in sorted(delegaciones)},
            "foto": (anterior.get("foto") or {}) if historico else self.foto,
            # El filtro de cliente y centro (docs/72): la ficha de cada centro y
            # los meses que tienen su reparto, en operativo/centros-AAAA-MM.
            "centros": (self.fichas_de_centros(meses, anterior) if meses is not None
                        else anterior.get("centros") or {}),
            "meses_centros": sorted(set(anterior.get("meses_centros") or []) | set(meses or {})),
            "_nota": ("Un día por fecha, con la cifra de ese día tal cual. Lo que no tiene dato "
                      "lleva sin_dato y el motivo. Puntos de venta, telemetría auditable y "
                      "almacenes son la foto de la noche en que se escribió. por_delegacion "
                      "reparte cada cuadrado por delegación con cifras que se suman (la clave "
                      "vacía es lo que no tiene delegación); zonas da el área de cada una. "
                      "centros da nombre (n), cliente (c) y delegación (d) de cada centro; el "
                      "reparto por centro de cada día está en un fichero por mes (meses_centros)."),
        }


# ----------------------------------------------------------------------
# los almacenes
# ----------------------------------------------------------------------
def almacenes(balance_por_periodo, rutas, ambito):
    """El valor del producto en los almacenes, del ULTIMO cierre mensual.

    `balance_por_periodo`: {(anho, mes): [filas del balance]}, sin filtrar por
    ambito —las filas de almacen no traen centro—. `rutas`: filas {almacen,
    delegacion}, las de almacenes.delegacion_de_almacenes (maestro de almacenes y,
    para lo que no este, maestro de rutas).

    No hay un valor «de hoy»: VenCloud da un cierre al mes (C9) y sumar los
    movimientos encima no cuadra con el cierre siguiente (comprobado el
    13-oct-2026: agosto + movimientos de septiembre daba 861.069 EUR contra un
    cierre de 502.430). Se ensena el cierre con su mes delante.

    Un almacen es de una delegacion, no de un cliente: un perfil acotado por
    clientes o centros no tiene almacenes suyos, y se dice.
    """
    deleg_de = {}
    for r in rutas or []:
        a = str(R.v(r, "almacen", "") or "").strip()
        if a and R.v(r, "delegacion", ""):
            deleg_de.setdefault(a, str(R.v(r, "delegacion")))
    delegaciones = [str(d) for d in (ambito or {}).get("delegaciones") or []]
    acotado = bool((ambito or {}).get("clientes") or (ambito or {}).get("centros"))
    if acotado and not delegaciones:
        return {"sin_dato": "Los almacenes son de una delegación: este perfil está acotado "
                            "por clientes o centros y no tiene almacenes propios."}

    periodos = sorted(p for p, filas in (balance_por_periodo or {}).items()
                      if any(R.v(b, "tipo_elemento") == "A" for b in filas))
    if not periodos:
        return {"sin_dato": "No hay ningún cierre de inventario de almacén en la ventana."}
    anho, mes = periodos[-1]
    lista = []
    for b in balance_por_periodo[(anho, mes)]:
        if R.v(b, "tipo_elemento") != "A":
            continue
        nombre = str(R.v(b, "almacen", "") or "").strip()
        deleg = deleg_de.get(nombre, "")
        if delegaciones and deleg not in delegaciones:
            continue
        lista.append({"almacen": nombre[:60], "delegacion": deleg,
                      "valor": round(float(R.v(b, "valor_total", 0) or 0), 2)})
    if not lista:
        return {"sin_dato": "Ningún almacén de las delegaciones de este perfil tiene cierre."}
    lista.sort(key=lambda x: -x["valor"])
    return {"valor": round(sum(x["valor"] for x in lista), 2),
            "periodo": f"{anho}-{int(mes):02d}",
            "por_almacen": lista}


# ----------------------------------------------------------------------
# la pagina de rutas (docs/55)
# ----------------------------------------------------------------------
# Un festivo «tiene muchas menos visitas» (Gabriele, 13-oct) si no llega a esta
# fraccion de un dia normal de su delegacion. Y un dia laborable que no llega,
# sin festivo apuntado, es un festivo local que falta o un dia que fallo.
FESTIVO_BAJO = 0.5
# Con menos dias laborables que estos no se sabe como es un dia normal.
MIN_DIAS_NORMALES = 3


# Los tres estados de una visita, como el informe 69 de VenCloud y el Power BI
# «Control operativo Visitas Pendientes» que se usaba antes de esta pagina.
HECHA, PENDIENTE, FUERA = "HECHA", "PENDIENTE", "FUERA DE RUTA"
SIN_LINEAS = ("No ha llegado ninguna línea de reposición de ese día (A2): sin ellas no se "
              "sabe qué visita fue un pasaje vacío.")


def pasajes_vacios(d):
    """Los puntos de venta visitados ese dia en los que NINGUN parte de persona
    tiene una sola linea de reposicion: «fue y no hizo nada» (docs/04, informe 69).

    None si ese dia no llego ninguna linea: con visitas y sin lineas lo que
    falta es el informe, no el trabajo, y no se marca a todos como vacios.
    """
    if d.visitados and not d.partes_con_lineas:
        return None
    con_algo = {pdv for pid, pdv in d.partes_pdv.items() if pid in d.partes_con_lineas}
    # Un punto de venta cuyo parte no trae id no se puede cruzar: no se marca.
    con_id = set(d.partes_pdv.values())
    return {pdv for pdv in d.visitados if pdv in con_id and pdv not in con_algo}


def rutas_del_dia(d, ubicaciones=None):
    """Lo de un dia: total, delegaciones, rutas y la lista maquina a maquina.

    La lista `visitas` lleva una fila por punto de venta y estado, como el
    informe 69: [estado, pdv, matricula, delegacion, ruta(s), nº centro, centro,
    ubicacion, hora, reponedor, pasaje_vacio]. pasaje_vacio es 1, 0 o None (no
    se sabe); en una PENDIENTE no aplica y va None.
    """
    ubicaciones = ubicaciones or {}
    out = {"visitas_deleg": dict(sorted(d.visitas_deleg.items()))}
    if d.plan is None or not d.plan:
        out["sin_dato"] = (SIN_PLAN if d.plan is None
                           else "El plan de ese día no tiene ninguna visita prevista.")
        out["total"] = {"visitas": d.visitas}
        return out
    hechas = d.plan & d.visitados
    fuera = d.visitados - d.plan
    vacios = pasajes_vacios(d)

    def es_vacio(pdv):
        return None if vacios is None else int(pdv in vacios)

    deleg, rutas = {}, {}

    def fila_deleg(nombre):
        return deleg.setdefault(nombre, {"delegacion": nombre, "previstas": 0, "hechas": 0,
                                         "fuera": 0, "vacio": 0,
                                         "visitas": d.visitas_deleg.get(nombre, 0)})

    def fila_ruta(dl, ruta):
        return rutas.setdefault((dl, ruta), {"delegacion": dl, "ruta": ruta or "Sin ruta",
                                             "previstas": 0, "hechas": 0, "fuera": 0, "vacio": 0})

    lista = []
    for pdv in sorted(d.plan):
        x = d.plan_de.get(pdv, {"d": "", "r": [], "n": "", "c": "", "m": ""})
        hecho = pdv in hechas
        vacio = es_vacio(pdv) if hecho else None
        g = fila_deleg(x["d"])
        g["previstas"] += 1
        g["hechas"] += hecho
        g["vacio"] += bool(vacio)
        # Un punto de venta en dos rutas cuenta en las dos rutas, y una sola
        # vez en su delegacion y en el total.
        for r in x["r"] or [""]:
            fr = fila_ruta(x["d"], r)
            fr["previstas"] += 1
            fr["hechas"] += hecho
            fr["vacio"] += bool(vacio)
        v = d.visita_de.get(pdv, {}) if hecho else {}
        # La ruta es la del plan; el reponedor, el que fue, que puede ser de
        # otra ruta (docs/04, informe 69).
        mat = x.get("m") or v.get("m", "")
        lista.append([HECHA if hecho else PENDIENTE, pdv, mat, x["d"], " / ".join(x["r"]),
                      x["n"], x["c"], ubicaciones.get(mat, ""), v.get("h", ""), v.get("e", ""), vacio])
    for pdv in sorted(fuera):
        x = d.visita_de.get(pdv, {"d": "", "r": "", "e": "", "n": "", "c": "", "m": "", "h": ""})
        vacio = es_vacio(pdv)
        g = fila_deleg(x["d"])
        g["fuera"] += 1
        g["vacio"] += bool(vacio)
        fr = fila_ruta(x["d"], x["r"])
        fr["fuera"] += 1
        fr["vacio"] += bool(vacio)
        lista.append([FUERA, pdv, x.get("m", ""), x["d"], x["r"], x["n"], x["c"],
                      ubicaciones.get(x.get("m", ""), ""), x.get("h", ""), x["e"], vacio])
    for nombre, n in d.visitas_deleg.items():
        fila_deleg(nombre)

    def con_pct(f):
        p = porcentaje(f["hechas"], f["previstas"])
        f = dict(f, pct=p, color=semaforo(p))
        if vacios is None:
            f["vacio"] = None
        return f

    pct = porcentaje(len(hechas), len(d.plan))
    orden = {PENDIENTE: 0, HECHA: 1, FUERA: 2}
    out.update({
        "total": {"previstas": len(d.plan), "hechas": len(hechas), "pct": pct,
                  "color": semaforo(pct), "fuera": len(fuera), "visitas": d.visitas,
                  "vacio": None if vacios is None else len(vacios & d.visitados)},
        "delegaciones": sorted((con_pct(f) for f in deleg.values()),
                               key=lambda f: (f["pct"] is None, f["pct"] or 0, f["delegacion"])),
        "rutas": sorted((con_pct(f) for f in rutas.values()),
                        key=lambda f: (f["delegacion"], f["pct"] is None, f["pct"] or 0, f["ruta"])),
        "visitas": sorted(lista, key=lambda x: (orden[x[0]], x[3], x[4], x[6], x[1])),
    })
    if vacios is None:
        out["sin_vacio"] = SIN_LINEAS
    return out


def _de_la_delegacion(festivos, delegacion):
    """Locales y autonomicos de una delegacion. La lista sola es el formato de
    antes, cuando solo habia locales."""
    d = (festivos.get("delegaciones") or {}).get(delegacion)
    if isinstance(d, dict):
        auto = (festivos.get("autonomicos") or {}).get(d.get("comunidad")) or []
        return list(d.get("locales") or []), list(auto), d
    return list(d or []), [], {}


def es_festivo(fecha, delegacion, festivos):
    """'nacional', 'autonómico', 'local' o None, segun config/festivos.json."""
    if not festivos:
        return None
    if fecha in (festivos.get("nacional") or []):
        return "nacional"
    locales, auto, _ = _de_la_delegacion(festivos, delegacion)
    if fecha in auto:
        return "autonómico"
    if fecha in locales:
        return "local"
    return None


def resumen_festivos(festivos):
    """Lo que la pagina dice del calendario: que hay apuntado y que no."""
    if not festivos:
        return None
    deleg = {}
    for k in (festivos.get("delegaciones") or {}):
        locales, auto, d = _de_la_delegacion(festivos, k)
        if locales or auto:
            deleg[k] = {"ciudad": d.get("ciudad"), "comunidad": d.get("comunidad"),
                        "autonomico": sorted(auto), "local": sorted(locales)}
    return {"nacional": sorted(festivos.get("nacional") or []), "delegaciones": deleg,
            "nota": festivos.get("nota", "")}


def _mediana(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return None
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def control_festivos(dias, festivos):
    """Delegacion por delegacion, que los festivos tengan muchas menos visitas.

    El dia normal de una delegacion es la mediana de sus visitas en los dias
    laborables (lunes a viernes) que no son festivo. Contra el se mira:

      · un festivo apuntado con visitas de dia normal -> «festivo_con_visitas»;
      · un festivo con el plan entero, sin descontar -> plan_sin_descontar;
      · un laborable sin festivo apuntado y con menos de la mitad de visitas ->
        «pocas_sin_festivo»: un festivo local que falta en el calendario, o un
        dia que fallo. No se decide cual: se ensena.

    Sin calendario solo se puede ver lo tercero, y se dice.
    """
    por_deleg = {}
    for f, v in sorted(dias.items()):
        dsem = datetime.date.fromisoformat(f).weekday()
        prev = {x["delegacion"]: x["previstas"] for x in v.get("delegaciones") or []}
        for dl, n in (v.get("visitas_deleg") or {}).items():
            por_deleg.setdefault(dl, []).append((f, dsem, n, prev.get(dl)))
        for dl in prev:
            if dl not in (v.get("visitas_deleg") or {}):
                por_deleg.setdefault(dl, []).append((f, dsem, 0, prev[dl]))
    salida = []
    for dl, filas in sorted(por_deleg.items()):
        normales = [(n, p) for f, dsem, n, p in filas
                    if dsem < 5 and not es_festivo(f, dl, festivos)]
        normal = _mediana([n for n, p in normales]) if len(normales) >= MIN_DIAS_NORMALES else None
        normal_p = _mediana([p for n, p in normales if p]) if len(normales) >= MIN_DIAS_NORMALES else None
        for f, dsem, n, p in filas:
            fest = es_festivo(f, dl, festivos)
            if not fest and (dsem >= 5 or not normal or n >= FESTIVO_BAJO * normal):
                continue
            if fest:
                # Una delegacion que un dia normal no visita nada no dice nada
                # de sus festivos.
                estado = ("sin_normal" if not normal
                          else "bien" if n < FESTIVO_BAJO * normal else "festivo_con_visitas")
            else:
                estado = "pocas_sin_festivo"
            salida.append({
                "fecha": f, "delegacion": dl, "festivo": fest, "estado": estado,
                "visitas": n, "normal": normal, "previstas": p, "normal_previstas": normal_p,
                "plan_sin_descontar": bool(fest and p and normal_p and p >= FESTIVO_BAJO * normal_p)})
    return salida
