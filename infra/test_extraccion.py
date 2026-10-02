"""
La capa de red de la extraccion, con un servidor falso.

Reproduce lo que VenCloud contesto de verdad —404 en los informes con fechas,
307 en los maestros, 405 con la barra final— y comprueba que el codigo monta la
URL que el propio servicio nos dijo que queria:

    GET .../GetReportV2/{token}/{empresa}/{informe}%7C{aaaa-mm-dd}%7C{aaaa-mm-dd}/

Tres cosas, cada una medida: GET y no POST (el 405 con barra final lo dijo),
barra final (el 307 la anadia), y fecha ISO (dd/MM/yyyy daba 404 porque IIS
rechaza la barra codificada dentro de la ruta).

    python3 infra/test_extraccion.py
"""

import os
import sys
import types
import urllib.error

AQUI = __file__.rsplit("/", 1)[0]
sys.path.insert(0, AQUI)

sys.modules["boto3"] = types.SimpleNamespace(client=lambda *a, **k: None)
os.environ.update(
    VENCLOUD_ENDPOINT="https://vencloudpro.eac.es/2311_api/webservices//Api/Api.svc",  # con la doble barra, como venia
    VENCLOUD_TOKEN="EL-TOKEN-SECRETO",
    VENCLOUD_EMPRESA="2311",
    BUCKET="b",
)

import lambda_extraccion as L  # noqa: E402

fallos = []


def comprueba(que, obtenido, esperado):
    if obtenido == esperado:
        print(f"  ok    {que}")
    else:
        print(f"  FALLO {que}: {obtenido!r} != {esperado!r}")
        fallos.append(que)


# ---------------------------------------------------------------- servidor falso
PETICIONES = []


class _Respuesta:
    def __init__(self, status, headers, body):
        self.status, self.headers, self._body = status, headers, body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Abridor:
    """GUION es una lista de (comprobacion, status, headers, body)."""

    GUION = []

    def open(self, peticion, timeout=None):
        PETICIONES.append({"url": peticion.full_url, "metodo": peticion.get_method(),
                           "cuerpo": peticion.data})
        for condicion, status, headers, body in self.GUION:
            if condicion(peticion):
                if status >= 400:
                    raise urllib.error.HTTPError(peticion.full_url, status, "x",
                                                 _Cabeceras(headers), _Cuerpo(body))
                return _Respuesta(status, _Cabeceras(headers), body)
        raise AssertionError("ningun caso del guion encaja con " + peticion.full_url)


class _Cabeceras(dict):
    pass


class _Cuerpo:
    def __init__(self, b):
        self.b = b

    def read(self):
        return self.b

    def close(self):
        """HTTPError lo cierra al destruirse; sin esto el intérprete se queja."""


L.ABRIDOR = _Abridor()


def guion(*casos):
    PETICIONES.clear()
    _Abridor.GUION = list(casos)


# ----------------------------------------------------------------------
import datetime  # noqa: E402

print("\nUna fecha con barras no arranca siquiera")
# La plantilla pasaba FORMATO_FECHA=%d/%m/%Y como variable de entorno y pisaba
# el valor del codigo: 66 descargas con 404 en la primera carga real. Ahora el
# modulo se niega a cargar, que es un fallo de medio segundo y no de una noche.
import importlib  # noqa: E402
os.environ["FORMATO_FECHA"] = "%d/%m/%Y"
try:
    importlib.reload(L)
    comprueba("deberia negarse a arrancar", True, False)
except RuntimeError as e:
    comprueba("se niega", "barra" in str(e), True)
    comprueba("y dice cual poner", "%Y-%m-%d" in str(e), True)
del os.environ["FORMATO_FECHA"]
importlib.reload(L)
L.ABRIDOR = _Abridor()

print("\nLa URL es exactamente la que el servicio pidio")
comprueba("fecha en ISO", L.FORMATO_FECHA, "%Y-%m-%d")
comprueba("metodo GET", L.METODO, "GET")
comprueba("el endpoint pierde la doble barra",
          L.ENDPOINT, "https://vencloudpro.eac.es/2311_api/webservices/Api/Api.svc")
comprueba("las fechas salen sin barras",
          L.filtros_de("propia", datetime.date(2026, 9, 30)), ["2026-09-30", "2026-09-30"])

rutas = L.rutas_posibles(105, ["2026-09-30", "2026-09-30"])
comprueba("dos formas", len(rutas), 2)
comprueba("la primera con %7C", rutas[0], "105%7C2026-09-30%7C2026-09-30")
comprueba("la segunda con | literal", rutas[1], "105|2026-09-30|2026-09-30")
comprueba("un maestro va solo", L.rutas_posibles(157, []), ["157"])
comprueba("y sin %2F en ninguna, que es lo que daba 404",
          any("%2F" in r for r in rutas), False)

print("\nUn 307 se sigue SIN cambiar de metodo")
guion(
    (lambda p: "/Api.svc/" in p.full_url, 307, {"Location": "https://otro.eac.es/bien"}, b""),
    (lambda p: p.full_url == "https://otro.eac.es/bien", 200, {}, b'[{"a":1}]'),
)
codigo, _, cuerpo = L.llamar(f"{L.ENDPOINT}/Api.svc/x")
comprueba("acaba en 200", codigo, 200)
comprueba("con el cuerpo bueno", cuerpo, b'[{"a":1}]')
comprueba("dos peticiones", len(PETICIONES), 2)
comprueba("la segunda sigue siendo POST", PETICIONES[1]["metodo"], "POST")
comprueba("y conserva el cuerpo", PETICIONES[1]["cuerpo"], b"")

print("\nUn 302, en cambio, pasa a GET (lo dice la norma)")
guion(
    (lambda p: p.get_method() == "POST", 302, {"Location": "/otro"}, b""),
    (lambda p: p.get_method() == "GET", 200, {}, b"ok"),
)
L.llamar(f"{L.ENDPOINT}/x")
comprueba("la segunda es GET", PETICIONES[1]["metodo"], "GET")

print("\nUna cadena de redirecciones infinita para, y devuelve el ultimo 307")
# No lanza: devolver el 307 con su Location es informacion util; "demasiados
# saltos" no lo es, y es lo que necesitabamos leer la primera noche.
guion((lambda p: True, 307, {"Location": "/da/vueltas"}, b""))
codigo, cabeceras, _ = L.llamar(f"{L.ENDPOINT}/x")
comprueba("devuelve el 307", codigo, 307)
comprueba("con su destino", cabeceras["Location"], "/da/vueltas")
comprueba("y para a los cuatro intentos", len(PETICIONES), L.MAX_SALTOS + 1)

print("\nLa llamada de verdad: GET, barra final y nada de POST")
guion((lambda p: True, 200, {}, b'[{"ok":true}]'))
comprueba("devuelve el cuerpo", L.descargar(157, []), b'[{"ok":true}]')
comprueba("va por GET", PETICIONES[0]["metodo"], "GET")
comprueba("acaba en barra", PETICIONES[0]["url"].endswith("/157/"), True)
comprueba("sin doble barra", "//" in PETICIONES[0]["url"].split("://", 1)[1], False)

guion((lambda p: True, 200, {}, b"[]"))
L.descargar(105, ["2026-09-30", "2026-09-30"])
comprueba("el incremental tambien acaba en barra",
          PETICIONES[0]["url"].endswith("105%7C2026-09-30%7C2026-09-30/"), True)

print("\nUn 404 prueba la forma siguiente de ruta, no se rinde")
guion(
    (lambda p: "%7C" not in p.full_url, 200, {}, b'[{"ok":true}]'),
    (lambda p: True, 404, {}, b"no"),
)
comprueba("encuentra la segunda", L.descargar(105, ["2026-09-30", "2026-09-30"]), b'[{"ok":true}]')
comprueba("tras probar las dos", len(PETICIONES), 2)

print("\nUn 405 dice que metodos acepta, y eso va en el mensaje")
guion((lambda p: True, 405, {"Allow": "GET, HEAD"}, b""))
try:
    L.descargar(157, [])
    comprueba("deberia fallar", True, False)
except RuntimeError as e:
    comprueba("trae el 405", "HTTP 405" in str(e), True)
    comprueba("y lo que acepta", "acepta GET, HEAD" in str(e), True)

print("\nSi fallan todas, el error dice el codigo Y a donde redirigia")
guion((lambda p: True, 307, {"Location": "https://vencloudpro.eac.es/login"}, b""))
try:
    L.descargar(157, [])
    comprueba("deberia fallar", True, False)
except RuntimeError as e:
    comprueba("trae el 307", "HTTP 307" in str(e), True)
    comprueba("y el destino", "/login" in str(e), True)

print("\nUn 5xx si reintenta; un 404 no espera")
L.REINTENTOS = 2
guion((lambda p: True, 503, {}, b""))
import time as _t
t0 = _t.time()
try:
    L.descargar(157, [])
except RuntimeError:
    pass
comprueba("ha esperado entre tandas", _t.time() - t0 >= 1, True)
comprueba("dos tandas, una llamada cada una", len(PETICIONES), 2)

guion((lambda p: True, 404, {}, b""))
t0 = _t.time()
try:
    L.descargar(157, [])
except RuntimeError:
    pass
comprueba("con 404 no espera", _t.time() - t0 < 0.5, True)

print("\nEl token no aparece en ningun mensaje")
guion((lambda p: True, 307, {"Location": "https://x/?t=EL-TOKEN-SECRETO"}, b""))
try:
    L.descargar(157, [])
except RuntimeError as e:
    comprueba("redactado", "EL-TOKEN-SECRETO" in str(e), False)
    comprueba("y se ve que estaba", "TOKEN" in str(e), True)

print("\nEl endpoint se normaliza sin romper el esquema")
comprueba("colapsa", L._endpoint("https://a.es/x//y/z.svc"), "https://a.es/x/y/z.svc")
comprueba("no toca https://", L._endpoint("https://a.es/x"), "https://a.es/x")
comprueba("y quita la barra final", L._endpoint("https://a.es/x/"), "https://a.es/x")

print("\nContar filas sin parsear: un informe grande no cabe en memoria")
import json as _json  # noqa: E402
for obj, que in [
    ([{"a": 1}, {"a": 2}, {"a": 3}], "tres filas"),
    ([], "vacio"),
    ([{"t": "llaves { } dentro de texto"}, {"t": "otra }"}], "llaves en una cadena"),
    ([{"t": 'comilla " escapada y una llave {'}, {"t": "x"}], "comilla escapada"),
    ([{"t": "barra final \\"}, {"t": "y"}], "barra invertida al final"),
    ([{"a": {"b": [1, 2, {"c": 3}]}}], "anidamiento hondo"),
]:
    comprueba(que, L._contar_objetos(_json.dumps(obj).encode()), len(obj))

grande = _json.dumps([{"parte_id": i, "centro": "AIRBUS GETAFE"} for i in range(20000)]).encode()
L.LIMITE_PARSEO = 1000
comprueba("por encima del limite no parsea, cuenta", L.filas_de(grande), 20000)
L.LIMITE_PARSEO = 48 * 1024 * 1024
comprueba("y por debajo si parsea", L.filas_de(b'[{"a":1},{"a":2}]'), 2)
comprueba("una respuesta que no es JSON devuelve None, no un numero inventado",
          L.filas_de(b"<html>error</html>"), None)

# m_carriles devolvio None en la primera carga: 6,3 MB que no empezaban por [.
comprueba("un array envuelto tambien se cuenta",
          L._contar_objetos(b'{"Rows":[{"a":1},{"a":2},{"a":3}]}'), 3)
comprueba("y con BOM delante", L._contar_objetos('\ufeff[{"a":1},{"a":2}]'.encode()), 2)
comprueba("filas_de lo intenta antes de rendirse",
          L.filas_de('\ufeff[{"a":1},{"a":2}]'.encode()), 2)
comprueba("sin ningun array, None", L._contar_objetos(b'{"a":1}'), None)

print("\nRecortar antes de limpiar: esto reventaba la sonda por memoria")
# _limpio normalizaba el cuerpo ENTERO para quedarse con 400 caracteres:
# texto.split() sobre 6,4 MB construye una lista de un millon de cadenas.
enorme = b'[{"x":"' + b"a" * 6_000_000 + b'"}]'
comprueba("devuelve 400 caracteres", len(L._limpio(enorme, 400)), 400)

print("\nDe una pagina de error de WCF se lee el mensaje, no el CSS")
pagina = (b"<html><head><style>BODY{color:#000;font-family:Verdana}</style></head>"
          b"<body><div id='content'><p class='heading1'>Servicio</p>"
          b"<p>Extremo no encontrado.</p></div></body></html>")
comprueba("el mensaje", L._limpio(pagina), "Servicio Extremo no encontrado.")
comprueba("un JSON pasa intacto", L._limpio(b'[{"id":1}]'), '[{"id":1}]')

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("La capa de red se comporta.")
