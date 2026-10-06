# Paquetes listos para subir a AWS

Los zips de las Lambdas, construidos y versionados aquí para poder **descargarlos
directamente**, sin clonar nada ni ejecutar un script.

| Lambda de AWS | Fichero |
|---|---|
| `digivend-extraccion` | `extraccion.zip` |
| `digivend-agregados` | `agregados.zip` |
| `digivend-api` | `api.zip` |
| `digivend-alarmas` | `alarmas.zip` |

En GitHub se descargan con el botón **Download raw file** de cada uno, o desde la
dirección `.../raw/<rama>/paquetes/<fichero>.zip`.

Luego, en AWS: `Lambda → la función → pestaña Code → Upload from → .zip file`.

## El del asistente va aparte

`asistente.zip` no está aquí porque pesa unos megas: lleva dentro el SDK de
Anthropic. Se construye cuando haga falta:

```sh
mkdir -p paquete && pip install anthropic -t paquete/
cp infra/api/comun.py infra/api/autorizacion.py infra/api/lambda_asistente.py paquete/
(cd paquete && zip -r ../paquetes/asistente.zip .)
```

## Que no se queden viejos

Un zip versionado tiene un peligro evidente: que alguien cambie una Lambda, no
vuelva a empaquetar, y acabe subiéndose a AWS código viejo. El síntoma sería de
los malos —el repositorio dice una cosa y lo que corre hace otra—, así que es un
fallo de las pruebas: `infra/test_paquetes.py` compara el contenido de cada zip
con el de los ficheros de los que sale, y falla si no coinciden.

Después de tocar cualquier Lambda:

```sh
sh infra/empaquetar.sh      # reconstruye paquetes/
sh infra/pruebas.sh         # y comprueba que todo cuadra
```
