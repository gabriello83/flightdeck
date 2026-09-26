# SQL de rentabilidad y de receta

Todas siguen las tres reglas que hemos aprendido a golpes con el motor de informes:

1. Nada de casts con dos puntos: `cast(x as text)`.
2. Nunca `sum(alias.columna)` en un informe con parámetros. Si hace falta agregar con joins, los
   joins van dentro de una subconsulta y el agregado fuera, sobre nombres sin prefijo.
3. En este modelo «sin referencia» es **0**, no nulo: `coalesce(campo,0) = 0`.

Ninguna de estas consultas lleva parámetros, así que la pestaña Parámetros va vacía en todas.

---

# Parte 1 · Rentabilidad

## R1 — Los parámetros globales

Aquí es donde probablemente están los 8,3 años de amortización y el coste de servicio que no
aparecen en el maestro de PDVs.

```sql
select
  plazoamortizacion,
  modocalculoamortizacion,
  costevisitamodo,
  costemediovisitatecnica,
  costeaveria,
  costesolicitudcom,
  costemantenimiento,
  costeserviciotelemetria,
  costeserviciopagobancario,
  costeservicioappmovil,
  modorentabilidad,
  origeningreso,
  origeningresoest,
  tiporepartocomision,
  modoaplicaocs,
  tipodelegacionalv
from configuracion.confrentabilidad
```

## R2 — Coste de servicio por tipo de telemetría

Sabemos que todo el parque conectado es `tipotelemetria = 40` (Nayax). Esta tabla dice lo que
cuesta cada transacción por ese canal.

```sql
select
  tipotelemetria,
  costeserviciotelemetria,
  costeserviciopagobancario,
  costeservicioappmovil,
  confrentabilidadid
from configuracion.confrentabilidadcostesservicios
order by tipotelemetria
```

## R3 — ¿Está ya calculada la rentabilidad mensual?

La consulta que decide si la cabina calcula rentabilidad o simplemente la lee. **Lánzala antes
que R4**, porque su resultado dice qué meses existen.

```sql
select
  anho,
  mes,
  count(*)                    as filas,
  count(distinct pdvid)       as pdvs,
  count(distinct maquinaid)   as maquinas,
  sum(costetotalcomis)        as comisiones,
  sum(costefijopdv)           as coste_fijo,
  sum(costeamortizacionmaquina)  as amort_maquina,
  sum(costeamortizacionmaqdisp)  as amort_dispositivo,
  sum(costetotalamortizacion) as amortizacion_total,
  sum(costeserviciotelemetria)   as serv_telemetria,
  sum(costeserviciopagobancario) as serv_banco,
  sum(costetotalservicios)    as servicios_total
from vending.pdvsrentabilidades
group by anho, mes
order by anho desc, mes desc
```

Si devuelve filas con importes, la rentabilidad por máquina está resuelta y sólo hay que cruzarla
con la venta. Si devuelve cero filas o todo a cero, hay que calcularla nosotros a partir de R1.

## R4 — Volcado de rentabilidad por máquina

Cambia `2026` y `8` por el año y mes que te haya dado R3.

```sql
select
  m.codigo     as matricula,
  pdv.codigo   as cod_pdv,
  cen.numcentro as num_centro,
  cen.denomina as centro,
  cli.codigo   as cod_cliente,
  cli.nombre   as cliente,
  del.nombre   as delegacion,
  r.anho       as anho,
  r.mes        as mes,
  r.costecomispdv,
  r.costecomiscentro,
  r.costecomiscliente,
  r.costetotalcomis,
  r.costefijopdv,
  r.costeamortizacionmaquina,
  r.costeamortizacionmaqdisp,
  r.costetotalamortizacion,
  r.costeserviciotelemetria,
  r.costeserviciopagobancario,
  r.costeservicioappmovil,
  r.costetotalservicios
from vending.pdvsrentabilidades r
left join recursos.maquinas m           on m.id   = r.maquinaid
left join vending.pdvs pdv              on pdv.id = r.pdvid
left join comercial.clientescentros cen on cen.id = r.clientecentroid
left join comercial.clientes cli        on cli.id = r.clienteid
left join general.delegaciones del      on del.id = pdv.delegacionid
where r.anho = 2026 and r.mes = 8
order by m.codigo
```

---

# Parte 2 · La receta del café

El modelo, ya entendido: **`stocks.articulosdetalle` dice de qué se compone cada bebida
preparada, pero no con qué artículo concreto.** Dice «un café con leche lleva tanto de materia
prima tipo 1, tanto de tipo 5 y un vaso del tipo 3». El artículo real que hay cargado en cada
máquina sale de **`recursos.maquinascarriles`**, que sí tiene `tipomateriaprima` **y**
`articuloid`.

O sea: el coste de un café **no es único**, depende de qué café esté cargado en esa máquina. Por
eso no puede estar en `stocks.articulos.puc`, y por eso `preciocoste` está vacío al 98 %.

Códigos de `tipomateriaprima`: 1 café · 2 azúcar · 3 vaso · 4 paletina · 5 leche · 6 soluble ·
7 garrafa · 8 cápsula · 9 chocolate · 10 infusión · 11 café soluble · 12 café grano · 13 toppings.

## C1 — La receta entera

Debería ser pequeña: sólo las bebidas preparadas tienen detalle.

```sql
select
  a.codigo   as cod_bebida,
  a.denomina as bebida,
  a.clase    as clase,
  a.precioventa,
  d.orden    as orden,
  d.tipomateriaprima as tipo_materia,
  d.tipounidad as unidad,
  d.cantunidad as cantidad
from stocks.articulosdetalle d
join stocks.articulos a on a.id = d.articuloid
order by a.codigo, d.orden
```

## C2 — Cuántas bebidas tienen receta, y cuántas no

```sql
select
  clase,
  count(*) as articulos,
  sum(con_receta) as con_receta,
  sum(sin_receta) as sin_receta
from (
  select
    a.clase as clase,
    case when d.articuloid is null then 0 else 1 end as con_receta,
    case when d.articuloid is null then 1 else 0 end as sin_receta
  from stocks.articulos a
  left join (select distinct articuloid from stocks.articulosdetalle) d
         on d.articuloid = a.id
  where a.clase = 1
) x
group by clase
```

## C3 — Los carriles de materia prima de una máquina caliente

Prueba con una que venda café. Cambia la matrícula.

```sql
select
  m.codigo   as matricula,
  c.numero   as carril,
  c.tipomateriaprima as tipo_materia,
  c.formato  as formato,
  c.virtual  as virtual,
  c.extra    as extra,
  c.capacmax as capacidad,
  c.stockrecom as stock_recomendado,
  c.cargaminima as carga_minima,
  a.codigo   as cod_materia,
  a.denomina as materia,
  a.puc      as puc,
  a.unidcaja as unid_caja,
  a.unidmedida as unidad_medida
from recursos.maquinascarriles c
join recursos.maquinas m on m.id = c.maquinaid
left join stocks.articulos a on a.id = c.articuloid
where m.codigo = '24CE4829'
order by c.numero
```

## C4 — Cuánto cubre el modelo: carriles con artículo asignado

```sql
select
  count(*) as carriles,
  count(distinct maquinaid) as maquinas,
  sum(con_articulo) as con_articulo,
  sum(con_puc)      as con_puc,
  sum(es_virtual)   as virtuales
from (
  select
    c.maquinaid as maquinaid,
    case when coalesce(c.articuloid,0) = 0 then 0 else 1 end as con_articulo,
    case when coalesce(a.puc,0) > 0 then 1 else 0 end        as con_puc,
    case when c.virtual is true then 1 else 0 end            as es_virtual
  from recursos.maquinascarriles c
  left join stocks.articulos a on a.id = c.articuloid
) x
```

## C5 — El coste real del café, máquina a máquina

Esta es la que cierra el margen. Cruza la receta con lo que hay cargado en cada máquina. Empieza
por **una sola matrícula** para comprobar que el cruce es correcto antes de lanzarla a todo el
parque.

```sql
select
  matricula,
  cod_bebida,
  bebida,
  precioventa,
  tipo_materia,
  cantidad,
  unidad,
  cod_materia,
  materia,
  puc_materia,
  unid_caja,
  (cantidad * puc_materia) as coste_linea
from (
  select
    m.codigo    as matricula,
    ab.codigo   as cod_bebida,
    ab.denomina as bebida,
    ab.precioventa as precioventa,
    d.tipomateriaprima as tipo_materia,
    d.cantunidad as cantidad,
    d.tipounidad as unidad,
    am.codigo   as cod_materia,
    am.denomina as materia,
    am.puc      as puc_materia,
    am.unidcaja as unid_caja
  from stocks.articulosdetalle d
  join stocks.articulos ab on ab.id = d.articuloid
  join recursos.maquinascarriles c on c.tipomateriaprima = d.tipomateriaprima
  join recursos.maquinas m on m.id = c.maquinaid
  left join stocks.articulos am on am.id = c.articuloid
  where m.codigo = '24CE4829'
) x
order by cod_bebida, tipo_materia
```

**Aviso sobre C5.** El cruce se hace por `tipomateriaprima`, no por una clave directa, así que si
una máquina tiene dos carriles del mismo tipo —dos cafés distintos, por ejemplo— la receta se
duplicará contra los dos. Hay que mirar el resultado de C3 antes de fiarse de C5: si sale algún
`tipo_materia` repetido en la misma máquina, el cruce necesita una regla más (probablemente
`articulocategoriaprecioid`, o el carril concreto que la selección de la bebida usa). Por eso
esta va de una en una y no de golpe.

## C6 — La unidad importa

`cantunidad` viene con `tipounidad`. Si la cantidad está en gramos y el `puc` es por kilo o por
caja, el coste sale mil veces mal. Antes de multiplicar nada hay que ver qué unidades usa:

```sql
select
  tipounidad,
  tipomateriaprima,
  count(*) as lineas,
  min(cantunidad) as minimo,
  max(cantunidad) as maximo,
  avg(cantunidad) as media
from stocks.articulosdetalle
group by tipounidad, tipomateriaprima
order by tipomateriaprima, tipounidad
```
