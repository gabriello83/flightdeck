#!/bin/sh
# Prepara los zips de las Lambdas. Pegar ficheros largos en el editor de la
# consola de AWS es poco fiable: con 400 lineas el navegador puede truncar el
# pegado y el error que sale luego (un error de sintaxis a mitad) no apunta a
# la causa. Con un zip no puede pasar.
#
#   sh infra/empaquetar.sh [carpeta de salida]
set -e
cd "$(dirname "$0")/.."
SALIDA="${1:-paquetes}"
mkdir -p "$SALIDA"
SALIDA="$(cd "$SALIDA" && pwd)"
TEMP="$(mktemp -d)"
trap 'rm -rf "$TEMP"' EXIT

# --- ingesta ---------------------------------------------------------------
# El handler de digivend-extraccion es index.lambda_handler, asi que dentro del
# zip el fichero tiene que llamarse index.py.
cp infra/lambda_extraccion.py "$TEMP/index.py"
(cd "$TEMP" && zip -q "$SALIDA/extraccion.zip" index.py)
rm "$TEMP/index.py"

# El de digivend-agregados apunta al modulo, asi que van con su nombre.
(cd infra && zip -q "$SALIDA/agregados.zip" lambda_agregados.py reglas.py)

# --- plataforma web --------------------------------------------------------
(cd infra/api && zip -q "$SALIDA/api.zip" comun.py autorizacion.py catalogo.py lambda_api.py)
(cd infra/api && zip -q "$SALIDA/alarmas.zip" comun.py autorizacion.py catalogo.py lambda_alarmas.py)

echo "Listos en $SALIDA:"
ls -la "$SALIDA"
echo
echo "El del asistente lleva el SDK de Anthropic y se hace aparte:"
echo "  mkdir -p paquete && pip install anthropic -t paquete/"
echo "  cp infra/api/comun.py infra/api/autorizacion.py infra/api/lambda_asistente.py paquete/"
echo "  (cd paquete && zip -r ../$SALIDA/asistente.zip .)"
