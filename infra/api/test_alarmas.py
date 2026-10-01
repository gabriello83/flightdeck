"""
El motor de alarmas.

La prueba que mas importa es la de las no evaluables: una alarma cuya fuente
todavia no se calcula NO puede pasar por «no ha saltado». Tiene que decirse.

    python3 infra/api/test_alarmas.py
"""

import json
import os
import sys

AQUI = __file__.rsplit("/", 1)[0]
sys.path.insert(0, AQUI)

import falsos  # noqa: E402

falsos.instala()
falsos.SECRETOS.clear()
os.environ.update(TABLA="t", BUCKET_DATOS="b", REMITENTE="avisos@serunion.es",
                  SECRETO_WHATSAPP="s/wa")

import lambda_alarmas as L  # noqa: E402

fallos = []


def comprueba(que, obtenido, esperado):
    if obtenido == esperado:
        print(f"  ok    {que}")
    else:
        print(f"  FALLO {que}: {obtenido!r} != {esperado!r}")
        fallos.append(que)


PANEL = {
    "periodo": {"desde": "2026-06-03", "hasta": "2026-09-30"},
    "servicio": {"merma": {"caducidad": {"euros": 2374.53}}},
    "jornadas": {"temperatura_fuera": 115, "km_total": 41000},
    "dinero": {"periodos": [{"periodo": "2026-08", "efectivo_sin_telemetria": 1000, "pct_ciego": 40},
                            {"periodo": "2026-09", "efectivo_sin_telemetria": 122327, "pct_ciego": 93}]},
    "sat": {"averias_tecnicas": 6400, "horas_cierre": {"mediana": 94.4}},
    "inventario": {"cumplimiento": {"pct_en_norma": 8.6}},
}


def escenario(alarmas, hora=12):
    falsos.limpia()
    falsos.SECRETOS.clear()
    falsos.pon_panel("interno", PANEL)
    for i, a in enumerate(alarmas):
        falsos.pon_fila(f"ALARMA#a{i}", a)
    L.datetime_original = L.datetime
    return hora


def corre(hora_utc=10):
    """hora_utc 10 -> 12 en Madrid, fuera del silencio por defecto."""
    import datetime as dt

    class _Ahora(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return dt.datetime(2026, 10, 1, hora_utc, 0, 0, tzinfo=dt.timezone.utc)

    real = L.datetime.datetime
    L.datetime.datetime = _Ahora
    try:
        return L.lambda_handler({}, None)
    finally:
        L.datetime.datetime = real


BASE = {"nombre": "Prueba", "activa": True, "perfil": "interno",
        "canal": ["correo"], "destinos": ["jefe@serunion.es"],
        "silencio": {"desde": 22, "hasta": 7}}

# ----------------------------------------------------------------------
print("\nUna alarma con fuente buena salta y avisa")
escenario([dict(BASE, nombre="Caducidad alta", fuente="stock", campo="caducidad_mes",
                comparacion=">", umbral=1000)])
res = corre()
comprueba("una saltada", len(res["saltadas"]), 1)
comprueba("con su valor", res["saltadas"][0]["valor"], 2374.53)
comprueba("se envio por correo", res["saltadas"][0]["enviados"], ["correo"])
comprueba("y salio un correo", len(falsos.CORREOS), 1)
comprueba("al destinatario", falsos.CORREOS[0]["para"], ["jefe@serunion.es"])
comprueba("con la cifra en el texto", "2374.53" in falsos.CORREOS[0]["texto"], True)
comprueba("y queda en la bandeja", len(falsos.lista("AVISO#")), 1)

print("\nLa misma alarma no vuelve a avisar en 24 h")
res2 = corre()
comprueba("ya no salta", len(res2["saltadas"]), 0)
comprueba("pero si se evalua", res2["ok"], 1)
comprueba("y no manda un segundo correo", len(falsos.CORREOS), 1)

print("\nPor debajo del umbral no pasa nada")
escenario([dict(BASE, fuente="stock", campo="caducidad_mes", comparacion=">", umbral=99999)])
res = corre()
comprueba("evaluada", res["ok"], 1)
comprueba("no saltada", len(res["saltadas"]), 0)

print("\nEl silencio nocturno retiene el aviso, no lo descarta")
escenario([dict(BASE, fuente="stock", campo="caducidad_mes", comparacion=">", umbral=1000)])
res = corre(hora_utc=1)  # 03:00 en Madrid
comprueba("en silencio", len(res["en_silencio"]), 1)
comprueba("sin correo", len(falsos.CORREOS), 0)
res = corre(hora_utc=10)  # 12:00, ya puede
comprueba("y a mediodia sale", len(res["saltadas"]), 1)

print("\nUna fuente que todavia no se calcula SE DICE")
escenario([dict(BASE, nombre="Horas sin venta", fuente="telemetria", campo="horas_sin_venta",
                comparacion=">", umbral=4)])
res = corre()
comprueba("no evaluable", len(res["no_evaluables"]), 1)
comprueba("ni saltada ni correcta", (len(res["saltadas"]), res["ok"]), (0, 0))
comprueba("y el motivo lo explica", "todavia no se calcula" in res["no_evaluables"][0]["motivo"], True)

print("\nUna fuente inventada tampoco pasa por buena")
escenario([dict(BASE, fuente="loquesea", campo="nada", comparacion=">", umbral=1)])
res = corre()
comprueba("no evaluable", len(res["no_evaluables"]), 1)
comprueba("y dice que es desconocida", "desconocida" in res["no_evaluables"][0]["motivo"], True)

print("\nUna alarma desactivada se ignora del todo")
escenario([dict(BASE, activa=False, fuente="stock", campo="caducidad_mes",
                comparacion=">", umbral=1)])
res = corre()
comprueba("nada", (len(res["saltadas"]), res["ok"], len(res["no_evaluables"])), (0, 0, 0))

print("\nEl ultimo mes es el que se mira, no el primero")
escenario([dict(BASE, fuente="recaudacion", campo="efectivo_ciego_mes",
                comparacion=">", umbral=100000)])
res = corre()
comprueba("usa septiembre, no agosto", res["saltadas"][0]["valor"], 122327)

print("\nSin perfil con panel, se dice")
escenario([dict(BASE, perfil="no-existe", fuente="stock", campo="caducidad_mes",
                comparacion=">", umbral=1)])
res = corre()
comprueba("no evaluable", "Sin panel" in res["no_evaluables"][0]["motivo"], True)

# ----------------------------------------------------------------------
print("\nLa cola de WhatsApp sin proveedor configurado NO finge haber enviado")
escenario([])
falsos.pon_fila("TELEFONO#12", {"nombre": "Luis", "telefono": "+34600111222"})
falsos.pon_fila("COLA#1", {"tipo": "whatsapp", "destino": "12", "texto": "Revisa la 18FE1538",
                           "pedido_por": "ope@serunion.es"})
L._wa = None
res = corre()
comprueba("queda pendiente", res["cola"]["pendientes"], 1)
comprueba("no enviado", res["cola"]["enviados"], 0)
avisos = falsos.lista("AVISO#")
comprueba("y el motivo esta en la bandeja", "sin configurar" in avisos[0]["texto"], True)
comprueba("la cola no se borra", len(falsos.lista("COLA#")), 1)

print("\nCon proveedor configurado, se envia")
escenario([])
falsos.SECRETOS["s/wa"] = json.dumps({"token": "T", "numero_id": "999"})
falsos.pon_fila("TELEFONO#12", {"nombre": "Luis", "telefono": "+34600111222"})
falsos.pon_fila("COLA#1", {"tipo": "whatsapp", "destino": "12", "texto": "Revisa la 18FE1538"})
L._wa = None
enviados = []


class _Respuesta:
    """`with` busca __enter__ en la CLASE, no en la instancia: un
    SimpleNamespace con esos atributos no sirve como gestor de contexto."""

    def read(self):
        return b"{}"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _urlopen_falso(peticion, timeout=None):
    enviados.append({"url": peticion.full_url, "cuerpo": json.loads(peticion.data)})
    return _Respuesta()


L.urllib.request.urlopen = _urlopen_falso
res = corre()
comprueba("enviado", res["cola"]["enviados"], 1)
comprueba("al telefono de la agenda", enviados[0]["cuerpo"]["to"], "34600111222")
comprueba("con el texto", "18FE1538" in enviados[0]["cuerpo"]["text"]["body"], True)
comprueba("y la cola se vacia", len(falsos.lista("COLA#")), 0)

print("\nUn WhatsApp a un empleado sin telefono no se queda colgado")
escenario([])
falsos.SECRETOS["s/wa"] = json.dumps({"token": "T", "numero_id": "999"})
falsos.pon_fila("COLA#1", {"tipo": "whatsapp", "destino": "77", "texto": "hola"})
L._wa = None
res = corre()
comprueba("sale de la cola", len(falsos.lista("COLA#")), 0)
comprueba("y deja aviso del motivo", "No hay telefono" in falsos.lista("AVISO#")[0]["texto"], True)

print("\nEl alta de incidencia espera el endpoint, y no se da por hecha")
escenario([])
falsos.pon_fila("COLA#1", {"tipo": "incidencia", "matricula": "18FE1538",
                           "descripcion": "Monedero atascado"})
res = corre()
comprueba("sigue pendiente", res["cola"]["pendientes"], 1)
comprueba("y en la cola, visible", len(falsos.lista("COLA#")), 1)

print("\nLas horas de silencio que cruzan la medianoche")
comprueba("03:00 con 22-7 es silencio", L.en_silencio({"desde": 22, "hasta": 7}, 3), True)
comprueba("23:00 tambien", L.en_silencio({"desde": 22, "hasta": 7}, 23), True)
comprueba("12:00 no", L.en_silencio({"desde": 22, "hasta": 7}, 12), False)
comprueba("tramo normal 9-18, 12 si", L.en_silencio({"desde": 9, "hasta": 18}, 12), True)
comprueba("iguales = sin silencio", L.en_silencio({"desde": 0, "hasta": 0}, 3), False)

print("\nLas comparaciones")
for signo, a, b, esperado in [(">", 2, 1, True), (">=", 1, 1, True), ("<", 1, 2, True),
                              ("<=", 2, 1, False), ("=", 1, 1, True), ("?", 1, 1, False)]:
    comprueba(f"{a} {signo} {b}", L.compara(a, signo, b), esperado)

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("Las alarmas se comportan.")
