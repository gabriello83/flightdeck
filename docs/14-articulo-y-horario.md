# Producto y horario, septiembre 2026

Dos tablas más: **máquina × artículo** (50.171 filas) y **perfil horario por centro y día**
(30.086 filas). Ambas cuadran con el resumen diario: 1.090.340,02 € y 1.090.376,82 €, las
diferencias son del 26 de septiembre en curso.

---

## 1. El 26,3 % del dinero no sabe qué producto es

**287.076,97 € y 242.433 unidades del mes salieron por canales sin artículo asignado.**

| | |
|---|---|
| máquinas afectadas | **1.693 de 2.064** (82 %) |
| máquinas con el 100 % del importe sin mapear | **215** (60.637 €) |
| máquinas con más del 50 % sin mapear | 294 |
| canal más frecuente sin mapear | `-1` (1.125 casos), luego 0, 1, 3, 5 |

Y no está repartido al azar: **se concentra en hospitales**.

| matrícula | centro | € perdidos | canales |
|---|---|---|---|
| 16SE1309 | Hosp. Virgen Macarena Urgencias | 3.581,10 | 36 |
| 24CE4845 | Can Ruti | 1.749,40 | 28 |
| 16SE1310 | Hosp. Virgen Macarena General | 1.644,40 | 36 |
| 19FE1578 | CosmoCaixa Público | 1.326,40 | 52 |
| 15SE0768 | Hosp. Virgen Macarena General | 1.259,70 | 35 |
| 25FP4585 | Hospital José María Morales Meseguer | 1.211,60 | 2 |
| 21CE4612 | Pere Virgili - Edifici Xaloc | 1.068,00 | 19 |

Cuatro máquinas del Virgen Macarena con 34–36 canales cada una, todos sin mapear: eso no es un
descuido puntual, es un planograma que nunca se cargó. **Es la acción operativa más rentable que
sale de todo el análisis**: 215 máquinas a mapear, ordenadas por importe, y se recupera visibilidad
sobre 60.637 € al mes en el peor grupo y 287.077 € en total.

Mientras esto no se arregle, ningún indicador de producto, de rotura de stock ni de margen cubre
más de tres cuartas partes del negocio.

## 2. El Pareto: 70 artículos hacen el 80 %

446 artículos distintos vendidos. **20 artículos son el 49,4 % del importe identificado, 50 son
el 71,9 %, y 70 llegan al 80 %.**

| código | artículo | unidades | importe | máquinas | precio medio | puc |
|---|---|---|---|---|---|---|
| 5322 | AGUA FONT VELLA PET 50CL | 80.570 | 59.363,63 € | 546 | 0,74 | 0,146 |
| 9321 | COCA COLA ZERO LATA 33CL | 47.540 | 43.553,74 € | 582 | 0,94 | 0,499 |
| R04 | **Café con leche normal** | **90.491** | 41.540,56 € | 630 | 0,54 | — |
| 9354 | COCA COLA LATA 33CL | 40.830 | 38.273,18 € | 571 | 0,93 | 0,547 |
| 5356 | AGUA LANJARON PET 0,5L | 24.154 | 25.917,68 € | 82 | 0,90 | 0,164 |
| R03 | Café cortado normal | 42.380 | 19.197,76 € | 602 | 0,53 | — |

El café con leche es **el artículo más vendido en unidades de toda la compañía** —90.491 al mes,
en 630 máquinas— y es justo el que no tiene coste.

## 3. El margen, por fin con número

| tramo | importe | peso |
|---|---|---|
| identificado y con `puc` | 590.317,64 € | **54,1 %** |
| identificado sin `puc` (café) | 212.945,41 € | 19,5 % |
| sin artículo | 287.076,97 € | 26,3 % |

Sobre la parte medible: **coste 260.581,40 €, margen 329.736,24 €, un 55,9 %.**

| clase | importe | margen | % |
|---|---|---|---|
| 2 · bebida fría envasada | 324.141,42 € | 186.897,70 € | **57,7 %** |
| 3 · snack | 266.176,22 € | 142.838,54 € | **53,7 %** |

Es un margen bruto sano y consistente entre las dos familias. Pero **sólo cubre el 54,1 % del
negocio**, y las dos mitades que faltan tienen cada una su remedio: la receta de
`stocks.articulosdetalle` para el café, y el mapeo de canales para el resto.

**Artículos que se salen por abajo** (con 500 unidades o más):

| artículo | unidades | margen |
|---|---|---|
| MONSTER ENERGY LATA 50CL | 3.093 | **23,2 %** |
| MONSTER ULTRA WHITE LATA 50CL | 3.267 | 30,7 % |
| DONETTES CLASICO | 6.894 | 31,2 % |
| PAN BOCADILLO EMBOLSADO | 4.222 | 32,7 % |

Sólo uno de 128 artículos baja del 30 %, así que no hay un problema general de precios: hay un
problema con Monster, que se vende a 2,00 € con un coste de 1,36 €. Revisar ese precio, o esa
compra, vale unos 1.000 € al mes.

## 4. Dos defectos de dato en las ventas

**Precios negativos.** 158 filas, 3.174 unidades, **−1.974,64 €** en 158 máquinas distintas. Son
devoluciones o anulaciones que la telemetría manda como importe negativo. El importe total ya las
incluye y está bien, pero cualquier cálculo de precio mínimo o de precio medio por unidad hay que
hacerlo filtrando `precio > 0`, o salen disparates como un artículo «vendido» a −4,90 €.

**Dispersión de precios enorme.** De los 146 artículos presentes en 50 máquinas o más, **131 se
venden con más de 1 € de diferencia** entre la máquina más barata y la más cara:

| artículo | mínimo | mediana | máximo |
|---|---|---|---|
| AGUA FONT VELLA PET 50CL | 0,08 € | 0,60 € | 2,95 € |
| MONSTER ENERGY LATA 50CL | 0,28 € | 2,00 € | 3,00 € |
| AGUA LANJARON PET 0,5L | 0,40 € | 0,80 € | 2,90 € |

Parte es política comercial legítima —cada cliente tiene su tarifa— pero un agua a 0,08 € en una
máquina y a 2,95 € en otra no se explica con eso. Es un candidato claro para un indicador de
precio fuera de rango por artículo, comparando cada máquina contra la mediana de su cliente.

---

## 5. El horario: sólo 49 centros son de verdad de 24 horas

Con mínimo y máximo, 159 de 287 centros parecían de 24 h. Calculando la ventana como el tramo que
concentra el 90 % del importe (percentil 5 al 95, sólo laborables), la foto cambia por completo:

| tipo de centro | ventana | centros |
|---|---|---|
| oficina / industria | ≤ 11 h | **123** |
| intermedio | 12–19 h | 115 |
| 24 horas real | ≥ 20 h | **49** |

| centro | ventana real |
|---|---|
| AIRBUS GETAFE | **6 – 17** |
| AIRBUS TABLADA | 6 – 17 |
| AIRBUS SAN PABLO SUR | 6 – 19 |
| AIRBUS ILLESCAS | 3 – 19 |
| ALHAMBRA | 9 – 19 |
| Hospital La Paz | 5 – 21 |
| Can Ruti | 2 – 21 |
| Hospital Príncipe de Asturias | 3 – 22 |
| Serunion - Hospital Clínico | 2 – 22 |

AIRBUS GETAFE registra ventas de 0 a 23 h, pero el 90 % de su dinero entra entre las 6 y las 17.
Ese es el horario que tiene que usar la alarma.

**Y el fin de semana: 52 centros cierran del todo y 119 hacen menos del 5 % de lo que hacen en
laborable.** Una alarma de falta de ventas sin calendario semanal por centro dispararía sobre 119
centros cada sábado.

## 6. La curva del día, con el mes entero

En laborable, las horas 9, 10 y 11 concentran el 26 % del importe, con el pico a las 10 (88.429 €
en el mes). De 22:00 a 05:00 entra el 6 %. El bajón de mediodía existe pero es suave: de 85.770 €
a las 11 a 70.231 € a las 12.

Con esto, la regla de reposición se puede afinar: **una máquina de oficina que no ha vendido nada
a las 11 de la mañana de un laborable es una incidencia**, no una máquina tranquila. Ese es el
umbral que la telemetría permite vigilar y que ninguna visita detecta hasta que se pasa por allí.
