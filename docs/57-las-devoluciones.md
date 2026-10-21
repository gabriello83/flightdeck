# 57 · Las devoluciones

> Gabriele, 16-oct-2026: «se crea otro cuadrado con las devoluciones y en el cuadrado el total de
> las devoluciones del mes y cuando entras pon varias tablas y gráfico sobre las devoluciones».

El mismo día las devoluciones salieron del estudio de incidencias (docs/56): ni se cuentan ni se
escriben allí. Tienen su propio cuadrado en el informe general y su propia página.

## El cuadrado

**Devoluciones**, entre Incidencias y Almacenes. Desde el 20-oct-2026 la cifra es el dinero
abonado en las devoluciones del mes de ayer, del día 1 hasta ayer (ver «De dónde salen»). Debajo
van cuántas son, el dinero de los mismos días del mes anterior, las que siguen sin resolver y las
rechazadas. No lleva semáforo, porque nadie ha fijado un objetivo; lleva su color propio. El día 1 enseña
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
  área (Centro, Sur, Cataluña, Levante, Norte) con su dinero abonado, cuántas son, cuántas están
  abonadas y cuántas siguen sin resolver. El área sale de la delegación (`operativo.zona_de`). Un
  perfil de una sola área entra directamente en ella.
- **Dentro de un área.**
  - Cuatro cifras: dinero devuelto, devoluciones, sin resolver y rechazadas. Las tres últimas
    filtran la lista de registradas.
  - **Devoluciones registradas**: las 10 últimas («una tabla con los 10»); la flecha abre todas.
    Se baja en CSV.
  - **Máquinas con más devoluciones** y **Devoluciones con más importe**: 5 y la flecha.
  - **Devoluciones por mes y tipo**, el gráfico de antes («de acuerdo»), apilado por tipo de
    devolución y con el dinero abonado de cada mes en la punta y en la vista de tabla.
  - **Clientes con más devoluciones**: 5 y la flecha.

Las tablas de antes por canal, por zona, por técnico y la hoja «Sin cerrar» se van: lo de sin
resolver queda en la cifra que filtra la lista.

## De dónde salen: la Gestión de Devoluciones (M16)

Hasta el 20-oct-2026 se contaban las tareas de devolución de la SAT (M13: serie A de atención al
cliente y serie E de solicitudes especiales), y el importe se leía de la cifra del título. Gabriele,
ese día: «el texto no es correcto … no podemos fiarnos del texto del cliente». La A-70707 decía
«50 €»; la solicitud especial E-11985 que la cerró, 0,50 €. Y señaló la pantalla buena: «Gestión de
Devoluciones», la tabla `vending.reclamaciones`, que se baja con el informe M16 · EXT_DEVOLUCIONES
(informe 198, docs/17).

| | |
|---|---|
| Devolución | una fila de la Gestión de Devoluciones, sin la matrícula ficticia |
| Importe | el campo `impdevolucion` |
| Estado | `estado_devolucion`: 1 En estudio, 2 Pendiente, 3 Abonada, 4 Rechazada. El 2 está abierto, como el 1 |
| Tipo | `tipodevolucion` con su nombre: Transferencia, Sin devolución, En mano, Monyx, Tarjeta prepago, Vendingart, Sobre… |
| Dinero devuelto | la suma de los importes de las **abonadas** |
| Sin resolver | en estudio o pendientes; su importe se dice aparte |
| Fuera del tope | un importe de más de 50 € (`IMPORTE_MAX`) no suma y se enseña: el 9-oct-2026 hay una abonada de 44.504 € en Bilbao |

Con el Excel del informe del 20-oct-2026: 21.204 devoluciones desde el 15-sep-2025; 14.059
abonadas, 4.329 en estudio, 1.297 pendientes y 1.518 rechazadas.

El informe no trae nombre, teléfono, email, NIF, cuenta, firma ni observaciones.

## El fichero

Los agregados escriben cada noche `cabina/<perfil>/devoluciones.json.gz` con el ámbito del perfil
ya aplicado, de la foto M16 (`escribe_incidencias`). Lleva una fila por devolución de los últimos
trece meses enteros, más las que siguen sin resolver aunque sean más viejas. Los centros,
delegaciones, tipos, motivos y estados van en listas aparte. Sin M16 el fichero
dice que falta y no trae filas, y el cuadrado sale «Sin dato».

Se sirve por `/api/devoluciones` tal cual está comprimido, como `/api/incidencias`. Lo pide un
perfil de operaciones o superior que tenga el cuadrado. No hay parámetro con el que pedir el de otro
perfil.

Pruebas: `infra/test_devoluciones.py` (estado, filas, tope, cuadrado y fechas), `infra/test_agregados.py`
(el fichero de AIRBUS, solo con lo suyo, y su cuadrado), `infra/api/test_api.py` (quién la ve) y
`app/comun/prueba_pantallas.js` (la página en claro, oscuro y móvil, sin peticiones fuera).
