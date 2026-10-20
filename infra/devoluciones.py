"""
Las devoluciones de dinero: el cuadrado del informe general y su pagina (docs/57).

Lo pidio Gabriele el 16 de octubre de 2026, al sacarlas del estudio de
incidencias: un cuadrado propio con el total de devoluciones del mes y una
pagina con tablas y graficos solo de ellas.

Salen de la misma foto de cada noche que las incidencias, el M13 ·
EXT_SAT_INCIDENCIAS (docs/17): una devolucion es una tarea de la SAT con una
operacion de devolucion (D01, D03, D04, C24, DEV01...). Sin M13 no hay nada que
contar con garantias y se dice: D7 solo trae la ventana de tres dias.

LO QUE NO VIAJA. Ni el titulo ni las notas: en las devoluciones por
transferencia el cliente escribe ahi su IBAN, su nombre o su telefono.

EL IMPORTE (Gabriele, 20-oct-2026: «en el cuadrante tiene que salir el total de
dinero que se ha devuelto»). VenCloud no tiene un campo para el, pero el
formulario de reclamaciones escribe el titulo siempre igual: «Devolución = 1,40 €
PRODUCTO NO ENTREGADO ... TICKET: ...», y los tecnicos a mano «DEV. 0,50». De ahi
se lee la cifra y nada mas (`importe_de`); el titulo sigue sin viajar. Lo que no
es una cifra limpia («OTRO», «Cinco euros», «5+5», «O,40») se queda sin importe y
se dice cuantas son: no se adivina. Lo escrito por encima de IMPORTE_MAX tampoco
se suma: «85 €» o «90 €» en una maquina de vending son casi siempre centimos,
pero eso no se puede saber, asi que viaja aparte (`g`) para que se vea.

DOS ORIGENES. Gabriele (16-oct-2026): «las devoluciones en VenCloud las puedes
encontrar en solicitudes especiales». Estan en la serie E (categoria
«Devolución dinero», DEV01...) y tambien en la serie A de atencion al cliente
(D01, D03, C24, D04). Se guardan las dos con su origen (`e`: 1 si es solicitud
especial), y la pagina deja separarlas: en 107 de 356 especiales desde
septiembre hay una de atencion al cliente en la misma maquina y el mismo dia.

LA MATRICULA FICTICIA (00SE0000) se queda fuera, como en el resto de la
plataforma: son un tercio de las devoluciones y todas cuelgan de «CENTRO TEST»
en la central, sin maquina ni sitio.

EL AMBITO SE APLICA AL ESCRIBIR: las filas que llegan ya son las del perfil.

Sin dependencias: se prueba con `python3 infra/test_devoluciones.py`.
"""

import datetime
import re

import incidencias as IN
import reglas as R

# Los canales de devolucion, en el orden de la pagina. Se reconocen por un trozo
# del nombre de la operacion, sin acentos: el catalogo tiene dos codigos para la
# misma cosa (D01 y DEV01 son las dos «in situ»; D03 y DEV06, transferencia).
CANALES = (
    ("IN SITU", "En el sitio"),
    ("TRANSFER", "Transferencia"),
    ("TRASFER", "Transferencia"),
    ("TARJETA DE CREDITO", "Tarjeta de crédito"),
    ("TARJETA EMPLEADO", "Tarjeta de empleado"),
)
OTRO_CANAL = "Otra"
# El origen de cada devolucion: `e` es la posicion en esta lista.
ORIGENES = ("Atención al cliente", "Solicitud especial")
ORDEN_CANALES = ("En el sitio", "Transferencia", "Tarjeta de crédito", "Tarjeta de empleado", OTRO_CANAL)

# Lo que se guarda: trece meses enteros, para comparar un mes con el del ano
# anterior. Las que siguen sin cerrar van todas, sean de cuando sean.
MESES = 13

SIN_M13 = ("Falta el informe M13 · EXT_SAT_INCIDENCIAS de VenCloud (docs/17). Sin él no se "
           "pueden contar las devoluciones del mes: la carga diaria solo trae los tres "
           "últimos días de cada tarea.")


# Lo que se suma, en euros. Por encima, la cifra se ensena pero no se suma.
IMPORTE_MAX = 50.0

# «Devolución = 1,40 € ...» (el formulario) y «DEV. 0,50» (a mano). Delante
# puede ir una fecha («23.09 Devolución = ...»).
_CABEZA = re.compile(r"^\s*(?:[\d.]+\s+)?(?:(DEVOLUCI\w*N\s*=)|DEV[.,]?(?=\s*[\d.,'’]))\s*", re.I)
# La cifra, con coma, punto o apostrofo para los decimales, y su unidad.
_CIFRA = (r"(\d{0,4}(?:[.,'’]\d{1,2})?)\s*"
          r"(€|EUROS?|UEROS?|EUR|E|C(?:[EÉÈ]?NT[A-ZÀ-ÿ]*|TS?|TM|M))?\.?")
# En el formulario lo que escribe el usuario va entre el «=» y el «€» que pone
# el formulario: si hay algo mas («5+5 (17/11)», «2 cafes»), no es una cifra
# limpia. A mano, detras va un espacio o el final.
_FORMULARIO = re.compile(_CIFRA + r"[.,]?\s*€", re.I)
_A_MANO = re.compile(_CIFRA + r"\s*(?:€|\s|$)", re.I)


def importe_de(titulo):
    """Los euros que dice el titulo de una devolucion, o None si no lo dice
    con una cifra limpia. «50 cnt» son 0,50; «3€ €», 3."""
    texto = str(titulo or "")
    m = _CABEZA.match(texto)
    if not m:
        return None
    c = (_FORMULARIO if m.group(1) else _A_MANO).match(texto[m.end():])
    if not c or not re.search(r"\d", c.group(1)):
        return None
    try:
        v = float(c.group(1).replace(",", ".").replace("'", ".").replace("’", "."))
    except ValueError:
        return None
    unidad = (c.group(2) or "").upper()
    if unidad.startswith("C"):
        if not c.group(1).isdigit():
            return None
        v = v / 100
    return round(v, 2)


def canal_de(operacion):
    op = IN.sin_acentos(operacion)
    for trozo, canal in CANALES:
        if trozo in op:
            return canal
    return OTRO_CANAL


def es_devolucion(tarea):
    return bool(IN.marcas(tarea, "") & IN.DEVOLUCION)


def _primero_de_mes(dia, atras=0):
    m = dia.year * 12 + dia.month - 1 - atras
    return datetime.date(m // 12, m % 12 + 1, 1)


class Devoluciones:
    """Las devoluciones de un perfil, de la foto M13."""

    def __init__(self):
        self.foto = None

    def come_foto(self, filas):
        self.foto = (self.foto or []) + [t for t in R.tareas_de_maquina(filas) if es_devolucion(t)]

    # --------------------------------------------------------- las filas
    def _filas(self, hoy):
        desde = _primero_de_mes(hoy - datetime.timedelta(days=1), MESES - 1).isoformat()
        centros, delegs, canales, tecnicos = IN._Indice(), IN._Indice(), IN._Indice(), IN._Indice()
        for c in ORDEN_CANALES:
            canales(c)
        filas = []
        for t in self.foto or []:
            alta = IN._fecha_hora(R.v(t, "apertura", "")) or \
                (IN._fecha_hora(R.v(t, "fecha_alta", "")) or "")[:10] or None
            if not alta:
                continue
            cerrada = (int(R.v(t, "tipo_estado", -1) or -1) == IN.TIPO_ESTADO_FINALIZADA
                       or int(R.v(t, "estado", -1) or -1) == IN.ESTADO_FINALIZADA)
            if alta[:10] < desde and cerrada:
                continue
            fila = {
                "n": f"{R.v(t, 'serie', '') or ''}-{R.v(t, 'numero', '')}",
                "a": alta,
                "m": str(R.v(t, "matricula", "") or ""),
                "c": centros((str(R.v(t, "num_centro", "") or ""), str(R.v(t, "centro", "") or ""),
                              str(R.v(t, "cod_cliente", "") or ""), str(R.v(t, "cliente", "") or ""))),
                "d": delegs(str(R.v(t, "delegacion", "") or "")),
                "k": canales(canal_de(R.v(t, "operacion", ""))),
                "t": tecnicos(str(R.v(t, "tecnico_asignado", "") or "")),
            }
            if R.es_solicitud_especial(t):
                fila["e"] = 1
            imp = importe_de(R.v(t, "titulo", ""))
            if imp is not None and imp > IMPORTE_MAX:
                fila["g"] = imp
            elif imp is not None:
                fila["i"] = imp
            if cerrada:
                cierre = IN._fecha_hora(R.v(t, "cierre", "")) or \
                    (IN._fecha_hora(R.v(t, "fecha_fin", "")) or "")[:10] or None
                fila["x"] = cierre or ""
                h = IN._horas(alta, cierre)
                if h is not None:
                    fila["h"] = h
            filas.append(fila)
        filas.sort(key=lambda f: f["a"])
        return filas, centros, delegs, canales, tecnicos

    # --------------------------------------------------------- la salida
    def cuadrado(self, hoy):
        """El cuadrado: las devoluciones del mes de ayer, hasta ayer, contra los
        mismos dias del mes anterior."""
        if self.foto is None:
            return {"sin_dato": SIN_M13}
        ayer = hoy - datetime.timedelta(days=1)
        ini = _primero_de_mes(ayer)
        ini_ant = _primero_de_mes(ayer, 1)
        # El mismo dia del mes anterior; si no existe (31 de marzo), su ultimo dia.
        fin_ant = min(ini_ant + datetime.timedelta(days=ayer.day - 1), ini - datetime.timedelta(days=1))
        filas = self._filas(hoy)[0]
        del_mes = [f for f in filas if ini.isoformat() <= f["a"][:10] <= ayer.isoformat()]
        antes = [f for f in filas if ini_ant.isoformat() <= f["a"][:10] <= fin_ant.isoformat()]
        euros = lambda fs: round(sum(f.get("i", 0) for f in fs), 2)
        por_canal = {}
        for f in del_mes:
            k = ORDEN_CANALES[f["k"]]
            por_canal[k] = por_canal.get(k, 0) + 1
        return {
            "mes": ini.isoformat()[:7],
            "hasta": ayer.isoformat(),
            "total": len(del_mes),
            "mes_anterior": len(antes),
            # El dinero devuelto, de las que lo dicen en el titulo (importe_de).
            "importe": euros(del_mes),
            "importe_anterior": euros(antes),
            "sin_importe": sum(1 for f in del_mes if "i" not in f),
            "sin_cerrar": sum(1 for f in del_mes if "x" not in f),
            "especiales": sum(1 for f in del_mes if f.get("e")),
            "por_canal": [[k, por_canal[k]] for k in ORDEN_CANALES if k in por_canal],
        }

    def fichero(self, perfil_id, hoy):
        """El fichero de la pagina: una fila por devolucion, con sus catalogos."""
        ayer = (hoy - datetime.timedelta(days=1)).isoformat()
        base = {
            "generado": datetime.datetime.utcnow().isoformat() + "Z",
            "perfil": perfil_id,
            "ultimo_dia": ayer,
        }
        if self.foto is None:
            return {**base, "sin_dato": SIN_M13, "devoluciones": []}
        filas, centros, delegs, canales, tecnicos = self._filas(hoy)
        return {
            **base,
            "fuente": "M13 · EXT_SAT_INCIDENCIAS",
            "desde": _primero_de_mes(hoy - datetime.timedelta(days=1), MESES - 1).isoformat(),
            "zonas": {d: IN.zona_de(d) for d in delegs.lista},
            "centros": [list(c) for c in centros.lista],
            "delegaciones": delegs.lista,
            "canales": canales.lista,
            "origenes": list(ORIGENES),
            "tecnicos": tecnicos.lista,
            "devoluciones": filas,
            "_nota": ("Una fila por devolución de dinero de la SAT, sin la matrícula ficticia. "
                      "a = apertura; x = cierre (sin x, sin cerrar; x vacía: cerrada sin fecha); "
                      "h = horas hasta el cierre; k = canal; e = 1 si es solicitud especial (serie E); c, d, t = posición en centros, "
                      "delegaciones y técnicos. i = euros devueltos, leídos de la cifra del título; g = la cifra "
                      f"escrita cuando pasa de {IMPORTE_MAX:g} € (no se suma); sin i ni g, el título no dice una cifra "
                      "limpia. Ni título ni notas: traen datos del cliente."),
            "importe_max": IMPORTE_MAX,
        }
