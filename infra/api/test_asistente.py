"""
El asistente, con la API de Claude falseada y la API de la plataforma de verdad.

Lo que se comprueba no es la calidad de la respuesta: es que el dato le llega al
modelo por la MISMA API que al navegador, con la sesion del usuario. Las
consultas del asistente se sirven aqui con infra/api/lambda_api.py contra el AWS
falso, asi que si el coste de servicio llegara al modelo seria porque la API se
lo da al navegador, y eso ya lo para test_api.py.

    python3 infra/api/test_asistente.py
"""

import gzip
import json
import os
import sys
import types
import urllib.parse

AQUI = __file__.rsplit("/", 1)[0]
sys.path.insert(0, AQUI)
sys.path.insert(1, AQUI.rsplit("/", 1)[0])

import falsos  # noqa: E402

falsos.instala()
falsos.SECRETOS["s/clave"] = "sk-de-pega"
os.environ.update(TABLA="t", BUCKET_DATOS="b", SECRETO_CLAVE="s/clave", POOL="p", CLIENTE_POOL="c",
                  MODELO="claude-opus-5-5")

# ---------------------------------------------------------------- Claude falso
LLAMADAS = []
COLA = []          # lo que contestara el modelo, vuelta a vuelta
TEXTO = "En septiembre hubo 1.107 visitas reales."


class _BadRequest(Exception):
    pass


class _Uso:
    input_tokens = 1500
    output_tokens = 120
    cache_read_input_tokens = 2400
    cache_creation_input_tokens = 0


class _Bloque(types.SimpleNamespace):
    def model_dump(self, exclude_none=True):
        return dict(vars(self))


def texto(t=TEXTO, stop="end_turn"):
    return {"content": [_Bloque(type="thinking", thinking="", signature="f"),
                        _Bloque(type="text", text=t)], "stop": stop}


def recuerda(t):
    return {"content": [_Bloque(type="tool_use", id=f"m{len(LLAMADAS)}", name="memoria", input={"texto": t})],
            "stop": "tool_use"}


def consulta(**entrada):
    return {"content": [_Bloque(type="tool_use", id=f"t{len(LLAMADAS)}", name="consulta", input=entrada)],
            "stop": "tool_use"}


class _Respuesta:
    def __init__(self):
        sig = COLA.pop(0) if COLA else texto()
        self.content = sig["content"]
        self.stop_reason = sig["stop"]
        self.usage = _Uso()


class _Mensajes:
    def create(self, **kw):
        LLAMADAS.append(json.loads(json.dumps(kw, default=str)))
        return _Respuesta()


class _ClienteFalso:
    def __init__(self, **kw):
        self.messages = _Mensajes()
        self.beta = types.SimpleNamespace(messages=_Mensajes())


sys.modules["anthropic"] = types.SimpleNamespace(
    Anthropic=lambda **kw: _ClienteFalso(**kw), BadRequestError=_BadRequest)

import lambda_api as API  # noqa: E402
import lambda_asistente as L  # noqa: E402

# Las consultas del asistente, servidas por la API de verdad con su cookie.
PEDIDAS = []


def _baja(url, token):
    u = urllib.parse.urlparse(url)
    PEDIDAS.append(url)
    q = dict(urllib.parse.parse_qsl(u.query))
    res = API.lambda_handler(falsos.peticion("GET", u.path, None, token, query=q), None)
    b = res["body"]
    if res.get("isBase64Encoded"):
        import base64
        b = base64.b64decode(b)
        if b[:2] == b"\x1f\x8b":
            b = gzip.decompress(b)
    return res["statusCode"], json.loads(b)


L._baja = _baja

fallos = []


def comprueba(que, obtenido, esperado):
    if obtenido == esperado:
        print(f"  ok    {que}")
    else:
        print(f"  FALLO {que}: {obtenido!r} != {esperado!r}")
        fallos.append(que)


# ---------------------------------------------------------------- escenario
PANEL = {
    "generado": "2026-10-01T04:45:00Z",
    "periodo": {"desde": "2026-06-03", "hasta": "2026-09-30"},
    "servicio": {"visitas": 1107, "coste_servicio": {"coste": 8856.0}},
    "dinero": {"periodos": [{"periodo": "2026-09", "total": 42000}]},
    "sat": {"tareas": 150},
    "inventario": {"cumplimiento": {"pct_en_norma": 8.6}, "existencias": {"A": 500000}},
}
OPERATIVO = {
    "generado": "2026-10-22T04:45:00Z", "ultimo_dia": "2026-10-21", "primer_dia": "2026-10-20",
    "umbrales": {"verde": 95, "amarillo": 75},
    "dias": {"2026-10-21": {"rutas": {"previstas": 100, "hechas": 81, "pct": 81.0, "color": "amarillo"},
                            "ventas": {"importe": 777777.0}}},
    "foto": {"rutas": {"x": 1}, "ventas": {"y": 2}},
}
PERFIL = {
    "nombre": "AIRBUS", "tipo": "operaciones",
    "ambito": {"clientes": ["AIRBUS"], "centros": ["AIRBUS GETAFE"], "delegaciones": []},
    "sesiones": ["resumen", "disponibilidad"],
    "permisos": {"asistente": True},
    "cuadrados": ["rutas"],
}
falsos.pon_panel("cli-airbus", PANEL)
falsos.OBJETOS["cabina/cli-airbus/operativo.json.gz"] = gzip.compress(json.dumps(OPERATIVO).encode())
falsos.pon_fila("PERFIL#cli-airbus", PERFIL)
ANA = {"nombre": "Ana", "perfil_id": "cli-airbus", "estado": "activo", "asistente": True}
falsos.pon_fila("USUARIO#ana@airbus.com", ANA)
falsos.pon_fila("USUARIO#luis@airbus.com", dict(ANA, nombre="Luis"))


def sesion_de(correo):
    import comun
    return comun.abre_sesion(correo)


def pregunta(texto_, cookie, historial=None, pagina=None, sigue=None):
    d = {"pregunta": texto_, "historial": historial or []}
    if pagina:
        d["pagina"] = pagina
    if sigue:
        d = {"sigue": sigue}
    ev = falsos.peticion("POST", "/api/pregunta", d, cookie)
    return L.lambda_handler(ev, None)


def cuerpo(res):
    return json.loads(res["body"])


def resultado(llamada):
    """Lo que la ultima consulta le devolvio al modelo, en esa llamada."""
    for m in reversed(llamada["messages"]):
        if m["role"] == "user" and isinstance(m["content"], list):
            for b in m["content"]:
                if b.get("type") == "tool_result":
                    return b["content"]
    return ""


COOKIE = sesion_de("ana@airbus.com")
OTRA = sesion_de("luis@airbus.com")
L.SEGUNDOS_VUELTA = 999   # en las pruebas, todo en una peticion salvo donde se diga

# ----------------------------------------------------------------------
print("\nUna pregunta que no necesita consultar")
res = pregunta("Hola, que puedes hacer?", COOKIE)
comprueba("200", res["statusCode"], 200)
comprueba("devuelve la respuesta", cuerpo(res)["respuesta"], TEXTO)
comprueba("y lo que ha costado", cuerpo(res)["coste_usd"] > 0, True)
comprueba("una sola llamada al modelo", len(LLAMADAS), 1)

k = LLAMADAS[0]
print("\nLa llamada esta bien formada")
comprueba("el modelo", k["model"], "claude-opus-5-5")
comprueba("pensamiento adaptativo", k["thinking"], {"type": "adaptive"})
comprueba("esfuerzo explicito", k["output_config"]["effort"], "medium")
comprueba("sin budget_tokens (daria 400)", "budget_tokens" in json.dumps(k["thinking"]), False)
comprueba("tope de salida", k["max_tokens"], 4000)
comprueba("con reintento en otro modelo si declina", k.get("fallbacks"), "default")
comprueba("con las herramientas de consulta, memoria y muneco", [t["name"] for t in k["tools"]], ["consulta", "memoria", "muneco"])
comprueba("que puede usar o no", k["tool_choice"], {"type": "auto"})

print("\nEl recetario va en el sistema, y en cache")
comprueba("un solo bloque de sistema", len(k["system"]), 1)
comprueba("marcado para cachear", k["system"][0]["cache_control"], {"type": "ephemeral"})
comprueba("lleva las trampas", "00SE0000" in k["system"][0]["text"], True)
comprueba("y la de los partes del sistema", "SYSTEM" in k["system"][0]["text"], True)
comprueba("el recetario NO lleva nada variable",
          any(x in k["system"][0]["text"] for x in ["ana@airbus.com", "2026-10-01", "AIRBUS GETAFE"]), False)
comprueba("las herramientas tampoco",
          any(x in json.dumps(k["tools"]) for x in ["ana@airbus.com", "AIRBUS GETAFE"]), False)

print("\nEl mensaje lleva el contexto, no los datos")
enviado = json.dumps(k["messages"][-1]["content"], ensure_ascii=False)
comprueba("su ambito si", "AIRBUS GETAFE" in enviado, True)
comprueba("la fecha de hoy, para saber que es ayer", '\\"hoy\\":\\"' in enviado, True)
comprueba("la pagina desde la que pregunta", '\\"pagina\\":\\"panel\\"' in enviado, True)
comprueba("y la pregunta", "que puedes hacer" in enviado, True)
comprueba("ningun dato por adelantado", "1107" in enviado, False)
comprueba("con el corte de cache en el ultimo mensaje",
          k["messages"][-1]["content"][-1].get("cache_control"), {"type": "ephemeral"})

# ----------------------------------------------------------------------
print("\nConsulta el panel por la API, con la sesion del usuario")
LLAMADAS.clear(); PEDIDAS.clear()
COLA[:] = [consulta(seccion="panel"), texto()]
res = pregunta("Cuantas visitas hubo?", COOKIE)
comprueba("200 con respuesta", (res["statusCode"], "respuesta" in cuerpo(res)), (200, True))
comprueba("dos vueltas del modelo", len(LLAMADAS), 2)
comprueba("pidio /api/panel", [urllib.parse.urlparse(u).path for u in PEDIDAS], ["/api/panel"])
visto = resultado(LLAMADAS[1])
comprueba("las visitas si", "1107" in visto, True)
comprueba("el COSTE DE SERVICIO no: la API no se lo da a operaciones", "8856" in visto, False)
comprueba("ni el valor de las existencias", "500000" in visto, False)
comprueba("el pensamiento vuelve entero en la vuelta siguiente",
          LLAMADAS[1]["messages"][-2]["content"][0]["type"], "tool_use")

print("\nEl informe general, con los cuadrados que ve")
LLAMADAS.clear(); PEDIDAS.clear()
COLA[:] = [consulta(seccion="informe_general", camino=["dias", "2026-10-21"]), texto()]
pregunta("como fueron las rutas ayer?", COOKIE, pagina="operativo")
visto = resultado(LLAMADAS[1])
comprueba("lleva las rutas del dia", '"hechas":81' in visto, True)
comprueba("sin el cuadrado que su perfil no ve", "777777" in visto, False)

print("\nLo que se le quito a el (docs/61) tampoco llega")
falsos.pon_fila("USUARIO#ana@airbus.com", dict(ANA, cuadrados_ocultos=["rutas"]))
LLAMADAS.clear()
COLA[:] = [consulta(seccion="informe_general", camino=["dias", "2026-10-21"]), texto()]
pregunta("y las rutas?", COOKIE, pagina="operativo")
comprueba("sin rutas", '"hechas":81' in resultado(LLAMADAS[1]), False)
falsos.pon_fila("USUARIO#ana@airbus.com", ANA)

print("\nUna seccion que no tiene: el error de la API, no el dato")
LLAMADAS.clear()
COLA[:] = [consulta(seccion="almacenes"), texto()]
pregunta("y los almacenes?", COOKIE)
visto = json.loads(resultado(LLAMADAS[1]))
comprueba("dice que no tiene permiso", (visto.get("codigo"), "almacenes" in visto.get("error", "")), (403, True))
LLAMADAS.clear()
COLA[:] = [consulta(seccion="vencloud"), texto()]
pregunta("y vencloud?", COOKIE)
comprueba("una seccion que no existe, error", "error" in json.loads(resultado(LLAMADAS[1])), True)
LLAMADAS.clear(); PEDIDAS.clear()
COLA[:] = [consulta(seccion="panel", parametros={"perfil": "interno"}), texto()]
pregunta("y el panel del interno?", COOKIE)
comprueba("los parametros que la seccion no admite no se mandan", PEDIDAS[0].endswith("/api/panel"), True)

print("\nBajar por una seccion grande")
grande = {"centros": [{"centro": f"C{i:03}", "delegacion": "Sevilla" if i % 2 else "Madrid",
                       "venta": i * 10.0, "notas": "x" * 400} for i in range(300)],
          "otra": {"a": 1}}
cache = {L.URL_API + "/api/rutas": (200, grande)}
top = L.consulta({"seccion": "rutas"}, "t", cache)
comprueba("sin camino: las claves, con lo grande resumido", (top["centros"], top["otra"]), ("<lista de 300>", {"a": 1}))
lst = L.consulta({"seccion": "rutas", "camino": ["centros"], "filtro": {"delegacion": "sevi"},
                  "orden": "-venta", "max": 3}, "t", cache)
comprueba("filtro, orden y max", [x["centro"] for x in lst["elementos"]], ["C299", "C297", "C295"])
comprueba("con el total filtrado", lst["total"], 150)
comprueba("y lo largo de cada elemento, resumido", lst["elementos"][0]["notas"].endswith("…"), True)
comprueba("una posicion de la lista", L.consulta({"seccion": "rutas", "camino": ["centros", 5, "centro"]}, "t", cache), "C005")
comprueba("un camino que no existe lo dice, con lo que hay",
          L.consulta({"seccion": "rutas", "camino": ["nada"]}, "t", cache)["hay"], ["centros", "otra"])

print("\nSerie y tarifas sin parametros dicen como pedir el detalle")
cache = {L.URL_API + "/api/tarifas": (200, {"total": {"pct": 61.6}, "delegaciones": []}),
         L.URL_API + "/api/tarifas?centro=290010": (200, {"num_centro": "290010", "filas": []}),
         L.URL_API + "/api/serie": (200, {"meses": ["2026-10"]})}
comprueba("tarifas sin centro: el indice y la pista",
          "centro" in L.consulta({"seccion": "tarifas"}, "t", cache).get("_parametros", ""), True)
comprueba("con centro, sin pista",
          "_parametros" in L.consulta({"seccion": "tarifas", "parametros": {"centro": "290010"}}, "t", cache), False)
fallo = L.consulta({"seccion": "serie", "camino": ["filas"]}, "t", cache)
comprueba("serie: si busca filas sin mes, el error dice que pida el mes",
          ("hay" in fallo, "mes" in fallo.get("parametros", "")), (True, True))
comprueba("rutas, que no admite parametros, no lleva pista",
          "_parametros" in L.consulta({"seccion": "rutas"}, "t", {L.URL_API + "/api/rutas": (200, {"a": 1})}), False)

# ----------------------------------------------------------------------
print("\nPor pasos: cada peticion, una vuelta; el navegador sigue con el id")
L.SEGUNDOS_VUELTA = -1
LLAMADAS.clear()
COLA[:] = [consulta(seccion="panel"), consulta(seccion="informe_general"), texto()]
dia, antes = L.uso_de_hoy("ana@airbus.com")
r1 = cuerpo(pregunta("cruza el panel y el informe", COOKIE))
comprueba("la primera devuelve sigue", "sigue" in r1 and "respuesta" not in r1, True)
comprueba("y dice que esta mirando", r1.get("estado"), "Mirando el panel…")
comprueba("otro usuario no puede seguirla", pregunta("", OTRA, sigue=r1["sigue"])["statusCode"], 404)
r2 = cuerpo(pregunta("", COOKIE, sigue=r1["sigue"]))
comprueba("la segunda sigue", r2.get("estado"), "Mirando el informe general…")
r3 = cuerpo(pregunta("", COOKIE, sigue=r2["sigue"]))
comprueba("la tercera contesta", r3.get("respuesta"), TEXTO)
_, despues = L.uso_de_hoy("ana@airbus.com")
comprueba("la pregunta se cuenta una vez", despues["preguntas"] - antes.get("preguntas", 0), 1)
comprueba("y el gasto, de las tres vueltas", round(despues["gasto_usd"] - antes.get("gasto_usd", 0), 5),
          round(3 * L.coste(_Uso()), 5))
comprueba("un id inventado, 404", pregunta("", COOKIE, sigue="nada")["statusCode"], 404)
L.SEGUNDOS_VUELTA = 999

print("\nEn la ultima vuelta ya no puede consultar: contesta")
LLAMADAS.clear()
COLA[:] = [consulta(seccion="panel")] * (L.VUELTAS_MAX - 1) + [texto()]
r_ = cuerpo(pregunta("da vueltas", COOKIE))
comprueba("contesta", r_.get("respuesta"), TEXTO)
comprueba("con VUELTAS_MAX llamadas", len(LLAMADAS), L.VUELTAS_MAX)
comprueba("la ultima sin herramientas", LLAMADAS[-1]["tool_choice"], {"type": "none"})
ultimo = LLAMADAS[-1]["messages"][-1]["content"]
comprueba("y se le dice que ya no quedan consultas",
          any(c.get("type") == "text" and "no quedan consultas" in c.get("text", "") for c in ultimo), True)
comprueba("en las anteriores, no",
          any(c.get("type") == "text" for c in LLAMADAS[-2]["messages"][-1]["content"]), False)

print("\nUn objeto con muchas claves ensena las primeras y las ultimas")
dias = {f"2026-10-{d:02d}": {"x": "y" * 400} for d in range(1, 22)}
comprueba("las ultimas fechas se ven", "2026-10-01" in L._corto(dias) and "2026-10-21" in L._corto(dias), True)

print("\nCada usuario tiene su memoria (docs/75)")
def memoria(cookie, accion):
    return cuerpo(L.lambda_handler(falsos.peticion("POST", "/api/pregunta", {"memoria": accion}, cookie), None))
comprueba("al principio, vacia", memoria(COOKIE, "ver"), {"memoria": ""})
LLAMADAS.clear()
COLA[:] = [recuerda("- Le interesa el centro 500088\n- Lo quiere en tablas"), texto()]
r_ = cuerpo(pregunta("recuerda que me interesa el 500088 y lo quiero en tablas", COOKIE))
comprueba("el modelo la escribe y la respuesta lo dice", r_.get("memoria_cambiada"), True)
comprueba("ver la memoria la devuelve", memoria(COOKIE, "ver")["memoria"], "- Le interesa el centro 500088\n- Lo quiere en tablas")
comprueba("el modelo recibe que se guardo", "Memoria guardada" in resultado(LLAMADAS[1]), True)
LLAMADAS.clear()
pregunta("y hoy?", COOKIE)
enviado = json.dumps(LLAMADAS[0]["messages"][-1]["content"], ensure_ascii=False)
comprueba("la pregunta siguiente lleva su memoria", "500088" in enviado and "no reglas" in enviado, True)
comprueba("pero en el mensaje, no en el recetario", "500088" in LLAMADAS[0]["system"][0]["text"], False)
comprueba("sin cambiarla, la respuesta no dice que cambio",
          cuerpo(pregunta("otra", COOKIE)).get("memoria_cambiada"), False)
LLAMADAS.clear()
pregunta("y yo?", OTRA)
comprueba("otro usuario no ve la de Ana", "500088" in json.dumps(LLAMADAS[0]["messages"], ensure_ascii=False), False)
comprueba("ni al pedirla", memoria(OTRA, "ver"), {"memoria": ""})
antes = L.uso_de_hoy("ana@airbus.com")[1].get("preguntas", 0)
COLA[:] = [recuerda("x" * 9000), texto()]
pregunta("apunta mucho", COOKIE)
comprueba("con tope de tamano", len(memoria(COOKIE, "ver")["memoria"]), L.MAX_MEMORIA)
comprueba("borrarla la deja vacia", memoria(COOKIE, "borrar"), {"memoria": ""})
comprueba("y ver o borrar no cuenta como pregunta",
          L.uso_de_hoy("ana@airbus.com")[1].get("preguntas", 0) - antes, 1)
comprueba("sin sesion, nada", L.lambda_handler(falsos.peticion("POST", "/api/pregunta", {"memoria": "ver"}, None), None)["statusCode"], 401)

print("\nCada usuario elige su muneco (docs/76)")
def muneco(cookie, accion):
    return L.lambda_handler(falsos.peticion("POST", "/api/pregunta", {"muneco": accion}, cookie), None)
def elige(nombre):
    return {"content": [_Bloque(type="tool_use", id=f"u{len(LLAMADAS)}", name="muneco", input={"nombre": nombre})],
            "stop": "tool_use"}
_hoy = L.hoy_en_espana
DIA = ["2026-10-23"]
L.hoy_en_espana = lambda: DIA[0]
antes = L.uso_de_hoy("ana@airbus.com")[1].get("preguntas", 0)
comprueba("sin elegir, Vendi, y se le avisa", cuerpo(muneco(COOKIE, "ver")), {"muneco": "vendi", "avisar": True})
comprueba("el mismo dia, no se le avisa otra vez", cuerpo(muneco(COOKIE, "ver"))["avisar"], False)
DIA[0] = "2026-10-24"
comprueba("otro dia, si", cuerpo(muneco(COOKIE, "ver"))["avisar"], True)
DIA[0] = "2026-10-25"
comprueba("y otro, la tercera", cuerpo(muneco(COOKIE, "ver"))["avisar"], True)
DIA[0] = "2026-10-26"
comprueba("despues de tres, nunca mas", cuerpo(muneco(COOKIE, "ver"))["avisar"], False)
comprueba("elegir uno que no existe, 400", muneco(COOKIE, "pikachu")["statusCode"], 400)
comprueba("elegir en el chat", cuerpo(muneco(COOKIE, "bufy")), {"muneco": "bufy"})
comprueba("se queda", cuerpo(muneco(COOKIE, "ver"))["muneco"], "bufy")
comprueba("cada usuario el suyo", cuerpo(muneco(OTRA, "ver")), {"muneco": "vendi", "avisar": True})
comprueba("ni ver ni elegir cuenta como pregunta", L.uso_de_hoy("ana@airbus.com")[1].get("preguntas", 0) - antes, 0)
LLAMADAS.clear()
pregunta("hola", COOKIE)
comprueba("el modelo sabe como se llama", '"muneco":"Bufy"' in json.dumps(LLAMADAS[0]["messages"][-1]["content"], ensure_ascii=False).replace("\\", ""), True)
comprueba("pero no en el recetario", "Bufy" in LLAMADAS[0]["system"][0]["text"] and "`muneco`" in LLAMADAS[0]["system"][0]["text"], True)
LLAMADAS.clear()
COLA[:] = [elige("tom"), texto()]
r_ = cuerpo(pregunta("ponme a Tom", OTRA))
comprueba("pedirlo por escrito lo cambia", r_.get("muneco"), "tom")
comprueba("y se guarda", cuerpo(muneco(OTRA, "ver")), {"muneco": "tom", "avisar": False})
comprueba("el modelo recibe que cambio", "Tom" in resultado(LLAMADAS[1]), True)
COLA[:] = [elige("nadie"), texto()]
r_ = cuerpo(pregunta("ponme a nadie", OTRA))
comprueba("uno que no existe no cambia nada", (r_.get("muneco"), cuerpo(muneco(OTRA, "ver"))["muneco"]), (None, "tom"))
comprueba("sin cambiarlo, la respuesta no trae muneco", cuerpo(pregunta("otra", COOKIE)).get("muneco"), None)
comprueba("sin sesion, nada", muneco(None, "ver")["statusCode"], 401)
L.hoy_en_espana = _hoy

print("\nEl historial se pasa, recortado a tres idas y venidas")
LLAMADAS.clear()
hist = []
for i in range(5):
    hist += [{"de": "usuario", "texto": f"p{i}"}, {"de": "asistente", "texto": f"r{i}"}]
pregunta("y ahora?", COOKIE, hist)
comprueba("seis turnos mas la pregunta", len(LLAMADAS[0]["messages"]), 7)
comprueba("son los ultimos", LLAMADAS[0]["messages"][0]["content"], "p2")

print("\nEl limite diario corta")
falsos.pon_fila("USUARIO#ana@airbus.com", dict(ANA, limite_preguntas_dia=2))
comprueba("429", pregunta("otra mas", COOKIE)["statusCode"], 429)
falsos.pon_fila("USUARIO#ana@airbus.com", ANA)

print("\nSin los tres interruptores, el asistente no contesta")
falsos.pon_fila("CONFIG", {"asistente_global": False}, "GLOBAL")
r_ = pregunta("hola", COOKIE)
comprueba("403", r_["statusCode"], 403)
comprueba("y dice que es global", "plataforma" in cuerpo(r_)["error"], True)
falsos.pon_fila("CONFIG", {"asistente_global": True}, "GLOBAL")
falsos.pon_fila("PERFIL#cli-airbus", dict(PERFIL, permisos={"asistente": False}))
comprueba("perfil sin asistente, 403", pregunta("hola", COOKIE)["statusCode"], 403)
falsos.pon_fila("PERFIL#cli-airbus", PERFIL)

print("\nSin sesion, nada")
comprueba("401", pregunta("hola", None)["statusCode"], 401)

print("\nUna pregunta vacia o kilometrica")
comprueba("vacia, 400", pregunta("   ", COOKIE)["statusCode"], 400)
comprueba("de 3.000 caracteres, 400", pregunta("x" * 3000, COOKIE)["statusCode"], 400)

print("\nSi el modelo declina, no se devuelve un hueco")
COLA[:] = [texto("", stop="refusal")]
r_ = pregunta("algo raro", COOKIE)
comprueba("200 con mensaje util", r_["statusCode"], 200)
comprueba("y un texto, no vacio", len(cuerpo(r_)["respuesta"]) > 20, True)

print("\nSi la API falla, el usuario no ve una traza")
def _revienta(**kw):
    raise RuntimeError("la red")
L.cliente().beta.messages.create = _revienta
L.cliente().messages.create = _revienta
r_ = pregunta("y ahora?", COOKIE)
comprueba("502", r_["statusCode"], 502)
comprueba("sin detalles internos", "la red" in r_["body"], False)

print("\nEl coste se calcula con los precios de Opus 5.5")
class _U:
    input_tokens = 1_000_000
    output_tokens = 0
    cache_read_input_tokens = 0
    cache_creation_input_tokens = 0
comprueba("un millon de entrada son 4 dolares", round(L.coste(_U()), 2), 4.00)
class _U2(_U):
    input_tokens = 0
    output_tokens = 1_000_000
comprueba("un millon de salida, 20", round(L.coste(_U2()), 2), 20.00)
class _U3(_U):
    input_tokens = 0
    cache_read_input_tokens = 1_000_000
comprueba("y leido de cache, 0,20", round(L.coste(_U3()), 2), 0.20)

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("El asistente se comporta.")
