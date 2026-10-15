# 52 · Tarifas contra venta real

Lo pidió Gabriele el 14 de octubre de 2026: un cuadrado más en el informe general operativo
(`/operativo/`) con el **porcentaje de productos que cobran exactamente su tarifa**, y detrás una
página (`/tarifas/`) que baja de nacional a delegación, de delegación a centro y de centro a
producto, con un **Excel por centro** para el responsable de la delegación.

## Las reglas, como las fijó Gabriele

| | |
|---|---|
| **Qué se cuenta** | Cada producto de cada máquina. No las unidades vendidas. |
| **Qué productos** | Los repuestos en la máquina en los últimos seis meses (líneas `CM` con canal; el azúcar y los vasos de una caliente no son un producto con precio). Las recetas de café no se reponen: entran si se han vendido. |
| **Coincide** | El precio cobrado es **exactamente** el de la tarifa, medio de pago por medio de pago: efectivo, tarjeta privada (vale también su precio con descuento, `preciotpdto`) y tarjeta de crédito. Sin tolerancia. |
| **Qué venta** | La **última** cobrada en cada medio, posterior al último cambio de esa tarifa, y como mucho de hace seis meses. Por telemetría; si no hay, por el audit de la visita (importe entre ventas). |
| **Fuera del %** | Lo que no se puede controlar: sin tarifa (`sin_tarifa`) o sin venta electrónica desde el cambio (`sin_dato`). Se cuentan aparte y se dicen. |
| **Excel** | Uno por centro: resumen, precio distinto, sin tarifa (con tres columnas amarillas para que la delegación ponga el precio) y sin venta electrónica. |

El semáforo es el del informe operativo: verde por encima del 95 %, rojo por debajo del 75 %.

## Los niveles, y cuál manda

Hay **precios sueltos** por producto (o por categoría) puestos en un punto de venta, en un centro,
en un cliente o en un grupo de clientes, y hay **tarifas estándar**: las tablas con nombre del menú
*Gestión de Tarifas Vending Estándar* de VenCloud («AIRBUS OPERATIONS SLU», «ALHAMBRA PUBLICO»…,
`comercial.tarifasvending`), que se definen aparte y se asignan a un punto de venta o a un cliente.
Un precio que sale de una de esas tablas es de nivel **Estándar**, y se dice a quién está asignada.

El orden es el de VenCloud: su función `vending.getprecioscanal`, leída el 15-oct-2026 con la sonda
`EXT_SONDA_PRECIOS` (docs/17, M7Z). Busca así, y se queda con lo primero que encuentra:

| paso | dónde | nivel en la página |
|---|---|---|
| 1 | el punto de venta está marcado de **venta gratuita** (`pdvs.vtagratuita`): todo a 0 | Venta gratuita |
| 2 | la máquina tiene **precios en canales** (`maquinas.preciosencanales`): el precio de cada canal, sin mirar tarifas | Precio en la máquina |
| 3 | el precio suelto **del artículo**: punto de venta, centro, cliente, grupo | el sitio donde está |
| 4 | el precio suelto **de su categoría**: punto de venta, centro, cliente, grupo | el sitio donde está |
| 5 | la **tarifa estándar asignada al punto de venta** | Estándar |
| 6 | la **tarifa estándar asignada al cliente** | Estándar |
| — | nada de lo anterior: VenCloud pone 0 | Sin tarifa |

Tres cosas que no se ven en la pantalla de VenCloud y que salen de leer la función:

- **Toda la búsqueda por artículo va antes que cualquiera por categoría.** Un precio del artículo
  puesto en el cliente gana a uno de su categoría puesto en el punto de venta.
- **La tarifa estándar asignada al centro no se usa** (`clientescentros.tarifavendingid`). En el
  censo de octubre ninguna máquina la tiene, así que hoy no cambia nada; pero si alguien la
  asigna, VenCloud no la aplicará. Tampoco usa los precios de la ficha del centro ni del cliente
  (`clientescentrostarifas*`, `clientestarifasvending`) ni el precio suelto que no cuelga de nadie.
- El precio de la ficha del artículo y el de su categoría sólo valdrían con la tarifa global
  (`usatarifavendingglobal`), que en Serunion está **apagada**.

Una máquina con **planograma por categorías** sólo hace el paso 4, con la categoría puesta en el
canal y no la del artículo.

Los puntos de venta con **subvención en vigor** van marcados en el detalle y en el Excel: VenCloud
calcula aparte un precio subvencionado, y si la máquina cobra ése, ahí no coincidirá.

## De dónde sale cada cosa

| | |
|---|---|
| Precio de tarifa, venta gratuita, precios en canales | `EXT_TARIFAS` (docs/17, M7), maestro, cada noche → `maestros/tarifas/m_tarifas.json.gz` |
| Qué tarifa estándar tiene asignada cada sitio | `EXT_INSTALACIONES` (M5): `tarifa_vending_pdv` y `tarifa_vending_cliente` |
| Precio cobrado | telemetría (A12) y audit de la visita (A11) |
| Productos de la máquina | reposiciones (A2) |

## Por qué hay un estado que pasa de una noche a otra

Los agregados leen 120 días y aquí hacen falta seis meses. Leer 180 días de telemetría cada noche son
once millones de ventas. En vez de eso, `cabina/_tarifas/estado.json.gz` guarda lo único que hace
falta —la última carga de cada producto en cada máquina y el último precio cobrado en cada medio,
por fuente— y cada noche se le suma lo leído y se poda lo de más de seis meses. Guardar sólo el
último precio basta: la ventana empieza en una fecha y termina hoy, así que el último precio está
dentro o no hay ninguno.

Un relleno histórico de agregados (`{"desde": …, "hasta": …}`) también lo alimenta. Es como se
completan los seis meses la primera vez: la primera noche sólo trae 120 días.

## Lo que escribe la noche

- `cabina/<perfil>/tarifas/resumen.json.gz`: total, delegaciones y sus centros, con el nivel de las
  tarifas de cada centro.
- `cabina/<perfil>/tarifas/centros/<num_centro>.json.gz`: cada producto de cada máquina, con
  tarifa, último precio cobrado por medio, fecha, fuente y estado.
- `foto.tarifas` en `operativo.json`: lo que enseña el cuadrado.

La API (`/api/tarifas`, `/api/tarifas?centro=N`) sirve el del perfil de la sesión y un centro sólo
si su resumen de esa noche lo cita. El cuadrado va con la sesión de instalaciones, como la tarifa
que falta en ese bloque. El Excel se hace en el navegador (`app/comun/xlsx.js`), sin librerías de
fuera.

## Lo que se vio en el dato al montarlo

- Telemetría (`lineaprecio`): 1 tarjeta de crédito, 2 efectivo, 3 prepago (tarjeta privada) y un
  **11** en un 1 % de las ventas que no sabemos qué es: no se compara.
- Un 20 % de las ventas de telemetría llegan **sin artículo** (sólo la selección): no se pueden
  atribuir a un producto y no entran.
- En cinco días de octubre, 1.111 de 41.282 combinaciones máquina-artículo-medio cobraron más de un
  precio: cambios de precio a mitad de semana o precio de empleado. Por eso se compara el último.
