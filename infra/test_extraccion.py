"""
La capa de red de la extraccion, con un servidor falso.

Reproduce lo que VenCloud contesto de verdad la primera noche —404 en los
informes con fechas y 307 en los maestros— y comprueba que el codigo nuevo lo
maneja: codifica las barras de la fecha, sigue el 307 sin cambiar de metodo, y
cuando falla deja dicho A DONDE redirigia, que es la mitad del diagnostico.

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
    VENCLOUD_ENDPOINT="https://vencloudpro.eac.es/2311_api/webservices//Api/Api.svc",
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
print("\nLas barras de la fecha se codifican: eso era el 404")
rutas = list(L.rutas_posibles(105, ["30/09/2026", "30/09/2026"]))
comprueba("cuatro formas", len(rutas), 4)
comprueba("la primera lleva %2F", rutas[0], "105|30%2F09%2F2026|30%2F09%2F2026")
comprueba("y conserva la barra vertical", "|" in rutas[0], True)
comprueba("la segunda codifica tambien el |", rutas[1], "105%7C30%2F09%2F2026%7C30%2F09%2F2026")
comprueba("la tercera es en claro, como estaba", rutas[2], "105|30/09/2026|30/09/2026")
comprueba("la cuarta parte por segmentos", rutas[3], "105/30%2F09%2F2026/30%2F09%2F2026")
comprueba("un maestro no lleva separadores", list(L.rutas_posibles(157, []))[0], "157")

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

print("\nUn 404 prueba la forma siguiente de ruta, no se rinde")
guion(
    (lambda p: "%2F" in p.full_url, 200, {}, b'[{"ok":true}]'),
    (lambda p: True, 404, {}, b"no"),
)
comprueba("encuentra la buena", L.descargar(105, ["30/09/2026", "30/09/2026"]), b'[{"ok":true}]')
comprueba("a la primera, porque %2F va primero", len(PETICIONES), 1)

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

print("\nLa sonda quita la doble barra del endpoint, pero no la del esquema")
comprueba("colapsa", L._sin_doble_barra("https://a.es/x//y/z.svc"), "https://a.es/x/y/z.svc")
comprueba("no toca https://", L._sin_doble_barra("https://a.es/x").startswith("https://"), True)

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("La capa de red se comporta.")
