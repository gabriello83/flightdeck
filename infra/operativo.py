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
        self.venta_tel = set()       # maquinas con venta por telemetria
        self.repo = {}               # clase -> unidades vendibles repuestas
        self.repo_consumibles = 0.0
        self.repo_valor = 0.0
        self.venta = None
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
                if pdv:
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
                else:
                    self.visitas_sin_vehiculo += 1
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
        # La telemetria segun los ficheros de los sistemas de cobro (docs/53):
        # None mientras no se haya subido ninguno.
        self.externa = None
        self.fuera = None
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
                    "cod_pdv": str(R.v(f, "cod_pdv", "") or ""), "ubicacion": R.v(f, "ubicacion", "")})
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

        out["telemetria"] = self.telemetria_vencloud(d)
        if self.externa is not None and "sin_dato" not in out["telemetria"]:
            out["telemetria"]["diferencias"] = self.diferencias()
        return out

    def telemetria_vencloud(self, d):
        """Sin ficheros de los sistemas: lo que VenCloud dice que lleva telemetria
        (40 maquinas en octubre de 2026) y cuantas mandaron su DEX."""
        auditables = getattr(self, "_auditables", None)
        if auditables:
            con = len(d.dex & auditables)
            pct = porcentaje(con, len(auditables))
            return {"auditables": len(auditables), "con_dex": con, "pct": pct,
                    "color": semaforo(pct)}
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
                    "cod_pdv": c["cod_pdv"], "ubicacion": c["ubicacion"]}
            if "nayax" in x:
                fila["nayax"] = {"id": x["nayax"]["id"], "ultima": x["nayax"]["ultima"]}
            if "prodelfi" in x:
                p = x["prodelfi"]
                fila["prodelfi"] = {"codigo": p["codigo"], "grupo": p["grupo"],
                                    "descripcion": p["descripcion"], "como": p["como"]}
            if "nebula" in x:
                fila["nebula"] = dict(x["nebula"])
            maquinas.append(fila)
        return {
            "generado": datetime.datetime.utcnow().isoformat() + "Z",
            "perfil": perfil_id,
            "ultimo_dia": max(dias) if dias else None,
            "dias": dias,
            "ficheros": self.foto.get("telemetria"),
            "maquinas": maquinas,
            "fuera": self.fuera,
            "_nota": ("Diferencias entre los sistemas de telemetría (ficheros de Nayax, Prodelfi y "
                      "Nebula subidos en la consola) y VenCloud: máquinas de un sistema, con "
                      "«vencloud» si el censo las marca con telemetría, y las que el censo marca "
                      "sin estar en ningún sistema (sistema «solo_vencloud»). Cada día lleva "
                      "las que mandaron venta por telemetría (informe 179) y las que mandaron "
                      "su lectura (DEX). «fuera» son las de esos sistemas que no están en "
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
