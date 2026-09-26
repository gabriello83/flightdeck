# Resultados del relleno: artículos y puntos de venta

Primeros dos bloques ejecutados en VenCloud. Son la respuesta a la pregunta que importaba:
qué indicadores puede sostener la cabina hoy, sin rellenar nada.

## 1. Artículos (27.179 registros)

| campo | relleno | qué significa |
|---|---|---|
| `unidcaja` | **100 %** | la conversión caja → unidad está siempre. Se puede convertir compra a unidad de venta |
| `puc` (último precio de compra) | **94 %** | **este es el coste utilizable** |
| `preciocoste` | 2,2 % | vacío |
| `pmc` (precio medio de compra) | 2,2 % | vacío |
| `numunidart` | 0,5 % | vacío |
| `coeficienteservicios` | 0,2 % | vacío — los coeficientes no están aquui |
| `caducidaddias` | 0,1 % | vacío |
| activos | 26.754 de 27.179 | sólo 425 marcados obsoletos: el maestro no se depura |
| frescos | 65 | |

**Consecuencias directas**

- El margen por artículo **sí se puede calcular**, pero con `puc`, no con `preciocoste`. Cualquier
  indicador de rentabilidad que use `preciocoste` saldría vacío en el 98 % de los casos.
- `caducidaddias` al 0,1 % cierra la puerta a una caducidad *prevista*. La caducidad sólo se
  conoce cuando el reponedor la marca con el terminal, así que el indicador que se puede construir
  sigue siendo de **disciplina de marcado**, no de producto caducado real.
- `coeficienteservicios` al 0,2 % confirma la sospecha sobre el informe 25: los coeficientes que
  usa el informe 66 **no salen de `stocks.articulos`**. Salen de `stocks.articulosdetalle`, que es
  la tabla de receta: por artículo, una fila por materia prima con `tipomateriaprima`,
  `tipounidad` y `cantunidad`. Hay que volcarla.
- 425 obsoletos sobre 27.179 significa que el catálogo activo está inflado. Al cruzar con lo que
  realmente se vende habrá que filtrar por uso, no por el flag.

## 2. Puntos de venta (5.203 registros, 3.200 activos)

| campo | relleno |
|---|---|
| `costemediovisita` | **0 %** |
| `costefijomensual` | **0 %** |
| `impminrentabilidad` | **0 %** |
| `impminrecaudacion` | **0 %** |
| `actalarmasrentrec` | **0 PDVs** |
| `gpslatitud` | **0 %** |
| `sinrecaudacion` | 201 PDVs |

Esto es más contundente de lo que esperaba: no es que esté poco relleno, es que **está vacío**.

**Consecuencias directas**

1. **La rentabilidad por máquina no se puede calcular desde el maestro de PDV.** Pero antes de
   darla por imposible hay que mirar dos tablas que sí existen y que el volcado de estructura ha
   destapado:
   - `configuracion.confrentabilidad` — los parámetros globales: `plazoamortizacion`,
     `costemediovisitatecnica`, `costeaveria`, `costemantenimiento`, `costevisitamodo`,
     `costeserviciotelemetria`, `costeserviciopagobancario`. Si esto está relleno, el coste no se
     lleva por PDV sino por configuración general, que es una forma perfectamente razonable de
     hacerlo.
   - `vending.pdvsrentabilidades` — rentabilidad **ya calculada por PDV, año y mes**, con
     comisiones, coste fijo, amortización de máquina y coste de servicios. Si esta tabla tiene
     filas, la cabina no tiene que calcular rentabilidad: tiene que leerla.
2. **Las alarmas de rentabilidad y recaudación de VenCloud están desactivadas en los 5.203 PDVs.**
   El motor existe, el campo existe, nadie lo ha encendido. Es la vía más corta para las alarmas
   que se piden: no hay que construir nada nuevo, hay que configurar `impminrecaudacion` y
   `actalarmasrentrec`. Encaja además con la regla operativa: recaudar como mínimo una vez al mes
   y más a menudo por encima de 100 € en bolsa.
3. **No hay GPS en el maestro de PDV, pero sí en otros tres sitios**, y son mejores:
   - `vending.partesvisita.maplatitud` / `maplongitud` y `posgpsfuerarango`: **dónde estuvo
     realmente el reponedor** al hacer la visita. Eso permite verificar la visita, no sólo
     planificarla.
   - `general.direcciones.maplatitud` vía `comercial.clientescentros.direccionid`: la coordenada
     del centro, suficiente para el mapa.
   - `utils.trackinggps`: el rastro del dispositivo.
4. 2.003 PDVs inactivos de 5.203 (38 %). Cualquier recuento que no filtre por `estado` exagera el
   parque a casi el doble.

## 3. Lo que hay que mirar ahora

```sql
-- 3.1 Parámetros globales de rentabilidad: ¿el coste está aquí en vez de en el PDV?
select plazoamortizacion, modocalculoamortizacion, costevisitamodo,
       costemediovisitatecnica, costeaveria, costesolicitudcom, costemantenimiento,
       costeserviciotelemetria, costeserviciopagobancario, costeservicioappmovil,
       modorentabilidad, origeningreso, tiporepartocomision
from configuracion.confrentabilidad;

-- 3.2 ¿Está ya calculada la rentabilidad mensual por PDV?
select anho, mes, count(*) as filas, count(distinct pdvid) as pdvs,
       sum(costetotalcomis)        as comisiones,
       sum(costefijopdv)           as coste_fijo,
       sum(costetotalamortizacion) as amortizacion,
       sum(costetotalservicios)    as servicios
from vending.pdvsrentabilidades
group by anho, mes
order by anho desc, mes desc;

-- 3.3 La receta: los coeficientes de materia prima que usa el informe 66
select a.codigo as cod_articulo, a.denomina as articulo, a.clase,
       d.orden, d.tipomateriaprima, d.tipounidad, d.cantunidad
from stocks.articulosdetalle d
join stocks.articulos a on a.id = d.articuloid
order by a.codigo, d.orden;

-- 3.4 Carriles de materia prima: el planograma de las máquinas calientes
select m.codigo as matricula, c.numero as carril, c.tipomateriaprima, c.formato,
       c.capacmax, c.stockrecom, c.cargaminima, c.virtual, c.extra,
       a.codigo as cod_articulo, a.denomina as articulo
from recursos.maquinascarriles c
join recursos.maquinas m on m.id = c.maquinaid
left join stocks.articulos a on a.id = c.articuloid
order by m.codigo, c.numero;

-- 3.5 El GPS que sí existe: dónde estuvo el reponedor  ({0} y {1} = fechas)
select count(*) as partes,
       round(100.0*count(*) filter (where maplatitud is not null and maplatitud <> 0)/count(*),1) as pct_gps_visita,
       count(*) filter (where posgpsfuerarango is true) as fuera_de_rango
from vending.partesvisita
where fechaini >= '{0}' and fechaini <= '{1} 23:59:59';

-- 3.6 Coordenadas del centro, ya que el PDV no las tiene
select count(*) as centros,
       round(100.0*count(*) filter (where d.maplatitud is not null and d.maplatitud <> 0)/count(*),1) as pct_con_coords
from comercial.clientescentros cen
left join general.direcciones d on d.id = cen.direccionid;
```

## 4. Corrección al modelo de datos

El planograma **no es una sola tabla**. `recursos.maquinascanales` son los canales de snack y
frío; `recursos.maquinascarriles` son los carriles de materia prima de las máquinas calientes,
con su propio `tipomateriaprima`, `capacmax`, `stockrecom` y `cargaminima`. El volcado de
planograma del bloque 5.4 de `08-sql-relleno.md` sólo cubre la mitad: hace falta también 3.4.
