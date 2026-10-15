# 54 · Los almacenes por dentro

Lo pidió Gabriele el 15 de octubre de 2026, en dos mensajes:

> En la parte de almacenes poner la parte que los productos tengan fotos. Cada producto tiene
> tener la información de cuánto van por packs. Los productos donde no hay el código de barra
> por la unidad.

> En los almacenes hay que tener por cada almacén cuando una cantidad está abajo del 15
> porciento de la cantidad del último pedido.

Hasta ahora el cuadrado de almacenes del informe operativo (docs/51) daba el valor del último
cierre y no llevaba a ninguna parte. Ahora lleva a `/almacenes/`: cada almacén con sus
productos, su foto, sus unidades por pack y por caja, su código de barras de la unidad y lo que
le queda frente a lo que se compró la última vez.

## De dónde sale cada cosa

| Qué | De dónde | ¿Se bajaba ya? |
|---|---|---|
| Existencia de hoy | el último movimiento de cada producto en cada almacén (C1, `diarmovalm.existen`) | sí |
| … si no se ha movido en 120 días | el detalle del último cierre (C10) | sí, pero no se usaba |
| Última compra | el último movimiento CO (entrada por albarán de compra), en unidades | sí |
| Unidades por pack y por caja | `stocks.articulos.unidpack` / `unidcaja` | **no: M8** |
| Códigos de barras | `stocks.articuloscodequivalentes` (código y cantidad que representa) | **no: M8** |
| Foto | `stocks.articulosfotos` (miniatura), por `articulos.articulofotoid` | **no: M9** |

**La existencia es la de VenCloud, no una suma nuestra.** Cada movimiento trae la existencia
que deja. Ordenados por fecha, la cadena cuadra en el 95 % de los pasos de septiembre
(62.867 de 66.016), y lo que no cuadra son sobre todo inventarios (IN), que fijan la cantidad
en vez de sumarle. Con el cierre de septiembre coincide en dos de cada tres productos; lo más
probable (no comprobado) es que el resto sea porque el cierre se hace a una hora y los
movimientos de ese día siguen, y porque falta el día 15 de septiembre en el crudo. Manda lo
más reciente: el último movimiento, o el cierre si es posterior.

**«Último pedido» es la última compra recibida**: la entrada por albarán de compra
(«Albarán de compra: 1537710210», «Proveedor: BIMBO»). Es lo que llegó al almacén, en las
mismas unidades que la existencia. El pedido de compra en sí (`compras.pedidoscpa`) no se baja;
si hiciera falta el pedido y no la entrada, es un informe más.

**Bajo mínimo**: existencia por debajo del 15 % de esa última compra (`UMBRAL` en
`infra/almacenes.py`). Un producto sin compra en la ventana no tiene porcentaje y se dice. Una
existencia negativa es un descuadre de VenCloud: cuenta como bajo mínimo, sin porcentaje.

**El código de la unidad es el de cantidad 1.** Es lo que se deduce del modelo
(`articuloscodequivalentes.cantidad` = cuántas unidades representa el código). M8 trae el dato
en bruto (`código|cantidad|tipo`) para comprobarlo con el primer volcado. Mientras M8 no exista,
la página lo dice arriba y no enseña a nadie «sin código».

## Lo que salió con el dato real

Con los movimientos de septiembre y el cierre de septiembre: 30 almacenes con producto, 3.063
productos-almacén, 442 artículos distintos en los cierres, y 230 por debajo del 15 % de su
última compra. Casi la mitad de los productos no tiene una compra en septiembre; con la ventana
de 120 días serán menos.

Hay almacenes que el maestro de rutas no sitúa en ninguna delegación (Cornellà, Bilbao,
Málaga, Granada…). El interno los ve; un perfil por delegaciones no, como ya pasaba con el
cuadrado. El SQL de un maestro de almacenes con su delegación ya está escrito (M3, docs/17).

## Quién ve qué

Lo mismo que el cuadrado: dirección y administración (los almacenes son nuestro stock).
`/api/almacenes` sirve `cabina/<perfil>/almacenes.json.gz`, y `/api/almacenes/foto?art=` la foto
de un producto **solo si el fichero de ese perfil lo cita con foto**. Las fotos se guardan una
vez para todos en `cabina/_articulos/fotos/<código>`, y solo se reescriben si cambian.

## Para ponerlo en marcha

1. En VenCloud, crear los dos informes nuevos con el SQL de docs/17: **M8 ·
   EXT_MAESTRO_ARTICULOS** y **M9 · EXT_MAESTRO_ARTICULOS_FOTOS**, los dos sin parámetros.
   Apuntar el número que les dé VenCloud.
2. Con esos números se añaden al manifiesto (`maestros/articulos`, `maestros/articulos_fotos`) y
   se sube `config/manifiesto.json` al bucket de DATOS. Sin números no se pueden poner: la
   extracción se niega a arrancar con un informe sin número.
3. Subir `agregados.zip` y `api.zip`, y a la web `almacenes/index.html` y
   `operativo/index.html` (con `--cache-control no-cache`).

Sin los pasos 1 y 2 la página ya funciona: existencias, última compra y bajo mínimo salen de lo
que ya se baja, y arriba dice que faltan los dos informes.
