# Qué da de sí el dato (mayo–agosto 2026)

Análisis sobre las tablas consolidadas: 1.124.774 líneas de venta, 778.370,65 €,
549 máquinas, 370 artículos, 7 centros. Reproducible con `python3 scripts/analisis.py`.

## 1. El día de la semana manda

| | media por día |
|---|---:|
| martes | 9.568 € |
| miércoles | 9.365 € |
| lunes | 8.976 € |
| jueves | 8.836 € |
| viernes | 6.922 € |
| sábado | 633 € |
| domingo | 485 € |

El viernes vende un **28% menos** que el martes, y el fin de semana es un 6% de un día
laborable. Consecuencia para el cuadro de mando: **nunca comparar contra "ayer"**, sino
contra el mismo día de la semana anterior. Un panel que enseñe "viernes vs jueves" va a
dar una falsa alarma todas las semanas.

## 2. El surtido está muy concentrado

- Top 10 artículos = **43,5%** de la venta. Top 50 = 79,1%.
- Líder absoluto: Café con Leche Normal (94.756 €), seguido de Coca Cola Zero (55.428 €).
- **141 de los 370 artículos no llegan a 100 €** en cuatro meses. Ocupan canal, generan
  caducidades y obligan a reponer referencias que casi nadie compra.

## 3. Las máquinas son muy desiguales

- Mediana: **14,1 € por día laborable**. El 20% mejor concentra el **46%** de la venta.
- La mejor (24SE1983, comedor de San Pablo Sur) hace **219,7 €/día**: quince veces la mediana.
- La cola son máquinas de menos de 1 €/día, con totales de 4 a 40 € en todo el periodo.

## 4. Máquinas mudas: el hallazgo más accionable

Una máquina que no vende nada durante varios días laborables seguidos está averiada,
vacía o desenchufada, y nadie se entera hasta que alguien pasa por allí.

Mayo–julio (agosto se excluye por el parón de verano):

- **61 máquinas** con al menos un parón de 3+ días laborables consecutivos.
- **594 días laborables mudos** acumulados.
- Peores casos: 24CE5040 (CBC) 22 días seguidos, 18CE1686 (Getafe) 5 parones y 35 días
  mudos, 25FE1782 (San Pablo Sur) 19 días.

Esto es una alerta automática de primer orden, y no necesita telemetría: sale de comparar
la venta diaria de cada máquina con su propio comportamiento normal.

## 5. Las rutas no están equilibradas

16.017 visitas, 15 rutas, 17 reponedores, 547 máquinas visitadas.

- El rendimiento por visita va de **0,2 €** a **617 €**.
- **6 máquinas recibieron 55 visitas sin vender absolutamente nada** en el periodo.
- En el extremo opuesto, 24CE4829 (San Pablo Sur) hace 3.239 € con solo 8 visitas: o está
  infra-atendida o se queda vacía entre visitas.

## 6. Las incidencias no son lo que parecen

De 785 incidencias, **la mitad no son averías**:

| Categoría | Nº |
|---|---:|
| Atención al cliente | 390 |
| Averías técnicas | 310 |
| Solicitudes cliente | 48 |
| Devolución dinero | 21 |
| Obsoletas | 16 |

**276 son devoluciones de dinero** (transferencia 100, tarjeta empleado 99, tarjeta de
crédito 39, in situ 38). Eso es un indicador de calidad y de medios de pago, no de avería,
y merece su propio panel. Entre las técnicas dominan "distribuidor fuera de servicio"
(66 snack/bebida + 59 café) y "calidad no conforme" en café (29).

Por modelo de máquina: ARIA L EVO MASTER (183), OPERA ONE 2C (170), LEI 600 TOUCH (98).

## 7. El tiempo de resolución, corregido

Al conocer el SQL del informe 8 (ver `04-informes-vencloud.md`) se aclara qué significan
las horas de cierre, y la conclusión cambia respecto a la primera lectura.

`fecha_cierre` no es un campo, es un cálculo con tres salidas: el evento de cierre del log
cuando existe —y entonces trae hora real—, `t.fechafin` cuando la tarea está finalizada sin
ese evento —y entonces es una fecha sin hora, que se pinta como 00:00—, y `01/01/1900`
cuando la tarea **sigue abierta**.

De las 785 incidencias:

| | |
|---|---:|
| Cerradas con hora exacta | 339 |
| Cerradas con fecha pero sin hora | 404 |
| Todavía abiertas (01/01/1900) | 42 |

Así que no es que el dato esté mal: de las 743 cerradas conocemos el día en todas y la
hora en 339.

- Con hora exacta: **mediana 22 h**, 53% en menos de 24 h.
- Con solo fecha: **62,9% se cierran el mismo día**, 80,7% al día siguiente.
- Conjunto completo, en días: **mediana 0,07 días**, 58% el mismo día, **p90 de 7 días**.

El servicio es bastante mejor de lo que parecía. Lo que sí conviene vigilar es esa cola:
un 9% tarda más de una semana, y son las que hay que mirar una a una.

Desde ahora esto no hay que calcularlo: el informe 8 trae una columna `diferencia` con el
intervalo exacto.

## 8. Lo que cuestan las averías, medido de verdad

Cruzando la ventana de cada incidencia con la venta esperada de esa máquina (su mediana
diaria): **6.225 € de venta por debajo de lo normal** durante las incidencias, un 0,80%
del periodo, en 369 casos. Es una cifra modesta, y encaja: la mayoría de incidencias son
devoluciones, no máquinas paradas. El dinero de verdad está en las máquinas mudas del
punto 4, que en su mayoría **no tienen ninguna incidencia abierta**.

## 9. Preventivos: cobertura buena, conclusión imposible

463 preventivos sobre 463 máquinas distintas — exactamente uno por máquina — que cubren el
83% de las que venden. La comparación "averías en máquinas con preventivo (1,68) vs sin
preventivo (0,04)" **no demuestra nada**: las 92 máquinas sin preventivo son justamente
las de venta marginal, que ni se usan ni se rompen. Para evaluar el preventivo haría falta
comparar la misma máquina antes y después, con un histórico más largo.

## 10. El mismo artículo a precios muy distintos

121 artículos tienen precio distinto según el centro. Algunos casos son llamativos:

| Artículo | Diferencia | Ejemplo |
|---|---:|---|
| PAN AIRBUS | 1,74 € | CBC 2,05 € vs Illescas 0,31 € |
| AGUA FONT VELLA 500ml | 1,54 € | San Pablo Sur 2,05 € vs Illescas 1,22 € |
| COCA COLA ZERO LATA33 | 1,28 € | San Pablo Norte 2,05 € vs San Pablo Sur 1,50 € |

Puede ser tarifa negociada por centro (legítimo) o un error de tarifa que está costando
dinero. Hay que contrastarlo con los contratos antes de sacar conclusiones. Aparece además
un artículo literalmente llamado **"Unknown"**: un problema de calidad de dato a revisar.

## Lo que no se puede analizar con lo que hay

| Falta | Para qué serviría | Dónde está |
|---|---|---|
| Hora de la venta | Picos de consumo, dimensionar reposición y turnos | En VenCloud; solo llegó en el fichero de agosto |
| Medio de pago | Cuadrar las 276 devoluciones, efectivo vs tarjeta vs app | VenCloud |
| Planograma y capacidad | Rotura de stock real y venta perdida por canal vacío | VenCloud / módulo de planogramas |
| Coste de compra | Margen por artículo y por máquina, no solo facturación | Compras |
| Censo completo | Modelo, capacidad, fecha de instalación, ubicación de las 549 máquinas | VenCloud (hoy solo tenemos las 125 de San Pablo) |
| Calendario laboral por centro | Distinguir un parón real de un festivo local | Airbus |
| Telemetría | Alarmas de máquina, temperaturas, estado de canales | Sistemas de telemetría integrados en VenCloud |
