"""
Que los zips de `paquetes/` sean los del codigo de ahora.

Estan en el repositorio para que se puedan descargar sin tener que construirlos,
y eso tiene un peligro evidente: que alguien cambie una Lambda, no vuelva a
empaquetar, y se suba a AWS un zip viejo. El sintoma seria de los malos —el
codigo del repositorio dice una cosa y lo que corre hace otra—, asi que esto lo
convierte en un fallo de las pruebas.

Compara CONTENIDOS, no bytes: un zip guarda la fecha de cada fichero, asi que
dos zips del mismo codigo nunca son iguales byte a byte.

    python3 infra/test_paquetes.py
"""

import io
import os
import sys
import zipfile
import zlib

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
PAQUETES = os.path.join(RAIZ, "paquetes")

# zip -> {nombre dentro del zip: fichero del repositorio}
ESPERADO = {
    # El handler de digivend-extraccion es index.lambda_handler, asi que dentro
    # del zip el fichero tiene que llamarse index.py.
    "extraccion.zip": {"index.py": "infra/lambda_extraccion.py"},
    "agregados.zip": {"lambda_agregados.py": "infra/lambda_agregados.py",
                      "reglas.py": "infra/reglas.py"},
    "api.zip": {"comun.py": "infra/api/comun.py",
                "autorizacion.py": "infra/api/autorizacion.py",
                "catalogo.py": "infra/api/catalogo.py",
                "lambda_api.py": "infra/api/lambda_api.py"},
    "alarmas.zip": {"comun.py": "infra/api/comun.py",
                    "autorizacion.py": "infra/api/autorizacion.py",
                    "catalogo.py": "infra/api/catalogo.py",
                    "lambda_alarmas.py": "infra/api/lambda_alarmas.py"},
}

fallos = []


def comprueba(que, ok, detalle=""):
    print(f"  {'ok   ' if ok else 'FALLO'} {que}{'' if ok else ' · ' + detalle}")
    if not ok:
        fallos.append(que)


def crc(ruta):
    with io.open(os.path.join(RAIZ, ruta), "rb") as f:
        return zlib.crc32(f.read()) & 0xFFFFFFFF


print("Los zips de paquetes/ son los del codigo de ahora\n")
for nombre, contenido in ESPERADO.items():
    ruta = os.path.join(PAQUETES, nombre)
    if not os.path.exists(ruta):
        comprueba(nombre, False, "no esta. Lanza: sh infra/empaquetar.sh")
        continue
    with zipfile.ZipFile(ruta) as z:
        dentro = {i.filename: i.CRC for i in z.infolist()}
    comprueba(f"{nombre}: lleva lo que tiene que llevar",
              sorted(dentro) == sorted(contenido),
              f"lleva {sorted(dentro)} y esperaba {sorted(contenido)}")
    for en_zip, fuente in contenido.items():
        if en_zip not in dentro:
            continue
        comprueba(f"{nombre}: {en_zip} esta al dia",
                  dentro[en_zip] == crc(fuente),
                  f"el zip no coincide con {fuente}. Lanza: sh infra/empaquetar.sh")

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos[:4])}"
          + (" ..." if len(fallos) > 4 else ""))
    sys.exit(1)
print("Los paquetes estan al dia.")
