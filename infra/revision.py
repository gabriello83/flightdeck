"""
Revision de clientes: lo que esta mal configurado maquina a maquina (docs/59).

Lo pidio Gabriele el 18 de octubre de 2026: un cuadrado «Revision clientes» en
el informe general operativo, con su pagina, filtros por delegacion, cliente y
centro, y estas tablas:

  1. Las maquinas SIN PLANOGRAMA. Es la cifra del cuadrado. La regla es la del
     bloque de instalaciones (`reglas.sin_planograma`): marcada como sin
     planograma, o sin un solo canal con articulo.
  2. Las maquinas con productos SIN TARIFA, con el nivel del que sacan las
     tarifas que si tienen (estandar, centro, punto de venta...). Las de tarifa
     estandar se señalan. Pulsando la matricula, los productos sin tarifa.
  3. Las maquinas con PRECIO DISTINTO: cuantos productos cobran otra cosa que
     su tarifa y la diferencia mas grande. Pulsando, los productos.
  4. Los PLANOGRAMAS CREADOS: su equipo crea cada dia los que faltan, y al dia
     siguiente quiere ver cuales se crearon y quien.

Las tablas 2 y 3 no calculan nada nuevo: son el detalle de tarifas (docs/52)
vuelto del reves, por maquina en vez de por centro. Asi «sin tarifa» es lo
mismo aqui que en la pagina de tarifas: el producto repuesto en seis meses para
el que VenCloud no encuentra precio siguiendo su propio orden. No es la regla
del bloque de instalaciones («ningun id de tarifa en pdv, centro ni cliente»),
que cuenta la tarifa estandar del centro y VenCloud no la usa.

LOS PLANOGRAMAS CREADOS. VenCloud no guarda la historia del planograma
(`recursos.maquinascanales` es el estado de hoy, docs/04) y la fecha de ultimo
cambio no se rellena nunca (docs/09). Asi que se compara el censo de esta noche
con el de la noche anterior: una maquina que anoche no tenia planograma y hoy
si lo tiene, sigue instalada, es un planograma creado ayer. Se guarda en
`cabina/_revision/planogramas.json.gz` y se conservan `DIAS_CREADOS` dias.
Quien lo creo no esta en ningun informe que se baje hoy: va en el campo
`usuario` cuando llegue, y mientras tanto se dice que falta.

Sin dependencias: se prueba con `python3 infra/test_revision.py`.
"""

import datetime

import reglas as R

DIAS_CREADOS = 62

SIN_USUARIO = ("Quién lo creó todavía no se descarga de VenCloud: falta el informe con el "
               "usuario del planograma.")


def _s(x):
    if x is None:
        return ""
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    return str(x).strip()


def _sitio(f):
    return {"delegacion": _s(R.v(f, "delegacion", ""))[:40] or "Sin delegación",
            "cod_cliente": _s(R.v(f, "cod_cliente", "")),
            "cliente": _s(R.v(f, "cliente", ""))[:60],
            "num_centro": _s(R.v(f, "num_centro", "")),
            "centro": _s(R.v(f, "centro", ""))[:60],
            "cod_pdv": _s(R.v(f, "cod_pdv", "")),
            "ubicacion": _s(R.v(f, "ubicacion", ""))[:60]}


def sin_planograma(censo, hoy):
    """{matricula: sitio} de las maquinas instaladas sin planograma.

    La misma cuenta que el bloque de instalaciones: `incidencias_de` ya aparta
    lo que esta de baja, la centinela y el punto de venta sin maquina.
    """
    out = {}
    for f in censo or []:
        mat = _s(R.v(f, "matricula", ""))
        if mat and mat not in out and "sin_planograma" in R.incidencias_de(f, hoy):
            out[mat] = dict(_sitio(f), matricula=mat,
                            marcada=bool(int(R.v(f, "sin_planograma", 0) or 0)),
                            canales=int(R.v(f, "canales_con_articulo", 0) or 0))
    return out


def con_planograma(censo, hoy):
    """{matricula: fila} de las maquinas instaladas que si lo tienen."""
    out = {}
    for f in censo or []:
        mat = _s(R.v(f, "matricula", ""))
        if not mat or mat in out:
            continue
        inc = R.incidencias_de(f, hoy)
        if R.instalado(f) and R.pdv_vivo(f) and R.centro_vivo(f) and R.cliente_vivo(f) \
                and not R.es_centinela(f) and "sin_planograma" not in inc:
            out[mat] = f
    return out


# ----------------------------------------------------------------------
# los planogramas creados, de una noche a otra
# ----------------------------------------------------------------------
def planogramas(estado, censo, hoy, usuarios=None):
    """El estado nuevo: las sin planograma de hoy y los creados.

    `estado` es el de la noche anterior (o None). `usuarios`, si llega, es
    {matricula: {"usuario", "fecha"}} del informe de VenCloud.

    Una segunda ejecucion el mismo dia compara con la misma noche de antes que
    la primera, no consigo misma: si no, los creados de hoy desaparecerian.
    """
    e = estado or {}
    hoy_s = hoy.isoformat()
    if e.get("fecha") == hoy_s:
        previo = e.get("previo") or {}
    else:
        previo = {"fecha": e.get("fecha"), "sin": e.get("sin") or {}}
    ahora = sin_planograma(censo, hoy)
    creados = [c for c in (e.get("creados") or []) if c.get("detectado") != hoy_s]
    if previo.get("fecha"):
        con = con_planograma(censo, hoy)
        dia = (hoy - datetime.timedelta(days=1)).isoformat()
        for mat, antes in sorted(previo["sin"].items()):
            f = con.get(mat)
            if f is None:
                # Ya no esta instalada, o sigue sin planograma: no se ha creado nada.
                continue
            c = dict(_sitio(f), matricula=mat, dia=dia, detectado=hoy_s,
                     desde=previo["fecha"],
                     canales=int(R.v(f, "canales_con_articulo", 0) or 0))
            u = (usuarios or {}).get(mat)
            if u:
                c["usuario"] = u.get("usuario") or ""
                if u.get("fecha"):
                    c["fecha"] = u["fecha"]
            creados.append(c)
    corte = (hoy - datetime.timedelta(days=DIAS_CREADOS)).isoformat()
    creados = [c for c in creados if c.get("detectado", "") >= corte]
    creados.sort(key=lambda c: (c.get("detectado", ""), c["matricula"]), reverse=True)
    return {"fecha": hoy_s, "sin": ahora, "previo": previo, "creados": creados}


# ----------------------------------------------------------------------
# un perfil
# ----------------------------------------------------------------------
def _nivel_de(filas):
    """De donde sacan las tarifas los productos que si la tienen."""
    niveles, estandar = {}, {}
    for r in filas:
        n = r.get("nivel")
        if not n:
            continue
        niveles[n] = niveles.get(n, 0) + 1
        if n == "estandar" and r.get("tarifa"):
            k = (r["tarifa"], r.get("asignada") or "")
            estandar[k] = estandar.get(k, 0) + 1
    principal = max(niveles, key=lambda n: niveles[n]) if niveles else None
    return {"nivel": principal, "niveles": niveles,
            "estandar": [{"tarifa": t, "asignada": a, "productos": n}
                         for (t, a), n in sorted(estandar.items(), key=lambda x: -x[1])]}


def _diferencia(medios):
    """La diferencia mas grande, en valor absoluto, de los medios que no cuadran."""
    out = None
    for x in (medios or {}).values():
        if x.get("ok") is False and x.get("venta") and x.get("tarifa") is not None:
            d = round(x["venta"]["precio"] - x["tarifa"], 2)
            if out is None or abs(d) > abs(out):
                out = d
    return out


def calcula(censo, detalle_tarifas, estado_planogramas, hoy):
    """El fichero de la pagina para un perfil.

    `censo`: las filas de EXT_INSTALACIONES del ambito del perfil.
    `detalle_tarifas`: {num_centro: detalle} de tarifas.calcula, o None si no
    hay maestro de tarifas (y entonces las tablas 2 y 3 dicen que falta).
    `estado_planogramas`: el de `planogramas`, de toda la red; aqui se queda
    con las maquinas del perfil.
    """
    sin = sin_planograma(censo, hoy)
    mias = {_s(R.v(f, "matricula", "")) for f in censo or []}
    out = {"generado": datetime.datetime.utcnow().isoformat() + "Z",
           "sin_planograma": sorted(sin.values(),
                                    key=lambda m: (m["delegacion"], m["cliente"], m["centro"],
                                                   m["matricula"]))}

    e = estado_planogramas or {}
    out["creados"] = [c for c in e.get("creados") or [] if c["matricula"] in mias]
    out["creados_desde"] = (e.get("previo") or {}).get("fecha") or e.get("fecha")
    if not any(c.get("usuario") for c in out["creados"]):
        out["sin_usuario"] = SIN_USUARIO

    if detalle_tarifas is None:
        import tarifas as TA
        out["sin_tarifa"] = {"sin_dato": TA.SIN_MAESTRO}
        out["precio_distinto"] = {"sin_dato": TA.SIN_MAESTRO}
        return out

    sin_tarifa, distinto = [], []
    for num, det in sorted(detalle_tarifas.items()):
        por_maquina = {}
        for r in det.get("filas", []):
            por_maquina.setdefault(r["matricula"], []).append(r)
        for mat, filas in sorted(por_maquina.items()):
            base = {"delegacion": det.get("delegacion", ""), "cod_cliente": det.get("cod_cliente", ""),
                    "cliente": det.get("cliente", ""), "num_centro": num,
                    "centro": det.get("centro", ""), "matricula": mat,
                    "cod_pdv": filas[0].get("cod_pdv", ""), "ubicacion": filas[0].get("ubicacion", ""),
                    "subvencion": any(r.get("subvencion") for r in filas),
                    "productos_total": len(filas)}
            faltan = [r for r in filas if r["estado"] == "sin_tarifa"]
            if faltan:
                sin_tarifa.append(dict(base, **_nivel_de(filas), sin_tarifa=len(faltan),
                                       productos=[{"cod_articulo": r["cod_articulo"],
                                                   "articulo": r.get("articulo", ""),
                                                   "ultima_carga": r.get("ultima_carga", ""),
                                                   "medios": r.get("medios", {})}
                                                  for r in faltan]))
            mal = [r for r in filas if r["estado"] == "no_coincide"]
            if mal:
                prods = []
                for r in mal:
                    prods.append({"cod_articulo": r["cod_articulo"], "articulo": r.get("articulo", ""),
                                  "nivel": r.get("nivel"), "tarifa": r.get("tarifa", ""),
                                  "asignada": r.get("asignada", ""),
                                  "cambio_tarifa": r.get("cambio_tarifa", ""),
                                  "diferencia": _diferencia(r.get("medios")),
                                  "medios": r.get("medios", {})})
                prods.sort(key=lambda p: -abs(p["diferencia"] or 0))
                distinto.append(dict(base, **_nivel_de(filas), distintos=len(mal),
                                     comprobados=sum(1 for r in filas
                                                     if r["estado"] in ("coincide", "no_coincide")),
                                     max_diferencia=prods[0]["diferencia"], productos=prods))
    clave = lambda m: (m["delegacion"], m["cliente"], m["centro"], m["matricula"])
    out["sin_tarifa"] = sorted(sin_tarifa, key=clave)
    out["precio_distinto"] = sorted(distinto, key=clave)
    return out


def cuadrado(fichero, hoy):
    """Lo que el informe general operativo ensena: las maquinas sin planograma."""
    ayer = (hoy - datetime.timedelta(days=1)).isoformat()
    out = {"sin_planograma": len(fichero["sin_planograma"]),
           "creados_ayer": sum(1 for c in fichero.get("creados", []) if c.get("dia") == ayer)}
    if isinstance(fichero.get("sin_tarifa"), list):
        out["sin_tarifa"] = len(fichero["sin_tarifa"])
        out["precio_distinto"] = len(fichero["precio_distinto"])
    return out
