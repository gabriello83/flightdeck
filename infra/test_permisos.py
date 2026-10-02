"""
Que cada Lambda tenga permiso para lo que su codigo hace de verdad.

Esta prueba existe porque el fallo ya pasó, y es de los peores: el codigo es
correcto, las pruebas pasan, se despliega, y la consola entera contesta 500
porque al rol le faltaba `dynamodb:Scan`. No se ve hasta produccion, y lo que se
lee en pantalla («Error interno») no dice nada de IAM.

Lo que comprueba, leyendo la plantilla y el codigo:

  1. Cada llamada a AWS del codigo esta en la tabla de equivalencias de abajo.
     Si alguien anade una llamada nueva, la prueba falla hasta que se diga que
     permiso necesita: es lo que obliga a pensarlo.
  2. El ROL de cada Lambda permite todas las acciones que su codigo usa.
  3. La FRONTERA de permisos tambien. Es un techo: si una accion no esta en la
     frontera, dársela al rol no sirve de nada, y ese es el fallo que mas cuesta
     ver porque el rol «parece» correcto.

    python3 infra/test_permisos.py
"""

import io
import os
import re
import sys

import yaml

AQUI = os.path.dirname(os.path.abspath(__file__))


class _Suelto(yaml.SafeLoader):
    """CloudFormation lleva !Sub, !Ref, !GetAtt... que a PyYAML no le constan."""


def _etiqueta(loader, sufijo, nodo):
    if isinstance(nodo, yaml.ScalarNode):
        return loader.construct_scalar(nodo)
    if isinstance(nodo, yaml.SequenceNode):
        return loader.construct_sequence(nodo)
    return loader.construct_mapping(nodo)


_Suelto.add_multi_constructor("!", _etiqueta)

# llamada de boto3 -> accion de IAM
EQUIVALENCIAS = {
    "ddb.get_item": "dynamodb:GetItem",
    "ddb.put_item": "dynamodb:PutItem",
    "ddb.update_item": "dynamodb:UpdateItem",
    "ddb.delete_item": "dynamodb:DeleteItem",
    "ddb.query": "dynamodb:Query",
    "ddb.scan": "dynamodb:Scan",
    "ddb.batch_get_item": "dynamodb:BatchGetItem",
    # HeadObject se autoriza con s3:GetObject: no hay un s3:HeadObject.
    "s3.get_object": "s3:GetObject",
    "s3.head_object": "s3:GetObject",
    "cog.admin_initiate_auth": "cognito-idp:AdminInitiateAuth",
    "cog.admin_respond_to_auth_challenge": "cognito-idp:AdminRespondToAuthChallenge",
    "cog.admin_create_user": "cognito-idp:AdminCreateUser",
    "cog.admin_set_user_password": "cognito-idp:AdminSetUserPassword",
    "cog.admin_delete_user": "cognito-idp:AdminDeleteUser",
    "cog.admin_get_user": "cognito-idp:AdminGetUser",
    "ses.send_email": "ses:SendEmail",
    "sm.get_secret_value": "secretsmanager:GetSecretValue",
}

# que modulos lleva cada zip, y a que rol van
LAMBDAS = {
    "RolApi":        ["comun.py", "autorizacion.py", "catalogo.py", "lambda_api.py"],
    "RolAlarmas":    ["comun.py", "autorizacion.py", "catalogo.py", "lambda_alarmas.py"],
    "RolAsistente":  ["comun.py", "autorizacion.py", "lambda_asistente.py"],
}

# Lo que cada modulo usa de verdad de `comun.py`. Sin esto, `comun` obligaria a
# dar a todas las Lambdas todo lo que cualquiera de ellas necesita.
COMUN_POR_ROL = {
    "RolApi":       {"lee", "escribe", "borra", "lista", "panel_de"},
    "RolAlarmas":   {"lee", "escribe", "borra", "lista", "panel_de"},
    "RolAsistente": {"lee", "escribe", "panel_de"},
}
COMUN_USA = {           # funcion de comun.py -> llamadas de boto3
    "lee": {"ddb.get_item"},
    "escribe": {"ddb.put_item"},
    "borra": {"ddb.delete_item"},
    "lista": {"ddb.scan"},
    "panel_de": {"s3.get_object"},
}

RE_LLAMADA = re.compile(r"\b((?:ddb|s3|cog|ses|sm)\.[a-z_]+)\s*\(")

fallos = []


def comprueba(que, ok, detalle=""):
    print(f"  {'ok   ' if ok else 'FALLO'} {que}{'' if ok else ' · ' + detalle}")
    if not ok:
        fallos.append(que)


def llamadas_de(fichero):
    texto = io.open(os.path.join(AQUI, "api", fichero), encoding="utf-8").read()
    # Fuera la cadena del recetario del asistente y los comentarios: ahi puede
    # haber texto que parece una llamada y no lo es.
    texto = re.sub(r'"""(?:.|\n)*?"""', "", texto)
    texto = re.sub(r"^\s*#.*$", "", texto, flags=re.M)
    return set(RE_LLAMADA.findall(texto))


def acciones_del(rol):
    usadas = set()
    for fichero in LAMBDAS[rol]:
        if fichero == "comun.py":
            for f in COMUN_POR_ROL[rol]:
                usadas |= COMUN_USA[f]
            continue
        usadas |= llamadas_de(fichero)
    return usadas


def permitidas(doc):
    """Todas las acciones de todas las sentencias de una politica."""
    out = set()

    def mete(x):
        if isinstance(x, str):
            out.add(x)
        elif isinstance(x, list):
            for y in x:
                mete(y)

    def anda(n):
        if isinstance(n, dict):
            if "Action" in n and n.get("Effect", "Allow") == "Allow":
                mete(n["Action"])
            for v in n.values():
                anda(v)
        elif isinstance(n, list):
            for v in n:
                anda(v)

    anda(doc)
    return out


print("La plantilla da a cada Lambda lo que su codigo usa\n")
plantilla = yaml.load(io.open(os.path.join(AQUI, "plantilla-web.yaml"), encoding="utf-8"),
                      Loader=_Suelto)
recursos = plantilla["Resources"]

frontera = permitidas(recursos["Frontera"]["Properties"]["PolicyDocument"])

print("Toda llamada a AWS del codigo tiene su accion de IAM escrita")
for rol, ficheros in LAMBDAS.items():
    for fichero in ficheros:
        if fichero == "comun.py":
            continue
        for llamada in llamadas_de(fichero):
            comprueba(f"{fichero}: {llamada}", llamada in EQUIVALENCIAS,
                      "anadela a EQUIVALENCIAS y mira que permiso necesita")

for rol in LAMBDAS:
    print(f"\n{rol}")
    usadas = acciones_del(rol)
    rolp = permitidas(recursos[rol]["Properties"])
    for llamada in sorted(usadas):
        accion = EQUIVALENCIAS.get(llamada)
        if not accion:
            continue
        comprueba(f"el rol permite {accion} ({llamada})", accion in rolp,
                  "el codigo lo llama y el rol no lo tiene")
        # El techo manda: si no esta en la frontera, dárselo al rol no sirve.
        comprueba(f"y la frontera lo deja pasar: {accion}", accion in frontera,
                  "esta en el rol pero la frontera lo deniega, asi que no se puede")

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos[:6])}"
          + (" ..." if len(fallos) > 6 else ""))
    sys.exit(1)
print("Los permisos cuadran con el codigo.")
