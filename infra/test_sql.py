"""
Que el SQL de los informes se sostenga antes de pegarlo en VenCloud.

Esta prueba existe porque el fallo ya pasó: al añadir `cli.codigo` y `cli.nombre`
a EXT_SAT_AVERIAS se quedó sin su `left join comercial.clientes cli`. Postgres lo
habría rechazado con «missing FROM-clause entry for table cli», pero eso se
descubre pegando la consulta en VenCloud, no aquí.

No es un analizador de SQL: es la comprobación barata que caza ese error, que es
el que se comete de verdad al editar un select de setenta columnas.

  1. Todo alias que se usa (`cli.nombre`) está definido en un `from`, un `join` o
     como alias de una subconsulta.
  2. Los informes con fechas llevan sus dos parámetros, {0} y {1}.
  3. Ningún informe se ha quedado sin `from`.

    python3 infra/test_sql.py
"""

import io
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(AQUI, "..", "docs", "17-sql-extraccion-completa.md")

# `from x.y z` y `join x.y z`, con o sin `as`
RE_ALIAS = re.compile(r"(?:from|join)\s+[\w.]+\s+(?:as\s+)?(\w+)", re.I)
# el alias de una subconsulta: `) inv on ...` o `) inv\n`
RE_SUB = re.compile(r"\)\s*(\w+)\s*(?:on\b|\n|$)", re.I)
RE_ESQUEMA = re.compile(r"(?:from|join)\s+(\w+)\.", re.I)
RE_USO = re.compile(r"\b(\w+)\.\w+")
RE_BLOQUE = re.compile(r"## ([A-Z0-9]+) · (EXT_[A-Z_0-9]+)(.*?)\n```sql\n(.*?)\n```", re.S)

# Palabras que llevan punto y no son un alias.
NO_ALIAS = {"cast", "count", "coalesce", "sum", "min", "max", "avg", "extract"}

fallos = []


def comprueba(que, ok, detalle=""):
    print(f"  {'ok   ' if ok else 'FALLO'} {que}{'' if ok else ' · ' + detalle}")
    if not ok:
        fallos.append(que)


texto = io.open(DOC, encoding="utf-8").read()
bloques = RE_BLOQUE.findall(texto)
print(f"{len(bloques)} informes en docs/17\n")
comprueba("hay informes que revisar", len(bloques) > 30, f"solo {len(bloques)}")

print("\nTodo alias que se usa esta definido")
for cod, nombre, cabecera, sql in bloques:
    definidos = set(RE_ALIAS.findall(sql)) | set(RE_SUB.findall(sql)) | set(RE_ESQUEMA.findall(sql))
    usados = {a for a in RE_USO.findall(sql) if a not in NO_ALIAS}
    faltan = sorted(usados - definidos)
    comprueba(f"{cod} {nombre}", not faltan,
              f"usa {faltan} y no hay join ni subconsulta que lo defina")

print("\nLos informes con fechas llevan sus dos parametros")
for cod, nombre, cabecera, sql in bloques:
    if "sin parámetros" in cabecera or "sin parametros" in cabecera:
        comprueba(f"{cod} {nombre}: sin parametros, y no los usa",
                  "{0}" not in sql and "{1}" not in sql,
                  "dice que no lleva parametros pero el SQL los usa")
    elif "{0}" in sql or "{1}" in sql:
        comprueba(f"{cod} {nombre}: lleva {{0}} y {{1}}",
                  "{0}" in sql and "{1}" in sql,
                  "lleva uno de los dos y no el otro")

print("\nNingun informe se ha quedado sin from")
for cod, nombre, cabecera, sql in bloques:
    comprueba(f"{cod} {nombre}", re.search(r"\bfrom\b", sql, re.I) is not None, "sin from")

print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos[:6])}"
          + (" ..." if len(fallos) > 6 else ""))
    sys.exit(1)
print("El SQL de los informes se sostiene.")
