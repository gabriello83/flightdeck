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
| **Punto de venta sin máquina** | hay sitio dado de alta y no hay máquina puesta |
| **Sin tarifa** | vende sin precio configurado: dinero mal facturado o perdido |
| **Sin planograma** | no se puede saber qué debería haber en cada canal, así que tampoco si estaba vacía o es que no había demanda |
| **Telemetría sin dato electrónico** | tiene sistema de telemetría y no tiene dispositivo: la venta por tarjeta no llega |

El catálogo con su explicación **viaja en el panel**, no está escrito en la página: añadir una
incidencia es tocar `reglas.py` y nada más.

Y el panel no da sólo el número: da **la lista**, con cliente, centro, punto de venta, máquina y
delegación. Un contador sin la lista no se puede accionar.

## Lo que no se cuenta como incidencia

Un punto de venta **de baja** no es una incidencia: es una baja. Se mira `baja_pdv` y `estado_pdv`,
y lo que está muerto no sale. Sin eso el panel nacería con cientos de casos falsos y nadie volvería
a abrirlo.

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

Un informe nuevo, `EXT_INSTALACIONES` (`docs/17`, M5). Arranca de `comercial.clientes` y baja con
`left join` hasta la máquina, no al revés: así un cliente sin centros, o un centro sin puntos de
venta, **sale igual** con el resto en blanco.

Es un maestro: la foto de hoy, no una ventana de días. Y de paso arregla algo que venía de antes —
es la **primera fuente del mapa de centros**, así que el mapa arranca con todo el parque situado en
vez de ir aprendiéndolo máquina a máquina según aparecen en la ventana. Una máquina que no ha tenido
ni una visita en 120 días también queda situada.

## Lo que falta

**La tarifa de productos del cliente y del centro.** El informe 10 de VenCloud las enseña, así que
las columnas existen, pero su nombre no está escrito en ninguna parte de esta documentación y no se
inventa — es exactamente el error que se cometió con el `join` de `EXT_SAT_AVERIAS`.

Mientras tanto, «sin tarifa» mira la del punto de venta y la del cliente: **lo que marca, lo está de
verdad, pero puede haber más**. El panel lo dice en su propia nota, en vez de dar una cifra que
parece completa y no lo es.

Se cierra con `EXT_SONDA_COLUMNAS` (`docs/17`, M6), que no es un informe de datos sino la pregunta
«¿cómo se llaman de verdad estas columnas?».
