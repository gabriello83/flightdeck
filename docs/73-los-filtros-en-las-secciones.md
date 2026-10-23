# 73 · Los filtros de David en todas las secciones

> `app/comun/filtros.js` (`Filtros.cuatro`, `Filtros.fichas`, `Filtros.mesCentros`), las páginas de
> `app/` (rutas, incidencias, devoluciones, furgonetas, almacenes, tarifas, cifras, revisión,
> telemetría, utilizo y operativo), `infra/api/lambda_api.py` (`?fichas=1`) e
> `infra/api/autorizacion.py` (`fichas_operativo`).

Es la segunda mitad del correo de David (docs/72): *«En todas las ventanas añadiría los mismos filtros
(Área, Delegación, Cliente, Centro)… multiselección y que permita buscar»*.

## Un solo componente

`Filtros.cuatro(contenedor, opciones)` monta los cuatro botones encadenados de la portada en cualquier
página. Cada página le da sus delegaciones (con su área) y sus centros (con cliente y delegación), y le
pregunta:

- `pasaDeleg(delegacion)` y `pasaCentro(numero, delegacion)`: si una fila entra;
- `porCentro()`: si hay cliente o centro elegido (lo que necesita el reparto por centro);
- `texto()`: lo elegido, para el título, la miga y el nombre del Excel;
- `pon(campo, lista)` y `limpia()`: lo que hacen los cuadrados de área y «Todas las áreas».

Lo elegido va en la dirección igual que en la portada (`?area=Sur&cliente=…&centro=500088`), y los
cuadrados del informe general lo pasan a su sección: entrar en Rutas desde la portada con AIRBUS
elegido abre Rutas con AIRBUS elegido.

Las fichas de los centros (`{n, c, d}`) y las áreas salen del informe general:
`GET /api/operativo?fichas=1` devuelve solo `generado`, `zonas` y `centros` de la carpeta de la sesión.
Un perfil de cliente no tiene informe general y recibe 403; sus secciones montan los filtros con lo que
traen sus propios datos.

## La portada de áreas

Las secciones que tenían portada de áreas la conservan, pero ya no es un estado aparte: sale mientras
no hay nada elegido. Pulsar un área es elegirla en el filtro; «Todas las áreas» lo vacía. Así el filtro,
la miga y la dirección dicen siempre lo mismo.

## Qué hace cada sección con cliente y centro

| sección | área y delegación | cliente y centro |
|---|---|---|
| Rutas | sus datos del día | cifras del reparto por centro del mes; las tablas por ruta y por delegación dicen que no se reparten |
| Incidencias | sus filas | sus filas (cada incidencia trae cliente y centro) |
| Devoluciones | sus filas | sus filas |
| Furgonetas | sus vehículos | los vehículos que visitaron esos centros en la semana, del reparto por centro |
| Almacenes | sus almacenes | lo dice: el stock no es de ningún cliente |
| Tarifas | sus delegaciones | rehace el porcentaje con los centros que quedan |
| Puntos de venta, ventas y reposiciones | cuadros por delegación | cuadros por centro, de la foto o del mes por centro |
| Revisión clientes | sus máquinas | sus máquinas |
| Telemetría | sus máquinas | sus máquinas |
| Utilizo | lo dice: es lo que hace cada persona en VenCloud, en toda la red | ídem |

Lo que no tiene reparto por centro (los días de antes del 22 de octubre de 2026, una tabla por ruta) lo
dice, no enseña el total ni un cero.

## Pruebas

`prueba_pantallas.js` acepta `SOLO=<texto>` para correr solo los bloques cuyo título lo contiene. El
bloque «Los filtros en todas las secciones» abre cada sección, comprueba que están los filtros, que no
sale ninguna petición fuera del dominio y que no hay errores; con `FOTOS_FILTROS=<carpeta>` hace las
capturas en claro, oscuro y móvil.

## Despliegue

`api.zip` y `alarmas.zip` (llevan `autorizacion.py`; `asistente.zip` también lo lleva, pero no usa
`fichas_operativo` y no hace falta subirlo). Las páginas de las once secciones, `comun/filtros.js` y
`comun/areas.js` con `Cache-Control: no-cache`, y la invalidación. Sin cambios en las pilas ni en los
agregados. Orden: API primero, páginas después.
