# Segunda tanda: relleno de campos y volcados con las columnas reales

Ya conocemos los nombres de columna, así que estas consultas son precisas. El orden importa:
**primero el relleno** (sirve para decidir qué se puede construir), luego los volcados.

---

## 1. Relleno de los campos críticos

Una fila por tabla con el porcentaje de registros que tienen cada campo. Es la consulta más
importante de la tanda: dice cuáles de los campos que encontramos en el modelo sostienen un
indicador y cuáles están vacíos.

### 1.1 Artículos

```sql
select
  count(*)                                                                    as articulos,
  count(*) filter (where obsoleto is not true)                                as activos,
  round(100.0*count(*) filter (where unidcaja is not null and unidcaja <> 0)/count(*),1)        as pct_unidcaja,
  round(100.0*count(*) filter (where numunidart is not null and numunidart <> 0)/count(*),1)    as pct_numunidart,
  round(100.0*count(*) filter (where unidpack is not null and unidpack <> 0)/count(*),1)        as pct_unidpack,
  round(100.0*count(*) filter (where preciocoste is not null and preciocoste <> 0)/count(*),1)  as pct_preciocoste,
  round(100.0*count(*) filter (where pmc is not null and pmc <> 0)/count(*),1)                  as pct_pmc,
  round(100.0*count(*) filter (where puc is not null and puc <> 0)/count(*),1)                  as pct_puc,
  round(100.0*count(*) filter (where precioventa is not null and precioventa <> 0)/count(*),1)  as pct_precioventa,
  round(100.0*count(*) filter (where coeficienteservicios is not null and coeficienteservicios <> 0)/count(*),1) as pct_coefservicios,
  round(100.0*count(*) filter (where caducidaddias is not null and caducidaddias <> 0)/count(*),1) as pct_caducidaddias,
  count(*) filter (where fresco is true)                                      as n_frescos,
  count(*) filter (where temperatura is true)                                 as n_con_temperatura,
  round(100.0*count(*) filter (where huecosimplecant is not null and huecosimplecant <> 0)/count(*),1) as pct_huecosimple,
  round(100.0*count(*) filter (where tipoiva is not null)/count(*),1)         as pct_tipoiva
from stocks.articulos;
```

### 1.2 Máquinas

```sql
select
  count(*)                                                                    as maquinas,
  count(*) filter (where estado = 1)                                          as operativas,
  count(*) filter (where cedida is true)                                      as cedidas,
  count(*) filter (where tipopropiedad = 1)                                   as de_proveedor,
  round(100.0*count(*) filter (where nserie is not null and nserie <> '')/count(*),1)               as pct_nserie,
  round(100.0*count(*) filter (where costecompra is not null and costecompra <> 0)/count(*),1)      as pct_costecompra,
  round(100.0*count(*) filter (where fechacompra > '1900-01-02')/count(*),1)                        as pct_fechacompra,
  round(100.0*count(*) filter (where cuotaamortizacion is not null and cuotaamortizacion <> 0)/count(*),1)  as pct_cuotaamort,
  round(100.0*count(*) filter (where mesesamortizacion is not null and mesesamortizacion <> 0)/count(*),1)  as pct_mesesamort,
  round(100.0*count(*) filter (where fechafinamortizacion > '1900-01-02')/count(*),1)               as pct_finamort,
  round(100.0*count(*) filter (where telemetriadispositivo is not null and telemetriadispositivo <> '')/count(*),1) as pct_dispositivo,
  count(*) filter (where auditgenalarmas is true)                             as con_alarmas_audit,
  round(100.0*count(*) filter (where fechaultcambioplanograma > '1900-01-02')/count(*),1)           as pct_ultcambioplano,
  round(100.0*count(*) filter (where consumomaximo is not null and consumomaximo <> 0)/count(*),1)  as pct_consumomaximo,
  round(100.0*count(*) filter (where fechafingarantia > '1900-01-02')/count(*),1)                   as pct_fingarantia
from recursos.maquinas;
```

### 1.3 Puntos de venta: el coste del servicio

Aquí está lo que decide si podemos calcular rentabilidad de verdad.

```sql
select
  count(*)                                                                    as pdvs,
  count(*) filter (where estado = 1)                                          as activos,
  round(100.0*count(*) filter (where costemediovisita is not null and costemediovisita <> 0)/count(*),1)   as pct_costemediovisita,
  round(100.0*count(*) filter (where costefijomensual is not null and costefijomensual <> 0)/count(*),1)   as pct_costefijomensual,
  round(100.0*count(*) filter (where impminrentabilidad is not null and impminrentabilidad <> 0)/count(*),1) as pct_impminrentab,
  round(100.0*count(*) filter (where impminrecaudacion is not null and impminrecaudacion <> 0)/count(*),1) as pct_impminrecaud,
  count(*) filter (where actalarmasrentrec is true)                           as con_alarmas_rentab,
  round(100.0*count(*) filter (where gpslatitud is not null and gpslatitud <> 0)/count(*),1)        as pct_gps,
  round(100.0*count(*) filter (where consumoobjetivo is not null and consumoobjetivo <> 0)/count(*),1) as pct_consumoobjetivo,
  count(*) filter (where vtaefectivo is true)                                 as admite_efectivo,
  count(*) filter (where vtatprivada is true)                                 as admite_t_privada,
  count(*) filter (where vtatcredito is true)                                 as admite_t_credito,
  count(*) filter (where vtapmovil is true)                                   as admite_movil,
  count(*) filter (where vtagratuita is true)                                 as admite_gratuita,
  count(*) filter (where sinrecaudacion is true)                              as sin_recaudacion,
  count(*) filter (where acuerdopartner is true)                              as con_partner,
  count(*) filter (where acuerdoalquiler is true)                             as con_alquiler,
  count(*) filter (where acuerdosubvencion is true)                           as con_subvencion
from vending.pdvs;
```

### 1.4 Canales de planograma

```sql
select
  count(*)                                                                    as canales,
  count(*) filter (where activo is true)                                      as activos,
  count(*) filter (where articuloid is not null)                              as con_articulo,
  round(100.0*count(*) filter (where capacmax is not null and capacmax <> 0)/count(*),1)          as pct_capacmax,
  round(100.0*count(*) filter (where stockrecom is not null and stockrecom <> 0)/count(*),1)      as pct_stockrecom,
  round(100.0*count(*) filter (where stockseguridad is not null and stockseguridad <> 0)/count(*),1) as pct_stockseguridad,
  round(100.0*count(*) filter (where cargaminima is not null and cargaminima <> 0)/count(*),1)    as pct_cargaminima,
  round(100.0*count(*) filter (where tipoespiral is not null)/count(*),1)                         as pct_tipoespiral,
  round(100.0*count(*) filter (where fila is not null and columna is not null)/count(*),1)        as pct_rejilla,
  round(100.0*count(*) filter (where precioef is not null and precioef <> 0)/count(*),1)          as pct_precioef
from recursos.maquinascanales;
```

### 1.5 Partes de visita: los campos calculados

```sql
select
  count(*)                                                                    as partes,
  round(100.0*count(*) filter (where cal_beneficio is not null and cal_beneficio <> 0)/count(*),1)              as pct_beneficio,
  round(100.0*count(*) filter (where cal_totimpvtas is not null and cal_totimpvtas <> 0)/count(*),1)            as pct_totimpvtas,
  round(100.0*count(*) filter (where cal_impvtasef is not null and cal_impvtasef <> 0)/count(*),1)              as pct_vtas_efectivo,
  round(100.0*count(*) filter (where cal_impvtastp is not null and cal_impvtastp <> 0)/count(*),1)              as pct_vtas_tprivada,
  round(100.0*count(*) filter (where cal_impvtastc is not null and cal_impvtastc <> 0)/count(*),1)              as pct_vtas_tcredito,
  round(100.0*count(*) filter (where cal_impcostecaducidad is not null and cal_impcostecaducidad <> 0)/count(*),1) as pct_coste_caducidad,
  round(100.0*count(*) filter (where cal_impcosterotura is not null and cal_impcosterotura <> 0)/count(*),1)    as pct_coste_rotura,
  count(*) filter (where cal_haydifprecios is true)                           as con_dif_precios,
  count(*) filter (where roboenmaquina is true)                               as con_robo,
  count(*) filter (where limpieza is true)                                    as con_limpieza,
  count(*) filter (where temperatura is true)                                 as con_temperatura,
  count(*) filter (where estadolec = 2 and lectura <> '')                     as con_audit
from vending.partesvisita
where fechaini >= '{0}' and fechaini <= '{1} 23:59:59';
```

---

## 2. Un día de ventas de telemetría, con todo

Empieza por **un solo día** para medir volumen antes de pedir meses.

```sql
select
  m.codigo                  as matricula,
  cen.numcentro             as num_centro,
  cen.denomina              as centro,
  del.nombre                as delegacion,
  ru.denomina               as ruta,
  t.fechaventa::text        as fecha_venta,
  t.hora                    as hora,
  t.diasemana               as dia_semana,
  a.codigo                  as cod_articulo,
  a.denomina                as articulo,
  t.seleccion               as seleccion,
  t.codcanal                as canal,
  t.precio                  as precio,
  t.coste                   as coste,
  (t.precio - coalesce(t.coste,0)) as margen,
  case t.lineaprecio when 1 then 'Tarjeta crédito' when 2 then 'Efectivo'
                     when 3 then 'Prepago' else t.lineaprecio::text end as medio_pago,
  t.tipoventaorigen         as tipo_origen,
  t.transactionid           as id_transaccion
from telemetry.telemetrysales t
left join recursos.maquinas m           on m.id   = t.maquinaid
left join vending.pdvs p                on p.id   = t.pdvid
left join comercial.clientescentros cen on cen.id = p.clientecentroid
left join comercial.clientes cli        on cli.id = cen.clienteid
left join general.delegaciones del      on del.id = p.delegacionid
left join vending.rutas ru              on ru.id  = t.rutaid
left join stocks.articulos a            on a.id   = t.articuloid
where t.fechaventa >= '{0}' and t.fechaventa <= '{1} 23:59:59'
  and ((0 = {2}) or (cli.codigo = {2}))
order by t.fechaventa;
```

Y el resumen del mismo día, para comparar el total contra lo que dice el informe 68:

```sql
select
  t.fechaventa::date        as fecha,
  count(*)                  as transacciones,
  count(distinct t.maquinaid) as maquinas,
  sum(t.precio)             as importe,
  sum(coalesce(t.coste,0))  as coste,
  round(100.0*count(*) filter (where t.coste is not null and t.coste <> 0)/count(*),1) as pct_con_coste,
  count(*) filter (where t.lineaprecio = 2) as n_efectivo,
  count(*) filter (where t.lineaprecio = 1) as n_tarjeta_credito,
  count(*) filter (where t.lineaprecio = 3) as n_prepago
from telemetry.telemetrysales t
where t.fechaventa >= '{0}' and t.fechaventa <= '{1} 23:59:59'
group by t.fechaventa::date
order by fecha;
```

---

## 3. Alarmas: lo que ya existe

```sql
-- 3.1 Criterios configurados de alarma por falta de ventas
select c.id, c.activa, c.latencia, c.modohoras,
       c.horadesde1, c.horahasta1, c.horadesde2, c.horahasta2,
       c.lunes, c.martes, c.miercoles, c.jueves, c.viernes, c.sabado, c.domingo, c.festivos,
       cen.numcentro, cen.denomina as centro, pdv.codigo as cod_pdv, m.codigo as matricula
from configuracion.criteriosalarmasnovtas c
left join comercial.clientescentros cen on cen.id = c.clientecentroid
left join vending.pdvs pdv on pdv.id = c.pdvid
left join recursos.maquinas m on m.id = pdv.maquinaid
order by c.activa desc, cen.denomina;

-- 3.2 Alarmas de máquina disparadas por la telemetría
select m.codigo as matricula, cen.denomina as centro, pdv.codigo as cod_pdv,
       al.firedon::text as disparada, al.code as codigo_alarma,
       al.eventdescription as descripcion, al.status as estado, al.telemetrysource as fuente
from telemetry.telemetryalarms al
left join recursos.maquinas m on m.id = al.maquinaid
left join vending.pdvs pdv on pdv.id = al.pdvid
left join comercial.clientescentros cen on cen.id = pdv.clientecentroid
where al.firedon >= '{0}' and al.firedon <= '{1} 23:59:59'
order by al.firedon desc;

-- 3.3 Alarmas detectadas en el audit de la visita
select m.codigo as matricula, a.codigoalarma, a.fechaalarma::text as fecha
from vending.partesvisitaauditalarmas a
left join recursos.maquinas m on m.id = a.maquinaid
where a.fechaalarma >= '{0}' and a.fechaalarma <= '{1} 23:59:59';

-- 3.4 Dispositivos de telemetría: cuáles tienen alarmas activadas
select d.devicecode, d.deviceprovider, d.serialnumber, d.simprovider, d.simnumber,
       d.phonenumber, d.auditsenable, d.alarmsenable, d.monitorize, d.isown, d.portsqty
from telemetry.telemetrydevices d
order by d.deviceprovider, d.devicecode;
```

---

## 4. A quién avisar

```sql
select e.codigo, e.nombre, e.cargo, del.nombre as delegacion,
       e.telefono, e.email, e.actmobile, e.coddispositivo,
       e.responsableven, e.incluirven, e.responsablesat, e.incluirsat,
       e.esoperaciones, e.escallcenter, e.esinstalaciones, e.taller, e.directivo
from recursos.empleados e
left join general.delegaciones del on del.id = e.delegacionid
where e.activo is true
order by del.nombre, e.nombre;
```

Y para ver si el canal de notificación móvil se está usando:

```sql
select tiponotificacion, count(*) as n,
       count(*) filter (where leida is true) as leidas,
       min(fecha)::text as desde, max(fecha)::text as hasta
from recursos.empleadosnotificacionesmobile
group by tiponotificacion order by n desc;
```

---

## 5. Volcados de maestro con las columnas que interesan

```sql
-- 5.1 Artículos
select a.codigo as cod_articulo, a.denomina as articulo, a.tipo, a.clase, a.obsoleto,
       a.unidcaja, a.numunidart, a.unidpack, a.unidmedida, a.pesounid, a.pesocaja,
       a.preciocoste, a.pmc, a.puc, a.pcr, a.precioventa, a.tipoiva,
       a.coeficienteservicios, a.caducidaddias, a.fresco, a.temperatura, a.clasalergeno,
       a.huecosimple, a.huecosimplecant, a.huecodoble, a.huecodoblecant,
       a.huecotriple, a.huecotriplecant, a.actvending, a.actocs, a.actmicromarket,
       f.nombre as fabricante
from stocks.articulos a
left join general.fabricantes f on f.id = a.fabricanteid
order by a.codigo;

-- 5.2 Máquinas (las matrículas), con todo lo de activo y telemetría
select m.codigo as matricula, m.nserie, m.estado, m.cedida, m.tipopropiedad, m.proveedorexterno,
       mo.modelo, mo.clase as clase_modelo, fab.nombre as fabricante,
       m.fechacompra::text, m.costecompra, m.cuotaamortizacion, m.mesesamortizacion,
       m.fechafinamortizacion::text, m.fechafingarantia::text,
       m.tipoconectividad, m.tipotelemetria, m.telemetriadispositivo, m.auditgenalarmas,
       m.sinplanograma, m.fechaultcambioplanograma::text, m.consumomaximo, m.tipoexplotacion,
       pdv.codigo as cod_pdv, pdv.ubicacion, cen.numcentro, cen.denomina as centro,
       cli.codigo as cod_cliente, cli.nombre as cliente, del.nombre as delegacion
from recursos.maquinas m
left join recursos.maquinasmodelos mo on mo.id = m.maquinamodeloid
left join general.fabricantes fab on fab.id = mo.fabricanteid
left join vending.pdvs pdv on pdv.id = m.pdvid
left join comercial.clientescentros cen on cen.id = pdv.clientecentroid
left join comercial.clientes cli on cli.id = cen.clienteid
left join general.delegaciones del on del.id = m.delegacionid
order by m.codigo;

-- 5.3 Puntos de venta con el coste del servicio y las coordenadas
select pdv.codigo as cod_pdv, m.codigo as matricula, pdv.ubicacion, pdv.clase, pdv.estado,
       cen.numcentro, cen.denomina as centro, cli.codigo as cod_cliente, cli.nombre as cliente,
       del.nombre as delegacion,
       pdv.costemediovisita, pdv.costefijomensual, pdv.impminrentabilidad, pdv.impminrecaudacion,
       pdv.actalarmasrentrec, pdv.consumoobjetivo, pdv.consumosabado, pdv.consumodomingo,
       pdv.vtaefectivo, pdv.vtatprivada, pdv.vtatcredito, pdv.vtapmovil, pdv.vtagratuita,
       pdv.sinrecaudacion, pdv.gpslatitud, pdv.gpslongitud,
       pdv.acuerdopartner, pdv.acuerdoalquiler, pdv.impalquiler, pdv.acuerdosubvencion,
       pdv.fechaalta::text, pdv.fechabaja::text
from vending.pdvs pdv
left join recursos.maquinas m on m.id = pdv.maquinaid
left join comercial.clientescentros cen on cen.id = pdv.clientecentroid
left join comercial.clientes cli on cli.id = cen.clienteid
left join general.delegaciones del on del.id = pdv.delegacionid
order by pdv.codigo;

-- 5.4 Planograma completo, con rejilla y stocks
select m.codigo as matricula, c.numero as canal, c.etiqueta, c.fila, c.columna,
       c.tipoespiral, c.activo, a.codigo as cod_articulo, a.denomina as articulo,
       c.precioef, c.preciotp, c.preciotc, c.capacmax, c.stockrecom, c.stockseguridad,
       c.cargaminima
from recursos.maquinascanales c
join recursos.maquinas m on m.id = c.maquinaid
left join stocks.articulos a on a.id = c.articuloid
where ((0 = {0}) or (m.delegacionid = {0}))
order by m.codigo, c.numero;
```

---

## Cómo leer los resultados

El objetivo de la tanda 1 es una tabla de decisión: **campo → porcentaje de relleno → qué
indicador sostiene**. Con eso se cierra la lista de lo que la cabina puede medir hoy y lo
que hay que rellenar antes.

Sospecho, por lo visto hasta ahora, que `costemediovisita` y `cal_beneficio` estarán poco
rellenos, y que `unidcaja` sí. Pero es una sospecha: el sentido de la consulta es
comprobarlo, no confirmarla.
