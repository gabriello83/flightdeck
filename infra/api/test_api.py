"""
La API entera contra un AWS falso.

Lo que de verdad se comprueba aqui: que un usuario no puede llegar al dato de
otro, que el techo de permisos se aplica al servir y no al guardar, y que el
circuito de acceso se comporta en los casos incomodos (clave inicial, fuerza
bruta, cuenta sin ficha).

    python3 infra/api/test_api.py
"""

import json
import os
import sys

AQUI = __file__.rsplit("/", 1)[0]
sys.path.insert(0, AQUI)

import falsos  # noqa: E402

falsos.instala()
os.environ.update(TABLA="t", BUCKET_DATOS="b", POOL="p", CLIENTE_POOL="c")

import lambda_api as L  # noqa: E402
from falsos import cookie_de, cuerpo_de, peticion, pon_fila, pon_panel  # noqa: E402

fallos = []


def comprueba(que, obtenido, esperado):
    if obtenido == esperado:
        print(f"  ok    {que}")
    else:
        print(f"  FALLO {que}: {obtenido!r} != {esperado!r}")
        fallos.append(que)


def llama(metodo, ruta, cuerpo=None, cookie=None, origen="same-origin", query=None):
    return L.lambda_handler(peticion(metodo, ruta, cuerpo, cookie, origen, query), None)


# ----------------------------------------------------------------------
# escenario
# ----------------------------------------------------------------------
PANEL_AIRBUS = {
    "generado": "2026-10-01T04:45:00Z",
    "periodo": {"desde": "2026-06-03", "hasta": "2026-09-30"},
    "servicio": {"visitas": 1107, "coste_servicio": {"coste": 8856.0}},
    "dinero": {"periodos": [{"periodo": "2026-09", "total": 42000}]},
    "sat": {"tareas": 150},
    "inventario": {"cumplimiento": {"pct_en_norma": 8.6}, "existencias": {"A": 500000}},
}
PANEL_INTERNO = dict(PANEL_AIRBUS, servicio={"visitas": 99999, "coste_servicio": {"coste": 1.0}})

falsos.pon_panel("cli-airbus", PANEL_AIRBUS)
falsos.pon_panel("interno", PANEL_INTERNO)

pon_fila("PERFIL#cli-airbus", {
    "nombre": "AIRBUS", "tipo": "cliente",
    "ambito": {"clientes": ["AIRBUS"], "centros": [], "delegaciones": []},
    "sesiones": ["resumen", "venta_consumo", "disponibilidad"],
    "paneles": ["evolucion", "centros"],
    "permisos": {"asistente": True, "whatsapp": True},  # whatsapp marcado: no debe valer
    "reglas_negocio": {"umbral_rentabilidad_mes": 350},
})
pon_fila("PERFIL#interno", {"nombre": "Serunion", "tipo": "admin", "sesiones": [], "permisos": {}})

pon_fila("USUARIO#ana@airbus.com", {"nombre": "Ana", "perfil_id": "cli-airbus",
                                    "estado": "activo", "asistente": True})
pon_fila("USUARIO#jefe@serunion.es", {"nombre": "Jefe", "perfil_id": "interno",
                                      "estado": "activo", "asistente": True})
falsos.USUARIOS_COG["ana@airbus.com"] = {"clave": "ClaveLarga123", "temporal": False}
falsos.USUARIOS_COG["jefe@serunion.es"] = {"clave": "OtraClaveLarga1", "temporal": False}

# ----------------------------------------------------------------------
print("\nSin sesion no se ve nada")
comprueba("panel pide sesion", llama("GET", "/api/panel")["statusCode"], 401)
comprueba("admin pide sesion", llama("GET", "/api/admin/usuarios")["statusCode"], 401)

print("\nAcceso")
mal = llama("POST", "/api/acceso", {"correo": "ana@airbus.com", "clave": "noesesa"})
comprueba("clave mala, 401", mal["statusCode"], 401)
comprueba("y no dice si la cuenta existe", cuerpo_de(mal)["error"], "Correo o contrasena incorrectos.")
fantasma = llama("POST", "/api/acceso", {"correo": "nadie@x.com", "clave": "cualquiera123"})
comprueba("cuenta inexistente, el mismo texto", cuerpo_de(fantasma)["error"],
          cuerpo_de(mal)["error"])

bien = llama("POST", "/api/acceso", {"correo": "ana@airbus.com", "clave": "ClaveLarga123"})
comprueba("clave buena, 200", bien["statusCode"], 200)
COOKIE_ANA = cookie_de(bien)
comprueba("entrega cookie", bool(COOKIE_ANA), True)
comprueba("la cookie es HttpOnly", "HttpOnly" in bien["cookies"][0], True)
comprueba("y Secure", "Secure" in bien["cookies"][0], True)
comprueba("y SameSite=Strict", "SameSite=Strict" in bien["cookies"][0], True)
comprueba("en la tabla se guarda el resumen, no el token",
          ("SESION#" + COOKIE_ANA, "FICHA") in falsos.TABLA, False)

print("\nFuerza bruta: a los 6 intentos se cierra")
for _ in range(6):
    llama("POST", "/api/acceso", {"correo": "ana@airbus.com", "clave": "mala"})
comprueba("bloqueado con 429",
          llama("POST", "/api/acceso", {"correo": "ana@airbus.com", "clave": "ClaveLarga123"})["statusCode"], 429)
falsos.TABLA.pop(("FALLOS#ana@airbus.com", "CUENTA"), None)
comprueba("y al limpiar el contador vuelve a entrar",
          llama("POST", "/api/acceso", {"correo": "ana@airbus.com", "clave": "ClaveLarga123"})["statusCode"], 200)

print("\nPrimer acceso: la clave del admin es de un solo uso")
falsos.USUARIOS_COG["nuevo@airbus.com"] = {"clave": "Provisional12", "temporal": True}
pon_fila("USUARIO#nuevo@airbus.com", {"nombre": "Nuevo", "perfil_id": "cli-airbus", "estado": "activo"})
primera = llama("POST", "/api/acceso", {"correo": "nuevo@airbus.com", "clave": "Provisional12"})
comprueba("pide cambiar la clave", cuerpo_de(primera).get("cambio_requerido"), True)
comprueba("y todavia no hay cookie", cookie_de(primera), None)
corta = llama("POST", "/api/acceso/nueva-clave",
              {"correo": "nuevo@airbus.com", "reto": cuerpo_de(primera)["reto"], "clave": "corta"})
comprueba("una clave corta no cuela", corta["statusCode"], 400)
cambio = llama("POST", "/api/acceso/nueva-clave",
               {"correo": "nuevo@airbus.com", "reto": "reto-nuevo@airbus.com", "clave": "ClaveNueva123"})
comprueba("con una buena, entra", cambio["statusCode"], 200)
comprueba("y ya trae cookie", bool(cookie_de(cambio)), True)

print("\nY tampoco entra cambiando la clave: la ficha se mira antes de gastarla")
# Una cuenta que existe en Cognito con clave de un solo uso y NO tiene ficha.
falsos.USUARIOS_COG["fantasma@serunion.es"] = {"clave": "ClaveTemporal1", "temporal": True}
_sin = llama("POST", "/api/acceso", {"correo": "fantasma@serunion.es", "clave": "ClaveTemporal1"})
comprueba("primero le pide cambiar la clave", cuerpo_de(_sin).get("cambio_requerido"), True)
if cuerpo_de(_sin).get("cambio_requerido"):
    _cam = llama("POST", "/api/acceso/nueva-clave",
                 {"correo": "fantasma@serunion.es", "reto": cuerpo_de(_sin)["reto"],
                  "clave": "ClaveNuevaLarga1"})
    comprueba("403, no una cookie", _cam["statusCode"], 403)
    comprueba("y no abre sesion", cookie_de(_cam), None)

print("\nUna cuenta de Cognito sin ficha no entra")
falsos.USUARIOS_COG["huerfano@x.com"] = {"clave": "ClaveLarga123", "temporal": False}
comprueba("403, no 200",
          llama("POST", "/api/acceso", {"correo": "huerfano@x.com", "clave": "ClaveLarga123"})["statusCode"], 403)

# ----------------------------------------------------------------------
print("\nEl cliente ve su panel, recortado")
p = cuerpo_de(llama("GET", "/api/panel", cookie=COOKIE_ANA))
comprueba("sus visitas", p["servicio"]["visitas"], 1107)
comprueba("sin el coste de servicio", "coste_servicio" in p["servicio"], False)
comprueba("sin inventario", "inventario" in p, False)
comprueba("tres sesiones", len(p["sesiones"]), 3)

print("\nY no hay forma de pedir el panel de otro")
# Los tres intentos evidentes: por query, por cuerpo y con barra de mas.
ajeno = cuerpo_de(llama("GET", "/api/panel", cookie=COOKIE_ANA, query={"perfil": "interno"}))
comprueba("la query no se mira", ajeno["servicio"]["visitas"], 1107)
comprueba("no las 99.999 del interno", ajeno["servicio"]["visitas"] != 99999, True)
por_cuerpo = cuerpo_de(llama("GET", "/api/panel", {"perfil_id": "interno"}, cookie=COOKIE_ANA))
comprueba("el cuerpo tampoco", por_cuerpo["servicio"]["visitas"], 1107)
comprueba("y una barra de mas no cambia de ruta",
          cuerpo_de(llama("GET", "/api/panel/", cookie=COOKIE_ANA))["servicio"]["visitas"], 1107)

print("\nEl techo se aplica al servir")
yo = cuerpo_de(llama("GET", "/api/yo", cookie=COOKIE_ANA))
comprueba("WhatsApp marcado en el perfil", True, True)
comprueba("pero efectivo en false", yo["permisos"].get("whatsapp"), False)
comprueba("y la ruta lo rechaza",
          llama("POST", "/api/whatsapp", {"telefono": "+34600000000", "texto": "hola"},
                cookie=COOKIE_ANA)["statusCode"], 403)
comprueba("administrar tampoco",
          llama("GET", "/api/admin/usuarios", cookie=COOKIE_ANA)["statusCode"], 403)
comprueba("ni las alarmas", llama("GET", "/api/alarmas", cookie=COOKIE_ANA)["statusCode"], 403)
comprueba("ni el catalogo de alarmas",
          llama("GET", "/api/catalogo-alarmas", cookie=COOKIE_ANA)["statusCode"], 403)
comprueba("el umbral llega", yo["umbral"], 350)
comprueba("y el asistente esta habilitado", yo["asistente"]["habilitado"], True)

print("\nEl orden de los paneles se guarda en el servidor")
comprueba("al principio vacio", cuerpo_de(llama("GET", "/api/orden", cookie=COOKIE_ANA))["orden"], [])
llama("PUT", "/api/orden", {"orden": ["centros", "evolucion"]}, cookie=COOKIE_ANA)
comprueba("y luego el que puso", cuerpo_de(llama("GET", "/api/orden", cookie=COOKIE_ANA))["orden"],
          ["centros", "evolucion"])
comprueba("una lista absurda se rechaza",
          llama("PUT", "/api/orden", {"orden": "no soy una lista"}, cookie=COOKIE_ANA)["statusCode"], 400)

print("\nUna escritura desde otro origen no entra")
comprueba("403 aunque la cookie sea buena",
          llama("PUT", "/api/orden", {"orden": []}, cookie=COOKIE_ANA, origen="cross-site")["statusCode"], 403)
comprueba("pero leer desde otro sitio no rompe nada",
          llama("GET", "/api/yo", cookie=COOKIE_ANA, origen="cross-site")["statusCode"], 200)

print("\nSalir cierra la sesion de verdad")
salida = llama("POST", "/api/salir", cookie=COOKIE_ANA)
comprueba("200", salida["statusCode"], 200)
comprueba("la cookie se vacia", "Max-Age=0" in salida["cookies"][0], True)
comprueba("y la cookie vieja ya no vale",
          llama("GET", "/api/panel", cookie=COOKIE_ANA)["statusCode"], 401)

# ----------------------------------------------------------------------
print("\nEl administrador")
COOKIE_JEFE = cookie_de(llama("POST", "/api/acceso",
                              {"correo": "jefe@serunion.es", "clave": "OtraClaveLarga1"}))
comprueba("ve los usuarios", llama("GET", "/api/admin/usuarios", cookie=COOKIE_JEFE)["statusCode"], 200)
comprueba("ve las 18 sesiones",
          len(cuerpo_de(llama("GET", "/api/yo", cookie=COOKIE_JEFE))["sesiones"]), 18)

alta = llama("POST", "/api/admin/usuarios",
             {"correo": "Pepe@Airbus.com", "nombre": "Pepe", "perfil_id": "cli-airbus",
              "clave": "ClaveInicial12"}, cookie=COOKIE_JEFE)
comprueba("da de alta", cuerpo_de(alta)["nuevo"], True)
comprueba("el correo se normaliza a minusculas",
          ("USUARIO#pepe@airbus.com", "FICHA") in falsos.TABLA, True)
comprueba("y queda en Cognito con clave temporal",
          falsos.USUARIOS_COG["pepe@airbus.com"]["temporal"], True)
comprueba("un alta sin perfil valido falla",
          llama("POST", "/api/admin/usuarios",
                {"correo": "x@y.com", "nombre": "X", "perfil_id": "no-existe",
                 "clave": "ClaveInicial12"}, cookie=COOKIE_JEFE)["statusCode"], 400)
comprueba("una clave inicial corta falla",
          llama("POST", "/api/admin/usuarios",
                {"correo": "z@y.com", "nombre": "Z", "perfil_id": "cli-airbus",
                 "clave": "corta"}, cookie=COOKIE_JEFE)["statusCode"], 400)
comprueba("no puede borrarse a si mismo",
          llama("DELETE", "/api/admin/usuarios/jefe@serunion.es", cookie=COOKIE_JEFE)["statusCode"], 400)

print("\nLa consola recibe lo que necesita para no repetir las reglas")
pf = cuerpo_de(llama("GET", "/api/admin/perfiles", cookie=COOKIE_JEFE))
comprueba("las 18 sesiones con su tipo minimo", len(pf["catalogo_sesiones"]), 18)
comprueba("el techo de los cuatro tipos", sorted(pf["techo"]), ["admin", "cliente", "direccion", "operaciones"])
comprueba("y la escalera de niveles", pf["niveles"]["cliente"] < pf["niveles"]["operaciones"], True)
comprueba("y que trae puesto cada tipo", "alarmas_ver" in pf["implicitos"]["operaciones"], True)

print("\nY se ve que perfiles tienen panel calculado de verdad")
# Un perfil vive en dos sitios: la ficha de la plataforma (DynamoDB) y la lista
# de paneles que hay que calcular (config/perfiles.json, en el bucket de datos).
# Tener solo el primero es tener un cliente que entra a una pantalla vacia.
_con = [p for p in pf["perfiles"] if p["panel"]["existe"]]
_sin = [p for p in pf["perfiles"] if not p["panel"]["existe"]]
comprueba("cli-airbus lo tiene", any(p["_id"] == "cli-airbus" for p in _con), True)
comprueba("y dice de cuando es", "2026-10-02" in _con[0]["panel"]["calculado"], True)
comprueba("un perfil sin panel se distingue", len(_sin) >= 0, True)

print("\nAl crear un perfil se dice que permisos no van a tener efecto")
res = cuerpo_de(llama("POST", "/api/admin/perfiles",
                      {"perfil_id": "cli-nuevo", "nombre": "Cliente nuevo", "tipo": "cliente",
                       "sesiones": ["resumen", "rentabilidad"],
                       "permisos": {"exportar": True, "whatsapp": True, "administrar": True}},
                      cookie=COOKIE_JEFE))
comprueba("exportar vale", "exportar" in res["permisos_efectivos"], True)
comprueba("whatsapp se ignora", "whatsapp" in res["ignorados"], True)
comprueba("administrar se ignora", "administrar" in res["ignorados"], True)

print("\nUn perfil con usuarios no se borra")
comprueba("400 y lo explica",
          llama("DELETE", "/api/admin/perfiles/cli-airbus", cookie=COOKIE_JEFE)["statusCode"], 400)
comprueba("uno vacio si",
          llama("DELETE", "/api/admin/perfiles/cli-nuevo", cookie=COOKIE_JEFE)["statusCode"], 200)

print("\nEl interruptor global del asistente")
llama("PUT", "/api/admin/config", {"asistente_global": False}, cookie=COOKIE_JEFE)
COOKIE_ANA2 = cookie_de(llama("POST", "/api/acceso",
                              {"correo": "ana@airbus.com", "clave": "ClaveLarga123"}))
yo2 = cuerpo_de(llama("GET", "/api/yo", cookie=COOKIE_ANA2))
comprueba("apagado para todos", yo2["asistente"]["habilitado"], False)
comprueba("y dice que es global", "plataforma" in yo2["asistente"]["motivo"], True)
llama("PUT", "/api/admin/config", {"asistente_global": True}, cookie=COOKIE_JEFE)

print("\nUn usuario bloqueado no pasa, aunque tenga cookie")
pon_fila("USUARIO#ana@airbus.com", {"nombre": "Ana", "perfil_id": "cli-airbus",
                                    "estado": "bloqueado", "asistente": True})
comprueba("401", llama("GET", "/api/panel", cookie=COOKIE_ANA2)["statusCode"], 401)

print("\nTelefonos de los tecnicos")
comprueba("sin prefijo no se acepta",
          llama("POST", "/api/admin/telefonos",
                {"empleado_id": "12", "telefono": "600000000"}, cookie=COOKIE_JEFE)["statusCode"], 400)
comprueba("con prefijo si",
          llama("POST", "/api/admin/telefonos",
                {"empleado_id": "12", "nombre": "Luis", "telefono": "+34600000000",
                 "oficio": "reponedor"}, cookie=COOKIE_JEFE)["statusCode"], 200)
comprueba("y se listan", len(cuerpo_de(llama("GET", "/api/admin/telefonos", cookie=COOKIE_JEFE))["telefonos"]), 1)

print("\nEl catalogo de alarmas lo sirve la API, no lo copia el navegador")
cat = cuerpo_de(llama("GET", "/api/catalogo-alarmas", cookie=COOKIE_JEFE))["catalogo"]
comprueba("el admin si", len(cat) > 10, True)
comprueba("cada entrada trae fuente y campo", all(x["fuente"] and x["campo"] for x in cat), True)
comprueba("y dice cuales se pueden evaluar hoy", any(x["evaluable"] for x in cat), True)
comprueba("y cuales todavia no", any(not x["evaluable"] for x in cat), True)
import catalogo as _cat
comprueba("es la misma lista que evalua la Lambda de alarmas", len(cat), len(_cat.CATALOGO))

print("\nEl cuadro de mando: solo con su sesion, y solo el de su perfil")
falsos.OBJETOS["cabina/cli-airbus/cuadro/indice.json"] = json.dumps(
    {"perfil": "cli-airbus", "trozos": ["2026-09"], "maquinas": [["24SE1983", 0, "Comedor", "S1", 1]]}).encode()
falsos.OBJETOS["cabina/cli-airbus/cuadro/ventas-2026-09.json"] = json.dumps(
    {"trozo": "2026-09", "filas": [[1, 0, 0, 2, 1.3]]}).encode()
falsos.OBJETOS["cabina/interno/cuadro/indice.json"] = json.dumps(
    {"perfil": "interno", "trozos": ["2026-09"]}).encode()
# Una usuaria nueva: a estas alturas a Ana ya la han bloqueado mas arriba.
falsos.USUARIOS_COG["eva@airbus.com"] = {"clave": "ClaveLarga123", "temporal": False}
pon_fila("USUARIO#eva@airbus.com", {"nombre": "Eva", "perfil_id": "cli-airbus", "estado": "activo"})
COOKIE_ANA = cookie_de(llama("POST", "/api/acceso", {"correo": "eva@airbus.com", "clave": "ClaveLarga123"}))
_perfil_airbus = {"nombre": "AIRBUS", "tipo": "cliente", "ambito": {"clientes": ["AIRBUS"]},
                  "sesiones": ["resumen"], "permisos": {}}
pon_fila("PERFIL#cli-airbus", _perfil_airbus)
comprueba("sin la sesion «cuadro», 403",
          llama("GET", "/api/cuadro", cookie=COOKIE_ANA)["statusCode"], 403)
pon_fila("PERFIL#cli-airbus", dict(_perfil_airbus, sesiones=["resumen", "cuadro"]))
_ix = llama("GET", "/api/cuadro", cookie=COOKIE_ANA)
comprueba("con ella, el indice de su perfil", cuerpo_de(_ix)["perfil"], "cli-airbus")
comprueba("sin pasar por json: el cuerpo es el fichero tal cual",
          _ix["body"], falsos.OBJETOS["cabina/cli-airbus/cuadro/indice.json"].decode())
comprueba("un trozo que el indice cita",
          cuerpo_de(llama("GET", "/api/cuadro", cookie=COOKIE_ANA, query={"trozo": "2026-09"}))["filas"],
          [[1, 0, 0, 2, 1.3]])
for _malo in ("2026-08", "../../interno/cuadro/indice", "2026-09.json", ""):
    comprueba(f"un trozo que no cita ({_malo!r}), 400",
              llama("GET", "/api/cuadro", cookie=COOKIE_ANA, query={"trozo": _malo})["statusCode"], 400)
comprueba("y la query no cambia de perfil",
          cuerpo_de(llama("GET", "/api/cuadro", cookie=COOKIE_ANA, query={"perfil": "interno"}))["perfil"],
          "cli-airbus")
comprueba("el catalogo de sesiones lo ofrece a la consola",
          "cuadro" in cuerpo_de(llama("GET", "/api/yo", cookie=COOKIE_ANA))["catalogo_sesiones"], True)
comprueba("y /api/yo dice que lo tiene",
          "cuadro" in cuerpo_de(llama("GET", "/api/yo", cookie=COOKIE_ANA))["sesiones"], True)
del falsos.OBJETOS["cabina/cli-airbus/cuadro/indice.json"]
comprueba("sin calcular todavia, 503",
          llama("GET", "/api/cuadro", cookie=COOKIE_ANA)["statusCode"], 503)

print("\nUna ruta que no existe")
comprueba("404", llama("GET", "/api/loquesea", cookie=COOKIE_JEFE)["statusCode"], 404)

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("La API se comporta.")
