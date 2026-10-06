"""
AWS de pega para las pruebas. DynamoDB, S3 y Cognito en memoria.

Se instala en sys.modules ANTES de importar las Lambdas, asi que ni boto3 ni la
red entran en juego. Lo justo para que las pruebas ejerciten el codigo de verdad.
"""

import datetime
import json
import types

TABLA = {}        # (pk, sk) -> item
OBJETOS = {}      # clave -> bytes
USUARIOS_COG = {} # correo -> {"clave":..., "temporal":bool}
CORREOS = []      # lo que se habria enviado por SES
WHATSAPPS = []    # lo que se habria enviado por WhatsApp


def limpia():
    TABLA.clear(); OBJETOS.clear(); USUARIOS_COG.clear()
    CORREOS.clear(); WHATSAPPS.clear()


class _Error(Exception):
    pass


class _DDB:
    def get_item(self, TableName, Key):
        clave = (Key["pk"]["S"], Key["sk"]["S"])
        return {"Item": TABLA[clave]} if clave in TABLA else {}

    def put_item(self, TableName, Item):
        TABLA[(Item["pk"]["S"], Item["sk"]["S"])] = Item
        return {}

    def delete_item(self, TableName, Key):
        TABLA.pop((Key["pk"]["S"], Key["sk"]["S"]), None)
        return {}

    def scan(self, TableName, FilterExpression=None, ExpressionAttributeValues=None, **kw):
        pref = ExpressionAttributeValues[":p"]["S"]
        sk = ExpressionAttributeValues[":s"]["S"]
        items = [v for (pk, s), v in TABLA.items() if pk.startswith(pref) and s == sk]
        return {"Items": items}


class _S3:
    exceptions = types.SimpleNamespace(NoSuchKey=_Error)

    def get_object(self, Bucket, Key):
        if Key not in OBJETOS:
            raise _Error(Key)
        return {"Body": types.SimpleNamespace(read=lambda: OBJETOS[Key])}

    def put_object(self, Bucket, Key, Body, **kw):
        OBJETOS[Key] = Body
        return {}

    def head_object(self, Bucket, Key):
        if Key not in OBJETOS:
            raise _Error(Key)
        return {"LastModified": datetime.datetime(2026, 10, 2, 4, 45,
                                                  tzinfo=datetime.timezone.utc)}


class _NoAutorizado(Exception):
    pass


class _NoExiste(Exception):
    pass


class _YaExiste(Exception):
    pass


class _ClaveMala(Exception):
    pass


class _Cognito:
    exceptions = types.SimpleNamespace(
        NotAuthorizedException=_NoAutorizado,
        UserNotFoundException=_NoExiste,
        UsernameExistsException=_YaExiste,
        InvalidPasswordException=_ClaveMala,
    )

    def admin_initiate_auth(self, UserPoolId, ClientId, AuthFlow, AuthParameters):
        correo = AuthParameters["USERNAME"]
        u = USUARIOS_COG.get(correo)
        if not u:
            raise _NoExiste(correo)
        if u["clave"] != AuthParameters["PASSWORD"]:
            raise _NoAutorizado(correo)
        if u.get("temporal"):
            return {"ChallengeName": "NEW_PASSWORD_REQUIRED", "Session": "reto-" + correo}
        return {"AuthenticationResult": {"AccessToken": "x"}}

    def admin_respond_to_auth_challenge(self, UserPoolId, ClientId, ChallengeName,
                                        Session, ChallengeResponses):
        correo = ChallengeResponses["USERNAME"]
        if Session != "reto-" + correo:
            raise Exception("reto no valido")
        if len(ChallengeResponses["NEW_PASSWORD"]) < 12:
            raise _ClaveMala("corta")
        USUARIOS_COG[correo] = {"clave": ChallengeResponses["NEW_PASSWORD"], "temporal": False}
        return {}

    def admin_create_user(self, UserPoolId, Username, UserAttributes,
                          TemporaryPassword, MessageAction=None):
        if Username in USUARIOS_COG:
            raise _YaExiste(Username)
        USUARIOS_COG[Username] = {"clave": TemporaryPassword, "temporal": True}
        return {}

    def admin_set_user_password(self, UserPoolId, Username, Password, Permanent):
        USUARIOS_COG[Username] = {"clave": Password, "temporal": not Permanent}
        return {}

    def admin_delete_user(self, UserPoolId, Username):
        USUARIOS_COG.pop(Username, None)
        return {}


class _SES:
    def send_email(self, Source, Destination, Message):
        CORREOS.append({"de": Source, "para": Destination["ToAddresses"],
                        "asunto": Message["Subject"]["Data"],
                        "texto": Message["Body"]["Text"]["Data"]})
        return {"MessageId": "x"}


class _SM:
    def __init__(self, secretos=None):
        # `secretos or {}` seria un fallo: un diccionario vacio es falsy, asi que
        # al instalarse (cuando todavia no hay secretos) se creaba uno NUEVO y
        # quedaba desconectado del que las pruebas rellenan despues.
        self.secretos = {} if secretos is None else secretos

    def get_secret_value(self, SecretId):
        if SecretId not in self.secretos:
            raise _Error(SecretId)
        return {"SecretString": self.secretos[SecretId]}


SECRETOS = {}


def instala():
    """Pone un boto3 falso en sys.modules. Llamar antes de importar las Lambdas."""
    import sys
    cliente = {"dynamodb": _DDB(), "s3": _S3(), "cognito-idp": _Cognito(),
               "ses": _SES(), "secretsmanager": _SM(SECRETOS)}
    sys.modules["boto3"] = types.SimpleNamespace(client=lambda nombre, **kw: cliente[nombre])
    return cliente


# ----------------------------------------------------------------------
# ayudas para montar el escenario
# ----------------------------------------------------------------------
def pon_fila(pk, dato, sk="FICHA"):
    TABLA[(pk, sk)] = {"pk": {"S": pk}, "sk": {"S": sk},
                       "dato": {"S": json.dumps(dato, ensure_ascii=False)}}


def lista(prefijo):
    """Las fichas que hay en la tabla falsa, para comprobar en las pruebas."""
    out = []
    for (pk, sk), it in TABLA.items():
        if pk.startswith(prefijo) and sk == "FICHA":
            d = json.loads(it["dato"]["S"])
            d["_id"] = pk.split("#", 1)[-1]
            out.append(d)
    return out


def pon_panel(perfil, panel):
    OBJETOS[f"cabina/{perfil}/panel.json"] = json.dumps(panel).encode()


def peticion(metodo, ruta, cuerpo=None, cookie=None, origen="same-origin", query=None):
    """API Gateway entrega el path SIN la query: la query va en su propio campo."""
    ev = {"requestContext": {"http": {"method": metodo, "path": ruta}},
          "headers": {"sec-fetch-site": origen},
          "queryStringParameters": query or {},
          "rawQueryString": "&".join(f"{k}={v}" for k, v in (query or {}).items()),
          "body": json.dumps(cuerpo) if cuerpo is not None else None}
    if cookie:
        ev["cookies"] = [f"sesion={cookie}"]
    return ev


def cookie_de(respuesta):
    for c in respuesta.get("cookies", []):
        if c.startswith("sesion="):
            return c.split("=", 1)[1].split(";")[0]
    return None


def cuerpo_de(respuesta):
    return json.loads(respuesta["body"])
