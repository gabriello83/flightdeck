"""
La pagina de rutas por areas: lo que no es del plan de un dia (docs/67).

Lo pidio Gabriele el 19 de octubre de 2026. La pagina de rutas (docs/55) ya
daba, dia a dia, el plan contra las visitas. Ahora entra por areas y, de cada
area, quiere ademas cuatro cosas que no salen del plan:

  · quien ha hecho cada ruta;
  · las llamadas de maquina vacia y de que maquina son;
  · las maquinas que faltan por recaudar en el mes, con el dinero que se
    puede esperar de ellas por lo que recaudaron los meses anteriores;
  · las maquinas que llevan mas de 12 dias laborables sin reponer.

El 21 de octubre añadio una quinta: las maquinas con una incidencia de
producto caducado o de insectos (lo mismo que las tarjetas «Caducados» y
«Emergencia sanitaria» de la pagina de incidencias, docs/56).

Las cuatro miran la VENTANA ENTERA de los agregados (120 dias), no los siete
ultimos del informe general: por eso es un modulo aparte, que se alimenta en
el mismo recorrido por dias y no guarda filas, solo la ultima fecha de cada
cosa por maquina.

De donde sale cada una, y por que:

  · Recaudada = un parte de reponedor con la marca `recaudacion` (informe
    105), o un acto de recaudar de la recaudacion oficial (informe 132,
    criterio 3). La marca del parte es la que llega al dia; la oficial llega a
    tandas, cuando Loomis cuenta las bolsas (docs/24, docs/25), asi que sola
    dejaria el mes en curso casi vacio.
  · El dinero que se espera es el EFECTIVO oficial de los tres meses
    completos anteriores (imp_recaudado, criterios 2, 3 y 4, por anho/mes y
    nunca por `fecha`: reglas.recaudacion_del_periodo), dividido entre tres.
    Un mes sin recaudar cuenta como cero: es lo que esa maquina da al mes.
  · Repuesta = una linea de carga (A2, tipo CM) en su matricula ese dia.
  · Llamada de maquina vacia = una tarea de la SAT con la operacion S010
    «Reponer distribuidor automatico» o C016 «Selecciones vacias».
  · Caducado o insectos = una tarea de la SAT con las marcas CADUCADO o
    HIGIENE de incidencias.marcas (la operacion, o la palabra en el titulo o
    en la ultima nota). Las devoluciones no cuentan, como en incidencias.

EL AMBITO SE APLICA AL ESCRIBIR: las filas que llegan aqui ya vienen del
perfil, como en todo lo demas.

Sin dependencias: se prueba con `python3 infra/test_rutas.py`.
"""

import bisect
import datetime

import incidencias as IN
import operativo as OP
import reglas as R

# Gabriele, 19-oct: «las maquinas que no se han repuesto mas de 12 dias
# laborales». Laborable = de lunes a viernes y sin festivo de su delegacion
# (config/festivos.json, el mismo calendario del control de festivos).
LABORABLES_SIN_REPONER = 12

# Los meses completos con los que se calcula lo que una maquina recauda al mes.
MESES_PROMEDIO = 3

# Las operaciones de la SAT que son una llamada de maquina vacia.
CODIGOS_VACIA = ("S010", "C016")
TEXTOS_VACIA = ("REPONER DISTRIBUIDOR", "SELECCIONES VACIAS")

# Un parte con esta marca lleva bolsa de recaudacion (informe 105). Llega como
# 1/0, y en algun informe como booleano.
MARCAS_SI = ("1", "true", "t", "s", "si")

SIN_LINEAS = ("No ha llegado ninguna línea de carga (A2) en la ventana: sin ellas no se "
              "sabe cuándo se repuso cada máquina.")
SIN_PARTES = ("No ha llegado ningún parte de visita en la ventana: sin ellos no se sabe qué "
              "máquinas se han recaudado.")
SIN_OFICIAL = ("No ha llegado la recaudación oficial (informe 132) de los meses anteriores: "
               "no se puede calcular cuánto recauda cada máquina al mes.")


def _iso(d):
    return d.isoformat() if hasattr(d, "isoformat") else str(d)[:10]


def _mes(fecha):
    return str(fecha)[:7]


def meses_anteriores(mes, n=MESES_PROMEDIO):
    """Los n meses completos antes de 'AAAA-MM', del mas viejo al mas nuevo."""
    a, m = int(mes[:4]), int(mes[5:7])
    out = []
    for _ in range(n):
        a, m = (a - 1, 12) if m == 1 else (a, m - 1)
        out.append(f"{a}-{m:02d}")
    return out[::-1]


def dias_laborables(desde, hasta, delegacion, festivos):
    """Los dias laborables de `desde` a `hasta`, los dos incluidos y en orden:
    de lunes a viernes y sin festivo de la delegacion."""
    d = datetime.date.fromisoformat(str(desde)[:10])
    fin = datetime.date.fromisoformat(str(hasta)[:10])
    out = []
    while d <= fin:
        if d.weekday() < 5 and not OP.es_festivo(d.isoformat(), delegacion, festivos):
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


def laborables_entre(desde, hasta, delegacion, festivos):
    """Los dias laborables despues de `desde` y hasta `hasta` incluido."""
    return len([d for d in dias_laborables(desde, hasta, delegacion, festivos) if d > str(desde)[:10]])


def es_llamada_vacia(tarea):
    codigo = str(R.v(tarea, "cod_operacion", "") or "").strip().upper()
    op = IN.sin_acentos(R.v(tarea, "operacion", ""))
    return codigo in CODIGOS_VACIA or any(t in op for t in TEXTOS_VACIA)


def _vivo(f):
    """Un punto de venta que hay que atender: el mismo filtro que el cuadrado
    de puntos de venta activos (operativo.come_censo)."""
    return (not R.es_centinela(f) and R.cliente_vivo(f) and R.centro_vivo(f) and R.pdv_vivo(f)
            and str(R.v(f, "estado_pdv", "")) == str(OP.PDV_ACTIVO))


# ----------------------------------------------------------------------
# un perfil, a lo largo de la ventana
# ----------------------------------------------------------------------
class Maquinas:
    """Lo que un perfil acumula de la ventana para la pagina de rutas.

    Nada guarda filas: por maquina, la ultima fecha de cada cosa; por dia y
    ruta, quien la hizo.
    """

    def __init__(self):
        self.desde = None
        self.hay_partes = False
        self.hay_lineas = False
        self.ultima_visita = {}      # pdv -> (fecha, ruta, reponedor), la ultima visita real
        self.ultima_carga = {}       # matricula -> fecha
        self.recaudada = {}          # pdv -> {fechas}
        self.efectivo = {}           # pdv -> {'AAAA-MM': euros}
        self.meses_oficiales = set()
        self.quien = {}              # fecha -> {(delegacion, ruta): {reponedores}}

    def come(self, nombre, filas, dia):
        f = _iso(dia)
        self.desde = min(self.desde or f, f)
        if nombre == "partes":
            self.come_partes(filas, f)
        elif nombre == "lineas":
            self.come_lineas(filas, f)
        elif nombre == "recaudacion":
            self.come_recaudacion(filas)

    def come_partes(self, filas, fecha):
        self.hay_partes = True
        for p in filas:
            if not R.es_visita_real(p):
                continue
            pdv = str(R.v(p, "cod_pdv", "") or "")
            ruta = str(R.v(p, "ruta", "") or "").strip()
            emp = str(R.v(p, "empleado", "") or "").strip()
            deleg = str(R.v(p, "delegacion", "") or "")
            if emp:
                self.quien.setdefault(fecha, {}).setdefault((deleg, ruta or "Sin ruta"), set()).add(emp)
            if not pdv:
                continue
            antes = self.ultima_visita.get(pdv)
            if antes is None or fecha >= antes[0]:
                self.ultima_visita[pdv] = (fecha, ruta, emp)
            if str(R.v(p, "hay_recaudacion", "")).strip().lower() in MARCAS_SI:
                self.recaudada.setdefault(pdv, set()).add(fecha)

    def come_lineas(self, filas, fecha):
        self.hay_lineas = True
        for l in filas:
            if R.v(l, "tipo_linea") != "CM":
                continue
            m = str(R.v(l, "matricula", "") or "").strip()
            if m and fecha > self.ultima_carga.get(m, ""):
                self.ultima_carga[m] = fecha

    def come_recaudacion(self, filas):
        for x in filas:
            pdv = str(R.v(x, "cod_pdv", "") or "")
            if not pdv or not R.es_acto_de_recaudar(x):
                continue
            try:
                anio, mes = int(R.v(x, "anho")), int(R.v(x, "mes"))
                imp = float(R.v(x, "imp_recaudado", 0) or 0)
            except (TypeError, ValueError):
                continue
            # Una fila imposible es un contador roto, no dinero (reglas).
            if abs(imp) > R.LIMITE_FILA_RECAUDACION:
                continue
            periodo = f"{anio}-{mes:02d}"
            self.meses_oficiales.add(periodo)
            e = self.efectivo.setdefault(pdv, {})
            e[periodo] = e.get(periodo, 0.0) + imp
            if int(R.v(x, "criterio_calculo")) == 3:
                try:
                    dia = int(R.v(x, "dia"))
                    self.recaudada.setdefault(pdv, set()).add(f"{periodo}-{dia:02d}")
                except (TypeError, ValueError):
                    pass

    # --------------------------------------------------------- la salida
    def promedio(self, pdv, meses):
        e = self.efectivo.get(pdv)
        if not e:
            return None
        return round(sum(e.get(m, 0.0) for m in meses) / len(meses), 2)

    def bloque(self, censo, incidencias, festivos, hoy, dias=OP.DIAS_GUARDADOS):
        """Lo que se anade al fichero de rutas: quien hizo cada ruta, las
        llamadas de maquina vacia y las dos listas de maquinas, con el area de
        cada delegacion."""
        ayer = (hoy - datetime.timedelta(days=1)).isoformat()
        primero = (hoy - datetime.timedelta(days=dias)).isoformat()
        mes = _mes(ayer)
        anteriores = meses_anteriores(mes)
        fichas, matriculas = {}, {}
        for f in censo or []:
            if not _vivo(f):
                continue
            pdv = str(R.v(f, "cod_pdv", "") or "")
            if not pdv or pdv in fichas:
                continue
            m = str(R.v(f, "matricula", "") or "").strip()
            fichas[pdv] = f
            if m:
                matriculas[pdv] = m

        def fila(pdv):
            f = fichas[pdv]
            v = self.ultima_visita.get(pdv) or ("", "", "")
            rec = sorted(self.recaudada.get(pdv, ()))
            return {"p": pdv, "m": matriculas.get(pdv, ""),
                    "d": str(R.v(f, "delegacion", "") or ""),
                    "n": str(R.v(f, "num_centro", "") or ""),
                    "c": str(R.v(f, "centro", "") or "").strip(),
                    "u": str(R.v(f, "ubicacion", "") or "").strip()[:60],
                    "k": OP.nombre_clase(R.v(f, "clase_pdv", None)),
                    "r": v[1], "e": v[2], "v": v[0] or None,
                    "rc": rec[-1] if rec else None,
                    "mr": sum(1 for m in anteriores if any(x.startswith(m) for x in rec)),
                    "pm": self.promedio(pdv, anteriores)}

        # Por recaudar: se recaudo en alguno de los meses anteriores y en este
        # todavia no.
        por_recaudar, recaudadas_mes, recaudan = [], 0, 0
        for pdv in fichas:
            rec = self.recaudada.get(pdv, ())
            if not any(_mes(x) in anteriores for x in rec):
                continue
            recaudan += 1
            if any(_mes(x) == mes for x in rec):
                recaudadas_mes += 1
            else:
                por_recaudar.append(fila(pdv))
        por_recaudar.sort(key=lambda x: (-(x["pm"] or 0), x["d"], x["c"]))

        # Sin reponer: mas de 12 laborables desde la ultima carga, o ninguna en
        # toda la ventana. Los laborables de cada delegacion se cuentan una vez.
        sin_reponer, nunca, laborables = [], [], {}
        for pdv, m in matriculas.items():
            ultima = self.ultima_carga.get(m)
            if ultima is None:
                x = fila(pdv)
                x["rp"], x["lab"] = None, None
                nunca.append(x)
                continue
            dl = str(R.v(fichas[pdv], "delegacion", "") or "")
            if dl not in laborables:
                laborables[dl] = dias_laborables(self.desde or ultima, ayer, dl, festivos)
            lab = len(laborables[dl]) - bisect.bisect_right(laborables[dl], ultima)
            if lab > LABORABLES_SIN_REPONER:
                x = fila(pdv)
                x["rp"], x["lab"] = ultima, lab
                sin_reponer.append(x)
        sin_reponer.sort(key=lambda x: (-x["lab"], x["d"], x["c"]))
        nunca.sort(key=lambda x: (x["d"], x["k"], x["c"]))

        # Las llamadas de maquina vacia y las de caducado o insectos: la foto
        # de M13 si llego, si no las tareas de la ventana.
        llamadas, sanitarias = [], []
        if incidencias is not None:
            al_dia = incidencias.foto is not None
            for t in (incidencias.foto if al_dia else incidencias.tareas.values()):
                vacia = es_llamada_vacia(t)
                texto = " · ".join(x for x in (str(R.v(t, "titulo", "") or "").strip(),
                                               str(R.v(t, "ultima_nota", "") or "").strip()) if x)
                marcas = IN.marcas(t, texto)
                san = 0 if marcas & IN.DEVOLUCION else marcas & (IN.CADUCADO | IN.HIGIENE)
                if not vacia and not san:
                    continue
                ident = R.v(t, "id", None)
                alta = ((IN._fecha_hora(R.v(t, "apertura", "")) if al_dia
                         else incidencias.apertura.get(ident))
                        or (IN._fecha_hora(R.v(t, "fecha_alta", "")) or "")[:10])
                if not alta or alta[:10] < primero or alta[:10] > ayer:
                    continue
                abierta = None
                if al_dia:
                    abierta = int(not (int(R.v(t, "tipo_estado", -1) or -1) == IN.TIPO_ESTADO_FINALIZADA
                                       or int(R.v(t, "estado", -1) or -1) == IN.ESTADO_FINALIZADA))
                fila = {
                    "f": alta, "m": str(R.v(t, "matricula", "") or ""),
                    "p": str(R.v(t, "cod_pdv", "") or ""),
                    "d": str(R.v(t, "delegacion", "") or ""),
                    "n": str(R.v(t, "num_centro", "") or ""),
                    "c": str(R.v(t, "centro", "") or "").strip(),
                    "o": str(R.v(t, "operacion", "") or "").strip(),
                    "x": f"{R.v(t, 'serie', '') or ''}-{R.v(t, 'numero', '')}", "a": abierta}
                if vacia:
                    llamadas.append(fila)
                if san:
                    sanitarias.append(dict(fila, k=" y ".join(
                        n for b, n in ((IN.CADUCADO, "caducado"), (IN.HIGIENE, "insectos")) if san & b)))
            llamadas.sort(key=lambda x: x["f"], reverse=True)
            sanitarias.sort(key=lambda x: x["f"], reverse=True)

        quien = {f: {f"{dl}\u0001{r}": sorted(e, key=str.lower) for (dl, r), e in sorted(rs.items())}
                 for f, rs in sorted(self.quien.items()) if f >= primero}
        delegs = {x["d"] for x in por_recaudar + sin_reponer + nunca + llamadas + sanitarias}
        delegs |= {dl for rs in self.quien.values() for dl, _ in rs}
        sin_oficial = not any(m in self.meses_oficiales for m in anteriores)
        return {
            "zonas": {dl: IN.zona_de(dl) for dl in sorted(delegs)},
            "quien": quien,
            "control_maquinas": {
                "desde": self.desde,
                "mes": mes,
                "meses_promedio": anteriores,
                "laborables": LABORABLES_SIN_REPONER,
                "recaudan": recaudan,
                "recaudadas_mes": recaudadas_mes,
                "sin_partes": None if self.hay_partes else SIN_PARTES,
                "sin_lineas": None if self.hay_lineas else SIN_LINEAS,
                "sin_oficial": SIN_OFICIAL if sin_oficial else None,
            },
            # Cada lista en la raiz: se quita entera si al usuario le quitaron
            # su tabla (docs/61).
            "por_recaudar": por_recaudar,
            "sin_reponer": sin_reponer,
            "nunca_repuestas": nunca,
            "llamadas": llamadas,
            "sanitarias": sanitarias,
            "llamadas_fuente": ("M13 · EXT_SAT_INCIDENCIAS" if incidencias is not None
                                and incidencias.foto is not None else "D7 · EXT_SAT_AVERIAS"),
            "_nota_maquinas": (
                "por_recaudar, sin_reponer y nunca_repuestas: por punto de venta activo del censo. p pdv, m matrícula, d delegación, n nº centro, "
                "c centro, u ubicación, k clase, r ruta y e reponedor de la última visita real (v), "
                "rc última recaudación, mr meses recaudada de los tres anteriores, pm efectivo "
                "oficial al mes de media en esos tres meses (null sin recaudación oficial), rp "
                "última carga y lab días laborables desde entonces. llamadas: f apertura, o "
                "operación, x número de tarea, a abierta (null sin M13). sanitarias: igual, y k "
                "caducado, insectos o los dos. quien: los reponedores "
                "de cada «delegación␁ruta» por día, según la ruta del parte."),
        }
