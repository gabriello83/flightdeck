# Tanda B · El dinero: dos informes que lo cambian todo y dos tablas más vacías

B3 y B4 lanzados sobre agosto, B5 y B6 sobre el 01–25 de septiembre. B1 y B2 no se lanzaron porque
la sonda ya había demostrado que `recogidasbolsasrec` está vacía.

---

## 1. `fecha` no es el período contable. Y esto afecta a toda la carga nocturna

B3 filtrado por `r.fecha` entre el 01 y el 31 de agosto devuelve **57.452 filas**. De ellas:

| período contable (`anho`/`mes`) | filas |
|---|---:|
| **julio de 2026** | **52.161** |
| agosto de 2026 | 5.291 |

**Nueve de cada diez filas escritas en agosto pertenecen a julio.** Es exactamente lo que cabe
esperar del circuito que describe operaciones: Loomis cuenta, manda el fichero y se importa
semanas después.

De ahí salen tres reglas, y las tres son de diseño:

1. **La extracción incremental va por `fecha`**, la fecha de escritura de la fila. Es lo único que
   garantiza que la carga nocturna no se deje nada. Y como cada fila lleva su `id`, es idempotente
   aunque toque períodos viejos.
2. **Los informes de negocio agrupan por `anho` y `mes`**, nunca por `fecha`.
3. **Un mes no está cerrado hasta más o menos el final del mes siguiente.** El cuadro de mando
   tiene que enseñar el último mes como provisional, o dará cifras que bajan sin motivo.

Esto explica del todo la rareza que vimos antes: la sonda daba 6.398 registros para septiembre
contra 48.443 de agosto. No era una caída, era que septiembre aún no se había escrito.

## 2. Las delegaciones, ya con nombre, y el efectivo ciego

Sobre las 57.452 filas —que son básicamente el período de julio—:

| delegación | efectivo | total | **sin telemetría** | % ciego |
|---|---:|---:|---:|---:|
| Madrid - Leganés | 117.672,08 € | 309.977,27 € | **47.810,64 €** | 40,6 % |
| Levante - Murcia | 69.577,89 € | 114.260,90 € | **38.377,55 €** | **55,2 %** |
| Andalucía - Sevilla | 49.734,06 € | 115.300,96 € | 21.702,80 € | 43,6 % |
| Andalucía - La Línea | 13.008,30 € | 13.008,30 € | 13.008,30 € | **100 %** |
| Cataluña - Cornellà | 65.540,49 € | 226.231,28 € | 11.478,31 € | 17,5 % |
| Levante - Valencia | 17.092,82 € | 44.889,83 € | 5.182,21 € | 30,3 % |
| Cataluña - Amazon (Girona) | 4.599,31 € | 4.599,31 € | 4.559,11 € | **99,1 %** |
| Norte - Cantabria | 15.312,28 € | 20.483,00 € | 4.247,06 € | 27,7 % |
| Madrid - Hospital La Paz | 25.513,29 € | 80.158,12 € | 688,10 € | 2,7 % |
| Norte - Bilbao | 33.633,70 € | 65.049,26 € | 0,00 € | 0 % |
| Andalucía - Cádiz | 4.031,70 € | 16.900,05 € | 0,00 € | 0 % |
| **TOTAL** | **511.886,16 €** | **1.231.941,99 €** | **152.676,26 €** | **29,8 %** |

El 29,8 % confirma el 28,6 % que salió de agosto por otro camino. Y hay dos lecturas nuevas:

**Madrid-Leganés mueve 47.810 € ciegos, la mayor cifra absoluta del país** — y es la misma
delegación que tiene el 1,1 % de cumplimiento de inventario. Dos controles distintos apuntando al
mismo sitio.

**Levante-Murcia va al 55,2 %**, y eso cierra un círculo: es la delegación de Consum, donde
contamos que 54 de 58 máquinas no tienen telemetría. Lo que vimos en un cliente concreto hace
semanas era la foto de toda la delegación.

## 3. B4 cuadra con B3, y da el desglose fiscal

77.991 líneas sobre las 57.452 recaudaciones. Y la suma cuadra: **1.231.940,74 € contra los
1.231.941,99 € de la cabecera, 1,25 € de redondeo**. Las dos tablas son consistentes.

| tipo | % IVA | líneas | base | cuota | con IVA | % del total |
|---|---:|---:|---:|---:|---:|---:|
| Normal | 21 % | 15.552 | 186.578,27 € | 39.181,44 € | 225.759,70 € | 18,3 % |
| **Reducido** | **10 %** | 55.818 | 882.205,45 € | 88.220,54 € | **970.426,00 €** | **78,8 %** |
| Super reducido | 4 % | 6.621 | 34.379,85 € | 1.375,19 € | 35.755,04 € | 2,9 % |
| **TOTAL** | | 77.991 | 1.103.163,56 € | **128.777,17 €** | 1.231.940,74 € | |

Casi cuatro de cada cinco euros van al 10 %. El campo `codigo` viene vacío en las 77.991 líneas, y
`porcentaje` es el reparto del IVA dentro de cada recaudación: 40.423 líneas al 100 %, o sea
recaudaciones con un solo tipo.

## 4. B5 y B6: vacías

| informe | tabla | filas |
|---|---|---:|
| B5 · BANCO | `vending.pdvstransbancariasdetalles` | **0** |
| B6 · CASHLESS | `vending.partesvisitaauditcashlessgroups` | **0** |

B5 dolía porque era la remesa bancaria transacción a transacción, con comisión e incidencia: el
contraste de los 720.055,83 € de pago bancario. Pero el dato está igualmente en B3 agregado por
punto de venta y día, que para el cuadro de mando llega.

B6 era el detalle de promociones, gratuitos y recargas del cashless. Sin él, la tarjeta privada
—que son 227.909,31 € en septiembre, el 45,4 % de la venta del A11— sólo se ve como importe, sin
saber cuánto es prepago, cuánto promoción y cuánto gratuito.

## Recuento de tablas muertas

Van **ocho** de las lanzadas hasta ahora:

`partesvisitainvcanales` · `partesvisitacontajes` · `partesvisitacontajesdetalle` ·
`partesvisitaincidencias` · `recogidasbolsasrec` · `recogidasbolsasrecdetalles` ·
`pdvstransbancariasdetalles` · `partesvisitaauditcashlessgroups`

No es un problema del modelo de VenCloud, es que la casa usa una parte de él. Pero sólo se
descubre lanzando, y por eso la Lambda no se puede programar contra el catálogo teórico.

## Siguiente

B3 relanzado con **01/09/2026 – 25/09/2026** para tener el dinero en la misma ventana que la tanda
A, y con eso queda cerrado el bloque del dinero.

---

# B3 sobre septiembre: la conciliación cierra exacta, y aparece el ciclo de escritura

Relanzado con `fecha` del 01 al 25 de septiembre: **47.936 filas**, la última escrita el 22/09.

| período contable | filas | efectivo | total |
|---|---:|---:|---:|
| agosto de 2026 | 43.152 | 109.062,84 € | 646.342,92 € |
| septiembre de 2026 | 4.784 | 289.273,17 € | 289.273,17 € |

## La conciliación a tres bandas, al céntimo

Juntando las dos ventanas de escritura, el período contable de agosto queda completo:

| | filas | efectivo | total |
|---|---:|---:|---:|
| Escrito en agosto | 5.291 | 318.940,57 € | 318.940,57 € |
| Escrito en septiembre | 43.152 | 109.062,84 € | 646.342,92 € |
| **Suma** | **48.443** | **428.003,41 €** | **965.283,49 €** |
| **R1, filtrado por `anho`/`mes`** | **48.443** | **428.003,41 €** | **965.283,49 €** |

**Coincide exactamente en las tres cifras.** Dos consultas distintas, filtros distintos, mismo
resultado. El modelo del período contable está entendido y `prefacrecauda` es una fuente fiable.

## Y sale el ciclo de escritura, que es lo importante

Mira la columna del total frente a la del efectivo:

- Lo escrito **dentro del mes** es **todo efectivo**: 318.940,57 € de efectivo y 318.940,57 € de
  total. Cero banco.
- Lo escrito **al mes siguiente** aporta 109.062,84 € de efectivo y 646.342,92 € de total, o sea
  **537.280,08 € de banco** — que es, al céntimo, el `imppagobancario` de agosto que dio R1.

**El cobro por tarjeta de un mes entero se escribe de golpe al mes siguiente.** Septiembre lo
confirma: sus 4.784 filas escritas hasta el día 22 son 289.273,17 €, todo efectivo, y el banco
llegará en octubre.

### La consecuencia para el cuadro de mando

El mes en curso **siempre se ve un 55 % más pequeño de lo que es**, porque le falta toda la
tarjeta, que es el 55,7 % de la facturación. No es un fallo del dato: es el ciclo.

Así que el cuadro de mando tiene que:

1. **Marcar el mes en curso como provisional**, y decir explícitamente que falta el cobro
   bancario.
2. Para el mes en curso, **usar la telemetría** —que sí ve tarjeta el mismo día— y dejar
   `prefacrecauda` para los meses cerrados.
3. **No comparar nunca un mes en curso contra uno cerrado** sin avisar, o la caída aparente será
   del 55 %.

Esto cierra además, por fin, la discrepancia que llevábamos arrastrando entre los 1.088.439,33 €
de telemetría de septiembre y las cifras oficiales: no eran fuentes contradictorias, es que
miden momentos distintos del mismo ciclo.

## El efectivo ciego, tercera medición

27,4 % en esta ventana, contra el 28,6 % de agosto por `anho`/`mes` y el 29,8 % de la ventana
anterior. Tres mediciones independientes en el mismo entorno: **entre el 27 % y el 30 % del
efectivo se recauda sin dato electrónico**. La cifra es sólida.
