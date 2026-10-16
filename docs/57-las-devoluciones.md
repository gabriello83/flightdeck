# 57 · Las devoluciones

> Gabriele, 16-oct-2026: «se crea otro cuadrado con las devoluciones y en el cuadrado el total de
> las devoluciones del mes y cuando entras pon varias tablas y gráfico sobre las devoluciones».

El mismo día las devoluciones salieron del estudio de incidencias (docs/56): ni se cuentan ni se
escriben allí. Tienen su propio cuadrado en el informe general y su propia página.

## El cuadrado

**Devoluciones**, entre Incidencias y Almacenes. La cifra es el número de devoluciones del mes de
ayer, del día 1 hasta ayer. Debajo van los mismos días del mes anterior y las que siguen sin
cerrar. No lleva semáforo, porque nadie ha fijado un objetivo; lleva su color propio. El día 1 enseña
el mes anterior entero. El 31 de marzo se compara con febrero entero.

Lo ve quien ve el bloque SAT, los mismos perfiles que ven Incidencias (`autorizacion.CUADRADOS`).

## La página, /devoluciones/

Tiene dos hojas y los filtros de periodo, canal, zona, delegación y centro. Arranca en el mes
corriente, que es la cifra del cuadrado.

- **Panel de control.**
  - Cuatro cifras contra el periodo anterior: devoluciones, sin cerrar (y cuántas hay hoy en
    total), la mediana hasta cerrar (y la media) y las máquinas con alguna devolución (y cuántas
    tienen tres o más).
  - Un gráfico de columnas por mes, de los trece meses que trae el fichero, apiladas por canal,
    con su vista de tabla.
  - Barras por canal y por zona y delegación.
  - Los 15 centros con más devoluciones, con una columna por canal.
  - Las 15 máquinas con más devoluciones.
  - Una tabla por técnico, con las que tiene sin cerrar y lo que tarda.
- **Sin cerrar.** Todas las que siguen abiertas, sean de cuando sean, de la más vieja a la más
  nueva, con los días que llevan esperando. La lista se baja en CSV.

Pulsar un canal, una delegación o un centro filtra la página por él.

## Las cuentas

| | |
|---|---|
| Devolución | tarea de la SAT con una operación de devolución: los códigos del catálogo (`reglas.OPERACIONES_NO_TECNICAS`, motivo «devolucion») o «DEVOLUC» en la operación |
| Canal | por un trozo del nombre de la operación. D01 y DEV01 son «En el sitio»; D03 y DEV06, «Transferencia»; C24, «Tarjeta de crédito»; D04, «Tarjeta de empleado». Lo demás («No devuelve cambio», «Imposible devolver») va a «Otra» |
| Sin cerrar | sin estado 99 / tipo 9 en la foto de hoy |
| Hasta cerrar | de la apertura al cierre, con su hora; las cerradas sin hora no entran en la mediana |
| Fuera | la matrícula ficticia 00SE0000, como en toda la plataforma. Con el M13 del 16-oct eran 9.934 de 27.450, todas en «CENTRO TEST» de la central, sin máquina ni sitio |

Con el M13 del 16-oct-2026 sale esto para el perfil interno: 16.724 devoluciones en trece meses y
518 entre el 1 y el 15 de octubre, frente a 569 en los mismos días de septiembre. 76 de esas siguen
sin cerrar, y hoy hay 497 sin cerrar en total.

## Lo que no hay

**El importe.** VenCloud no guarda en ningún campo cuánto se devolvió. Solo está en el título que
escribe el técnico, de muchas formas: «0,80€», «DEV. 1,50», «Devolución = 60 centimos». Sacarlo de
ahí sería adivinar, así que se cuentan devoluciones y no euros. Si algún día hace falta el importe,
lo correcto es un campo en VenCloud o un informe que lo traiga.

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
