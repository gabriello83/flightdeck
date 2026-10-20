# 57 · Las devoluciones

> Gabriele, 16-oct-2026: «se crea otro cuadrado con las devoluciones y en el cuadrado el total de
> las devoluciones del mes y cuando entras pon varias tablas y gráfico sobre las devoluciones».

El mismo día las devoluciones salieron del estudio de incidencias (docs/56): ni se cuentan ni se
escriben allí. Tienen su propio cuadrado en el informe general y su propia página.

## El cuadrado

**Devoluciones**, entre Incidencias y Almacenes. Desde el 20-oct-2026 la cifra es el dinero
devuelto en el mes de ayer, del día 1 hasta ayer (ver «El importe, como campo»). Debajo van cuántas
son, el dinero de los mismos días del mes anterior, las que no tienen importe que sumar y las que
siguen sin cerrar. No lleva semáforo, porque nadie ha fijado un objetivo; lleva su color propio. El día 1 enseña
el mes anterior entero. El 31 de marzo se compara con febrero entero.

Lo ve quien ve el bloque SAT, los mismos perfiles que ven Incidencias (`autorizacion.CUADRADOS`).

## La página, /devoluciones/ (por áreas desde el 20-oct-2026)

> Gabriele, 20-oct-2026: «en el cuadrante tiene que salir el total de dinero que se ha devuelto. Una
> vez abierto lo mismo separado por área. Cuando entras en un área poner las devoluciones que se han
> registrado, el top 5 de las máquinas que han registrado más devoluciones, si le das a la flecha
> salen todas, el top 5 de las devoluciones con más importe, si le das a la flecha salen todas, una
> tabla con los 10. Devolución mes y canal de acuerdo. Los top 5 clientes por cada área con más
> devoluciones».

Sigue el patrón de /rutas/ (docs/67) y /furgonetas/ (docs/58). Un filtro de periodo (arranca en el
mes corriente, que es la cifra del cuadrado) y, dentro de un área, otro de delegación.

- **Portada.** El dinero devuelto en todo el ámbito, contra el periodo anterior, y un cuadrante por
  área (Centro, Sur, Cataluña, Levante, Norte) con su dinero, cuántas son, cuántas siguen sin cerrar
  y cuántas no tienen importe que sumar. El área sale de la delegación (`operativo.zona_de`). Un
  perfil de una sola área entra directamente en ella.
- **Dentro de un área.**
  - Cuatro cifras: dinero devuelto, devoluciones, sin cerrar y sin importe. Las tres últimas
    filtran la lista de registradas.
  - **Devoluciones registradas**: las 10 últimas («una tabla con los 10»); la flecha abre todas.
    Se baja en CSV.
  - **Máquinas con más devoluciones** y **Devoluciones con más importe**: 5 y la flecha.
  - **Devoluciones por mes y canal**, el gráfico de antes («de acuerdo»), ahora con el dinero de
    cada mes en la punta y en la vista de tabla.
  - **Clientes con más devoluciones**: 5 y la flecha.

Las tablas de antes por canal, por zona, por técnico y la hoja «Sin cerrar» se van: lo de sin
cerrar queda en la cifra que filtra la lista.

## Dos orígenes

Gabriele, 16-oct-2026: «las devoluciones en VenCloud las puedes encontrar en solicitudes
especiales». Están en dos sitios:

- en **solicitudes especiales** (serie E, categoría «Devolución dinero»: DEV01 in situ, DEV05,
  DEV06), que en lo que va de octubre son 92;
- en **atención al cliente** (serie A: D01 in situ, D03 transferencia, C24 tarjeta de crédito, D04
  tarjeta de empleado), que son 426.

La página cuenta las dos, y un filtro y unas barras «Por origen» las separan. El cuadrado dice
cuántas son especiales. Desde septiembre, 107 de las 356 especiales tienen una de atención al
cliente en la misma máquina y el mismo día, así que puede que algunas estén apuntadas dos veces.
Está pendiente que Gabriele decida si se queda una sola fuente.

## Las cuentas

| | |
|---|---|
| Devolución | tarea de la SAT con una operación de devolución: los códigos del catálogo (`reglas.OPERACIONES_NO_TECNICAS`, motivo «devolucion») o «DEVOLUC» en la operación |
| Canal | por un trozo del nombre de la operación. D01 y DEV01 son «En el sitio»; D03 y DEV06, «Transferencia»; C24, «Tarjeta de crédito»; D04, «Tarjeta de empleado». Lo demás («No devuelve cambio», «Imposible devolver») va a «Otra» |
| Sin cerrar | sin estado 99 / tipo 9 en la foto de hoy |
| Hasta cerrar | de la apertura al cierre, con su hora; las cerradas sin hora no entran en la mediana |
| Fuera | la matrícula ficticia 00SE0000, como en toda la plataforma. Con el M13 del 16-oct eran 9.934 de 27.450, todas en «CENTRO TEST» de la central, sin máquina ni sitio |

Con el M13 del 16-oct-2026 sale esto para el perfil interno: 16.681 devoluciones en trece meses hasta ayer y
518 entre el 1 y el 15 de octubre, frente a 569 en los mismos días de septiembre. 76 de esas siguen
sin cerrar, y hoy hay 497 sin cerrar en total.

## Lo que no hay

**El importe, como campo.** VenCloud no guarda en ningún campo cuánto se devolvió. Pero el
formulario de reclamaciones escribe el título siempre igual: «Devolución = 1,40 € PRODUCTO NO
ENTREGADO DEVOLUCIÓN EN SITU TICKET: …», donde lo que va entre el «=» y el «€» es lo que tecleó el
usuario; los técnicos, a mano, «DEV. 0,50». Desde el 20-oct-2026 la noche lee esa cifra
(`devoluciones.importe_de`) y solo la cifra viaja (`i`); el título no.

- Se aceptan coma, punto o apóstrofo para los decimales, «€», «EUR», «euros» y los céntimos
  («50 cnt», «90centimos», «75 cèntims» son 0,50, 0,90 y 0,75).
- Lo que no es una cifra limpia no se adivina: «OTRO», «Cinco euros», «5+5 (17/11)», «2 cafés»,
  «1, 70», «O,40». Se cuenta como «sin importe».
- Por encima de 50 € (`IMPORTE_MAX`) tampoco se suma: «85 €» o «90 €» en una máquina de vending son
  casi siempre céntimos, pero no se puede saber. Viaja aparte (`g`) y se enseña como «escritos · no
  suma».

Con el M13 del 20-oct-2026: de 16.807 devoluciones en trece meses, 14.415 tienen importe (29.925 €)
y 76 lo tienen por encima de 50 €. Octubre hasta el 19: 1.121,10 € en 654 devoluciones, 87 sin
importe que sumar; septiembre a estas alturas, 1.179,33 €.

**El título y las notas.** En las devoluciones por transferencia el usuario escribe ahí su IBAN,
su nombre o su teléfono. No viajan al fichero, ni siquiera en las abiertas.

## El fichero

Los agregados escriben cada noche `cabina/<perfil>/devoluciones.json.gz` con el ámbito del perfil
ya aplicado, de la misma foto M13 que las incidencias (`escribe_incidencias`). Lleva una fila por
devolución de los últimos trece meses enteros, más las que siguen sin cerrar aunque sean más
viejas. Los centros, delegaciones, canales y técnicos van en listas aparte. Sin M13 el fichero
dice que falta y no trae filas, y el cuadrado sale «Sin dato».

Se sirve por `/api/devoluciones` tal cual está comprimido, como `/api/incidencias`. Lo pide un
perfil de operaciones o superior que tenga el cuadrado. No hay parámetro con el que pedir el de otro
perfil.

Pruebas: `infra/test_devoluciones.py` (canal, filas, cuadrado y fechas), `infra/test_agregados.py`
(el fichero de AIRBUS, sin el IBAN, y su cuadrado), `infra/api/test_api.py` (quién la ve) y
`app/comun/prueba_pantallas.js` (la página en claro, oscuro y móvil, sin peticiones fuera).
