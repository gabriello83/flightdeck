"""
El asistente, con la API de Claude falseada.

Lo que se comprueba no es la calidad de la respuesta: es que el recorte ocurre
ANTES de la llamada. Si el coste de servicio llegara al modelo, daria igual lo
bien escrito que estuviera el recetario, porque el dato ya habria salido del
ambito. Eso es lo que se mide aqui.

    python3 infra/api/test_asistente.py
"""

import json
import os
import sys
import types

AQUI = __file__.rsplit("/", 1)[0]
sys.path.insert(0, AQUI)

import falsos  # noqa: E402

falsos.instala()
falsos.SECRETOS["s/clave"] = "sk-de-pega"
os.environ.update(TABLA="t", BUCKET_DATOS="b", SECRETO_CLAVE="s/clave",
                  MODELO="claude-opus-5-5")

# ---------------------------------------------------------------- Claude falso
LLAMADAS = []
SIGUIENTE = {"texto": "En septiembre hubo 1.107 visitas reales.", "stop": "end_turn"}


class _BadRequest(Exception):
    pass


class _Uso:
    input_tokens = 1500
    output_tokens = 120
    cache_read_input_tokens = 2400
    cache_creation_input_tokens = 0


class _Respuesta:
    def __init__(self):
        self.content = [types.SimpleNamespace(type="thinking", thinking=""),
                        types.SimpleNamespace(type="text", text=SIGUIENTE["texto"])]
        self.stop_reason = SIGUIENTE["stop"]
        self.usage = _Uso()


class _Mensajes:
    def create(self, **kw):
        LLAMADAS.append(kw)
        return _Respuesta()


class _ClienteFalso:
    def __init__(self, **kw):
        self.messages = _Mensajes()
        self.beta = types.SimpleNamespace(messages=_Mensajes())


sys.modules["anthropic"] = types.SimpleNamespace(
    Anthropic=lambda **kw: _ClienteFalso(**kw), BadRequestError=_BadRequest)

import lambda_asistente as L  # noqa: E402

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

# De operaciones: un cliente ya no tiene panel (docs/49), y el asistente
# contesta con el panel. El recorte del coste es el mismo, por debajo de direccion.
falsos.pon_panel("cli-airbus", PANEL)
falsos.pon_fila("PERFIL#cli-airbus", {
    "nombre": "AIRBUS", "tipo": "operaciones",
    "ambito": {"clientes": ["AIRBUS"], "centros": ["AIRBUS GETAFE"], "delegaciones": []},
    "sesiones": ["resumen", "disponibilidad"],
    "permisos": {"asistente": True},
})
falsos.pon_fila("USUARIO#ana@airbus.com", {"nombre": "Ana", "perfil_id": "cli-airbus",
                                           "estado": "activo", "asistente": True})


def sesion_de(correo):
    import comun
    return comun.abre_sesion(correo)


def pregunta(texto, cookie, historial=None):
    ev = falsos.peticion("POST", "/api/pregunta",
                         {"pregunta": texto, "historial": historial or []}, cookie)
    return L.lambda_handler(ev, None)


COOKIE = sesion_de("ana@airbus.com")

# ----------------------------------------------------------------------
print("\nUna pregunta normal")
res = pregunta("Cuantas visitas hubo?", COOKIE)
comprueba("200", res["statusCode"], 200)
cuerpo = json.loads(res["body"])
comprueba("devuelve la respuesta", cuerpo["respuesta"], SIGUIENTE["texto"])
comprueba("y lo que ha costado", cuerpo["coste_usd"] > 0, True)
comprueba("una sola llamada al modelo", len(LLAMADAS), 1)

k = LLAMADAS[0]
print("\nLa llamada esta bien formada")
comprueba("el modelo", k["model"], "claude-opus-5-5")
comprueba("pensamiento adaptativo", k["thinking"], {"type": "adaptive"})
comprueba("esfuerzo explicito", k["output_config"]["effort"], "medium")
comprueba("sin budget_tokens (daria 400)", "budget_tokens" in json.dumps(k["thinking"]), False)
comprueba("tope de salida", k["max_tokens"], 2000)
comprueba("con reintento en otro modelo si declina", k.get("fallbacks"), "default")

print("\nEl recetario va en el sistema, y en cache")
comprueba("un solo bloque de sistema", len(k["system"]), 1)
comprueba("marcado para cachear", k["system"][0]["cache_control"], {"type": "ephemeral"})
comprueba("lleva las trampas", "00SE0000" in k["system"][0]["text"], True)
comprueba("y la de los partes del sistema", "SYSTEM" in k["system"][0]["text"], True)
comprueba("el recetario NO lleva nada variable",
          any(x in k["system"][0]["text"] for x in ["ana@airbus.com", "2026-10-01", "AIRBUS GETAFE"]), False)

print("\nLo que el modelo recibe esta ya recortado")
enviado = k["messages"][-1]["content"]
comprueba("las visitas si", "1107" in enviado, True)
comprueba("el COSTE DE SERVICIO no", "8856" in enviado, False)
comprueba("ni la palabra coste_servicio", "coste_servicio" in enviado, False)
comprueba("ni el valor de las existencias", "500000" in enviado, False)
comprueba("el inventario entero fuera", "pct_en_norma" in enviado, False)
comprueba("su ambito si", "AIRBUS GETAFE" in enviado, True)
comprueba("y la pregunta", "Cuantas visitas" in enviado, True)

print("\nEl historial se pasa, recortado a tres idas y venidas")
LLAMADAS.clear()
hist = [{"de": "usuario", "texto": f"p{i}"} for i in range(10)]
pregunta("y ahora?", COOKIE, hist)
comprueba("seis turnos mas la pregunta", len(LLAMADAS[0]["messages"]), 7)
comprueba("son los ultimos", LLAMADAS[0]["messages"][0]["content"], "p4")

print("\nEl consumo se cuenta por usuario y dia")
import comun  # noqa: E402
dia, usado = L.uso_de_hoy("ana@airbus.com")
comprueba("dos preguntas contadas", usado["preguntas"], 2)
comprueba("y el gasto acumulado", usado["gasto_usd"] > 0, True)

print("\nEl limite diario corta")
falsos.pon_fila("USUARIO#ana@airbus.com", {"nombre": "Ana", "perfil_id": "cli-airbus",
                                           "estado": "activo", "asistente": True,
                                           "limite_preguntas_dia": 2})
comprueba("429", pregunta("otra mas", COOKIE)["statusCode"], 429)

print("\nSin los tres interruptores, el asistente no contesta")
falsos.pon_fila("CONFIG", {"asistente_global": False}, "GLOBAL")
r = pregunta("hola", COOKIE)
comprueba("403", r["statusCode"], 403)
comprueba("y dice que es global", "plataforma" in json.loads(r["body"])["error"], True)
falsos.pon_fila("CONFIG", {"asistente_global": True}, "GLOBAL")

falsos.pon_fila("PERFIL#cli-airbus", {"nombre": "AIRBUS", "tipo": "operaciones",
                                      "sesiones": ["resumen"], "permisos": {"asistente": False}})
comprueba("perfil sin asistente, 403", pregunta("hola", COOKIE)["statusCode"], 403)
falsos.pon_fila("PERFIL#cli-airbus", {
    "nombre": "AIRBUS", "tipo": "operaciones",
    "ambito": {"clientes": ["AIRBUS"], "centros": ["AIRBUS GETAFE"], "delegaciones": []},
    "sesiones": ["resumen", "disponibilidad"], "permisos": {"asistente": True}})
falsos.pon_fila("USUARIO#ana@airbus.com", {"nombre": "Ana", "perfil_id": "cli-airbus",
                                           "estado": "activo", "asistente": True})

print("\nSin sesion, nada")
comprueba("401", pregunta("hola", None)["statusCode"], 401)

print("\nUna pregunta vacia o kilometrica")
comprueba("vacia, 400", pregunta("   ", COOKIE)["statusCode"], 400)
comprueba("de 3.000 caracteres, 400", pregunta("x" * 3000, COOKIE)["statusCode"], 400)

print("\nSi el modelo declina, no se devuelve un hueco")
SIGUIENTE["stop"] = "refusal"
r = pregunta("algo raro", COOKIE)
comprueba("200 con mensaje util", r["statusCode"], 200)
comprueba("y un texto, no vacio", len(json.loads(r["body"])["respuesta"]) > 20, True)
SIGUIENTE["stop"] = "end_turn"

print("\nSi la API falla, el usuario no ve una traza")
def _revienta(**kw):
    raise RuntimeError("la red")
L.cliente().beta.messages.create = _revienta
L.cliente().messages.create = _revienta
r = pregunta("y ahora?", COOKIE)
comprueba("502", r["statusCode"], 502)
comprueba("sin detalles internos", "la red" in r["body"], False)

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
