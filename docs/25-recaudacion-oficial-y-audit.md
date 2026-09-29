# La recaudación oficial y el dato electrónico, con los campos delante

Las dos extracciones de descubrimiento. `facturacion.prefacrecauda` de agosto de 2026 (48.443
filas, 26 columnas) y `vending.partesvisitaauditmonbil` del 25/09 (6.755 filas, 10 columnas).

---

## 1. `prefacrecauda` es la cuenta oficial, y cuadra al céntimo

Columnas: `id, fecha, anho, mes, dia, imprecaudado, cambiocargado, estado, critcalculo,
criteriodesccambio, pdvid, delegacionid, empresacorpcomerid, empresacorpexplotaid, maquinaid,
fechacontable, imppagobancario, imptotalconiva, formapago, tipotelemetria, centrocosteid,
prefacrecaudaresumenid, centrocostepdvid, albaranvtaid, imprecargasbancarias, impdevolreclama`.

**Agosto de 2026, 2.612 puntos de venta, 31 días:**

| | importe | % |
|---|---:|---:|
| `imprecaudado` — efectivo | 428.003,41 € | 44,3 % |
| `imppagobancario` — banco y tarjeta | 537.280,08 € | 55,7 % |
| **`imptotalconiva`** | **965.283,49 €** | 100 % |

Y la identidad es exacta: efectivo + banco = total, con diferencia **0,0000 €**. Esta es la cifra
oficial del mes, y es la referencia contra la que hay que cerrar la discusión abierta entre los
1.088.439,33 € de telemetría de septiembre y los 881.793,77 € del informe 68.

Dos cosas sobre la granularidad: **`maquinaid` viene nulo en las 48.443 filas** —esto va por punto
de venta, no por máquina— y hay una fila por PDV y día.

### `critcalculo` separa el cobro diario del acto de recaudar

| `critcalculo` | filas | efectivo |
|---:|---:|---:|
| 1 | 37.019 | 3.396,95 € |
| 2 | 64 | 7.209,15 € |
| **3** | **5.665** | **393.578,07 €** |
| 4 | 5.695 | 23.819,24 € |

El 1 son las filas diarias de cobro electrónico, casi sin efectivo. **El 3 es el acto de recaudar**:
5.665 en el mes, unos 270 por día laborable, que encaja con los 340 partes con recaudación que
vimos el 25/09. El 92 % del efectivo del mes está ahí.

Para cualquier informe de recaudación, **el filtro es `critcalculo` 2, 3 y 4**; el 1 es cobro, no
recaudación.

## 2. El agujero de control, medido: 122.327 € de efectivo sin dato electrónico

`tipotelemetria` vale 40 (Nayax) o 0 (ninguna).

| | filas | efectivo |
|---|---:|---:|
| Con telemetría | 47.234 | 305.676,06 € |
| **Sin telemetría** | 1.209 | **122.327,35 €** |

**El 28,6 % del efectivo de agosto viene de puntos de venta sin telemetría**, 504 PDVs que no
aparecen nunca con telemetría. Ese dinero entra en bolsa sin importe teórico contra el que
contrastarlo: se cuenta lo que haya y no hay con qué compararlo. Es exactamente el riesgo que
describe operaciones, y ahora tiene número.

Y está muy concentrado:

| delegación (id) | efectivo | sin telemetría | % |
|---:|---:|---:|---:|
| 16 | 15.417,41 € | 15.417,41 € | **100 %** |
| 14 | 4.064,61 € | 4.020,36 € | **98,9 %** |
| 11 | 57.088,10 € | 32.303,16 € | 56,6 % |
| 9 | 44.128,53 € | 21.392,49 € | 48,5 % |
| 12 | 70.422,20 € | 26.377,99 € | 37,5 % |
| 8 | 19.727,97 € | 6.264,41 € | 31,8 % |
| 7 | 49.643,08 € | 8.546,03 € | 17,2 % |
| 10 | 35.594,59 € | 3.262,49 € | 9,2 % |
| 1 y 18 | 31.464,44 € | 0,00 € | 0 % |

Van por `delegacionid` porque el `select *` no trae el nombre; el informe definitivo une con
`general.delegaciones`. **Dos delegaciones recaudan a ciegas el 100 % y el 99 % de su efectivo**, y
la 11 es la que más euros ciegos mueve en términos absolutos.

## 3. `partesvisitaauditmonbil` es el arqueo moneda a moneda

Columnas: `id, tipo, valor, aceptadas, aceptadasa, encajon, encajona, entubos, entubosa,
partevisitaid`.

- `tipo` — **M** moneda, **B** billete. El 25/09 las 6.755 filas son todas M: ni un billete, que
  cuadra con la cabecera.
- `valor` — la denominación.
- Los tres pares son **contadores**: sin sufijo es el movimiento desde la última lectura, y con
  **`a`** el acumulado de la vida de la máquina. Se ve solo: los primeros tienen valores negativos
  (74 filas en `encajon`, 49 en `entubos` — devoluciones y recargas de tubos) y los acumulados no
  tienen ninguno.

**El importe teórico de la bolsa es `suma(valor × encajon)`** por parte. Es el número que permite
controlar lo que Loomis debería contar.

### Dos avisos antes de usarlo

**Hay valores que no son monedas.** `12,75` aparece en 169 filas de 101 máquinas, y también salen
`0,04`, `0,40`, `0,45` y `2,55`. Para calcular efectivo hay que quedarse con las denominaciones
reales de euro o esas filas contaminan el total.

**La cobertura del mismo día es baja.** De las 340 máquinas recaudadas el 25/09, sólo **60 tienen
lectura de audit ese mismo día**. Con un día no se puede concluir que las otras 280 no tengan
lectura nunca — puede haberse leído otro día —, y por eso la medida buena es la del mes. Lo que sí
está medido y no depende de esto son los 122.327 € del punto 2.

## 4. Lo que queda

- Extraer `auditmonbil` del mes de septiembre y medir la cobertura real de la lectura sobre las
  recaudaciones, no sobre un día.
- Escribir el informe de recaudación con los nombres de delegación y el filtro `critcalculo in
  (2,3,4)`.
- Cruzar teórico contra contado por punto de venta y periodo: es el control de recaudación
  terminado.
- Cerrar la conciliación de septiembre contra `imptotalconiva`, que ahora tiene una referencia
  oficial que cuadra sola.
