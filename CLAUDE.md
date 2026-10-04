# Flightdeck · digivend

Plataforma de operaciones de vending de Serunion, alimentada desde VenCloud.
`docs/` lleva el relato completo, numerado; `infra/PASOS.md` es el despliegue
paso a paso.

## Cómo se escribe aquí

**Código entero, nunca fragmentos.** Cuando se entregue un SQL, una plantilla,
un fichero de configuración o cualquier cosa que haya que pegar en otro sitio,
va **completo y listo para copiar y pegar**, aunque sólo cambien dos líneas. Un
fragmento obliga a quien lo recibe a hacer el empalme, y ahí es donde se pierde
el tiempo y donde entran los errores. (Pasó con `EXT_SAT_AVERIAS`: se dieron las
dos columnas nuevas sin su `join`, y el SQL no se sostenía.)

Lo mismo con los pasos de la consola de AWS: el camino entero, con el nombre
exacto de cada botón, no "ya sabes dónde".

## Lo que no se negocia

- **Un solo origen.** La web se sirve en `dashboard.digivend.es` y no llama a
  ningún otro dominio: hay redes de cliente que cortan las páginas que lo hacen.
  Nada de CDN, de tipografías externas ni de SDK en el navegador. Lo que haya que
  hablar con fuera (VenCloud, la API de Claude, WhatsApp) lo habla una Lambda.
- **Lo de AWS va aparte.** Dos pilas, `digivend-ingesta` y `digivend-web`, con su
  frontera de permisos, sus nombres propios y sus etiquetas de coste. No se
  adopta ni se toca nada que ya estuviera en la cuenta.
- **El ámbito se aplica al escribir, no al leer.** La Lambda de agregados escribe
  un panel por perfil; la API sirve el del perfil de la sesión. No hay ningún
  parámetro con el que pedir el de otro.
- **Si un dato no está, se dice.** Nunca se estima, ni se rellena, ni se enseña
  un cero que no es un cero.

## Antes de dar nada por bueno

```sh
sh infra/pruebas.sh        # las diez baterias, sin AWS, sin red
sh infra/empaquetar.sh     # los zips de las Lambdas
```

Las pruebas no son decorado: varias existen porque el fallo ya pasó en
producción. `test_permisos.py` lee la plantilla y el código y comprueba que cada
Lambda pueda hacer lo que hace; `test_sql.py` revisa los informes de VenCloud;
`test_agregados.py` fija que trocear da lo mismo que sumar de golpe.

Una página nueva se comprueba en Chromium —claro, oscuro y móvil— y se mira que
no haya una sola petición fuera del dominio.
