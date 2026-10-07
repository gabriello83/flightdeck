#!/bin/sh
# Todas las baterias. Sin AWS, sin red, sin instalar nada.
#   sh infra/pruebas.sh
set -e
cd "$(dirname "$0")/.."
for t in infra/test_manifiesto.py infra/test_extraccion.py infra/test_reglas.py infra/test_agregados.py infra/test_cuadro.py infra/test_serie.py \
         infra/test_permisos.py infra/test_sql.py infra/test_airbus_tarifa.py infra/test_paquetes.py \
         infra/api/test_autorizacion.py infra/api/test_api.py \
         infra/api/test_alarmas.py infra/api/test_asistente.py; do
  printf '%-34s ' "$t"
  if python3 "$t" >/dev/null 2>&1; then echo "pasa"; else echo "FALLA"; python3 "$t"; exit 1; fi
done
# Las tres pantallas, abiertas de verdad en un navegador. Necesita node y
# playwright (npm install), asi que si no estan se dice y se sigue: lo demas no
# depende de ellas.
printf '%-34s ' "app/comun/prueba_pantallas.js"
if [ -d node_modules/playwright ]; then
  if node app/comun/prueba_pantallas.js >/dev/null 2>&1; then echo "pasa"
  else echo "FALLA"; node app/comun/prueba_pantallas.js; exit 1; fi
else
  echo "saltada (npm install para probar las pantallas)"
fi
echo "Todo pasa."
