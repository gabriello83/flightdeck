# 48 · El histórico desde 2025, y elegir el tiempo

> `infra/serie.py`, `infra/lambda_agregados.py`, `infra/cuadro.py`, `infra/api/lambda_api.py`
> (`/api/serie`), `app/comun/periodos.js`, y el selector en `app/panel/`, `app/consola/` y
> `app/cuadro/`.

Hasta aquí todo lo que se veía era **una foto de los últimos 120 días**. Sirve para «cómo va el
parque» y no sirve para nada de lo que se pregunta a diario: cuánto se vendió ayer, cómo va este
mes contra el pasado, qué pasó en marzo. Esos números no estaban, y **no salen de restar**: el
panel es un resumen, no un saldo.

Lo que hacía falta eran dos cosas distintas, y conviene no confundirlas:

1. **La historia**: que en S3 haya dato desde el **1 de enero de 2025**.
2. **El tiempo elegible**: que cualquiera pueda pedir hoy, ayer, este mes, el mes pasado o un
   intervalo cualquiera, y que la cifra salga en el acto.

## La serie diaria: una fila por día que se puede sumar

`infra/serie.py` escribe, para cada perfil y cada día, una fila con lo que pasó ese día. La regla
que sostiene el fichero entero es una:

> **Una fila sólo guarda cosas que se pueden sumar.**

Un contador se suma. Un importe se suma. Una media **no** se suma, y una mediana menos todavía. Así
que de las distribuciones —minutos de visita, horas de cierre de una avería, kilómetros,
temperatura— no se guarda el resumen: se guarda el **histograma**, que sí se suma, y la mediana de
un rango sale del histograma sumado. Es aproximada hasta el ancho de su tramo, y se dice donde se
enseña; la media y los totales son exactos, porque la fila guarda también la suma y el número de
valores.

Los tramos están afinados donde está el dato: la mediana de una visita cae sobre los 6-7 minutos
(docs/21), así que ahí los tramos van de un minuto y arriba de hora en hora. Un tramo de 0 a 10
habría dado una mediana inútil justo donde importa.

**Lo que no se puede sumar no se disimula.** «Máquinas distintas atendidas» en un intervalo no es
la suma de las de cada día: la misma máquina se visita diez veces al mes. Se guarda el valor de
cada día y al juntar un rango se da el **máximo de un día**, nunca un total inventado.

**El dinero va por periodo contable, no por día.** `prefacrecauda` se agrupa por año/mes y la fecha
del fichero es la de escritura (reglas.py). La fila de un día guarda, por eso, un diccionario
`periodo -> importes`: lo escrito ese día, del mes al que pertenezca. Sumar días da los periodos
completos, que es como hay que leerlo.

| en S3 | qué es |
|---|---|
| `cabina/<perfil>/serie/indice.json` | los meses que hay, con sus totales, los tramos de los histogramas y los rangos con nombre |
| `cabina/<perfil>/serie/<AAAA-MM>.json.gz` | las filas de ese mes, una por día |

## La noche no se encarece con la historia

Esto era la parte difícil. Recalcular 650 días cada noche no cabe en ninguna Lambda, y leer sólo la
ventana dejaría la historia sin escribir.

La noche sigue leyendo **los mismos 120 días de siempre** y, con lo que ya está leyendo, escribe
también las filas de esos días. Al guardar, **fusiona**: los días que ha leído sustituyen a los que
hubiera —es el mismo día visto otra vez, no más dato— y los demás días del mes **se quedan como
estaban**. Por eso la historia se acumula sin releerla.

El recorrido pasó a ser **por días, y dentro de cada día por informes** (antes era al revés), para
poder cerrar la fila de un día en cuanto se acaba. El orden de `FUENTES` sigue mandando dentro de un
día, que es donde importaba: los tres informes con columna `centro` van antes que los que sólo
traen matrícula, y la telemetría de un día antes que la venta del parte de ese día.

La historia anterior al despliegue se rellena **una vez**, con un evento:

```json
{"desde": "2025-01-01", "hasta": "2025-01-31"}
```

Ese modo escribe serie y meses del cuadro, y **ni panel ni censo**: el panel es la foto de hoy y no
se puede reescribir con una ventana de enero de 2025. Si se acaba el tiempo, para y dice por dónde
seguir, igual que la extracción.

## El cuadro: un fichero por mes que se entiende solo

El cuadro de David ya iba troceado por mes, pero los trozos citaban las máquinas y los artículos
por su posición en el **índice**, que se reescribía cada noche. Eso impedía las dos cosas que ahora
hacen falta: fusionar un mes sin releerlo, y bajar sólo los meses del periodo elegido.

Ahora **cada mes lleva dentro su propia lista de máquinas y de artículos**, y sus filas las citan
por posición dentro de ese mes. Eso compra:

- La noche sólo reescribe los meses que ha mirado, fusionando por días.
- El navegador baja **sólo los meses del periodo** que se elija. Veintitantos meses de venta por
  día, máquina y artículo no caben en una pestaña, y no hacen falta.
- Una máquina retirada en marzo de 2025 **sigue teniendo centro** en el fichero de marzo de 2025,
  aunque no esté en el censo de hoy.

Los meses no se parten: se **comprueba** que caben en una respuesta de Lambda y, si uno no cabe, lo
dice el índice (`_aviso_tamano`) en vez de descubrirse con un error en el navegador. Un mes de
AIRBUS son unos tres megas de JSON, unos cuatrocientos kilos comprimido.

## El selector de tiempo, el mismo en las tres pantallas

`app/comun/periodos.js` lo comparten la consola, el panel de cliente y el cuadro. Lleva los rangos
con nombre, la suma de la serie y el selector pintado. Está en un solo sitio para que «este mes»
signifique lo mismo en las tres, y porque **la misma cuenta está en Python** (`serie.suma_filas`):
`infra/test_serie.py` las compara de verdad, ejecutando el fichero con node, porque si las dos no
dan lo mismo el número que lee el cliente no es el que decimos nosotros, y eso no se ve mirando
ninguno de los dos ficheros por separado.

| rango | qué es |
|---|---|
| Hoy | el día de hoy. Puede estar vacío: la carga va de noche y trae hasta ayer |
| Ayer | el último día con dato normalmente |
| Esta semana | del lunes a hoy |
| Este mes | del día 1 a hoy |
| Mes pasado | el mes anterior **entero** |
| Últimos 30 días | hoy y los 29 anteriores |
| Este año | del 1 de enero a hoy |
| Todo el histórico | desde el 1 de enero de 2025 |
| Intervalo | dos fechas, acotadas entre el primer día con historia y hoy |

Un mes se baja **una vez por visita**: cambiar de rango dentro de un mes ya bajado no pide nada al
servidor, y un intervalo largo sólo pide los meses que le falten.

### En el panel de cliente

El panel arranca como siempre, en la foto de la ventana, con un botón para volver a ella. Al elegir
un periodo, las cifras de tiempo se recalculan de la serie y **lo que no se puede partir por días
sigue siendo la foto de la ventana, y se dice arriba**: el reparto por centro, la merma por
artículo, las máquinas reincidentes, el inventario y las instalaciones. Esa es la deuda que queda
(ver abajo), y es mejor decirla que rellenarla con un número que no significa nada.

### En la consola

Una pestaña «Histórico», con el ámbito del administrador —todo el parque— y, debajo, **la tabla de
lo que hay cargado mes a mes**. Esa tabla es la que dice si un relleno se quedó a medias: un mes con
pocos días se vuelve a lanzar y se completa.

### En el cuadro

Los mismos rangos sobre las dos fechas que ya tenía, y arranca en el **último mes con dato** en vez
de en la historia entera. Elegir un periodo baja los meses que falten; los filtros de centro,
máquina y artículo se quedan como estaban, porque cambiar de mes no es empezar de cero.

## El recorte: la serie no es la puerta de atrás del panel

Una fila de la serie lleva los mismos bloques que el panel —servicio, dinero, sat, jornadas— con
las mismas cifras partidas por días. Si se sirviera entera, un perfil al que se le quitó el dinero
lo vería aquí día a día. Así que `/api/serie` la recorta **con la misma tijera y en la misma
función** que el panel (`autorizacion.recorta_dia`), ni en una copia ni en el navegador:

- fuera los bloques que ninguna de sus sesiones necesita;
- fuera el coste de servicio si no es dirección ni administración;
- la venta va con «dinero», porque es facturación.

Y el perfil sale de la **sesión**, nunca de la petición: un mes sólo se sirve si el índice de ese
perfil lo cita, así que no hay forma de componer la clave de otro.

## Lo que queda

- **El reparto por centro, por días.** Es lo único que se echa en falta al elegir un periodo. Para
  un perfil de cliente son diez centros y cabría de sobra en la fila del día; para el interno son
  más de mil, y ahí no. O sea que la fila tendría que llevarlo sólo cuando el perfil tiene pocos
  centros, y eso es una forma distinta de fila según el perfil: se deja escrito aquí y se hace
  cuando se pida, no por adelantado.
- **La venta sigue siendo parcial** mientras no exista el informe `EXT_TELEMETRIA_VENTAS`
  (docs/46): el histórico de venta arrastra la misma limitación, y el cuadro lo avisa.
- **Las averías que cruzan de un día a otro** no entran en el cierre mediano de un rango: una fila
  diaria no puede medir lo que empieza en otro día. El panel de la ventana sí las mide, y la
  pantalla lo dice donde da el número.
