# Catálogo de informes rápidos de VenCloud

Cada informe es una consulta SQL publicada con un número. Se piden con
`scripts/vencloud.py informe <n> [filtros...]`, y los parámetros van en el orden que
declara el informe (`Orden: 0`, `Orden: 1`…), sustituyendo a `{0}`, `{1}` en el SQL. Este
documento crece según se van conociendo.

Que el informe sea SQL plano tiene una consecuencia importante: **se pueden encargar
informes a medida**. Si falta un campo, no hay que rodearlo, se pide la consulta que lo
trae. Al final del documento están los que conviene encargar.

---

## De dónde sale cada cosa

Decisión del 25/09/2026: **la venta por producto probablemente venga de Nayax**, no de
VenCloud. Nayax es la pasarela de pago y telemetría de las máquinas, y registra la
transacción con su hora, su importe y su medio de pago.

| | Fuente |
|---|---|
| Venta por producto, hora y medio de pago | **Nayax** (pendiente de ver un informe) |
| Visitas, incidencias, preventivos, temperatura | VenCloud |
| Artículos, proveedores, precios de compra | VenCloud |
| Censo de máquinas, modelos, centros y clientes | VenCloud |

Esto tiene una consecuencia de diseño: el cuadro de mando cruza **dos sistemas**, y lo que
manda ya no es el nombre del artículo sino **las claves que unen ambos mundos**:

- **Máquina**: el identificador de dispositivo de Nayax contra el `cod_maq` de VenCloud.
  Sin esa correspondencia no se puede decir qué vendió la máquina que se visitó o se
  averió.
- **Producto**: el artículo de Nayax (que suele venir del planograma cargado en la
  máquina) contra el `cod_art` de VenCloud, que es el que lleva el precio de compra.

Hasta ver un informe de Nayax no se sabe cuál de las dos correspondencias existe ya y cuál
hay que construir. **Es lo primero que hay que resolver**, antes que cualquier pantalla:
si esas claves no casan, el cuadro de mando se queda en dos mitades incomunicadas.

Mientras tanto, las tablas de ventas que manejamos (las exportaciones de mayo a agosto) se
usan solo para dimensionar y prototipar, no como origen definitivo.

---

## Informe 2 — Artículos: proveedor y precio de compra

Sin parámetros.

```sql
select p.codigo cod_prov, p.razsocial proveedor, a.codigo cod_art, a.denomina articulo, precio
from compras.tarifascpa tc
left join compras.proveedores p on p.id = tc.proveedorid
left join stocks.articulos a on a.id = tc.articuloid
order by p.codigo, a.codigo
```

**Salida**: 1.628 filas · 93 proveedores · 1.570 artículos · columnas `cod_prov`,
`proveedor`, `cod_art`, `articulo`, `precio`.

Precio de compra: mediana 1,65 €, máximo 2.013,13 €, dos artículos a cero. Zambú Higiene
concentra 681 referencias; 44 artículos tienen tarifa de más de un proveedor.

### Qué aporta

Es el **coste de compra** que faltaba para calcular margen, y no solo facturación. Donde
casa, los márgenes salen coherentes: Ruffles jamón 73%, Doritos 68%, Agua Font Vella 1,5 L
62%, Coca Cola PET 39%, Monster 33%.

### Tres cosas que impiden usarlo tal cual

**1. No hay cómo cruzarlo con las ventas.** El informe trae `cod_art`, pero el export de
ventas solo trae el nombre del artículo. Cruzando por nombre normalizado casan **143 de
los 370** artículos vendidos: el **28,2%** de la facturación. Los que más venden no casan
(Café con Leche 94.756 €, Coca Cola Zero 55.428 €, Agua Font Vella 500 ml 31.130 €).

**2. El precio es por unidad de compra, no por unidad de venta.** De ahí salen márgenes
imposibles: CAÑA CREMA CACAO se vende a 0,93 € y figura a 10,84 € de compra —
evidentemente una caja. Sin el factor de conversión (unidades por caja) el margen de esos
artículos no se puede calcular. Afecta al menos a 17 de los 143 que casan.

**3. Las bebidas calientes no son artículos comprados, son recetas.** Son el **41,6% de la
facturación** (323.653 €) y su coste es un escandallo: café, leche en polvo, vaso,
paletina, azúcar. Sin esa composición, casi la mitad del negocio se queda sin margen.

---

## Informe 4 — Calidad: control de temperatura

**Parámetros**: `Desde Fecha` (orden 0) y `Hasta Fecha` (orden 1), ambos de tipo Fecha.
En el SQL entran como `fechaini >= '{0}'` y `fechaini < '{1} 23:59:59'`, así que van como
texto en formato de fecha de PostgreSQL: `2026-05-01`. Ejemplo de llamada:

```bash
python3 scripts/vencloud.py informe 4 2026-05-01 2026-08-31
```

```sql
select cli.codigo cod_cli, cli.nombre cliente, cn.numcentro, cn.denomina centro,
       pdv.codigo cod_pdv, pdv.ubicacion, m.codigo cod_maq, mod.modelo modelo,
       p.fechaini::text fecha_visita, tempvalor valortemperatura
from vending.partesvisita p
left join vending.pdvs pdv on pdv.id = p.pdvid
left join recursos.maquinas m on m.id = pdv.maquinaid
left join recursos.maquinasmodelos mod on mod.id = m.maquinamodeloid
left join comercial.clientescentros cn on cn.id = pdv.clientecentroid
left join comercial.clientes cli on cli.id = cn.clienteid
where temperatura and fechaini >= '{0}' and fechaini < '{1} 23:59:59'
order by cli.codigo, cn.numcentro, pdv.codigo, p.fechaini
```

La temperatura la anota el reponedor en el terminal durante la visita. Las máquinas con
producto fresco (sándwiches, platos de quinta gama) deben estar **entre 0 y 4 °C**.

### Salida analizada (25/09/2026, un solo día)

119 lecturas · 106 máquinas · **toda la cartera de la empresa**, no solo Airbus: Alhambra,
Hospital Clínico, Europastry, Kellogg, Airbus San Pablo Sur…

**Hay dos poblaciones mezcladas en la misma columna.** Nueve lecturas están entre 90 y
96 °C: son máquinas de bebida caliente (OPERA, ZENSIA, KIKKO, WINNING) y esa es la
temperatura de caldera, no un fallo. El umbral 0–4 °C **solo aplica a las refrigeradas**,
así que cualquier alarma tiene que clasificar antes la máquina o se llena de falsos
positivos.

Sobre las 110 lecturas refrigeradas:

| | |
|---|---:|
| Mediana | 4,2 °C |
| Por encima de 4 °C | 66 (60,0%) |
| Por encima de 5 °C | 32 (29,1%) |
| Por encima de 6 °C | 27 (24,5%) |
| Por encima de 8 °C | 3 (2,7%) |
| Máximo | 9,0 °C |

Las peores son tres G-DRINK DC6 de la Alhambra, entre 8,4 y 9,0 °C. En Airbus hay 29
lecturas refrigeradas y 14 por encima de 4 °C, pero ninguna pasa de 4,9 °C: incumplimiento
formal, no riesgo sanitario.

### Advertencias sobre el dato

- **La lectura es manual**, la teclea el reponedor. En el Hospital Clínico todas las
  lecturas del día son exactamente `8.0`, y hay muchos `3.0` redondos repetidos. Antes de
  montar una alarma sobre esto hay que saber si el terminal propone un valor por defecto,
  porque un valor tecleado en bloque no mide nada.
- **No se sabe la cobertura**: 119 lecturas en un día, pero no cuántas máquinas con
  producto fresco deberían haberse controlado. Sin el censo, el indicador que de verdad
  importa —qué máquinas con fresco se han quedado **sin** control— no se puede calcular.

### Para qué sirve en el cuadro de mando interno

Es un panel de calidad y APPCC con valor propio: porcentaje de lecturas en rango por
cliente y centro, máquinas reincidentes fuera de rango, y cobertura del control. Es además
el tipo de indicador que respalda a la empresa ante una inspección o una reclamación.

---

## Informe 6 — Recaudación HUCA por mes

**Parámetros**: `FECHAINICIO` (orden 0) y `FECHAFIN` (orden 1), tipo Fecha. El primero se
usa además para sacar el año y el mes que necesita el cálculo del IVA.

```sql
select tmp.fechaini as fecha, pdvs.codigo, pdvs.ubicacion, tmp.imprecauda as total,
       (select public.calcula_iva_medio(date_part('year', timestamp '{0}')::int,
                                        date_part('month', timestamp '{0}')::int,
                                        tmp.pdvid, tmp.prefacrecaudaresumenid)) as iva_medio
from (SELECT fechaini::date, p.pdvid, p.id, imprecauda, p.recprosegurid,
             p.recprosegurdetalleid, rp.prefacrecaudaresumenid
      FROM vending.partesvisita as p
      left join utils.recprosegur as rp on rp.id = recprosegurid
      left join utils.recprosegurdetalle as rpd on rpd.id = p.recprosegurdetalleid
      where p.delegacionid = 2 and recaudacion = 1
        and fechaini >= '{0}'
        and fechaini < ('{1}' || ' 23:59:59')::timestamp without time zone
      order by p.pdvid asc, fechaini asc) as tmp
left join vending.pdvs on pdvs.id = tmp.pdvid
```

**Salida**: columnas `fecha`, `codigo`, `ubicacion`, `total`, `iva_medio`. La primera
ejecución de prueba (25/09/2026 a 25/09/2026) devolvió cero registros.

Agosto de 2026 completo, delegación 2 (HUCA):

| | |
|---|---:|
| Recaudaciones | 21 |
| Puntos de venta | 14 |
| Total recaudado | 3.273,32 € |
| Por recaudación | mediana 145 €, de 92 € a 303 € |
| Días con recaudación | 6 (entre el 5 y el 24 de agosto) |

Ni ceros ni negativos. La frecuencia es baja —1,5 recaudaciones por punto en todo el mes—
y se concentra en seis días: la ruta de recaudación pasa cada dos o tres semanas.

El `iva_medio` sale distinto en cada punto de venta (de 10 a 14,09) porque es el IVA medio
ponderado según el surtido de esa máquina, mezcla de tipos. Es el que permite pasar de
recaudación bruta a base imponible sin inventar un tipo único.

Un detalle del export, no del informe: las fechas llegan al Excel como número de serie
(46239 = 05/08/2026). Por la API, `fechaini::date` viene ya como fecha.

### Qué aporta

Es el **dinero efectivamente recaudado** de cada máquina, que no es lo mismo que lo
vendido. La recaudación se marca en el parte de visita (`recaudacion = 1`, importe en
`imprecauda`) y se concilia con Prosegur a través de `utils.recprosegur` y su detalle.

Cruzado con la venta —que vendrá de Nayax— permite el indicador que ningún panel de
cliente va a tener: **descuadre entre lo vendido en efectivo y lo recaudado**, máquina a
máquina. Ahí se ven atascos de monedero, recuentos mal hechos y mermas.

### Cómo generalizarlo

El informe está atado a una delegación (`p.delegacionid = 2`, HUCA). Para el cuadro de
mando interno hace falta la versión sin ese filtro, o con la delegación como tercer
parámetro, y añadiendo cliente y centro al resultado —igual que hace el informe 4— para
poder agrupar por cartera. Conviene incluir también `delegacionid` como columna.

---

## Informes que conviene encargar

Aprovechando que son consultas SQL a medida:

1. **Ventas con código de artículo, hora y medio de pago.** El campo que desbloquea todo
   lo demás: sin `cod_art` no hay margen, sin hora no hay análisis por franja, sin medio
   de pago no se cuadran las 276 devoluciones. Filtros por rango de fechas y centro.
2. **Maestro de artículos completo**: `cod_art`, denominación, familia, formato, unidades
   por caja o factor de conversión, PVP de tarifa, IVA.
3. **Escandallo de las selecciones de bebida caliente**: qué ingredientes y qué cantidad
   consume cada selección.
4. **Censo de máquinas**. Con las tablas que ya conocemos por el informe 4 se puede
   escribir entero, solo hay que publicarlo. Resuelve la cobertura del control de
   temperatura y la ubicación de las 549 máquinas, de las que hoy solo tenemos 125:

   ```sql
   select cli.codigo cod_cli, cli.nombre cliente, cn.numcentro, cn.denomina centro,
          pdv.codigo cod_pdv, pdv.ubicacion, m.codigo cod_maq, mod.modelo modelo
   from vending.pdvs pdv
   left join recursos.maquinas m on m.id = pdv.maquinaid
   left join recursos.maquinasmodelos mod on mod.id = m.maquinamodeloid
   left join comercial.clientescentros cn on cn.id = pdv.clientecentroid
   left join comercial.clientes cli on cli.id = cn.clienteid
   order by cli.codigo, cn.numcentro, pdv.codigo
   ```

   Si la máquina tiene marca de refrigerada, tipo o capacidad en `recursos.maquinas` o en
   `recursos.maquinasmodelos`, conviene añadir esas columnas: son las que permiten separar
   las máquinas de fresco de las de bebida caliente.
5. **Planograma por máquina**: canal, artículo asignado y capacidad, que es lo que permite
   distinguir "no había demanda" de "estaba vacío".
