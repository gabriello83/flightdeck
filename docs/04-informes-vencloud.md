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

## Informe 7 — Total de cargas por punto de venta, artículo y periodo

**Parámetros**: `Desde` (0), `Hasta` (1), `Codigo_Centro` (2, numérico) y `Codigo_Cliente`
(3, numérico). Los dos últimos admiten **0 como comodín**: `((0 = {2}) or (clicen.numcentro = {2}))`.
Es el primer informe que permite pedir toda la cartera o acotar a un cliente o centro.

```sql
select cli.codigo codigocliente, cli.nombre nombrecliente,
       clicen.numcentro, clicen.denomina centro,
       m.codigo cod_maq, a.codigo cod_art, a.denomina articulo, rdo.cargas_totales
from (select pdvid, articuloid, sum(cantidad) cargas_totales
      from vending.partesvisita p
      left join vending.partesvisitareposiciones rep on p.id = rep.partevisitaid
      where rep.tipo = 'CM'
        and p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
      group by pdvid, articuloid) rdo
left join vending.pdvs pdv on pdv.id = rdo.pdvid
left join recursos.maquinas m on m.id = pdv.maquinaid
left join comercial.clientescentros clicen on clicen.id = pdv.clientecentroid
left join comercial.clientes cli on cli.id = clicen.clienteid
left join stocks.articulos a on a.id = rdo.articuloid
where pdv.estado = 1
  and ((0 = {2}) or (clicen.numcentro = {2}))
  and ((0 = {3}) or (cli.codigo = {3}))
order by m.codigo, cod_art
```

El comentario que arrastra el informe explica una limitación real: una máquina puede haber
estado en taller y cambiar de punto de venta dentro del periodo, así que lo correcto sería
agrupar por PDV. Se agrupa por PDV pero se pinta la máquina, el cliente y el centro
**actuales**. Para series largas hay que tenerlo en cuenta: la máquina que aparece puede no
ser la que estuvo allí todo el periodo.

**Salida**: 7.497 filas · 1.019 máquinas · 338 artículos · toda la cartera (Serunion, La
Paz, Institut Català de la Salut, RTVE, Alhambra, Airbus…). Suma 154.312 unidades.

### ¿Son cargas reales o vienen de coeficientes?

**Son reales, anotadas en el parte de visita.** Cuatro evidencias:

1. Cruzando con las ventas de los centros de Airbus, el ratio cargas/ventas va de 0,002 a
   0,82, con un coeficiente de variación de 1,05. Si salieran de aplicar un coeficiente
   sobre la venta, el ratio sería estable; no lo es ni de lejos.
2. Hay **3.801 combinaciones de máquina y artículo vendidas sin ninguna línea de carga** en
   el periodo. Un cálculo derivado de la venta no dejaría huecos.
3. Aparecen **medias unidades** (0,5, 1,5, 2,5): seis casos. Eso es alguien tecleando.
4. Se cargan cosas que **no se venden**: café a granel, preparado lácteo, azúcar, vasos y
   paletinas. Son ingredientes y consumibles, no artículos de venta, y solo pueden venir de
   una anotación física.

### Lo que este informe desbloquea

Es la vía para **valorar el consumo sin necesidad del escandallo del café**. El `cod_art`
de este informe cruza con el del informe 2 (precios de compra) en el **97% de los
artículos y el 100% de las unidades cargadas**, que es justo el cruce que no funcionaba
con el nombre del artículo.

Es decir: coste de mercancía cargada = cargas × precio de compra, por máquina y por
centro. Y los ingredientes del café entran solos, porque se cargan como artículo.

**Pero falta el factor de conversión.** Multiplicando tal cual sale un disparate:
6.150 paletinas × 15,90 € = 97.785 €, porque el precio es por caja de cien o de mil. En
cambio Coca Cola lata, 4.186 × 0,549 = 2.298 €, es correcto. Sin saber en qué unidad está
cada cosa, la valoración no se puede cerrar. Es el mismo problema del informe 2 y se
resuelve con el mismo campo: unidades por caja en el maestro de artículos.

---

## Informe 8 — Tareas técnicas por cliente y fecha

**Parámetros**: `Codigo Cliente` (0, numérico, 0 = todos), `Desde Fecha recepción` (1),
`Hasta Fecha recepción` (2) y `Num Centro` (3, numérico, 0 = todos).

Es el informe del que salió el fichero de averías que ya teníamos. Ahora, con el SQL a la
vista, se entienden cosas que antes había que adivinar. 24 columnas, de `sat.tareatecnica`
más los catálogos de operaciones, estados, máquinas, centros y direcciones.

### Lo que aclara el SQL

**`fecha_cierre` no es un campo, es un cálculo con tres salidas:**

1. El evento de cierre del log (`sat.tareatecnicaeventoslog`) cuando existe: trae hora real.
2. `t.fechafin` cuando la tarea está finalizada pero no hay ese evento: es una fecha sin
   hora, y por eso se pinta como **00:00**.
3. `01/01/1900 00:00` cuando la tarea **sigue abierta**.

Esto corrige la lectura inicial del análisis: las incidencias cerradas a las 00:00 no son
cierres administrativos por lotes, es que el cierre viene de un campo de fecha. El día es
bueno; solo falta la hora. Y las de 1900 no son cierres raros, son tareas abiertas.

**La columna `diferencia`** da el intervalo exacto entre recepción y cierre, o `0` si no
está cerrada. Ahorra calcularlo.

**Los códigos traducidos** que conviene guardar como catálogo propio:

- `origen`: 0 Email · 1 Teléfono · 2 WhatsApp · 3 Interna · 4 Portal B2B · 9 Autogenerada.
- `mod.clase` (tipo de máquina): 0 Bebidas Frías/Envasadas · 2 Bebidas Calientes/Preparadas ·
  3 Zumos · 4 Combi · 7 Epis · 8 Tabaco · 9 Snack/Multiproducto · 10 Fuente de Agua ·
  11 OCS/Café Cápsula-Grano · 99 Genérica · 100 Compactadoras · 101 Máquinas de cambio ·
  102 Partner · 200 Kiosko.
- `arearesponsable`: 0 SAT-Técnico · 1 Operaciones (Reponedor) · 2 Taller · 3 Call Center ·
  4 Comercial · 5 TI · 6 Instalaciones.

`mod.clase` es importante por sí solo: **es lo que separa las máquinas refrigeradas de las
de bebida caliente**, que era justo lo que hacía falta para que la alarma de temperatura
del informe 4 no dé falsos positivos.

### Salida analizada (25/09/2026, un día)

114 tareas de toda la cartera. Dos cosas a tener en cuenta:

- **34 de las 114 son del cliente `CLIENTE TEST`**: hay datos de prueba en producción. Hay
  que excluirlos en la ingesta o contaminan cualquier indicador.
- **59 de 114 tienen `origenllamada` vacío**: el `CASE` no cubre todos los valores de
  `t.origen` (faltan 5, 6, 7, 8). O se completa el mapeo o ese campo no sirve para segmentar.

Reparto del día: 62 de atención al cliente y 38 de averías técnicas; 83 las resuelve el
SAT, 20 operaciones y 11 el call center; 57 sobre máquinas de snack, 33 de bebida caliente
y 24 de bebida fría.

Trae además dos campos que no estaban en la exportación anterior y valen para el cuadro de
mando: `comentarios`, con las notas del técnico —"limpio tubo de residuos, máquina y mueble
porque está todo manchado"— y la dirección completa del centro con provincia y ciudad.

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

   Conviene añadirle `mod.clase` traducido, como hace el informe 8: es lo que separa las
   máquinas refrigeradas de las de bebida caliente. Y la capacidad, si existe en
   `recursos.maquinas` o `recursos.maquinasmodelos`.
5. **Planograma por máquina**: canal, artículo asignado y capacidad, que es lo que permite
   distinguir "no había demanda" de "estaba vacío".
