"""
La telemetria de fuera: los ficheros de Nayax, Prodelfi y Nebula cruzados con
el censo de VenCloud (docs/52).

Lo pidio Gabriele el 14 de octubre de 2026. VenCloud dice que maquinas mandan
venta por telemetria y cuales mandan su lectura (DEX), pero no sabe cuales
DEBERIAN mandarla: eso lo saben los sistemas de cobro. Asi que se suben sus
listados desde la consola y la noche los cruza con el censo. De ahi salen los
cuatro analisis que pidio:

  · maquinas con Nayax que no transmiten datos a VenCloud;
  · maquinas que estan en Nayax y no estan en VenCloud;
  · maquinas con Prodelfi cuya venta o DEX no entra en VenCloud;
  · lo mismo con Nebula (los lectores Coges).

Este modulo hace dos cosas, y las dos sin dependencias, porque va dentro de dos
Lambdas que no instalan nada:

  1. LEER los ficheros tal y como salen de cada sistema (lo usa la API al
     subirlos): el .xlsx de Nayax —que trae un styles.xml que openpyxl no sabe
     abrir—, el .xlsx de Prodelfi, el .csv de Nebula y el .xls de los grupos de
     Prodelfi, que en realidad es XML de Excel 2003. Se reconoce cual es cada uno
     por sus columnas, no por el nombre del fichero.
  2. CRUZARLOS con el censo (lo usa la noche). Las reglas son las que se fueron
     decidiendo con Gabriele, una a una, al hacer el listado por PDV del 14-oct:
     estan escritas donde se aplican.

    python3 infra/test_telemetria.py
"""

import csv
import datetime
import io
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

TIPOS = ("nayax", "prodelfi", "nebula", "grupos")
NOMBRE = {"nayax": "Nayax", "prodelfi": "Prodelfi", "nebula": "Nebula (Coges)",
          "grupos": "Grupos de Prodelfi"}
# Lo que se cruza: los grupos solo sirven para leer Prodelfi.
SISTEMAS = ("nayax", "prodelfi", "nebula")

# La matricula de VenCloud: dos cifras del ano, tipo de maquina y numero
# (24CE4790). Es lo unico que comparten los cuatro sistemas.
MATRICULA = re.compile(r"(\d{2}[A-Z]{2}\d{4})(?!\d)")
ES_MATRICULA = re.compile(r"^\d{2}[A-Z]{2}\d{4}$")
# Tipo y numero sin el ano (CE4507): asi escriben muchas descripciones de Prodelfi.
SUFIJO = re.compile(r"([CSFA][EP]\d{4})(?!\d)")
CUATRO_CIFRAS = re.compile(r"(?<!\d)(\d{4})(?!\d)")

# Un fichero de mas de esto no es un listado de maquinas.
MAX_FILAS = 50_000


class FicheroNoValido(ValueError):
    """Lo que se le dice a quien sube el fichero: por que no vale."""


# ----------------------------------------------------------------------
# leer
# ----------------------------------------------------------------------
def _local(etiqueta):
    """El nombre de una etiqueta XML sin su espacio de nombres."""
    return etiqueta.rsplit("}", 1)[-1]


def _hijos(nodo, nombre):
    return [h for h in nodo if _local(h.tag) == nombre]


def _texto(nodo):
    """Todo el texto de un nodo, sea <v>, <is><t> o <is><r><t>...</t></r>."""
    return "".join(t.text or "" for t in nodo.iter() if _local(t.tag) == "t")


def _columna(ref):
    """'AB12' -> 27 (empezando en 0)."""
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def _numero(texto):
    """Un numero de celda como texto: 249.0 -> '249'."""
    try:
        f = float(texto)
    except (TypeError, ValueError):
        return texto
    return str(int(f)) if f.is_integer() and abs(f) < 1e15 else texto


def _lee_xlsx(datos):
    """La primera hoja de un .xlsx, como lista de filas de texto.

    Sin openpyxl y sin mirar styles.xml A PROPOSITO: el de Nayax viene roto y
    openpyxl no lo abre (TypeError al leer los estilos). Las fechas de los
    ficheros que nos llegan vienen como texto, asi que los estilos no hacen
    falta para nada.
    """
    z = zipfile.ZipFile(io.BytesIO(datos))
    nombres = set(z.namelist())
    compartidas = []
    if "xl/sharedStrings.xml" in nombres:
        raiz = ET.fromstring(z.read("xl/sharedStrings.xml"))
        compartidas = [_texto(si) for si in raiz if _local(si.tag) == "si"]

    # La primera hoja del libro, por su relacion. Prodelfi la llama sheet.xml
    # y no sheet1.xml, asi que no se puede dar el nombre por supuesto.
    hoja = None
    try:
        libro = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        destino = {r.get("Id"): r.get("Target") for r in rels}
        for s in libro.iter():
            if _local(s.tag) == "sheet":
                rid = next((v for k, v in s.attrib.items() if _local(k) == "id"), None)
                t = destino.get(rid)
                if t:
                    hoja = t.lstrip("/") if t.startswith("/") else "xl/" + t
                break
    except (KeyError, ET.ParseError):
        hoja = None
    if hoja not in nombres:
        hojas = sorted(n for n in nombres if n.startswith("xl/worksheets/") and n.endswith(".xml"))
        if not hojas:
            raise FicheroNoValido("El .xlsx no tiene ninguna hoja.")
        hoja = hojas[0]

    filas = []
    for fila in ET.fromstring(z.read(hoja)).iter():
        if _local(fila.tag) != "row":
            continue
        celdas, siguiente = {}, 0
        for c in fila:
            if _local(c.tag) != "c":
                continue
            # Nayax no pone la referencia de la celda (r="A1"): van en orden.
            col = _columna(c.get("r")) if c.get("r") else siguiente
            siguiente = col + 1
            tipo = c.get("t", "n")
            v = next((h for h in c if _local(h.tag) == "v"), None)
            if tipo == "inlineStr":
                valor = _texto(c)
            elif tipo == "s":
                i = int(v.text) if v is not None and v.text else -1
                valor = compartidas[i] if 0 <= i < len(compartidas) else ""
            elif tipo in ("str", "e"):
                valor = (v.text or "") if v is not None else ""
            elif tipo == "b":
                valor = "1" if v is not None and v.text == "1" else "0"
            else:
                valor = _numero(v.text) if v is not None and v.text else ""
            celdas[col] = valor
        if celdas:
            filas.append([celdas.get(i, "") for i in range(max(celdas) + 1)])
        if len(filas) > MAX_FILAS:
            raise FicheroNoValido(f"El fichero pasa de {MAX_FILAS} filas.")
    return filas


def _lee_xml_excel(datos):
    """XML de Excel 2003 (SpreadsheetML): lo que exporta Prodelfi como .xls."""
    try:
        raiz = ET.fromstring(datos)
    except ET.ParseError as e:
        raise FicheroNoValido(f"El fichero parece XML de Excel pero no se puede leer ({e}).")
    hoja = next((w for w in raiz.iter() if _local(w.tag) == "Worksheet"), None)
    if hoja is None:
        raise FicheroNoValido("El XML de Excel no tiene ninguna hoja.")
    filas = []
    for fila in hoja.iter():
        if _local(fila.tag) != "Row":
            continue
        celdas, siguiente = {}, 0
        for c in fila:
            if _local(c.tag) != "Cell":
                continue
            ind = next((v for k, v in c.attrib.items() if _local(k) == "Index"), None)
            col = int(ind) - 1 if ind else siguiente
            siguiente = col + 1
            d = next((h for h in c if _local(h.tag) == "Data"), None)
            celdas[col] = "".join(d.itertext()) if d is not None else ""
        if celdas:
            filas.append([celdas.get(i, "") for i in range(max(celdas) + 1)])
        if len(filas) > MAX_FILAS:
            raise FicheroNoValido(f"El fichero pasa de {MAX_FILAS} filas.")
    return filas


def _lee_csv(datos):
    for cod in ("utf-8-sig", "cp1252"):
        try:
            texto = datos.decode(cod)
            break
        except UnicodeDecodeError:
            continue
    primera = texto.split("\n", 1)[0]
    sep = max((";", ",", "\t"), key=primera.count)
    filas = list(csv.reader(io.StringIO(texto), delimiter=sep))
    if len(filas) > MAX_FILAS:
        raise FicheroNoValido(f"El fichero pasa de {MAX_FILAS} filas.")
    return filas


def lee_filas(datos):
    """Las filas de un fichero, sea .xlsx, XML de Excel o .csv. Por su contenido."""
    if not datos:
        raise FicheroNoValido("El fichero esta vacio.")
    if datos[:2] == b"PK":
        try:
            return _lee_xlsx(datos)
        except zipfile.BadZipFile:
            raise FicheroNoValido("El .xlsx esta dañado.")
    if datos[:4] == b"\xd0\xcf\x11\xe0":
        raise FicheroNoValido("Es un .xls antiguo (binario). Ábrelo en Excel y guárdalo como .xlsx.")
    cabeza = datos[:600].lstrip(b"\xef\xbb\xbf \r\n\t")
    if cabeza.startswith(b"<?xml") or cabeza.startswith(b"<Workbook"):
        return _lee_xml_excel(datos)
    return _lee_csv(datos)


# ----------------------------------------------------------------------
# reconocer y normalizar
# ----------------------------------------------------------------------
def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", s)


def _clave(s):
    """Un nombre de columna comparable: sin tildes, mayusculas ni espacios de mas."""
    return " ".join(_norm(s).split())


# Las columnas que hacen falta de cada fichero, con la clave por la que se
# reconocen. Lo demas se ignora.
COLUMNAS = {
    "nayax": {"id": "id maquina operador", "nombre": "nombre de la maquina",
              "jerarquia": "jerarquia operador", "ultima": "ultima comunicacion"},
    "prodelfi": {"empresa": "empresa", "codigo": "codigo maquina", "descripcion": "descripcion",
                 "comunicacion": "tipo comunicacion", "dispositivo": "dispositivo",
                 "estado": "estado"},
    "nebula": {"nombre": "nombre", "dispositivo": "dispositivo", "id_telemetria": "id telemetria",
               "cliente": "nombre cliente", "conexion": "conexion",
               "ultima_venta": "ultima venta", "ultima_auditoria": "ultima auditoria"},
    "grupos": {"codigo": "codigo", "nombre": "nombre"},
}
# Las que no pueden faltar.
OBLIGATORIAS = {
    "nayax": ("id", "nombre", "ultima"),
    "prodelfi": ("empresa", "codigo", "descripcion", "comunicacion"),
    "nebula": ("nombre", "id_telemetria"),
    "grupos": ("codigo", "nombre"),
}


def detecta(cabecera):
    """Que fichero es, por sus columnas. None si no se reconoce."""
    c = {_clave(x) for x in cabecera if str(x).strip()}
    if "jerarquia operador" in c or "id maquina operador" in c:
        return "nayax"
    if "codigo maquina" in c and "tipo comunicacion" in c:
        return "prodelfi"
    if "id telemetria" in c and "nombre" in c:
        return "nebula"
    if c == {"codigo", "nombre"}:
        return "grupos"
    return None


def fecha(valor):
    """Una fecha de cualquiera de los ficheros, en ISO. '' si no la hay.

    Nayax escribe 14/10/2026 13:10:19; Nebula, 2026-10-14 13:17:37.000. Un
    numero suelto es una fecha de Excel.
    """
    s = str(valor or "").strip()
    if not s:
        return ""
    for formato in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
                    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s.split(".")[0], formato).isoformat()
        except ValueError:
            continue
    try:
        n = float(s)
        if 20000 < n < 80000:
            return (datetime.datetime(1899, 12, 30) + datetime.timedelta(days=n)).replace(
                microsecond=0).isoformat()
    except ValueError:
        pass
    return ""


def _entero(valor):
    try:
        return int(float(str(valor).strip()))
    except (TypeError, ValueError):
        return None


def matricula_de(*textos):
    """La primera matricula de VenCloud que aparezca en estos textos."""
    for t in textos:
        m = MATRICULA.search(str(t or "").upper())
        if m:
            return m.group(1)
    return ""


def normaliza(filas):
    """De las filas de un fichero, (tipo, filas normalizadas, resumen).

    Lanza FicheroNoValido con el motivo, en palabras de quien lo sube.
    """
    # La cabecera es la primera fila que tiene algo: el CSV de Nebula empieza
    # con una columna vacia, pero la cabecera esta en la primera linea.
    filas = [f for f in filas if any(str(x).strip() for x in f)]
    if not filas:
        raise FicheroNoValido("El fichero no tiene ninguna fila.")
    cab = [_clave(x) for x in filas[0]]
    tipo = detecta(filas[0])
    if not tipo:
        raise FicheroNoValido(
            "No se reconoce el fichero. Tiene que ser el listado de máquinas de Nayax "
            "(MachineStatus), el de Prodelfi (Máquinas), el de Nebula (devices) o el de "
            "grupos de Prodelfi (Código, Nombre). Columnas leídas: "
            + ", ".join(str(x).strip() for x in filas[0][:8] if str(x).strip()))
    pos = {}
    for campo, clave in COLUMNAS[tipo].items():
        if clave in cab:
            pos[campo] = cab.index(clave)
    faltan = [COLUMNAS[tipo][c] for c in OBLIGATORIAS[tipo] if c not in pos]
    if faltan:
        raise FicheroNoValido(f"Es el fichero de {NOMBRE[tipo]}, pero le faltan columnas: "
                              + ", ".join(faltan) + ".")

    def celda(f, campo):
        i = pos.get(campo)
        return str(f[i]).strip() if i is not None and i < len(f) else ""

    out = []
    for f in filas[1:]:
        if tipo == "nayax":
            d = {"id": celda(f, "id"), "nombre": celda(f, "nombre"),
                 "jerarquia": celda(f, "jerarquia"), "ultima": fecha(celda(f, "ultima"))}
            if not (d["id"] or d["nombre"]):
                continue
            d["mat"] = matricula_de(d["id"], d["nombre"])
        elif tipo == "prodelfi":
            d = {"empresa": _entero(celda(f, "empresa")), "codigo": _entero(celda(f, "codigo")),
                 "descripcion": celda(f, "descripcion"), "comunicacion": celda(f, "comunicacion"),
                 "dispositivo": celda(f, "dispositivo"), "estado": celda(f, "estado")}
            if d["codigo"] is None:
                continue
        elif tipo == "nebula":
            d = {"nombre": celda(f, "nombre"), "dispositivo": celda(f, "dispositivo"),
                 "cliente": celda(f, "cliente"), "conexion": celda(f, "conexion"),
                 "ultima_venta": fecha(celda(f, "ultima_venta")),
                 "ultima_auditoria": fecha(celda(f, "ultima_auditoria"))}
            if not (d["nombre"] or d["dispositivo"]):
                continue
            d["mat"] = matricula_de(d["nombre"])
        else:
            cod = _entero(celda(f, "codigo"))
            if cod is None:
                continue
            d = {"codigo": cod, "nombre": celda(f, "nombre")}
        out.append(d)
    if not out:
        raise FicheroNoValido(f"Es el fichero de {NOMBRE[tipo]}, pero no trae ninguna máquina.")
    return tipo, out, resumen(tipo, out)


def resumen(tipo, filas):
    """Lo que la consola ensena del fichero recien subido."""
    r = {"filas": len(filas)}
    if tipo == "nayax":
        r["con_matricula"] = sum(1 for f in filas if f["mat"])
        fechas = [f["ultima"] for f in filas if f["ultima"]]
        r["exportado"] = max(fechas)[:10] if fechas else None
    elif tipo == "prodelfi":
        r["con_comunicacion"] = sum(1 for f in filas if con_comunicacion(f))
        r["grupos"] = len({f["empresa"] for f in filas})
    elif tipo == "nebula":
        r["con_matricula"] = sum(1 for f in filas if f["mat"])
        fechas = [f["ultima_venta"] for f in filas if f["ultima_venta"]]
        r["ultima_venta"] = max(fechas)[:10] if fechas else None
    return r


def lee(datos):
    """El fichero subido, de los bytes a (tipo, filas, resumen)."""
    return normaliza(lee_filas(datos))


# ----------------------------------------------------------------------
# cruzar con el censo
# ----------------------------------------------------------------------
def con_comunicacion(fila_prodelfi):
    """Gabriele, 14-oct: las filas de Prodelfi «Sin comunicación» no cuentan
    para nada, ni como telemetria ni para buscarles maquina."""
    return _clave(fila_prodelfi.get("comunicacion")) != "sin comunicacion"


# Los dispositivos de Prodelfi que son una maquina. Los demas (TPV de economato,
# portales, Easy Pay, kioscos) no tienen maquina en VenCloud que buscarles.
DISPOSITIVOS_MAQUINA = {"terminal vending", "summum", "summum 25", "imperium"}

# Asociaciones a mano (Codigo Maquina de Prodelfi -> matricula), revisadas con
# Gabriele el 14-oct. Amazon ZAZ1 «NECTA TANGO-155EO771»: matricula mal escrita.
MANUAL = {17677: "15SE0771"}
# Grupos de Prodelfi cuyo nombre no se parece al del cliente en VenCloud.
ALIAS = {138: "Radio Television", 139: "Radio Television", 140: "Radio Television"}
# Centros donde todas las maquinas tienen Prodelfi aunque su descripcion no lleve
# la matricula (Gabriele, 14-oct): centro de VenCloud -> grupo de Prodelfi. Las
# cafeteras (CE) no llevan sistema de pago y no entran.
CENTROS_TODO_PRODELFI = {500013: 249,   # AMAZON ZAZ1
                         174003: 250}   # AMAZON BCN4 (FIGUERES)

# Palabras que salen en cualquier nombre de cliente y no dicen de quien es.
_VACIAS = {"hospital", "hopsital", "hospiral", "laboratorio", "laboratorios", "madrid", "sevilla",
           "grupo", "centro", "nuevo", "clinica", "universitario", "residencia", "colegio",
           "eliminar", "vending", "students", "student", "universidad", "oficinas", "campus",
           "fundacion", "instituto", "espana"}


def _palabras(nombre):
    """Las palabras de un nombre de grupo que sirven para reconocer al cliente."""
    s = re.sub(r"\b[lo]0[a-z0-9]{4,5}\b", "", _norm(nombre))
    t = [w for w in s.split() if len(w) >= 4 and w not in _VACIAS and not w.isdigit()]
    return t or [w for w in s.split()
                 if len(w) >= 2 and w not in _VACIAS and not (w.isdigit() and len(w) > 2)]


class _Grupo:
    """Lo que se sabe de un grupo de Prodelfi para elegir entre candidatas."""

    def __init__(self, nombre, textos):
        self.patrones = [re.compile(r"\b" + re.escape(w)) for w in _palabras(nombre)] if nombre else []
        # Si el nombre del grupo se reconoce en algun cliente o centro de VenCloud.
        self.conocido = bool(self.patrones) and any(self.puntos(t) for t in textos)

    def puntos(self, texto_norm):
        return sum(1 for p in self.patrones if p.search(texto_norm))


def _texto_maquina(m):
    return _norm(f"{m.get('cliente') or ''} {m.get('centro') or ''}")


def empareja_prodelfi(prodelfi, maquinas, grupos):
    """{indice de la fila de Prodelfi: (matricula, como)} de las que se asocian.

    `prodelfi`: las filas CON comunicacion. `maquinas`: {matricula: fila del
    censo}. `grupos`: {codigo de grupo: nombre}.

      1. La descripcion trae la matricula completa y existe en VenCloud.
      2. Trae tipo y numero sin el ano (CE4507).
      3. Solo trae un numero de 4 cifras, y nunca si ya trae una matricula.

    En 2 y 3 se buscan las maquinas con ese final y se queda la del cliente del
    grupo: por su nombre (contra cliente y centro de VenCloud) si se reconoce, o
    por estar en un centro donde ya hay otra maquina del grupo cruzada por
    matricula completa si no. Si queda mas de una, o ninguna, no se asocia.
    """
    grupos = {k: f"{v} {ALIAS.get(k, '')}".strip() for k, v in (grupos or {}).items()}
    for k, v in ALIAS.items():
        grupos.setdefault(k, v)
    textos = {mat: _texto_maquina(m) for mat, m in maquinas.items()}
    distintos = set(textos.values())
    centro = {mat: m.get("num_centro") for mat, m in maquinas.items()}
    por_sufijo, por_cuatro = {}, {}
    for mat in maquinas:
        por_sufijo.setdefault(mat[2:], []).append(mat)
        por_cuatro.setdefault(mat[-4:], []).append(mat)

    res = {}
    contexto = {}
    for i, p in enumerate(prodelfi):
        m = MATRICULA.search(str(p.get("descripcion") or "").upper())
        if m and m.group(1) in maquinas:
            res[i] = (m.group(1), "matrícula completa")
            contexto.setdefault(p.get("empresa"), set()).add(centro[m.group(1)])

    cache = {}

    def grupo(emp):
        if emp not in cache:
            cache[emp] = _Grupo(grupos.get(emp, ""), distintos)
        return cache[emp]

    def elige(candidatas, emp):
        g = grupo(emp)
        if g.conocido:
            pts = [(g.puntos(textos[c]), c) for c in candidatas]
            pts = [x for x in pts if x[0] > 0]
        else:
            cen = contexto.get(emp, set())
            pts = [(g.puntos(textos[c]), c) for c in candidatas if centro[c] in cen]
        if not pts:
            return None
        mejor = max(x[0] for x in pts)
        quedan = [c for x, c in pts if x == mejor]
        return quedan[0] if len(quedan) == 1 else None

    for i, p in enumerate(prodelfi):
        if i in res:
            continue
        if p.get("codigo") in MANUAL:
            res[i] = (MANUAL[p["codigo"]], "a mano")
            continue
        txt = str(p.get("descripcion") or "").upper()
        emp = p.get("empresa")
        s = SUFIJO.search(txt)
        if s:
            k = elige(por_sufijo.get(s.group(1), []), emp)
            if k:
                res[i] = (k, f"tipo y número {s.group(1)}")
        elif not MATRICULA.search(txt):
            hits = {}
            for n in CUATRO_CIFRAS.findall(txt):
                k = elige(por_cuatro.get(n, []), emp)
                if k:
                    hits[k] = n
            if len(hits) == 1:
                k, n = next(iter(hits.items()))
                res[i] = (k, f"últimos 4 números {n}")
    return res


def cruza(censo, ficheros):
    """El cruce de los ficheros con el censo.

    `censo`: las filas del maestro de instalaciones (todas: el cruce de Prodelfi
    necesita ver el parque entero para saber si un final de matricula es unico).
    `ficheros`: {tipo: [filas normalizadas]} con los que haya.

    Devuelve {"maquinas": {matricula: {...}}, "fuera": [...], "exportado": fecha}.
    `fuera` son las de los sistemas que no estan en VenCloud.
    """
    maquinas = {}
    for f in censo:
        mat = str(f.get("matricula") or "").strip().upper()
        if mat and mat not in maquinas:
            maquinas[mat] = f
    out, fuera = {}, []

    def ficha(mat):
        return out.setdefault(mat, {"sistemas": []})

    # ---- Nayax
    nayax = ficheros.get("nayax") or []
    fechas = [f["ultima"] for f in nayax if f.get("ultima")]
    exportado = max(fechas)[:10] if fechas else None
    for f in nayax:
        mat = f.get("mat") or ""
        if mat in maquinas:
            x = ficha(mat)
            if "nayax" in x["sistemas"]:
                continue
            x["sistemas"].append("nayax")
            x["nayax"] = {"id": f.get("id", ""), "ultima": f.get("ultima", ""),
                          "jerarquia": f.get("jerarquia", "")}
        else:
            fuera.append({"sistema": "nayax", "id": f.get("id", ""), "nombre": f.get("nombre", ""),
                          "detalle": f.get("jerarquia", ""), "ultima": f.get("ultima", ""),
                          "motivo": (f"La matrícula {mat} no está instalada en VenCloud." if mat
                                     else "No lleva una matrícula reconocible.")})

    # ---- Prodelfi
    prodelfi = [f for f in ficheros.get("prodelfi") or [] if con_comunicacion(f)]
    grupos = {g["codigo"]: g["nombre"] for g in ficheros.get("grupos") or []}
    pares = empareja_prodelfi(prodelfi, maquinas, grupos)
    # Una maquina con dos filas de Prodelfi se queda con la activada.
    elegida = {}
    for i, (mat, como) in pares.items():
        if mat not in maquinas:
            continue
        p = prodelfi[i]
        if mat not in elegida or str(p.get("estado") or "") < str(prodelfi[elegida[mat][0]].get("estado") or ""):
            elegida[mat] = (i, como)
    for mat, (i, como) in elegida.items():
        p = prodelfi[i]
        x = ficha(mat)
        x["sistemas"].append("prodelfi")
        x["prodelfi"] = {"codigo": p.get("codigo"), "grupo": p.get("empresa"),
                         "descripcion": p.get("descripcion", ""), "como": como,
                         "estado": p.get("estado", "")}
    for i, p in enumerate(prodelfi):
        if i not in pares and _clave(p.get("dispositivo")) in DISPOSITIVOS_MAQUINA:
            fuera.append({"sistema": "prodelfi", "id": str(p.get("codigo") or ""),
                          "nombre": p.get("descripcion", ""),
                          "detalle": f"Grupo {p.get('empresa')} {grupos.get(p.get('empresa'), '')}".strip(),
                          "ultima": "",
                          "motivo": "No se ha podido asociar a una máquina de VenCloud."})
    # Los centros que llevan Prodelfi entero, aunque la descripcion no lo diga.
    if ficheros.get("prodelfi"):
        for mat, f in maquinas.items():
            try:
                c = int(f.get("num_centro"))
            except (TypeError, ValueError):
                continue
            if (c in CENTROS_TODO_PRODELFI and ES_MATRICULA.match(mat) and mat[2:4] != "CE"
                    and "prodelfi" not in out.get(mat, {}).get("sistemas", [])):
                x = ficha(mat)
                x["sistemas"].append("prodelfi")
                x["prodelfi"] = {"codigo": None, "grupo": CENTROS_TODO_PRODELFI[c],
                                 "descripcion": "", "como": "todo el centro tiene Prodelfi",
                                 "estado": ""}

    # ---- Nebula
    for f in ficheros.get("nebula") or []:
        mat = f.get("mat") or ""
        if mat in maquinas:
            x = ficha(mat)
            if "nebula" in x["sistemas"]:
                continue
            x["sistemas"].append("nebula")
            x["nebula"] = {"dispositivo": f.get("dispositivo", ""),
                           "ultima_venta": f.get("ultima_venta", ""),
                           "ultima_auditoria": f.get("ultima_auditoria", "")}
        else:
            fuera.append({"sistema": "nebula", "id": f.get("dispositivo", ""),
                          "nombre": f.get("nombre", ""), "detalle": f.get("cliente", ""),
                          "ultima": f.get("ultima_venta", ""),
                          "motivo": (f"La matrícula {mat} no está instalada en VenCloud." if mat
                                     else "No lleva una matrícula reconocible.")})

    for mat, x in out.items():
        x["sistema"] = principal(x, exportado)
    return {"maquinas": out, "fuera": fuera, "exportado": exportado}


def principal(x, exportado):
    """El sistema por el que se le pide el dato a una maquina.

    Gabriele, 14-oct: si el Nayax de la maquina comunico el dia de la
    exportacion, la maquina es de Nayax aunque tambien tenga otro. Si no, manda
    el otro: un Nayax que lleva dias callado en una maquina con Prodelfi no es
    el que tiene que mandar el dato.
    """
    s = x["sistemas"]
    if "nayax" in s:
        hoy = bool(exportado) and str(x["nayax"].get("ultima") or "")[:10] >= exportado
        if hoy or len(s) == 1:
            return "nayax"
    if "prodelfi" in s:
        return "prodelfi"
    if "nebula" in s:
        return "nebula"
    return s[0]
