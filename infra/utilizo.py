"""
Utilizo: cuanto usa VenCloud cada persona, dia a dia (docs/60).

Lo pidio Gabriele el 18 de octubre de 2026: saber cada dia cuanto utiliza
VenCloud cada usuario, en un cuadrado propio, «Utilizo», con su pagina. Dos
personas trabajan con dos cuentas cada una (M.GARCIA y M2.GARCIA, J.MARCOS y
J2.MARCOS) y se ven juntas; ademas, su detalle va en la revision de clientes
(docs/59).

De donde sale: `control.activitylog` de VenCloud apunta cada alta (I), cambio
(U) y borrado (D) que hace un usuario, con la hora (sondas M14Y, docs/17). El
informe `M15 · EXT_ACTIVIDAD_USUARIOS` baja los tres ultimos dias, ya contados
por usuario, dia y hora, y por usuario, dia, entidad y accion. Los ids
negativos son procesos de VenCloud, no personas, y no entran.

La historia la guarda la noche (`cabina/_utilizo/actividad.json.gz`, dos
meses): el informe solo trae tres dias. Un dia que vuelve a llegar sustituye al
guardado, y el de hoy no se guarda, que va a medias.

Solo lo ve un perfil sin ambito de direccion o administracion: es lo que hace
la gente, no ningun cliente, y un perfil de delegacion no tiene por que ver a
la de otra.
"""
import datetime

import reglas as R


def _s(x):
    if x is None:
        return ""
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    return str(x).strip()


GRUPOS_USUARIOS = (
    ("M. García", ("M.GARCIA", "M2.GARCIA")),
    ("J. Marcos", ("J.MARCOS", "J2.MARCOS")),
)
DIAS_ACTIVIDAD = 62

SIN_ACTIVIDAD = ("La actividad de los usuarios todavía no se descarga de VenCloud: falta el "
                 "informe M15 · EXT_ACTIVIDAD_USUARIOS.")


def actividad(estado, filas, hoy):
    """La historia de actividad por usuario y dia, con lo de esta noche dentro.

    `filas`: M15 · EXT_ACTIVIDAD_USUARIOS (tres dias). Un dia que llega
    sustituye entero al guardado: la noche siguiente lo trae completo. Hoy no
    se guarda, que va a medias.
    """
    dias = {d: v for d, v in ((estado or {}).get("dias") or {}).items()}
    nuevos = {}
    for f in filas or []:
        dia, usuario = _s(R.v(f, "dia", ""))[:10], _s(R.v(f, "usuario", "")).upper()
        if len(dia) != 10 or not usuario or dia >= hoy.isoformat():
            continue
        try:
            n = int(float(R.v(f, "veces", 0) or 0))
        except (TypeError, ValueError):
            continue
        u = nuevos.setdefault(dia, {}).setdefault(usuario, {"horas": {}, "entidades": {},
                                                            "primera": "", "ultima": ""})
        if R.v(f, "tipo", "") == "hora":
            try:
                h = str(int(float(R.v(f, "hora", 0))))
            except (TypeError, ValueError):
                continue
            u["horas"][h] = u["horas"].get(h, 0) + n
            p, ul = _s(R.v(f, "primera", ""))[11:19], _s(R.v(f, "ultima", ""))[11:19]
            if p and (not u["primera"] or p < u["primera"]):
                u["primera"] = p
            if ul > u["ultima"]:
                u["ultima"] = ul
        else:
            k = f"{_s(R.v(f, 'entidad', ''))}|{_s(R.v(f, 'accion', ''))}"
            u["entidades"][k] = u["entidades"].get(k, 0) + n
    dias.update(nuevos)
    corte = (hoy - datetime.timedelta(days=DIAS_ACTIVIDAD)).isoformat()
    return {"dias": {d: v for d, v in sorted(dias.items()) if d >= corte}}


def personas(estado, grupos=GRUPOS_USUARIOS, todos=True):
    """Por persona y dia, sus cuentas juntas.

    Con `todos`, todos los usuarios de VenCloud (Utilizo): los de `grupos` con
    sus dos cuentas juntas y cada uno de los demas por su cuenta. Sin el, solo
    `grupos` (su detalle en la revision de clientes). Las horas
    con actividad se cuentan sobre la union de las horas de las cuentas: si las
    dos trabajaron a las 10, es una hora, no dos.
    """
    dias_estado = (estado or {}).get("dias") or {}
    juntas = {c for _, cuentas in grupos for c in cuentas}
    sueltos = sorted({u for us in dias_estado.values() for u in us} - juntas) if todos else []
    personas = [*grupos, *((u, (u,)) for u in sueltos)]
    out = []
    for nombre, cuentas in personas:
        por_dia = []
        for dia, usuarios in sorted(dias_estado.items(), reverse=True):
            mias = [usuarios[c] for c in cuentas if c in usuarios]
            if not mias:
                continue
            horas, entidades = {}, {}
            for u in mias:
                for h, n in u["horas"].items():
                    horas[h] = horas.get(h, 0) + n
                for k, n in u["entidades"].items():
                    entidades[k] = entidades.get(k, 0) + n
            primeras = [u["primera"] for u in mias if u["primera"]]
            por_dia.append({
                "dia": dia, "acciones": sum(horas.values()) or sum(entidades.values()),
                "horas": len(horas), "primera": min(primeras) if primeras else "",
                "ultima": max(u["ultima"] for u in mias),
                "cuentas": [c for c in cuentas if c in usuarios],
                "por_hora": {h: horas[h] for h in sorted(horas, key=int)},
                "entidades": sorted(([*k.split("|", 1), n] for k, n in entidades.items()),
                                    key=lambda x: -x[2])})
        if por_dia or not todos:
            out.append({"nombre": nombre, "cuentas": list(cuentas), "dias": por_dia})
    return out


def fichero(estado, hoy):
    """La pagina de Utilizo: todas las personas, con su historia."""
    if estado is None:
        return {"sin_dato": SIN_ACTIVIDAD}
    gente = personas(estado)
    dias = sorted({d["dia"] for p in gente for d in p["dias"]}, reverse=True)
    return {"generado": hoy.isoformat(), "dias": dias, "personas": gente}


def cuadrado(f):
    """El cuadrado: cuantas personas usaron VenCloud el ultimo dia, y cuanto."""
    if "sin_dato" in f:
        return {"sin_dato": f["sin_dato"]}
    if not f["dias"]:
        return {"sin_dato": "Todavía no ha llegado ningún día de actividad de VenCloud."}
    dia = f["dias"][0]
    del_dia = [d for p in f["personas"] for d in p["dias"] if d["dia"] == dia]
    return {"dia": dia, "usuarios": len(del_dia), "acciones": sum(d["acciones"] for d in del_dia),
            "horas": sum(d["horas"] for d in del_dia)}
