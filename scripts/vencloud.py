#!/usr/bin/env python3
"""Cliente de la API externa de VenCloud (WebReports).

La API publica informes numerados. Todo va en la ruta, no en el cuerpo ni en la
query, y la llamada es un POST:

    {endpoint}/GetReportV2/{token}/{empresa}/{informe}[|filtro1|filtro2...]

Devuelve un JSON cuya forma depende del informe.

El token no se guarda en el repositorio; se lee del entorno:

    export VENCLOUD_TOKEN=xxxxxxxx
    export VENCLOUD_EMPRESA=2311

Uso:
    python3 scripts/vencloud.py informe 1                      # un informe
    python3 scripts/vencloud.py informe 12 2026-05-01 2026-05-31   # con filtros
    python3 scripts/vencloud.py catalogo 1 40                  # que hay en cada numero

Solo usa la biblioteca estandar, para poder ejecutarlo en cualquier maquina sin
instalar nada.
"""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINT = os.environ.get(
    "VENCLOUD_ENDPOINT",
    "https://vencloudpro.eac.es/2311_api/webservices//VenCloudExternalApi/VenCloudExternalApi.svc",
)
SALIDA = Path(__file__).resolve().parent.parent / "data" / "vencloud"
ESPERA_ENTRE_LLAMADAS = 1.0  # segundos; no sabemos el limite de la API, vamos despacio


def credenciales():
    token = os.environ.get("VENCLOUD_TOKEN")
    empresa = os.environ.get("VENCLOUD_EMPRESA", "2311")
    if not token:
        sys.exit("Falta VENCLOUD_TOKEN en el entorno. Ver .env.example")
    return token, empresa


def sin_token(texto, token):
    """Nunca escribimos el token en pantalla ni en los ficheros de salida."""
    return texto.replace(token, "TOKEN")


def llamar(informe, filtros=(), timeout=120, reintentos=3):
    """Devuelve (codigo_http, cuerpo_texto, json_o_None, url_sin_token)."""
    token, empresa = credenciales()
    # El informe y sus filtros son un unico segmento separado por '|'.
    segmento = "|".join([str(informe), *(str(f) for f in filtros)])
    # Por defecto se codifica la barra vertical (%7C). Algunos IIS rechazan la
    # barra cruda en la ruta y otros rechazan justo lo contrario, asi que se
    # puede forzar el envio literal con VENCLOUD_FILTRO_CRUDO=1.
    if os.environ.get("VENCLOUD_FILTRO_CRUDO") == "1":
        ruta = urllib.parse.quote(segmento, safe="|")
    else:
        ruta = urllib.parse.quote(segmento, safe="")
    url = f"{ENDPOINT}/GetReportV2/{token}/{empresa}/{ruta}"
    publica = sin_token(url, token)

    contexto = ssl.create_default_context()
    if os.environ.get("VENCLOUD_CA_BUNDLE"):
        contexto.load_verify_locations(os.environ["VENCLOUD_CA_BUNDLE"])

    espera = 2
    for intento in range(1, reintentos + 1):
        peticion = urllib.request.Request(url, method="POST", data=b"",
                                          headers={"Accept": "application/json",
                                                   "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(peticion, timeout=timeout, context=contexto) as r:
                cuerpo = r.read().decode("utf-8", "replace")
                codigo = r.status
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", "replace")
            codigo = e.code
        except Exception as e:  # red, DNS, TLS, timeout
            if intento == reintentos:
                return 0, f"{type(e).__name__}: {sin_token(str(e), token)}", None, publica
            time.sleep(espera)
            espera *= 2
            continue

        try:
            datos = json.loads(cuerpo)
        except json.JSONDecodeError:
            datos = None
        # Un 5xx puede ser transitorio; un 4xx no se reintenta.
        if codigo >= 500 and intento < reintentos:
            time.sleep(espera)
            espera *= 2
            continue
        return codigo, sin_token(cuerpo, token), datos, publica
    return 0, "sin respuesta", None, publica


def filas_de(datos):
    """Localiza la lista de registros dentro de la respuesta, venga como venga."""
    if isinstance(datos, list):
        return datos
    if isinstance(datos, dict):
        # Muchos servicios .NET envuelven el resultado en GetReportV2Result, d, Data...
        for clave in ("GetReportV2Result", "d", "Data", "data", "Result", "result",
                      "Rows", "rows", "Table", "Items", "items"):
            if clave in datos:
                interior = datos[clave]
                if isinstance(interior, str):
                    try:
                        interior = json.loads(interior)
                    except json.JSONDecodeError:
                        return []
                return filas_de(interior)
        for valor in datos.values():
            if isinstance(valor, list) and valor and isinstance(valor[0], dict):
                return valor
    return []


def resumen(datos):
    filas = filas_de(datos)
    if not filas:
        return {"filas": 0, "columnas": [], "muestra": None}
    primera = filas[0]
    columnas = list(primera.keys()) if isinstance(primera, dict) else []
    return {"filas": len(filas), "columnas": columnas, "muestra": primera}


def guardar(nombre, contenido):
    SALIDA.mkdir(parents=True, exist_ok=True)
    destino = SALIDA / nombre
    destino.write_text(contenido, encoding="utf-8")
    return destino


def cmd_informe(args):
    if not args:
        sys.exit("Uso: vencloud.py informe <numero> [filtro ...]")
    informe, filtros = args[0], args[1:]
    codigo, cuerpo, datos, url = llamar(informe, filtros)
    print(f"POST {url}")
    print(f"HTTP {codigo} · {len(cuerpo):,} bytes")
    if datos is None:
        print("La respuesta no es JSON. Primeros 600 caracteres:\n")
        print(cuerpo[:600])
        return 1
    r = resumen(datos)
    print(f"filas: {r['filas']}")
    if r["columnas"]:
        print(f"columnas ({len(r['columnas'])}): {', '.join(r['columnas'])}")
    if r["muestra"]:
        print("primer registro:")
        print(json.dumps(r["muestra"], ensure_ascii=False, indent=2)[:1200])
    sufijo = "_".join(str(f) for f in filtros)
    destino = guardar(f"informe_{informe}{'_' + sufijo if sufijo else ''}.json", cuerpo)
    print(f"\nrespuesta completa en {destino}")
    return 0


def cmd_catalogo(args):
    """Recorre un rango de numeros de informe y apunta que devuelve cada uno."""
    desde = int(args[0]) if args else 1
    hasta = int(args[1]) if len(args) > 1 else 40
    catalogo = {}
    for n in range(desde, hasta + 1):
        codigo, cuerpo, datos, _ = llamar(n, timeout=90, reintentos=2)
        r = resumen(datos) if datos is not None else {"filas": 0, "columnas": [], "muestra": None}
        catalogo[n] = {"http": codigo, "bytes": len(cuerpo), "filas": r["filas"],
                       "columnas": r["columnas"],
                       "error": None if datos is not None else cuerpo[:200]}
        marca = f"{r['filas']:>7} filas" if r["filas"] else "        -"
        print(f"  informe {n:>3}  HTTP {codigo:<3} {marca}  "
              f"{', '.join(r['columnas'][:6])}{'...' if len(r['columnas']) > 6 else ''}")
        time.sleep(ESPERA_ENTRE_LLAMADAS)
    destino = guardar("catalogo.json", json.dumps(catalogo, ensure_ascii=False, indent=2))
    print(f"\ncatalogo en {destino}")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    orden, args = sys.argv[1], sys.argv[2:]
    if orden == "informe":
        return cmd_informe(args)
    if orden == "catalogo":
        return cmd_catalogo(args)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
