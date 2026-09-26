# Un día de telemetría: 24 de septiembre de 2026

59.547 transacciones, **54.792,25 €**, 1.841 máquinas, 253 centros, 115 clientes, 47 rutas,
375 artículos, 14 delegaciones. Un jueves. Es el primer dato de venta real con hora que
tenemos, y responde de golpe varias preguntas que los informes dejaban abiertas.

## 1. AIRBUS es un tercio de la compañía

| centro | líneas | importe | máquinas | % venta sin artículo |
|---|---|---|---|---|
| AIRBUS GETAFE | 8.103 | 7.353,79 € | 223 | 8,6 % |
| AIRBUS SAN PABLO SUR | 3.151 | 3.269,01 € | 112 | 19,8 % |
| AIRBUS TABLADA | 1.613 | 1.662,35 € | 45 | 19,5 % |
| AIRBUS CBC | 1.326 | 1.373,30 € | 40 | 19,9 % |
| AIRBUS ILLESCAS | 1.493 | 1.286,76 € | 49 | 11,7 % |
| AIRBUS ITC | 1.017 | 1.056,41 € | 10 | 5,0 % |
| AIRBUS ALBACETE | 1.044 | 808,89 € | 26 | 3,5 % |
| AIRBUS SAN PABLO NORTE | 421 | 417,71 € | 22 | 19,7 % |
| AIRBUS ALBACETE (Parque Científico) | 51 | 0,00 € | 2 | 0 % |
| **total** | **18.219** | **17.228,22 €** | **529** | |

**31,4 % de toda la venta telemétrica de la compañía en un solo día**, con 529 máquinas.
AIRBUS GETAFE por sí solo es el primer centro del país, por delante de Can Ruti y La Paz.

Y AIRBUS opera distinto al resto:

| medio de pago | AIRBUS | global |
|---|---|---|
| Prepago | **57,3 %** | 28,6 % |
| Tarjeta crédito | 38,4 % | 46,3 % |
| Efectivo | **3,2 %** | 24,0 % |

Sólo un 3,2 % de efectivo. En AIRBUS la recaudación casi no es un problema operativo; lo que
importa es la disponibilidad y el planograma. La regla de «recaudar mínimo una vez al mes, y más
si hay más de 100 € en bolsa» apenas aplica ahí, y sí aplica con fuerza en el resto de la red.
La cabina no puede usar el mismo umbral para todos.

El Parque Científico de Albacete vende 51 líneas a 0,00 €: es vending gratuito.

## 2. El café no tiene coste, y es el 37 % de las líneas

| clase de artículo | líneas | importe | `coste` relleno | `puc` relleno |
|---|---|---|---|---|
| 1 · bebida caliente preparada | 20.948 | 10.934,98 € | **0 %** | **0 %** |
| 2 · bebida fría envasada | 15.199 | 14.850,32 € | 100 % | 100 % |
| 3 · snack | 11.510 | 13.280,49 € | 94,3 % | 99,3 % |
| sin artículo | 11.890 | 15.726,46 € | 0 % | 0 % |

Esto explica de una vez por qué `stocks.articulos.puc` salía al 94 % y aun así media venta se
queda sin coste. **El café no se compra, se fabrica en la máquina.** Los artículos R01–R29 (café
con leche normal, cortado, cappuccino, premium, descafeinado…) no tienen precio de compra porque
su coste es la suma de su receta: café, leche, azúcar, vaso, paletina.

Los doce artículos sin coste más vendidos del día son todos café:

| código | artículo | líneas | importe |
|---|---|---|---|
| R04 | Café con leche normal | 4.837 | 2.241,88 € |
| R03 | Café cortado normal | 2.205 | 998,67 € |
| R12 | Café con leche premium | 1.626 | 944,61 € |
| R02 | Café largo normal | 1.613 | 767,53 € |
| R05 | Cappuccino normal | 1.180 | 598,93 € |

Conclusión operativa: **el margen del café sale de `stocks.articulosdetalle`** (receta:
`tipomateriaprima`, `tipounidad`, `cantunidad`) multiplicado por el `puc` de cada materia prima.
Sin esa tabla, el 21 % del importe del día no tiene coste y cualquier margen global está inflado.

Donde sí hay coste, `t.coste` y `a.puc` coinciden: 23.017 de 26.046 líneas iguales dentro de un
céntimo. O sea, el coste de la telemetría **es** el último precio de compra. No son dos fuentes,
son la misma.

## 3. Un cuarto del dinero no sabe qué producto es

11.890 líneas, **15.726,46 € — el 28,7 % de la venta del día — no tienen artículo asociado.** Son
canales sin mapear: 2.628 de ellas con `canal = -1`. Afectan a 1.155 máquinas, y **176 máquinas
venden el 100 % de su importe sin artículo identificado**; 363 máquinas pasan del 50 %.

Su precio medio es 1,49 €, el más alto de todas las categorías, así que no son residuales: es
probablemente producto de máquina cara o combinada.

Esto es lo que más limita hoy la cabina. No se puede hacer un Pareto de producto fiable, ni
calcular rotura de stock, ni margen por artículo, sobre un cuarto del dinero. Y no es un problema
de la consulta: es planograma sin mapear en VenCloud. Es una acción concreta y medible: 176
máquinas a revisar, por orden de importe.

## 4. La curva del día

|franja|comportamiento|
|---|---|
| 06:00–11:00 | subida continua hasta el pico de las **11:00** (5.262 líneas, 5.086 €) |
| 12:00–13:00 | bajón claro (hora de comer) |
| 14:00 | repunte (3.797 líneas) |
| 15:00–19:00 | meseta descendente |
| 22:00–05:00 | **3.643 líneas y 3.164 €** de madrugada |

La madrugada no es ruido: es el 6 % del importe, y sale de hospitales e industria a turnos. Una
alarma de «máquina sin ventas» que no distinga el perfil horario del centro daría falsos
positivos en toda la red diurna y se perdería los fallos reales de los centros 24 h.
`configuracion.criteriosalarmasnovtas` ya tiene `horadesde1`/`horahasta1`, `horadesde2`/
`horahasta2` y los siete días de la semana justo para eso. Está sin usar.

## 5. Concentración y silencio

- El **10 % de las máquinas hace el 35,7 %** del importe.
- **317 máquinas vendieron menos de 5 €** en todo el día.
- **1.029 máquinas tienen dispositivo de telemetría y no vendieron nada** ese día (1.841 con
  venta de las 2.870 con dispositivo). Parte será cierre de centro, parte máquina vacía o
  averiada. Distinguirlo exige cruzar con el calendario del centro, y es exactamente la alarma
  que hay que construir.
- Toda la telemetría del día es `tipotelemetria = 40`: **Nayax, sin excepción**.

## 6. Un número que no cuadra

Un jueves normal hace 52.389 €. Un mes laborable son ~22 días, más fines de semana reducidos:
del orden de 1,2–1,3 M€. El informe 68 daba **881.793,77 €** para septiembre.

No sé cuál de los dos es el bueno y no conviene suponerlo. Hay que reconciliarlo antes de poner
una cifra de ingresos en la cabina: puede que el informe 68 filtre por algo, que excluya
prepago, o que el 24 de septiembre fuera un día alto. La consulta de resumen diario sobre un mes
entero lo resuelve en una ejecución.

## 7. Correcciones al SQL

1. **El Orden de los parámetros empieza en 0**, no en 1. `{0}` es Orden 0 y `{1}` es Orden 1.
2. **El margen estaba mal calculado.** Usé `coalesce(t.coste, a.puc, 0)`, pero `t.coste` no llega
   como nulo: llega como **0**. `coalesce` no lo sustituye y el margen salía inflado al 77 %. Lo
   correcto es:

```sql
  case when coalesce(t.coste,0) > 0 then t.coste else coalesce(a.puc,0) end as coste_est,
  (t.precio - case when coalesce(t.coste,0) > 0 then t.coste else coalesce(a.puc,0) end) as margen,
```

   Aun así quedan 29.974 líneas sin coste ni puc, que son el café y los canales sin mapear. El
   margen real del día no se puede cerrar hasta tener la receta.


---

## 8. Corrección: 2.940 líneas que se me quedaron fuera

Al cargar el fichero descarté por error las filas sin matrícula. El día no son 56.607
transacciones y 52.389,11 €, sino **59.547 y 54.792,25 €**. Todas las cifras de arriba están ya
recalculadas sobre el día completo.

Y lo descartado resulta ser un hallazgo: **2.940 transacciones, 2.403,14 €, el 4,4 % del día,
llegan de 118 dispositivos de telemetría que no corresponden a ninguna máquina de
`recursos.maquinas`.** No tienen matrícula, ni centro, ni ruta, ni artículo: sólo dispositivo,
importe y medio de pago. Es dinero real entrando —1.288 cobros en efectivo, 1.172 con tarjeta—
desde equipos que el maestro no reconoce.

A escala de mes son del orden de 60.000 €. Puede ser máquina dada de baja con el dispositivo aún
activo, dispositivo reasignado sin actualizar, o alta pendiente. Sea lo que sea, es una lista
corta y cerrada: 118 `devicecode` que cruzar con `telemetry.telemetrydevices` y con
`recursos.maquinas.telemetriadispositivo` para ver a quién pertenecen.

La cabina tiene que enseñar ese importe en algún sitio en vez de perderlo en un join, porque un
cuadro de mando que se come el 4,4 % de los ingresos sin avisar es peor que no tenerlo.
