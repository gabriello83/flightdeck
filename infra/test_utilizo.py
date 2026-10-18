"""
Utilizo (docs/60): cuanto usa VenCloud cada persona, dia a dia, y el detalle de
las dos personas con dos cuentas en la revision de clientes.

    python3 infra/test_utilizo.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import revision as RV  # noqa: E402
import utilizo as UT  # noqa: E402

fallos = 0


def comprueba(que, obtenido, esperado):
    global fallos
    ok = obtenido == esperado
    print(f"  {'ok   ' if ok else 'FALLO'} {que}" + ("" if ok else f": {obtenido!r} != {esperado!r}"))
    if not ok:
        fallos += 1


HOY = datetime.date(2026, 10, 19)


def hora(usuario, dia, h, veces, primera="", ultima=""):
    return {"tipo": "hora", "usuario": usuario, "dia": dia, "hora": h, "entidad": "", "accion": "",
            "veces": veces, "primera": f"{dia} {primera}" if primera else "",
            "ultima": f"{dia} {ultima}" if ultima else ""}


def entidad(usuario, dia, ent, acc, veces):
    return {"tipo": "entidad", "usuario": usuario, "dia": dia, "hora": -1, "entidad": ent,
            "accion": acc, "veces": veces, "primera": "", "ultima": ""}


print("La historia: lo de esta noche dentro, hoy fuera")
filas = [
    hora("M.GARCIA", "2026-10-18", 9, 10, "09:05:00", "09:59:00"),
    hora("M.GARCIA", "2026-10-18", 10, 5, "10:00:00", "10:30:00"),
    hora("M2.GARCIA", "2026-10-18", 10, 3, "10:10:00", "10:20:00"),
    hora("m2.garcia", "2026-10-18", 16, 2, "16:00:00", "16:45:12"),
    entidad("M.GARCIA", "2026-10-18", "MaquinaCanal", "U", 12),
    entidad("M2.GARCIA", "2026-10-18", "MaquinaCanal", "U", 3),
    entidad("M2.GARCIA", "2026-10-18", "Maquina", "I", 2),
    hora("A.PEREZ", "2026-10-18", 8, 7, "08:00:00", "08:40:00"),
    entidad("A.PEREZ", "2026-10-18", "Pdv", "U", 7),
    hora("A.PEREZ", "2026-10-19", 8, 99, "08:00:00", "08:10:00"),
]
viejo = {"dias": {"2026-08-01": {"A.PEREZ": {"horas": {"9": 1}, "entidades": {}, "primera": "", "ultima": ""}},
                  "2026-10-18": {"X.VIEJO": {"horas": {"9": 1}, "entidades": {}, "primera": "", "ultima": ""}},
                  "2026-10-17": {"A.PEREZ": {"horas": {"11": 4}, "entidades": {"Pdv|U": 4},
                                             "primera": "11:00:00", "ultima": "11:30:00"}}}}
e = UT.actividad(viejo, filas, HOY)
comprueba("hoy no se guarda, que va a medias", "2026-10-19" in e["dias"], False)
comprueba("mas de dos meses, fuera", "2026-08-01" in e["dias"], False)
comprueba("un dia que llega sustituye al guardado", "X.VIEJO" in e["dias"]["2026-10-18"], False)
comprueba("el dia que no llega se queda", e["dias"]["2026-10-17"]["A.PEREZ"]["horas"], {"11": 4})
comprueba("el usuario, en mayusculas", sorted(e["dias"]["2026-10-18"]),
          ["A.PEREZ", "M.GARCIA", "M2.GARCIA"])

print("\nTodos los usuarios, y las dos cuentas de una persona juntas")
gente = {p["nombre"]: p for p in UT.personas(e)}
comprueba("M. Garcia, A.PEREZ; J. Marcos sin actividad no sale", sorted(gente), ["A.PEREZ", "M. García"])
mg = gente["M. García"]["dias"][0]
comprueba("acciones de las dos cuentas", mg["acciones"], 20)
comprueba("horas: la union, las 10 cuentan una vez", mg["horas"], 3)
comprueba("primera y ultima de las dos cuentas", (mg["primera"], mg["ultima"]), ("09:05:00", "16:45:12"))
comprueba("por hora, sumadas", mg["por_hora"], {"9": 10, "10": 8, "16": 2})
comprueba("que toco, de mas a menos", mg["entidades"], [["MaquinaCanal", "U", 15], ["Maquina", "I", 2]])
comprueba("las dos cuentas", mg["cuentas"], ["M.GARCIA", "M2.GARCIA"])
comprueba("A.PEREZ, sus dos dias, el ultimo primero", [d["dia"] for d in gente["A.PEREZ"]["dias"]],
          ["2026-10-18", "2026-10-17"])

print("\nLa pagina y el cuadrado")
f = UT.fichero(e, HOY)
comprueba("los dias, el ultimo primero", f["dias"], ["2026-10-18", "2026-10-17"])
comprueba("el cuadrado: usuarios y acciones del ultimo dia", UT.cuadrado(f),
          {"dia": "2026-10-18", "usuarios": 2, "acciones": 27, "horas": 4})
comprueba("sin informe ni historia, se dice", "M15" in UT.fichero(None, HOY)["sin_dato"], True)
comprueba("y el cuadrado lo repite", "sin_dato" in UT.cuadrado(UT.fichero(None, HOY)), True)
comprueba("sin ningun dia, se dice", "sin_dato" in UT.cuadrado(UT.fichero({"dias": {}}, HOY)), True)

print("\nEn la revision de clientes: solo las dos personas, aunque no hicieran nada")
r = RV.calcula([], None, None, HOY, e)
comprueba("M. Garcia y J. Marcos", [g["nombre"] for g in r["actividad"]["grupos"]], ["M. García", "J. Marcos"])
comprueba("J. Marcos sin dias", r["actividad"]["grupos"][1]["dias"], [])
comprueba("sin el informe, se dice", "M15" in RV.calcula([], None, None, HOY, None)["actividad"]["sin_dato"], True)
comprueba("un perfil con ambito no lo lleva", "actividad" in RV.calcula([], None, None, HOY), False)

print()
print("todo bien" if not fallos else f"{fallos} fallos")
sys.exit(1 if fallos else 0)
