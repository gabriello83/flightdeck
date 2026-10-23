# 72 · La portada que pidió David y los filtros con buscador

> `app/operativo/`, `app/comun/filtros.js`, `infra/operativo.py` (`por_centro`, `centros_por_mes`,
> `fichas_de_centros`), `infra/lambda_agregados.py` (`escribe_operativo`), `infra/api/lambda_api.py`
> (`operativo_centros`) e `infra/api/autorizacion.py` (`recorta_operativo_centros`).

David Alonso escribió a Gabriele el 22 de octubre de 2026 («Cuadro Mando Vending»), con una captura de
cómo quería la portada del informe general:

> *Si un KPI es correcto estaría en gris, si está regular amarillo y mal es rojo. En la caja de ventas
> se quedaría del color que tienes, pero añadiría dos cálculos (precio medio unidad vendida y venta
> media de máquina). La cajita de PREFERIDOS la llevaría a la parte superior junto con el botón «Panel
> completo», «Preguntar»… Añadiría en esta página los filtros de Cliente y Centro (multiselección).*
>
> *En todas las ventanas añadiría los mismos filtros (Área, Delegación, Cliente, Centro). En todos los
> filtros pondría que fuera multiselección y que permita buscar: comenzar a escribir y que encuentre
> todo lo que contenga lo que escribo.*

## La portada

- **Colores.** Los cuadrados con porcentaje (rutas, incidencias, telemetría, tarifas) van en **gris**
  si están en objetivo (más del 95 %), en **amarillo** entre el 75 y el 95 % y en **rojo** por debajo.
  Los demás van en gris; **Ventas**, en su morado. Antes cada cuadrado sin semáforo tenía su color, y
  el verde de «bien» competía con el rojo por la vista: ahora lo único que destaca es lo que falla.
- **Orden**, el de la captura: Ventas, Rutas, Incidencias, Telemetría · Tarifas, Devoluciones,
  Revisión clientes, Puntos de venta · Reposiciones, Furgonetas, Almacenes, Utilizo. La página ordena
  lo que le llega; un cuadrado nuevo que no esté en la lista va al final.
- **Ventas** lleva dos cifras más, debajo del importe: el **precio medio de la unidad vendida**
  (importe ÷ unidades) y la **venta media por máquina** (importe ÷ máquinas con venta). En varios días
  es **por máquina y día**: las máquinas de cada día no se pueden sumar entre sí (serían la misma
  muchas veces), pero sí las máquinas-día.
- **Preferidos** deja de ser un cuadrado: es un botón arriba, entre «Panel completo» y «Preguntar»,
  con cuántas tablas tiene marcadas.

## Los filtros

Cuatro, encadenados: **Área**, **Delegación**, **Cliente** y **Centro**. El área deja en la lista sus
delegaciones; las delegaciones, sus clientes; los clientes, sus centros. Cada uno sale solo si hay más
de una cosa que elegir.

Todos son el mismo componente, `app/comun/filtros.js`, pensado para llevarlo a las demás secciones:
un botón con lo elegido; al pulsarlo, un buscador y la lista con casillas. El buscador encuentra lo
que **contiene** lo escrito, sin mirar mayúsculas ni acentos («leg» da «Madrid - Leganes»); con una
sola coincidencia, Enter la marca. «Marcar los que salen» marca lo que el buscador deja a la vista.
Nada marcado es «todos». Con miles de centros la lista enseña 300 y pide afinar.

Lo elegido va en la dirección, repetido: `?area=Sur&area=Norte&cliente=…&centro=500088`.

## El reparto por centro

Área y delegación se suman con el `por_delegacion` de cada día (docs/66). Cliente y centro necesitan
el día partido por centro, y eso no cabe en el fichero del informe: son miles de centros por día y el
fichero lleva toda la historia. Así que la noche escribe, al lado, **un fichero por mes**:

`cabina/<perfil>/operativo/centros-AAAA-MM.json.gz` → `{"mes", "dias": {fecha: {cuadrado: {centro: [...]}}}}`

En listas, para que pese poco:

| cuadrado | lista por centro |
|---|---|
| rutas | previstas, hechas, fuera del plan, visitas |
| incidencias (`averias`) | cerradas, a tiempo |
| furgonetas | visitas, visitas sin vehículo, matrículas |
| ventas | importe, unidades, máquinas |
| reposiciones | unidades, carriles de café, {clase: unidades} |
| telemetría | auditables, con lectura |

El centro es la misma clave con que la serie parte la venta (`MapaCentros.clave_centro`: el número de
centro y, si la fila no lo trae, el de su máquina). La suma de todos los centros da la cifra del día,
salvo lo que no tiene centro (clave vacía), que cuenta en el total y en ningún centro.

El fichero del informe lleva además:

- **`centros`**: la ficha de cada centro, `{"n": nombre, "c": cliente, "d": delegación}`. Es lo que
  llena las listas de Cliente y Centro. Las de antes se quedan: un centro que ya no aparece sigue en los
  días viejos.
- **`meses_centros`**: los meses que tienen su fichero.
- En la foto, **`pdvs.por_centro`**: puntos de venta activos y máquinas de cada centro.

La página solo pide un mes (`GET /api/operativo?centros=AAAA-MM`) cuando se filtra por cliente o
centro, y solo los meses del rango elegido. La API lo busca dentro de la carpeta de la sesión, como el
resto: no hay con qué pedir el de otro perfil. El mes tiene que ser `AAAA-MM`; se recorta con la misma
tijera que el informe (solo los cuadrados que el perfil ve).

**Lo que no se reparte se dice.** Con cliente o centro, devoluciones, tarifas, revisión, utilizo y
almacenes dicen que no se reparten por cliente ni centro, en vez de enseñar el total. Los días de antes
de la primera noche con este cambio no tienen reparto por centro y lo dicen. El relleno histórico
(docs/66) también escribe los meses por centro de su tramo, y no pisa la telemetría ni las incidencias
de un día que ya escribió la noche.

## Despliegue

`agregados.zip`, `api.zip` y `alarmas.zip` (llevan `autorizacion.py`), y la página `operativo/` y
`comun/filtros.js` con `Cache-Control: no-cache`, más la invalidación. Sin cambios en las pilas: la
API y los agregados ya leen y escriben en `cabina/`. Orden: API, agregados (y lanzarlos), páginas.
Hasta que corran los agregados, Cliente y Centro no salen (no hay fichas) y la portada funciona con
Área y Delegación.

## Lo que queda

~~Llevar el mismo filtro a las demás secciones.~~ Hecho en docs/73: las once secciones llevan los
cuatro filtros, y los cuadrados de esta portada pasan lo elegido a su sección.
