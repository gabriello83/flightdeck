# Consultas agregadas del mes, y el fallo del motor de informes

## El fallo

El motor de WebReports **no soporta `sum(alias.columna)` cuando el informe tiene parámetros
declarados**. La consulta se ejecuta —se ve porque tarda lo que tiene que tardar— y revienta
después, al montar el documento, con el aviso genérico «Ha ocurrido un error durante la
operación».

Se acotó así, con cuatro informes mínimos sobre el mismo día:

| prueba | `sum()` | parámetros | alias `t.` | resultado |
|---|---|---|---|---|
| T1 `select count(*) …` | no | sí | sí | funciona |
| T2 `select count(*), sum(precio) …` (fecha fija) | sí | no | no | funciona |
| T3 `select count(*), sum(precio) …` con `{0}`/`{1}` | sí | sí | **no** | **funciona** |
| A `select count(*), sum(t.precio) …` con `{0}`/`{1}` | sí | sí | **sí** | **falla** |

Los dos mensajes de error del motor significan cosas distintas y conviene no confundirlos:

- **«La sentencia no está bien configurada»** → el SQL se rechaza al validarlo. Es un error de
  sintaxis o de tipos: columna que no existe, `is true` sobre un entero, un cast con `::`.
- **«Ha ocurrido un error durante la operación»** → el SQL es correcto y se ejecuta. Lo que falla
  es la generación del documento con el resultado.

## El patrón obligatorio

Con joins hacen falta alias, así que no basta con quitarlos. La forma que funciona siempre:

> **Los joins y el filtro de fechas van dentro de una subconsulta, sin agregar nada. Los
> agregados van fuera, sobre nombres de columna sin prefijo.**

Además, el Orden de los parámetros empieza en **0**: `{0}` es Orden 0, `{1}` es Orden 1, los dos
de tipo Fecha.

---

## A. Resumen diario del mes — 26 filas

```sql
select
  fecha,
  dia_semana,
  count(*)                  as transacciones,
  count(distinct maquinaid) as maquinas_con_venta,
  sum(precio)               as importe,
  sum(coste_ok)             as coste_conocido,
  round(100.0 * sum(tiene_coste) / count(*), 1)  as pct_con_coste,
  round(100.0 * sum(sin_articulo) / count(*), 1) as pct_sin_articulo,
  sum(imp_efectivo)         as imp_efectivo,
  sum(imp_tarjeta)          as imp_tarjeta,
  sum(imp_prepago)          as imp_prepago,
  sum(imp_otros)            as imp_otros
from (
  select
    cast(fechaventa as date) as fecha,
    diasemana                as dia_semana,
    maquinaid,
    precio,
    case when coalesce(coste,0) > 0 then coste else 0 end       as coste_ok,
    case when coalesce(coste,0) > 0 then 1 else 0 end           as tiene_coste,
    case when articuloid is null then 1 else 0 end              as sin_articulo,
    case when lineaprecio = 2 then precio else 0 end            as imp_efectivo,
    case when lineaprecio = 1 then precio else 0 end            as imp_tarjeta,
    case when lineaprecio = 3 then precio else 0 end            as imp_prepago,
    case when lineaprecio not in (1,2,3) then precio else 0 end as imp_otros
  from telemetry.telemetrysales
  where fechaventa >= '{0}' and fechaventa <= '{1} 23:59:59'
) x
group by fecha, dia_semana
order by fecha
```

## B. Máquina × día — unas 46.000 filas

La tabla base de la cabina.

```sql
select
  matricula,
  fecha,
  num_centro,
  centro,
  delegacion,
  count(*)                   as transacciones,
  sum(precio)                as importe,
  sum(coste_ok)              as coste_conocido,
  sum(imp_efectivo)          as imp_efectivo,
  min(hora)                  as primera_hora,
  max(hora)                  as ultima_hora,
  count(distinct articuloid) as articulos_distintos,
  sum(sin_articulo)          as lineas_sin_articulo
from (
  select
    m.codigo                   as matricula,
    cast(t.fechaventa as date) as fecha,
    cen.numcentro              as num_centro,
    cen.denomina               as centro,
    del.nombre                 as delegacion,
    t.precio                   as precio,
    t.hora                     as hora,
    t.articuloid               as articuloid,
    case when coalesce(t.coste,0) > 0 then t.coste else 0 end as coste_ok,
    case when t.lineaprecio = 2 then t.precio else 0 end      as imp_efectivo,
    case when t.articuloid is null then 1 else 0 end          as sin_articulo
  from telemetry.telemetrysales t
  left join recursos.maquinas m           on m.id   = t.maquinaid
  left join vending.pdvs p                on p.id   = t.pdvid
  left join comercial.clientescentros cen on cen.id = p.clientecentroid
  left join general.delegaciones del      on del.id = p.delegacionid
  where t.fechaventa >= '{0}' and t.fechaventa <= '{1} 23:59:59'
) x
group by matricula, fecha, num_centro, centro, delegacion
order by matricula, fecha
```

## C. Máquina × artículo del mes — unas 25.000 filas

Pareto de producto y revisión de planograma. Las filas con `cod_articulo` vacío son los canales
sin mapear.

```sql
select
  matricula,
  centro,
  cod_articulo,
  articulo,
  clase_articulo,
  canal,
  count(*)    as unidades,
  sum(precio) as importe,
  avg(precio) as precio_medio,
  max(puc)    as puc,
  min(fecha)  as primera_venta,
  max(fecha)  as ultima_venta
from (
  select
    m.codigo     as matricula,
    cen.denomina as centro,
    a.codigo     as cod_articulo,
    a.denomina   as articulo,
    a.clase      as clase_articulo,
    t.codcanal   as canal,
    t.precio     as precio,
    a.puc        as puc,
    cast(t.fechaventa as date) as fecha
  from telemetry.telemetrysales t
  left join recursos.maquinas m           on m.id   = t.maquinaid
  left join vending.pdvs p                on p.id   = t.pdvid
  left join comercial.clientescentros cen on cen.id = p.clientecentroid
  left join stocks.articulos a            on a.id   = t.articuloid
  where t.fechaventa >= '{0}' and t.fechaventa <= '{1} 23:59:59'
) x
group by matricula, centro, cod_articulo, articulo, clase_articulo, canal
order by matricula, importe desc
```

## D. Perfil horario por centro y día de la semana

La base de las alarmas de falta de ventas: es lo que distingue un centro diurno de un hospital
de 24 horas.

```sql
select
  num_centro,
  centro,
  dia_semana,
  hora,
  count(distinct fecha) as dias_con_dato,
  count(*)              as transacciones,
  sum(precio)           as importe
from (
  select
    cen.numcentro as num_centro,
    cen.denomina  as centro,
    t.diasemana   as dia_semana,
    t.hora        as hora,
    t.precio      as precio,
    cast(t.fechaventa as date) as fecha
  from telemetry.telemetrysales t
  left join vending.pdvs p                on p.id   = t.pdvid
  left join comercial.clientescentros cen on cen.id = p.clientecentroid
  where t.fechaventa >= '{0}' and t.fechaventa <= '{1} 23:59:59'
) x
group by num_centro, centro, dia_semana, hora
order by centro, dia_semana, hora
```
