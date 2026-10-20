"""
La pagina de incidencias: lo que abre el cuadrado de Incidencias (docs/56).

Lo pidio Gabriele el 16 de octubre de 2026 con un Power BI suyo («Control
operativo Incidencias 2») como modelo: un panel de control con el total, la
tasa de resolucion, el tiempo medio y el SLA de 24 horas, por zona y por
delegacion, con los diez centros con mas averias; y una
segunda hoja con las incidencias ABIERTAS en seis tarjetas (tecnicas,
reposicion, caducados, emergencia sanitaria, fuera de servicio y maquinas
criticas), una tabla y la ficha de la que se pulsa.

POR QUE HACE FALTA UN INFORME NUEVO (M13). Las tareas de la SAT (D7) y sus
eventos (D8) se bajan por la fecha de ALTA de la tarea, y la extraccion solo
vuelve a bajar los tres ultimos dias. Una tarea que se cierra al cuarto dia se
queda abierta para siempre en el crudo: con eso no se puede decir cuantas hay
abiertas ni cuanto se tarda en cerrar, solo cuantas entraron. M13 ·
EXT_SAT_INCIDENCIAS (docs/17) es la foto de cada noche: todas las tareas de
los ultimos 400 dias y todas las que siguen sin cerrar, con su estado de hoy y
la hora de apertura y de cierre sacadas del registro de eventos.

Sin M13 el fichero se escribe igual con D7 y D8 de la ventana, pero lleva
`estado_al_dia: false` y la pagina ensena solo lo que no depende del estado
(cuantas entraron, por donde y de que tipo) y dice por que falta lo demas.

EL AMBITO SE APLICA AL ESCRIBIR, como en todo lo demas: las filas que llegan
aqui ya vienen filtradas por el perfil, y el fichero es uno por perfil.

Sin dependencias: se prueba con `python3 infra/test_incidencias.py`.
"""

import datetime

import operativo as OP
import reglas as R

# Una incidencia se da por resuelta a tiempo si se cierra en menos de esto. Es
# el SLA del Power BI y el mismo umbral que el cuadrado del informe general.
HORAS_SLA = 24

# El estado de una tarea finalizada en VenCloud (`tipoestado`). En la muestra del
# 15-oct-2026 todas las de estado 99 traen tipo 9, y ninguna otra lo trae.
TIPO_ESTADO_FINALIZADA = 9
ESTADO_FINALIZADA = 99

# El texto de una incidencia solo viaja si sigue abierta: es lo que se lee en la
# ficha. Las cerradas solo cuentan, y asi el fichero no pasa de un mega.
LARGO_TEXTO = 300

# Las marcas de cada incidencia. Viajan como un numero para que el fichero sea
# pequeno; la pagina tiene la misma tabla.
TECNICA = 1          # fallo tecnico por operacion (reglas.es_fallo_tecnico)
DEVOLUCION = 2
REPOSICION = 4
CADUCADO = 8
HIGIENE = 16         # insectos, hongos, moho: «emergencia sanitaria»
BLOQUEANTE = 32      # la maquina no puede vender
ESPECIAL = 64        # serie E: solicitud especial, no averia

# Lo que el Power BI busca en las notas para caducados e higiene. Aqui se busca
# en el titulo de la tarea y en la ultima nota de sus eventos, sin acentos.
PALABRAS_CADUCADO = ("CADUC",)
PALABRAS_HIGIENE = ("INSECTO", "BICHO", "HORMIGA", "CUCARAC", "HONGOS", "MOHO")

# Las operaciones que dejan la maquina sin vender, las «bloqueantes» del Power
# BI. Alli se comparan con el nombre entero; aqui con un trozo, porque VenCloud
# les pone delante el tipo de maquina («CAFÉ - Distribuidor fuera de servicio»,
# «SNACK/BEBIDA - Distribuidor fuera de servicio»).
BLOQUEANTES = (
    "AVERIA ELECTRICA",
    "AVERIA SISTEMA DE PAGO",
    "FALTA AGUA",
    "FUERA DE SERVICIO",
    "SALTA DIFERENCI",
    "NO FUNCIONA PANTALLA",
    "NO SE PUEDE CERRAR",
    "ATASCO MONEDA",
    "AVERIA ASCENSOR",
    "PUERTA RECOGE PRODUCTO BLOQUEADA",
)

# Los codigos del catalogo que son una devolucion (reglas.OPERACIONES_NO_TECNICAS).
DEVOLUCIONES = frozenset(c for c, motivo in R.OPERACIONES_NO_TECNICAS.items()
                         if motivo == "devolucion")

# Las zonas viven en operativo: las usa tambien la pagina de furgonetas.
ZONAS, OTRA_ZONA, sin_acentos, zona_de = OP.ZONAS, OP.OTRA_ZONA, OP.sin_acentos, OP.zona_de

SIN_M13 = ("Falta el informe M13 · EXT_SAT_INCIDENCIAS de VenCloud (docs/17). Sin él, una "
           "incidencia cerrada después de su tercer día sigue abierta en los datos, así que "
           "no se pueden dar las abiertas, la tasa de resolución, el tiempo medio ni el SLA.")


def marcas(tarea, texto):
    """Las marcas de una tarea, mirando su operacion y su texto."""
    op = sin_acentos(R.v(tarea, "operacion", ""))
    codigo = str(R.v(tarea, "cod_operacion", "") or "").strip()
    tx = sin_acentos(texto)
    m = 0
    tecnica = R.es_fallo_tecnico(tarea)
    if tecnica:
        m |= TECNICA
    if codigo in DEVOLUCIONES or "DEVOLUC" in op:
        m |= DEVOLUCION
    if "REPONER" in op or codigo == "S010":
        m |= REPOSICION
    if "CADUCADO" in op or any(p in tx for p in PALABRAS_CADUCADO):
        m |= CADUCADO
    if "INSECTO" in op or any(p in tx for p in PALABRAS_HIGIENE):
        m |= HIGIENE
    if tecnica and any(b in op for b in BLOQUEANTES):
        m |= BLOQUEANTE
    if R.es_solicitud_especial(tarea):
        m |= ESPECIAL
    return m


def _fecha_hora(texto):
    """'2026-10-15 07:35:37' -> '2026-10-15 07:35'; las fechas 1900 son «sin fecha»."""
    t = str(texto or "")[:16].replace("T", " ")
    return t if R.fecha_valida(t[:10]) and not t.startswith("1900") else None


def _horas(desde, hasta):
    if not desde or not hasta or len(desde) < 16 or len(hasta) < 16:
        return None
    h = (datetime.datetime.fromisoformat(hasta)
         - datetime.datetime.fromisoformat(desde)).total_seconds() / 3600
    return round(h, 1) if h >= 0 else None


class _Indice:
    """Una lista de valores sin repetir, para que cada fila lleve un numero."""

    def __init__(self):
        self.lista, self._pos = [], {}

    def __call__(self, valor):
        if valor not in self._pos:
            self._pos[valor] = len(self.lista)
            self.lista.append(valor)
        return self._pos[valor]


# ----------------------------------------------------------------------
# un perfil
# ----------------------------------------------------------------------
class Incidencias:
    """Las incidencias de un perfil.

    `come_foto` recibe el M13; `come_tareas` y `come_eventos`, el D7 y el D8 de
    la ventana. Si llega la foto, manda la foto: es el estado de hoy.
    """

    def __init__(self):
        self.foto = None
        self.tareas = {}
        self.apertura = {}

    # --------------------------------------------------------- las fuentes
    def come_foto(self, filas):
        self.foto = (self.foto or []) + list(R.tareas_de_maquina(filas))

    def come_tareas(self, filas):
        for t in R.tareas_de_maquina(filas):
            ident = R.v(t, "id", None)
            if ident is not None:
                self.tareas[ident] = t

    def come_eventos(self, filas):
        for e in filas:
            ident = R.v(e, "averia_id", None)
            cuando = _fecha_hora(R.v(e, "fecha", ""))
            if ident is None or not cuando:
                continue
            if ident not in self.apertura or cuando < self.apertura[ident]:
                self.apertura[ident] = cuando

    def eventos_de_la_foto(self):
        """La apertura y el cierre de la foto como eventos del D8, para que el
        cuadrado de Incidencias del informe general tambien vea los cierres que
        llegan despues del tercer dia (Operativo.come_sat_eventos)."""
        out = []
        for t in self.foto or []:
            ident = R.v(t, "id", None)
            ab, ci = _fecha_hora(R.v(t, "apertura", "")), _fecha_hora(R.v(t, "cierre", ""))
            if ident is None:
                continue
            if ab:
                out.append({"averia_id": ident, "fecha": ab + ":00", "estado": 0})
            if ci:
                out.append({"averia_id": ident, "fecha": ci + ":00", "estado": ESTADO_FINALIZADA})
        return out

    # --------------------------------------------------------- la salida
    def fichero(self, perfil_id, hoy):
        """El fichero del perfil: una fila por incidencia, con sus catalogos."""
        al_dia = self.foto is not None
        centros, delegs, ops, tecnicos = _Indice(), _Indice(), _Indice(), _Indice()
        filas = []
        fuente = self.foto if al_dia else list(self.tareas.values())
        for t in fuente:
            if R.es_operacion_preventiva(R.v(t, "operacion", "")):
                # Un preventivo es mantenimiento planificado, no una incidencia
                # (docs/50): ni se cuenta ni se lista.
                continue
            ident = R.v(t, "id", None)
            alta = (_fecha_hora(R.v(t, "apertura", "")) if al_dia else self.apertura.get(ident)) \
                or (_fecha_hora(R.v(t, "fecha_alta", "")) or "")[:10] or None
            if not alta:
                continue
            texto = " · ".join(x for x in (str(R.v(t, "titulo", "") or "").strip(),
                                           str(R.v(t, "ultima_nota", "") or "").strip()) if x)
            fila = {
                "n": f"{R.v(t, 'serie', '') or ''}-{R.v(t, 'numero', '')}",
                "a": alta,
                "m": str(R.v(t, "matricula", "") or ""),
                "c": centros((str(R.v(t, "num_centro", "") or ""), str(R.v(t, "centro", "") or ""),
                              str(R.v(t, "cod_cliente", "") or ""), str(R.v(t, "cliente", "") or ""))),
                "d": delegs(str(R.v(t, "delegacion", "") or "")),
                "o": ops((str(R.v(t, "cod_operacion", "") or ""), str(R.v(t, "operacion", "") or ""),
                          str(R.v(t, "categoria", "") or ""))),
                "t": tecnicos(str(R.v(t, "tecnico_asignado", "") or "")),
                "f": marcas(t, texto),
            }
            if fila["f"] & DEVOLUCION:
                # Las devoluciones de dinero no entran en el estudio: lo pidio
                # Gabriele el 16-oct-2026. Ni se cuentan ni viajan.
                continue
            if al_dia:
                cerrada = (int(R.v(t, "tipo_estado", -1) or -1) == TIPO_ESTADO_FINALIZADA
                           or int(R.v(t, "estado", -1) or -1) == ESTADO_FINALIZADA)
                if cerrada:
                    # El cierre con hora sale del evento; si no lo hay, VenCloud
                    # solo tiene la fecha (`fechafin`) y no se puede medir.
                    cierre = _fecha_hora(R.v(t, "cierre", "")) or \
                        (_fecha_hora(R.v(t, "fecha_fin", "")) or "")[:10] or None
                    fila["x"] = cierre or ""
                    h = _horas(alta, cierre)
                    if h is not None:
                        fila["h"] = h
                else:
                    # La ficha de una abierta: lo que se lee para ir a arreglarla.
                    fila["tx"] = texto[:LARGO_TEXTO]
                    fila["u"] = str(R.v(t, "ubicacion", "") or "")[:80]
                    fila["p"] = str(R.v(t, "cod_pdv", "") or "")
            filas.append(fila)
        filas.sort(key=lambda f: f["a"])
        ayer = (hoy - datetime.timedelta(days=1)).isoformat()
        return {
            "generado": datetime.datetime.utcnow().isoformat() + "Z",
            "perfil": perfil_id,
            "estado_al_dia": al_dia,
            "sin_estado": None if al_dia else SIN_M13,
            "fuente": "M13 · EXT_SAT_INCIDENCIAS" if al_dia else "D7 · EXT_SAT_AVERIAS y D8 · EXT_SAT_EVENTOS",
            "ultimo_dia": ayer,
            "desde": filas[0]["a"][:10] if filas else None,
            "horas_sla": HORAS_SLA,
            # El semaforo del informe general, para que el SLA de la pagina y el
            # del cuadrado salgan del mismo color.
            "umbrales": {"verde": OP.VERDE, "amarillo": OP.AMARILLO},
            "marcas": {"tecnica": TECNICA, "reposicion": REPOSICION,
                       "caducado": CADUCADO, "higiene": HIGIENE, "bloqueante": BLOQUEANTE,
                       "especial": ESPECIAL},
            "zonas": {d: zona_de(d) for d in delegs.lista},
            "centros": [list(c) for c in centros.lista],
            "delegaciones": delegs.lista,
            "operaciones": [list(o) for o in ops.lista],
            "tecnicos": tecnicos.lista,
            "incidencias": filas,
            "_nota": ("Una fila por incidencia de la SAT, sin la matrícula ficticia ni los "
                      "preventivos ni las devoluciones. a = apertura; x = cierre (sin x, abierta); h = horas hasta el "
                      "cierre, solo si el cierre trae hora (x vacía: cerrada sin fecha); f = marcas; c, d, o, t = posición en "
                      "centros, delegaciones, operaciones y técnicos."),
        }
