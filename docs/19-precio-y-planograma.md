# Precio y planograma: tres fuentes, y cuál manda

Esta página recoge lo aprendido tras equivocarme dos veces seguidas leyendo el planograma de
Consum. Vale para cualquier análisis de planograma que hagamos.

## Las tres cifras de precio, y qué es cada una

| fuente | dónde | qué es |
|---|---|---|
| **Tarifa** | `comercial.tarifasvendingproductos` (por artículo) y `…categorias` (por categoría) | el precio que **debe** cobrarse. Es la referencia |
| **Canal** | `recursos.maquinascanales.precioef` / `preciotp` / `preciotc` | un valor **almacenado** en el planograma. Se rellena copiándolo de la tarifa al montarlo, y **puede quedarse viejo**. La pantalla de VenCloud no lo muestra |
| **Cobrado** | `telemetry.telemetrysales.precio`, o `vending.partesvisitaventas` en las máquinas sin telemetría | lo que la máquina cobró de verdad |

**La máquina debe cobrar el de la tarifa.** Puede no hacerlo, y la única forma de saberlo es
comparar contra la tercera columna: telemetría o audit de visita.

**No usar `maquinascanales.precioef` como «el precio de la máquina».** Comprobado en la
`18FE1536`: los 42 canales coinciden en artículo y capacidad con lo que enseña VenCloud, y 41 de
42 difieren en precio, siempre cinco céntimos por debajo. La pantalla muestra la tarifa; la
columna guarda un valor anterior.

## Dos trampas de lectura del planograma

**1 · `numero` no es el canal.** `maquinascanales.numero` es un ordinal correlativo (1, 2, 3…).
El canal que ve el reponedor y que muestra VenCloud es **`etiqueta`** (11, 12, 13, 21…). Toda
comparación con una exportación de VenCloud tiene que cruzarse por `etiqueta`.

**2 · Los canales inactivos no son huecos vacíos.** Cuando un canal es doble, ocupa dos
posiciones y la segunda queda inactiva: si el 11 es doble, el 12 existe en la tabla pero no
físicamente. En la `09SE3201`, los 13 canales «sin artículo» que detecté son exactamente los 13
inactivos. **Todo recuento de huecos, capacidad o surtido lleva `where c.activo is true`.**

## Dos carencias confirmadas

**El stock recomendado está a 0 en general**, no sólo en Consum. Sin `stockrecom` no hay
reposición sugerida ni se puede medir rotura de stock, porque no hay contra qué comparar lo que
queda en la visita. Es un campo que se puede cargar de forma masiva y que desbloquearía un
indicador entero.

**Hay artículos activos sin tarifa, y por eso salen a 0 €.** En la `09SE3201` son cuatro canales
activos con producto y precio cero: OREO 41G bañadas blanco, Ñaming Go! jamón cremoso y dos de LM
croissant serrano y queso. Los cuatro están entre las 23 referencias que no aparecen en la tarifa
de Consum. El caso mayor es el agua Lanjarón: 237 canales en 26 máquinas, sin tarifa.

La cadena es: **sin tarifa → nada que copiar → canal a cero → producto que no cobra.**

## El control que sale de aquí

Comparar, por máquina y artículo, **tarifa contra precio cobrado**. Donde hay telemetría, con
`telemetrysales`; donde no, con `partesvisitaventas`, que trae importe y número de ventas por
artículo y permite deducir el precio unitario.

Es una alarma de cabina, no un informe puntual: cada máquina que cobre distinto de su tarifa
debería aparecer sola, con la diferencia y las unidades afectadas.

Para Consum tiene una pega: 54 de sus 58 máquinas no tienen telemetría, así que su única vía es
el audit de visita. Queda por comprobar si esas máquinas generan audit.
