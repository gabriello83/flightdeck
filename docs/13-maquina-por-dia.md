# Máquina × día, septiembre 2026

44.724 filas, 2.064 matrículas, 287 centros, 26 días. **1.090.290,50 €.**

Es la tabla base de la cabina: cada fila es una máquina en un día, con su importe, su efectivo,
su primera y última hora de venta. Todo lo que sigue sale de aquí.

## 0. Cuadra con el resumen diario

El resumen daba 1.088.439,33 € y esta tabla 1.090.290,50 €. La diferencia, 1.851,17 € y 1.699
transacciones, está **entera en el 26 de septiembre**: el día seguía en curso entre una
extracción y otra. En los otros 25 días coinciden al céntimo. Las dos consultas miden lo mismo.

## 1. 806 máquinas conectadas que no han vendido nada

Hay 2.870 máquinas con dispositivo de telemetría en el maestro y **2.064 han vendido algo en
septiembre**. Faltan 806: un 28 % del parque conectado, sin un solo euro en 26 días.

Parte serán máquinas en taller, de baja o en almacén cuyo dispositivo sigue contando en el
maestro — el 63,8 % de `telemetriadispositivo` está calculado sobre las 4.498 máquinas, no sólo
sobre las operativas. Hay que cruzarlo con `estado = 1` antes de dar una cifra. Pero aunque la
mitad se explique así, quedan cientos de máquinas instaladas, conectadas y mudas.

## 2. La cola larga no paga las visitas

| tramo | máquinas | % del importe |
|---|---|---|
| top 5 % | 103 | 26,4 % |
| top 10 % | 206 | 39,0 % |
| top 20 % | 412 | 56,4 % |
| top 50 % | 1.032 | 85,9 % |

Y al otro extremo: **399 máquinas facturaron menos de 100 € en todo el mes**, sumando 17.725 €
entre las 399. De ellas, **125 no llegaron a 25 €**. Una máquina que hace 25 € al mes no paga ni
una visita, y hay que visitarla igual.

Esto es lo que la cabina tiene que poner delante cada mes: no el ranking de las mejores, que ya
se sabe, sino **la lista de las que cuestan más de lo que dan**.

## 3. Veintiuna máquinas se han callado

21 máquinas vendían con normalidad y llevan **más de 7 días sin una sola venta**. Entre ellas
dos de AIRBUS GETAFE. Hacían 2.533 € en el mes antes de callarse.

| matrícula | centro | última venta | € antes |
|---|---|---|---|
| 18CE1651 | Hospital de Urduliz | 15/09 | 311,18 |
| 17SE1527 | Hospital Príncipe de Asturias | 16/09 | 283,95 |
| 22SE1845 | Transportes Grupo Caliche Valencia | 14/09 | 263,90 |
| 24SE2152 | **AIRBUS GETAFE** | 10/09 | 257,17 |
| 19SE1667 | I.U.N.A Fundació Puigvert | 15/09 | 250,30 |
| 17FP1494 | **AIRBUS GETAFE** | 09/09 | 112,33 |

Esta es la alarma que se amortiza sola y que se puede construir **hoy**, sin datos nuevos: venta
diaria por matrícula, comparada con su propio histórico. No hace falta ni saber qué producto
lleva ni cuánto cuesta.

## 4. La regla de los 100 € en bolsa, medida

Es la primera vez que se puede poner número a la regla operativa. Ritmo de efectivo por máquina:

| ritmo | máquinas |
|---|---|
| juntan 100 € en menos de 1 semana | 184 |
| juntan 100 € en menos de 15 días | 394 |
| juntan 100 € en menos de un mes | 633 |
| **tardan más de 90 días en juntar 100 €** | **667** |
| no cogen nada de efectivo en todo el mes | 408 |

Las 184 primeras hay que recaudarlas **cada semana**: con la pauta mensual acumulan más de 400 €
en bolsa. Y a las 667 últimas se las visita todos los meses para recoger menos de 35 €.

Dicho en plata: **la misma regla está quedándose corta en 184 máquinas y tirando el viaje en
667.** La frecuencia de recaudación tiene que salir del ritmo de cada máquina, no de un
calendario único. Con esta tabla se calcula sola.

Un matiz honesto: la pauta mensual puede tener razones que no son económicas — control,
cuadre, riesgo de que el dinero se quede parado dentro de la máquina. Los números dicen lo que
cuesta, no si compensa. Esa decisión es vuestra.

Las máquinas con más efectivo acumulado del mes son hospitalarias, no de oficina:

| matrícula | centro | efectivo mes |
|---|---|---|
| 23FE1675 | ALHAMBRA | 3.236,40 € |
| 18SE1529 | Serunion Hospital de León | 2.895,70 € |
| 16CE1298 | Hosp. Virgen Macarena General | 2.816,80 € |
| 17SE1436 | Hospital Príncipe de Asturias | 2.247,90 € |

## 5. AIRBUS en el mes: 270.012,15 €

**El 24,8 % de la compañía, con 542 máquinas.** Menos que el 31,4 % del jueves 24, y la
diferencia es justo la que cabía esperar: AIRBUS es industria y oficina, así que pesa mucho más
en laborable que en el conjunto del mes con sus fines de semana.

| centro | máquinas | importe mes | % efectivo |
|---|---|---|---|
| AIRBUS GETAFE | 228 | 128.281,34 € | 2,1 % |
| AIRBUS SAN PABLO SUR | 114 | 38.248,59 € | 2,8 % |
| AIRBUS ILLESCAS | 50 | 23.655,59 € | 1,9 % |
| AIRBUS TABLADA | 49 | 22.968,71 € | 3,1 % |
| AIRBUS CBC | 40 | 20.143,05 € | 4,0 % |
| AIRBUS ITC | 10 | 16.859,37 € | 1,0 % |
| AIRBUS ALBACETE | 26 | 14.561,02 € | 4,3 % |
| AIRBUS SAN PABLO NORTE | 24 | 5.293,71 € | 4,8 % |
| AIRBUS PUERTO REAL | 1 | 0,77 € | — |
| AIRBUS ALBACETE (Parque Científico) | 2 | 0,00 € (806 transacciones) | — |

Tres cosas que saltan a la vista. **El efectivo en AIRBUS está entre el 1 % y el 4,8 %**, frente
al 23,7 % de la compañía: la recaudación ahí es casi irrelevante y la operación tiene que ir por
disponibilidad y planograma. **AIRBUS ITC hace 16.859 € con 10 máquinas** — 65 € por máquina y
día, el mejor rendimiento del grupo con diferencia. Y **30 de las 542 máquinas de AIRBUS no
llegan a 50 € en el mes**: hay sitio para reubicar sin perder venta.

El Parque Científico de Albacete son 806 transacciones a 0,00 €: vending gratuito, que conviene
marcar como tal para que no ensucie ningún indicador de rendimiento.

## 6. Las ventanas horarias: usar mediana, no extremos

159 de 287 centros registran alguna venta antes de las 2 y después de las 22. Si la alarma de
falta de ventas se construye con el mínimo y el máximo, **más de la mitad de los centros
parecerán de 24 horas** y la alarma no saltará nunca de madrugada.

La mediana cuenta otra cosa: AIRBUS GETAFE tiene ventas de 0 a 23 h, pero su primera hora
**típica** es las 6 y la última las 16. Can Ruti, que sí es hospital de 24 h, tiene mediana de 2
a 21.

Conclusión de diseño: **la ventana operativa de cada centro se calcula por percentiles de esta
tabla, no por mínimo y máximo.** Y se recalcula sola cada mes.

## 7. Delegaciones: rendimiento muy desigual

| delegación | máquinas | importe mes | €/máquina/día | % efectivo |
|---|---|---|---|---|
| Madrid - Leganés | 543 | 277.631,04 € | 19,67 | 14,4 % |
| Cataluña - Cornellà | 409 | 194.174,41 € | 18,26 | 18,8 % |
| Andalucía - Sevilla | 284 | 127.573,63 € | 17,28 | 20,9 % |
| Madrid - Hospital La Paz | 119 | 79.929,57 € | 25,83 | 26,3 % |
| Levante - Murcia | 184 | 77.871,37 € | 16,28 | 29,0 % |
| **Andalucía - Granada** | 30 | 64.273,10 € | **82,40** | 21,0 % |
| Norte - Bilbao | 120 | 64.094,52 € | 20,54 | 47,5 % |
| Cataluña - Tarragona | 95 | 35.748,89 € | 14,47 | 18,5 % |
| Andalucía - Málaga | 70 | 32.245,30 € | 17,72 | 31,6 % |
| Levante - Valencia | 84 | 27.699,32 € | 12,68 | 28,8 % |
| Andalucía - Cádiz | 45 | 23.399,42 € | 20,00 | 10,7 % |
| **Norte - León** | 17 | 16.658,05 € | 37,69 | **75,2 %** |
| Norte - Cantabria | 27 | 13.206,67 € | 18,81 | 47,4 % |
| **Norte - Oviedo** | 34 | 4.092,74 € | **4,63** | 52,0 % |

Dos extremos que piden explicación antes que acción. **Granada hace 82,40 € por máquina y día
con 30 máquinas**, cuatro veces la media: o es un parque excepcional, o hay máquinas de otra
delegación imputadas ahí. Y **Oviedo hace 4,63 €**, la cuarta parte de la media, con 34 máquinas:
a ese ritmo ninguna de las 34 paga su propio servicio.

El porcentaje de efectivo va del 10,7 % de Cádiz al 75,2 % de León. La política de recaudación no
puede ser nacional.

## 8. Un defecto confirmado

`lineas_sin_articulo` sale **0 en las 44.724 filas**, y sabemos por el detalle del día 24 que el
20 % de las líneas no tienen artículo. Confirma lo ya visto: `articuloid` viene a **0**, no a
nulo. Cualquier comprobación de clave ajena en este modelo tiene que ser
`coalesce(campo,0) = 0`, nunca `is null`.
