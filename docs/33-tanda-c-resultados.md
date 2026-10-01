# Tanda C · Resultados: el balance de stock, y dos procesos que no se cierran

C4, C5, C7 y C10 sobre el 01–25 de septiembre; C8 y C9 sobre el año 2026.

---

## C9 · No son inventarios de almacén: es el balance de stock de la compañía

Me equivoqué al catalogarlo. `infinventarioresumenes` no valora almacenes, **valora los tres
eslabones a la vez**, y es el cierre mensual de existencias:

| `tipo_elemento` | filas | valor |
|---|---:|---:|
| **A** · almacén | 152 | **5.119.222,06 €** |
| **M** · máquina | 30.493 | **2.602.819,09 €** |
| **V** · vehículo | 893 | **569.796,62 €** |
| **TOTAL** | 31.538 | **8.291.837,77 €** |

**Ocho millones y cuarto de euros de existencias**, de los cuales 2,6 M están dentro de las
máquinas y medio millón viajando en furgonetas. Es una cifra que no teníamos y que sale de un solo
informe.

140 resúmenes en nueve meses, ~3.300 elementos valorados al mes. O sea que **el parque entero se
valora todos los meses**, tenga inventario real o no: la valoración es del stock teórico.

### Y confirma por su cuenta el problema de inventario

`fecha_ult_inventario` viene a `01/01/1900` —el centinela de «nunca»— en **8.979 de los 31.538
elementos, el 28,5 %**. Lo medimos hace dos días por otro camino y dio 23,8 % de máquinas nunca
inventariadas. Dos fuentes independientes, el mismo orden de magnitud.

**C10** trae el detalle producto a producto: 50.231 líneas de 2.313 elementos, 912.942,40 €, y los
2.313 elementos existen todos en C9. Encaja perfecto. 3.163 líneas con `precio_coste` a cero — el
mismo agujero de siempre.

## C7 · El plan de carga está abandonado

La sonda decía 5.932 planes históricos. En el 01–25 de septiembre hay **4 líneas, 3 planes, y una
sola ruta**: «Ruta Alhambra Mañana», en Granada.

De 58 rutas diarias, **una usa el plan de carga**. Los 5.932 planes históricos y el 82 % atascado
en estado 1 se explican solos: se probó, no cuajó, y quedó un resto.

**Y esto explica el C4.** De los 1.149 traspasos del mes, **1.049 llevan el motivo «Traspaso extra
sin picking»**: el 91 %. Sin plan de carga no hay picking, así que la carga del vehículo se hace a
mano y se registra como traspaso extra. No es un fallo de dato, es cómo se trabaja.

La consecuencia para el cuadro de mando: **«lo planificado contra lo cargado» no se puede medir**,
porque no hay plan. Lo que sí se puede medir es lo contrario —qué se carga y qué vuelve— con C2 y
C8.

## C4 · Los traspasos sí se cierran

1.149 traspasos en 25 días, **todos en estado 2 y todos con fecha de entrada**. Ninguno a medias.
Eso responde la duda que dejó la sonda 1: el estado 2 es «recepcionado» y el proceso se completa
siempre.

| motivo | traspasos |
|---|---:|
| Traspaso extra sin picking | 1.049 |
| Devolución de furgoneta a almacén | 48 |
| Envío productos almacén | 30 |
| Traspaso repuesto a vehículo | 8 |
| Traspaso entre vehículos | 7 |

Origen almacén en 1.093 y destino vehículo en 1.070: es, casi en su totalidad, **cargar la
furgoneta**.

## C5 · Las regularizaciones son 35 en todo el mes

Y aquí hay una contradicción que hay que resolver antes de publicar nada.

Los diarios marcaron **1.838 movimientos con `dif_inventario`** por 62.453 € en 25 días. Pero
regularizaciones formales sólo hay **35**, concentradas en seis delegaciones —Murcia 16, Málaga 8,
Cornellà 5— y hechas por once personas.

Las dos cosas no pueden describir lo mismo. La lectura más probable: `dif_inventario` marca el
ajuste que genera **el propio recuento de inventario**, automático, mientras que
`regularizacionesstock` es la **corrección manual** que alguien decide hacer. Son dos cosas
distintas y el cuadro de mando no debe sumarlas.

Y las 35 manuales, por sí solas, dicen algo: **Madrid-Leganés, la delegación más grande, hizo una.**
Murcia dieciséis.

## C8 · Los retornos se anotan y nunca se verifican

12.249 líneas en 231 retornos, de enero a septiembre, 40 vehículos y 451 artículos.

| campo | valor |
|---|---|
| `estado` | **0 en las 12.249** |
| `verificado` | **0 en las 12.249** |
| `fecha_verif_reponedor` | **1900 en las 12.249** |
| `fecha_verif_almacen` | **1900 en las 12.249** |
| `cant_verif_reponedor` | **0,00** |
| `cant_verif_almacen` | **0,00** |

Ni un solo retorno verificado en nueve meses, por ninguna de las dos partes.

Y el detalle importa: **la cantidad devuelta sólo se registra al verificar**. `cant_stock` es el
stock en ese momento, no lo que se devuelve. Así que la tabla guarda la intención de devolver y
**nunca el resultado**: no se puede saber cuánto producto volvió del vehículo al almacén.

Es el mismo agujero que la entrega de bolsas a Loomis, y del mismo tipo: **producto que cambia de
manos sin que nadie firme la recepción.** Lo que más se retorna son, otra vez, los frescos
—ÑAMING GO! POLLO CHEDAR a la cabeza— y café en grano.

## Balance de la tanda C

| informe | estado | qué aporta |
|---|---|---|
| C1 · almacén | **vivo** | 1,14 M € movidos en el mes |
| C2 · vehículo | **vivo** | 0,78 M €, y el 79 % de la caducidad |
| C3 · máquina | **vivo** | trazabilidad con la reposición, al 100 % |
| C4 · traspasos | **vivo** | 1.149 en el mes, todos cerrados |
| C5 · regularizaciones | **vivo pero mínimo** | 35 en el mes |
| C6 · recogidas | **muerto** | tabla vacía |
| C7 · plan de carga | **abandonado** | 1 ruta de 58 |
| C8 · retornos | **vivo a medias** | se abre, nunca se cierra |
| C9 · balance de stock | **vivo, y clave** | **8,29 M € de existencias** |
| C10 · detalle | **vivo** | producto a producto |

Y con esto quedan cubiertas las cuatro áreas que pediste: control de almacenes, inventario de
almacenes, devoluciones y la parte de stock de rutas.
