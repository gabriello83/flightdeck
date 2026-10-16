"""
Los almacenes por dentro (docs/54): las piezas sueltas de almacenes.py.

La prueba de punta a punta, con el S3 falso, esta en test_agregados.py. Aqui
van las trampas del dato: los codigos juntos en una columna, una foto que no
es una foto, la existencia negativa y el movimiento que llega desordenado.

    python3 infra/test_almacenes.py
"""

import base64
import datetime
import sys

AQUI = __file__.rsplit("/", 1)[0]
sys.path.insert(0, AQUI)

import almacenes as AL  # noqa: E402

fallos = []


def comprueba(que, dado, esperado):
    ok = dado == esperado
    print(f"  {'ok   ' if ok else 'FALLO'} {que}" + ("" if ok else f": {dado!r} != {esperado!r}"))
    if not ok:
        fallos.append(que)


print("Los codigos de barras, juntos en una columna")
comprueba("codigo|cantidad|tipo separados por punto y coma",
          AL.codigos("8410000000016|1|0; 8410000000023|24|0"),
          [{"codigo": "8410000000016", "cantidad": 1}, {"codigo": "8410000000023", "cantidad": 24}])
comprueba("vacio es ninguno", AL.codigos(None), [])
comprueba("sin cantidad no se inventa", AL.codigos("123"), [{"codigo": "123", "cantidad": None}])
a = AL.Articulos([{"cod_articulo": "1", "unid_pack": 0, "unid_caja": 12,
                   "codigos_barras": "999|12|0"}])
comprueba("sin codigo de cantidad 1, sin codigo de la unidad", a.get("1")["ean_unidad"], [])
comprueba("el pack a cero es que no esta", a.get("1")["unid_pack"], None)
comprueba("un maestro vacio cuenta como que no ha llegado", bool(AL.Articulos([])), False)

print("\nLas fotos")
jpg = b"\xff\xd8\xff\xe0resto"
f = AL.fotos([{"cod_articulo": "5322", "foto": base64.b64encode(jpg).decode()},
              # encode() de Postgres parte el base64 en lineas de 76
              {"cod_articulo": "7", "foto": base64.encodebytes(b"\x89PNG\r\n\x1a\n" + b"x" * 80).decode()},
              {"cod_articulo": "8", "foto": base64.b64encode(b"texto").decode()},
              {"cod_articulo": "../9", "foto": base64.b64encode(jpg).decode()},
              {"cod_articulo": "10", "foto": "esto no es base64!"}])
comprueba("jpeg y png, con saltos de linea", sorted(f), ["5322", "7"])
comprueba("con su tipo", (f["5322"][1], f["7"][1]), ("image/jpeg", "image/png"))

print("\nLa existencia: el ultimo movimiento por fecha")
ex = AL.Existencias()
ex.come([{"id": 9, "fecha": "2026-10-14 10:00:00", "almacen": "A", "cod_articulo": "1",
          "tipo_mov": "SV", "cantidad": -5, "existencia_resultante": -3},
         {"id": 2, "fecha": "2026-10-13 10:00:00", "almacen": "A", "cod_articulo": "1",
          "tipo_mov": "CO", "cantidad": 40, "existencia_resultante": 42},
         {"id": 1, "fecha": "2026-10-12 10:00:00", "almacen": "A", "cod_articulo": "1",
          "tipo_mov": "CO", "cantidad": 10, "existencia_resultante": 12},
         # una devolucion al proveedor no es una compra
         {"id": 10, "fecha": "2026-10-14 11:00:00", "almacen": "A", "cod_articulo": "1",
          "tipo_mov": "CO", "cantidad": -1, "existencia_resultante": -4}])
comprueba("el ultimo", ex.ultimo[("A", "1")][1], -4.0)
comprueba("la ultima compra, que no es la devolucion", ex.compra[("A", "1")][1], 40.0)
fi = AL.fichero(ex, {}, "2026-09", {"A": ""}, None, set(), datetime.date(2026, 10, 15))
p = fi["almacenes"][0]["productos"][0]
comprueba("negativa: bajo minimo, sin un porcentaje absurdo", (p["bajo"], p["pct"]), (True, None))
comprueba("sin maestro se avisa, y sin fotos tambien", len(fi["avisos"]), 2)
comprueba("y no se cuenta nadie «sin codigo»", "sin_codigo_unidad" in fi["total"], False)

print("\nQue almacenes ve cada perfil")
rutas = [{"almacen": "Sevilla", "delegacion": "Andalucia - Sevilla"}]
comprueba("el interno, todos", AL.almacenes_del_perfil({"Sevilla", "Otro"}, rutas, {})[0],
          {"Sevilla": "Andalucia - Sevilla", "Otro": ""})
comprueba("uno de delegacion, los suyos",
          AL.almacenes_del_perfil({"Sevilla", "Otro"}, rutas, {"delegaciones": ["Andalucia - Sevilla"]})[0],
          {"Sevilla": "Andalucia - Sevilla"})
comprueba("uno de cliente, ninguno, y lo dice",
          AL.almacenes_del_perfil({"Sevilla"}, rutas, {"clientes": ["AIRBUS"]})[0], None)

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("Los almacenes salen bien.")
