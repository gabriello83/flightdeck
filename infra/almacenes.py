"""
Los almacenes por dentro: que producto hay en cada uno, con su foto, cuantas
unidades lleva cada pack y cada caja, su codigo de barras de la unidad, y si ya
esta por debajo del 15 % de lo que se compro la ultima vez (docs/54).

Lo pidio Gabriele el 15 de octubre de 2026, para el cuadrado de almacenes del
informe operativo, que hasta entonces no llevaba a ninguna parte.

DE DONDE SALE LA EXISTENCIA. No del cierre mensual (C9/C10) solo: es de hace
un mes y para avisar de que algo se acaba no sirve. Cada movimiento de almacen
(C1, `stocks.diarmovalm`) trae la existencia que deja (`existen`), calculada
por VenCloud. Ordenados por fecha, la cadena cuadra en el 95 % de los pasos, y
lo que no cuadra son sobre todo inventarios (IN), que fijan la existencia en
vez de sumarle (comprobado con septiembre de 2026: 62.867 de 66.016). Asi que la
existencia de hoy es la del ULTIMO movimiento de cada producto en cada almacen.
Un producto que no se ha movido en toda la ventana se queda con la cantidad del
ultimo cierre; si hay las dos cosas, manda la mas reciente.

LA ULTIMA COMPRA es el ultimo movimiento de tipo CO (entrada por albaran de
compra: «Albarán de compra: ...», «Proveedor: BIMBO»), en unidades, como la
existencia. Es lo que llego al almacen; el pedido de compra en si no se baja.

LO QUE TRAE EL MAESTRO DE ARTICULOS (M8 · EXT_MAESTRO_ARTICULOS, sin parametros): las
unidades por pack y por caja (`unidpack`, `unidcaja`) y los codigos de barras
(`stocks.articuloscodequivalentes`), cada uno con la cantidad que representa.
Un codigo con cantidad 1 es el de la UNIDAD; el de cantidad 24, el de una caja
de 24. Eso es lo que se deduce del modelo, y el maestro trae el dato en bruto
para poder comprobarlo con el primer volcado. Mientras el informe no exista,
la pagina lo dice en vez de enseñar los productos como si no tuvieran codigo.

Las fotos (M9 · EXT_MAESTRO_ARTICULOS_FOTOS) vienen en base64 y se guardan una vez
para todos en cabina/_articulos/fotos/; quien puede ver cada una lo dice el
fichero de su perfil, que solo cita las de los productos de sus almacenes.
"""

import base64
import datetime
import hashlib
import re

import reglas as R

# Por debajo de esta fraccion de la ultima compra, el producto esta bajo minimo.
UMBRAL = 0.15
MOV_COMPRA = "CO"

SIN_MAESTRO = ("Falta el maestro de artículos de VenCloud (M8 · EXT_MAESTRO_ARTICULOS): sin él no "
               "hay unidades por pack ni códigos de barras.")
SIN_FOTOS = ("Falta el informe de fotos de VenCloud (M9 · EXT_MAESTRO_ARTICULOS_FOTOS): los "
             "productos salen sin foto.")

# Lo que puede ir en la clave de S3 de una foto. Los codigos de VenCloud son
# numeros; lo demas se rechaza antes de tocar S3, en la noche y en la API.
CODIGO_VALIDO = re.compile(r"[A-Za-z0-9._-]{1,40}")


def _txt(x):
    return str(x if x is not None else "").strip()


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------
# lo que la noche va guardando de los movimientos
# ----------------------------------------------------------------------
class Existencias:
    """El ultimo movimiento y la ultima compra de cada producto en cada almacen.

    Se le dan los movimientos dia a dia, en cualquier orden: guarda solo lo mas
    reciente por (fecha, id), asi que no hay filas en memoria.
    """

    def __init__(self):
        self.ultimo = {}    # (almacen, cod) -> (orden, existencia, nombre)
        self.compra = {}    # (almacen, cod) -> (orden, cantidad, proveedor, documento)
        self.leidas = 0

    def come(self, filas):
        for m in filas:
            alm, cod = _txt(R.v(m, "almacen", "")), _txt(R.v(m, "cod_articulo", ""))
            if not alm or not cod:
                continue
            self.leidas += 1
            clave = (alm, cod)
            orden = (_txt(R.v(m, "fecha", ""))[:19].replace("T", " "), int(R.v(m, "id", 0) or 0))
            ex = _num(m.get("existencia_resultante"))
            if ex is not None and (clave not in self.ultimo or orden > self.ultimo[clave][0]):
                self.ultimo[clave] = (orden, ex, _txt(R.v(m, "articulo", "")))
            cant = _num(m.get("cantidad"))
            if R.v(m, "tipo_mov", "") == MOV_COMPRA and cant and cant > 0 and \
                    (clave not in self.compra or orden > self.compra[clave][0]):
                self.compra[clave] = (orden, cant, _txt(R.v(m, "origen_destino", "")),
                                      _txt(R.v(m, "documento", "")))


def ultimo_cierre(balance_por_periodo):
    """Los elementos de almacen (tipo A) del ultimo cierre: {id: fila}, y su periodo."""
    periodos = sorted(p for p, filas in (balance_por_periodo or {}).items()
                      if any(R.v(b, "tipo_elemento") == "A" for b in filas))
    if not periodos:
        return {}, None
    anho, mes = periodos[-1]
    elementos = {R.v(b, "id"): b for b in balance_por_periodo[(anho, mes)]
                 if R.v(b, "tipo_elemento") == "A"}
    return elementos, f"{anho}-{int(mes):02d}"


def dias_del_cierre(elementos):
    """Los dias en que se guardo el detalle (C10) de esos elementos."""
    out = set()
    for b in elementos.values():
        f = _txt(R.v(b, "fecha", ""))[:10]
        try:
            out.add(datetime.date.fromisoformat(f))
        except ValueError:
            continue
    return sorted(out)


def cantidades_del_cierre(elementos, filas_detalle):
    """{(almacen, cod): (fecha del cierre, cantidad, nombre)} del detalle C10."""
    out = {}
    for p in filas_detalle or []:
        b = elementos.get(R.v(p, "elemento_id"))
        if b is None:
            continue
        alm, cod = _txt(R.v(b, "almacen", "")), _txt(R.v(p, "cod_articulo", ""))
        if not alm or not cod:
            continue
        out[(alm, cod)] = (_txt(R.v(b, "fecha", ""))[:19], float(_num(p.get("cantidad")) or 0),
                           _txt(R.v(p, "articulo", "")))
    return out


# ----------------------------------------------------------------------
# el maestro de articulos
# ----------------------------------------------------------------------
def codigos(texto):
    """'8410000000016|1|0;8410000000023|24|0' -> [{'codigo': ..., 'cantidad': 1}, ...]

    El informe los junta en una columna (codigo|cantidad|tipo, separados por
    punto y coma) para no repetir el articulo una vez por codigo.
    """
    out = []
    for trozo in _txt(texto).split(";"):
        partes = [x.strip() for x in trozo.split("|")]
        if not partes or not partes[0]:
            continue
        c = _num(partes[1]) if len(partes) > 1 else None
        out.append({"codigo": partes[0][:40], "cantidad": int(c) if c is not None else None})
    return out


class Articulos:
    def __init__(self, filas):
        self.de = {}
        for a in filas or []:
            cod = _txt(R.v(a, "cod_articulo", ""))
            if not cod:
                continue
            todos = codigos(R.v(a, "codigos_barras", ""))
            unidad = [c["codigo"] for c in todos if c["cantidad"] == 1]
            otros = [c for c in todos if c["cantidad"] != 1]
            pack, caja = _num(R.v(a, "unid_pack", 0)), _num(R.v(a, "unid_caja", 0))
            self.de[cod] = {
                "categoria": _txt(R.v(a, "categoria", ""))[:60],
                # 0 es "sin dato" en este modelo (reglas.v): no hay packs de cero.
                "unid_pack": int(pack) if pack else None,
                "unid_caja": int(caja) if caja else None,
                "ean_unidad": unidad,
                "otros_codigos": otros,
                "ean_oficial": _txt(R.v(a, "ean_oficial", ""))[:40] or None,
            }

    def __bool__(self):
        return bool(self.de)

    def get(self, cod):
        return self.de.get(cod)


def _tipo_imagen(b):
    if b[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if b[:4] == b"GIF8":
        return "image/gif"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "image/webp"
    if b[:2] == b"BM":
        return "image/bmp"
    return None


def fotos(filas):
    """{cod: (bytes, tipo)} de las filas del informe de fotos. Lo que no es una
    imagen reconocible se descarta: el navegador no la pintaria."""
    out = {}
    for f in filas or []:
        cod = _txt(R.v(f, "cod_articulo", ""))
        b64 = R.v(f, "foto", "")
        if not cod or not b64 or not CODIGO_VALIDO.fullmatch(cod):
            continue
        try:
            datos = base64.b64decode(re.sub(r"\s+", "", str(b64)), validate=True)
        except Exception:
            continue
        tipo = _tipo_imagen(datos)
        if tipo:
            out[cod] = (datos, tipo)
    return out


def huella(datos):
    return hashlib.sha1(datos).hexdigest()


# ----------------------------------------------------------------------
# el fichero de un perfil
# ----------------------------------------------------------------------
def almacenes_del_perfil(nombres, rutas, ambito):
    """Que almacenes ve un perfil: {nombre: delegacion}, o un motivo si ninguno.

    La misma regla que el cuadrado (operativo.almacenes): un almacen es de una
    delegacion, y la delegacion sale del maestro de rutas.
    """
    deleg_de = {}
    for r in rutas or []:
        a = _txt(R.v(r, "almacen", ""))
        if a and R.v(r, "delegacion", ""):
            deleg_de.setdefault(a, str(R.v(r, "delegacion")))
    delegaciones = [str(d) for d in (ambito or {}).get("delegaciones") or []]
    acotado = bool((ambito or {}).get("clientes") or (ambito or {}).get("centros"))
    if acotado and not delegaciones:
        return None, ("Los almacenes son de una delegación: este perfil está acotado por "
                      "clientes o centros y no tiene almacenes propios.")
    out = {}
    for n in nombres:
        d = deleg_de.get(n, "")
        if delegaciones and d not in delegaciones:
            continue
        out[n] = d
    return out, None


def producto(cod, existencia, compra, articulos, con_foto):
    """Una fila de la pagina. `existencia`: (cuando, cantidad, nombre, de_donde)."""
    cuando, cant, nombre, origen = existencia
    p = {"cod": cod, "nombre": nombre[:80], "existencias": round(cant, 2),
         "de": origen, "fecha": cuando[:10]}
    if compra:
        (fc, _), cc, prov, doc = compra
        p["compra"] = {"fecha": fc[:10], "cantidad": round(cc, 2),
                       "proveedor": prov.replace("Proveedor:", "").strip()[:60],
                       "documento": doc[:80]}
        p["bajo"] = cant < UMBRAL * cc
        # Una existencia negativa es un descuadre de VenCloud: esta bajo minimo,
        # pero un «-1.083 %» no le dice nada a nadie.
        p["pct"] = round(100 * cant / cc, 1) if cant >= 0 else None
    if articulos:
        a = articulos.get(cod)
        if a is None:
            p["fuera_del_maestro"] = True
        else:
            p.update({k: a[k] for k in ("categoria", "unid_pack", "unid_caja",
                                       "ean_unidad", "otros_codigos", "ean_oficial")})
    p["foto"] = cod in con_foto
    return p


def fichero(existencias, cierre, periodo_cierre, visibles, articulos, con_foto, hoy):
    """El fichero de almacenes de un perfil.

    `cierre`: lo de cantidades_del_cierre. `visibles`: {almacen: delegacion}.
    `articulos`: un Articulos o None si el maestro no ha llegado. `con_foto`: los
    codigos con foto guardada.
    """
    claves = set(existencias.ultimo) | set(cierre)
    lista = []
    for alm in sorted(visibles):
        prods = []
        for (a, cod) in sorted(k for k in claves if k[0] == alm):
            mov = existencias.ultimo.get((a, cod))
            cie = cierre.get((a, cod))
            # Manda lo mas reciente: el ultimo movimiento, o el cierre si es
            # posterior (un inventario de cierre fija la cantidad).
            if mov and (not cie or mov[0][0] >= cie[0]):
                ex = (mov[0][0], mov[1], mov[2] or (cie[2] if cie else ""), "movimiento")
            else:
                ex = (cie[0], cie[1], cie[2], "cierre")
            compra = existencias.compra.get((a, cod))
            # Lo que no hay ni se ha comprado en la ventana es historia del
            # maestro, no un producto del almacen.
            if not ex[1] and not compra:
                continue
            prods.append(producto(cod, ex, compra, articulos, con_foto))
        if not prods:
            continue
        prods.sort(key=lambda p: (not p.get("bajo"), p["nombre"]))
        lista.append({"almacen": alm[:60], "delegacion": visibles[alm],
                      "resumen": resumen(prods, articulos), "productos": prods})
    total = resumen([p for x in lista for p in x["productos"]], articulos)
    total["almacenes"] = len(lista)
    return {
        "generado": datetime.datetime.utcnow().isoformat() + "Z",
        "hoy": hoy.isoformat() if hasattr(hoy, "isoformat") else str(hoy),
        "umbral_pct": round(UMBRAL * 100),
        "periodo_cierre": periodo_cierre,
        "maestro": bool(articulos),
        "fotos": bool(con_foto),
        "avisos": ([] if articulos else [SIN_MAESTRO]) + ([] if con_foto else [SIN_FOTOS]),
        "total": total,
        "almacenes": lista,
    }


def resumen(prods, articulos):
    r = {"productos": len(prods),
         "bajo_minimo": sum(1 for p in prods if p.get("bajo")),
         "sin_compra": sum(1 for p in prods if "compra" not in p),
         "sin_foto": sum(1 for p in prods if not p["foto"])}
    if articulos:
        r["sin_codigo_unidad"] = sum(1 for p in prods
                                     if not p.get("fuera_del_maestro") and not p.get("ean_unidad"))
        r["sin_pack"] = sum(1 for p in prods
                            if not p.get("fuera_del_maestro") and not p.get("unid_pack"))
    return r


def fotos_citadas(fich):
    return {p["cod"] for a in fich.get("almacenes", []) for p in a["productos"] if p.get("foto")}
