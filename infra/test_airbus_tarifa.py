"""
La tarifa de AIRBUS y su contraste con el planograma.

  1. El CSV de la tarifa se lee entero, sin codigos repetidos ni precios a cero.
  2. Un canal con el precio de la tarifa pasa; con otro, no; sin tarifa, se dice.
  3. Un canal sin articulo no se da por bueno.
  4. Los cafes se contrastan por su precio de venta.

    python3 infra/test_airbus_tarifa.py
"""

import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airbus_tarifa as at

fallos = []


def comprueba(que, ok, detalle=""):
    print(f"  {'ok   ' if ok else 'FALLO'} {que}{'' if ok else ' · ' + detalle}")
    if not ok:
        fallos.append(que)


t = at.lee_tarifa()
print("La tarifa")
comprueba("se lee entera", len(t) == 175, f"{len(t)} lineas")
comprueba("ningun precio a cero ni vacio", all(p and p > 0 for p in t.values()))
comprueba("el cafe solo cuesta 0,46", t["R01"] == Decimal("0.46"))
comprueba("el premium cuesta 0,61", t["R10"] == Decimal("0.61"))

print("\nEl planograma contra la tarifa")
c = lambda cod, precio, centro="AIRBUS TABLADA": {
    "centro": centro, "matricula": "M1", "canal": "11", "cod_articulo": cod,
    "articulo": "x", "precio_canal_ef": precio}
prob, res = at.contrasta([c("9354", "0,77"), c("9354", "0.82"), c("999", "1"), c("", "0")], t)
r = res["AIRBUS TABLADA"]
comprueba("uno bien", r["ok"] == 1)
comprueba("uno con otro precio", r["distinto"] == 1)
comprueba("uno sin tarifa", r["sin_tarifa"] == 1)
comprueba("uno sin articulo", r["sin_articulo"] == 1)
comprueba("tres problemas en total", len(prob) == 3, str(len(prob)))
comprueba("los centros no se mezclan",
          set(at.contrasta([c("9354", "0.77", "AIRBUS SAN PABLO SUR")], t)[1]) == {"AIRBUS SAN PABLO SUR"})

print("\nLos cafes")
pb, faltan = at.contrasta_bebidas(
    [{"cod_bebida": "R01", "bebida": "solo", "precio_venta": "0.46"},
     {"cod_bebida": "R01", "bebida": "solo", "precio_venta": "0.46"},
     {"cod_bebida": "R04", "bebida": "cl", "precio_venta": "0.50"}], t)
comprueba("R04 con otro precio se marca", [p[0] for p in pb] == ["R04"], str(pb))
comprueba("los cafes que M2 no trae se dicen", "R10" in faltan and "R01" not in faltan)

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS")
    sys.exit(1)
print("La tarifa de AIRBUS se sostiene.")
