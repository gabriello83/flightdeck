# La cadena del efectivo, y dónde está cada eslabón

Cómo funciona de verdad, contado por operaciones:

1. En cada visita hay que **reponer, recaudar y leer el dato electrónico** — o que lo mande la
   telemetría.
2. **Los reponedores no recaudan siempre.**
3. Cuando sí se recauda, **tiene que haber dato electrónico**: es lo que dice cuánto dinero
   debería haber en la bolsa.
4. Al final del día el reponedor **verifica que tiene físicamente todas las bolsas**.
5. Una o dos veces por semana **pasa el camión de Loomis**, recoge las bolsas y las cuenta.
6. Loomis manda el fichero de lo contado y **se importa en VenCloud**.

De ahí salen los dos controles que pedía el cuadro de mando, y que no son el mismo:

- **Control de recaudación**: ¿cuadra lo contado con lo que decía el dato electrónico?
- **Control de bolsa entregada**: ¿está cada bolsa recogida, entregada, contada e importada?

## El eslabón que falta es el dato electrónico, no el contaje

El paso 3 es la clave y es el más frágil. Si una máquina no tiene telemetría ni se le lee el
audit, **su bolsa no tiene importe teórico**: se cuenta lo que haya y no hay contra qué compararlo.
Ese dinero es incontrolable por construcción, y no porque falte un informe.

Sobre el 25/09, de las **1.107 visitas reales**, 340 llevan marca de recaudación. El `cod_bolsa`
está en las 340, así que la bolsa se identifica siempre. Lo que no está es el importe: sólo 12
traen cifra, y `estado_contaje` es 0 en 327. Normal — en ese momento la bolsa aún no había pasado
por Loomis.

## Por qué `partesvisitacontajes` sale vacía

Lanzada por fecha de visita: 0 filas. Lanzada por `fechacontaje`: 0 filas también.

La hipótesis que encaja con el circuito es que **esa tabla es el arqueo manual dentro de VenCloud**
—alguien que cuenta a mano y lo teclea— y aquí no se usa, porque quien cuenta es Loomis y lo que
entra es **una importación**. Si es así, el dinero contado no está ahí sino en la recaudación
oficial, y las bolsas en las tablas de recogida.

## El mapa completo, eslabón por eslabón

| paso del circuito | tabla | qué aporta |
|---|---|---|
| 1 · La visita recauda | `vending.partesvisita` | `recaudacion`, `codbolsa`, `codbolsaprecinto` |
| 2 · Dato electrónico | `vending.partesvisitaauditmonbil`, `…audittubos`, `…contadores` | lo que la máquina dice que tiene |
| 3 · Cierre del día | `vending.partesvisita` | `estadobolsa`, `fechaverificabolsa` |
| 4 · Entrega a Loomis | `vending.recogidasbolsasrec` | `fechareg`, `numbolsas`, `tipobolsa`, **`firma`**, reponedor, ruta |
| 4b · Bolsa a bolsa | `vending.recogidasbolsasrecdetalles` | **`codbolsa`**, máquina, PDV y `partevisitaid` |
| 5 · Contado e importado | `facturacion.prefacrecauda` (+ detalle, resumen) | `imprecaudado`, `cambiocargado`, fecha contable, estado |
| — · Arqueo manual | `vending.partesvisitacontajes` | vacía, aparentemente sin uso |

`recogidasbolsasrecdetalles` es la pieza que cose las dos mitades: lleva **`codbolsa` y
`partevisitaid` en la misma fila**. Con eso, cada bolsa contada se puede devolver a la visita que
la generó, y de ahí al dato electrónico de esa máquina. El circuito se cierra entero.

## Las cuatro sondas

Antes de escribir un informe más hay que saber qué tablas están vivas. `partesvisitainvcanales` ya
nos enseñó que una tabla puede existir en el modelo y no tener una sola fila, y `partesvisitacontajes`
parece el segundo caso. Las cuatro van sin parámetros y devuelven una fila por mes.

### S1 · SONDA_BOLSAS_ENTREGADAS

```sql
select
  substring(cast(b.fechareg as text) from 1 for 7) as mes,
  count(b.id)      as entregas,
  sum(b.numbolsas) as bolsas
from vending.recogidasbolsasrec b
group by substring(cast(b.fechareg as text) from 1 for 7)
order by 1
```

Si diera error, quita la línea del `sum` y deja sólo el `count`.

### S2 · SONDA_RECAUDACION_OFICIAL

```sql
select
  p.anho      as anio,
  p.mes       as mes,
  count(p.id) as registros
from facturacion.prefacrecauda p
group by p.anho, p.mes
order by 1, 2
```

### S3 · SONDA_AUDIT_MONBIL

Va por la fecha de la visita madre, que es columna conocida y segura.

```sql
select
  substring(cast(p.fechaini as text) from 1 for 7) as mes,
  count(a.id)                     as lineas,
  count(distinct a.partevisitaid) as partes
from vending.partesvisitaauditmonbil a
join vending.partesvisita p on p.id = a.partevisitaid
group by substring(cast(p.fechaini as text) from 1 for 7)
order by 1
```

### S4 · SONDA_CONTAJES

La misma sobre contajes, pero por la fecha de la madre en vez de `fechacontaje`, para descartar
que el problema sea esa columna y no la tabla.

```sql
select
  substring(cast(p.fechaini as text) from 1 for 7) as mes,
  count(c.id)                     as lineas,
  count(distinct c.partevisitaid) as partes
from vending.partesvisitacontajes c
join vending.partesvisita p on p.id = c.partevisitaid
group by substring(cast(p.fechaini as text) from 1 for 7)
order by 1
```

## Lo que se podrá medir cuando sepamos qué tabla está viva

- **Bolsas recaudadas sin dato electrónico.** El agujero de control, y se mide desde ya cruzando
  las visitas con recaudación contra la cobertura de telemetría y el audit.
- **Diferencia entre lo contado y lo teórico**, por bolsa, ruta y reponedor.
- **Bolsas recogidas que no aparecen en ninguna entrega a Loomis**, y entregas sin firma.
- **Días desde que se recoge una bolsa hasta que se cuenta**: dinero parado. Con Loomis pasando
  una o dos veces por semana, lo normal son de 3 a 7 días; lo que pase de ahí es la excepción que
  hay que mirar.
- **Máquinas que llevan demasiado sin recaudar**, que es el otro lado del problema: el dinero se
  queda dentro de la máquina. Enlaza con la regla de los 100 € en bolsa de
  [13-maquina-por-dia.md](13-maquina-por-dia.md).

---

# Resultado de las sondas, 29/09/2026

Las cuatro lanzadas. Dos tablas vivas, dos muertas, y el mapa cambia.

| tabla | estado | desde | volumen reciente |
|---|---|---|---|
| `facturacion.prefacrecauda` | **viva** | 2023-08 | ~57.000 registros/mes |
| `vending.partesvisitaauditmonbil` | **viva** | 2023-08 | ~200.000 líneas y ~31.000 partes/mes |
| `vending.recogidasbolsasrec` | **vacía** | — | 0 filas |
| `vending.partesvisitacontajes` | **muerta** | 2023-08 | 107 filas, un solo mes, hace tres años |

`2023-08` es el mes en que arranca todo: es la puesta en marcha de VenCloud. Las dos tablas vivas
suben desde ahí y se estabilizan a lo largo de 2024.

## El dato electrónico existe, y a escala

Era la duda que importaba, y la respuesta es buena: **30.590 partes con lectura de monedero y
billetero en septiembre de 2026**, 193.723 líneas. Como las visitas reales de un mes son unas
23.000, la lectura cubre también los partes automáticos — que ya sabíamos que traen venta y cajón.

El despliegue se ve mes a mes: 297 partes en agosto de 2023, 1.169 en abril de 2024, 11.126 en
julio de 2024, y a partir de febrero de 2025 la meseta de 33.000–39.000.

**Hay una caída que conviene mirar**: del máximo de 39.135 partes en marzo de 2025 a los 30.590 de
septiembre de 2026 se pierde un 22 %. Puede ser parque, puede ser dispositivos que dejaron de
leer. Con el detalle por delegación se sabe.

## El agujero está en la entrega, no en el contaje

`recogidasbolsasrec` está vacía. O sea que **el paso 4 del circuito —el reponedor entrega las
bolsas y Loomis se las lleva— no queda registrado en VenCloud**. Ni el recuento de bolsas
entregadas, ni el tipo, ni la firma.

Entre «el reponedor verifica al final del día que tiene sus bolsas» y «Loomis las contó y el
fichero se importó» no hay nada. Si una bolsa se pierde en ese tramo, el sistema no lo sabe: sólo
se vería como una recaudación que nunca aparece contada, y sin fecha de entrega no se puede decir
en qué punto se perdió.

Eso es un hallazgo de control interno, no un problema de informes.

## El control que sí se puede montar

Queda de dos extremos, y son los dos buenos:

**Teórico** = `partesvisitaauditmonbil`, lo que la máquina dice que tiene.
**Real** = `facturacion.prefacrecauda`, lo que se contó y se importó.

La diferencia entre los dos, por punto de venta y por periodo, es el control de recaudación. Y el
volumen a vigilar lo da la telemetría: en septiembre de 2026, **258.490,96 € de efectivo sobre
1.088.439,33 € de venta, el 23,7 %**. Eso es lo que tiene que acabar en bolsas y volver contado.

Nota sobre el cierre: septiembre lleva 6.398 registros en `prefacrecauda` contra los 48.443 de
agosto. No es una caída, es que el mes no está cerrado — la importación va por detrás, como toca
cuando quien cuenta es un tercero.

## Siguiente paso

Dos extracciones de descubrimiento, porque de estas dos tablas no conocemos los nombres de campo:

- **R1** · `select * from facturacion.prefacrecauda where anho = {0} and mes = {1}` — dos
  parámetros **numéricos**, AÑO (Orden 0) y MES (Orden 1). Lanzar con 2026 y 8, que es el último
  mes cerrado.
- **R2** · `select a.* from vending.partesvisitaauditmonbil a join vending.partesvisita p on
  p.id = a.partevisitaid where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'` — los dos
  parámetros de fecha de siempre, con 25/09 en los dos, para ver la forma con ~6.500 filas antes
  de pedir el mes.

Con los nombres de campo delante se escriben los informes buenos y se cierra el cruce.
