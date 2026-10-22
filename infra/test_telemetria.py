"""
La telemetria de fuera (docs/53): leer los ficheros de Nayax, Prodelfi y Nebula
tal y como salen de cada sistema, cruzarlos con el censo con las reglas que se
decidieron con Gabriele, y lo que de eso llega al cuadrado y a la pagina.

Los ficheros de aqui se fabrican con las MISMAS rarezas que los de verdad: el
Nayax con un styles.xml que no se puede leer y sin referencias de celda, el
Prodelfi con la hoja llamada sheet.xml y textos compartidos, el Nebula con BOM y
una primera columna vacia, y los grupos en XML de Excel 2003 con extension .xls.

    python3 infra/test_telemetria.py
"""

import datetime
import gzip
import io
import json
import os
import sys
import types
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import telemetria as TE  # noqa: E402
import operativo as OP  # noqa: E402
import incidencias as IN  # noqa: E402

fallos = []


def comprueba(que, dado, esperado):
    ok = dado == esperado
    print(f"  {'ok   ' if ok else 'FALLO'} {que}" + ("" if ok else f": {dado!r} != {esperado!r}"))
    if not ok:
        fallos.append(que)


HOY = datetime.date.today()
AYER = HOY - datetime.timedelta(days=1)
HACE_3 = HOY - datetime.timedelta(days=3)


def dmy(d, hora="10:00:00"):
    return d.strftime("%d/%m/%Y") + " " + hora


# ----------------------------------------------------------------------
# los ficheros, con sus rarezas
# ----------------------------------------------------------------------
def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def xlsx_nayax(filas):
    """Como el de Nayax: celdas sin r="A1", texto en linea, fechas como texto,
    y un styles.xml que openpyxl no sabe abrir."""
    def celda(v, cab=False):
        if cab:
            return f'<x:c s="1" t="str"><x:v>{_esc(v)}</x:v></x:c>'
        return f'<x:c t="inlineStr"><x:is><x:t>{_esc(v)}</x:t></x:is></x:c>'
    hoja = ('<?xml version="1.0" encoding="utf-8"?><x:worksheet '
            'xmlns:x="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><x:sheetData>'
            + "".join("<x:row>" + "".join(celda(v, i == 0) for v in f) + "</x:row>"
                      for i, f in enumerate(filas))
            + "</x:sheetData></x:worksheet>")
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0"?><x:workbook xmlns:x="http://schemas.openxmlformats.org/'
                   'spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/'
                   'officeDocument/2006/relationships"><x:sheets><x:sheet name="Hoja" sheetId="1" '
                   'r:id="R1"/></x:sheets></x:workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/'
                   'package/2006/relationships"><Relationship Id="R1" Type="x" '
                   'Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/styles.xml", "<roto esto no es un styleSheet")
        z.writestr("xl/worksheets/sheet1.xml", hoja)
    return b.getvalue()


def xlsx_prodelfi(filas):
    """Como el de Prodelfi: la hoja se llama sheet.xml (no sheet1.xml), con BOM,
    ruta absoluta en la relacion, textos compartidos y numeros."""
    compartidas, idx = [], {}

    def celda(v, col, fila):
        ref = f"{chr(65 + col)}{fila}"
        if isinstance(v, (int, float)):
            return f'<x:c r="{ref}"><x:v>{v}</x:v></x:c>'
        if v not in idx:
            idx[v] = len(compartidas)
            compartidas.append(v)
        return f'<x:c r="{ref}" t="s"><x:v>{idx[v]}</x:v></x:c>'
    cuerpo = "".join(f'<x:row r="{i + 1}">' + "".join(celda(v, c, i + 1) for c, v in enumerate(f))
                     + "</x:row>" for i, f in enumerate(filas))
    hoja = ('﻿<?xml version="1.0" encoding="utf-8"?><x:worksheet '
            'xmlns:x="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><x:sheetData>'
            + cuerpo + "</x:sheetData></x:worksheet>")
    sst = ('<?xml version="1.0"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
           + "".join(f"<si><t>{_esc(s)}</t></si>" for s in compartidas) + "</sst>")
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("xl/workbook.xml",
                   '﻿<?xml version="1.0" encoding="utf-8"?><x:workbook xmlns:x="http://schemas.'
                   'openxmlformats.org/spreadsheetml/2006/main"><x:sheets><x:sheet name="Table1" '
                   'sheetId="1" r:id="Rabc" xmlns:r="http://schemas.openxmlformats.org/officeDocument/'
                   '2006/relationships" /></x:sheets></x:workbook>'.encode("utf-8"))
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/'
                   'package/2006/relationships"><Relationship Type="x" Target="/xl/worksheets/'
                   'sheet.xml" Id="Rabc" /></Relationships>')
        z.writestr("xl/sharedStrings.xml", sst)
        z.writestr("xl/worksheets/sheet.xml", hoja.encode("utf-8"))
    return b.getvalue()


def xml_grupos(filas):
    """RadGridExport.xls: XML de Excel 2003, con una fila en blanco al principio."""
    def fila(f):
        return ("<Row>" + "".join(f'<Cell ss:Index="{i + 1}"><Data ss:Type="String">{_esc(v)}</Data></Cell>'
                                  for i, v in enumerate(f)) + "</Row>")
    return ('<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?>'
            '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
            'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="W">'
            "<Table>" + fila(filas[0]) + fila(["", ""]) + "".join(fila(f) for f in filas[1:])
            + "</Table></Worksheet></Workbook>").encode("utf-8")


def csv_nebula(filas):
    return ("﻿" + "\n".join(",".join(f) for f in filas) + "\n").encode("utf-8")


CAB_NAYAX = ["ID Máquina (Operador)  ", "Nombre de la máquina", "Jerarquía Operador",
             "Última Comunicación  ", "VPOS Serial Number  ", "VPOS ID"]
NAYAX = xlsx_nayax([CAB_NAYAX,
                    ["20SE0001", "FASTER 900", "Serunion / Norte", dmy(HOY, "13:10:19"), "1", "2"],
                    # Nayax callado hace tres dias en una maquina con Prodelfi
                    ["20SE0002", "NECTA", "Serunion / Norte", dmy(HACE_3), "1", "2"],
                    # solo Nayax y callado: sigue siendo de Nayax
                    ["20SE0003", "JOFEMAR", "Serunion / Norte", dmy(HACE_3), "1", "2"],
                    # Nayax de hoy en una maquina que tambien tiene Prodelfi: Nayax
                    ["20SE0004", "NECTA", "Serunion / Norte", dmy(HOY), "1", "2"],
                    # la matricula en el nombre, no en el id
                    ["", "OPERA 20SE0006", "Serunion / Sur", dmy(HOY), "1", "2"],
                    ["99XX9999", "FANTASMA", "Serunion / Sur", dmy(HOY), "1", "2"],
                    ["CAJA 7", "SIN MATRICULA", "Serunion / Sur", dmy(HOY), "1", "2"]])

CAB_PRODELFI = ["Empresa", "Código Máquina", "Descripción", "Almacén", "Grupo", "Dirección",
                "Código Tarifa Efectivo", "Tarifa Efectivo", "Tipo Comunicación", "IP", "Socket",
                "Protocolo Conexión", "Dispositivo", "Version", "TouchFree", "Estado"]


def pf(emp, cod, desc, com="TCP", disp="Terminal Vending", estado="Activada"):
    return [emp, cod, desc, 0, 991, "", 0, "Tarifa 1", com, "", 0, "Máquina Vending", disp, "", "N", estado]


PRODELFI = xlsx_prodelfi([
    CAB_PRODELFI,
    pf(101, 1, "NECTA 20SE0002 planta 1"),
    pf(101, 2, "NECTA 20SE0004"),
    # Gabriele, 14-oct: «Sin comunicación» no cuenta para nada
    pf(101, 3, "NECTA 20SE0005", com="Sin comunicación"),
    # tipo y numero sin el año: dos maquinas en VenCloud con ese final, y el
    # nombre del grupo (138, alias Radio Television) elige la de RTVE
    pf(138, 4, "CE4507 Torrespaña"),
    # solo cuatro cifras: la unica 0777 de la Fundacio Puigvert
    pf(101, 5, "Maquina comedor 0777"),
    # cuatro cifras con dos candidatas del mismo cliente: no se asocia
    pf(101, 6, "Maquina pasillo 0888"),
    # un TPV no es una maquina: ni se cruza ni sale como que falta
    pf(999, 7, "TPV economato 1234", disp="TPV Economato"),
    # la de la matricula mal escrita, puesta a mano
    pf(249, 17677, "NECTA TANGO-155EO771"),
])

GRUPOS = xml_grupos([["Código", "Nombre"], ["101", "Fundacio Puigvert - L0G829"],
                     ["138", "RTVE Prado del Rey"], ["249", "Eliminar"]])

NEBULA = csv_nebula([["", "Nombre", "Dispositivo", "Gama", "Id telemetría", "Nombre cliente",
                      "Conexión", "Última auditoría", "Última venta"],
                     ["", "15FE1566", "CUNI-91920270", "Unica", "abc", "APPLE BCN", "Connected",
                      "2025-01-09 11:55:54.635", f"{AYER} 13:17:37.000"],
                     ["", "PRUEBAS", "CUNI-1", "Unica", "def", "APPLE BCN", "Connected", "", ""]])


def maquina(mat, centro, num, cliente, cod_cliente="C1", deleg="Cataluña", pdv=None):
    return {"cod_cliente": cod_cliente, "cliente": cliente, "num_centro": num, "centro": centro,
            "delegacion": deleg, "cod_pdv": pdv or "P" + mat, "ubicacion": "Hall", "matricula": mat,
            "estado_pdv": 1, "telemetria": 0, "modelo": "ARIA L EVO" if mat.startswith("20") else ""}


PUIG = ("HOSPITAL FUNDACIO PUIGVERT", 100, "FUNDACIO PUIGVERT")
CENSO = [
    maquina("20SE0001", *PUIG), maquina("20SE0002", *PUIG), maquina("20SE0003", *PUIG),
    maquina("20SE0004", *PUIG), maquina("20SE0005", *PUIG), maquina("20SE0006", *PUIG),
    maquina("21SE0777", *PUIG), maquina("22SE0888", *PUIG), maquina("23SE0888", *PUIG),
    maquina("24SE0777", "COLEGIO SANTA ANA", 300, "COLEGIO SANTA ANA", "C3", "Madrid"),
    maquina("18CE4507", "TORRESPAÑA", 200, "RADIO TELEVISION ESPAÑOLA", "C2", "Madrid"),
    maquina("19CE4507", "COLEGIO SANTA ANA", 300, "COLEGIO SANTA ANA", "C3", "Madrid"),
    # Amazon ZAZ1: todo el centro lleva Prodelfi, menos las cafeteras
    maquina("15SE0771", "AMAZON ZAZ1", 500013, "AMAZON", "C4", "Aragón"),
    maquina("23FE1655", "AMAZON ZAZ1", 500013, "AMAZON", "C4", "Aragón"),
    maquina("16CE1180", "AMAZON ZAZ1", 500013, "AMAZON", "C4", "Aragón"),
    maquina("15FE1566", "APPLE PLAÇA CATALUNYA", 400, "APPLE", "C5"),
]

# ----------------------------------------------------------------------
print("Leer: cada fichero se reconoce por sus columnas, no por su nombre")
leidos = {}
for nombre, datos in (("MachineStatus.xlsx", NAYAX), ("Maquinas 1.xlsx", PRODELFI),
                      ("devices.csv", NEBULA), ("RadGridExport.xls", GRUPOS)):
    tipo, filas, res = TE.lee(datos)
    leidos[tipo] = filas
    print(f"    {nombre} -> {tipo} {res}")
comprueba("los cuatro", sorted(leidos), ["grupos", "nayax", "nebula", "prodelfi"])
comprueba("Nayax: el styles.xml roto no importa, siete maquinas", len(leidos["nayax"]), 7)
comprueba("Nayax: la fecha dd/mm/aaaa pasa a ISO", leidos["nayax"][0]["ultima"],
          f"{HOY.isoformat()}T13:10:19")
comprueba("Nayax: la matricula sale del id o, si no, del nombre",
          [f["mat"] for f in leidos["nayax"]],
          ["20SE0001", "20SE0002", "20SE0003", "20SE0004", "20SE0006", "99XX9999", ""])
comprueba("Nayax: la fecha de la exportacion es la ultima comunicacion mas nueva",
          TE.resumen("nayax", leidos["nayax"])["exportado"], HOY.isoformat())
comprueba("Prodelfi: la hoja sheet.xml, con sus numeros enteros",
          (leidos["prodelfi"][0]["empresa"], leidos["prodelfi"][0]["codigo"]), (101, 1))
comprueba("Prodelfi: textos compartidos", leidos["prodelfi"][3]["descripcion"], "CE4507 Torrespaña")
comprueba("Nebula: BOM y primera columna vacia", leidos["nebula"][0]["mat"], "15FE1566")
comprueba("Nebula: la fecha con milesimas", leidos["nebula"][0]["ultima_venta"],
          f"{AYER.isoformat()}T13:17:37")
comprueba("grupos: XML de Excel, sin la fila en blanco", leidos["grupos"],
          [{"codigo": 101, "nombre": "Fundacio Puigvert - L0G829"},
           {"codigo": 138, "nombre": "RTVE Prado del Rey"}, {"codigo": 249, "nombre": "Eliminar"}])


def rechaza(datos):
    try:
        TE.lee(datos)
    except TE.FicheroNoValido as e:
        return str(e)
    return None


comprueba("un fichero de otra cosa se rechaza diciendo que columnas tiene",
          "Columnas leídas: Fecha, Importe" in (rechaza(b"Fecha;Importe\n1;2\n") or ""), True)
comprueba("uno de Nayax sin la ultima comunicacion dice que le falta",
          rechaza(xlsx_nayax([["ID Máquina (Operador)", "Nombre de la máquina"], ["20SE0001", "X"]])),
          "Es el fichero de Nayax, pero le faltan columnas: ultima comunicacion.")
comprueba("un .xls binario antiguo se pide como .xlsx",
          "guárdalo como .xlsx" in (rechaza(b"\xd0\xcf\x11\xe0" + b"\0" * 100) or ""), True)
comprueba("vacio", rechaza(b""), "El fichero esta vacio.")

# ----------------------------------------------------------------------
print("\nCruzar: las reglas del 14 de octubre")
c = TE.cruza(CENSO, leidos)
M = c["maquinas"]


def sistema(m):
    return M[m]["sistema"] if m in M else None


comprueba("Nayax que comunico hoy: Nayax", sistema("20SE0001"), "nayax")
comprueba("Nayax callado con Prodelfi: manda Prodelfi", sistema("20SE0002"), "prodelfi")
comprueba("  y se sabe que tambien tiene Nayax", M["20SE0002"]["sistemas"], ["nayax", "prodelfi"])
comprueba("solo Nayax aunque este callado: Nayax", sistema("20SE0003"), "nayax")
comprueba("Nayax de hoy con Prodelfi: Nayax", sistema("20SE0004"), "nayax")
comprueba("Prodelfi «Sin comunicación» no cuenta", sistema("20SE0005"), None)
comprueba("matricula en el nombre de Nayax", sistema("20SE0006"), "nayax")
comprueba("tipo y número: elige la de RTVE por el nombre del grupo (alias)",
          (sistema("18CE4507"), sistema("19CE4507")), ("prodelfi", None))
comprueba("  y dice como", M["18CE4507"]["prodelfi"]["como"], "tipo y número CE4507")
comprueba("cuatro cifras: la del cliente del grupo, no la de otro",
          (sistema("21SE0777"), sistema("24SE0777")), ("prodelfi", None))
comprueba("cuatro cifras con dos candidatas del cliente: ninguna",
          (sistema("22SE0888"), sistema("23SE0888")), (None, None))
comprueba("la puesta a mano", M["15SE0771"]["prodelfi"]["como"], "a mano")
comprueba("ZAZ1: todo el centro tiene Prodelfi",
          M["23FE1655"]["prodelfi"]["como"], "todo el centro tiene Prodelfi")
comprueba("  menos la cafetera, que no tiene sistema de pago", sistema("16CE1180"), None)
comprueba("Nebula", sistema("15FE1566"), "nebula")
fuera = sorted((f["sistema"], f["id"]) for f in c["fuera"])
comprueba("fuera de VenCloud: las de Nayax sin maquina, la Prodelfi ambigua y la de Nebula",
          fuera, [("nayax", "99XX9999"), ("nayax", "CAJA 7"), ("nebula", "CUNI-1"), ("prodelfi", "6")])
comprueba("  con el motivo", [f["motivo"] for f in c["fuera"] if f["id"] == "99XX9999"],
          ["La matrícula 99XX9999 no está instalada en VenCloud."])
comprueba("el TPV no es una maquina que falte", any(f["id"] == "7" for f in c["fuera"]), False)
comprueba("sin fichero de Prodelfi, ZAZ1 no se da por Prodelfi",
          "23FE1655" in TE.cruza(CENSO, {"nayax": leidos["nayax"]})["maquinas"], False)

# ----------------------------------------------------------------------
print("\nEl cuadrado sale de VenCloud; los ficheros, solo para las diferencias (Gabriele, 15-oct)")
DIA = AYER.isoformat()
meta = {"ficheros": {"nayax": {"nombre": "MachineStatus.xlsx"}}, "faltan": []}
# VenCloud marca con telemetria: una que tiene Nayax, una de Prodelfi y una que
# no esta en ningun sistema.
for f in CENSO:
    if f["matricula"] in ("20SE0001", "18CE4507", "24SE0777"):
        f["telemetria"] = 40


def dex(m):
    return {"empleadoid": 0, "empleado": "SYSTEM", "tipo_parte": 2, "origen": 2,
            "estado_lectura": 2, "matricula": m, "cod_pdv": "X"}


op = OP.Operativo([DIA])
op.come_censo(CENSO)
op.pon_telemetria(c, CENSO, meta, fuera=c["fuera"])
d = op.dia(DIA)
d.come_telemetria([{"matricula": "20SE0001"}, {"matricula": "20se0002"}, {"matricula": "15FE1566"}])
d.come_partes([dex("20SE0001"), dex("18CE4507"), dex("15FE1566")])
t = op.cuadrados_del_dia(d)["telemetria"]
n = len(c["maquinas"])
comprueba("el universo es el de VenCloud: las tres que marca", t["auditables"], 3)
comprueba("y el DEX, de esas: 2 (la de Nebula no esta marcada y no suma)", t["con_dex"], 2)
comprueba("con su semaforo", (t["pct"], t["color"]), (OP.porcentaje(2, 3), "rojo"))
comprueba("debajo, las diferencias con los sistemas", t["diferencias"],
          {"en_sistemas": n, "sin_marca": n - 2, "solo_vencloud": 1, "fuera": 4})

det = op.detalle_telemetria("interno")
comprueba("la pagina: las de los sistemas y la que solo tiene VenCloud", len(det["maquinas"]), n + 1)
solo = [x["matricula"] for x in det["maquinas"] if x["sistema"] == "solo_vencloud"]
comprueba("la que VenCloud marca y ningun sistema tiene", solo, ["24SE0777"])
comprueba("el dia lleva quien mando venta", det["dias"][DIA]["venta"], ["15FE1566", "20SE0001", "20SE0002"])
f2 = next(x for x in det["maquinas"] if x["matricula"] == "20SE0002")
comprueba("con su sistema y lo que tambien tiene", (f2["sistema"], f2["tambien"]), ("prodelfi", ["nayax"]))
comprueba("si VenCloud la marca con telemetria", (f2["vencloud"],
          next(x for x in det["maquinas"] if x["matricula"] == "20SE0001")["vencloud"]), (False, True))
comprueba("y el centro del censo", (f2["centro"], f2["delegacion"]), ("HOSPITAL FUNDACIO PUIGVERT", "Cataluña"))
comprueba("y la ultima comunicacion de Nayax", f2["nayax"]["ultima"][:10], HACE_3.isoformat())
comprueba("y el modelo de VenCloud, vacio si el censo no lo trae",
          (f2["modelo"], next(x for x in det["maquinas"] if x["matricula"] == "24SE0777")["modelo"]),
          ("ARIA L EVO", ""))
comprueba("y el area de cada delegacion, para abrir por areas", det["zonas"],
          {d: IN.zona_de(d) for d in {x["delegacion"] for x in det["maquinas"]}})
comprueba("Cataluña y Madrid caen en sus areas del Power BI",
          (det["zonas"]["Cataluña"], det["zonas"]["Madrid"]), ("Cataluña", "Centro"))
viejo = {"dias": {"2020-01-01": {"venta": ["X"], "dex": []}}}
comprueba("acumula los dias anteriores, y guarda una semana",
          "2020-01-01" in op.detalle_telemetria("interno", viejo)["dias"], True)

print("\nUn perfil acotado: solo sus maquinas, y sin las de fuera")
propias = [f for f in CENSO if f["cliente"] == "AMAZON"]
op2 = OP.Operativo([DIA])
op2.come_censo(propias)
op2.pon_telemetria(c, propias, meta, fuera=None)
t2 = op2.cuadrados_del_dia(op2.dia(DIA))["telemetria"]
comprueba("VenCloud no marca ninguna de Amazon: sin dato, aunque Prodelfi tenga dos",
          ("sin_dato" in t2, "diferencias" in t2), (True, False))
det2 = op2.detalle_telemetria("amazon")
comprueba("pero la pagina si las ensena", sorted(x["matricula"] for x in det2["maquinas"]),
          ["15SE0771", "23FE1655"])
comprueba("las de fuera no son de nadie: no salen", det2["fuera"], None)

print("\nSin ficheros, el cuadrado de siempre y sin pagina")
op4 = OP.Operativo([DIA])
op4.come_censo([dict(CENSO[0], telemetria=40)])
op4.pon_telemetria(None, CENSO, meta)
d4 = op4.dia(DIA)
d4.come_partes([dex("20SE0001")])
comprueba("auditables y DEX, como antes",
          op4.cuadrados_del_dia(d4)["telemetria"],
          {"auditables": 1, "con_dex": 1, "pct": 100.0, "color": "verde"})
comprueba("y no hay pagina de telemetria", op4.detalle_telemetria("interno"), None)

# ----------------------------------------------------------------------
print("\nLa noche entera, con un S3 falso")
ALMACEN = {}


class _S3:
    def get_object(self, Bucket, Key):
        if Key not in ALMACEN:
            raise KeyError(Key)
        cuerpo = ALMACEN[Key]
        return {"Body": types.SimpleNamespace(read=lambda: cuerpo)}

    def put_object(self, Bucket, Key, Body, **kw):
        ALMACEN[Key] = Body
        return {}


class _DDB:
    def scan(self, **kw):
        return {"Items": []}


sys.modules["boto3"] = types.SimpleNamespace(
    client=lambda servicio, *a, **k: _DDB() if servicio == "dynamodb" else _S3())
os.environ.setdefault("BUCKET", "prueba")
os.environ["DIAS"] = "2"
import lambda_agregados as L  # noqa: E402


def pon(destino, ident, dia, filas):
    ALMACEN[f"{destino}/anio={dia.year}/mes={dia.month:02d}/dia={dia.day:02d}/{ident}.json.gz"] = \
        gzip.compress(json.dumps(filas).encode())


ALMACEN["maestros/instalaciones/m_instalaciones.json.gz"] = gzip.compress(json.dumps(CENSO).encode())
pon("crudo/telemetria_ventas", "telemetria_ventas", AYER,
    [{"matricula": "20SE0001", "centro": PUIG[0], "num_centro": 100, "cliente": PUIG[2],
      "importe": 1.2, "unidades": 1},
     {"matricula": "23FE1655", "centro": "AMAZON ZAZ1", "num_centro": 500013, "cliente": "AMAZON",
      "importe": 1.0, "unidades": 1}])
pon("crudo/visita_cabecera", "visita_cabecera", AYER,
    [dict(dex("23FE1655"), centro="AMAZON ZAZ1", num_centro=500013, cliente="AMAZON")])
for tipo, datos in (("nayax", NAYAX), ("prodelfi", PRODELFI), ("nebula", NEBULA), ("grupos", GRUPOS)):
    t_, filas, res = TE.lee(datos)
    ALMACEN[f"externo/telemetria/{t_}/actual.json"] = json.dumps(
        {"tipo": t_, "nombre": f"{t_}.xlsx", "subido": "2026-10-14T16:00:00Z", "por": "g@x",
         "resumen": res, "filas": filas}).encode()
# Ningun perfil con cuadro: la telemetria se tiene que leer igual, para el informe.
ALMACEN["config/perfiles.json"] = json.dumps({"perfiles": [
    {"id": "interno", "ambito": {}, "cuadro": False},
    {"id": "amazon", "ambito": {"clientes": ["AMAZON"]}, "cuadro": False}]}).encode()

res = L.lambda_handler({}, None)
comprueba("se leyo el informe de venta por telemetria sin ningun cuadro", res["filas_leidas"].get("telemetria"), 2)
comprueba("el resumen dice con que ficheros se cruzo",
          (res["telemetria_externa"]["faltan"], res["telemetria_externa"]["maquinas"]), ([], n))
oi = json.loads(gzip.decompress(ALMACEN["cabina/interno/operativo.json.gz"]))
oa = json.loads(gzip.decompress(ALMACEN["cabina/amazon/operativo.json.gz"]))
ti, ta = oi["dias"][DIA]["telemetria"], oa["dias"][DIA]["telemetria"]
comprueba("interno: el dato de VenCloud (3 marcadas, ningun DEX suyo)", (ti["auditables"], ti["con_dex"]), (3, 0))
comprueba("  y las diferencias", ti["diferencias"]["solo_vencloud"], 1)
comprueba("Amazon: VenCloud no marca ninguna, y se dice", "sin_dato" in ta, True)
comprueba("la foto dice que ficheros hay", sorted(oi["foto"]["telemetria"]["ficheros"]),
          ["grupos", "nayax", "nebula", "prodelfi"])
pi = json.loads(ALMACEN["cabina/interno/telemetria.json"])
pa = json.loads(ALMACEN["cabina/amazon/telemetria.json"])
comprueba("la pagina del interno lleva las de fuera de VenCloud", len(pi["fuera"]), 4)
comprueba("la de Amazon no: no son de ningun cliente", pa["fuera"], None)
comprueba("y solo sus maquinas", sorted(x["matricula"] for x in pa["maquinas"]), ["15SE0771", "23FE1655"])

del ALMACEN["cabina/interno/telemetria.json"]
for t_ in TE.TIPOS:
    del ALMACEN[f"externo/telemetria/{t_}/actual.json"]
L.lambda_handler({}, None)
oi = json.loads(gzip.decompress(ALMACEN["cabina/interno/operativo.json.gz"]))
comprueba("sin ficheros, el cuadrado vuelve a ser el de VenCloud",
          "auditables" in oi["dias"][DIA]["telemetria"] or "sin_dato" in oi["dias"][DIA]["telemetria"], True)
comprueba("y no se escribe la pagina", "cabina/interno/telemetria.json" in ALMACEN, False)

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("La telemetria de fuera se lee y se cruza como se decidio.")
