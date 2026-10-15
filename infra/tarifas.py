"""
Tarifas: si cada maquina cobra lo que dice la tarifa de su cliente (docs/52).

Lo pidio Gabriele el 14 de octubre de 2026: un cuadrado en el informe general
operativo con el porcentaje de productos cuyo precio de venta real coincide con
la tarifa, y debajo el detalle por delegacion, por centro y por producto, con un
Excel por centro para el responsable de la delegacion.

LAS REGLAS, TAL COMO LAS FIJO GABRIELE:

  · Se cuenta cada producto de cada maquina, no las unidades vendidas.
  · Coincide si el precio cobrado es EXACTAMENTE el de la tarifa, medio de pago
    por medio de pago: efectivo contra efectivo, tarjeta privada contra tarjeta
    privada, tarjeta de credito contra tarjeta de credito.
  · Cuenta la venta posterior al ultimo cambio de esa tarifa: un precio que ya
    se corrigio no es un error. Y como mucho la de los ultimos seis meses.
  · Los productos son los repuestos en la maquina en los ultimos seis meses.
  · Lo que no se puede controlar no entra en el porcentaje: un producto sin
    venta electronica despues del cambio (`sin_dato`) o sin tarifa
    (`sin_tarifa`) se cuenta aparte y se dice cuantos son.

DE DONDE SALE CADA PRECIO:

  · La tarifa: el maestro EXT_TARIFAS (docs/17, M7), con todas las lineas de
    precio de VenCloud y el nivel del que cuelga cada una.
  · El precio cobrado: la telemetria (A12), venta a venta, y donde no la hay, el
    audit de la visita (A11), que da importe y numero de ventas por medio de
    pago. La telemetria manda: es la venta de verdad, una a una; el audit es una
    media desde la lectura anterior.
  · Se compara el ULTIMO precio cobrado: es el que la maquina tiene puesto hoy.

LOS NIVELES, COMO LOS LLAMA GABRIELE (14-oct-2026). Hay precios sueltos por
producto puestos en un punto de venta, en un centro o en un cliente (y en un
grupo de clientes), y hay TARIFAS ESTANDAR: las tablas con nombre del menu
«Gestion de Tarifas Vending Estandar» de VenCloud (`tarifasvending`, «AIRBUS
OPERATIONS SLU», «ALHAMBRA PUBLICO»...), que se definen aparte y luego se
asignan a un punto de venta, un centro o un cliente. Un precio que sale de una
de esas tablas es de nivel «estandar», y se dice ademas a quien esta asignada.

QUE PRECIO RIGE EN CADA MAQUINA. Lo decide VenCloud con su funcion
`vending.getprecioscanal`, leida el 15-oct-2026 con EXT_SONDA_PRECIOS (docs/17,
M7Z), y el orden de `ORDEN` es el suyo, paso a paso:

  1. El punto de venta marcado de venta gratuita (`pdvs.vtagratuita`): todo a 0.
  2. La maquina con precios en canales (`maquinas.preciosencanales`): el precio
     guardado en cada canal, sin mirar ninguna tarifa.
  3. El precio suelto del ARTICULO: punto de venta, centro, cliente, grupo.
  4. El precio suelto de su CATEGORIA: punto de venta, centro, cliente, grupo.
     Toda la busqueda por articulo va antes que cualquiera por categoria.
  5. La tarifa estandar asignada al punto de venta.
  6. La tarifa estandar asignada al cliente.

  Y lo que NO usa: la tarifa estandar asignada al CENTRO
  (`clientescentros.tarifavendingid`; en el censo de octubre no la tiene
  ninguna maquina), los precios de la ficha del centro y del cliente
  (`clientescentrostarifas*`, `clientestarifasvending`) ni el precio suelto que
  no cuelga de nadie. El precio de la ficha del articulo y el de su categoria
  solo entrarian con `usatarifavendingglobal`, que en Serunion esta apagado: sin
  nada de lo anterior, VenCloud pone 0, y aqui es «sin tarifa».

  Una maquina con planograma por categorias (`planogporcategorias`) solo mira
  el paso 4, con la categoria puesta en el canal y no la del articulo.

POR QUE HAY UN ESTADO QUE SE GUARDA DE UNA NOCHE A OTRA. Los agregados leen 120
dias y aqui hacen falta seis meses. En vez de leer 180 dias de telemetria cada
noche (once millones de ventas), se guarda lo poco que hace falta —la ultima
carga de cada producto en cada maquina y el ultimo precio cobrado por medio de
pago— y cada noche se le suma lo leido. Un relleno historico de agregados
tambien lo alimenta, y asi se arranca.

Sin dependencias: se prueba con `python3 infra/test_tarifas.py`.
"""

import datetime
import re

import reglas as R

# Seis meses, como pidio Gabriele.
DIAS_VENTANA = 183

# El medio de pago de la telemetria (`lineaprecio`, docs/04 informe 37 y
# docs/06): 1 tarjeta de credito, 2 efectivo, 3 prepago, que es la tarjeta
# privada. Lo demas (hay un 1 % con 11) no se sabe que es y no se compara.
MEDIO_TELEMETRIA = {1: "tc", 2: "ef", 3: "tp"}
MEDIOS = ("ef", "tp", "tc")
NOMBRE_MEDIO = {"ef": "Efectivo", "tp": "Tarjeta privada", "tc": "Tarjeta de crédito"}

# Las columnas del audit de la visita, por medio de pago (A11).
AUDIT = {"ef": ("num_efectivo", "imp_efectivo"),
         "tp": ("num_t_privada", "imp_t_privada"),
         "tc": ("num_t_credito", "imp_t_credito")}

# Las recetas de bebida caliente (R01..R72) no se «reponen»: se cargan cafe,
# leche y vasos. Para que entren, una receta cuenta si se ha vendido.
RECETA = re.compile(r"^R\d+$")

NIVELES = ("gratuito", "maquina", "pdv", "centro", "cliente", "grupo", "estandar")
ASIGNADA = {"pdv": "al punto de venta", "cliente": "al cliente"}
NOMBRE_NIVEL = {"gratuito": "Venta gratuita", "maquina": "Precio en la máquina",
                "pdv": "Punto de venta", "centro": "Centro", "cliente": "Cliente",
                "grupo": "Grupo de clientes", "estandar": "Estándar"}

# El orden en que VenCloud busca el precio (getprecioscanal, ver el docstring).
# Los dos primeros pasos, venta gratuita y precio en canales, van antes y
# aparte: dependen del punto de venta y de la maquina, no del articulo.
ORDEN = (
    ("pdv", "productos"), ("centro", "productos"),
    ("cliente", "productos"), ("grupo", "productos"),
    ("pdv", "categorias"), ("centro", "categorias"),
    ("cliente", "categorias"), ("grupo", "categorias"),
    ("pdv", "tarifa"), ("cliente", "tarifa"),
)

SIN_MAESTRO = ("Falta el maestro de tarifas: el informe EXT_TARIFAS de VenCloud "
               "todavía no se descarga.")

# Coincide, no coincide, sin tarifa, sin dato.
ESTADOS = ("coincide", "no_coincide", "sin_tarifa", "sin_dato")


def _s(x):
    """Un codigo como texto: el censo trae numeros y el maestro texto."""
    if x is None:
        return ""
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    return str(x).strip()


def _precio(x):
    try:
        p = round(float(x), 2)
    except (TypeError, ValueError):
        return None
    return p if p > 0 else None


def _fecha(x):
    s = str(x or "")[:10]
    # El 01/01/1900 de VenCloud es «nunca».
    return s if len(s) == 10 and not s.startswith("1900") else ""


def _mas_nueva(actual, nueva):
    return actual is None or nueva[0] >= actual[0]


# ----------------------------------------------------------------------
# lo que se guarda de una noche a otra
# ----------------------------------------------------------------------
class Observador:
    """La ultima carga de cada producto y el ultimo precio cobrado.

    `cargas`  {"matricula|articulo": "AAAA-MM-DD"}
    `ventas`  {"matricula|articulo|medio|fuente": ["AAAA-MM-DD hh:mm:ss", precio]}
    `fuente`  "t" telemetria, "a" audit de la visita.
    """

    def __init__(self, estado=None):
        e = estado or {}
        self.cargas = dict(e.get("cargas") or {})
        self.ventas = {k: tuple(v) for k, v in (e.get("ventas") or {}).items()}
        self.sin_articulo = 0
        self.medio_desconocido = 0

    def _venta(self, mat, art, medio, fuente, cuando, precio):
        k = f"{mat}|{art}|{medio}|{fuente}"
        nueva = (cuando, precio)
        if _mas_nueva(self.ventas.get(k), nueva):
            self.ventas[k] = nueva

    def _carga(self, mat, art, dia):
        k = f"{mat}|{art}"
        if dia > self.cargas.get(k, ""):
            self.cargas[k] = dia
            self._por_maquina = None

    def come_cargas(self, filas):
        """Lineas CM de la reposicion. Lo que va en los carriles de una caliente
        (azucar, vasos, cafe) no es un producto con precio de venta."""
        for l in filas:
            if R.v(l, "tipo_linea") != "CM" or R.es_consumible_de_cafe(l):
                continue
            mat, art, dia = _s(R.v(l, "matricula", "")), _s(R.v(l, "cod_articulo", "")), _fecha(R.v(l, "fecha", ""))
            if mat and art and dia:
                self._carga(mat, art, dia)

    def come_telemetria(self, filas):
        for t in filas:
            mat, art = _s(R.v(t, "matricula", "")), _s(R.v(t, "cod_articulo", ""))
            if not art:
                self.sin_articulo += 1
                continue
            try:
                medio = MEDIO_TELEMETRIA.get(int(R.v(t, "linea_precio", 0)))
            except (TypeError, ValueError):
                medio = None
            if medio is None:
                self.medio_desconocido += 1
                continue
            cuando = str(R.v(t, "fecha_venta", ""))[:19]
            try:
                precio = round(float(R.v(t, "precio", 0) or 0), 2)
            except (TypeError, ValueError):
                continue
            if mat and cuando:
                self._venta(mat, art, medio, "t", cuando, precio)
                if RECETA.match(art):
                    self._carga(mat, art, cuando[:10])

    def come_audit(self, filas):
        """El audit de la visita: el precio es importe entre numero de ventas.
        Si en ese tramo cobro dos precios distintos sale una media que no es
        ninguno de los dos, y no coincidira: es lo que hay que mirar."""
        for v in filas:
            mat, art = _s(R.v(v, "matricula", "")), _s(R.v(v, "cod_articulo", ""))
            cuando = str(R.v(v, "fecha_visita", ""))[:19]
            if not (mat and art and cuando):
                continue
            for medio, (cn, ci) in AUDIT.items():
                try:
                    n, imp = float(R.v(v, cn, 0) or 0), float(R.v(v, ci, 0) or 0)
                except (TypeError, ValueError):
                    continue
                if n > 0:
                    self._venta(mat, art, medio, "a", cuando, round(imp / n, 4))
            if RECETA.match(art) and float(R.v(v, "num_total", 0) or 0) > 0:
                self._carga(mat, art, cuando[:10])

    def poda(self, hoy):
        """Lo de hace mas de seis meses ya no se mira nunca."""
        corte = (hoy - datetime.timedelta(days=DIAS_VENTANA)).isoformat()
        self.cargas = {k: d for k, d in self.cargas.items() if d >= corte}
        self.ventas = {k: v for k, v in self.ventas.items() if v[0][:10] >= corte}
        self._por_maquina = None

    def estado(self):
        return {"cargas": self.cargas, "ventas": {k: list(v) for k, v in self.ventas.items()}}

    def productos_de(self, matricula, corte):
        """Los articulos repuestos (o vendidos, si son recetas) desde `corte`."""
        if getattr(self, "_por_maquina", None) is None:
            self._por_maquina = {}
            for k, d in self.cargas.items():
                mat, art = k.split("|", 1)
                self._por_maquina.setdefault(mat, {})[art] = d
        return sorted(a for a, d in self._por_maquina.get(matricula, {}).items() if d >= corte)

    def ultima_carga(self, matricula, articulo):
        return self.cargas.get(f"{matricula}|{articulo}", "")

    def ultimo_precio(self, matricula, articulo, medio, desde):
        """El ultimo precio cobrado desde `desde`: telemetria si la hay."""
        for fuente in ("t", "a"):
            x = self.ventas.get(f"{matricula}|{articulo}|{medio}|{fuente}")
            if x and x[0][:10] >= desde:
                return {"precio": x[1], "fecha": x[0][:10],
                        "fuente": "telemetria" if fuente == "t" else "audit"}
        return None


# ----------------------------------------------------------------------
# el maestro de tarifas
# ----------------------------------------------------------------------
class Tarifas:
    """EXT_TARIFAS, indexado para buscar el precio de un articulo en un sitio."""

    def __init__(self, filas):
        self.filas = len(filas or [])
        self.detalle = {}           # tarifa_id -> articulo -> linea
        self.nombre = {}            # tarifa_id -> (nombre, activa, fecha)
        self.sueltos = {}           # (origen, nivel, clave) -> articulo|categoria -> linea
        self.categoria_de = {}      # articulo -> categoria
        self.articulo = {}          # articulo -> nombre
        self.grupo_de = {}          # cod_cliente -> grupo_id
        self.maquina = {}           # matricula -> {"modo": "canal"|"planograma", "arts": {...}}
        self.gratuito = set()       # cod_pdv de venta gratuita
        self.subvencion = set()     # cod_pdv con subvencion en vigor
        for f in filas or []:
            o = R.v(f, "origen", "")
            linea = {"ef": _precio(R.v(f, "precio_ef", None)),
                     "tp": _precio(R.v(f, "precio_tp", None)),
                     "tc": _precio(R.v(f, "precio_tc", None)),
                     "tpdto": _precio(R.v(f, "precio_tpdto", None)),
                     "fecha": _fecha(R.v(f, "fecha_cambio", ""))}
            art, cat = _s(R.v(f, "cod_articulo", "")), _s(R.v(f, "cod_categoria", ""))
            if o == "tarifa":
                t = _s(R.v(f, "tarifa_id", ""))
                # VenCloud salta la linea de una tarifa estandar sin precio de
                # efectivo y sigue buscando.
                if t and art and R.v(f, "precio_ef", None) is not None:
                    linea["tarifa"] = _s(R.v(f, "tarifa", ""))
                    self.detalle.setdefault(t, {})[art] = linea
                if t:
                    self.nombre[t] = (_s(R.v(f, "tarifa", "")), R.v(f, "activa", True),
                                      linea["fecha"])
            elif o == "articulo":
                if art:
                    self.articulo[art] = _s(R.v(f, "articulo", ""))[:60]
                if art and cat:
                    self.categoria_de[art] = cat
            elif o == "cliente_grupo":
                c, g = _s(R.v(f, "cod_cliente", "")), _s(R.v(f, "grupo_id", ""))
                if c and g:
                    self.grupo_de[c] = g
            elif o == "canal":
                mat, modo = _s(R.v(f, "matricula", "")), R.v(f, "nivel", "")
                if not mat or modo not in ("canal", "planograma"):
                    continue
                m = self.maquina.setdefault(mat, {"modo": modo, "arts": {}})
                if art and art not in m["arts"]:
                    m["arts"][art] = dict(linea, categoria=cat)
            elif o == "pdv":
                pdv, que = _s(R.v(f, "cod_pdv", "")), R.v(f, "nivel", "")
                if pdv and que == "gratuito":
                    self.gratuito.add(pdv)
                elif pdv and que == "subvencion":
                    self.subvencion.add(pdv)
            elif o in ("productos", "categorias"):
                nivel = R.v(f, "nivel", "")
                clave = {"pdv": _s(R.v(f, "cod_pdv", "")), "centro": _s(R.v(f, "num_centro", "")),
                         "cliente": _s(R.v(f, "cod_cliente", "")),
                         "grupo": _s(R.v(f, "grupo_id", ""))}.get(nivel)
                que = cat if o == "categorias" else art
                # El precio suelto que no cuelga de nadie VenCloud no lo usa.
                if not clave or not que:
                    continue
                self.sueltos.setdefault((o, nivel, clave), {})[que] = linea

    def precio(self, articulo, sitio):
        """La linea de precio que rige y de donde sale, o None.

        `sitio`: {"matricula", "pdv", "centro", "cliente", "tarifa_pdv",
        "tarifa_cliente"} de la fila del censo. El orden es el de VenCloud.
        """
        if sitio.get("pdv") and sitio["pdv"] in self.gratuito:
            return {"ef": 0.0, "tp": 0.0, "tc": 0.0, "tpdto": None, "fecha": "",
                    "nivel": "gratuito", "origen": "gratuito"}
        maq = self.maquina.get(sitio.get("matricula", ""))
        if maq and maq["modo"] == "canal":
            linea = maq["arts"].get(articulo)
            if not linea:
                return None
            return dict(linea, nivel="maquina", origen="canal")
        claves = {"pdv": sitio.get("pdv", ""), "centro": sitio.get("centro", ""),
                  "cliente": sitio.get("cliente", ""),
                  "grupo": self.grupo_de.get(sitio.get("cliente", ""), "")}
        if maq:
            # Planograma por categorias: la categoria del canal, y nada mas.
            canal = maq["arts"].get(articulo) or {}
            cat, solo = canal.get("categoria", ""), "categorias"
        else:
            cat, solo = self.categoria_de.get(articulo, ""), None
        for nivel, origen in ORDEN:
            if solo and origen != solo:
                continue
            clave = claves[nivel]
            if not clave:
                continue
            if origen == "tarifa":
                t = sitio.get(f"tarifa_{nivel}", "")
                linea = self.detalle.get(t, {}).get(articulo) if t else None
                if linea:
                    # Una tarifa estandar: su nivel es «estandar», este donde
                    # este asignada; donde lo esta va en `asignada`.
                    return dict(linea, nivel="estandar", asignada=nivel, origen="tarifa",
                                tarifa_id=t)
                continue
            que = cat if origen == "categorias" else articulo
            linea = self.sueltos.get((origen, nivel, clave), {}).get(que) if que else None
            if linea:
                return dict(linea, nivel=nivel, origen=origen)
        return None

    def tarifa_asignada(self, sitio):
        """La tarifa estandar que VenCloud aplica: la del punto de venta, y si
        no tiene, la del cliente. La del centro no la usa."""
        for nivel in ("pdv", "cliente"):
            t = sitio.get(f"tarifa_{nivel}", "")
            if t:
                return {"nivel": nivel, "id": t, "nombre": (self.nombre.get(t) or ("",))[0]}
        return None


# ----------------------------------------------------------------------
# un producto de una maquina
# ----------------------------------------------------------------------
def compara(linea, obs, matricula, articulo, hoy):
    """El estado de un producto de una maquina, con lo que se ha comparado."""
    corte = (hoy - datetime.timedelta(days=DIAS_VENTANA)).isoformat()
    if not linea or not any(linea.get(m) is not None for m in MEDIOS):
        # Sin tarifa: se ensena lo que cobra, para que se pueda rellenar.
        venta = {m: obs.ultimo_precio(matricula, articulo, m, corte) for m in MEDIOS}
        return "sin_tarifa", {m: {"venta": v} for m, v in venta.items() if v}, corte
    desde = max(corte, linea.get("fecha") or "")
    medios, alguno, todos = {}, False, True
    for m in MEDIOS:
        t = linea.get(m)
        v = obs.ultimo_precio(matricula, articulo, m, desde)
        if t is None:
            # Ese medio no tiene precio en la tarifa: no se puede controlar.
            if v:
                medios[m] = {"venta": v, "tarifa": None}
            continue
        if not v:
            medios[m] = {"tarifa": t}
            continue
        validos = {t} | ({linea["tpdto"]} if m == "tp" and linea.get("tpdto") else set())
        ok = any(abs(v["precio"] - x) < 0.0005 for x in validos)
        medios[m] = {"tarifa": t, "venta": v, "ok": ok}
        alguno = True
        todos = todos and ok
    if not alguno:
        return "sin_dato", medios, desde
    return ("coincide" if todos else "no_coincide"), medios, desde


def cuenta(estados):
    c = {e: 0 for e in ESTADOS}
    for e in estados:
        c[e] += 1
    controlados = c["coincide"] + c["no_coincide"]
    c["controlados"] = controlados
    c["pct"] = round(100.0 * c["coincide"] / controlados, 1) if controlados else None
    return c


def _suma(a, b):
    for e in ESTADOS:
        a[e] = a.get(e, 0) + b.get(e, 0)
    a["controlados"] = a.get("coincide", 0) + a.get("no_coincide", 0)
    a["pct"] = round(100.0 * a["coincide"] / a["controlados"], 1) if a["controlados"] else None
    return a


# ----------------------------------------------------------------------
# un perfil
# ----------------------------------------------------------------------
def calcula(censo, tarifas, obs, hoy, semaforo=None):
    """El resumen del perfil y el detalle de cada centro.

    `censo`: las filas de EXT_INSTALACIONES del ambito del perfil.
    Devuelve (resumen, {num_centro: detalle}).
    """
    corte = (hoy - datetime.timedelta(days=DIAS_VENTANA)).isoformat()
    centros = {}
    for f in censo or []:
        if (R.es_centinela(f) or not R.cliente_vivo(f) or not R.centro_vivo(f)
                or not R.pdv_vivo(f) or not R.instalado(f)):
            continue
        num = _s(R.v(f, "num_centro", ""))
        mat = _s(R.v(f, "matricula", ""))
        if not num or not mat:
            continue
        sitio = {"matricula": mat, "pdv": _s(R.v(f, "cod_pdv", "")), "centro": num,
                 "cliente": _s(R.v(f, "cod_cliente", "")),
                 "tarifa_pdv": _s(R.v(f, "tarifa_vending_pdv", "") or ""),
                 "tarifa_cliente": _s(R.v(f, "tarifa_vending_cliente", "") or "")}
        c = centros.setdefault(num, {
            "num_centro": num, "centro": _s(R.v(f, "centro", "")),
            "cod_cliente": sitio["cliente"], "cliente": _s(R.v(f, "cliente", "")),
            "delegacion": _s(R.v(f, "delegacion", "")) or "Sin delegación",
            "maquinas": 0, "filas": [], "niveles": {n: 0 for n in NIVELES},
            "tarifas": {}})
        c["maquinas"] += 1
        asignada = tarifas.tarifa_asignada(sitio)
        if asignada:
            k = f"{asignada['nombre'] or asignada['id']} (asignada {ASIGNADA[asignada['nivel']]})"
            c["tarifas"][k] = c["tarifas"].get(k, 0) + 1
        for art in obs.productos_de(mat, corte):
            linea = tarifas.precio(art, sitio)
            estado, medios, desde = compara(linea, obs, mat, art, hoy)
            if linea:
                c["niveles"][linea["nivel"]] += 1
            c["filas"].append({
                "matricula": mat, "cod_pdv": sitio["pdv"],
                "ubicacion": _s(R.v(f, "ubicacion", ""))[:60],
                "cod_articulo": art, "articulo": tarifas.articulo.get(art, ""),
                "ultima_carga": obs.ultima_carga(mat, art),
                "nivel": linea["nivel"] if linea else None,
                "origen": linea["origen"] if linea else None,
                "tarifa": (linea.get("tarifa") or "") if linea else "",
                "asignada": (linea.get("asignada") or "") if linea else "",
                "cambio_tarifa": (linea.get("fecha") or "") if linea else "",
                "subvencion": sitio["pdv"] in tarifas.subvencion,
                "desde": desde, "medios": medios, "estado": estado})

    detalle, delegaciones = {}, {}
    total = {}
    for num, c in centros.items():
        cu = cuenta(r["estado"] for r in c["filas"])
        principal = max(NIVELES, key=lambda n: c["niveles"][n]) if any(c["niveles"].values()) else None
        fila = {"num_centro": num, "centro": c["centro"], "cliente": c["cliente"],
                "cod_cliente": c["cod_cliente"], "maquinas": c["maquinas"],
                "nivel": principal,
                "niveles": {n: k for n, k in c["niveles"].items() if k},
                "tarifas": [{"tarifa": t, "maquinas": n}
                            for t, n in sorted(c["tarifas"].items(), key=lambda x: -x[1])],
                **cu}
        if semaforo:
            fila["color"] = semaforo(cu["pct"])
        d = delegaciones.setdefault(c["delegacion"], {"delegacion": c["delegacion"], "centros": []})
        d["centros"].append(fila)
        _suma(total, cu)
        c["filas"].sort(key=lambda r: (ESTADOS.index(r["estado"]) if r["estado"] != "coincide" else 9,
                                       r["matricula"], r["cod_articulo"]))
        detalle[num] = {"num_centro": num, "centro": c["centro"], "cliente": c["cliente"],
                        "cod_cliente": c["cod_cliente"], "delegacion": c["delegacion"],
                        "resumen": fila, "filas": c["filas"]}
    lista = []
    for d in delegaciones.values():
        acu = {}
        for fila in d["centros"]:
            _suma(acu, fila)
        d.update(acu)
        if semaforo:
            d["color"] = semaforo(acu["pct"])
        d["centros"].sort(key=lambda x: (x["pct"] is None, x["pct"] if x["pct"] is not None else 0,
                                         x["centro"]))
        lista.append(d)
    lista.sort(key=lambda x: x["delegacion"])
    if not total:
        total = cuenta([])
    resumen = {"generado": datetime.datetime.utcnow().isoformat() + "Z",
               "desde": corte, "dias": DIAS_VENTANA, "total": total,
               "delegaciones": lista,
               "subvencion": ("Los puntos de venta con subvención en vigor van marcados: "
                              "si la máquina cobra el precio subvencionado, ahí no coincidirá.")}
    return resumen, detalle


def cuadrado(resumen, semaforo):
    """Lo que el informe general operativo ensena en el cuadrado."""
    t = resumen["total"]
    if not t["controlados"]:
        return {"sin_dato": "Ningún producto de este ámbito tiene a la vez tarifa y venta "
                            "electrónica después del último cambio.",
                "sin_tarifa": t["sin_tarifa"], "sin_dato_productos": t["sin_dato"]}
    return {"pct": t["pct"], "color": semaforo(t["pct"]), "coinciden": t["coincide"],
            "controlados": t["controlados"], "sin_tarifa": t["sin_tarifa"],
            "sin_dato_productos": t["sin_dato"], "desde": resumen["desde"]}
