"""
Las devoluciones de dinero: el cuadrado del informe general y su pagina (docs/57).

Lo pidio Gabriele el 16 de octubre de 2026, al sacarlas del estudio de
incidencias, y el 20 de octubre la rehizo por areas y con el dinero: «en el
cuadrante tiene que salir el total de dinero que se ha devuelto».

DE DONDE SALEN. De la pantalla «Gestión de Devoluciones» de VenCloud, la tabla
`vending.reclamaciones`, que se baja entera cada noche con el informe M16 ·
EXT_DEVOLUCIONES (informe 198, docs/17). Cada devolucion lleva su importe en un
campo, su estado (en estudio, pendiente, abonada, rechazada) y como se devolvio
(transferencia, en mano, Monyx, tarjeta prepago...).

Hasta el 20-oct-2026 se contaban las tareas de devolucion de la SAT (M13) y el
importe se leia del titulo. Gabriele: «el texto no es correcto ... no podemos
fiarnos del texto del cliente» (la A-70707 decia 50 € y la solicitud especial
E-11985 que la cerro, 0,50 €). La tabla de devoluciones es la buena.

EL DINERO DEVUELTO es la suma de las abonadas. Lo de las que estan en estudio o
pendientes se dice aparte, y lo de las rechazadas no se devolvio. Un importe por
encima de IMPORTE_MAX no se suma: el 9-oct-2026 hay una abonada de 44.504 € en
una maquina de vending. Viaja aparte (`g`) para que se vea y se corrija.

LO QUE NO VIAJA. El informe ya no trae nombre, telefono, email, NIF, cuenta,
firma ni observaciones: no hacen falta para contar y son datos del cliente.

LA MATRICULA FICTICIA (00SE0000) se queda fuera, como en el resto de la
plataforma.

EL AMBITO SE APLICA AL ESCRIBIR: las filas que llegan ya son las del perfil.

Sin dependencias: se prueba con `python3 infra/test_devoluciones.py`.
"""

import datetime

import incidencias as IN
import reglas as R

# El estado de la devolucion (`estadodevolucion`), como lo ensena VenCloud.
# 1, 3 y 4 los dice la pantalla; el 2 esta abierto, como el 1, y no se abona.
ESTADOS = {1: "En estudio", 2: "Pendiente", 3: "Abonada", 4: "Rechazada"}
SIN_ESTADO = "Sin estado"
ORDEN_ESTADOS = ("En estudio", "Pendiente", "Abonada", "Rechazada", SIN_ESTADO)
ABONADA = ORDEN_ESTADOS.index("Abonada")
RECHAZADA = ORDEN_ESTADOS.index("Rechazada")
# Las que siguen sin resolver.
ABIERTAS = frozenset((ORDEN_ESTADOS.index("En estudio"), ORDEN_ESTADOS.index("Pendiente"),
                      ORDEN_ESTADOS.index(SIN_ESTADO)))

# Lo que se suma, en euros. Por encima, la cifra se ensena pero no se suma.
IMPORTE_MAX = 50.0

# Lo que se guarda: trece meses enteros, para comparar un mes con el del ano
# anterior. Las que siguen sin resolver van todas, sean de cuando sean.
MESES = 13

SIN_M16 = ("Falta el informe M16 · EXT_DEVOLUCIONES de VenCloud (informe 198, docs/17): "
           "sin él no hay devoluciones que contar.")


def _primero_de_mes(dia, atras=0):
    m = dia.year * 12 + dia.month - 1 - atras
    return datetime.date(m // 12, m % 12 + 1, 1)


def estado_de(fila):
    try:
        return ESTADOS.get(int(R.v(fila, "estado_devolucion", 0) or 0), SIN_ESTADO)
    except (TypeError, ValueError):
        return SIN_ESTADO


def importe_de(fila):
    try:
        v = R.v(fila, "importe", None)
        return None if v in (None, "") else round(float(v), 2)
    except (TypeError, ValueError):
        return None


class Devoluciones:
    """Las devoluciones de un perfil, de la foto M16."""

    def __init__(self):
        self.foto = None

    def come_foto(self, filas):
        self.foto = (self.foto or []) + [f for f in filas
                                         if R.v(f, "matricula") != R.MATRICULA_FICTICIA]

    # --------------------------------------------------------- las filas
    def _filas(self, hoy):
        desde = _primero_de_mes(hoy - datetime.timedelta(days=1), MESES - 1).isoformat()
        centros, delegs, tipos, motivos = IN._Indice(), IN._Indice(), IN._Indice(), IN._Indice()
        filas = []
        for t in self.foto or []:
            alta = IN._fecha_hora(R.v(t, "fecha", ""))
            if not alta:
                continue
            s = ORDEN_ESTADOS.index(estado_de(t))
            if alta[:10] < desde and s not in ABIERTAS:
                continue
            fila = {
                "n": str(R.v(t, "numero", "") or ""),
                "a": alta,
                "m": str(R.v(t, "matricula", "") or ""),
                "c": centros((str(R.v(t, "num_centro", "") or ""), str(R.v(t, "centro", "") or ""),
                              str(R.v(t, "cod_cliente", "") or ""), str(R.v(t, "cliente", "") or ""))),
                "d": delegs(str(R.v(t, "delegacion", "") or "")),
                "k": tipos(str(R.v(t, "tipo_devolucion_nombre", "") or "") or "Sin tipo"),
                "o": motivos(str(R.v(t, "motivo", "") or "") or "Sin motivo"),
                "s": s,
            }
            imp = importe_de(t)
            if imp is not None and imp > IMPORTE_MAX:
                fila["g"] = imp
            elif imp is not None:
                fila["i"] = imp
            filas.append(fila)
        filas.sort(key=lambda f: f["a"])
        return filas, centros, delegs, tipos, motivos

    # --------------------------------------------------------- la salida
    def cuadrado(self, hoy):
        """El cuadrado: el dinero abonado de las devoluciones del mes de ayer,
        hasta ayer, contra los mismos dias del mes anterior."""
        if self.foto is None:
            return {"sin_dato": SIN_M16}
        ayer = hoy - datetime.timedelta(days=1)
        ini = _primero_de_mes(ayer)
        ini_ant = _primero_de_mes(ayer, 1)
        # El mismo dia del mes anterior; si no existe (31 de marzo), su ultimo dia.
        fin_ant = min(ini_ant + datetime.timedelta(days=ayer.day - 1), ini - datetime.timedelta(days=1))
        filas = self._filas(hoy)[0]
        del_mes = [f for f in filas if ini.isoformat() <= f["a"][:10] <= ayer.isoformat()]
        antes = [f for f in filas if ini_ant.isoformat() <= f["a"][:10] <= fin_ant.isoformat()]
        euros = lambda fs: round(sum(f.get("i", 0) for f in fs), 2)
        abonadas = lambda fs: [f for f in fs if f["s"] == ABONADA]
        abiertas = [f for f in del_mes if f["s"] in ABIERTAS]
        return {
            "mes": ini.isoformat()[:7],
            "hasta": ayer.isoformat(),
            "total": len(del_mes),
            "mes_anterior": len(antes),
            "importe": euros(abonadas(del_mes)),
            "importe_anterior": euros(abonadas(antes)),
            "abonadas": len(abonadas(del_mes)),
            "sin_resolver": len(abiertas),
            "importe_sin_resolver": euros(abiertas),
            "rechazadas": sum(1 for f in del_mes if f["s"] == RECHAZADA),
            "fuera_de_tope": sum(1 for f in del_mes if "g" in f),
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
            return {**base, "sin_dato": SIN_M16, "devoluciones": []}
        filas, centros, delegs, tipos, motivos = self._filas(hoy)
        return {
            **base,
            "fuente": "M16 · EXT_DEVOLUCIONES",
            "desde": _primero_de_mes(hoy - datetime.timedelta(days=1), MESES - 1).isoformat(),
            "zonas": {d: IN.zona_de(d) for d in delegs.lista},
            "centros": [list(c) for c in centros.lista],
            "delegaciones": delegs.lista,
            "tipos": tipos.lista,
            "motivos": motivos.lista,
            "estados": list(ORDEN_ESTADOS),
            "importe_max": IMPORTE_MAX,
            "devoluciones": filas,
            "_nota": ("Una fila por devolución de la Gestión de Devoluciones de VenCloud, sin la matrícula "
                      "ficticia. n = número; a = fecha; k = tipo de devolución; o = motivo; s = estado "
                      "(posición en estados); i = importe en euros; g = el importe cuando pasa de "
                      f"{IMPORTE_MAX:g} € (no se suma); c, d = posición en centros y delegaciones. "
                      "Sin datos del cliente."),
        }
