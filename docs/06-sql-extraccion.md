# SQL de extracción para VenCloud

Consultas listas para publicar como informes rápidos. Cada una sigue las convenciones que
hemos aprendido catalogando los informes existentes:

- Los filtros opcionales usan **comodín 0**: `((0 = {n}) or (columna = {n}))`.
- El corte superior de fechas lleva siempre **`'{n} 23:59:59'`**.
- **Ninguna fecha va escrita a fuego** (es el fallo de los informes 9, 28 y 34).
- Se devuelve siempre la **matrícula** (`recursos.maquinas.codigo`), que es el
  identificador que usa el equipo, además del código de PDV para poder enlazar.
- Nada de `select` sobre `telemetry.telemetrysales` sin rango de fechas (es lo que tumba
  los informes 37 y 59).

---

## Bloque 0 — Estructura de la base

Lo primero. Sin esto vamos adivinando nombres de columna.

### 0.1 Tablas y su tamaño

```sql
select
  n.nspname                                   as esquema,
  c.relname                                   as tabla,
  case c.relkind when 'r' then 'tabla' when 'v' then 'vista'
                 when 'm' then 'vista materializada' else c.relkind::text end as tipo,
  c.reltuples::bigint                         as filas_aprox,
  pg_size_pretty(pg_total_relation_size(c.oid)) as tamano
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where c.relkind in ('r','v','m')
  and n.nspname in ('comercial','vending','recursos','stocks','compras',
                    'facturacion','general','utils','telemetry','configuracion',
                    'importacion','sat','public')
order by n.nspname, c.relname;
```

### 0.2 Columnas de cada tabla

```sql
select
  table_schema  as esquema,
  table_name    as tabla,
  ordinal_position as pos,
  column_name   as columna,
  data_type     as tipo,
  is_nullable   as admite_nulo,
  column_default as valor_defecto
from information_schema.columns
where table_schema in ('comercial','vending','recursos','stocks','compras',
                       'facturacion','general','utils','telemetry','configuracion',
                       'importacion','sat')
order by table_schema, table_name, ordinal_position;
```

### 0.3 Claves ajenas (cómo se enlazan las tablas)

```sql
select
  tc.table_schema || '.' || tc.table_name     as tabla,
  kcu.column_name                             as columna,
  ccu.table_schema || '.' || ccu.table_name   as referencia,
  ccu.column_name                             as columna_referida
from information_schema.table_constraints tc
join information_schema.key_column_usage kcu
  on kcu.constraint_name = tc.constraint_name and kcu.constraint_schema = tc.constraint_schema
join information_schema.constraint_column_usage ccu
  on ccu.constraint_name = tc.constraint_name and ccu.constraint_schema = tc.constraint_schema
where tc.constraint_type = 'FOREIGN KEY'
  and tc.table_schema in ('comercial','vending','recursos','stocks','compras',
                          'facturacion','general','utils','telemetry','sat')
order by tabla, columna;
```

---

## Bloque 1 — Maestros completos

`select *` a propósito: queremos la tabla entera, incluidas las columnas que todavía no
conocemos. Ninguna de estas pasa de unas pocas miles de filas.

```sql
-- 1.1 Artículos (unas 1.600 filas)
select * from stocks.articulos order by codigo;

-- 1.2 Modelos de máquina (unos 130)
select * from recursos.maquinasmodelos order by codigo;

-- 1.3 Máquinas: las matrículas (4.498)
select * from recursos.maquinas order by codigo;

-- 1.4 Puntos de venta (3.203 activos, más históricos)
select * from vending.pdvs order by codigo;

-- 1.5 Clientes y centros
select * from comercial.clientes order by codigo;
select * from comercial.clientescentros order by numcentro;

-- 1.6 Organización
select * from general.delegaciones order by id;
select * from recursos.empleados order by nombre;
select * from recursos.vehiculos order by matricula;
select * from general.fabricantes order by nombre;

-- 1.7 Rutas
select * from vending.rutas order by codigo;
select * from vending.rutasdetalle order by rutaid, pdvid;
select * from vending.rutasdetallecriterios order by rutadetalleid;

-- 1.8 Compras
select * from compras.proveedores order by codigo;
select * from compras.tarifascpa order by proveedorid, articuloid;

-- 1.9 Catálogos de configuración
select * from configuracion.satoperaciones;
select * from configuracion.satoperacionescategorias;
select * from configuracion.satworkflowestados;
select * from configuracion.motvisitanorealizable;
```

### 1.10 Artículos con todo lo que necesitamos, ya enlazado

Si se prefiere una sola consulta legible en vez del `select *`:

```sql
select
  a.codigo                     as cod_articulo,
  a.denomina                   as articulo,
  a.clase                      as clase_cod,
  case a.clase
    when 0 then 'Materia prima'      when 1 then 'Bebida caliente/preparada'
    when 2 then 'Bebida fría envasada' when 3 then 'Snacks/sólidos'
    when 6 then 'Garrafas de agua'   else 'Recambios' end as clase,
  a.tipo                       as tipo,
  a.obsoleto                   as obsoleto,
  a.puc                        as precio_ultima_compra,
  a.coeficienteservicios       as coef_servicios,
  (select p.razsocial from compras.tarifascpa tc
     join compras.proveedores p on p.id = tc.proveedorid
    where tc.articuloid = a.id order by tc.precio asc limit 1) as proveedor_mas_barato,
  (select min(tc.precio) from compras.tarifascpa tc where tc.articuloid = a.id) as precio_compra_min,
  (select max(tc.precio) from compras.tarifascpa tc where tc.articuloid = a.id) as precio_compra_max
from stocks.articulos a
order by a.codigo;
```

> **Lo que hay que buscar en `stocks.articulos`**: el campo de **unidades por caja** o
> factor de conversión. Sin él, `puc` (precio por unidad de compra) no se puede convertir a
> coste por unidad vendida, y el margen sigue sin poder calcularse. Con el volcado del
> bloque 0.2 lo localizamos.

---

## Bloque 2 — Ventas en tiempo real (telemetría)

Es la tabla que rellena el hueco de los audits. Por el informe 37 sabemos que
`telemetry.telemetrysales` tiene `maquinaid`, `articuloid`, `seleccion`, `precio`,
`fechaventa`, `pdvid`, `lineaprecio`, `tipotelemetria` y `tipoventaorigen`.

### 2.1 Detalle de ventas — para rangos cortos (un día o una semana)

```sql
select
  m.codigo                 as matricula,
  mo.modelo                as modelo,
  del.nombre               as delegacion,
  cli.codigo               as cod_cliente,
  cli.nombre               as cliente,
  cen.numcentro            as num_centro,
  cen.denomina             as centro,
  p.codigo                 as cod_pdv,
  p.ubicacion              as ubicacion,
  t.fechaventa::text       as fecha_venta,
  a.codigo                 as cod_articulo,
  a.denomina               as articulo,
  t.seleccion              as seleccion,
  t.precio                 as precio,
  case t.lineaprecio when 1 then 'Tarjeta crédito'
                     when 2 then 'Efectivo'
                     when 3 then 'Prepago'
                     else t.lineaprecio::text end as medio_pago,
  t.tipoventaorigen        as tipo_origen,
  case t.tipotelemetria when 40 then 'NAYAX' when 0 then 'Sin telemetría'
                        else t.tipotelemetria::text end as telemetria
from telemetry.telemetrysales t
left join recursos.maquinas m       on m.id  = t.maquinaid
left join recursos.maquinasmodelos mo on mo.id = m.maquinamodeloid
left join vending.pdvs p            on p.id  = t.pdvid
left join comercial.clientescentros cen on cen.id = p.clientecentroid
left join comercial.clientes cli    on cli.id = cen.clienteid
left join general.delegaciones del  on del.id = p.delegacionid
left join stocks.articulos a        on a.id  = t.articuloid
where t.fechaventa >= '{0}' and t.fechaventa <= '{1} 23:59:59'
  and ((0 = {2}) or (cli.codigo = {2}))
  and ((0 = {3}) or (cen.numcentro = {3}))
order by t.fechaventa;
```

Parámetros: `{0}` desde, `{1}` hasta, `{2}` código de cliente (0 = todos), `{3}` número de
centro (0 = todos).

### 2.2 Ventas agregadas por máquina, artículo y día — para rangos largos

La misma información sin el detalle transacción a transacción. Es la que conviene para
cargar meses enteros.

```sql
select
  m.codigo                 as matricula,
  cen.numcentro            as num_centro,
  cen.denomina             as centro,
  a.codigo                 as cod_articulo,
  a.denomina               as articulo,
  t.fechaventa::date       as fecha,
  case t.lineaprecio when 1 then 'Tarjeta crédito'
                     when 2 then 'Efectivo'
                     when 3 then 'Prepago'
                     else t.lineaprecio::text end as medio_pago,
  count(*)                 as unidades,
  sum(t.precio)            as importe
from telemetry.telemetrysales t
left join recursos.maquinas m on m.id = t.maquinaid
left join vending.pdvs p on p.id = t.pdvid
left join comercial.clientescentros cen on cen.id = p.clientecentroid
left join comercial.clientes cli on cli.id = cen.clienteid
left join stocks.articulos a on a.id = t.articuloid
where t.fechaventa >= '{0}' and t.fechaventa <= '{1} 23:59:59'
  and ((0 = {2}) or (cli.codigo = {2}))
group by m.codigo, cen.numcentro, cen.denomina, a.codigo, a.denomina,
         t.fechaventa::date, t.lineaprecio
order by fecha, matricula, cod_articulo;
```

### 2.3 Última venta y última conexión por máquina

Para saber qué máquinas han dejado de hablar, que es la causa raíz del 12% de audits.

```sql
select
  m.codigo                       as matricula,
  cen.denomina                   as centro,
  p.codigo                       as cod_pdv,
  case m.tipotelemetria when 40 then 'NAYAX' when 0 then 'Sin telemetría'
                        else m.tipotelemetria::text end as telemetria,
  p.telemetriadispositivo        as id_dispositivo,
  max(t.fechaventa)::text        as ultima_venta,
  count(*)                       as ventas_periodo
from vending.pdvs p
left join recursos.maquinas m on m.id = p.maquinaid
left join comercial.clientescentros cen on cen.id = p.clientecentroid
left join telemetry.telemetrysales t
       on t.pdvid = p.id
      and t.fechaventa >= '{0}' and t.fechaventa <= '{1} 23:59:59'
where p.estado = 1
group by m.codigo, cen.denomina, p.codigo, m.tipotelemetria, p.telemetriadispositivo
order by ultima_venta nulls first;
```

---

## Bloque 3 — Movimiento operativo

```sql
-- 3.1 Cabecera de partes de visita
select p.*, m.codigo as matricula, pdv.codigo as cod_pdv, cen.numcentro, cen.denomina as centro
from vending.partesvisita p
left join recursos.maquinas m on m.id = p.maquinaid
left join vending.pdvs pdv on pdv.id = p.pdvid
left join comercial.clientescentros cen on cen.id = p.clientecentroid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59';

-- 3.2 Líneas de reposición, con el tipo como columna (sustituye a los informes 7, 12 y 66)
select
  m.codigo as matricula, cen.denomina as centro, p.fechaini::date as fecha,
  r.tipo as tipo_movimiento, a.codigo as cod_articulo, a.denomina as articulo,
  r.cantidad, a.coeficienteservicios as coef_servicios
from vending.partesvisitareposiciones r
join vending.partesvisita p on p.id = r.partevisitaid
left join recursos.maquinas m on m.id = p.maquinaid
left join comercial.clientescentros cen on cen.id = p.clientecentroid
left join stocks.articulos a on a.id = r.articuloid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59';

-- 3.3 Ventas leídas en el audit de la visita
select m.codigo as matricula, p.fechaini::date as fecha, a.codigo as cod_articulo,
       v.totnumvtas as unidades, v.totimpvtas as importe
from vending.partesvisitaventas v
join vending.partesvisita p on p.id = v.partevisitaid
left join recursos.maquinas m on m.id = p.maquinaid
left join stocks.articulos a on a.id = v.articuloid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59';

-- 3.4 Contajes de recaudación
select * from vending.partesvisitacontajes c
where c.partevisitaid in (select id from vending.partesvisita
                          where fechaini >= '{0}' and fechaini <= '{1} 23:59:59');

-- 3.5 Detalle de máquina en el parte (precios leídos)
select * from vending.partesvisitamaqdetalle d
where d.partevisitaid in (select id from vending.partesvisita
                          where fechaini >= '{0}' and fechaini <= '{1} 23:59:59');

-- 3.6 Control de jornada de ruta
select * from vending.rutascontrol
where fechaini >= '{0}' and fechaini <= '{1} 23:59:59';

-- 3.7 Plan de visitas
select * from vending.planvisitas where fecha >= '{0}' and fecha <= '{1}';

-- 3.8 Histórico de instalaciones
select * from vending.pdvshisinstalaciones
where fechaejecucion >= '{0}' and fechaejecucion <= '{1} 23:59:59';
```

---

## Bloque 4 — Planograma y tarifas

```sql
-- 4.1 Canales de todas las máquinas, con matrícula
select m.codigo as matricula, mo.modelo, c.*
from recursos.maquinascanales c
join recursos.maquinas m on m.id = c.maquinaid
left join recursos.maquinasmodelos mo on mo.id = m.maquinamodeloid
where ((0 = {0}) or (m.delegacionid = {0}));

-- 4.2 Carriles de materia prima (las calientes)
select m.codigo as matricula, r.*
from recursos.maquinascarriles r
join recursos.maquinas m on m.id = r.maquinaid;

-- 4.3 Plantillas de modelo y sus carriles
select * from recursos.maquinasmodelosplantillas;
select * from recursos.maquinasmodelosplantillascarriles;

-- 4.4 Tarifas: cabecera, detalle y a qué PDV se aplican
select * from comercial.tarifasvending;
select * from comercial.tarifasvendingdetalle;
select p.codigo as cod_pdv, m.codigo as matricula, p.tarifavendingid
from vending.pdvs p left join recursos.maquinas m on m.id = p.maquinaid
where p.tarifavendingid is not null;
select * from comercial.tarifasvendingproductos;
```

---

## Bloque 5 — Servicio técnico, inventario y compras

```sql
-- 5.1 Tareas técnicas completas
select t.*, m.codigo as matricula
from sat.tareatecnica t
left join recursos.maquinas m on m.id = t.maquinaid
where t.fecha >= '{0}' and t.fecha <= '{1} 23:59:59';

-- 5.2 Log de eventos de la tarea (de aquí sale el tiempo de resolución real)
select * from sat.tareatecnicaeventoslog
where tareatecnicaid in (select id from sat.tareatecnica
                         where fecha >= '{0}' and fecha <= '{1} 23:59:59');

-- 5.3 Visitas técnicas
select * from sat.tareatecnicavisita
where tareatecnicaid in (select id from sat.tareatecnica
                         where fecha >= '{0}' and fecha <= '{1} 23:59:59');

-- 5.4 Inventarios
select * from stocks.infinventarioresumenes;
select * from stocks.infinventarioelementos;

-- 5.5 Compras
select * from compras.albaranescpa where fecha >= '{0}' and fecha <= '{1} 23:59:59';
select * from compras.albaranescpadetalle
where albarancpaid in (select id from compras.albaranescpa
                       where fecha >= '{0}' and fecha <= '{1} 23:59:59');

-- 5.6 Prefacturación de recaudación
select * from facturacion.prefacrecauda where anho = {0} and mes = {1};
select * from facturacion.prefacrecaudadetalle
where prefacrecaudaid in (select id from facturacion.prefacrecauda where anho = {0} and mes = {1});
```

---

## Dos avisos de modelado

**La matrícula es la identificación, pero las ventas cuelgan del PDV.** El equipo identifica
las máquinas por matrícula (`recursos.maquinas.codigo`) y no usa el código de punto de
venta. Perfecto para la interfaz, pero en la base el histórico se engancha al `pdvid`: las
ventas, las visitas y la recaudación apuntan al punto de venta, no a la máquina. Como una
máquina cambia de sitio —lo vimos con la 24SE1983, que pasó de San Pablo Sur a ITC—,
**atribuir ventas antiguas a la máquina que hoy ocupa ese PDV es un error**. Para series
largas hay que reconstruir qué máquina estuvo en cada PDV en cada momento con
`vending.pdvshisinstalaciones` (consulta 3.8). Lo bueno es que `telemetry.telemetrysales`
trae **las dos** claves, `maquinaid` y `pdvid`, así que ahí el problema no existe.

**Volumen.** La consulta 2.1 devuelve una fila por venta. Con el ingreso de septiembre en
881.794 € y un precio medio de 0,85 €, la cartera entera mueve del orden de un millón de
transacciones al mes. Hay que pedirla **por días o por semanas**, o usar la 2.2 agregada.
Antes de lanzar cargas grandes conviene saber si la API tiene tope de filas o de tiempo:
ninguno de los informes catalogados lo dice.
