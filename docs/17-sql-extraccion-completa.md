# SQL de extracción: los informes que alimentan el almacén de datos

Un informe rápido de VenCloud por cada tabla destino. La Lambda los llama por su número, guarda
el resultado en S3 particionado por fecha, y la cabina lee de ahí.

## Convenciones

**Nombre**: `EXT_<AREA>_<TABLA>`, para que en el listado de VenCloud queden juntos y se distingan
de los informes de trabajo.

**Parámetros**: los incrementales llevan siempre dos, **FECHA DESDE (Orden 0)** y **FECHA HASTA
(Orden 1)**, tipo Fecha. Los maestros no llevan ninguno.

**Las tres reglas que ya nos costaron una tarde**:

1. Nada de `::`. Los castes van como `cast(x as text)`.
2. Nunca `sum(alias.columna)` en un informe con parámetros. Estas extracciones no agregan, así
   que no aplica, pero si alguna vez añades un total, mételo en una subconsulta.
3. En este modelo «sin referencia» es **0**, no nulo: `coalesce(campo,0) = 0`.
4. **Los partes del sistema se extraen, pero no se cuentan como visitas.** Dos tercios de las
   filas de `partesvisita` son partes automáticos (`tipo` 2 y 3, `empleadoid` 0, ruta -99, 0
   minutos, todos a las 00:00:09). No son visitas, pero traen lectura de máquina, así que **se
   bajan igual**: la extracción no filtra. Quien filtra es la cabina, y siempre que cuente
   visitas, tiempos o coste de servicio: `coalesce(empleadoid,0) <> 0 and tipo in (0, 100)`.
   Sin ese filtro los indicadores salen más del triple. Comprobado el 25/09: 3.504 filas, 1.107
   visitas reales ([21-visita-cabecera-25-09.md](21-visita-cabecera-25-09.md)).

**Toda fila lleva su `id`.** Es lo que permite que la carga sea idempotente: si una noche falla y
se repite, se actualiza la fila en vez de duplicarla.

**Las hijas de la visita se filtran por la fecha de la madre**, no por la suya. Así todas las
tablas de una misma noche contienen exactamente el mismo conjunto de visitas y cuadran entre sí.

---

# Tanda A · La visita y sus hijas

## A1 · EXT_VISITA_CABECERA

```sql
select
  p.id                       as parte_id,
  cast(p.fechaini as text)   as fecha_ini,
  cast(p.fechaejec as text)  as fecha_ejec,
  cast(p.fechaprev as text)  as fecha_prevista,
  cast(p.fechaaudit as text) as fecha_audit,
  p.tiempo                   as minutos,
  p.tipo                     as tipo_parte,
  p.estado                   as estado,
  p.origen                   as origen,
  m.codigo                   as matricula,
  pdv.codigo                 as cod_pdv,
  cen.numcentro              as num_centro,
  cen.denomina               as centro,
  del.nombre                 as delegacion,
  ru.codigo                  as cod_ruta,
  ru.denomina                as ruta,
  emp.codigo                 as cod_empleado,
  emp.nombre                 as empleado,
  veh.matricula              as vehiculo,
  p.recaudacion              as hay_recaudacion,
  p.imprecauda               as imp_recaudado,
  p.imprecmonedas            as imp_monedas,
  p.imprecbilletes           as imp_billetes,
  p.estadocontaje            as estado_contaje,
  p.codbolsa                 as cod_bolsa,
  p.codbolsaprecinto         as precinto_bolsa,
  p.estadobolsa              as estado_bolsa,
  cast(p.fechaverificabolsa as text) as fecha_verifica_bolsa,
  p.cambiocargado            as cambio_cargado,
  p.impdevolmon              as imp_devuelto,
  p.roboenmaquina            as robo,
  p.limpieza                 as limpieza,
  p.temperatura              as temp_marcada,
  p.tempvalor                as temp_valor,
  p.estadolec                as estado_lectura,
  p.estadorepo               as estado_reposicion,
  p.cal_totnumvtas           as vtas_num,
  p.cal_totimpvtas           as vtas_imp,
  p.cal_impvtasef            as vtas_efectivo,
  p.cal_impvtastp            as vtas_t_privada,
  p.cal_impvtastc            as vtas_t_credito,
  p.cal_beneficio            as beneficio,
  p.cal_impcajon             as imp_cajon,
  p.cal_imptubos             as imp_tubos,
  p.cal_impcarga             as imp_carga,
  p.cal_impcostecaducidad    as coste_caducidad,
  p.cal_impcosterotura       as coste_rotura,
  p.cal_impcosteinv          as coste_inventario,
  p.cal_cm                   as und_carga,
  p.cal_rc                   as und_ret_caducidad,
  p.cal_rm                   as und_rm,
  p.cal_rr                   as und_rr,
  p.cal_haydifprecios        as dif_precios,
  p.cal_numcambioscanal      as cambios_canal,
  p.numcanalesvacios         as canales_vacios,
  p.costevisita              as coste_visita,
  cast(p.fechavisitaanterior as text) as visita_anterior,
  p.maplatitud               as gps_lat,
  p.maplongitud              as gps_lon,
  p.posgpsfuerarango         as gps_fuera_rango,
  p.norealizable             as no_realizable,
  p.motnorealizable          as motivo_no_realizable
from vending.partesvisita p
left join recursos.maquinas m           on m.id   = p.maquinaid
left join vending.pdvs pdv              on pdv.id = p.pdvid
left join comercial.clientescentros cen on cen.id = p.clientecentroid
left join general.delegaciones del      on del.id = p.delegacionid
left join vending.rutas ru              on ru.id  = p.rutaid
left join recursos.empleados emp        on emp.id = p.empleadoid
left join recursos.vehiculos veh        on veh.id = p.vehiculoid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
order by p.fechaini
```

## A2 · EXT_VISITA_REPOSICIONES

```sql
select
  r.id           as id,
  r.partevisitaid as parte_id,
  m.codigo       as matricula,
  cast(r.fecha as text) as fecha,
  r.tipo         as tipo_linea,
  r.codcanal     as cod_canal,
  r.etiqcanal    as etiq_canal,
  r.cantidad     as cantidad,
  r.preciocoste  as precio_coste,
  a.codigo       as cod_articulo,
  a.denomina     as articulo
from vending.partesvisitareposiciones r
join vending.partesvisita p on p.id = r.partevisitaid
left join recursos.maquinas m on m.id = p.maquinaid
left join stocks.articulos a  on a.id = r.articuloid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
```

`tipo_linea` es `CM` carga, `RC` retirada por caducidad, y `RM`/`RR`, cuyo significado todavía
tienes que confirmarme.

**Probado el 25/09: 8.187 filas en 2 segundos.** Mediana de 5 líneas por visita. El mes entero
cabe de sobra en una llamada.

**Cuadra con el A1 sin una sola diferencia por parte**
([22-reposiciones-25-09.md](22-reposiciones-25-09.md)): `CM` = `cal_cm` (154.312 unidades),
`RC` = `cal_rc` y su coste = `cal_impcostecaducidad`, `RR` = `cal_rr` y su coste =
`cal_impcosterotura`.

**Cuidado con `cal_impcarga`: es carga NETA**, `CM − RC − RM − RR`. Para valorar lo cargado hay
que sumar las líneas `CM` de esta tabla, no leer el campo de la cabecera.

**`etiq_canal` es texto, no entero** (`11`, pero también `V58`, `A12`, `VI001`, `DC`), y
`cod_canal` viene a 0 en una de cada cinco filas: no sirve. Las líneas **sin `etiq_canal` son
carriles de máquina caliente** — azúcar, vasos, paletinas, café —, el 62 % de las unidades y sólo
el 19 % del coste. Hay que separarlas de las de canal en cualquier indicador.

## A3 · EXT_VISITA_INVENTARIO

```sql
select
  i.id            as id,
  i.partevisitaid as parte_id,
  m.codigo        as matricula,
  cast(i.fecha as text) as fecha,
  i.cantidad      as cantidad,
  i.capacmax      as capacidad_max,
  i.stockrecom    as stock_recomendado,
  i.difcapacidad  as dif_capacidad,
  i.huecosrecom   as huecos_recomendados,
  i.preciocoste   as precio_coste,
  a.codigo        as cod_articulo,
  a.denomina      as articulo
from vending.partesvisitarecinventarios i
join vending.partesvisita p on p.id = i.partevisitaid
left join recursos.maquinas m on m.id = p.maquinaid
left join stocks.articulos a  on a.id = i.articuloid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
```

## A4 · EXT_VISITA_INVCANALES

```sql
select
  c.id            as id,
  c.partevisitaid as parte_id,
  m.codigo        as matricula,
  cast(c.fecha as text) as fecha,
  c.numcanal      as num_canal,
  c.codcanal      as cod_canal,
  c.etiqcanal     as etiq_canal,
  c.cantidad      as cantidad,
  c.capacmax      as capacidad_max,
  c.stockrecom    as stock_recomendado,
  c.huecosrecom   as huecos_recomendados,
  a.codigo        as cod_articulo,
  a.denomina      as articulo
from vending.partesvisitainvcanales c
join vending.partesvisita p on p.id = c.partevisitaid
left join recursos.maquinas m on m.id = p.maquinaid
left join stocks.articulos a  on a.id = c.articuloid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
```

## A5 · EXT_VISITA_CONTAJES

La tabla más interesante de todo el paquete: guarda el importe anterior y quién lo cambió.

```sql
select
  c.id            as id,
  c.partevisitaid as parte_id,
  m.codigo        as matricula,
  cen.denomina    as centro,
  ru.denomina     as ruta,
  cast(c.fechacontaje as text) as fecha_contaje,
  c.modocontaje   as modo,
  c.registradopor as registrado_por,
  c.impmonedas    as imp_monedas,
  c.impbilletes   as imp_billetes,
  c.importe       as importe,
  c.impmonedasant as imp_monedas_anterior,
  c.impbilletesant as imp_billetes_anterior,
  c.editadopor    as editado_por,
  cast(c.fechaedicion as text) as fecha_edicion
from vending.partesvisitacontajes c
join vending.partesvisita p on p.id = c.partevisitaid
left join recursos.maquinas m           on m.id   = p.maquinaid
left join comercial.clientescentros cen on cen.id = p.clientecentroid
left join vending.rutas ru              on ru.id  = p.rutaid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
```

## A6 · EXT_VISITA_CONTAJES_DETALLE

```sql
select
  d.id          as id,
  d.partevisitacontajeid as contaje_id,
  c.partevisitaid as parte_id,
  m.codigo      as matricula,
  d.tipo        as tipo,
  d.valordinero as valor_moneda,
  d.cantidad    as cantidad,
  d.importe     as importe,
  d.manual      as introducido_a_mano
from vending.partesvisitacontajesdetalle d
join vending.partesvisitacontajes c on c.id = d.partevisitacontajeid
join vending.partesvisita p on p.id = c.partevisitaid
left join recursos.maquinas m on m.id = p.maquinaid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
```

## A7 · EXT_VISITA_MONBIL

Lo que la máquina dice que tiene, frente a lo que el reponedor cuenta.

```sql
select
  b.id            as id,
  b.partevisitaid as parte_id,
  m.codigo        as matricula,
  cast(p.fechaini as text) as fecha_visita,
  b.tipo          as tipo,
  b.valor         as valor,
  b.aceptadas     as aceptadas,
  b.aceptadasa    as aceptadas_acum,
  b.encajon       as en_cajon,
  b.encajona      as en_cajon_acum,
  b.entubos       as en_tubos,
  b.entubosa      as en_tubos_acum
from vending.partesvisitaauditmonbil b
join vending.partesvisita p on p.id = b.partevisitaid
left join recursos.maquinas m on m.id = p.maquinaid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
```

## A8 · EXT_VISITA_TUBOS

```sql
select
  t.id            as id,
  t.partevisitaid as parte_id,
  m.codigo        as matricula,
  cast(p.fechaini as text) as fecha_visita,
  t.tipo          as tipo,
  t.valor         as valor,
  t.cantactual    as cantidad_actual,
  t.cantactualdif as diferencia,
  t.tubolleno     as tubo_lleno
from vending.partesvisitaaudittubos t
join vending.partesvisita p on p.id = t.partevisitaid
left join recursos.maquinas m on m.id = p.maquinaid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
```

## A9 · EXT_VISITA_INCIDENCIAS

Caducado, rotura y robo, canal a canal. El dato de caducado que decías que es fundamental.

```sql
select
  i.id            as id,
  i.partevisitaid as parte_id,
  m.codigo        as matricula,
  cen.denomina    as centro,
  ru.denomina     as ruta,
  emp.nombre      as reponedor,
  cast(i.fecha as text) as fecha,
  i.tipo          as tipo_incidencia,
  i.codcanal      as cod_canal,
  i.etiqcanal     as etiq_canal,
  i.unidades      as unidades,
  i.nombrecliente as nombre_cliente,
  a.codigo        as cod_articulo,
  a.denomina      as articulo,
  a.puc           as puc
from vending.partesvisitaincidencias i
join vending.partesvisita p on p.id = i.partevisitaid
left join recursos.maquinas m           on m.id   = p.maquinaid
left join comercial.clientescentros cen on cen.id = p.clientecentroid
left join vending.rutas ru              on ru.id  = p.rutaid
left join recursos.empleados emp        on emp.id = p.empleadoid
left join stocks.articulos a            on a.id   = i.articuloid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
```

## A10 · EXT_VISITA_DEVOLUCIONES

```sql
select
  d.id            as id,
  d.partevisitaid as parte_id,
  m.codigo        as matricula,
  cen.denomina    as centro,
  emp.nombre      as reponedor,
  cast(d.fecha as text) as fecha,
  d.nombre        as nombre_cliente,
  d.dni           as dni,
  d.importe       as importe
from vending.partesvisitadevolclientes d
join vending.partesvisita p on p.id = d.partevisitaid
left join recursos.maquinas m           on m.id   = p.maquinaid
left join comercial.clientescentros cen on cen.id = p.clientecentroid
left join recursos.empleados emp        on emp.id = p.empleadoid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
```

**Este informe lleva DNI y nombre de personas.** No debe entrar nunca en la consola de cliente, y
en el almacén de datos conviene guardarlo en su propio prefijo, con acceso restringido.

## A11 · EXT_VISITA_VENTAS

```sql
select
  v.id            as id,
  v.partevisitaid as parte_id,
  m.codigo        as matricula,
  cast(p.fechaini as text) as fecha_visita,
  v.tipo          as tipo,
  a.codigo        as cod_articulo,
  a.denomina      as articulo,
  v.costeunit     as coste_unitario,
  v.beneficio     as beneficio,
  v.numvtasef     as num_efectivo,
  v.impvtasef     as imp_efectivo,
  v.numvtastp     as num_t_privada,
  v.impvtastp     as imp_t_privada,
  v.numvtastc     as num_t_credito,
  v.impvtastc     as imp_t_credito,
  v.totnumvtas    as num_total,
  v.totimpvtas    as imp_total,
  v.totimpvtassiniva as imp_total_sin_iva
from vending.partesvisitaventas v
join vending.partesvisita p on p.id = v.partevisitaid
left join recursos.maquinas m on m.id = p.maquinaid
left join stocks.articulos a  on a.id = v.articuloid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
```

---

# Tanda B · El dinero

## B1 · EXT_DINERO_BOLSAS

```sql
select
  b.id          as id,
  cast(b.fechareg as text) as fecha_registro,
  b.numbolsas   as num_bolsas,
  b.tipobolsa   as tipo_bolsa,
  b.observaciones as observaciones,
  ru.codigo     as cod_ruta,
  ru.denomina   as ruta,
  rep.codigo    as cod_reponedor,
  rep.nombre    as reponedor,
  reg.nombre    as registrado_por,
  del.nombre    as delegacion,
  case when coalesce(b.firma,'') = '' then 0 else 1 end as tiene_firma
from vending.recogidasbolsasrec b
left join vending.rutas ru         on ru.id  = b.rutaid
left join recursos.empleados rep   on rep.id = b.reponedorid
left join recursos.empleados reg   on reg.id = b.registradoporid
left join general.delegaciones del on del.id = b.delegacionid
where b.fechareg >= '{0}' and b.fechareg <= '{1} 23:59:59'
order by b.fechareg
```

Si `firma` no fuera de texto, quita esa última línea: sirve sólo para saber si hay firma sin
arrastrar la imagen, que pesa.

## B2 · EXT_DINERO_BOLSAS_DETALLE

```sql
select
  d.id            as id,
  d.recogidabolsasrecid as recogida_id,
  d.codbolsa      as cod_bolsa,
  d.maqcodigo     as matricula,
  d.maqmodelo     as modelo,
  d.pdvcodigo     as cod_pdv,
  d.pdvubic       as ubicacion,
  d.cliente       as cliente,
  d.partevisitaid as parte_id,
  cast(d.partevisitafecharec as text) as fecha_recaudacion
from vending.recogidasbolsasrecdetalles d
join vending.recogidasbolsasrec b on b.id = d.recogidabolsasrecid
where b.fechareg >= '{0}' and b.fechareg <= '{1} 23:59:59'
```

Con B1, B2 y A5 sale el indicador que te falta: **bolsa recaudada, bolsa entregada, y los días
que pasan entre una cosa y la otra.**

## B3 · EXT_DINERO_RECAUDACION

```sql
select
  r.id             as id,
  cast(r.fecha as text) as fecha,
  r.anho           as anho,
  r.mes            as mes,
  r.dia            as dia,
  cast(r.fechacontable as text) as fecha_contable,
  r.estado         as estado,
  r.critcalculo    as criterio_calculo,
  r.criteriodesccambio as criterio_desc_cambio,
  r.formapago      as forma_pago,
  r.tipotelemetria as tipo_telemetria,
  r.imprecaudado   as imp_recaudado,
  r.cambiocargado  as cambio_cargado,
  r.imppagobancario as imp_pago_bancario,
  r.imprecargasbancarias as imp_recargas,
  r.impdevolreclama as imp_devoluciones,
  r.imptotalconiva as imp_total_con_iva,
  m.codigo         as matricula,
  pdv.codigo       as cod_pdv,
  del.nombre       as delegacion
from facturacion.prefacrecauda r
left join recursos.maquinas m      on m.id   = r.maquinaid
left join vending.pdvs pdv         on pdv.id = r.pdvid
left join general.delegaciones del on del.id = r.delegacionid
where r.fecha >= '{0}' and r.fecha <= '{1} 23:59:59'
order by r.fecha
```

## B4 · EXT_DINERO_RECAUDACION_DETALLE

```sql
select
  d.id             as id,
  d.prefacrecaudaid as recaudacion_id,
  d.codigo         as codigo,
  d.descripcion    as descripcion,
  d.impsiniva      as imp_sin_iva,
  d.cuota          as cuota_iva,
  d.impconiva      as imp_con_iva,
  d.tipiva         as tipo_iva,
  d.poriva         as por_iva,
  d.porcentaje     as porcentaje
from facturacion.prefacrecaudadetalle d
join facturacion.prefacrecauda r on r.id = d.prefacrecaudaid
where r.fecha >= '{0}' and r.fecha <= '{1} 23:59:59'
```

## B5 · EXT_DINERO_BANCO

```sql
select
  d.id            as id,
  d.pdvtransbancariaid as remesa_id,
  cast(d.fechatrans as text)    as fecha_transaccion,
  cast(d.fechatransutc as text) as fecha_transaccion_utc,
  d.transaccionid as id_transaccion,
  d.tpvnumero     as num_tpv,
  d.valor         as valor,
  d.impcomision   as comision,
  d.tipo          as tipo,
  d.estado        as estado,
  d.incidencia    as incidencia,
  m.codigo        as matricula,
  pdv.codigo      as cod_pdv,
  ru.denomina     as ruta
from vending.pdvstransbancariasdetalles d
left join recursos.maquinas m on m.id   = d.maquinaid
left join vending.pdvs pdv    on pdv.id = d.pdvid
left join vending.rutas ru    on ru.id  = d.rutaid
where d.fechatrans >= '{0}' and d.fechatrans <= '{1} 23:59:59'
order by d.fechatrans
```

`id_transaccion` es la clave del cuadre: se cruza con `telemetry.telemetrysales.transactionid`
para ver qué vendió la máquina frente a qué abonó el banco, con la comisión aparte.

## B6 · EXT_DINERO_CASHLESS

```sql
select
  g.id            as id,
  g.partevisitaid as parte_id,
  m.codigo        as matricula,
  cast(p.fechaini as text) as fecha_visita,
  g.cal_usergroup_numvtas   as grupo_num,
  g.cal_usergroup_impvtas   as grupo_imp,
  g.cal_usergroup_imprecargas as grupo_recargas,
  g.cal_usertype_numvtas    as tipousuario_num,
  g.cal_usertype_impvtas    as tipousuario_imp,
  g.cal_freeproduct_numvtas as gratuito_num,
  g.cal_freeproduct_impvtas as gratuito_imp,
  g.cal_freecredit_impvtas  as credito_gratis_imp,
  g.cal_promoproduct_numvtas as promo_num,
  g.cal_promoproduct_impvtas as promo_imp,
  g.cal_promocredit_impvtas as promo_credito_imp,
  g.cal_specialday_impvtas  as dia_especial_imp,
  g.cal_birthday_impvtas    as cumpleanos_imp,
  g.cal_productcombi_impvtas as combinado_imp
from vending.partesvisitaauditcashlessgroups g
join vending.partesvisita p on p.id = g.partevisitaid
left join recursos.maquinas m on m.id = p.maquinaid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
```

---

# Tanda C · El stock

## C1 · EXT_STOCK_MOV_ALMACEN

```sql
select
  d.id          as id,
  cast(d.fecha as text) as fecha,
  d.tipomov     as tipo_mov,
  d.motivo      as motivo,
  d.cantidad    as cantidad,
  d.existen     as existencia_resultante,
  d.pmc         as pmc,
  d.puc         as puc,
  d.preciocoste as precio_coste,
  d.usuario     as usuario,
  d.documento   as documento,
  d.origendestino as origen_destino,
  d.difinventario as dif_inventario,
  al.codigo     as cod_almacen,
  al.nombre     as almacen,
  a.codigo      as cod_articulo,
  a.denomina    as articulo,
  d.diarmovvehid as mov_vehiculo_id,
  d.diarmovmaqid as mov_maquina_id,
  d.traspasostockid as traspaso_id,
  d.regularizacionid as regularizacion_id,
  d.partevisitareposicionid as reposicion_id
from stocks.diarmovalm d
left join recursos.almacenes al on al.id = d.almacenid
left join stocks.articulos a    on a.id  = d.articuloid
where d.fecha >= '{0}' and d.fecha <= '{1} 23:59:59'
order by d.fecha
```

## C2 · EXT_STOCK_MOV_VEHICULO

```sql
select
  d.id          as id,
  cast(d.fecha as text) as fecha,
  d.tipomov     as tipo_mov,
  d.motivo      as motivo,
  d.cantidad    as cantidad,
  d.existen     as existencia_resultante,
  d.puc         as puc,
  d.preciocoste as precio_coste,
  d.usuario     as usuario,
  d.documento   as documento,
  d.origendestino as origen_destino,
  d.difinventario as dif_inventario,
  v.codigo      as cod_vehiculo,
  v.matricula   as matricula_vehiculo,
  a.codigo      as cod_articulo,
  a.denomina    as articulo,
  d.diarmovalmid as mov_almacen_id,
  d.diarmovmaqid as mov_maquina_id,
  d.partevisitareposicionid as reposicion_id
from stocks.diarmovveh d
left join recursos.vehiculos v on v.id = d.vehiculoid
left join stocks.articulos a   on a.id = d.articuloid
where d.fecha >= '{0}' and d.fecha <= '{1} 23:59:59'
order by d.fecha
```

## C3 · EXT_STOCK_MOV_MAQUINA

```sql
select
  d.id          as id,
  cast(d.fecha as text) as fecha,
  d.tipomov     as tipo_mov,
  d.motivo      as motivo,
  d.cantidad    as cantidad,
  d.existen     as existencia_resultante,
  d.puc         as puc,
  d.preciocoste as precio_coste,
  d.empleado    as empleado,
  d.clientecentro as centro,
  d.ruta        as ruta,
  d.vehiculo    as vehiculo,
  d.difinventario as dif_inventario,
  m.codigo      as matricula,
  a.codigo      as cod_articulo,
  a.denomina    as articulo,
  d.diarmovalmid as mov_almacen_id,
  d.diarmovvehid as mov_vehiculo_id,
  d.partevisitarecinventarioid as inventario_id,
  d.partevisitareposicionid    as reposicion_id,
  d.partevisitaincidenciaid    as incidencia_id
from stocks.diarmovmaq d
left join recursos.maquinas m on m.id = d.maquinaid
left join stocks.articulos a  on a.id = d.articuloid
where d.fecha >= '{0}' and d.fecha <= '{1} 23:59:59'
order by d.fecha
```

**C1, C2 y C3 juntos son la trazabilidad completa.** Cada fila apunta a la del eslabón anterior,
así que se puede seguir una unidad desde que entra en el almacén hasta que se vende.

## C4 · EXT_STOCK_TRASPASOS

```sql
select
  t.id           as id,
  t.numero       as numero,
  cast(t.fechacrea as text)    as fecha_crea,
  cast(t.fechasalida as text)  as fecha_salida,
  cast(t.fechaentrada as text) as fecha_entrada,
  t.estado       as estado,
  t.tipotraspaso as tipo_traspaso,
  t.tipoproducto as tipo_producto,
  t.tipoorigen   as tipo_origen,
  t.tipodestino  as tipo_destino,
  t.motivo       as motivo,
  t.registradopor as registrado_por,
  t.recepcionadopor as recepcionado_por,
  t.notas        as notas,
  dor.nombre     as delegacion_origen,
  des.nombre     as delegacion_destino
from stocks.traspasosstock t
left join general.delegaciones dor on dor.id = t.delegacionorigenid
left join general.delegaciones des on des.id = t.delegaciondestinoid
where t.fechacrea >= '{0}' and t.fechacrea <= '{1} 23:59:59'
```

## C5 · EXT_STOCK_REGULARIZACIONES

```sql
select
  r.id           as id,
  r.numero       as numero,
  cast(r.fecha as text)     as fecha,
  cast(r.fechacrea as text) as fecha_crea,
  r.tipo         as tipo,
  r.tiporegularizacion as tipo_regularizacion,
  r.tipoproducto as tipo_producto,
  r.registradopor as registrado_por,
  r.notas        as notas,
  del.nombre     as delegacion,
  emp.nombre     as empleado
from stocks.regularizacionesstock r
left join general.delegaciones del on del.id = r.delegacionid
left join recursos.empleados emp   on emp.id = r.empleadoid
where r.fecha >= '{0}' and r.fecha <= '{1} 23:59:59'
```

## C6 · EXT_STOCK_RECOGIDAS

Caducado y rotura separados, que es justo lo que pedías.

```sql
select
  d.id             as id,
  d.planrecogidaid as recogida_id,
  cast(p.fecha as text) as fecha,
  p.realizadopor   as realizado_por,
  ru.codigo        as cod_ruta,
  ru.denomina      as ruta,
  v.matricula      as vehiculo,
  a.codigo         as cod_articulo,
  a.denomina       as articulo,
  a.puc            as puc,
  d.cantstock      as cant_stock,
  d.cantretirada   as cant_retirada,
  d.cantcaducada   as cant_caducada,
  d.cantrotura     as cant_rotura
from stocks.planrecogidadetalle d
join stocks.planrecogida p on p.id = d.planrecogidaid
left join vending.rutas ru     on ru.id = p.rutaid
left join recursos.vehiculos v on v.id  = p.vehiculoid
left join stocks.articulos a   on a.id  = d.articuloid
where p.fecha >= '{0}' and p.fecha <= '{1} 23:59:59'
```

## C7 · EXT_STOCK_PLANCARGA

Lo planificado frente a lo confirmado.

```sql
select
  d.id            as id,
  d.plancargarutavehiculoid as plancarga_id,
  cast(c.fechaplan as text)    as fecha_plan,
  cast(c.fechaentrega as text) as fecha_entrega,
  c.estado        as estado,
  c.tipo          as tipo,
  ru.codigo       as cod_ruta,
  ru.denomina     as ruta,
  v.matricula     as vehiculo,
  a.codigo        as cod_articulo,
  a.denomina      as articulo,
  d.cantcalculada as cant_calculada,
  d.cantpedida    as cant_pedida,
  d.cantconfirmada as cant_confirmada,
  d.unidpack      as unid_pack,
  d.nivelfondo    as nivel_fondo,
  d.stockafecha   as stock_a_fecha,
  d.confirmado    as confirmado,
  d.verificado    as verificado
from stocks.plancargarutavehiculodetalle d
join stocks.plancargarutavehiculo c on c.id = d.plancargarutavehiculoid
left join vending.rutas ru     on ru.id = c.rutaid
left join recursos.vehiculos v on v.id  = c.vehiculoid
left join stocks.articulos a   on a.id  = d.articuloid
where c.fechaplan >= '{0}' and c.fechaplan <= '{1} 23:59:59'
```

## C8 · EXT_STOCK_RETORNOS

```sql
select
  d.id              as id,
  d.planretornoprodid as retorno_id,
  cast(r.fechacrea as text)      as fecha_crea,
  cast(r.fechaverifrepo as text) as fecha_verif_reponedor,
  cast(r.fechaverifalm as text)  as fecha_verif_almacen,
  r.estado          as estado,
  r.registradopor   as registrado_por,
  ru.denomina       as ruta,
  v.matricula       as vehiculo,
  a.codigo          as cod_articulo,
  a.denomina        as articulo,
  d.tipo            as tipo,
  d.cantstock       as cant_stock,
  d.cantverifrepo   as cant_verif_reponedor,
  d.cantverifalmacen as cant_verif_almacen,
  d.verificado      as verificado
from stocks.planesretornoproddetalles d
join stocks.planesretornoprod r on r.id = d.planretornoprodid
left join vending.rutas ru     on ru.id = r.rutaid
left join recursos.vehiculos v on v.id  = r.vehiculoid
left join stocks.articulos a   on a.id  = d.articuloid
where r.fechacrea >= '{0}' and r.fechacrea <= '{1} 23:59:59'
```

## C9 · EXT_STOCK_INVENTARIOS_ALM

```sql
select
  e.id           as id,
  e.infinventarioresumenid as resumen_id,
  cast(r.fecha as text) as fecha,
  r.anho         as anho,
  r.mes          as mes,
  r.estado       as estado_resumen,
  r.critcoste    as criterio_coste,
  r.tipoagrup    as tipo_agrupacion,
  e.tipoalm      as tipo_elemento,
  e.estado       as estado_elemento,
  e.cantidadtotal as cantidad_total,
  e.valortotal   as valor_total,
  cast(e.fechaultinventario as text) as fecha_ult_inventario,
  al.codigo      as cod_almacen,
  al.nombre      as almacen,
  v.matricula    as vehiculo,
  m.codigo       as matricula,
  del.nombre     as delegacion
from stocks.infinventarioelementos e
join stocks.infinventarioresumenes r on r.id = e.infinventarioresumenid
left join recursos.almacenes al    on al.id  = e.almacenid
left join recursos.vehiculos v     on v.id   = e.vehiculoid
left join recursos.maquinas m      on m.id   = e.maquinaid
left join general.delegaciones del on del.id = r.delegacionid
where r.fecha >= '{0}' and r.fecha <= '{1} 23:59:59'
```

## C10 · EXT_STOCK_INVENTARIOS_ALM_PROD

```sql
select
  p.id            as id,
  p.infinventarioelementoid as elemento_id,
  a.codigo        as cod_articulo,
  a.denomina      as articulo,
  p.cantidad      as cantidad,
  p.preciocoste   as precio_coste,
  p.valor         as valor
from stocks.infinventarioelementosprods p
join stocks.infinventarioelementos e on e.id = p.infinventarioelementoid
join stocks.infinventarioresumenes r on r.id = e.infinventarioresumenid
left join stocks.articulos a on a.id = p.articuloid
where r.fecha >= '{0}' and r.fecha <= '{1} 23:59:59'
```

---

# Tanda D · Rutas y SAT

## D1 · EXT_RUTAS_MAESTRO  *(sin parámetros)*

```sql
select
  r.id          as id,
  r.codigo      as cod_ruta,
  r.refexterna  as ref_externa,
  r.denomina    as ruta,
  r.activa      as activa,
  r.tipo        as tipo,
  cast(r.fechainicio as text) as fecha_inicio,
  r.minimovisitas as min_visitas,
  r.maximovisitas as max_visitas,
  r.sabado      as visita_sabado,
  r.domingo     as visita_domingo,
  r.horainicio  as hora_inicio,
  r.tiemporuta  as tiempo_ruta,
  r.vaciarvehiculo as vaciar_vehiculo,
  emp.nombre    as reponedor_titular,
  sup.nombre    as supervisor,
  tec.nombre    as tecnico,
  v.matricula   as vehiculo,
  al.nombre     as almacen,
  del.nombre    as delegacion
from vending.rutas r
left join recursos.empleados emp   on emp.id = r.empleadoid
left join recursos.empleados sup   on sup.id = r.supervisorid
left join recursos.empleados tec   on tec.id = r.tecnicoid
left join recursos.vehiculos v     on v.id   = r.vehiculoid
left join recursos.almacenes al    on al.id  = r.almacenid
left join general.delegaciones del on del.id = r.delegacionid
order by del.nombre, r.codigo
```

Ojo con esto, que ya nos mordió una vez: **`cod_ruta` se repite entre delegaciones.** La clave es
delegación + código, o `ref_externa`. Nunca agrupes sólo por `cod_ruta`.

## D2 · EXT_RUTAS_PDVS  *(sin parámetros)*

```sql
select
  d.id        as id,
  r.codigo    as cod_ruta,
  r.denomina  as ruta,
  del.nombre  as delegacion,
  d.norden    as orden,
  d.grupo     as grupo,
  d.turno     as turno,
  d.activo    as activo,
  cast(d.fechainicio as text) as fecha_inicio,
  pdv.codigo  as cod_pdv,
  m.codigo    as matricula,
  cen.numcentro as num_centro,
  cen.denomina  as centro
from vending.rutasdetalle d
join vending.rutas r                    on r.id   = d.rutaid
left join vending.pdvs pdv              on pdv.id = d.pdvid
left join recursos.maquinas m           on m.id   = pdv.maquinaid
left join comercial.clientescentros cen on cen.id = pdv.clientecentroid
left join general.delegaciones del      on del.id = r.delegacionid
order by del.nombre, r.codigo, d.norden
```

## D3 · EXT_RUTAS_CRITERIOS  *(sin parámetros)*

```sql
select
  c.id        as id,
  c.rutadetalleid as ruta_detalle_id,
  r.codigo    as cod_ruta,
  r.denomina  as ruta,
  pdv.codigo  as cod_pdv,
  m.codigo    as matricula,
  c.criterio  as criterio,
  c.numero    as numero,
  c.grupo     as grupo,
  c.turno     as turno,
  c.l1 as lun_1, c.m1 as mar_1, c.x1 as mie_1, c.j1 as jue_1, c.v1 as vie_1, c.s1 as sab_1, c.d1 as dom_1,
  c.l2 as lun_2, c.m2 as mar_2, c.x2 as mie_2, c.j2 as jue_2, c.v2 as vie_2, c.s2 as sab_2, c.d2 as dom_2,
  c.criteriorecaudacion as criterio_recaudacion,
  c.lrecauda1 as lun_rec, c.mrecauda1 as mar_rec, c.xrecauda1 as mie_rec,
  c.jrecauda1 as jue_rec, c.vrecauda1 as vie_rec, c.srecauda1 as sab_rec, c.drecauda1 as dom_rec,
  c.valorlimiterec as limite_recaudacion,
  c.visitasabado as visita_sabado,
  c.visitadomingo as visita_domingo
from vending.rutasdetallecriterios c
left join vending.rutasdetalle d on d.id   = c.rutadetalleid
left join vending.rutas r        on r.id   = d.rutaid
left join vending.pdvs pdv       on pdv.id = d.pdvid
left join recursos.maquinas m    on m.id   = pdv.maquinaid
```

`valorlimiterec` es el umbral de recaudación por criterio. Ahí es donde habría que reflejar tu
regla de los 100 € en bolsa, y donde se comprobará si alguien la tiene puesta.

## D4 · EXT_RUTAS_OPERARIOS  *(sin parámetros)*

```sql
select
  o.id       as id,
  r.codigo   as cod_ruta,
  r.denomina as ruta,
  del.nombre as delegacion,
  e.codigo   as cod_empleado,
  e.nombre   as empleado,
  cast(o.desde as text) as desde,
  cast(o.hasta as text) as hasta
from vending.rutasoperarios o
join vending.rutas r               on r.id   = o.rutaid
left join recursos.empleados e     on e.id   = o.empleadoid
left join general.delegaciones del on del.id = r.delegacionid
```

## D5 · EXT_RUTAS_JORNADAS

La jornada real del reponedor.

```sql
select
  c.id        as id,
  r.codigo    as cod_ruta,
  r.denomina  as ruta,
  del.nombre  as delegacion,
  e.nombre    as empleado,
  v.matricula as vehiculo,
  cast(c.fechaini as text)    as inicio,
  cast(c.fechafin as text)    as fin,
  cast(c.fechacierre as text) as cierre,
  c.kminiciales as km_inicio,
  c.kmfinales   as km_fin,
  c.temperaturaini as temperatura_inicio,
  c.incidencias as incidencias,
  c.maplatitudini as gps_lat_ini,
  c.maplongitudini as gps_lon_ini,
  c.maplatitudfin as gps_lat_fin,
  c.maplongitudfin as gps_lon_fin,
  c.coddispositivo as dispositivo
from vending.rutascontrol c
left join vending.rutas r          on r.id   = c.rutaid
left join recursos.empleados e     on e.id   = c.empleadoid
left join recursos.vehiculos v     on v.id   = c.vehiculoid
left join general.delegaciones del on del.id = r.delegacionid
where c.fechaini >= '{0}' and c.fechaini <= '{1} 23:59:59'
order by c.fechaini
```

Recuerda que `01/01/1900` es el centinela de «sin cerrar»: filtra con `fechacierre > '1900-01-02'`
cuando calcules duraciones.

## D6 · EXT_RUTAS_FONDOS  *(sin parámetros)*

```sql
select
  f.id       as id,
  r.codigo   as cod_ruta,
  r.denomina as ruta,
  a.codigo   as cod_articulo,
  a.denomina as articulo,
  f.cantidad as cantidad,
  f.stocklimite as stock_limite,
  f.bloqueado as bloqueado
from vending.rutasfondosfijos f
join vending.rutas r         on r.id = f.rutaid
left join stocks.articulos a on a.id = f.articuloid
```

## D7 · EXT_SAT_AVERIAS

```sql
select
  t.id          as id,
  t.numero      as numero,
  t.serie       as serie,
  cast(t.fecha as text)         as fecha_alta,
  cast(t.fechaprevista as text) as fecha_prevista,
  cast(t.fechafin as text)      as fecha_fin,
  t.tipotarea   as tipo_tarea,
  t.tipoelemento as tipo_elemento,
  t.titulo      as titulo,
  t.estado      as estado,
  t.tipoestado  as tipo_estado,
  t.severidad   as severidad,
  t.origen      as origen,
  t.registradopor as registrado_por,
  t.arearesponsable as area_responsable,
  t.maquinaparada as maquina_parada,
  t.slapausado  as sla_pausado,
  t.facturable  as facturable,
  t.pdvubicacion as ubicacion,
  op.codigo     as cod_operacion,
  op.nombre     as operacion,
  cat.nombre    as categoria,
  m.codigo      as matricula,
  pdv.codigo    as cod_pdv,
  cen.numcentro as num_centro,
  cen.denomina  as centro,
  emp.nombre    as tecnico_asignado,
  del.nombre    as delegacion
from sat.tareatecnica t
left join configuracion.satoperaciones op            on op.id  = t.satoperacionid
left join configuracion.satoperacionescategorias cat on cat.id = op.satoperacioncategoriaid
left join recursos.maquinas m           on m.id   = t.maquinaid
left join vending.pdvs pdv              on pdv.id = t.pdvid
left join comercial.clientescentros cen on cen.id = t.clientecentroid
left join recursos.empleados emp        on emp.id = t.empasignadoid
left join general.delegaciones del      on del.id = t.delegacionid
where t.fecha >= '{0}' and t.fecha <= '{1} 23:59:59'
order by t.fecha
```

## D8 · EXT_SAT_EVENTOS

El histórico de estados: **de aquí sale el tiempo de respuesta de verdad.**

```sql
select
  l.id           as id,
  l.tareatecnicaid as averia_id,
  t.numero       as numero,
  m.codigo       as matricula,
  cast(l.fecha as text) as fecha,
  l.estado       as estado,
  l.arearesponsable as area,
  l.asignadoa    as asignado_a,
  l.maquinaparada as maquina_parada,
  l.notas        as notas
from sat.tareatecnicaeventoslog l
join sat.tareatecnica t on t.id = l.tareatecnicaid
left join recursos.maquinas m on m.id = t.maquinaid
where t.fecha >= '{0}' and t.fecha <= '{1} 23:59:59'
order by l.tareatecnicaid, l.fecha
```

## D9 · EXT_SAT_VISITAS

```sql
select
  v.id           as id,
  v.tareatecnicaid as averia_id,
  t.numero       as numero,
  m.codigo       as matricula,
  cast(v.fechaini as text) as inicio,
  cast(v.fechafin as text) as fin,
  v.canttiempo   as tiempo,
  v.costeunittiempo as coste_hora,
  v.impcostetiempo  as coste_tiempo,
  v.costevisita  as coste_visita,
  v.estado       as estado,
  v.origen       as origen,
  e.nombre       as tecnico,
  veh.matricula  as vehiculo,
  v.gpslatitud   as gps_lat,
  v.gpslongitud  as gps_lon,
  v.notasrealizacion as notas
from sat.tareatecnicavisita v
join sat.tareatecnica t on t.id = v.tareatecnicaid
left join recursos.maquinas m    on m.id   = t.maquinaid
left join recursos.empleados e   on e.id   = v.emprealizaid
left join recursos.vehiculos veh on veh.id = v.vehiculoid
where t.fecha >= '{0}' and t.fecha <= '{1} 23:59:59'
```

## D10 · EXT_SAT_MATERIALES

```sql
select
  mt.id          as id,
  mt.tareatecnicavisitaid as visita_id,
  t.numero       as numero,
  m.codigo       as matricula,
  cast(v.fechaini as text) as fecha,
  a.codigo       as cod_recambio,
  a.denomina     as recambio,
  mt.referenciarecambio as referencia,
  mt.unidades    as unidades,
  mt.costeunidad as coste_unidad,
  mt.impcoste    as coste_total,
  mt.estadodevolalmacen as estado_devolucion
from sat.tareatecnicavisitamaterial mt
join sat.tareatecnicavisita v on v.id = mt.tareatecnicavisitaid
join sat.tareatecnica t       on t.id = v.tareatecnicaid
left join recursos.maquinas m on m.id = t.maquinaid
left join stocks.articulos a  on a.id = mt.recambioid
where t.fecha >= '{0}' and t.fecha <= '{1} 23:59:59'
```

## D11 · EXT_SAT_CATALOGO  *(sin parámetros)*

```sql
select
  op.id        as id,
  op.codigo    as codigo,
  op.nombre    as operacion,
  op.tipo      as tipo,
  op.severidad as severidad,
  op.tiempoestimado as tiempo_estimado,
  op.averiarapida   as averia_rapida,
  op.tipoasignacion as tipo_asignacion,
  op.desactivada    as desactivada,
  cat.nombre   as categoria,
  cat.tipo     as tipo_categoria,
  f.nombre     as fabricante
from configuracion.satoperaciones op
left join configuracion.satoperacionescategorias cat on cat.id = op.satoperacioncategoriaid
left join general.fabricantes f on f.id = op.fabricanteid
order by cat.nombre, op.codigo
```

---

# Maestros

Los cinco volcados de maestro ya están escritos en `docs/08-sql-relleno.md`, bloque 5: artículos,
máquinas, puntos de venta y planograma de canales. Faltan tres, que van aquí.

## M1 · EXT_MAESTRO_CARRILES  *(sin parámetros)*

El planograma de las máquinas calientes, que es la mitad que faltaba.

```sql
select
  c.id       as id,
  m.codigo   as matricula,
  c.numero   as carril,
  c.tipomateriaprima as tipo_materia,
  c.formato  as formato,
  c.virtual  as virtual,
  c.extra    as extra,
  c.capacmax as capacidad_max,
  c.stockrecom as stock_recomendado,
  c.cargaminima as carga_minima,
  c.refexterna  as ref_externa,
  a.codigo   as cod_articulo,
  a.denomina as articulo,
  a.puc      as puc,
  a.unidcaja as unid_caja,
  a.unidmedida as unidad_medida
from recursos.maquinascarriles c
join recursos.maquinas m on m.id = c.maquinaid
left join stocks.articulos a on a.id = c.articuloid
order by m.codigo, c.numero
```

## M2 · EXT_MAESTRO_RECETAS  *(sin parámetros)*

```sql
select
  d.id       as id,
  a.codigo   as cod_bebida,
  a.denomina as bebida,
  a.clase    as clase,
  a.precioventa as precio_venta,
  d.orden    as orden,
  d.tipomateriaprima as tipo_materia,
  d.tipounidad as unidad,
  d.cantunidad as cantidad
from stocks.articulosdetalle d
join stocks.articulos a on a.id = d.articuloid
order by a.codigo, d.orden
```

## M3 · EXT_MAESTRO_ALMACENES  *(sin parámetros)*

```sql
select
  al.id      as id,
  al.codigo  as cod_almacen,
  al.nombre  as almacen,
  al.tipo    as tipo,
  al.activo  as activo,
  al.codigo_sap as cod_sap,
  al.refexterna as ref_externa,
  al.incluirinfinventario as entra_en_inventario,
  al.salidasalmsoloconstock as salidas_solo_con_stock,
  del.nombre as delegacion,
  dir.ciudad as ciudad,
  dir.provincia as provincia
from recursos.almacenes al
left join general.delegaciones del on del.id = al.delegacionid
left join general.direcciones dir  on dir.id = al.direccionid
```

## M4 · EXT_MAESTRO_VEHICULOS  *(sin parámetros)*

```sql
select
  v.id        as id,
  v.codigo    as cod_vehiculo,
  v.denomina  as denominacion,
  v.matricula as matricula,
  v.activo    as activo,
  v.obsoleto  as obsoleto,
  v.ceco      as centro_coste,
  mo.nombre   as modelo,
  del.nombre  as delegacion
from recursos.vehiculos v
left join recursos.vehiculosmodelos mo on mo.id = v.vehiculomodeloid
left join general.delegaciones del     on del.id = v.delegacionid
```

---

# El manifiesto para la Lambda

Cuando tengas los informes creados y sepas su número, esto es lo que va en la variable de entorno
`INFORMES`. Sustituye cada `NNN`.

```json
{
  "visita_cabecera":   {"informe":"NNN","fechas":"ayer","ruta":"crudo/visita_cabecera"},
  "visita_reposicion": {"informe":"NNN","fechas":"ayer","ruta":"crudo/visita_reposicion"},
  "visita_inventario": {"informe":"NNN","fechas":"ayer","ruta":"crudo/visita_inventario"},
  "visita_invcanales": {"informe":"NNN","fechas":"ayer","ruta":"crudo/visita_invcanales"},
  "visita_contajes":   {"informe":"NNN","fechas":"ayer","ruta":"crudo/visita_contajes"},
  "visita_contajes_det":{"informe":"NNN","fechas":"ayer","ruta":"crudo/visita_contajes_det"},
  "visita_monbil":     {"informe":"NNN","fechas":"ayer","ruta":"crudo/visita_monbil"},
  "visita_tubos":      {"informe":"NNN","fechas":"ayer","ruta":"crudo/visita_tubos"},
  "visita_incidencias":{"informe":"NNN","fechas":"ayer","ruta":"crudo/visita_incidencias"},
  "visita_devoluciones":{"informe":"NNN","fechas":"ayer","ruta":"restringido/devoluciones"},
  "visita_ventas":     {"informe":"NNN","fechas":"ayer","ruta":"crudo/visita_ventas"},

  "telemetria_ventas": {"informe":"NNN","fechas":"ayer","ruta":"crudo/telemetria_ventas"},

  "dinero_bolsas":     {"informe":"NNN","fechas":"ayer","ruta":"crudo/dinero_bolsas"},
  "dinero_bolsas_det": {"informe":"NNN","fechas":"ayer","ruta":"crudo/dinero_bolsas_det"},
  "dinero_recaudacion":{"informe":"NNN","fechas":"ayer","ruta":"crudo/dinero_recaudacion"},
  "dinero_recauda_det":{"informe":"NNN","fechas":"ayer","ruta":"crudo/dinero_recauda_det"},
  "dinero_banco":      {"informe":"NNN","fechas":"ayer","ruta":"crudo/dinero_banco"},
  "dinero_cashless":   {"informe":"NNN","fechas":"ayer","ruta":"crudo/dinero_cashless"},

  "stock_mov_almacen": {"informe":"NNN","fechas":"ayer","ruta":"crudo/stock_mov_almacen"},
  "stock_mov_vehiculo":{"informe":"NNN","fechas":"ayer","ruta":"crudo/stock_mov_vehiculo"},
  "stock_mov_maquina": {"informe":"NNN","fechas":"ayer","ruta":"crudo/stock_mov_maquina"},
  "stock_traspasos":   {"informe":"NNN","fechas":"ayer","ruta":"crudo/stock_traspasos"},
  "stock_regulariza":  {"informe":"NNN","fechas":"ayer","ruta":"crudo/stock_regulariza"},
  "stock_recogidas":   {"informe":"NNN","fechas":"ayer","ruta":"crudo/stock_recogidas"},
  "stock_plancarga":   {"informe":"NNN","fechas":"ayer","ruta":"crudo/stock_plancarga"},
  "stock_retornos":    {"informe":"NNN","fechas":"ayer","ruta":"crudo/stock_retornos"},

  "rutas_jornadas":    {"informe":"NNN","fechas":"ayer","ruta":"crudo/rutas_jornadas"},
  "sat_averias":       {"informe":"NNN","fechas":"ayer","ruta":"crudo/sat_averias"},
  "sat_eventos":       {"informe":"NNN","fechas":"ayer","ruta":"crudo/sat_eventos"},
  "sat_visitas":       {"informe":"NNN","fechas":"ayer","ruta":"crudo/sat_visitas"},
  "sat_materiales":    {"informe":"NNN","fechas":"ayer","ruta":"crudo/sat_materiales"},

  "maestro_articulos": {"informe":"NNN","fechas":"ninguna","ruta":"maestros/articulos"},
  "maestro_maquinas":  {"informe":"NNN","fechas":"ninguna","ruta":"maestros/maquinas"},
  "maestro_pdvs":      {"informe":"NNN","fechas":"ninguna","ruta":"maestros/pdvs"},
  "maestro_canales":   {"informe":"NNN","fechas":"ninguna","ruta":"maestros/canales"},
  "maestro_carriles":  {"informe":"NNN","fechas":"ninguna","ruta":"maestros/carriles"},
  "maestro_recetas":   {"informe":"NNN","fechas":"ninguna","ruta":"maestros/recetas"},
  "maestro_rutas":     {"informe":"NNN","fechas":"ninguna","ruta":"maestros/rutas"},
  "maestro_rutas_pdvs":{"informe":"NNN","fechas":"ninguna","ruta":"maestros/rutas_pdvs"},
  "maestro_rutas_crit":{"informe":"NNN","fechas":"ninguna","ruta":"maestros/rutas_criterios"},
  "maestro_rutas_oper":{"informe":"NNN","fechas":"ninguna","ruta":"maestros/rutas_operarios"},
  "maestro_rutas_fondos":{"informe":"NNN","fechas":"ninguna","ruta":"maestros/rutas_fondos"},
  "maestro_almacenes": {"informe":"NNN","fechas":"ninguna","ruta":"maestros/almacenes"},
  "maestro_vehiculos": {"informe":"NNN","fechas":"ninguna","ruta":"maestros/vehiculos"},
  "maestro_empleados": {"informe":"NNN","fechas":"ninguna","ruta":"maestros/empleados"},
  "maestro_sat_catalogo":{"informe":"NNN","fechas":"ninguna","ruta":"maestros/sat_catalogo"},
  "maestro_inventarios":{"informe":"NNN","fechas":"mes_actual","ruta":"maestros/inventarios_alm"},
  "maestro_inventarios_prod":{"informe":"NNN","fechas":"mes_actual","ruta":"maestros/inventarios_prod"}
}
```

**Los maestros no hace falta bajarlos cada noche.** En la Lambda basta con añadir una condición:
si hoy es lunes, incluye también los de `fechas: ninguna`. Es una línea de código y divide por
siete el volumen semanal.

**Y `visita_devoluciones` va a otro prefijo a propósito**: lleva DNI y nombre de personas. Ese
prefijo debe tener su propia política de acceso y no lo lee la consola de cliente.

---

# Cómo se encadena todo

1. **Creas los informes** en VenCloud con estos SQL, uno por bloque, con el nombre de la
   convención. Al guardarlos, VenCloud les da un número.
2. **Me pasas los números** y los meto en el manifiesto.
3. **La Lambda** los llama cada noche, guarda el crudo en S3 particionado por fecha y deja un
   registro de la ejecución.
4. **Athena** ve esos ficheros como tablas SQL. Ahí se calculan los agregados.
5. **La cabina** lee los agregados ya calculados, no consulta Athena al abrirse.
6. **Las alarmas** salen de la misma capa: máquina muda, bolsa sin entregar, descuadre de
   contaje, avería fuera de plazo, stock bajo mínimo.

Antes de crear los treinta y tantos informes, **prueba con dos**: `EXT_VISITA_CABECERA` y
`EXT_VISITA_CONTAJES`. Si esos dos salen bien, los demás son del mismo molde y van seguidos.
