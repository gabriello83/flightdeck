# 45 · Instalaciones

> El panel de lo que está puesto y lo que está puesto a medias. Sesión `instalaciones`, a partir de
> perfil de operaciones.

## Por qué existe

Los demás paneles cuentan **lo que pasó**: visitas, recaudación, averías. Éste cuenta **lo que hay
que arreglar hoy**, y es otra clase de cosa.

Una máquina sin tarifa lleva sin facturar bien desde el día que se instaló, y nadie se entera
mirando la venta: la venta sale, simplemente sale mal. Una máquina con telemetría y sin dispositivo
vende y cierra su parte con normalidad, y su venta por tarjeta no llega nunca; eso aparece tres
meses después como efectivo ciego, cuando ya no se sabe de dónde salió. Son fallos que **no dan
error**, y por eso hay que ir a buscarlos.

## Las seis incidencias

| incidencia | qué significa |
|---|---|
| **Cliente sin centros** | dado de alta y sin un solo centro colgando |
| **Centro sin puntos de venta** | el centro existe y no tiene nada instalado |
| **Centro sin una sola máquina** | tiene puntos de venta dados de alta y ni una máquina puesta en ninguno |
| **Instalación pendiente** | punto de venta dado de alta hace menos de tres meses y todavía sin máquina |
| **Sin tarifa** | vende sin precio configurado: dinero mal facturado o perdido |
| **Sin planograma** | no se puede saber qué debería haber en cada canal, así que tampoco si estaba vacía o es que no había demanda |
| **Telemetría sin dato electrónico** | tiene sistema de telemetría y no tiene dispositivo: la venta por tarjeta no llega |

El catálogo con su explicación **viaja en el panel**, no está escrito en la página: añadir una
incidencia es tocar `reglas.py` y nada más.

Y el panel no da sólo el número: da **la lista**, con cliente, centro, punto de venta, máquina y
delegación. Un contador sin la lista no se puede accionar.

## Lo que no se cuenta como incidencia, y por qué

Esto es la mitad del trabajo. Un panel que marca dos mil casos que nadie va a tocar no se abre dos
veces, así que cada exclusión está medida sobre el censo real del 5 de octubre de 2026.

**`estado_pdv` no es un estado de alta o baja: es «tiene máquina puesta».** Lo dice el dato sin
ambigüedad: de los 3.200 con estado 1, los 3.200 tienen máquina; de los 2.005 con estado 0,
**ninguno**. El 9 es el único que significa baja, y esa fila además traía su fecha. Así que lo que
marca una baja es la fecha, no el estado — la primera versión suponía lo contrario.

**Un punto de venta sin máquina sólo es una incidencia si es nuevo.** Hay 2.006 sin máquina, y
**1.946 tienen `alta_pdv` a 1900-01-01**, el centinela de «nunca»: son huecos del parque, no trabajo
pendiente. Sólo 60 tienen fecha de verdad. Así que la incidencia es «dado de alta hace menos de tres
meses y todavía vacío» — hoy, **dos casos**, los dos de AIRBUS.

**La fila centinela no es un cliente.** VenCloud trae el cliente `0` «Ventas Contado», con centro
`-1` y punto de venta `-99`, igual que trae la matrícula `00SE0000` que no es una máquina. Ni da
incidencias ni cuenta en el censo ni entra en el mapa de centros.

## La pega que no cabe en una fila

Casi todas las incidencias se ven mirando una fila. Una no: **un centro con puntos de venta y ni una
sola máquina**. Hay que recorrerlo entero para saberlo, así que se cuenta por centro mientras se lee
y se decide al final.

Apareció por sí sola. Al enchufar el censo, `AIRBUS PUERTO REAL` desapareció de los diez centros que
el ámbito de AIRBUS reconocía, y quedaron nueve. No era un fallo: **el centro tiene 22 puntos de
venta y cero máquinas**, así que ninguna matrícula apunta a él. Lo mismo le pasa a `AIRBUS ITC`, que
además está duplicado —500094 con 10 máquinas y 500121 con uno vacío—.

Son **30 centros en todo el parque**, y los tres mayores son ERNST & YOUNG (28 puntos de venta),
AIRBUS PUERTO REAL (22) y HOSPITAL SAN JUAN DE DIOS BORMUJOS (22). O se retiraron todas las máquinas
y nadie cerró el centro, o la instalación nunca llegó. En los dos casos hay algo que hacer.

En esta lista lo gordo va primero: un centro con 22 puntos de venta vacíos no es lo mismo que uno
con uno.

## Lo que sale hoy, con el censo real

5.331 filas · 369 clientes · 889 centros · 5.209 puntos de venta · 3.203 máquinas.

| | |
|---:|---|
| **431** | Sin tarifa |
| **307** | Sin planograma |
| **71** | Centro sin puntos de venta |
| **9** | Cliente sin centros |
| **2** | Telemetría sin dato electrónico |
| **30** | Centro sin una sola máquina |
| **2** | Instalación pendiente |

Y 24 altas en el último mes: 13 puntos de venta, 9 centros y 2 clientes.

Las dos primeras cuadran con lo que midió el informe 10 de VenCloud en su día (402 sin tarifa, 314
sin planograma) sobre un parque algo distinto, que es lo que se esperaba de una regla escrita a
partir de él.

Las dos de telemetría son pocas **y es una buena noticia**, no un fallo de la regla: casi todas las
máquinas con NAYAX tienen su dispositivo. El 63,8 % de `telemetriadispositivo` relleno que cita
`docs/09` está medido sobre las 4.498 máquinas **del parque entero**, y 1.295 de ellas están en
taller o almacén, sin punto de venta: ésas no tienen por qué tener dispositivo.

## Qué es «nuevo»

VenCloud no dice cuándo se dio de alta un cliente ni un centro, y el maestro se sobrescribe cada
noche: **no hay historia que mirar**. Así que la historia se la guarda la Lambda de agregados, que
es la única que la necesita: después de cada ejecución escribe su censo en
`cabina/_censo/anterior.json`, y a la siguiente compara.

«Nuevo» es, por tanto, **lo que no estaba en la ejecución anterior**. La primera vez no hay con qué
comparar y no sale ninguna alta, que es lo correcto: lo contrario sería dar de alta hoy las 3.168
máquinas del parque y que nadie volviera a abrir este panel.

Si una noche falta el maestro, el censo **no se guarda**: así una caída no hace que al día siguiente
parezca que todo es nuevo.

## De dónde salen los datos

Un informe nuevo, `EXT_INSTALACIONES` (`docs/17`, M5, informe **173**). Arranca de `comercial.clientes` y baja con
`left join` hasta la máquina, no al revés: así un cliente sin centros, o un centro sin puntos de
venta, **sale igual** con el resto en blanco.

Es un maestro: la foto de hoy, no una ventana de días. Y de paso arregla algo que venía de antes —
es la **primera fuente del mapa de centros**, así que el mapa arranca con todo el parque situado en
vez de ir aprendiéndolo máquina a máquina según aparecen en la ventana. Una máquina que no ha tenido
ni una visita en 120 días también queda situada.

## Lo que la sonda cerró, y lo que destapó

`EXT_SONDA_COLUMNAS` (`docs/17`, M6, informe 174) no es un informe de datos: es la pregunta «¿cómo
se llaman de verdad estas columnas?». Devolvió las 98 de `comercial.clientes`, las 81 de
`comercial.clientescentros` y las 77 de `vending.pdvs`, y con ellas se cerraron dos cosas y se
destapó una tercera.

**La tarifa de productos se llama `tarifaocsid`** —OCS, el servicio de café de oficina—, y está
tanto en el cliente como en el centro. Adivinando se habría escrito `tarifaproductosid`, que no
existe. Así que «sin tarifa» mira ahora los **cinco** sitios de los que puede colgar: vending en
punto de venta, centro y cliente, y OCS en centro y cliente. Basta con uno, que es como lo hace el
informe 10 de VenCloud.

**Las altas tienen fecha.** `fechaalta` está en los tres niveles, así que las altas no hay que
adivinarlas comparando censos: se leen. El panel da «Altas recientes» con la fecha de verdad desde
la primera ejecución, y «nuevos desde anoche» sigue existiendo para lo que no tiene fecha —una
máquina, cuyo `fechacompra` es otra cosa—.

**Y `telemetriadispositivo` no está donde decía la documentación.** `docs/04` afirmaba que era
`pdvs.telemetriadispositivo`; la sonda lista las 77 columnas de `vending.pdvs` y no está. Vive en
`recursos.maquinas`, como dicen `docs/08` y `docs/10`. La primera versión del informe fue con la
columna mal y VenCloud la rechazó: un dato publicado en nuestra propia documentación, equivocado, y
copiado sin comprobar.
