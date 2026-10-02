"""
El motor de alarmas. Corre cada hora.

Hace tres cosas, en este orden:
  1. evalua las alarmas activas contra el panel del perfil al que pertenecen
  2. avisa por correo o WhatsApp lo que haya saltado, respetando horas de silencio
  3. vacia la cola de WhatsApp y de altas de incidencia que dejo la API

Una regla de diseno que importa mas que el resto: UNA ALARMA QUE NO SE PUEDE
EVALUAR SE DICE, NO SE DA POR BUENA. Si su fuente todavia no esta calculada en
el panel, no se evalua a 0 en silencio: queda marcada como no evaluable y sale
en el registro y en el panel de administracion. Una alarma que calla porque no
sabe medirse es peor que no tenerla, porque alguien confia en ella.
"""

import datetime
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

import boto3

from comun import escribe, lee, lista, panel_de, borra

ses = boto3.client("ses")
sm = boto3.client("secretsmanager")

REMITENTE = os.environ.get("REMITENTE", "")
SECRETO_WA = os.environ.get("SECRETO_WHATSAPP", "")
HORAS_REPETICION = int(os.environ.get("HORAS_REPETICION", "24"))


from catalogo import CATALOGO


def valor_en(panel, ruta):
    """Recorre una ruta con puntos. Admite indices negativos: -1 es el ultimo mes."""
    actual = panel
    for trozo in ruta.split("."):
        if isinstance(actual, list):
            try:
                actual = actual[int(trozo)]
            except (ValueError, IndexError):
                return None
        elif isinstance(actual, dict):
            if trozo not in actual:
                return None
            actual = actual[trozo]
        else:
            return None
    return actual if isinstance(actual, (int, float)) else None


def compara(valor, signo, umbral):
    if signo == ">":
        return valor > umbral
    if signo == ">=":
        return valor >= umbral
    if signo == "<":
        return valor < umbral
    if signo == "<=":
        return valor <= umbral
    if signo in ("=", "=="):
        return valor == umbral
    return False


def en_silencio(silencio, hora):
    """Las horas de silencio. Admite tramos que cruzan la medianoche (22 a 7)."""
    desde = int((silencio or {}).get("desde", 22))
    hasta = int((silencio or {}).get("hasta", 7))
    if desde == hasta:
        return False
    if desde < hasta:
        return desde <= hora < hasta
    return hora >= desde or hora < hasta


def ya_avisada(ident):
    e = lee(f"ESTADO_ALARMA#{ident}", "ULTIMO") or {}
    return (time.time() - float(e.get("cuando", 0))) < HORAS_REPETICION * 3600


def marca_avisada(ident, valor):
    escribe(f"ESTADO_ALARMA#{ident}", {"cuando": time.time(), "valor": valor}, "ULTIMO")


# ----------------------------------------------------------------------
# envios
# ----------------------------------------------------------------------
def manda_correo(destinos, asunto, texto):
    if not REMITENTE:
        return False, "No hay remitente verificado en SES."
    correos = [d for d in destinos if "@" in d]
    if not correos:
        return False, "La alarma no tiene ningun correo de destino."
    ses.send_email(
        Source=REMITENTE,
        Destination={"ToAddresses": correos[:20]},
        Message={"Subject": {"Data": asunto, "Charset": "UTF-8"},
                 "Body": {"Text": {"Data": texto, "Charset": "UTF-8"}}},
    )
    return True, ""


_wa = None


def _config_whatsapp():
    """El secreto trae el proveedor completo: identificador, token y plantilla."""
    global _wa
    if _wa is None:
        if not SECRETO_WA:
            _wa = {}
        else:
            try:
                _wa = json.loads(sm.get_secret_value(SecretId=SECRETO_WA)["SecretString"])
            except Exception:
                _wa = {}
    return _wa


def manda_whatsapp(telefono, texto):
    """Meta Cloud API. Mientras el secreto este vacio, no se envia y se dice.

    No se inventa un envio: si no hay proveedor configurado, el aviso queda en la
    bandeja con el motivo, y el que lo lea sabe que el WhatsApp no ha salido.
    """
    cfg = _config_whatsapp()
    if not cfg.get("token") or not cfg.get("numero_id"):
        return False, "WhatsApp sin configurar: falta el token del proveedor."
    url = f"https://graph.facebook.com/v21.0/{cfg['numero_id']}/messages"
    cuerpo = json.dumps({
        "messaging_product": "whatsapp",
        "to": telefono.lstrip("+"),
        "type": "text",
        "text": {"body": texto[:4000]},
    }).encode()
    pet = urllib.request.Request(url, data=cuerpo, method="POST")
    pet.add_header("Authorization", f"Bearer {cfg['token']}")
    pet.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(pet, timeout=20) as resp:
            resp.read()
        return True, ""
    except urllib.error.HTTPError as e:
        return False, f"El proveedor responde {e.code}."
    except Exception as e:  # noqa: BLE001
        return False, f"No se ha podido enviar: {type(e).__name__}."


def telefono_de(destino):
    """Un destino puede ser un telefono o el id de un empleado de la agenda."""
    if destino.startswith("+"):
        return destino
    ficha = lee(f"TELEFONO#{destino}")
    return (ficha or {}).get("telefono", "")


# ----------------------------------------------------------------------
# la cola que dejo la API
# ----------------------------------------------------------------------
def vacia_cola():
    hechos, pendientes = 0, 0
    for item in lista("COLA#"):
        ident = item["_id"]
        if item.get("tipo") == "whatsapp":
            tel = telefono_de(item.get("destino", ""))
            if not tel:
                guarda_aviso("WhatsApp sin destino", f"No hay telefono para {item.get('destino')}.",
                             item.get("pedido_por", ""))
                borra(f"COLA#{ident}")
                continue
            ok, motivo = manda_whatsapp(tel, item.get("texto", ""))
            if ok:
                borra(f"COLA#{ident}")
                hechos += 1
            else:
                guarda_aviso("WhatsApp no enviado", motivo, item.get("pedido_por", ""))
                pendientes += 1
        elif item.get("tipo") == "incidencia":
            # El alta en VenCloud es una ESCRITURA en el ERP. Hasta tener el
            # endpoint y el permiso confirmados, no se inventa la llamada: la
            # peticion queda en cola, visible, y nadie cree que se ha dado de alta.
            pendientes += 1
    return hechos, pendientes


def guarda_aviso(titulo, texto, para=""):
    ident = f"{int(time.time())}-{abs(hash(titulo)) % 10000}"
    escribe(f"AVISO#{ident}", {
        "titulo": titulo[:120], "texto": texto[:600], "para": para,
        "cuando": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })


# ----------------------------------------------------------------------
# ejecucion
# ----------------------------------------------------------------------
def lambda_handler(evento, contexto):
    ahora = datetime.datetime.now(datetime.timezone.utc)
    hora_madrid = (ahora.hour + 2) % 24  # suficiente para la ventana de silencio
    paneles = {}
    resultado = {"saltadas": [], "en_silencio": [], "no_evaluables": [], "ok": 0}

    for al in lista("ALARMA#"):
        ident = al["_id"]
        if not al.get("activa", True):
            continue
        clave = f"{al.get('fuente')}.{al.get('campo')}"
        entrada = CATALOGO.get(clave)
        if not entrada:
            resultado["no_evaluables"].append({"id": ident, "motivo": f"Fuente desconocida: {clave}"})
            continue
        ruta, etiqueta, unidad = entrada
        if ruta is None:
            resultado["no_evaluables"].append({
                "id": ident, "motivo": f"«{etiqueta}» todavia no se calcula en los agregados."})
            continue

        perfil = al.get("perfil", "interno")
        if perfil not in paneles:
            paneles[perfil] = panel_de(perfil)
        panel = paneles[perfil]
        if panel is None:
            resultado["no_evaluables"].append({"id": ident, "motivo": f"Sin panel para el perfil {perfil}."})
            continue

        valor = valor_en(panel, ruta)
        if valor is None:
            resultado["no_evaluables"].append({"id": ident, "motivo": f"El panel no trae {ruta}."})
            continue
        resultado["ok"] += 1

        if not compara(valor, al.get("comparacion", ">"), float(al.get("umbral", 0))):
            continue
        if en_silencio(al.get("silencio"), hora_madrid):
            resultado["en_silencio"].append(ident)
            continue
        if ya_avisada(ident):
            continue

        titulo = f"[digivend] {al.get('nombre')}"
        texto = (f"{etiqueta}: {valor} {unidad}\n"
                 f"Regla: {al.get('comparacion')} {al.get('umbral')} {unidad}\n"
                 f"Perfil: {perfil}\n"
                 f"Periodo: {panel.get('periodo', {}).get('desde')} a "
                 f"{panel.get('periodo', {}).get('hasta')}\n\n"
                 f"Este aviso se repite como mucho una vez cada {HORAS_REPETICION} h.")

        enviados, fallos = [], []
        for canal in al.get("canal", ["correo"]):
            if canal == "correo":
                ok, motivo = manda_correo(al.get("destinos", []), titulo, texto)
            elif canal == "whatsapp":
                ok, motivo = True, ""
                for dest in al.get("destinos", []):
                    tel = telefono_de(dest)
                    if not tel:
                        ok, motivo = False, f"Sin telefono para {dest}."
                        continue
                    ok, motivo = manda_whatsapp(tel, f"{titulo}\n{texto}")
            else:
                ok, motivo = False, f"Canal desconocido: {canal}"
            (enviados if ok else fallos).append(canal if ok else f"{canal}: {motivo}")

        guarda_aviso(titulo, texto + ("\nNo enviado por " + "; ".join(fallos) if fallos else ""))
        marca_avisada(ident, valor)
        resultado["saltadas"].append({"id": ident, "valor": valor,
                                      "enviados": enviados, "fallos": fallos})

    hechos, pendientes = vacia_cola()
    resultado["cola"] = {"enviados": hechos, "pendientes": pendientes}
    resultado["momento"] = ahora.isoformat()

    # Las no evaluables se guardan para que salgan en el panel de admin: una
    # alarma que no sabe medirse tiene que verse, no quedarse en un log.
    escribe("ESTADO_ALARMAS", resultado, "ULTIMA_REVISION")
    print(json.dumps(resultado, ensure_ascii=False))
    return resultado
