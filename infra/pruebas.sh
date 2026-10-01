#!/bin/sh
# Las seis baterias. Sin AWS, sin red, sin instalar nada.
#   sh infra/pruebas.sh
set -e
cd "$(dirname "$0")/.."
for t in infra/test_manifiesto.py infra/test_reglas.py infra/test_agregados.py \
         infra/api/test_autorizacion.py infra/api/test_api.py \
         infra/api/test_alarmas.py infra/api/test_asistente.py; do
  printf '%-34s ' "$t"
  if python3 "$t" >/dev/null 2>&1; then echo "pasa"; else echo "FALLA"; python3 "$t"; exit 1; fi
done
echo "Todo pasa."
