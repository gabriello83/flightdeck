"""
Pruebas de quien ve que.

Las importantes son las del techo: comprueban que marcar un permiso en el panel
de administracion NO se lo da a un perfil cuyo tipo no lo admite.

    python3 infra/api/test_autorizacion.py
"""

import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import autorizacion as A  # noqa: E402

fallos = []


def comprueba(que, obtenido, esperado):
    if obtenido == esperado:
        print(f"  ok    {que}")
    else:
        print(f"  FALLO {que}: {obtenido!r} != {esperado!r}")
        fallos.append(que)


CLIENTE = {
    "perfil_id": "cli-airbus", "nombre": "AIRBUS", "tipo": "cliente",
    "ambito": {"clientes": ["AIRBUS"], "centros": [], "delegaciones": []},
    "sesiones": ["resumen", "venta_consumo", "disponibilidad", "rentabilidad", "usuarios"],
    "permisos": {"reordenar": True, "exportar": True, "asistente": True,
                 "whatsapp": True, "incidencia": True, "administrar": True},
    "reglas_negocio": {"umbral_rentabilidad_mes": 350},
}
OPERACIONES = dict(CLIENTE, perfil_id="ope", tipo="operaciones",
                   sesiones=["resumen", "rutas", "efectivo", "avisos", "rentabilidad"])
DIRECCION = dict(CLIENTE, perfil_id="dir", tipo="direccion",
                 sesiones=["resumen", "rentabilidad", "cumplimiento"])
ADMIN = {"perfil_id": "admin", "tipo": "admin", "sesiones": [], "permisos": {}}
USUARIO = {"correo": "a@b.c", "asistente": True}
CONFIG = {"asistente_global": True, "limite_preguntas_dia": 40}

# ----------------------------------------------------------------------
print("\nEl techo: un cliente no recibe lo que su tipo no admite")
p = A.permisos_efectivos(CLIENTE, USUARIO, CONFIG)
comprueba("puede reordenar", p["reordenar"], True)
comprueba("WhatsApp marcado pero NO concedido", p.get("whatsapp", False), False)
comprueba("incidencia marcada pero NO concedida", p.get("incidencia", False), False)
comprueba("administrar llega, pero en false", p["administrar"], False)
comprueba("y el vocabulario viene completo", sorted(p) == A.TODOS, True)
comprueba("ver es siempre si", p["ver"], True)

print("\nOperaciones si tiene WhatsApp e incidencia")
po = A.permisos_efectivos(OPERACIONES, USUARIO, CONFIG)
comprueba("WhatsApp", po["whatsapp"], True)
comprueba("incidencia", po["incidencia"], True)
comprueba("ve alarmas", po["alarmas_ver"], True)
comprueba("pero no las crea", po["alarmas_crear"], False)
comprueba("ni ve costes", po["ver_costes"], False)

print("\nDireccion anade costes y creacion de alarmas")
pd = A.permisos_efectivos(DIRECCION, USUARIO, CONFIG)
comprueba("ver costes", pd["ver_costes"], True)
comprueba("crear alarmas", pd["alarmas_crear"], True)
comprueba("administrar no", pd["administrar"], False)

print("\nEl admin lo tiene todo sin que nadie se lo conceda")
pa = A.permisos_efectivos(ADMIN, USUARIO, CONFIG)
comprueba("administrar", pa["administrar"], True)
comprueba("ver costes", pa["ver_costes"], True)

# ----------------------------------------------------------------------
print("\nLas sesiones tambien tienen techo")
sc = A.sesiones_de("cliente", CLIENTE["sesiones"])
comprueba("tres de cliente", len(sc), 3)
comprueba("rentabilidad fuera", "rentabilidad" in sc, False)
comprueba("usuarios fuera", "usuarios" in sc, False)
comprueba("orden del catalogo, no del alta", sc[0], "resumen")
comprueba("operaciones si llega a rutas", "rutas" in A.sesiones_de("operaciones", OPERACIONES["sesiones"]), True)
comprueba("pero no a rentabilidad", "rentabilidad" in A.sesiones_de("operaciones", OPERACIONES["sesiones"]), False)
comprueba("direccion si", "rentabilidad" in A.sesiones_de("direccion", DIRECCION["sesiones"]), True)
comprueba("el admin ve las 16", len(A.sesiones_de("admin", [])), 16)

# ----------------------------------------------------------------------
print("\nEl asistente necesita los tres interruptores")
comprueba("los tres puestos", A.asistente_habilitado(CONFIG, CLIENTE, USUARIO)[0], True)
comprueba("global apagado", A.asistente_habilitado({"asistente_global": False}, CLIENTE, USUARIO)[0], False)
comprueba("perfil apagado",
          A.asistente_habilitado(CONFIG, dict(CLIENTE, permisos={"asistente": False}), USUARIO)[0], False)
comprueba("usuario apagado",
          A.asistente_habilitado(CONFIG, CLIENTE, {"asistente": False})[0], False)
comprueba("y dice por que", "usuario" in A.asistente_habilitado(CONFIG, CLIENTE, {"asistente": False})[1], True)
comprueba("el admin no necesita que se lo marquen",
          A.asistente_habilitado(CONFIG, ADMIN, USUARIO)[0], True)

print("\nEl limite diario")
comprueba("dentro", A.dentro_del_limite(3, 40), (True, 37))
comprueba("justo al borde", A.dentro_del_limite(40, 40)[0], False)
comprueba("limite 0 es sin limite", A.dentro_del_limite(9999, 0)[0], True)

# ----------------------------------------------------------------------
print("\nEl recorte del panel: lo que no sale de aqui no llega al navegador")
PANEL = {
    "generado": "2026-10-01T04:45:00Z",
    "periodo": {"desde": "2026-06-03", "hasta": "2026-09-30"},
    "servicio": {"visitas": 1107, "coste_servicio": {"coste": 8856.0}, "merma": {}},
    "dinero": {"periodos": [{"periodo": "2026-09", "total": 1000}]},
    "sat": {"tareas": 21046},
    "jornadas": {"jornadas": 1288},
    "inventario": {"cumplimiento": {"pct_en_norma": 8.6}, "existencias": {"A": 500000}},
}
rc = A.recorta(PANEL, CLIENTE)
comprueba("el cliente recibe servicio", "servicio" in rc, True)
comprueba("y sat, por disponibilidad", "sat" in rc, True)
comprueba("NO recibe jornadas", "jornadas" in rc, False)
comprueba("NO recibe inventario", "inventario" in rc, False)
comprueba("y el coste de servicio se le quita", "coste_servicio" in rc["servicio"], False)
comprueba("las visitas si", rc["servicio"]["visitas"], 1107)
comprueba("lleva sus sesiones", len(rc["sesiones"]), 3)
comprueba("y su umbral", rc["reglas_negocio"]["umbral_rentabilidad_mes"], 350)

rd = A.recorta(PANEL, DIRECCION)
comprueba("direccion SI ve el coste", rd["servicio"]["coste_servicio"]["coste"], 8856.0)
comprueba("y el valor de las existencias", rd["inventario"]["existencias"]["A"], 500000)

print("\nRecortar no toca el panel original (regresion)")
# Este fallo existio: el recorte del cliente borraba el coste del panel de
# verdad, y el siguiente perfil en leerlo ya no lo encontraba.
A.recorta(PANEL, CLIENTE)
comprueba("el panel original sigue entero", "coste_servicio" in PANEL["servicio"], True)
comprueba("y direccion lo sigue viendo despues",
          "coste_servicio" in A.recorta(PANEL, DIRECCION)["servicio"], True)
comprueba("el cliente sigue sin verlo",
          "coste_servicio" in A.recorta(PANEL, CLIENTE)["servicio"], False)

print("\nEl asistente recibe exactamente eso, y nada mas")
ctx = A.contexto_asistente(A.recorta(PANEL, CLIENTE), CLIENTE)
comprueba("sin coste de servicio", "coste_servicio" in ctx["datos"]["servicio"], False)
comprueba("sin jornadas", "jornadas" in ctx["datos"], False)
comprueba("con su ambito", ctx["ambito"]["clientes"], ["AIRBUS"])

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("La autorizacion se comporta.")
