# A11 y A8: el coste del café, por fin, y el cambio parado en las máquinas

Los dos últimos de la tanda A, del 01 al 25 de septiembre de 2026. Los dos vivos, y el A11 resuelve
una pregunta que llevaba abierta desde [09-relleno-resultados.md](09-relleno-resultados.md).

---

## A11 · El café tiene coste, y está aquí

156.443 filas, 21.024 partes, 766 máquinas. Todas de tipo `VE`.

La telemetría nunca supo costear el café: salía siempre sin coste porque **el café no es un
artículo de almacén, es una receta**. Pues bien, esta tabla no trae códigos de artículo para las
bebidas calientes, trae **códigos de receta** —`R01` a `R72`— con su nombre comercial y **su coste
unitario**.

### Café contra envasado, el dato que faltaba

| | unidades | importe | coste | **margen** | precio medio |
|---|---:|---:|---:|---:|---:|
| **Café (72 recetas)** | 254.161 | 141.267,21 € | 20.894,42 € | **85,2 %** | 0,556 € |
| **Envasado (310 refs)** | 306.586 | 360.793,68 € | 152.843,35 € | **57,6 %** | 1,177 € |

**El café es el 45 % de las unidades y sólo el 28 % de la facturación, pero su margen es 27 puntos
mayor.** Un café cuesta 8 céntimos de materia prima y se vende a 56. Es, con diferencia, el dato
comercial más importante que ha salido de todo el proyecto.

Las catorce recetas que más facturan:

| cód. | selección | unidades | importe | margen |
|---|---|---:|---:|---:|
| R04 | Café con leche normal | 55.901 | 27.010,02 € | 79,7 % |
| R03 | Café cortado normal | 30.826 | 14.698,56 € | 82,2 % |
| R12 | Café con leche premium | 17.918 | 11.916,20 € | 83,3 % |
| R02 | Café largo normal | 23.179 | 11.319,71 € | 86,2 % |
| R05 | Cappuccino normal | 15.890 | 8.590,49 € | 82,5 % |
| R29 | Cappuccino avellana | 13.046 | 8.128,65 € | 87,4 % |
| R11 | Café largo premium | 10.136 | 6.544,70 € | 87,5 % |
| R01 | Café solo normal | 12.730 | 6.381,23 € | 87,5 % |
| R16 | Café cortado premium | 9.394 | 5.881,29 € | 84,6 % |
| R10 | Café solo premium | 7.018 | 4.792,85 € | 88,6 % |
| R13 | Cappuccino premium | 5.906 | 3.963,37 € | 82,6 % |
| R06 | Leche manchada normal | 6.147 | 3.535,79 € | 85,1 % |
| R17 | Café con leche descafeinado | 6.314 | 3.423,98 € | 92,2 % |
| R30 | Chocolate con leche | 5.078 | 3.088,43 € | 88,1 % |

Y confirma lo que contaba operaciones sobre los precios: **normal y premium son selecciones
distintas con precio distinto**, y el descafeinado va con el precio del normal. Aquí se ve: café
con leche normal a 0,483 € de media y premium a 0,665 €.

### Cómo se usa esto en el resto del parque

Estas 766 máquinas son sólo las que se leen por visita: el informe factura 502.060,89 € contra los
1.071.227,72 € que da la telemetría en esas mismas fechas, un **46,9 %** del parque.

Pero lo que vale no son los totales, **es el coste unitario de cada receta**. Con la tabla
`R01…R72` → coste se puede costear el café de **todas** las máquinas cruzándola contra la
telemetría, que sí cubre el parque entero. Eso cierra el agujero del «43,7 % de ventas con coste
conocido» que arrastramos desde septiembre.

### Un aviso: no uses el campo `beneficio`

No cuadra. La suma de `imp_total_sin_iva` menos `coste_unitario × num_total` da **275.768,08 €**, y
el campo `beneficio` dice **297.029,17 €**: 21.261 € de diferencia, un 7,7 %.

El margen hay que calcularlo, no leerlo. Y `coste_unitario` viene a cero en el 6,0 % de las filas,
que hay que tratar aparte igual que los 59 artículos sin coste del A2.

### Un dato de paso sobre los medios de pago

| | importe | % |
|---|---:|---:|
| Efectivo | 229.424,24 € | 45,7 % |
| **Tarjeta privada** | **227.909,31 €** | **45,4 %** |
| Tarjeta de crédito | 44.727,34 € | 8,9 % |

Casi la mitad por tarjeta privada —la de empresa o prepago—, muy por encima de la de crédito. Y
suman exactamente el importe total.

---

## A8 · Hay unos 52 € de cambio parados en cada máquina

254.306 filas, 45.637 partes, 859 máquinas. Todas monedas, y `tubo_lleno` viene a `false` en las
254.306: ese campo no se usa.

A diferencia del `auditmonbil`, aquí **`cantidad_actual` es un stock, no un contador**: las monedas
que hay ahora mismo en el tubo. Máximo observado, 1.536 monedas en un tubo. Eso lo hace directamente
utilizable, sin la limpieza que necesitaba el monedero.

Cambio por máquina en cada lectura:

| | |
|---|---:|
| Mediana | **52,00 €** |
| Media | 63,84 € |
| Percentil 90 | 104,20 € |
| Percentil 99 | 143,95 € |
| Máximo | 827,35 € |

Sobre las 3.200 máquinas operativas son del orden de **166.000 € de dinero de la casa inmovilizado
en tubos de cambio**. No es una pérdida, pero es circulante, y hasta ahora nadie lo tenía contado.

Las máquinas del percentil 99 —por encima de 144 €— tienen cambio de sobra y son candidatas a
reducir la carga. La del máximo, con 827 €, hay que mirarla.

**Ojo con las denominaciones**, igual que en el monedero: además de las monedas de euro aparecen
`12,75` (2.160 filas), `2,55`, `48,00`, `0,04`, `0,40` y `0,45`. Hay que filtrar por denominación
real antes de sumar euros.

---

## La tanda A, cerrada

| | informes |
|---|---|
| **Vivos** | A1 cabecera · A2 reposiciones · A3 inventario (+A3B, A3C) · A7 monbil · A8 tubos · A10 devoluciones · A11 ventas |
| **Descartados** | A4 invcanales · A5 contajes · A6 contajes detalle · A9 incidencias |

Siete de once. Los cuatro descartados son tablas que existen en el modelo y nadie escribe, y eso
sólo se descubre lanzándolas.
