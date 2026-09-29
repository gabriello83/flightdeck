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

---

# Qué es `auditmonbil`, y por qué no se puede sumar en bruto

**AUDIT MONederos y BILleteros.** Es la lectura electrónica del monedero y del billetero de la
máquina: el «dato electrónico» del circuito. Cuando el reponedor conecta, o cuando la telemetría
lo manda sola, la máquina vuelca sus contadores y esto es lo que queda guardado. Sí, R2 es el
informe correcto.

Una fila por denominación y lectura, y para cada una tres pares de contadores:

| columna | qué cuenta |
|---|---|
| `aceptadas` / `aceptadasa` | monedas que ha tragado la máquina |
| `encajon` / `encajona` | las que han caído al cajón — **esto es lo que va a la bolsa** |
| `entubos` / `entubosa` | las que se han quedado en los tubos para dar cambio |

Sin sufijo es **lo movido desde la última lectura**; con `a`, **el acumulado de la vida de la
máquina**. Y el modelo se verifica solo, porque los acumulados cuadran fila a fila:

```
aceptadasa = encajona + entubosa
0,50 €:  14.416  =   4.431  +  9.985     ✓
0,20 €:  17.394  =   4.992  + 12.402     ✓
```

Lo que tragó = lo que fue al cajón + lo que se quedó en los tubos. **El importe teórico de la
bolsa es `suma(valor × encajon)`**.

## El extracto del 01 al 25 de septiembre

167.374 filas, 26.428 partes. Todo monedas, ni un billete en 25 días.

Y aquí está el problema: **sumado en bruto da 6.848.038 €**, contra los **253.573,19 €** de
efectivo que dice la telemetría en esas mismas fechas. Veintisiete veces más.

No es un error del modelo, son lecturas corruptas. El desglose por denominación lo enseña:

| denominación | filas | € en cajón | máximo de monedas en **una** lectura |
|---:|---:|---:|---:|
| 2,00 | 26.202 | 4.377.724 | **723.546** |
| 0,50 | 26.353 | 829.306 | 45.635 |
| 1,00 | 26.277 | 92.962 | 30.637 |
| 0,20 | 26.427 | −49.473 | 2.600 |
| 0,10 | 26.351 | −33.252 | 3.499 |

723.546 monedas de 2 € en una sola lectura son 1,4 millones de euros en un cajón. Es un contador
que ha dado la vuelta o un dispositivo que devuelve basura. Y no se arregla con un tope: probando
de 100 a 2.000 monedas por lectura el total salta de 120.770 € a 758.145 € sin acercarse nunca a
la cifra real.

También hay `valor` que no son monedas — `12,75` en 4.329 filas, y `0,04`, `0,39`, `0,40`, `0,45`,
`2,55` —, pero esas son inofensivas para el dinero: todas traen cajón a cero.

## La conclusión, que cambia cómo se usa la tabla

**Los contadores delta no se pueden agregar a nivel de parque.** Sirven para lo que están: el
importe teórico **de una bolsa concreta**, comparado con lo que Loomis contó para esa misma bolsa.
Ahí un contador corrupto se ve como una diferencia enorme en una máquina —que es justo una alarma
que queremos— en vez de contaminar un total nacional.

De los 26.194 partes, sólo **7.209 traen cajón mayor que cero**, con mediana de 5,00 €: son las
lecturas automáticas diarias, incrementos pequeños. Las que interesan son las de recaudación.

## R3 · El informe que hace falta

Una fila por visita con recaudación, con su teórico. Pequeño, directo, y es la mitad izquierda del
control. La agregación va fuera de la subconsulta sobre nombres sin prefijo, que es la única forma
que traga el motor cuando el informe lleva parámetros.

`recaudacion` es **entero**, no booleano — el mismo tropiezo que `auditgenalarmas`.

```sql
select
  parte_id, matricula, centro, ruta, empleado, fecha, cod_bolsa,
  sum(eur)     as teorico_cajon,
  sum(monedas) as num_monedas
from (
  select
    p.id                     as parte_id,
    m.codigo                 as matricula,
    cen.denomina             as centro,
    ru.denomina              as ruta,
    emp.nombre               as empleado,
    cast(p.fechaini as text) as fecha,
    p.codbolsa               as cod_bolsa,
    a.valor * a.encajon      as eur,
    a.encajon                as monedas
  from vending.partesvisita p
  join vending.partesvisitaauditmonbil a  on a.partevisitaid = p.id
  left join recursos.maquinas m           on m.id  = p.maquinaid
  left join comercial.clientescentros cen on cen.id = p.clientecentroid
  left join vending.rutas ru              on ru.id  = p.rutaid
  left join recursos.empleados emp        on emp.id = p.empleadoid
  where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
    and coalesce(p.recaudacion,0) <> 0
    and coalesce(p.empleadoid,0) <> 0
) x
group by parte_id, matricula, centro, ruta, empleado, fecha, cod_bolsa
order by fecha
```

Dos parámetros de fecha, 01/09 y 25/09. Deberían salir unas 5.500 filas, una por bolsa.

## Nota: `cal_haydifprecios` no es una alarma

Lo señalé como posible pista de precios mal puestos. No lo es: viene a `true` en 3.282 de los
3.504 partes del 25/09, **incluidos los automáticos**. Es una marca de configuración —que la
máquina tiene precios distintos por medio de pago— y no una discrepancia. Descartado.

---

# R3, del 01 al 25 de septiembre: el dato electrónico no está donde tiene que estar

El informe devuelve **503 filas**. Debería haber devuelto alrededor de **5.600**.

El cálculo del denominador, por dos caminos que coinciden en el orden de magnitud:

- El 25/09, día suelto y medido: **340 visitas con recaudación**. Por 21 días laborables ≈ 7.100.
- `prefacrecauda` de agosto, `critcalculo = 3`: **5.665 actos de recaudar** en el mes ≈ 270 al día
  laborable ≈ 5.600 en 21 días.

O sea que **sólo entre el 7 % y el 9 % de las recaudaciones tiene lectura electrónica de la
máquina**. Y no está repartido: las 503 salen de **183 máquinas, 33 rutas y 34 empleados**, de un
parque de más de mil máquinas y 58 rutas al día.

Esto es mucho peor que el 28,6 % de efectivo sin telemetría del apartado 2. Aquello eran puntos de
venta sin dispositivo. Esto son máquinas **que sí tienen con qué leer** y aun así la bolsa se cierra
sin lectura.

## Y de las 503, la mayoría tampoco vale

| diagnóstico | bolsas | % |
|---|---:|---:|
| Cajón a cero | 167 | 33,2 % |
| **Plausible** | **204** | **40,6 %** |
| Importe inverosímil, menos de 5 € | 96 | 19,1 % |
| Lectura imposible, más de 1.000 € | 29 | 5,8 % |
| Contador negativo | 7 | 1,4 % |

Mediana de 4,00 €. Quitando los 36 extremos, las 467 bolsas restantes suman **6.993,62 €** — una
media de 14,98 € por bolsa. Cuando la recaudación real de un mes son 428.003 €.

Los casos extremos se explican solos y son de dispositivo, no de modelo:

| máquina | centro | fecha | teórico | monedas |
|---|---|---|---:|---:|
| 22SE1837 | UNIVERSIDAD LA SALLE | 23/09 | **1.428.012,65 €** | 686.343 |
| 16SE1280 | TELEVISIÓ DE CATALUNYA | siete fechas | 6.507 → 6.648 € | ~9.000 |
| 22CE4672 | TELEVISIÓ DE CATALUNYA | varias | **−5.370,50 €** | −5.922 |

La 16SE1280 es el caso más didáctico: repite ~6.500 € en cada recaudación y va subiendo poco a
poco. Eso no es una bolsa, **es el contador acumulado que nunca se pone a cero**. Su `encajon` se
comporta como un `encajona`.

## Lo que esto significa para el proyecto

El control que describe operaciones —contrastar la bolsa contra el dato electrónico— **hoy no se
puede ejercer**, y no por falta de informes. Se puede ejercer sobre 204 bolsas de unas 5.600.

Son tres problemas distintos y cada uno tiene dueño distinto:

1. **No se lee al recaudar.** 91 de cada 100 bolsas se cierran sin volcar la máquina. Es
   procedimiento de reponedor.
2. **Hay dispositivos que devuelven basura.** Contadores que no se resetean, que dan la vuelta o
   que van en negativo. Es mantenimiento técnico, máquina a máquina.
3. **504 puntos de venta no tienen telemetría**, 122.327 € de efectivo al mes. Es inversión.

El cuadro de mando puede medir los tres y ponerles nombre, ruta y delegación. Lo que no puede es
inventarse el dato que no se tomó.

## Entregable

[`carga/audit_recaudacion_septiembre.xlsx`](../carga/audit_recaudacion_septiembre.xlsx): las 503
bolsas con su diagnóstico, el resumen, y la lista de máquinas a revisar ordenada por gravedad de
la lectura.

## Para fijar el denominador sin estimarlo

```sql
select fecha, count(parte_id) as recaudaciones
from (
  select
    substring(cast(p.fechaini as text) from 1 for 10) as fecha,
    p.id as parte_id
  from vending.partesvisita p
  where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
    and coalesce(p.recaudacion,0) <> 0
    and coalesce(p.empleadoid,0) <> 0
) x
group by fecha
order by fecha
```
