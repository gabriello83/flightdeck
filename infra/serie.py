"""
La serie diaria: una fila por dia y por perfil, pensada para SUMARSE.

POR QUE EXISTE. El panel es una foto de una ventana fija —120 dias— calculada
cada noche. Sirve para «como va el parque», y no sirve para «cuanto se vendio
ayer» ni «comparame marzo con abril»: esos numeros no estan, y no se pueden
sacar restando. Para que cualquiera pueda elegir el tiempo que mira —hoy, ayer,
este mes, el mes pasado, un intervalo cualquiera desde el 1 de enero de 2025—
hace falta el dato partido por dias, y hace falta que juntar dias sea una suma.

LA REGLA DE TODO ESTE FICHERO: una fila de la serie solo guarda cosas que se
pueden sumar. Un contador se suma. Un importe se suma. Una media NO se suma, y
una mediana menos todavia, asi que de las distribuciones —minutos de visita,
horas de cierre de una averia, kilometros, temperatura— no se guarda el
resumen: se guarda el HISTOGRAMA, que si se suma, y la mediana se saca al
final del histograma sumado. Es aproximada hasta el ancho de su tramo, y se
dice donde se ensena; la media y el total son exactos porque se guarda la suma
y el numero de valores.

LO QUE NO SE PUEDE SUMAR Y NO SE DISIMULA. «Maquinas distintas atendidas» en un
intervalo no es la suma de las de cada dia: la misma maquina se visita diez
veces al mes. Se guarda el valor de CADA DIA, y al juntar un rango se da el
maximo y la media diaria, nunca un total inventado. Quien quiera el parque
entero tiene el censo, que es otra cosa y esta en el panel.

EL DINERO VA POR PERIODO CONTABLE, NO POR DIA. `prefacrecauda` se agrupa por
anho/mes y la fecha del fichero es la de ESCRITURA (ver reglas.py). Asi que la
fila de un dia guarda un diccionario periodo -> importes: lo escrito ese dia,
de los meses a los que pertenezca. Sumar dias da los periodos completos, que es
justo como hay que leerlo.

Sin dependencias: se prueba con `python3 infra/test_serie.py`.
"""

import datetime
import json

import reglas as R

# La historia empieza aqui. Antes de esta fecha no se carga nada: es la linea
# que puso Gabriele, y tenerla escrita en un solo sitio evita que cada Lambda
# invente la suya.
PRIMER_DIA = "2025-01-01"

# Los tramos de cada histograma. Viajan en el indice de la serie para que la
# pagina no lleve una copia que se quede vieja el dia que se afinen.
#
# Son mas estrechos donde esta el dato y anchos en la cola: la mediana de los
# minutos de visita cae sobre 6-7 minutos (medido en docs/21), asi que ahi los
# tramos van de uno en uno y arriba de hora en hora. Un tramo de 0 a 10 habria
# dado una mediana aproximada inutil justo donde importa.
BORDES = {
    "minutos": [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20, 30, 45, 60, 90, 120, 180, 240, 360],
    "horas_cierre": [0, 1, 2, 4, 8, 12, 24, 48, 72, 120, 168, 336, 720],
    "km": [0, 10, 25, 50, 75, 100, 125, 150, 200, 250, 300, 400, 500],
    "temperatura": [-10, -2, 0, 2, 4, 6, 8, 10, 12, 15, 20, 25, 30],
}

# Por encima de 8 grados al arrancar es cadena de frio (ver el panel).
TEMPERATURA_LIMITE = 8.0

MOTIVOS_MERMA = ("caducidad", "rotura", "retirada")


# ----------------------------------------------------------------------
# histogramas sumables
# ----------------------------------------------------------------------
def _tramo(bordes, x):
    """En que tramo cae x. 0 es «por debajo del primer borde»."""
    i = 0
    for borde in bordes:
        if x < borde:
            return i
        i += 1
    return i


def hist_vacio(cual):
    return {"n": 0, "suma": 0.0, "h": [0] * (len(BORDES[cual]) + 1), "max": None}


def hist_de(cual, valores):
    """El histograma de unos valores, con su n, su suma y su maximo.

    La suma y el n van aparte del histograma a proposito: con ellos la media de
    cualquier rango es exacta, y es la unica cifra de una distribucion que se
    puede dar sin aproximar.
    """
    d = hist_vacio(cual)
    bordes = BORDES[cual]
    for x in valores:
        if x is None:
            continue
        try:
            x = float(x)
        except (TypeError, ValueError):
            continue
        d["n"] += 1
        d["suma"] += x
        d["h"][_tramo(bordes, x)] += 1
        d["max"] = x if d["max"] is None else max(d["max"], x)
    d["suma"] = round(d["suma"], 3)
    return d


def suma_hist(a, b):
    if not a:
        return dict(b) if b else None
    if not b:
        return dict(a)
    maximos = [x for x in (a.get("max"), b.get("max")) if x is not None]
    return {
        "n": a["n"] + b["n"],
        "suma": round(a["suma"] + b["suma"], 3),
        "h": [x + y for x, y in zip(a["h"], b["h"])],
        "max": max(maximos) if maximos else None,
    }


def resumen_hist(cual, d):
    """n, media exacta, y mediana y p90 APROXIMADAS: hasta el ancho del tramo.

    Devuelve la misma forma que `reglas.resumen_tiempos` para que la pagina no
    tenga que distinguir de donde viene el numero, mas `aprox: True`, que es lo
    que le permite decirlo.
    """
    if not d or not d.get("n"):
        return {"n": 0}
    bordes = BORDES[cual]
    return {
        "n": d["n"],
        "media": round(d["suma"] / d["n"], 2),
        "mediana": _percentil(bordes, d["h"], d["n"], 0.5, d.get("max")),
        "p90": _percentil(bordes, d["h"], d["n"], 0.9, d.get("max")),
        "max": round(float(d["max"]), 2) if d.get("max") is not None else None,
        "aprox": True,
    }


def _percentil(bordes, h, n, q, maximo=None):
    """El percentil dentro del tramo donde cae, interpolando.

    El ultimo tramo no tiene borde superior: ahi se usa el maximo observado, que
    es la unica cota real que tenemos. Sin eso, un percentil de la cola devolvia
    el borde del ultimo tramo y se quedaba corto siempre.
    """
    objetivo = q * n
    acumulado = 0
    for i, cuantos in enumerate(h):
        if not cuantos:
            continue
        if acumulado + cuantos >= objetivo:
            bajo = bordes[i - 1] if i > 0 else min(bordes[0], 0)
            alto = bordes[i] if i < len(bordes) else (maximo if maximo is not None else bordes[-1])
            if alto is None or alto <= bajo:
                return round(float(bajo), 2)
            dentro = (objetivo - acumulado) / cuantos
            return round(bajo + (alto - bajo) * dentro, 2)
        acumulado += cuantos
    return None


# ----------------------------------------------------------------------
# un dia de un perfil
# ----------------------------------------------------------------------
class Dia:
    """Lo que un perfil acumula de UN dia. Nada guarda filas.

    Los `come_*` reciben las filas de un informe de ese dia ya filtradas por el
    ambito del perfil, igual que los del Acumulador del panel, y por el mismo
    motivo: las reglas son las de `reglas.py` y no hay una segunda copia.
    """

    __slots__ = ("por_centro", "fecha", "visitas", "partes", "maquinas", "centros", "minutos",
                 "carga_valor", "carga_unidades", "carga_vendibles", "merma",
                 "periodos", "sat_tareas", "sat_averias", "sat_preventivos",
                 "sat_fallos", "sat_apertura", "sat_cierre", "jornadas",
                 "km", "temperaturas", "con_gps", "venta_unidades",
                 "venta_importe", "venta_maquinas", "venta_fuente", "venta_imposibles")

    def __init__(self, fecha, centro_de=None):
        self.fecha = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)[:10]
        # El mismo dia partido por centro, si quien lo crea sabe de que centro
        # es cada fila (ver PorCentro).
        self.por_centro = PorCentro(centro_de) if centro_de else None
        self.visitas = self.partes = 0
        self.maquinas = set()
        self.centros = set()
        self.minutos = []
        self.carga_valor = self.carga_unidades = self.carga_vendibles = 0.0
        self.merma = {m: {"lineas": 0, "unidades": 0.0, "euros": 0.0} for m in MOTIVOS_MERMA}
        self.periodos = {}
        self.sat_tareas = self.sat_averias = self.sat_preventivos = self.sat_fallos = 0
        self.sat_apertura = {}
        self.sat_cierre = {}
        self.jornadas = 0
        self.km = []
        self.temperaturas = []
        self.con_gps = 0
        self.venta_unidades = self.venta_importe = 0.0
        self.venta_maquinas = set()
        self.venta_fuente = None
        self.venta_imposibles = 0

    # ------------------------------------------------------------- servicio
    def come_partes(self, filas):
        self.partes += len(filas)
        for p in R.visitas_reales(filas):
            self.visitas += 1
            self.maquinas.add(R.v(p, "matricula"))
            self.centros.add(R.v(p, "centro"))
            m = R.v(p, "minutos", None)
            if m is not None:
                self.minutos.append(float(m))

    def come_lineas(self, filas):
        self.carga_valor += R.valor_cargado(filas)
        self.carga_unidades += R.unidades_cargadas(filas)
        self.carga_vendibles += R.unidades_cargadas(
            [l for l in filas if not R.es_consumible_de_cafe(l)])

    def come_mov_maquina(self, filas):
        for motivo, datos in R.merma(filas).items():
            acum = self.merma[motivo]
            acum["lineas"] += datos["lineas"]
            acum["unidades"] += datos["unidades"]
            acum["euros"] += datos["euros"]

    # ------------------------------------------------------------- dinero
    def come_recaudacion(self, filas):
        for anio, mes in {(int(R.v(x, "anho")), int(R.v(x, "mes"))) for x in filas}:
            r = R.recaudacion_del_periodo(filas, anio, mes)
            acum = self.periodos.setdefault(
                f"{anio}-{mes:02d}",
                {"registros": 0, "efectivo": 0.0, "banco": 0.0, "ciego": 0.0, "imposibles": 0})
            acum["registros"] += r["registros"]
            acum["efectivo"] += r["efectivo"]
            acum["banco"] += r["banco"]
            acum["ciego"] += r["efectivo_sin_telemetria"]
            acum["imposibles"] += r.get("filas_imposibles", 0)

    # ------------------------------------------------------------- SAT
    def come_sat(self, filas):
        for t in R.tareas_de_maquina(filas):
            self.sat_tareas += 1
            if R.es_preventivo(t):
                self.sat_preventivos += 1
            elif R.es_averia_tecnica(t):
                self.sat_averias += 1
            if R.es_fallo_tecnico(t) and not R.es_preventivo(t):
                self.sat_fallos += 1

    def come_sat_eventos(self, filas):
        """Apertura y cierre de una averia, para las horas que tardo en cerrarse.

        Una averia abierta un dia y cerrada otro tiene sus eventos en dos
        ficheros distintos, asi que aqui solo se apunta lo de este dia; el que
        junta los dias (`cierra_averias`) es quien puede restar.
        """
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

    # ------------------------------------------------------------- jornadas
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

    # ------------------------------------------------------------- venta
    def hay_telemetria(self):
        """Ese dia hay telemetria en el crudo, sea o no de este perfil.

        Lo marca quien lee el fichero entero, antes de filtrar por ambito. Un
        dia marcado ya no coge la venta del parte aunque al perfil no le toque
        ninguna venta de telemetria: mejor un dia a cero que un dia relleno con
        la venta parcial y fechada el dia de la lectura.
        """
        self.venta_fuente = "telemetria"

    def come_ventas_telemetria(self, filas):
        self.venta_fuente = "telemetria"
        for f in filas:
            if R.venta_imposible(1, R.v(f, "precio", 0)):
                self.venta_imposibles += 1
                continue
            self.venta_unidades += 1
            self.venta_importe += float(R.v(f, "precio", 0) or 0)
            m = R.v(f, "matricula", "")
            if m:
                self.venta_maquinas.add(m)

    def come_ventas_visita(self, filas):
        """La venta del parte. Solo si ese dia no hubo telemetria.

        Si hubiera las dos serian las mismas ventas dos veces; el handler ya no
        llama a esta cuando hay telemetria, y la comprobacion se repite aqui
        porque es la clase de cosa que se olvida al mover una llamada de sitio.
        """
        if self.venta_fuente == "telemetria":
            return
        self.venta_fuente = "visita_ventas"
        for f in filas:
            m = R.v(f, "matricula", "")
            if m == R.MATRICULA_FICTICIA:
                continue
            # Se aparta y se cuenta: ver reglas.LIMITE_PRECIO_UNIDAD.
            if R.venta_imposible(R.v(f, "num_total", 0), R.v(f, "imp_total", 0)):
                self.venta_imposibles += 1
                continue
            self.venta_unidades += float(R.v(f, "num_total", 0) or 0)
            self.venta_importe += float(R.v(f, "imp_total", 0) or 0)
            if m:
                self.venta_maquinas.add(m)

    # ------------------------------------------------------------- salida
    def horas_de_cierre(self):
        """Las horas de las averias que ABREN Y CIERRAN dentro de este dia.

        Las que cruzan de un dia a otro no se pueden medir con lo que cabe en
        una fila diaria, asi que no se cuentan aqui: el panel, que lee la
        ventana entera de una vez, si las mide. La serie da la distribucion de
        las que se resuelven el mismo dia, que es la que se puede sumar.
        """
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

    def vacio(self):
        """Un dia sin una sola fila. No se escribe: ocuparia sitio y no dice nada."""
        return not (self.partes or self.visitas or self.carga_unidades or self.periodos
                    or self.sat_tareas or self.jornadas or self.venta_unidades
                    or any(d["lineas"] for d in self.merma.values()))

    def fila(self):
        return {
            "f": self.fecha,
            "servicio": {
                "visitas": self.visitas,
                "partes": self.partes,
                # No sumable: es «distintas ESE dia». Ver la cabecera.
                "maquinas_dia": len([m for m in self.maquinas if m]),
                "centros_dia": len([c for c in self.centros if c]),
                "min": hist_de("minutos", self.minutos),
                "carga": {"valor": round(self.carga_valor, 2),
                          "unidades": round(self.carga_unidades, 2),
                          "vendibles": round(self.carga_vendibles, 2)},
                "merma": {m: {"lineas": d["lineas"],
                              "unidades": round(d["unidades"], 2),
                              "euros": round(d["euros"], 2)}
                          for m, d in self.merma.items()},
                # Interno: el coste de servicio es nuestro, no del cliente. Lo
                # recorta la API igual que en el panel.
                "coste_servicio": round(self.visitas * 8.0, 2),
            },
            "dinero": {"periodos": {k: {"registros": d["registros"],
                                        "efectivo": round(d["efectivo"], 2),
                                        "banco": round(d["banco"], 2),
                                        "ciego": round(d["ciego"], 2),
                                        "imposibles": d["imposibles"]}
                                    for k, d in sorted(self.periodos.items())}},
            "sat": {
                "tareas": self.sat_tareas,
                "averias_tecnicas": self.sat_averias,
                "preventivos": self.sat_preventivos,
                "fallos_tecnicos": self.sat_fallos,
                "cierres": hist_de("horas_cierre", self.horas_de_cierre()),
            },
            "jornadas": {
                "jornadas": self.jornadas,
                "km_total": round(sum(self.km), 2),
                "km": hist_de("km", self.km),
                "temperatura": hist_de("temperatura", self.temperaturas),
                "temperatura_fuera": sum(1 for t in self.temperaturas if t > TEMPERATURA_LIMITE),
                "gps": self.con_gps,
            },
            "venta": {
                "unidades": round(self.venta_unidades, 2),
                "importe": round(self.venta_importe, 2),
                "maquinas_dia": len(self.venta_maquinas),
                "fuente": self.venta_fuente,
                # Lecturas apartadas por precio imposible. Se dicen, no se esconden.
                "imposibles": self.venta_imposibles,
            },
        }


# ----------------------------------------------------------------------
# el mismo dia, partido por centro
# ----------------------------------------------------------------------
# POR QUE VA APARTE. El filtro por delegacion, cliente y centro necesita saber
# de que centro es cada cifra de cada dia. El CENTRO es el atomo: cliente y
# delegacion son atributos suyos —la ficha del centro, que va en el indice—, asi
# que filtrar por un cliente es sumar sus centros. Guardarlo por centro y no por
# cliente es lo que permite que la mudanza de clientes de VenCloud (docs/44) no
# rompa la historia: un centro que cambia de cliente se reagrupa con la ficha
# de hoy, sin reescribir ningun dia.
#
# Va en su propio fichero por mes (`centros-<mes>.json.gz`) y no dentro de la
# fila del dia porque para el interno son cientos de centros por dia: quien no
# filtra no tiene por que bajarselos.
#
# Lo que se guarda por centro es lo que se puede atribuir a un centro y sumar:
# visitas, carga, merma, recaudacion, tareas de SAT y venta. Las jornadas no:
# una jornada es de una ruta, que pasa por muchos centros. El cierre de las
# averias tampoco: sale de los eventos, que van por averia.

class PorCentro:
    """Las cifras de un dia, por centro. `centro_de(fila)` dice de que centro es.

    Cada centro lleva su propio `Dia`, asi que las reglas son las mismas que las
    de la fila del dia, sin una segunda copia: la suma de todos los centros da
    la fila del dia (salvo lo que no tiene centro, que no se puede filtrar).
    """

    # Lo que no se parte por centro: las jornadas son de una ruta, y el cierre
    # de una averia sale de los eventos, que van por averia y no por maquina.
    NO_SE_PARTE = ("jornadas",)

    def __init__(self, centro_de):
        self.centro_de = centro_de
        self.c = {}

    def _grupos(self, filas):
        grupos = {}
        for f in filas:
            clave = self.centro_de(f)
            if clave:
                grupos.setdefault(str(clave), []).append(f)
        return grupos

    def _reparte(self, metodo, filas):
        for clave, grupo in self._grupos(filas).items():
            if clave not in self.c:
                self.c[clave] = Dia("1900-01-01")
            getattr(self.c[clave], metodo)(grupo)

    def come_partes(self, filas):
        self._reparte("come_partes", filas)

    def come_lineas(self, filas):
        self._reparte("come_lineas", filas)

    def come_mov_maquina(self, filas):
        self._reparte("come_mov_maquina", filas)

    def come_recaudacion(self, filas):
        self._reparte("come_recaudacion", filas)

    def come_sat(self, filas):
        self._reparte("come_sat", filas)

    def come_ventas_telemetria(self, filas):
        self._reparte("come_ventas_telemetria", filas)

    def come_ventas_visita(self, filas):
        self._reparte("come_ventas_visita", filas)

    def fila(self, fecha):
        """{"f": dia, "centros": {clave: bloques}}, con los mismos bloques que la
        fila del dia —para que la API la recorte con la misma tijera— y sin lo
        que va a cero: para el interno son cientos de centros por dia y casi
        todos tienen uno o dos bloques."""
        centros = {}
        for clave, d in sorted(self.c.items()):
            if d.vacio():
                continue
            x = d.fila()
            x.pop("f", None)
            for b in self.NO_SE_PARTE:
                x.pop(b, None)
            x["sat"].pop("cierres", None)
            x["servicio"].pop("centros_dia", None)
            x["venta"].pop("fuente", None)
            x = _compacta(x)
            if x:
                centros[clave] = x
        return {"f": fecha, "centros": centros}


def _compacta(v):
    """Quita ceros, vacios y histogramas sin valores, recursivamente."""
    if isinstance(v, dict):
        if "h" in v and "n" in v:           # un histograma
            return v if v.get("n") else None
        out = {}
        for k, x in v.items():
            x = _compacta(x)
            if x not in (None, 0, 0.0, {}, [], ""):
                out[k] = x
        return out
    return v


def _suma_profunda(a, b):
    """Suma dos bloques de centro: numeros se suman, histogramas con suma_hist."""
    if a is None:
        return json.loads(json.dumps(b))
    if isinstance(b, dict):
        if "h" in b and "n" in b:
            return suma_hist(a, b)
        out = dict(a)
        for k, x in b.items():
            out[k] = _suma_profunda(a.get(k), x)
        return out
    if isinstance(b, (int, float)) and isinstance(a, (int, float)):
        r = a + b
        return round(r, 3) if isinstance(r, float) else r
    return b


def filas_de_centros(filas_centros, quiere=None):
    """Las filas de un dia, pero sumando solo los centros de `quiere`.

    Salen con la forma de la fila del dia, asi que `suma_filas` las junta igual
    y la pantalla no distingue si hay filtro o no. Lo que no se parte por centro
    —jornadas, cierre de averias, distintos del dia entre centros— no sale.
    `maquinas_dia` si se suma: una maquina es de un solo centro.

    La misma cuenta que `filasDeCentros` en app/comun/periodos.js.
    """
    out = []
    for f in sorted(filas_centros or [], key=lambda x: x.get("f", "")):
        fila = None
        for clave, c in (f.get("centros") or {}).items():
            if quiere is not None and clave not in quiere:
                continue
            fila = _suma_profunda(fila, c)
        if fila:
            fila["f"] = f["f"]
            out.append(fila)
    return out


def suma_centros(filas_centros, quiere=None):
    """Un renglon por centro para un rango: visitas, venta, tareas... sumadas.

    La misma cuenta que `sumaCentros` en app/comun/periodos.js.
    """
    por = {}
    for f in filas_centros or []:
        for clave, c in (f.get("centros") or {}).items():
            if quiere is not None and clave not in quiere:
                continue
            s, ve, sat = c.get("servicio") or {}, c.get("venta") or {}, c.get("sat") or {}
            a = por.setdefault(clave, {"visitas": 0, "min_n": 0, "min_suma": 0.0,
                                       "maquinas_dia_max": 0, "carga_valor": 0.0,
                                       "merma_euros": 0.0, "venta_importe": 0.0,
                                       "tareas": 0, "dias": 0})
            a["dias"] += 1
            a["visitas"] += s.get("visitas", 0)
            a["min_n"] += (s.get("min") or {}).get("n", 0)
            a["min_suma"] = round(a["min_suma"] + (s.get("min") or {}).get("suma", 0), 3)
            a["maquinas_dia_max"] = max(a["maquinas_dia_max"], s.get("maquinas_dia", 0))
            a["carga_valor"] = round(a["carga_valor"] + (s.get("carga") or {}).get("valor", 0), 2)
            a["merma_euros"] = round(a["merma_euros"] + sum(
                (m or {}).get("euros", 0) for m in (s.get("merma") or {}).values()), 2)
            a["venta_importe"] = round(a["venta_importe"] + ve.get("importe", 0), 2)
            a["tareas"] += sat.get("tareas", 0)
    for a in por.values():
        a["min_medio"] = round(a["min_suma"] / a["min_n"], 1) if a["min_n"] else None
    return por


# ----------------------------------------------------------------------
# juntar dias
# ----------------------------------------------------------------------
def suma_filas(filas):
    """Suma las filas de un rango y deja listo lo que la pagina va a ensenar.

    Es la MISMA cuenta que hace el navegador en `app/comun/periodos.js`, y esta
    aqui tambien a proposito: es la que se puede probar sin navegador, y la que
    usan el asistente y las alarmas el dia que miren un rango.
    """
    filas = [f for f in filas if f]
    if not filas:
        return {"dias": 0, "desde": None, "hasta": None}
    fechas = sorted(f["f"] for f in filas)
    out = {
        "dias": len(filas),
        "desde": fechas[0],
        "hasta": fechas[-1],
        "servicio": {"visitas": 0, "partes": 0, "coste_servicio": 0.0,
                     "carga": {"valor": 0.0, "unidades": 0.0, "vendibles": 0.0},
                     "merma": {m: {"lineas": 0, "unidades": 0.0, "euros": 0.0}
                               for m in MOTIVOS_MERMA},
                     "maquinas_dia_max": 0, "centros_dia_max": 0},
        "dinero": {"periodos": {}},
        "sat": {"tareas": 0, "averias_tecnicas": 0, "preventivos": 0, "fallos_tecnicos": 0},
        "jornadas": {"jornadas": 0, "km_total": 0.0, "temperatura_fuera": 0, "gps": 0},
        "venta": {"unidades": 0.0, "importe": 0.0, "maquinas_dia_max": 0, "fuentes": [],
                  "imposibles": 0},
        "por_dia": [],
    }
    hmin = hcierres = hkm = htemp = None
    fuentes = set()
    for f in filas:
        s = f.get("servicio") or {}
        o = out["servicio"]
        o["visitas"] += s.get("visitas", 0)
        o["partes"] += s.get("partes", 0)
        o["coste_servicio"] += s.get("coste_servicio", 0) or 0
        o["maquinas_dia_max"] = max(o["maquinas_dia_max"], s.get("maquinas_dia", 0))
        o["centros_dia_max"] = max(o["centros_dia_max"], s.get("centros_dia", 0))
        for k, v_ in (s.get("carga") or {}).items():
            o["carga"][k] = round(o["carga"].get(k, 0) + v_, 2)
        for motivo, d in (s.get("merma") or {}).items():
            acum = o["merma"].setdefault(motivo, {"lineas": 0, "unidades": 0.0, "euros": 0.0})
            acum["lineas"] += d.get("lineas", 0)
            acum["unidades"] = round(acum["unidades"] + d.get("unidades", 0), 2)
            acum["euros"] = round(acum["euros"] + d.get("euros", 0), 2)
        hmin = suma_hist(hmin, s.get("min"))

        for periodo, d in ((f.get("dinero") or {}).get("periodos") or {}).items():
            acum = out["dinero"]["periodos"].setdefault(
                periodo, {"registros": 0, "efectivo": 0.0, "banco": 0.0,
                          "ciego": 0.0, "imposibles": 0})
            for k in acum:
                acum[k] = round(acum[k] + d.get(k, 0), 2) if isinstance(acum[k], float) \
                    else acum[k] + d.get(k, 0)

        sat = f.get("sat") or {}
        for k in ("tareas", "averias_tecnicas", "preventivos", "fallos_tecnicos"):
            out["sat"][k] += sat.get(k, 0)
        hcierres = suma_hist(hcierres, sat.get("cierres"))

        j = f.get("jornadas") or {}
        out["jornadas"]["jornadas"] += j.get("jornadas", 0)
        out["jornadas"]["km_total"] = round(out["jornadas"]["km_total"] + j.get("km_total", 0), 2)
        out["jornadas"]["temperatura_fuera"] += j.get("temperatura_fuera", 0)
        out["jornadas"]["gps"] += j.get("gps", 0)
        hkm = suma_hist(hkm, j.get("km"))
        htemp = suma_hist(htemp, j.get("temperatura"))

        ve = f.get("venta") or {}
        out["venta"]["unidades"] = round(out["venta"]["unidades"] + ve.get("unidades", 0), 2)
        out["venta"]["importe"] = round(out["venta"]["importe"] + ve.get("importe", 0), 2)
        out["venta"]["maquinas_dia_max"] = max(out["venta"]["maquinas_dia_max"],
                                               ve.get("maquinas_dia", 0))
        out["venta"]["imposibles"] += ve.get("imposibles", 0)
        if ve.get("fuente"):
            fuentes.add(ve["fuente"])

        out["por_dia"].append({
            "f": f["f"],
            "visitas": s.get("visitas", 0),
            "importe": (f.get("venta") or {}).get("importe", 0),
            "tareas": sat.get("tareas", 0),
            "carga": (s.get("carga") or {}).get("valor", 0),
        })

    out["servicio"]["coste_servicio"] = round(out["servicio"]["coste_servicio"], 2)
    out["servicio"]["duracion_min"] = resumen_hist("minutos", hmin)
    out["sat"]["horas_cierre"] = resumen_hist("horas_cierre", hcierres)
    out["jornadas"]["km"] = resumen_hist("km", hkm)
    out["jornadas"]["temperatura"] = resumen_hist("temperatura", htemp)
    out["venta"]["fuentes"] = sorted(fuentes)
    out["por_dia"].sort(key=lambda x: x["f"])
    out["_nota_distintas"] = (
        "«maquinas_dia_max» es el maximo de un dia, no el total del rango: la misma "
        "maquina se visita muchas veces y sumar los dias la contaria una vez por visita.")
    out["_nota_aprox"] = (
        "Las medianas y los p90 de un rango salen del histograma sumado: son exactas "
        "hasta el ancho de su tramo. La media y los totales si son exactos.")
    return out


# ----------------------------------------------------------------------
# rangos con nombre
# ----------------------------------------------------------------------
def mes_de(fecha):
    return str(fecha)[:7]


def meses_entre(desde, hasta):
    """Los meses (AAAA-MM) que toca un intervalo, en orden."""
    d = datetime.date.fromisoformat(str(desde)[:10]).replace(day=1)
    fin = datetime.date.fromisoformat(str(hasta)[:10]).replace(day=1)
    out = []
    while d <= fin:
        out.append(f"{d.year}-{d.month:02d}")
        d = datetime.date(d.year + 1, 1, 1) if d.month == 12 else datetime.date(d.year, d.month + 1, 1)
    return out


def rango(nombre, hoy=None):
    """Los rangos con nombre que ofrece la pagina, resueltos a dos fechas.

    Estan aqui, en Python, aunque los pinte el navegador: asi el mismo nombre
    significa lo mismo en la pagina, en el asistente y en una prueba. «hoy»
    puede no tener dato todavia —la carga va de noche y trae hasta ayer—, y eso
    lo dice la pagina, no se corrige aqui: una fila que no esta se ve vacia, y
    una fecha movida en silencio no se ve.
    """
    hoy = hoy or datetime.date.today()
    ayer = hoy - datetime.timedelta(days=1)
    primero = hoy.replace(day=1)
    fin_mes_pasado = primero - datetime.timedelta(days=1)
    if nombre == "hoy":
        return hoy.isoformat(), hoy.isoformat()
    if nombre == "ayer":
        return ayer.isoformat(), ayer.isoformat()
    if nombre == "semana":            # lunes a hoy
        return (hoy - datetime.timedelta(days=hoy.weekday())).isoformat(), hoy.isoformat()
    if nombre == "mes":
        return primero.isoformat(), hoy.isoformat()
    if nombre == "mes_pasado":
        return fin_mes_pasado.replace(day=1).isoformat(), fin_mes_pasado.isoformat()
    if nombre == "30dias":
        return (hoy - datetime.timedelta(days=29)).isoformat(), hoy.isoformat()
    if nombre == "anio":
        return hoy.replace(month=1, day=1).isoformat(), hoy.isoformat()
    if nombre == "todo":
        return PRIMER_DIA, hoy.isoformat()
    raise ValueError(f"No existe el rango «{nombre}»")


RANGOS = ("hoy", "ayer", "semana", "mes", "mes_pasado", "30dias", "anio", "todo")

# El nombre que lee una persona. Va al indice para que la pagina no lleve su
# propia lista y se queden distintas.
NOMBRES_RANGO = {
    "hoy": "Hoy",
    "ayer": "Ayer",
    "semana": "Esta semana",
    "mes": "Este mes",
    "mes_pasado": "Mes pasado",
    "30dias": "Últimos 30 días",
    "anio": "Este año",
    "todo": "Todo el histórico",
}


# ----------------------------------------------------------------------
# los ficheros de la serie
# ----------------------------------------------------------------------
def fusiona_mes(filas_viejas, filas_nuevas):
    """Un mes de la serie: lo que ya habia, con los dias recalculados encima.

    Un dia recalculado SUSTITUYE al de antes, no se suma: es el mismo dia visto
    otra vez. Y los dias que esta ejecucion no ha mirado se quedan como estaban,
    que es lo que hace que la historia se acumule sin tener que releerla cada
    noche.
    """
    por_fecha = {f["f"]: f for f in (filas_viejas or []) if f.get("f")}
    for f in filas_nuevas or []:
        if f.get("f"):
            por_fecha[f["f"]] = f
    return [por_fecha[k] for k in sorted(por_fecha)]


def resumen_mes(mes, filas):
    """La linea de un mes en el indice: lo justo para pintar una barra sin bajarlo."""
    totales = suma_filas(filas)
    return {
        "mes": mes,
        "dias": totales["dias"],
        "desde": totales["desde"],
        "hasta": totales["hasta"],
        "visitas": totales.get("servicio", {}).get("visitas", 0),
        "importe": totales.get("venta", {}).get("importe", 0),
        "tareas": totales.get("sat", {}).get("tareas", 0),
        "carga": totales.get("servicio", {}).get("carga", {}).get("valor", 0),
        "imposibles": totales.get("venta", {}).get("imposibles", 0),
    }
