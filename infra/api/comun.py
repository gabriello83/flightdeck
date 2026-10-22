"""
Lo que comparten la API y el asistente.

Esta aqui por una razon de seguridad, no de estilo: la lectura de la sesion y la
del panel tienen que ser LA MISMA pieza en los dos sitios. Si cada Lambda tuviera
su copia, dentro de seis meses una de las dos se habria quedado atras, y ese es
el camino habitual por el que alguien acaba viendo datos que no son suyos.
"""

import base64
import gzip
import hashlib
import json
import os
import secrets
import time

import boto3

ddb = boto3.client("dynamodb")
s3 = boto3.client("s3")

TABLA = os.environ["TABLA"]
BUCKET = os.environ["BUCKET_DATOS"]
HORAS_SESION = int(os.environ.get("HORAS_SESION", "12"))

POR_DEFECTO = {
    "asistente_global": True,
    "limite_preguntas_dia": 40,
    "umbral_rentabilidad_mes": 350,
}


# ----------------------------------------------------------------------
# la tabla: una fila es un JSON
# ----------------------------------------------------------------------
def lee(pk, sk="FICHA"):
    r_ = ddb.get_item(Key={"pk": {"S": pk}, "sk": {"S": sk}}, TableName=TABLA)
    if "Item" not in r_:
        return None
    return json.loads(r_["Item"].get("dato", {}).get("S", "{}"))


def escribe(pk, dato, sk="FICHA", expira=None):
    item = {"pk": {"S": pk}, "sk": {"S": sk},
            "dato": {"S": json.dumps(dato, ensure_ascii=False)}}
    if expira:
        item["expira"] = {"N": str(int(expira))}
    ddb.put_item(TableName=TABLA, Item=item)


def borra(pk, sk="FICHA"):
    ddb.delete_item(TableName=TABLA, Key={"pk": {"S": pk}, "sk": {"S": sk}})


def lista(prefijo):
    """Todas las fichas de un tipo. La tabla es de cientos de filas, no de millones."""
    out, arranque = [], None
    while True:
        kw = {"TableName": TABLA,
              "FilterExpression": "begins_with(pk, :p) AND sk = :s",
              "ExpressionAttributeValues": {":p": {"S": prefijo}, ":s": {"S": "FICHA"}}}
        if arranque:
            kw["ExclusiveStartKey"] = arranque
        res = ddb.scan(**kw)
        for it in res.get("Items", []):
            d = json.loads(it.get("dato", {}).get("S", "{}"))
            d["_id"] = it["pk"]["S"].split("#", 1)[-1]
            out.append(d)
        arranque = res.get("LastEvaluatedKey")
        if not arranque:
            break
    return out


def config():
    c = dict(POR_DEFECTO)
    c.update(lee("CONFIG", "GLOBAL") or {})
    return c


# ----------------------------------------------------------------------
# sesion
# ----------------------------------------------------------------------
def huella(token):
    """De la cookie se guarda el resumen, no el token.

    Asi un volcado de la tabla no entrega sesiones con las que entrar.
    """
    return "SESION#" + hashlib.sha256(token.encode()).hexdigest()


def abre_sesion(correo):
    token = secrets.token_urlsafe(32)
    ahora = int(time.time())
    escribe(huella(token), {"correo": correo, "abierta": ahora},
            expira=ahora + HORAS_SESION * 3600)
    return token


def cierra_sesion(token):
    if token:
        borra(huella(token))


def quien_es(evento):
    """El usuario de esta peticion, o None.

    De aqui sale el perfil, y del perfil el ambito. La peticion no participa en
    esa decision: no hay ningun parametro con el que pedir el panel de otro.
    """
    token = None
    for c in evento.get("cookies", []) or []:
        if c.startswith("sesion="):
            token = c.split("=", 1)[1]
    if not token:
        return None
    fila = lee(huella(token))
    if not fila:
        return None
    usuario = lee(f"USUARIO#{fila['correo']}")
    if not usuario or usuario.get("estado") == "bloqueado":
        return None
    perfil = lee(f"PERFIL#{usuario.get('perfil_id', '')}") or {"tipo": "cliente"}
    usuario["correo"] = fila["correo"]
    perfil["perfil_id"] = usuario.get("perfil_id", "")
    perfil["cabina"], perfil["ambito"] = cabina_y_ambito(perfil["perfil_id"], perfil, usuario)
    return {"usuario": usuario, "perfil": perfil, "token": token}


# ----------------------------------------------------------------------
# la carpeta del panel de cada usuario (docs/65)
# ----------------------------------------------------------------------
def delegaciones_de(perfil, usuario):
    """Las delegaciones que el administrador le marco a ESTE usuario.

    Solo cuentan para el personal de Serunion: la delegacion es organizacion
    interna, un cliente no la ve (ve_delegaciones). Vacio = las de su perfil.
    """
    if perfil.get("tipo", "cliente") == "cliente":
        return []
    ds = usuario.get("delegaciones")
    if not isinstance(ds, list):
        return []
    return sorted({str(d).strip()[:80] for d in ds if str(d).strip()})[:200]


def cabina_de(perfil_id, delegaciones):
    """La carpeta de cabina/ de un perfil con esas delegaciones.

    La MISMA cuenta esta en lambda_agregados.cabina_de, que es quien escribe la
    carpeta: si dejaran de coincidir, el usuario se quedaria sin panel, nunca
    con el de otro. Las dos pruebas fijan el mismo valor.
    """
    ds = sorted({str(d) for d in delegaciones or []})
    if not perfil_id or not ds:
        return perfil_id
    return f"{perfil_id}~{hashlib.sha1(chr(10).join(ds).encode('utf-8')).hexdigest()[:12]}"


def cabina_y_ambito(perfil_id, perfil, usuario):
    """De que carpeta lee la sesion de este usuario, y con que ambito.

    El ambito se aplica al escribir: la Lambda de agregados escribe un panel por
    perfil y, para cada usuario del personal con delegaciones, uno con esas
    delegaciones y ninguna otra. Aqui solo se elige cual de los ya escritos le
    toca, y no hay ningun parametro de la peticion que entre en la cuenta.

    - Con delegaciones: su panel, `<perfil>~<huella>`. Las del usuario sustituyen
      a las que tuviera el perfil de antes; los clientes y centros del perfil,
      si los tiene, se quedan.
    - Del personal, sin delegaciones y con un perfil sin ambito: todo el parque,
      que es el panel del interno.
    - Lo demas, el de su perfil, como siempre.
    """
    ambito = dict(perfil.get("ambito") or {})
    ds = delegaciones_de(perfil, usuario)
    if ds:
        ambito["delegaciones"] = ds
        return cabina_de(perfil_id, ds), ambito
    if (perfil.get("tipo", "cliente") != "cliente" and perfil_id
            and not any(ambito.get(k) for k in ("clientes", "centros", "delegaciones"))):
        return "interno", ambito
    return perfil_id, ambito


# ----------------------------------------------------------------------
# respuestas HTTP
# ----------------------------------------------------------------------
def r(codigo, cuerpo_, cookies=None):
    resp = {
        "statusCode": codigo,
        "headers": {"content-type": "application/json; charset=utf-8",
                    "cache-control": "no-store"},
        "body": json.dumps(cuerpo_, ensure_ascii=False),
    }
    if cookies:
        resp["cookies"] = cookies
    return resp


def cookie_sesion(token, horas=None):
    edad = 0 if token == "" else (horas or HORAS_SESION) * 3600
    return f"sesion={token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age={edad}"


def cuerpo(evento):
    b = evento.get("body") or "{}"
    if evento.get("isBase64Encoded"):
        b = base64.b64decode(b).decode("utf-8")
    try:
        return json.loads(b) or {}
    except Exception:
        return {}


# ----------------------------------------------------------------------
# el panel
# ----------------------------------------------------------------------
def panel_de(perfil_id):
    """El panel de UN perfil. Lo escribio la Lambda de agregados ya filtrado."""
    if not perfil_id:
        return None
    try:
        b = s3.get_object(Bucket=BUCKET, Key=f"cabina/{perfil_id}/panel.json")["Body"].read()
    except Exception:
        return None
    if b[:2] == b"\x1f\x8b":
        b = gzip.decompress(b)
    return json.loads(b)
