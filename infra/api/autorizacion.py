"""
Quien ve que. La pieza que decide, y la unica que decide.

Dos ideas sostienen todo el fichero:

1. EL AMBITO SE APLICA AL ESCRIBIR, NO AL LEER. La Lambda de agregados ya
   escribio un panel por perfil, con los centros de ese perfil y ningun otro.
   La API lee `cabina/<perfil del usuario>/panel.json`, y ese perfil sale de la
   fila de sesion del servidor, NUNCA de la peticion. Un usuario no puede pedir
   el panel de otro porque en ninguna parte del camino hay un sitio donde pedirlo.

2. CADA TIPO DE PERFIL TIENE UN TECHO. El administrador concede permisos, pero
   no puede conceder lo que el tipo no permite: marcar «WhatsApp» en un perfil
   de cliente no se lo da. Igual que la frontera de permisos de IAM en la
   plantilla: la diferencia entre «no se lo hemos dado» y «no puede».

Sin dependencias: se prueba con `python3 infra/api/test_autorizacion.py`.
"""

# ----------------------------------------------------------------------
# los cuatro tipos de perfil, en orden
# ----------------------------------------------------------------------
NIVEL = {"cliente": 0, "operaciones": 1, "direccion": 2, "admin": 3}


def nivel_de(tipo):
    return NIVEL.get(tipo, -1)


# ----------------------------------------------------------------------
# las sesiones del catalogo (docs/39, mas el cuadro de mando de docs/46)
# ----------------------------------------------------------------------
# id: (nombre, tipo minimo, bloques del panel que necesita)
#
# Un perfil de cliente solo tiene el cuadro de mando (docs/49). Las sesiones
# del panel que antes eran de cliente piden ahora «operaciones»: asi el techo
# de siempre se lo quita, en la API y en la consola a la vez, sin una regla
# aparte que mantener.
SESIONES = {
    "resumen":          ("Resumen",                        "operaciones", ("servicio", "dinero")),
    "venta_consumo":    ("Venta y consumo",                "operaciones", ("dinero",)),
    "servicio":         ("Servicio recibido",              "operaciones", ("servicio",)),
    "disponibilidad":   ("Disponibilidad",                 "operaciones", ("sat",)),
    "surtido":          ("Surtido y planograma",           "operaciones", ("surtido",)),
    "calidad":          ("Calidad y seguridad alimentaria","operaciones", ("servicio", "jornadas")),
    "rutas":            ("Rutas y jornada",                "operaciones", ("jornadas", "servicio")),
    "efectivo":         ("Recaudacion y efectivo",         "operaciones", ("dinero",)),
    "stock":            ("Stock y merma",                  "operaciones", ("servicio", "inventario")),
    "avisos":           ("Avisos y acciones",              "operaciones", ("alarmas",)),
    "rentabilidad":     ("Rentabilidad",                   "direccion",   ("servicio", "dinero", "sat")),
    "cumplimiento":     ("Cumplimiento",                   "direccion",   ("inventario", "dinero")),
    "instalaciones":    ("Instalaciones y altas",          "operaciones", ("instalaciones",)),
    "usuarios":         ("Usuarios y permisos",            "admin",       ()),
    "catalogo":         ("Catalogo de informes",           "admin",       ()),
    "telefonos":        ("Telefonos y mensajes",           "admin",       ()),
    "carga":            ("Estado de la carga",             "admin",       ("carga",)),
    # El cuadro de mando de David (docs/46). No pide ningun bloque del panel:
    # va en su propia carpeta, cabina/<perfil>/cuadro/, y lo sirve /api/cuadro.
    "cuadro":           ("Cuadro de mando",                "cliente",     ()),
}


# ----------------------------------------------------------------------
# las secciones del cuadro de mando (docs/49)
# ----------------------------------------------------------------------
# id: (nombre, flujos del cuadro que necesita). En el orden de la pagina.
#
# El cuadro lleva tres flujos de datos: la venta, las visitas y las
# incidencias. Una seccion que mezcla varios (los indicadores, la evolucion,
# el mapa, el rendimiento por maquina, las conclusiones) los pide todos: con
# uno de menos ensenaria ceros que no son ceros. El servidor sirve la UNION de
# los flujos de las secciones que el perfil ve, y nada mas; lo que no hace
# falta no llega al navegador, igual que con el panel.
TODOS_FLUJOS = ("ventas", "visitas", "incidencias")
SECCIONES_CUADRO = {
    "indicadores":       ("Indicadores",                        TODOS_FLUJOS),
    "evolucion":         ("Evolución diaria",                   TODOS_FLUJOS),
    "mapa":              ("Mapa de centros",                    TODOS_FLUJOS),
    "visitas_maquina":   ("Visitas realizadas por máquina",     ("visitas",)),
    "articulos":         ("Mix de artículos",                   ("ventas",)),
    "incid_operacion":   ("Incidencias por operación",          ("incidencias",)),
    "rendimiento":       ("Rendimiento por máquina",            TODOS_FLUJOS),
    "detalle_incid":     ("Detalle de incidencias",             ("incidencias",)),
    "sin_venta":         ("Máquinas sin venta",                 ("ventas",)),
    "venta_baja":        ("Máquinas con venta baja",            ("ventas",)),
    "maquinas_centro":   ("Máquinas por centro",                ("ventas",)),
    "listado_visitas":   ("Listado de visitas",                 ("visitas",)),
    "preventivos":       ("Mantenimientos preventivos",         ()),
    "conclusiones":      ("Conclusiones",                       TODOS_FLUJOS),
}


def secciones_cuadro(perfil):
    """Las secciones del cuadro que ve este perfil, en el orden de la pagina.

    El perfil guarda las que se le QUITAN (`cuadro_ocultas`), no las que ve:
    asi una seccion nueva sale a todos sin tener que tocar cada perfil, que es
    lo que se pidio («todas puestas de serie»).
    """
    ocultas = set(perfil.get("cuadro_ocultas") or [])
    return [s for s in SECCIONES_CUADRO if s not in ocultas]


def flujos_cuadro(perfil):
    """Los flujos de datos que hacen falta para las secciones que ve."""
    pedidos = {f for s in secciones_cuadro(perfil) for f in SECCIONES_CUADRO[s][1]}
    return [f for f in TODOS_FLUJOS if f in pedidos]


# Lo que cada flujo pone en el indice (por mes y en cabecera) y en un mes.
_CAMPOS_MES_INDICE = {
    "ventas": ("filas", "unidades", "importe", "maquinas_con_venta", "fuente"),
    "visitas": ("visitas",),
    "incidencias": ("incidencias",),
}
_CAMPOS_MES = {
    "ventas": ("ventas", "articulos", "_columnas", "maquinas_con_venta", "fuente"),
    "visitas": ("visitas", "_visitas"),
    "incidencias": ("incidencias", "_incidencias"),
}


def recorta_cuadro_indice(indice, perfil):
    """El indice del cuadro sin los totales de los flujos que no ve."""
    fuera = [f for f in TODOS_FLUJOS if f not in flujos_cuadro(perfil)]
    if not fuera:
        return indice
    out = dict(indice)
    out["meses"] = []
    for m in indice.get("meses") or []:
        m = dict(m)
        for f in fuera:
            for campo in _CAMPOS_MES_INDICE[f]:
                m.pop(campo, None)
        out["meses"].append(m)
    if "ventas" in fuera:
        out.pop("ventas", None)
    return out


def recorta_cuadro_mes(mes, perfil):
    """Un mes del cuadro sin las filas de los flujos que no ve."""
    fuera = [f for f in TODOS_FLUJOS if f not in flujos_cuadro(perfil)]
    if not fuera:
        return mes
    out = dict(mes)
    for f in fuera:
        for campo in _CAMPOS_MES[f]:
            out.pop(campo, None)
    return out


def sesiones_de(tipo, concedidas):
    """Las sesiones que el usuario ve: las que el admin le dio, dentro de su techo.

    El administrador las ve todas sin tener que concederselas.
    """
    n = nivel_de(tipo)
    if tipo == "admin":
        return list(SESIONES)
    permitidas = [s for s in concedidas if s in SESIONES and nivel_de(SESIONES[s][1]) <= n]
    # Orden estable: el del catalogo, no el del alta.
    return [s for s in SESIONES if s in permitidas]


# ----------------------------------------------------------------------
# el techo de permisos por tipo
# ----------------------------------------------------------------------
TECHO = {
    "cliente":     {"ver", "reordenar", "exportar", "asistente"},
    "operaciones": {"ver", "reordenar", "exportar", "asistente", "whatsapp", "incidencia", "alarmas_ver"},
    "direccion":   {"ver", "reordenar", "exportar", "asistente", "whatsapp", "incidencia",
                    "alarmas_ver", "alarmas_crear", "ver_costes"},
    "admin":       {"ver", "reordenar", "exportar", "asistente", "whatsapp", "incidencia",
                    "alarmas_ver", "alarmas_crear", "ver_costes", "administrar"},
}

# El vocabulario completo. permisos_efectivos devuelve SIEMPRE todas estas
# claves, con false las que no apliquen: asi el navegador pregunta por
# permisos.whatsapp sin tener que saber si la clave existe en su tipo de perfil.
TODOS = sorted(set().union(*TECHO.values()))

# Lo que cada tipo trae puesto sin que nadie lo marque. La regla es simple:
# lo que solo sirve para MIRAR viene de serie con el nivel que lo permite, y lo
# que sirve para ACTUAR hacia fuera (WhatsApp, incidencias, administrar) o
# cuesta dinero (el asistente) hay que concederlo a mano. El administrador
# puede quitar un implicito marcandolo a false explicitamente.
IMPLICITOS = {
    "cliente":     {"ver", "reordenar", "exportar"},
    "operaciones": {"ver", "reordenar", "exportar", "alarmas_ver"},
    "direccion":   {"ver", "reordenar", "exportar", "alarmas_ver", "alarmas_crear", "ver_costes"},
    "admin":       set(TECHO["admin"]),
}

# Lo que el panel trae y un cliente no debe ver aunque el bloque sea suyo.
# No es pudor: es NUESTRO coste y NUESTRO stock, no el dato del cliente.
CAMPOS_INTERNOS = (
    ("servicio", "coste_servicio"),
    ("inventario", "existencias"),
)


def permisos_efectivos(perfil, usuario, config):
    """Lo que el usuario puede hacer de verdad.

    Interseccion de tres cosas: lo que el admin marco en el perfil, lo que el
    tipo de perfil admite, y los interruptores globales. Si las tres no
    coinciden, no se puede.
    """
    tipo = perfil.get("tipo", "cliente")
    techo = TECHO.get(tipo, TECHO["cliente"])
    concedidos = perfil.get("permisos", {}) or {}

    implicitos = IMPLICITOS.get(tipo, IMPLICITOS["cliente"])
    out = {p: bool(concedidos.get(p, p in implicitos)) and p in techo for p in TODOS}
    out["ver"] = True  # quien entra, ve; para eso se le dio de alta
    if tipo == "admin":
        for p in techo:
            out[p] = True

    ok, _ = asistente_habilitado(config, perfil, usuario)
    out["asistente"] = ok
    return out


def asistente_habilitado(config, perfil, usuario):
    """Tres interruptores en serie, y devuelve POR QUE no, si no.

    El motivo importa: un usuario al que le falta el interruptor global tiene
    que leer algo distinto de uno que ha agotado su limite del dia.
    """
    if config.get("asistente_global") is False:
        return False, "El asistente esta desactivado para toda la plataforma."
    if not (perfil.get("permisos", {}) or {}).get("asistente", False) and perfil.get("tipo") != "admin":
        return False, "El asistente no esta habilitado para este perfil."
    if usuario.get("asistente") is False:
        return False, "El asistente no esta habilitado para este usuario."
    return True, ""


def dentro_del_limite(usadas, limite):
    """El limite diario por usuario. 0 o ausente significa sin limite."""
    if not limite:
        return True, 0
    return int(usadas) < int(limite), max(0, int(limite) - int(usadas))


# ----------------------------------------------------------------------
# el recorte del panel
# ----------------------------------------------------------------------
def recorta(panel, perfil, config=None):
    """Devuelve solo lo que este perfil puede ver.

    Dos tijeras: fuera los bloques que ninguna de sus sesiones necesita, y
    fuera los campos internos si no es direccion ni admin. Lo que no sale de
    aqui no llega al navegador, asi que no hay nada que ocultar en el cliente.
    """
    tipo = perfil.get("tipo", "cliente")
    sesiones = sesiones_de(tipo, perfil.get("sesiones", []))
    necesarios = {b for s in sesiones for b in SESIONES[s][2]}

    fuera = {
        "generado": panel.get("generado"),
        "periodo": panel.get("periodo"),
        "perfil": perfil.get("perfil_id") or panel.get("perfil"),
        "sesiones": sesiones,
        "paneles": perfil.get("paneles", []),
        "reglas_negocio": perfil.get("reglas_negocio", {}),
    }
    # COPIA, no referencia. Sin esto, quitarle el coste a un cliente lo quitaria
    # del panel original, y el siguiente que lo leyera (otro perfil, o la misma
    # Lambda reutilizando el contenedor) se lo encontraria ya recortado. Es la
    # clase de fallo que no se ve hasta que alguien no ve un dato que si es suyo.
    for bloque in necesarios:
        if bloque in panel:
            fuera[bloque] = dict(panel[bloque]) if isinstance(panel[bloque], dict) else panel[bloque]

    if nivel_de(tipo) < NIVEL["direccion"]:
        for bloque, campo in CAMPOS_INTERNOS:
            if isinstance(fuera.get(bloque), dict):
                fuera[bloque].pop(campo, None)
    return fuera


def bloques_de(perfil):
    """Los bloques del panel que las sesiones de este perfil necesitan."""
    tipo = perfil.get("tipo", "cliente")
    sesiones = sesiones_de(tipo, perfil.get("sesiones", []))
    return {b for s in sesiones for b in SESIONES[s][2]}


def recorta_dia(fila, perfil):
    """Una fila de la serie diaria, con la misma tijera que el panel.

    Una fila de la serie lleva los mismos bloques que el panel —servicio,
    dinero, sat, jornadas—, con las mismas cifras partidas por dias. Si se
    sirviera entera, la serie seria la puerta de atras del panel: un perfil al
    que se le quito el dinero lo veria aqui dia a dia. Asi que se recorta
    igual, y en la MISMA funcion de siempre, no en una copia.

    La venta va con «dinero» a proposito: es facturacion.
    """
    necesarios = bloques_de(perfil)
    tipo = perfil.get("tipo", "cliente")
    fuera = {"f": fila.get("f")}
    for bloque, v in fila.items():
        if bloque == "f":
            continue
        pedido = "dinero" if bloque == "venta" else bloque
        if pedido in necesarios:
            fuera[bloque] = dict(v) if isinstance(v, dict) else v
    if nivel_de(tipo) < NIVEL["direccion"]:
        for bloque, campo in CAMPOS_INTERNOS:
            if isinstance(fuera.get(bloque), dict):
                fuera[bloque].pop(campo, None)
    return fuera


# ----------------------------------------------------------------------
# lo que el asistente puede responder
# ----------------------------------------------------------------------
def contexto_asistente(panel_recortado, perfil):
    """Lo que se le pasa al modelo: exactamente el panel ya recortado.

    El asistente no tiene una via de datos propia. Si un dato no esta en el
    panel que este usuario ve, el asistente tampoco lo tiene, asi que no puede
    filtrarlo ni por descuido ni porque alguien le insista.
    """
    return {
        "ambito": {
            "perfil": perfil.get("nombre") or perfil.get("perfil_id"),
            "tipo": perfil.get("tipo"),
            "centros": perfil.get("ambito", {}).get("centros", []),
            "clientes": perfil.get("ambito", {}).get("clientes", []),
        },
        "datos": panel_recortado,
    }
