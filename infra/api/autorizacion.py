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
    "preventivos":       ("Mantenimientos preventivos",         ("incidencias",)),
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


# ----------------------------------------------------------------------
# los paneles de cada sesion (docs/63)
# ----------------------------------------------------------------------
# Lo que dibuja /panel/ dentro de cada sesion, en el orden de la pagina. El
# perfil guarda los que se le QUITAN (`paneles_ocultos`), como cuadro_ocultas:
# un panel nuevo sale a todos sin tocar ningun perfil. Una sesion que no esta
# aqui no tiene paneles propios en /panel/ (da cuadrados del informe operativo,
# o pantallas de la consola). «inc_detalle» son las tablas de cada clase de
# instalacion a medias, que la pagina pinta una por clase (inc_<clase>).
#
# Se quitan en la pagina, no en el fichero: los paneles de una sesion salen de
# los mismos bloques, y quitar un bloque dejaria a los demas con ceros que no
# son ceros. Para que un dato no llegue, se quita la sesion entera.
PANELES_SESION = {
    "resumen": {"visitas_dia": "Visitas por día", "centros": "Visitas por centro",
                "semana": "Patrón semanal", "duracion": "Duración de la visita"},
    "venta_consumo": {"recaudacion": "Recaudación por mes", "ciego": "Efectivo sin telemetría",
                      "carga": "Reposición del periodo"},
    "servicio": {"merma": "Merma por motivo", "merma_art": "Caducidad por artículo"},
    "disponibilidad": {"sat": "Disponibilidad y averías", "reincidentes": "Máquinas reincidentes"},
    "instalaciones": {"censo": "Lo que hay instalado", "altas": "Altas recientes",
                      "incidencias": "Instalaciones a medias",
                      "inc_detalle": "Instalaciones a medias, una tabla por clase"},
}
PANELES = {p for d in PANELES_SESION.values() for p in d}


def paneles_ocultos(perfil):
    """Los paneles de /panel/ que este perfil no ve. Solo ids del catalogo."""
    pedidos = perfil.get("paneles_ocultos")
    if not isinstance(pedidos, list):
        return []
    return [p for d in PANELES_SESION.values() for p in d if p in pedidos]


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
# el informe general operativo (docs/51)
# ----------------------------------------------------------------------
# Que bloque del panel pide cada cuadrado, en el orden de la pagina. Es la
# misma tijera que el panel y la serie: un perfil que no ve la SAT en el panel
# tampoco ve aqui el cuadrado de averias. Los almacenes son nuestro stock
# (`inventario.existencias`, CAMPOS_INTERNOS): solo direccion y administracion.
CUADRADOS = (
    ("rutas", "servicio"),
    ("averias", "sat"),
    # Las devoluciones de dinero, sacadas de incidencias (docs/57): tambien SAT.
    ("devoluciones", "sat"),
    ("almacenes", "inventario"),
    ("furgonetas", "servicio"),
    ("pdvs", "instalaciones"),
    ("ventas", "dinero"),
    ("reposiciones", "servicio"),
    ("telemetria", "instalaciones"),
    # Tarifas contra venta real (docs/52): es configuracion de la maquina, como
    # la tarifa que falta en el bloque de instalaciones.
    ("tarifas", "instalaciones"),
    # Revision de clientes (docs/59): sin planograma, sin tarifa y precio
    # distinto, maquina a maquina. Tambien configuracion de la maquina.
    ("revision", "instalaciones"),
    # Utilizo (docs/60): cuanto usa VenCloud cada persona. Es lo que hace la
    # gente, no un cliente: solo direccion para arriba y sin ambito.
    ("utilizo", "instalaciones"),
)

SOLO_DIRECCION = ("almacenes", "utilizo")
# Y los que solo ve un perfil sin ambito: son de toda la empresa.
SIN_AMBITO = ("utilizo",)

# Como se llama cada cuadrado en la pagina y en la consola.
NOMBRE_CUADRADO = {
    "rutas": "Rutas", "averias": "Incidencias", "devoluciones": "Devoluciones",
    "almacenes": "Almacenes", "furgonetas": "Furgonetas", "pdvs": "Puntos de venta activos",
    "ventas": "Ventas", "reposiciones": "Reposiciones", "telemetria": "Telemetría",
    "tarifas": "Tarifas", "revision": "Revisión clientes", "utilizo": "Utilizo",
}

# Las tablas (y graficos) de la pagina de cada cuadrado, en el orden de la
# pagina (docs/61). En la consola solo se eligen las de las paginas con mas de
# una: en las demas, quitar la tabla es quitar el cuadrado. Todas llevan su
# estrella de preferidos (docs/62). id: nombre.
TABLAS = {
    "rutas": {
        "rutas": "Visitas por ruta",
        "estado": "Estado de las visitas",
        "maquinas": "Máquinas no visitadas",
        "delegaciones": "Por delegación",
        "festivos": "Festivos por delegación",
    },
    "averias": {
        "zonas": "Total de incidencias por zona",
        "tecnicas": "Los 10 centros con más averías técnicas",
        "abiertas": "Lista de incidencias y su ficha",
    },
    "devoluciones": {
        "meses": "Devoluciones por mes y canal",
        "canal": "Por canal y por origen",
        "zonas": "Por zona y delegación",
        "centros": "Los 15 centros con más devoluciones",
        "maquinas": "Las 15 máquinas con más devoluciones",
        "tecnicos": "Por técnico",
        "pendientes": "Devoluciones sin cerrar",
    },
    "furgonetas": {
        "vehiculos": "Furgonetas con visitas",
        "sin_vehiculo": "Visitas sin vehículo",
        "delegaciones": "Por delegación",
        "dias": "Furgonetas activas, día a día",
    },
    # Las paginas de una sola tabla: en la consola van con su cuadrado, pero la
    # tabla tiene su estrella de preferidos como las demas.
    "almacenes": {"productos": "Productos de los almacenes"},
    "telemetria": {"maquinas": "Máquinas por sistema de telemetría"},
    "tarifas": {"centros": "Tarifas por centro"},
    "utilizo": {"uso": "Uso de VenCloud por usuario"},
    "revision": {
        "planograma": "Sin planograma",
        "tarifa": "Sin tarifa",
        "precio": "Precio distinto",
        "creados": "Planogramas creados",
        "usuarios": "García y Marcos",
    },
}


def con_usuario(perfil, usuario):
    """El perfil de la sesion con lo que el administrador le quito a ESTE usuario.

    El usuario hereda los cuadrados y las tablas de su perfil, y el
    administrador le puede quitar los que quiera (docs/61). Quitar, nunca dar:
    lo que el perfil no ve, el usuario tampoco, por mucho que se marque. Se
    guarda lo que se le QUITA, como `cuadro_ocultas`: un cuadrado nuevo le sale
    sin tener que tocar a cada usuario. Devuelve una copia: el perfil leido no
    se toca.
    """
    out = dict(perfil)
    out["cuadrados_ocultos"] = limpia_restricciones(usuario)["cuadrados_ocultos"]
    out["tablas_ocultas"] = _tablas_validas(usuario.get("tablas_ocultas"))
    return out


def _tablas_validas(tablas):
    """{cuadrado: [tablas]} con solo cuadrados y tablas que existen, en el
    orden de la pagina, y sin los cuadrados que se quedan vacios."""
    tablas = tablas if isinstance(tablas, dict) else {}
    out = {}
    for c in TABLAS:
        pedidas = tablas.get(c)
        pedidas = {x for x in pedidas if isinstance(x, str)} if isinstance(pedidas, list) else set()
        ts = [t for t in TABLAS[c] if t in pedidas]
        if ts:
            out[c] = ts
    return out


def limpia_restricciones(d):
    """Lo que la consola manda de un usuario, con solo ids que existen."""
    pedidos = d.get("cuadrados_ocultos")
    pedidos = {x for x in pedidos if isinstance(x, str)} if isinstance(pedidos, list) else set()
    return {"cuadrados_ocultos": [c for c in NOMBRE_CUADRADO if c in pedidos],
            "tablas_ocultas": _tablas_validas(d.get("tablas_ocultas"))}


def cuadrados_de(perfil):
    """Los cuadrados que ve este perfil, en el orden de la pagina.

    Con `con_usuario` delante, los de este usuario: los de su perfil menos los
    que el administrador le quito.
    """
    necesarios = bloques_de(perfil)
    tipo = perfil.get("tipo", "cliente")
    out = [c for c, bloque in CUADRADOS if bloque in necesarios]
    if nivel_de(tipo) < NIVEL["direccion"]:
        out = [c for c in out if c not in SOLO_DIRECCION]
    ambito = perfil.get("ambito") or {}
    if any(ambito.get(k) for k in ("clientes", "centros", "delegaciones")):
        out = [c for c in out if c not in SIN_AMBITO]
    quitados = set(perfil.get("cuadrados_ocultos") or [])
    return [c for c in out if c not in quitados]


def tablas_ocultas(perfil, cuadrado):
    """Las tablas de la pagina de ese cuadrado que este usuario no ve."""
    return set((perfil.get("tablas_ocultas") or {}).get(cuadrado) or []) & set(TABLAS.get(cuadrado, ()))


def tablas_visibles(perfil, cuadrado):
    """Las que si ve, en el orden de la pagina."""
    fuera = tablas_ocultas(perfil, cuadrado)
    return [t for t in TABLAS.get(cuadrado, ()) if t not in fuera]


# Lo que solo usa una tabla, y por eso no sale del servidor si esa tabla se
# quita. Lo que comparten varias (las filas de incidencias, de las que la
# pagina saca todos sus graficos) no se puede quitar sin dejar a las demas con
# ceros que no son ceros: la tabla no se dibuja, pero sus filas siguen
# llegando para las que si se ven. Cada entrada: (tabla, donde, claves); donde
# es "raiz" (el fichero), "dias" (cada dia de dias) o "filas:<lista>" (cada
# fila de esa lista).
_SOLO_DE_UNA = {
    "rutas": (
        ("maquinas", "dias", ("visitas",)),
        ("festivos", "raiz", ("control_festivos",)),
    ),
    "averias": (
        # La ficha de una abierta: el texto, la ubicacion y el punto de venta.
        ("abiertas", "filas:incidencias", ("tx", "u", "p")),
    ),
    "furgonetas": (
        ("vehiculos", "dias", ("vehiculos",)),
        ("sin_vehiculo", "dias", ("sin_vehiculo",)),
    ),
    "revision": (
        ("planograma", "raiz", ("sin_planograma",)),
        ("tarifa", "raiz", ("sin_tarifa",)),
        ("precio", "raiz", ("precio_distinto",)),
        ("creados", "raiz", ("creados", "creados_desde", "sin_usuario")),
        ("usuarios", "raiz", ("actividad",)),
    ),
}


def hay_recorte(cuadrado, perfil):
    """Si a este usuario hay que quitarle algo del fichero de ese cuadrado."""
    fuera = tablas_ocultas(perfil, cuadrado)
    return any(x[0] in fuera for x in _SOLO_DE_UNA.get(cuadrado, ()))


def recorta_tablas(cuadrado, datos, perfil):
    """El fichero de la pagina de un cuadrado sin lo que solo usan sus tablas quitadas.

    Con todas las tablas a la vista sale el mismo objeto, sin copiar. Si no, una
    copia: el fichero leido no se toca.
    """
    fuera = tablas_ocultas(perfil, cuadrado)
    reglas = [x for x in _SOLO_DE_UNA.get(cuadrado, ()) if x[0] in fuera]
    if not reglas:
        return datos
    out = dict(datos)
    out["tablas_ocultas"] = sorted(fuera)
    for _, donde, claves in reglas:
        if donde == "raiz":
            for k in claves:
                out.pop(k, None)
        elif donde == "dias":
            out["dias"] = {f: ({k: v for k, v in d.items() if k not in claves}
                               if isinstance(d, dict) else d)
                           for f, d in (out.get("dias") or {}).items()}
        elif donde.startswith("filas:"):
            lista = donde.split(":", 1)[1]
            out[lista] = [({k: v for k, v in f.items() if k not in claves}
                           if isinstance(f, dict) else f)
                          for f in (out.get(lista) or [])]
    return out


def recorta_operativo(datos, perfil):
    """El fichero del informe operativo con los cuadrados que el perfil ve.

    Lo que no ve no sale de aqui: ni en el dia, ni en la foto.
    """
    ve = cuadrados_de(perfil)
    out = {k: datos.get(k) for k in ("generado", "ultimo_dia", "umbrales", "_nota")}
    out["cuadrados"] = ve
    out["dias"] = {f: {c: v for c, v in (d or {}).items() if c in ve}
                   for f, d in (datos.get("dias") or {}).items()}
    out["foto"] = {c: v for c, v in (datos.get("foto") or {}).items() if c in ve}
    return out


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


# ----------------------------------------------------------------------
# los preferidos (docs/62)
# ----------------------------------------------------------------------
ANCHOS = ("media", "entera")
ALTOS = ("bajo", "medio", "todo")
MAX_PREFERIDOS = 40


def preferidos_validos(lista, perfil):
    """Las tablas preferidas de un usuario que existen y que puede ver hoy.

    Lo que guardo antes de que se le quitara un cuadrado o una tabla no sale:
    la estrella no abre nada que el administrador haya cerrado. Sin repetidas,
    en el orden que eligio, con su ancho y su alto.
    """
    ve = {c: set(tablas_visibles(perfil, c)) for c in cuadrados_de(perfil)}
    out, vistos = [], set()
    for x in lista if isinstance(lista, list) else []:
        if not isinstance(x, dict):
            continue
        c, t = x.get("c"), x.get("t")
        if not isinstance(c, str) or not isinstance(t, str) or t not in ve.get(c, ()) or (c, t) in vistos:
            continue
        vistos.add((c, t))
        out.append({"c": c, "t": t,
                    "ancho": x.get("ancho") if x.get("ancho") in ANCHOS else "media",
                    "alto": x.get("alto") if x.get("alto") in ALTOS else "medio"})
        if len(out) >= MAX_PREFERIDOS:
            break
    return out
