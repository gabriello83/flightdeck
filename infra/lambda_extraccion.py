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
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import boto3

s3 = boto3.client("s3")

def _endpoint(url):
    """Quita la doble barra del endpoint: el servicio redirige para quitarla.

    Dejarla cuesta una redireccion en cada una de las 74 llamadas de la noche,
    para acabar exactamente en la misma URL.
    """
    esquema, resto = url.rstrip("/").split("://", 1)
    return esquema + "://" + resto.replace("//", "/")


ENDPOINT = _endpoint(os.environ["VENCLOUD_ENDPOINT"])


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
# ISO, no dd/mm/aaaa. La barra de una fecha va dentro de la RUTA, y IIS rechaza
# con un 404 cualquier barra codificada (%2F) en la ruta: es una proteccion suya
# contra el doble escapado, y no se puede sortear desde el cliente. Con
# 2026-09-30 la ruta encaja. Medido: dd/MM/yyyy daba 404 y la ISO, 307.
FORMATO_FECHA = os.environ.get("FORMATO_FECHA", "%Y-%m-%d")
# GET, no POST: con la barra final el servicio contesta 405 a un POST, que es su
# forma de decir "la ruta es buena, el metodo no".
METODO = os.environ.get("VENCLOUD_METODO", "GET")
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
# Un abridor que NO sigue las redirecciones solo. Urllib, en un POST, se niega
# a seguir un 307 y lanza el error sin mas; asi al menos podemos leer a donde
# nos manda el servidor, que es la mitad del diagnostico.
class _SinSeguirRedirecciones(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


ABRIDOR = urllib.request.build_opener(_SinSeguirRedirecciones)

MAX_SALTOS = 3


def una_llamada(url, metodo="POST", cuerpo=b"", espera=None):
    """UNA peticion, sin seguir redirecciones. Devuelve (codigo, cabeceras, bytes).

    Un 3xx no es una excepcion aqui: es una respuesta mas, con su Location, que
    es lo que hay que leer.
    """
    peticion = urllib.request.Request(url, data=cuerpo, method=metodo)
    peticion.add_header("Content-Type", "application/json")
    peticion.add_header("Accept", "application/json")
    try:
        with ABRIDOR.open(peticion, timeout=espera or TIEMPO_ESPERA) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


def llamar(url, metodo="POST", cuerpo=b""):
    """Como una_llamada, pero siguiendo las redirecciones sin cambiar de metodo.

    Si se agotan los saltos DEVUELVE la ultima respuesta en vez de lanzar: un
    bucle de redirecciones tiene que acabar en "HTTP 307 -> a donde", que es
    informacion, y no en "demasiados saltos", que no dice nada.
    """
    codigo, cabeceras, datos = 0, {}, b""
    for _ in range(MAX_SALTOS + 1):
        codigo, cabeceras, datos = una_llamada(url, metodo, cuerpo)
        destino = cabeceras.get("Location")
        if codigo in (301, 302, 303, 307, 308) and destino:
            # 307 y 308 conservan el metodo; 301, 302 y 303 lo pasan a GET.
            url = urllib.parse.urljoin(url, destino)
            if codigo in (301, 302, 303):
                metodo, cuerpo = "GET", None
            continue
        break
    return codigo, cabeceras, datos


def rutas_posibles(informe, filtros):
    """El segmento de parametros, en las dos formas que el servicio acepta.

    Con las fechas en ISO ya no hay barras que codificar, asi que lo unico que
    varia es la barra vertical: el servicio la acepta literal y la reescribe a
    %7C el solo. Se dejan las dos por si algun dia deja de hacerlo.
    """
    bruto = "|".join([str(informe), *filtros])
    return list(dict.fromkeys([urllib.parse.quote(bruto, safe=""), bruto]))


def descargar(informe, filtros):
    """Prueba las formas de ruta y reintenta con espera creciente.

    Reintenta en fallo de red y en 5xx. En 4xx no espera —un 404 no mejora
    esperando— pero SI prueba la siguiente forma de ruta, porque un 404 puede
    ser exactamente eso: la ruta mal montada.
    """
    errores = []
    for intento in range(REINTENTOS):
        reintentable = False
        for segmento in rutas_posibles(informe, filtros):
            # La barra final no es cosmetica: sin ella el servicio contesta 307
            # para anadirla, y nos cuesta una redireccion por llamada.
            url = f"{ENDPOINT}/GetReportV2/{TOKEN}/{EMPRESA}/{segmento}/"
            try:
                codigo, cabeceras, cuerpo = llamar(url, METODO)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                errores.append(sin_token(str(e)))
                reintentable = True
                continue
            if codigo == 200:
                return cuerpo
            detalle = f"HTTP {codigo}"
            if codigo == 405 and cabeceras.get("Allow"):
                detalle += f" (acepta {cabeceras['Allow']})"
            if cabeceras.get("Location"):
                detalle += f" -> {sin_token(cabeceras['Location'])}"
            errores.append(detalle)
            if codigo >= 500:
                reintentable = True
        if not reintentable or intento == REINTENTOS - 1:
            break
        time.sleep(2 ** intento)
    raise RuntimeError(" | ".join(dict.fromkeys(errores))[:400])


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
# sonda: descubrir la forma real de la API en UNA sola ejecucion
# ----------------------------------------------------------------------
# Se lanza con el evento de prueba {"sonda": true}. No escribe nada en S3: solo
# llama y cuenta lo que contesta cada forma. Existe porque ir probando de una en
# una, con una persona de intermediario, cuesta un dia; esto cuesta un minuto.

def _limpio(datos, limite=300):
    """El texto util, sin la hojarasca HTML.

    Las paginas de error de WCF son 1.500 bytes de CSS y una sola frase al
    final: «Extremo no encontrado». Quedarse con los primeros 300 caracteres
    deja justo el CSS y esconde el mensaje, que es lo unico que importa.
    """
    texto = datos.decode("utf-8", "replace") if datos else ""
    if "<" in texto[:200]:
        texto = re.sub(r"(?is)<(style|script|head)[^>]*>.*?</\1>", " ", texto)
        texto = re.sub(r"(?s)<[^>]+>", " ", texto)
        texto = html.unescape(texto)
    return " ".join(texto.split())[:limite]


def _sin_doble_barra(url):
    """La doble barra del endpoint es sospechosa: puede ser lo que redirige."""
    esquema, resto = url.split("://", 1)
    return esquema + "://" + resto.replace("//", "/")


def sonda(event):
    base = ENDPOINT
    base1 = _sin_doble_barra(ENDPOINT)

    # Un maestro y un incremental de verdad, sacados del manifiesto.
    try:
        _, informes = manifiesto()
        maestro = next(i["informe"] for i in informes if i["clave_fecha"] == "ninguna")
        incremental = next(i["informe"] for i in informes if i["clave_fecha"] != "ninguna")
    except Exception:
        maestro, incremental = 157, 105

    t, e = TOKEN, EMPRESA
    base = ENDPOINT                      # ya viene sin la doble barra
    ayer = datetime.date.today() - datetime.timedelta(days=1)

    def ruta(parametros):
        return f"{base}/GetReportV2/{t}/{e}/" + urllib.parse.quote(parametros, safe="") + "/"

    iso = ayer.strftime("%Y-%m-%d")
    casos = [
        # --- la candidata, y la prueba de que el metodo es ese -------------
        ("maestro GET, barra final",   "GET",     ruta(str(maestro)), b""),
        ("maestro POST (para Allow)",  "POST",    ruta(str(maestro)), b""),
        ("maestro OPTIONS",            "OPTIONS", ruta(str(maestro)), b""),

        # --- el incremental, que es el que lleva fechas --------------------
        ("incremental GET ISO",        "GET",  ruta(f"{incremental}|{iso}|{iso}"), b""),
        ("incremental, | literal",     "GET",
         f"{base}/GetReportV2/{t}/{e}/{incremental}|{iso}|{iso}/", b""),

        # --- por si el informe interpreta mal la ISO -----------------------
        ("fecha dd-MM-yyyy",           "GET", ruta(f"{incremental}|{ayer.strftime('%d-%m-%Y')}|{ayer.strftime('%d-%m-%Y')}"), b""),
        ("fecha yyyyMMdd",             "GET", ruta(f"{incremental}|{ayer.strftime('%Y%m%d')}|{ayer.strftime('%Y%m%d')}"), b""),
        ("fecha ISO con hora",         "GET", ruta(f"{incremental}|{iso} 00:00:00|{iso} 23:59:59"), b""),

        # --- una ventana mas ancha, por si ayer no tiene filas -------------
        ("incremental, mes de agosto", "GET", ruta(f"{incremental}|2026-08-01|2026-08-31"), b""),
    ]

    salida = []
    for nombre, metodo, url, cuerpo in casos:
        try:
            codigo, cabeceras, datos = una_llamada(url, metodo, cuerpo, espera=25)
            fila = {
                "caso": nombre,
                "metodo": metodo,
                "url": sin_token(url),
                "codigo": codigo,
                "redirige_a": sin_token(cabeceras.get("Location", "")) or None,
                "tipo": cabeceras.get("Content-Type", ""),
                "acepta": cabeceras.get("Allow"),
                "bytes": len(datos or b""),
                # La pagina de ayuda, si existe, lista TODAS las operaciones y
                # sus plantillas de URI: ahi se acaba el misterio, asi que de esa
                # se guarda mas texto.
                "respuesta": _limpio(datos, 400),
            }
        except Exception as ex:  # noqa: BLE001
            fila = {"caso": nombre, "metodo": metodo, "url": sin_token(url),
                    "error": sin_token(f"{type(ex).__name__}: {ex}")}
        salida.append(fila)
        print(f"{fila.get('codigo', '---'):>4}  {nombre:28} "
              f"{fila.get('bytes', 0):>7} B  {fila.get('acepta') or fila.get('redirige_a') or ''}")
        time.sleep(0.3)

    print(json.dumps(salida, ensure_ascii=False, indent=1))
    return {"sonda": salida}


# ----------------------------------------------------------------------
# ejecucion
# ----------------------------------------------------------------------
def lambda_handler(event, context):
    if (event or {}).get("sonda"):
        return sonda(event)

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
