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
    return {"usuario": usuario, "perfil": perfil, "token": token}


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
