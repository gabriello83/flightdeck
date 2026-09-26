"""
Extraccion nocturna de VenCloud hacia S3.

Fase 1: llama a la API y guarda la respuesta TAL CUAL, sin interpretarla.
Todavia no sabemos que formato devuelve GetReportV2, asi que primero
miramos y despues escribimos el intérprete. Guardar bytes no puede salir mal.

Solo usa la biblioteca estandar y boto3, que ya viene en Lambda. No hay
dependencias que empaquetar: este fichero se pega en el editor de la consola.

Variables de entorno necesarias:
  VENCLOUD_ENDPOINT  https://vencloudpro.eac.es/2311_api/webservices//VenCloudExternalApi/VenCloudExternalApi.svc
  VENCLOUD_TOKEN     el token
  VENCLOUD_EMPRESA   2311
  BUCKET             serunion-vending
  INFORMES           JSON con los informes a bajar (ver abajo)
  FORMATO_FECHA      %d/%m/%Y   (opcional)
"""

import datetime
import gzip
import json
import os
import urllib.error
import urllib.parse
import urllib.request

import boto3

s3 = boto3.client("s3")

ENDPOINT = os.environ["VENCLOUD_ENDPOINT"].rstrip("/")
TOKEN = os.environ["VENCLOUD_TOKEN"]
EMPRESA = os.environ.get("VENCLOUD_EMPRESA", "2311")
BUCKET = os.environ["BUCKET"]
FORMATO_FECHA = os.environ.get("FORMATO_FECHA", "%d/%m/%Y")
TIEMPO_ESPERA = int(os.environ.get("TIEMPO_ESPERA", "300"))

# Que informes se bajan y con que fechas. Se define en la variable de entorno
# INFORMES para poder cambiarlo sin tocar codigo. Ejemplo:
#
# {"ventas_dia":      {"informe": "101", "fechas": "ayer",   "ruta": "crudo/ventas"},
#  "maquina_dia":     {"informe": "102", "fechas": "ayer",   "ruta": "crudo/maquina_dia"},
#  "articulos":       {"informe": "103", "fechas": "ninguna","ruta": "maestros/articulos"},
#  "maquinas":        {"informe": "104", "fechas": "ninguna","ruta": "maestros/maquinas"}}
#
# "fechas" puede ser: "ayer" (desde=hasta=ayer), "mes_actual", o "ninguna".
INFORMES = json.loads(os.environ.get("INFORMES", "{}"))


def sin_token(texto):
    """El token no aparece nunca en los registros."""
    return texto.replace(TOKEN, "TOKEN")


def rango(modo, hoy):
    if modo == "ninguna":
        return []
    if modo == "ayer":
        ayer = hoy - datetime.timedelta(days=1)
        return [ayer.strftime(FORMATO_FECHA), ayer.strftime(FORMATO_FECHA)]
    if modo == "mes_actual":
        primero = hoy.replace(day=1)
        return [primero.strftime(FORMATO_FECHA), hoy.strftime(FORMATO_FECHA)]
    raise ValueError(f"modo de fechas desconocido: {modo}")


def llamar(informe, filtros, codificar_barra):
    """POST a GetReportV2. Devuelve (url_usada, cuerpo_en_bytes)."""
    segmento = "|".join([str(informe), *filtros])
    if codificar_barra:
        segmento = urllib.parse.quote(segmento, safe="/:")
    url = f"{ENDPOINT}/GetReportV2/{TOKEN}/{EMPRESA}/{segmento}"
    peticion = urllib.request.Request(url, data=b"", method="POST")
    peticion.add_header("Content-Type", "application/json")
    peticion.add_header("Content-Length", "0")
    with urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA) as respuesta:
        return url, respuesta.read()


def descargar(informe, filtros):
    """Prueba con la barra literal y, si falla, con la barra codificada."""
    errores = []
    for codificar in (False, True):
        try:
            return llamar(informe, filtros, codificar)
        except urllib.error.HTTPError as e:
            errores.append(f"{'codificada' if codificar else 'literal'}: HTTP {e.code} {sin_token(str(e.reason))}")
        except urllib.error.URLError as e:
            errores.append(f"{'codificada' if codificar else 'literal'}: {sin_token(str(e.reason))}")
    raise RuntimeError(" | ".join(errores))


def guardar(ruta_base, nombre, dia, cuerpo):
    clave = (
        f"{ruta_base}/anio={dia.year}/mes={dia.month:02d}/dia={dia.day:02d}/"
        f"{nombre}.gz"
    )
    s3.put_object(
        Bucket=BUCKET,
        Key=clave,
        Body=gzip.compress(cuerpo),
        ContentType="application/gzip",
        ServerSideEncryption="AES256",
    )
    return clave


def lambda_handler(event, context):
    hoy = datetime.date.today()
    resultado = {"fecha": hoy.isoformat(), "informes": [], "errores": []}

    if not INFORMES:
        raise RuntimeError("La variable de entorno INFORMES esta vacia")

    for nombre, cfg in INFORMES.items():
        try:
            filtros = rango(cfg.get("fechas", "ninguna"), hoy)
            url, cuerpo = descargar(cfg["informe"], filtros)
            clave = guardar(cfg["ruta"], nombre, hoy, cuerpo)
            resultado["informes"].append(
                {
                    "nombre": nombre,
                    "informe": cfg["informe"],
                    "filtros": filtros,
                    "bytes": len(cuerpo),
                    "clave": clave,
                    "primeros_200": cuerpo[:200].decode("utf-8", "replace"),
                }
            )
            print(f"OK  {nombre}: {len(cuerpo)} bytes -> s3://{BUCKET}/{clave}")
        except Exception as e:  # noqa: BLE001 - queremos que un fallo no pare el resto
            mensaje = sin_token(f"{type(e).__name__}: {e}")
            resultado["errores"].append({"nombre": nombre, "error": mensaje})
            print(f"FALLO {nombre}: {mensaje}")

    # El registro de la ejecucion se guarda tambien en S3, para poder mirar
    # despues que paso cada noche sin depender de los registros de Lambda.
    s3.put_object(
        Bucket=BUCKET,
        Key=f"registro/anio={hoy.year}/mes={hoy.month:02d}/{hoy.isoformat()}.json",
        Body=json.dumps(resultado, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )

    if resultado["errores"]:
        raise RuntimeError(f"{len(resultado['errores'])} informes fallaron: {resultado['errores']}")
    return resultado
