"""
Extraccion nocturna de VenCloud hacia S3.

Baja los informes del manifiesto, guarda la respuesta cruda comprimida y deja un
registro de la ejecucion. Solo biblioteca estandar y boto3, que ya vienen en Lambda:
no hay nada que empaquetar.

LO UNICO QUE NO ESTA PROBADO CONTRA LA API REAL es la forma de la respuesta. Por eso
siempre se guardan los bytes tal cual ANTES de intentar interpretarlos: si el
intérprete falla, el dato no se pierde y se arregla el intérprete, no la noche.

Variables de entorno:
  VENCLOUD_ENDPOINT  https://.../VenCloudExternalApi.svc
  VENCLOUD_TOKEN_SECRETO  nombre del secreto en Secrets Manager (lo que usa la plantilla)
  VENCLOUD_TOKEN     el token en claro; solo para pruebas locales
  VENCLOUD_EMPRESA   2311
  BUCKET             destino
  MANIFIESTO         (opcional) clave del manifiesto en el bucket; por defecto config/manifiesto.json
  FORMATO_FECHA      (opcional) %d/%m/%Y
  VENTANA_DIAS       (opcional) dias hacia atras que se reprocesan; por defecto el del manifiesto
  SOLO               (opcional) lista de ids separados por coma, para una carga parcial
"""

import datetime
import gzip
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

import boto3

s3 = boto3.client("s3")

ENDPOINT = os.environ["VENCLOUD_ENDPOINT"].rstrip("/")


def _token():
    """El token sale de Secrets Manager; la variable en claro es solo para pruebas.

    Asi no aparece en la consola de Lambda, ni en una captura de pantalla, ni en
    el historial de quien mire la configuracion de la funcion.
    """
    secreto = os.environ.get("VENCLOUD_TOKEN_SECRETO")
    if secreto:
        sm = boto3.client("secretsmanager")
        return sm.get_secret_value(SecretId=secreto)["SecretString"].strip()
    return os.environ["VENCLOUD_TOKEN"]


TOKEN = _token()
EMPRESA = os.environ.get("VENCLOUD_EMPRESA", "2311")
BUCKET = os.environ["BUCKET"]
CLAVE_MANIFIESTO = os.environ.get("MANIFIESTO", "config/manifiesto.json")
FORMATO_FECHA = os.environ.get("FORMATO_FECHA", "%d/%m/%Y")
TIEMPO_ESPERA = int(os.environ.get("TIEMPO_ESPERA", "300"))
REINTENTOS = int(os.environ.get("REINTENTOS", "3"))
PAUSA = float(os.environ.get("PAUSA_ENTRE_LLAMADAS", "1"))


def sin_token(texto):
    """El token no aparece nunca en un registro, ni en un error, ni en S3."""
    return texto.replace(TOKEN, "TOKEN") if TOKEN else texto


# ----------------------------------------------------------------------
# manifiesto
# ----------------------------------------------------------------------
def manifiesto():
    cuerpo = s3.get_object(Bucket=BUCKET, Key=CLAVE_MANIFIESTO)["Body"].read()
    m = json.loads(cuerpo)
    solo = {x.strip() for x in os.environ.get("SOLO", "").split(",") if x.strip()}
    informes = [i for i in m["informes"] if not solo or i["id"] in solo]
    sin_numero = [i["id"] for i in informes if not i.get("informe")]
    if sin_numero:
        # Preferimos parar a bajar el informe equivocado en silencio.
        raise RuntimeError(
            "Estos informes no tienen numero asignado en el manifiesto: "
            + ", ".join(sin_numero)
        )
    return m, informes


# ----------------------------------------------------------------------
# fechas
# ----------------------------------------------------------------------
def dias_a_cargar(hoy, ventana):
    """Ayer, y los dias anteriores de la ventana de reproceso.

    La ventana existe porque hay filas que llegan tarde: la carga de una noche
    vuelve a pedir los dias anteriores y, como cada fila lleva su id, repetirlas
    no duplica nada.
    """
    return [hoy - datetime.timedelta(days=d) for d in range(1, ventana + 1)]


def filtros_de(clave_fecha, dia):
    """Los dos parametros de fecha que espera el informe, o ninguno."""
    if clave_fecha == "ninguna":
        return []
    f = dia.strftime(FORMATO_FECHA)
    return [f, f]


# ----------------------------------------------------------------------
# llamada
# ----------------------------------------------------------------------
def llamar(informe, filtros, codificar_barra):
    """POST a GetReportV2. Todos los parametros van en la ruta."""
    segmento = "|".join([str(informe), *filtros])
    if codificar_barra:
        segmento = urllib.parse.quote(segmento, safe="/:")
    url = f"{ENDPOINT}/GetReportV2/{TOKEN}/{EMPRESA}/{segmento}"
    peticion = urllib.request.Request(url, data=b"", method="POST")
    peticion.add_header("Content-Type", "application/json")
    peticion.add_header("Content-Length", "0")
    with urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA) as respuesta:
        return respuesta.read()


def descargar(informe, filtros):
    """Prueba barra literal y codificada, y reintenta con espera creciente.

    Reintenta en fallo de red y en 5xx. En 4xx no: un 404 no mejora esperando.
    """
    errores = []
    for intento in range(REINTENTOS):
        for codificar in (False, True):
            try:
                return llamar(informe, filtros, codificar)
            except urllib.error.HTTPError as e:
                errores.append(f"HTTP {e.code}")
                if e.code < 500:
                    raise RuntimeError(sin_token(f"HTTP {e.code} {e.reason}")) from None
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                errores.append(sin_token(str(e)))
        if intento < REINTENTOS - 1:
            time.sleep(2 ** intento)
    raise RuntimeError(" | ".join(errores[-4:]))


# ----------------------------------------------------------------------
# lectura tolerante de la respuesta
# ----------------------------------------------------------------------
def filas_de(cuerpo):
    """Cuenta las filas sin saber de antemano la forma exacta de la respuesta.

    GetReportV2 devuelve JSON con forma variable segun el informe. Esto reconoce
    las formas habituales y, si no reconoce ninguna, devuelve None en vez de
    inventarse un numero: el dato crudo ya esta guardado y se mira a mano.
    """
    try:
        d = json.loads(cuerpo)
    except Exception:
        return None
    if isinstance(d, list):
        return len(d)
    if isinstance(d, dict):
        for clave in ("Rows", "rows", "Data", "data", "Table", "Result", "d"):
            v = d.get(clave)
            if isinstance(v, list):
                return len(v)
            if isinstance(v, dict):
                for k2 in ("Rows", "rows", "Table", "results"):
                    if isinstance(v.get(k2), list):
                        return len(v[k2])
    return None


# ----------------------------------------------------------------------
# S3
# ----------------------------------------------------------------------
def guardar(destino, id_informe, dia, cuerpo):
    """Particionado por anio/mes/dia. Repetir una noche sobrescribe la misma clave."""
    if dia is None:  # maestro: foto completa, sin particion
        clave = f"{destino}/{id_informe}.json.gz"
    else:
        clave = (
            f"{destino}/anio={dia.year}/mes={dia.month:02d}/dia={dia.day:02d}/"
            f"{id_informe}.json.gz"
        )
    s3.put_object(
        Bucket=BUCKET,
        Key=clave,
        Body=gzip.compress(cuerpo),
        ContentType="application/gzip",
        ServerSideEncryption="AES256",
    )
    return clave


def guardar_registro(hoy, resultado):
    s3.put_object(
        Bucket=BUCKET,
        Key=f"registro/extraccion/anio={hoy.year}/mes={hoy.month:02d}/{hoy.isoformat()}.json",
        Body=json.dumps(resultado, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )


# ----------------------------------------------------------------------
# ejecucion
# ----------------------------------------------------------------------
def lambda_handler(event, context):
    hoy = datetime.date.today()
    m, informes = manifiesto()
    ventana = int(os.environ.get("VENTANA_DIAS", m.get("ventana_reproceso_dias", 3)))
    dias = dias_a_cargar(hoy, ventana)

    resultado = {
        "ejecucion": datetime.datetime.utcnow().isoformat() + "Z",
        "ventana_dias": ventana,
        "dias": [d.isoformat() for d in dias],
        "ok": [],
        "errores": [],
    }

    for cfg in informes:
        maestro = cfg["clave_fecha"] == "ninguna"
        objetivos = [None] if maestro else dias
        for dia in objetivos:
            etiqueta = cfg["id"] if dia is None else f"{cfg['id']} {dia.isoformat()}"
            try:
                cuerpo = descargar(cfg["informe"], filtros_de(cfg["clave_fecha"], dia))
                clave = guardar(cfg["destino"], cfg["id"], dia, cuerpo)
                filas = filas_de(cuerpo)
                resultado["ok"].append(
                    {
                        "id": cfg["id"],
                        "dia": dia.isoformat() if dia else None,
                        "bytes": len(cuerpo),
                        "filas": filas,
                        "clave": clave,
                    }
                )
                print(f"OK  {etiqueta}: {len(cuerpo)} bytes, {filas} filas -> {clave}")
            except Exception as e:  # noqa: BLE001 - un informe que falla no para la noche
                mensaje = sin_token(f"{type(e).__name__}: {e}")
                resultado["errores"].append({"id": cfg["id"], "dia": dia.isoformat() if dia else None, "error": mensaje})
                print(f"FALLO {etiqueta}: {mensaje}")
            time.sleep(PAUSA)

    resultado["resumen"] = {
        "informes": len(informes),
        "descargas_ok": len(resultado["ok"]),
        "descargas_fallidas": len(resultado["errores"]),
        "bytes": sum(x["bytes"] for x in resultado["ok"]),
    }
    guardar_registro(hoy, resultado)

    if resultado["errores"]:
        # Lambda marca la ejecucion como fallida para que salte la alarma de
        # CloudWatch, pero el registro ya esta guardado y lo que si bajo, bajado.
        raise RuntimeError(
            f"{len(resultado['errores'])} descargas fallaron de {len(resultado['ok']) + len(resultado['errores'])}"
        )
    return resultado["resumen"]
