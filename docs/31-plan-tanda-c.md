# Tanda C · Qué crear, qué no, y con qué fechas

Diez informes escritos en el catálogo. Antes de crearlos todos conviene recordar el balance: de
los diecisiete lanzados hasta ahora, **ocho tablas estaban vacías**. Crear diez informes a ciegas
significa, estadísticamente, tirar cuatro.

Así que la tanda C va en tres pasos.

---

## Paso 1 · Una sola sonda, y contesta por las trece tablas

Sin parámetros. Devuelve **una fila con trece números**. Con eso sabemos de un vistazo qué existe
antes de crear un solo informe más.

```sql
select
  (select count(*) from stocks.diarmovalm)                    as mov_almacen,
  (select count(*) from stocks.diarmovveh)                    as mov_vehiculo,
  (select count(*) from stocks.diarmovmaq)                    as mov_maquina,
  (select count(*) from stocks.traspasosstock)                as traspasos,
  (select count(*) from stocks.regularizacionesstock)         as regularizaciones,
  (select count(*) from stocks.planrecogida)                  as planes_recogida,
  (select count(*) from stocks.planrecogidadetalle)           as recogida_detalle,
  (select count(*) from stocks.plancargarutavehiculo)         as planes_carga,
  (select count(*) from stocks.plancargarutavehiculodetalle)  as carga_detalle,
  (select count(*) from stocks.planesretornoprod)             as planes_retorno,
  (select count(*) from stocks.planesretornoproddetalles)     as retorno_detalle,
  (select count(*) from stocks.infinventarioresumenes)        as inventarios_alm,
  (select count(*) from stocks.infinventarioelementos)        as inventario_elementos
```

**Esa versión no funciona**: el validador de VenCloud rechaza un `select` de subconsultas
escalares **sin cláusula `from`**. Los agregados tienen que ir como tablas derivadas dentro del
`from`, cruzadas entre sí:

```sql
select
  a.n as mov_almacen,   b.n as mov_vehiculo,  c.n as mov_maquina,
  d.n as traspasos,     e.n as regularizaciones,
  f.n as planes_recogida, g.n as recogida_detalle,
  h.n as planes_carga,    i.n as carga_detalle,
  j.n as planes_retorno,  k.n as retorno_detalle,
  l.n as inventarios_alm, m.n as inventario_elementos
from (select count(*) as n from stocks.diarmovalm) a,
     (select count(*) as n from stocks.diarmovveh) b,
     (select count(*) as n from stocks.diarmovmaq) c,
     (select count(*) as n from stocks.traspasosstock) d,
     (select count(*) as n from stocks.regularizacionesstock) e,
     (select count(*) as n from stocks.planrecogida) f,
     (select count(*) as n from stocks.planrecogidadetalle) g,
     (select count(*) as n from stocks.plancargarutavehiculo) h,
     (select count(*) as n from stocks.plancargarutavehiculodetalle) i,
     (select count(*) as n from stocks.planesretornoprod) j,
     (select count(*) as n from stocks.planesretornoproddetalles) k,
     (select count(*) as n from stocks.infinventarioresumenes) l,
     (select count(*) as n from stocks.infinventarioelementos) m
```

Y si aun así falla, la alternativa es una fila por tabla con `union all`:

```sql
select 'diarmovalm' as tabla, count(*) as filas from stocks.diarmovalm
union all select 'diarmovveh', count(*) from stocks.diarmovveh
union all select 'diarmovmaq', count(*) from stocks.diarmovmaq
union all select 'traspasosstock', count(*) from stocks.traspasosstock
union all select 'regularizacionesstock', count(*) from stocks.regularizacionesstock
union all select 'planrecogida', count(*) from stocks.planrecogida
union all select 'planrecogidadetalle', count(*) from stocks.planrecogidadetalle
union all select 'plancargarutavehiculo', count(*) from stocks.plancargarutavehiculo
union all select 'plancargarutavehiculodetalle', count(*) from stocks.plancargarutavehiculodetalle
union all select 'planesretornoprod', count(*) from stocks.planesretornoprod
union all select 'planesretornoproddetalles', count(*) from stocks.planesretornoproddetalles
union all select 'infinventarioresumenes', count(*) from stocks.infinventarioresumenes
union all select 'infinventarioelementos', count(*) from stocks.infinventarioelementos
```

**Y esto es lo que pasó.** La versión con tablas derivadas valida bien —el error fue «ha ocurrido
un error durante la operación», o sea que el SQL se aceptó y lo que falló fue construir el
documento—, pero contar `diarmovmaq` entero se pasa de tiempo. Son millones de filas y un
`count(*)` sin filtro las recorre todas.

La sonda se queda en **las diez tablas pequeñas**:

```sql
select
  d.n as traspasos,       e.n as regularizaciones,
  f.n as planes_recogida, g.n as recogida_detalle,
  h.n as planes_carga,    i.n as carga_detalle,
  j.n as planes_retorno,  k.n as retorno_detalle,
  l.n as inventarios_alm, m.n as inventario_elementos
from (select count(*) as n from stocks.traspasosstock) d,
     (select count(*) as n from stocks.regularizacionesstock) e,
     (select count(*) as n from stocks.planrecogida) f,
     (select count(*) as n from stocks.planrecogidadetalle) g,
     (select count(*) as n from stocks.plancargarutavehiculo) h,
     (select count(*) as n from stocks.plancargarutavehiculodetalle) i,
     (select count(*) as n from stocks.planesretornoprod) j,
     (select count(*) as n from stocks.planesretornoproddetalles) k,
     (select count(*) as n from stocks.infinventarioresumenes) l,
     (select count(*) as n from stocks.infinventarioelementos) m
```

Los tres diarios no necesitan sonda: **el C1, C2 y C3 de un día ya dicen si están vivos y con qué
volumen**, y además traen el dato. Se lanzan directamente.

## Y la sonda combinada tampoco funcionó

Dos intentos, dos fallos. Se acabó el experimento: **el motor no traga consultas con varias
tablas derivadas cruzadas**, con o sin los diarios. Lo que sí está probado cuatro veces —las
sondas S1 a S4— es **una tabla, un `group by`, un `count`**. Ese es el patrón, y no se toca.

Así que la sonda se hace con **una sola consulta reutilizada**, cambiando tabla y columna de
fecha, y lanzándola seis veces. Plantilla:

```sql
select
  substring(cast(x.FECHA as text) from 1 for 7) as mes,
  count(x.id)                                   as filas
from stocks.TABLA x
group by substring(cast(x.FECHA as text) from 1 for 7)
order by 1
```

| # | `TABLA` | `FECHA` | qué mide |
|---:|---|---|---|
| 1 | `traspasosstock` | `fechacrea` | traspasos entre almacenes |
| 2 | `regularizacionesstock` | `fecha` | descuadres reconocidos |
| 3 | `planrecogida` | `fecha` | planes de recogida de caducado |
| 4 | `plancargarutavehiculo` | `fechaplan` | plan de carga de vehículo |
| 5 | `planesretornoprod` | `fechacrea` | retornos de producto |
| 6 | `infinventarioresumenes` | `fecha` | inventarios de almacén |

**Las tablas de detalle no se sondean.** Si el padre tiene filas, la hija también; y si el padre
está vacío, la hija sobra. Son seis lanzamientos en vez de diez, y con el patrón que ya sabemos
que funciona.

## Paso 2 · Los tres diarios, primero un día

`diarmovalm`, `diarmovveh` y `diarmovmaq` son el núcleo de la trazabilidad y **son las grandes**.
Las reposiciones de un solo día ya fueron 8.187 líneas, y estas cubren todo el movimiento de
stock, no sólo el de máquina.

| informe | fechas | por qué |
|---|---|---|
| **C1** · MOV_ALMACEN | **25/09/2026 – 25/09/2026** | un día, para medir volumen |
| **C2** · MOV_VEHICULO | **25/09/2026 – 25/09/2026** | un día |
| **C3** · MOV_MAQUINA | **25/09/2026 – 25/09/2026** | un día |

Con el resultado se decide si el mes entra de una vez o hay que partirlo por semanas. Si un día
responde rápido, se relanzan los tres con **01/09/2026 – 25/09/2026** y quedan alineados con toda
la tanda A.

Elijo el 25/09 y no otro día porque es del que tenemos **todo lo demás medido**: 1.107 visitas,
8.187 reposiciones, 29.265,13 € de carga. Eso permite cuadrar el movimiento de stock contra la
reposición, que es la comprobación que de verdad valida estas tres tablas.

## Paso 3 · Las siete restantes, sólo las que la sonda diga que viven

Todas con **01/09/2026 – 25/09/2026**, la misma ventana que el resto del proyecto.

| informe | tabla | área del cuadro de mando | nota |
|---|---|---|---|
| **C4** · TRASPASOS | `traspasosstock` | Control almacenes | |
| **C5** · REGULARIZACIONES | `regularizacionesstock` | Control almacenes | el descuadre reconocido |
| **C6** · RECOGIDAS | `planrecogida` + detalle | Devoluciones | caducado y rotura separados |
| **C7** · PLANCARGA | `plancargarutavehiculo` + detalle | Rutas | lo planificado contra lo confirmado |
| **C8** · RETORNOS | `planesretornoprod` + detalle | Devoluciones | |
| **C9** · INVENTARIOS_ALM | `infinventarioresumenes` | Inventario almacenes | |
| **C10** · INVENTARIOS_ALM_PROD | `infinventarioelementosprods` | Inventario almacenes | **no crearlo todavía** |

**C10 no se crea hasta que C9 devuelva filas.** Es su hija: si el padre está vacío, la hija
también, y es un informe menos que montar.

## Dónde apostaría

Sin datos no es más que una corazonada, y por eso está la sonda. Pero por el patrón que llevamos
—viven las tablas del proceso que la casa ejecuta de verdad, mueren las del proceso que hace de
otra manera—:

- **C1, C2 y C3 vivos y grandes.** El stock se mueve todos los días y VenCloud es el ERP que lo
  lleva; sin esto no habría ni albaranes.
- **C5 (regularizaciones) vivo**, porque el descuadre hay que reconocerlo en algún sitio.
- **C6 (planes de recogida) en duda**, por lo mismo que `partesvisitaincidencias` estaba vacía: la
  caducidad ya se registra en las líneas `RC` de la reposición. Si están las dos, habrá que
  decidir cuál es la buena antes de sumar, o el caducado saldrá doble.
- **C7 (plan de carga) en duda.** Si las rutas se cargan sin plan formal en el sistema, estará
  vacío. Es justo el tipo de proceso que puede hacerse en papel.

## Lo que cierra la tanda C

Cuatro de las nueve áreas que pediste: **control de almacenes, inventario de almacenes,
devoluciones y la parte de stock de rutas**. Y con C1+C2+C3 se cierra la cadena entera —compra →
almacén → vehículo → máquina → venta—, que es lo que permite medir la merma de verdad en vez de
deducirla.


---

## La sonda con fecha tampoco valida: versión a prueba de nombres

«La sentencia no está bien configurada» quiere decir que el SQL se rechaza antes de ejecutarse, y
el sospechoso es el nombre de la columna de fecha. En vez de seguir adivinando, la sonda se hace
**agrupando por una columna que el propio catálogo ya confirma que existe**, porque los informes
C4 a C9 la seleccionan. Sin fechas, sin `substring` y sin `count` de columna nombrada:

```sql
select x.COLUMNA as valor, count(*) as filas
from stocks.TABLA x
group by x.COLUMNA
order by 1
```

| # | `TABLA` | `COLUMNA` | por qué es segura |
|---:|---|---|---|
| 1 | `traspasosstock` | `estado` | el C4 selecciona `t.estado` |
| 2 | `regularizacionesstock` | `tipo` | el C5 selecciona `r.tipo` |
| 3 | `planrecogida` | `realizadopor` | el C6 selecciona `p.realizadopor` |
| 4 | `plancargarutavehiculo` | `estado` | el C7 selecciona `c.estado` |
| 5 | `planesretornoprod` | `estado` | el C8 selecciona `r.estado` |
| 6 | `infinventarioresumenes` | `anho` | el C9 selecciona `r.anho` |

La primera, entera:

```sql
select x.estado as valor, count(*) as filas
from stocks.traspasosstock x
group by x.estado
order by 1
```

Devuelve pocas filas y contesta lo único que importa ahora: **si la tabla tiene datos o no**. De
paso, agrupar por `estado` dice si los traspasos se quedan a medias, y agrupar por `anho` dice
desde cuándo hay inventarios de almacén.
