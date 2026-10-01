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
# las 16 sesiones del catalogo (docs/39)
# ----------------------------------------------------------------------
# id: (nombre, tipo minimo, bloques del panel que necesita)
SESIONES = {
    "resumen":          ("Resumen",                        "cliente",     ("servicio", "dinero")),
    "venta_consumo":    ("Venta y consumo",                "cliente",     ("dinero",)),
    "servicio":         ("Servicio recibido",              "cliente",     ("servicio",)),
    "disponibilidad":   ("Disponibilidad",                 "cliente",     ("sat",)),
    "surtido":          ("Surtido y planograma",           "cliente",     ("surtido",)),
    "calidad":          ("Calidad y seguridad alimentaria","cliente",     ("servicio", "jornadas")),
    "rutas":            ("Rutas y jornada",                "operaciones", ("jornadas", "servicio")),
    "efectivo":         ("Recaudacion y efectivo",         "operaciones", ("dinero",)),
    "stock":            ("Stock y merma",                  "operaciones", ("servicio", "inventario")),
    "avisos":           ("Avisos y acciones",              "operaciones", ("alarmas",)),
    "rentabilidad":     ("Rentabilidad",                   "direccion",   ("servicio", "dinero", "sat")),
    "cumplimiento":     ("Cumplimiento",                   "direccion",   ("inventario", "dinero")),
    "usuarios":         ("Usuarios y permisos",            "admin",       ()),
    "catalogo":         ("Catalogo de informes",           "admin",       ()),
    "telefonos":        ("Telefonos y mensajes",           "admin",       ()),
    "carga":            ("Estado de la carga",             "admin",       ("carga",)),
}


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
