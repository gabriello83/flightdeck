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

SIN_PLAN = ("No hay plan de visitas de este día: el informe D12 (VenCloud 184) "
            "no lo trae.")


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

    def __init__(self, fecha):
        self.fecha = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)[:10]
        self.plan = None             # None = no hay informe del plan ese dia
        self.visitados = set()       # puntos de venta con visita real
        self.visitas = 0
        self.vehiculos = set()
        self.visitas_sin_vehiculo = 0
        self.dex = set()             # maquinas con lectura remota
        self.repo = {}               # clase -> unidades vendibles repuestas
        self.repo_consumibles = 0.0
        self.repo_valor = 0.0
        self.venta = None

    def come_partes(self, filas):
        for p in filas:
            if R.es_visita_real(p):
                self.visitas += 1
                pdv = str(R.v(p, "cod_pdv", "") or "")
                if pdv:
                    self.visitados.add(pdv)
                v = R.v(p, "vehiculo", "")
                if vehiculo_real(v):
                    self.vehiculos.add(str(v).strip())
                else:
                    self.visitas_sin_vehiculo += 1
            elif es_lectura_remota(p):
                m = R.v(p, "matricula", "")
                if m:
                    self.dex.add(m)

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
            if R.v(l, "tipo_linea") != "CM":
                continue
            u = float(R.v(l, "cantidad", 0) or 0)
            if R.es_consumible_de_cafe(l):
                self.repo_consumibles += u
                continue
            clase = nombre_clase(clase_de.get(R.v(l, "matricula", "")))
            self.repo[clase] = self.repo.get(clase, 0.0) + u

    def pon_venta(self, dia_serie):
        """La venta del dia, de la MISMA cuenta que la serie (serie.Dia): una
        sola regla de venta, no dos."""
        self.venta = {
            "importe": round(dia_serie.venta_importe, 2),
            "unidades": round(dia_serie.venta_unidades, 2),
            "maquinas": len(dia_serie.venta_maquinas),
            "fuente": dia_serie.venta_fuente,
            "imposibles": dia_serie.venta_imposibles,
        }


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

    def __init__(self, publicar):
        self.dias = {d.isoformat() if hasattr(d, "isoformat") else str(d): None for d in publicar}
        self.fallo = {}          # id de tarea -> es un fallo tecnico
        self.apertura = {}
        self.cierre = {}
        self.foto = {}
        # Los cierres de inventario de ALMACEN, por periodo. Solo las filas de
        # tipo A: son unas quince al mes.
        self.balance = {}

    def dia(self, fecha):
        f = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)[:10]
        if f not in self.dias:
            return None
        if self.dias[f] is None:
            self.dias[f] = DiaOperativo(f)
        return self.dias[f]

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
        cerradas = a_tiempo = sin_tarea = 0
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
            cerradas += 1
            if horas < HORAS_A_TIEMPO:
                a_tiempo += 1
        return cerradas, a_tiempo, sin_tarea

    # ------------------------------------------------------------- la foto
    def come_censo(self, filas):
        """Lo que es foto de hoy: puntos de venta activos y maquinas que se
        pueden auditar en remoto. Las filas ya vienen del ambito del perfil."""
        pdvs, maquinas, auditables = set(), set(), set()
        for f in filas:
            if (R.es_centinela(f) or not R.cliente_vivo(f) or not R.centro_vivo(f)
                    or not R.pdv_vivo(f)):
                continue
            pdv = str(R.v(f, "cod_pdv", "") or "")
            # Activo es el estado 1 de VenCloud, el mismo que usa su informe 20.
            # El estado 0 son sitios sin maquina puesta: 2.012 en el parque de
            # octubre de 2026, que no son puntos de venta que atender.
            if pdv and str(R.v(f, "estado_pdv", "")) == str(PDV_ACTIVO):
                pdvs.add(pdv)
            m = R.v(f, "matricula", "")
            if m:
                maquinas.add(m)
                if tiene_telemetria(f):
                    auditables.add(m)
        self.foto["pdvs"] = {"activos": len(pdvs), "maquinas": len(maquinas)}
        self._auditables = auditables

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

        cerradas, a_tiempo, sin_tarea = self.averias_del_dia(d.fecha)
        pct = porcentaje(a_tiempo, cerradas)
        out["averias"] = ({"cerradas": cerradas, "a_tiempo": a_tiempo, "pct": pct,
                           "color": semaforo(pct), "horas": HORAS_A_TIEMPO,
                           "sin_tarea": sin_tarea}
                          if cerradas else
                          {"sin_dato": "Ese día no se cerró ninguna avería.",
                           "cerradas": 0, "sin_tarea": sin_tarea})

        out["furgonetas"] = {"activas": len(d.vehiculos), "visitas": d.visitas,
                             "visitas_sin_vehiculo": d.visitas_sin_vehiculo}

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

        auditables = getattr(self, "_auditables", None)
        if auditables:
            con = len(d.dex & auditables)
            pct = porcentaje(con, len(auditables))
            out["telemetria"] = {"auditables": len(auditables), "con_dex": con, "pct": pct,
                                 "color": semaforo(pct)}
        else:
            out["telemetria"] = {"sin_dato": "Ninguna máquina de este ámbito lleva telemetría."
                                 if auditables is not None else "No se ha podido leer el censo."}
        return out

    def fichero(self, perfil_id, anterior=None):
        """El fichero del perfil: los dias de esta noche sobre los que ya habia.

        Un dia recalculado sustituye al que hubiera; los demas se quedan, hasta
        DIAS_GUARDADOS. Asi la historia se acumula sin releerla, como la serie.
        """
        dias = dict((anterior or {}).get("dias") or {})
        for f, d in self.dias.items():
            if d is not None:
                dias[f] = self.cuadrados_del_dia(d)
        dias = dict(sorted(dias.items())[-DIAS_GUARDADOS:])
        return {
            "generado": datetime.datetime.utcnow().isoformat() + "Z",
            "perfil": perfil_id,
            "ultimo_dia": max(dias) if dias else None,
            "umbrales": {"verde": VERDE, "amarillo": AMARILLO},
            "dias": dias,
            "foto": self.foto,
            "_nota": ("Un día por fecha, con la cifra de ese día tal cual. Lo que no tiene dato "
                      "lleva sin_dato y el motivo. Puntos de venta, telemetría auditable y "
                      "almacenes son la foto de la noche en que se escribió."),
        }


# ----------------------------------------------------------------------
# los almacenes
# ----------------------------------------------------------------------
def almacenes(balance_por_periodo, rutas, ambito):
    """El valor del producto en los almacenes, del ULTIMO cierre mensual.

    `balance_por_periodo`: {(anho, mes): [filas del balance]}, sin filtrar por
    ambito —las filas de almacen no traen centro—. `rutas`: el maestro de rutas,
    que es lo unico que dice de que delegacion es cada almacen.

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
