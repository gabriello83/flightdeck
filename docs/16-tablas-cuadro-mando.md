# Las tablas que hacen falta, área por área

Todo lo de aquí sale del volcado de `information_schema`, no de suposiciones: cada tabla existe
y las columnas citadas son las reales.

## Lo primero: `vending.partesvisita` es la columna vertebral

Antes del listado conviene ver esto, porque cambia el orden de trabajo. **La visita del reponedor
es el hecho central del sistema.** Tiene 137 columnas propias y de ella cuelgan, con
`partevisitaid`, casi todo lo demás:

| tabla hija | qué registra | área a la que sirve |
|---|---|---|
| `partesvisitareposiciones` | qué se cargó en cada canal | Almacenes, Inventarios |
| `partesvisitarecinventarios` | inventario de la máquina en la visita | Inventarios máquinas |
| `partesvisitainvcanales` / `partesvisitainvhuecos` | inventario canal a canal | Inventarios máquinas |
| `partesvisitacontajes` + `…detalle` | el arqueo: monedas y billetes contados | Recaudación |
| `partesvisitaauditmonbil` / `partesvisitaaudittubos` | dinero dentro de la máquina | Recaudación, Bolsa |
| `partesvisitaauditcashlessgroups` + `…detalles` | ventas y recargas sin efectivo | Datos electrónico |
| `partesvisitadevolclientes` | devoluciones a clientes, con DNI y firma | Devoluciones |
| `partesvisitaincidencias` | caducado, rotura, robo por canal | Averías, Almacenes |
| `partesvisitaventas` | venta por artículo con coste y beneficio | Venta |
| `partesvisitacontadores` | contadores de la máquina | Recaudación |
| `partesvisitacambioscanal` / `…cambiosprecio` | cambios de planograma y precio | Planograma |

**Seis de las nueve áreas que pides salen de `partesvisita` y sus hijas.** Una sola extracción
bien hecha cubre más de la mitad del trabajo. Por eso va la primera.

---

## 1 · Rutas

| tabla | col. | qué aporta |
|---|---|---|
| `vending.rutas` | 35 | el maestro: código, denominación, delegación |
| `vending.rutasdetalle` | 9 | **qué PDV está en qué ruta**, con orden, grupo y turno |
| `vending.rutasdetallecriterios` | 40 | el criterio de visita: días de la semana en dos franjas (`l1…d1`, `l2…d2`) |
| `vending.rutasoperarios` | 5 | qué reponedor lleva qué ruta, con `desde`/`hasta` |
| `vending.rutascontrol` | 18 | **la jornada real**: hora inicio y fin, kilómetros, GPS de salida y llegada, vehículo, empleado, temperatura inicial |
| `vending.rutasfondosfijos` | 6 | el fondo fijo de producto que lleva la ruta |
| `vending.planesrutadinamica` + `…detalles` + `…paradas` | 28/27/15 | rutas dinámicas con sus paradas y coordenadas |
| `recursos.vehiculos` | 13 | matrícula del vehículo, delegación |
| `recursos.vehiculosrevisiones` | 8 | revisiones, kilómetros, próxima revisión |

Con esto sale: plan contra realizado, kilómetros por visita, coste de desplazamiento, horas de
jornada, y el cruce que ya vimos de 97 asignaciones de ruta que nunca generan visita.

## 2 · Averías

| tabla | col. | qué aporta |
|---|---|---|
| `sat.tareatecnica` | 36 | **la avería**: fecha, fecha prevista, estado, severidad, origen, técnico asignado, `maquinaparada`, `slapausado`, `facturable` |
| `sat.tareatecnicavisita` | 23 | cada intervención, con GPS |
| `sat.tareatecnicavisitamaterial` | 9 | recambios consumidos |
| `sat.tareatecnicaeventoslog` | 9 | el histórico de estados: aquí está el tiempo real de respuesta |
| `configuracion.satoperaciones` + `…categorias` | 15/4 | el catálogo de operaciones |
| `configuracion.satmotreportados` | 10 | motivos reportados |
| `configuracion.satworkflowestados` | 12 | los estados y su orden |
| `vending.partesvisitaincidencias` | 10 | lo que detecta el reponedor: caducado, rotura, robo, por canal |
| `sat.solicitudesrecambio` | 14 | recambios pedidos |

`tareatecnicaeventoslog` es la pieza que faltaba: con ella el tiempo de respuesta sale del paso
entre estados y no de `fecha_cierre`, que en el 95 % de los casos es un cierre administrativo a
las 00:00.

## 3 · Control Almacenes

Aquí está lo mejor del modelo. Hay **tres diarios de movimiento con la misma estructura**, y se
enlazan entre sí:

| tabla | col. | qué es |
|---|---|---|
| `stocks.diarmovalm` | 35 | movimientos de **almacén** |
| `stocks.diarmovveh` | 32 | movimientos de **vehículo** (la furgoneta del reponedor) |
| `stocks.diarmovmaq` | 23 | movimientos de **máquina** |

Los tres traen `fecha`, `tipomov`, `motivo`, `cantidad`, `existen` (la existencia resultante) y
los cuatro precios `pmc`, `puc`, `pcr`, `preciocoste`. Y se apuntan unos a otros:
`diarmovalm.diarmovvehid`, `diarmovveh.diarmovmaqid`, `diarmovmaq.diarmovalmid`.

**Eso es la trazabilidad completa: compra → almacén → vehículo → máquina → venta.** Es lo que
permite cerrar la merma de verdad, no estimarla.

Complementan:

| tabla | col. | qué aporta |
|---|---|---|
| `recursos.almacenes` + `…secciones` | 14/4 | el maestro de almacenes |
| `stocks.traspasosstock` | 26 | traspasos entre almacenes y vehículos, con origen, destino y estado |
| `stocks.regularizacionesstock` | 17 | ajustes de stock, con motivo |
| `stocks.plancarga` + `plancargarutavehiculo` + `…detalle` | 16/21/11 | lo que se planifica cargar frente a lo confirmado |
| `stocks.planrecogida` + `…detalle` | 6/7 | **retiradas con `cantcaducada` y `cantrotura` separadas** |
| `stocks.planesretornoprod` + `…detalles` | 10/8 | devolución de producto del vehículo al almacén, con doble verificación |
| `recursos.vehiculosnivelstock` | 5 | mínimos y máximos por vehículo |

## 4 · Inventario de almacenes

| tabla | col. | qué aporta |
|---|---|---|
| `stocks.recinventarios` | 9 | el recuento: fecha, almacén o vehículo, si está `cerrado` o es `parcial` |
| `stocks.infinventarioresumenes` | 16 | el informe mensual por año y mes, con criterio de coste y qué se verificó |
| `stocks.infinventarioelementos` + `…prods` | 12/6 | el detalle por elemento y producto |

Lo que sale: diferencia entre inventario teórico y contado, por almacén y por mes, valorada.

## 5 · Inventarios de máquinas

| tabla | col. | qué aporta |
|---|---|---|
| `vending.partesvisitarecinventarios` | 10 | por artículo: `cantidad`, `capacmax`, `stockrecom`, `difcapacidad`, `preciocoste` |
| `vending.partesvisitainvcanales` | 11 | lo mismo canal a canal, con etiqueta y número |
| `vending.partesvisitainvhuecos` | 11 | por hueco |
| `stocks.diarmovmaq` | 23 | el movimiento resultante, con `difinventario` |
| `recursos.maquinascanales` / `maquinascarriles` | 23/15 | el planograma contra el que se compara |

Con `difcapacidad` y `stockrecom` sale la rotura de stock real: cuántas veces una máquina llegó
a la visita por debajo de su mínimo, que es la causa de las máquinas mudas que ya detectamos.

## 6 · Devoluciones

| tabla | col. | qué aporta |
|---|---|---|
| `vending.partesvisitadevolclientes` | 7 | fecha, **DNI, nombre, importe y firma** del cliente |
| `configuracion.conftiposdevol` | 5 | tipos de devolución |
| `facturacion.prefacrecauda.impdevolreclama` | — | el importe devuelto que descuenta de la recaudación |
| `sat.tareatecnica` con categoría `Devolución dinero` | 36 | las devoluciones tramitadas por SAT, no en máquina |
| `stocks.planesretornoprod` + `…detalles` | 10/8 | devolución de producto, no de dinero |

Ojo con una cosa: las devoluciones aparecen por **tres vías distintas** —en la visita, por SAT y
como descuento en la recaudación— y hay que decidir cuál es la buena antes de sumar, o saldrá
contado dos y tres veces.

## 7 · Control de recaudación

| tabla | col. | qué aporta |
|---|---|---|
| `facturacion.prefacrecauda` | 26 | **la recaudación oficial**: `imprecaudado`, `cambiocargado`, `imppagobancario`, `imprecargasbancarias`, `impdevolreclama`, fecha contable, estado, criterio de cálculo |
| `facturacion.prefacrecaudadetalle` | 11 | desglose por IVA |
| `facturacion.prefacrecaudaresumen` | 11 | el agrupado |
| `vending.partesvisitacontajes` | 14 | **el arqueo**: `impmonedas`, `impbilletes`, `importe`, quién contó, y `impmonedasant`/`impbilletesant` con `editadopor` — o sea, **el rastro de las ediciones** |
| `vending.partesvisitacontajesdetalle` | 7 | moneda a moneda: `valordinero`, `cantidad`, `manual` |
| `vending.partesvisitaauditmonbil` | 10 | lo que dice la máquina: aceptadas, `encajon`, `entubos` |
| `vending.partesvisitaaudittubos` | 7 | nivel de los tubos de cambio |
| `vending.partesvisita` (campos `cal_*`) | 137 | los importes calculados de la visita |

La joya es `partesvisitacontajes`: **guarda el importe anterior y quién lo editó**. Eso permite
un indicador de descuadre y de corrección manual que hoy nadie está mirando. Y cruzando el
contaje con `auditmonbil` sale la diferencia entre lo que la máquina dice que tiene y lo que el
reponedor cuenta.

## 8 · Control de bolsas de dinero entregadas

Esto existe tal cual, con ese nombre:

| tabla | col. | qué aporta |
|---|---|---|
| `vending.recogidasbolsasrec` | 10 | la entrega: `fechareg`, `numbolsas`, `tipobolsa`, **`firma`**, reponedor, ruta, delegación, quién la registró |
| `vending.recogidasbolsasrecdetalles` | 10 | **`codbolsa`**, máquina, modelo, PDV, ubicación, cliente y `partevisitaid` |

Es la cadena de custodia completa: qué bolsa, de qué máquina, de qué visita, entregada por quién
y firmada por quién. Cruzada con `partesvisitacontajes` da el indicador que importa: **bolsas
contadas frente a bolsas entregadas, y el tiempo entre la recogida y la entrega.**

## 9 · Control de datos electrónicos

| tabla | col. | qué aporta |
|---|---|---|
| `vending.pdvstransbancarias` | 5 | la remesa: fecha, tipo de pago bancario |
| `vending.pdvstransbancariasdetalles` | 14 | **cada transacción**: `fechatrans`, `tpvnumero`, `transaccionid`, `valor`, `impcomision`, `estado`, `incidencia`, máquina, ruta |
| `telemetry.telemetrysales` | 24 | la venta que la máquina declara, con `transactionid` |
| `telemetry.telemetrydevices` | 14 | los dispositivos, con `auditsenable` y `alarmsenable` |
| `vending.partesvisitaauditcashlessgroups` | 46 | ventas, recargas y descuentos sin efectivo por tipo de usuario, producto gratuito, promoción, cumpleaños… |
| `recursos.tarjetasprivadas` | 7 | tarjeta privada |
| `general.ctasbancarias` / `general.bancos` | 14/3 | cuentas de abono |

El cuadre real se hace por `transactionid`: **lo que la máquina dice que vendió contra lo que el
banco abonó**, con la comisión separada. Eso es lo que el informe 9 intentaba hacer con fechas
fijas en el código.

---

## Cómo lo sacaría, por orden

**Tanda A — la visita y sus hijas.** `partesvisita` más las once tablas que cuelgan de ella, un
mes. Cubre inventarios de máquina, recaudación, contajes, devoluciones, incidencias y datos
electrónicos. Es la que más rinde con diferencia.

**Tanda B — el dinero.** `recogidasbolsasrec` y sus detalles, `prefacrecauda` y sus dos hijas,
`pdvstransbancarias` y sus detalles. Cierra bolsa, recaudación y banco.

**Tanda C — el stock.** Los tres `diarmov*`, `traspasosstock`, `regularizacionesstock`,
`planrecogida` y los inventarios de almacén. Es la que permite cerrar la merma.

**Tanda D — rutas y SAT.** Las nueve de rutas y las nueve de averías. Son maestros pequeños y
tablas de eventos; van juntas y rápido.

Son **unas 55 tablas**. Por volumen, las grandes son las hijas de `partesvisita` y los tres
`diarmov*`: ésas hay que pedirlas por rango de fechas, mes a mes. El resto son maestros que se
bajan enteros una vez por semana.

Cuando me digas por cuál empiezo, escribo el SQL con las tres reglas que ya conocemos: nada de
`::`, nada de `sum(alias.columna)` con parámetros, y `coalesce(campo,0) = 0` en vez de `is null`.
