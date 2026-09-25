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

## Informe 9 — Telemetría: cuadre de ventas con tarjeta por delegación

**Parámetros**: `DESDE` (0) y `HASTA` (1), tipo Fecha.

```sql
select case when delegacionid is null then 'Sin configurar'
            else (select nombre from general.delegaciones as d where delegacionid = d.id) end as delegacion,
       ventas_tc
from (SELECT delegacionid, sum(precio) as ventas_tc
      FROM telemetry.telemetrysales as t
      left join vending.pdvs as p on pdvid = p.id
      where fechaventa >= '{0}'
        and fechaventa <= ('20240229 23:59:59')::timestamp without time zone
        and tipotelemetria = 40 and lineaprecio = 1
      group by delegacionid) as tmp;
```

### La salida viene vacía porque el informe tiene un error

La fecha de fin está **escrita a fuego**: `fechaventa <= ('20240229 23:59:59')`. El
parámetro `{1}` no se usa en ninguna parte. Cualquier consulta posterior al 29 de febrero
de 2024 devuelve cero filas, se pida el rango que se pida. Se arregla sustituyendo esa
constante:

```sql
        and fechaventa <= ('{1} 23:59:59')::timestamp without time zone
```

Mientras no se corrija, el informe solo sirve para fechas anteriores a marzo de 2024.

### Lo importante no es el informe, es la tabla que revela

`telemetry.telemetrysales` es una tabla de **ventas de telemetría dentro de VenCloud**, con
`fechaventa`, `precio`, `pdvid`, `tipotelemetria` y `lineaprecio`. Por el informe 37 sabemos
que `lineaprecio` distingue el medio de pago: **2 efectivo, 1 tarjeta de crédito, 3
prepago**. O sea que este informe, al filtrar `lineaprecio = 1`, suma solo la venta con
tarjeta de crédito, no toda la venta. Es decir: puede que la
venta que dábamos por perdida —la que íbamos a buscar en Nayax— ya esté aquí, con su fecha
y hora, y ya enlazada al punto de venta de VenCloud, que es la unión que nos faltaba entre
los dos mundos.

Vale la pena comprobar qué contiene esa tabla antes de montar nada contra Nayax. Si trae
artículo, resuelve de golpe el problema de las claves.

Además, este informe es la otra mitad del informe 6: **recaudación (efectivo) + ventas con
tarjeta (telemetría) = venta total**, y la diferencia contra lo vendido es el descuadre que
interesa vigilar máquina a máquina.

---

## Informe 10 — PDVs y máquinas con tarifa vending o tarifa de productos

**Parámetro**: `Delegacion` (0, numérico, 0 = todas).

Sale de `recursos.maquinas` cruzando punto de venta, centro, cliente y delegación, y añade
tres banderas de configuración de tarifa. **Es el censo de máquinas que faltaba.**

**Salida**: 4.498 máquinas · 3.203 puntos de venta · 212 clientes · 12 delegaciones.

### El censo, por fin completo

| | |
|---|---:|
| Máquinas en total | 4.498 |
| Instaladas en un punto de venta | 3.203 (71%) |
| **Sin punto de venta** (taller o almacén) | **1.295 (29%)** |
| Con número de serie | 4.404 (98%) |
| En centros de Airbus | 563, en 9 centros |

Casi un tercio del parque está parado. Eso es un indicador de activos por derecho propio:
cuántas máquinas hay inmovilizadas, dónde y desde cuándo.

Los centros de Airbus son **nueve**, no siete: aparecen AIRBUS ITC (10 máquinas) y AIRBUS
ALBACETE (PARQUE CI) (2), que no tenían ventas en las exportaciones.

Contrastado con las ventas de mayo a agosto: de las 563 máquinas de Airbus, **546 venden,
17 no vendieron nada** en cuatro meses. Esas 17 son la primera lista a revisar, y enlazan
con las máquinas mudas del análisis.

### Configuración de tarifas

Las tarifas se pueden colgar del cliente, del centro o de un PDV suelto. La forma correcta,
según el equipo, es a nivel de cliente y de centro.

| | SI | NO |
|---|---:|---:|
| Tarifa vending asignada | 921 | 3.577 |
| Tarifa de productos en el cliente | 1.274 | 3.224 |
| Tarifa de productos en el centro | 1.230 | 3.268 |

**402 máquinas instaladas (12,6%) no tienen ninguna de las tres.** Se concentran en Madrid
- Leganés (163), Cataluña - Cornellà (63) y Levante - Murcia (41), y afectan a 35 clientes.
Una máquina vendiendo sin tarifa configurada es dinero mal facturado o directamente
perdido, así que esto es un panel de configuración pendiente, no una curiosidad. En los
centros de Airbus no hay ninguna: ahí la configuración está bien.

### `refexterna`: posible puente con la telemetría

`pdv.refexterna` coincide con el código de PDV en el 47% de los casos, pero en el **53%
restante es otra cosa**: referencias numéricas de seis dígitos como `010502`, `010507`,
`010671`. Eso tiene pinta de identificador de un sistema externo, y es el primer candidato
serio a ser la clave que enlaza con la telemetría o con Nayax. Conviene comprobarlo antes
de construir ninguna tabla de equivalencias a mano.

### Lo que le falta a este informe

Solo dos columnas para ser el censo definitivo: **`mod.clase` traducido** (el tipo de
máquina, que separa refrigeradas de bebida caliente) y la **capacidad**. El informe 8 ya
demuestra que `clase` está disponible en `recursos.maquinasmodelos`.

---

## Informe 11 — PDVs y máquinas con canales de planograma

**Parámetro**: `Delegación` (0, numérico, 0 = todas).

Mismo censo que el informe 10, con una bandera distinta: si la máquina tiene canales con
artículo asignado (`recursos.maquinascanales` con `articuloid` no nulo y la máquina no
marcada como `sinplanograma`). Sirve para localizar las máquinas sin planograma.

**Salida**: 4.498 máquinas. De las 3.203 instaladas, **2.889 tienen planograma y 314 no
(9,8%)**.

### Dónde están los huecos

| Delegación | Sin planograma | De |
|---|---:|---:|
| Serunion Vending - CENTRAL | 39 | 42 (**93%**) |
| Levante - Valencia | 62 | 199 (31%) |
| Levante - Murcia | 56 | 408 (14%) |
| Cataluña - Cornellà | 81 | 633 (13%) |
| Andalucía - Sevilla | 41 | 370 (11%) |
| Madrid - Leganés | 20 | 855 (2%) |

Airbus está bien: 8 de 563 máquinas sin planograma, un 1%, repartidas entre San Pablo Sur
(4), Tablada, ITC, Albacete e Illescas.

### Cruzado con las tarifas del informe 10

Sobre las 3.203 máquinas instaladas:

| | |
|---|---:|
| Bien configuradas (tarifa y planograma) | 2.579 (80,5%) |
| Con tarifa pero sin planograma | 222 |
| Con planograma pero sin tarifa | 310 |
| **Sin tarifa ni planograma** | **92** |

Esas 92 son máquinas instaladas, en un punto de venta, sin tarifa y sin planograma:
venden a ciegas y sin precio configurado. Es la lista más corta y más accionable que ha
salido hasta ahora, y encaja en el cuadro de mando interno como panel de calidad de
configuración, junto con las 402 sin tarifa del informe 10.

### Por qué importa para el análisis

Sin planograma no se puede saber qué debería haber en cada canal, así que no se puede
distinguir **"no había demanda" de "estaba vacío"**. Las máquinas sin planograma quedan
fuera de cualquier cálculo de rotura de stock y de venta perdida, y hay que decirlo en el
panel en vez de dar un dato incompleto como si fuera completo.

---

## Informe 12 — Total de retiradas por caducidad, por PDV, artículo y periodo

**Parámetros**: `Desde` (0), `Hasta` (1) y `NumCentro` (2, numérico).

Mismo motor que el informe 7, cambiando el tipo de línea de reposición: `rep.tipo = 'RC'`
(retirada por caducidad) en vez de `'CM'` (carga).

```sql
where rep.tipo = 'RC' and p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
  and p.clientecentroid = (select id from comercial.clientescentros where numcentro = {2})
```

**Salida**: la ejecución de prueba devolvió **cero registros**.

### Dos limitaciones de este informe

**El centro es obligatorio.** A diferencia del informe 7, aquí no hay comodín: el filtro es
una igualdad directa contra `numcentro`, así que no se puede pedir toda la cartera de una
vez. Para un cuadro de mando de empresa habría que llamarlo centro a centro, cientos de
veces. Se arregla con el mismo patrón que ya usa el 7:

```sql
  and ((0 = {2}) or (cn.numcentro = {2}))
```

**Y no hace falta que sea un informe aparte.** El 7 y el 12 son la misma consulta con
distinto `tipo`. Lo razonable es un solo informe de reposiciones con `rep.tipo` como
columna, y **ya existe: es el informe 66**, que además baja al detalle por parte de visita.

### Por qué el caducado importa, y por qué el cero engaña

El caducado es merma directa: producto comprado, cargado y tirado. Valorarlo es inmediato,
porque el `cod_art` cruza con los precios de compra del informe 2 igual que las cargas.

Pero el indicador hay que leerlo al revés de lo que parece. Según el equipo, **una ruta sin
caducado no es una ruta perfecta: es un reponedor que no está marcando el producto
caducado en el terminal**. Así que el primer indicador no es cuánto se retira, sino
**cuántas rutas y máquinas no registran ninguna retirada**, que es una alerta de disciplina
de proceso.

Cruzado con el informe 7 sale la merma real: retiradas / cargas por artículo y por máquina.

---

## Informe 14 — Albaranes de entrada: temperatura

**Parámetros**: `Id Delegacion` (0, numérico), `Codigo Proveedor` (1, numérico),
`Desde Fecha` (2) y `Hasta Fecha` (3).

```sql
from compras.albaranescpa alcpa
inner join compras.proveedores prove on alcpa.proveedorid = prove.id
inner join general.delegaciones del on alcpa.delegacionid = del.id
where prove.codigo = {1} and del.id = {0}
  and (alcpa.fecha >= '{2}' and alcpa.fecha <= '{3} 23:59:59')
  and estado = 2
```

Devuelve, por albarán: número, fecha, proveedor, número de artículos distintos, unidades
totales y `transtemperatura`, la **temperatura del transporte** anotada en la recepción.

**Salida**: la ejecución de prueba devolvió **cero registros**.

### Por qué sale vacío tan fácilmente

Este informe tiene cuatro filtros obligatorios y **ninguno admite comodín**: delegación y
proveedor son igualdades exactas, y además exige `estado = 2`. Basta fallar en uno de los
tres para no ver nada. Para el cuadro de mando hace falta la versión con comodines:

```sql
where ((0 = {0}) or (del.id = {0}))
  and ((0 = {1}) or (prove.codigo = {1}))
```

Conviene además **descomentar `alcpa.total`**, que está en el SQL anulado: da el importe
del albarán y con él el volumen de compra por proveedor, sin pedir otro informe.

### Lo que aporta

Cierra la **cadena de frío de punta a punta**. Hasta ahora teníamos la temperatura en la
máquina (informe 4); esto da la temperatura en la recepción de mercancía. Juntos cubren
proveedor → almacén → máquina, que es lo que pide una auditoría de seguridad alimentaria.

Como indicador de proveedor, lo primero no es la temperatura media sino **cuántos albaranes
llegan sin temperatura anotada**: igual que con el caducado, la ausencia de dato es el
primer hallazgo, no la buena noticia.

---

## Informe 20 — Resumen de inventario valorado por máquina

Sin parámetros. Recorre los puntos de venta activos (`pdv.estado = 1`) y, para cada uno,
busca su **último** informe de inventario de máquina (`tipoalm = 'M'`, `maquinaverif`) y
trae su `valortotal`.

**Salida**: 3.200 máquinas · **306.203,51 €** de valor total declarado.

Aporta además dos columnas que llevábamos tiempo necesitando: la **ruta** asignada al punto
de venta y la **clase de máquina** ya traducida.

### Pero ese número no es el stock de hoy

| | |
|---|---:|
| Máquinas **nunca inventariadas** | 954 (29,8%) |
| Antigüedad mediana del último inventario | **485 días** |
| Inventariadas en los últimos 30 días | 18 (0,6%) |
| Inventariadas en el último año | 828 (25,9%) |

El inventario más antiguo es de agosto de 2023. Así que "inventario valorado" es, en
realidad, la suma de fotos viejas: tres de cada cuatro máquinas llevan más de un año sin
contar. Para el cuadro de mando esto no invalida el dato, pero obliga a enseñarlo **siempre
junto a la antigüedad**, y probablemente el indicador principal no sea el valor sino
**cuántas máquinas llevan sin inventariar más de X meses**.

### Y hay valores imposibles

| Valor | Máquina | Centro | Último inventario |
|---:|---|---|---|
| 78.761,19 € | 20SE1717 (Snack) | TVE | 18/09/2024 |
| 19.275,48 € | 17FP1498 (Bebida Fría) | Centro de Estudios Jurídicos | 14/03/2024 |
| 2.142,99 € | 19SE1652 (Snack) | Fundación Teatro Real | 20/03/2025 |

El percentil 99 del parque son 336 €. Una máquina con 78.761 € dentro no existe: **una sola
máquina es el 26% del total declarado**. O son inventarios de almacén imputados a un punto
de venta, o son errores de captura. Sin las dos primeras, el total baja a unos 208.000 €,
que ya es una cifra creíble.

Cualquier indicador de valor de stock tiene que llevar control de atípicos, o un error de
tecleo mueve el panel entero.

### Reparto

- **Por clase**: Bebida Caliente 1.276, Snack 1.069, Bebida Fría 766, Fuente de Agua 47,
  Genérica 29, OCS 8, Zumos 1. Y **4 máquinas con "Valor no esperado"**: hay códigos de
  clase que el `CASE` no contempla.
- **Por delegación**: Madrid-Leganés concentra 151.006 € en 853 máquinas, la mitad del
  total.
- **Rutas**: 65 distintas, y **154 puntos de venta sin ruta asignada**.
- **Airbus**: 563 máquinas, 24.954,79 €, y **276 nunca inventariadas** (el 49%).

---

## Informe 22 — Recursos: máquinas sin reposición desde una fecha dada

**Parámetro**: `Desde fecha`, y aquí hay un detalle que importa para la API: su **orden es
1, no 0**, y el SQL lo usa como `{1}`. Es el primer informe donde la numeración no empieza
en cero, así que al construir la llamada no se puede dar por hecho que el primer filtro sea
`{0}`. Hay que probarlo.

```sql
where m.id not in (select pv.maquinaid
                   from vending.partesvisitareposiciones as pvr
                   left join vending.partesvisita as pv on pvr.partevisitaid = pv.id
                   where pvr.fecha >= '{1}')
```

**Salida** (desde el 01/09/2026): **1.664 máquinas**.

### Tres cuartas partes del resultado son ruido

De esas 1.664, **1.286 no tienen punto de venta**: son las máquinas de taller y almacén que
ya conocíamos por el informe 10. Lógicamente no se reponen, y aparecen aquí cada vez.

**Las que importan son 378**: máquinas instaladas, en un punto de venta, que llevan 24 días
sin una sola línea de reposición. Se concentran en Murcia (79), Leganés (75), Cornellà (70)
y Valencia (45). En Airbus son **30**, repartidas entre Getafe (7), CBC (6), San Pablo Norte
(6), Tablada (4), Illescas (3), San Pablo Sur (2) y Albacete (2).

Para el cuadro de mando basta añadir `and p.id is not null`, o separar ambas listas: una de
máquinas desatendidas y otra de parque inmovilizado, que son dos problemas distintos.

### El informe hermano que falta: sin recaudación

Este informe es de **reposición**. El comentario que arrastra el SQL menciona la
recaudación, pero el código mira `partesvisitareposiciones`; conviene corregir el
comentario para que no despiste.

Falta el equivalente para la otra regla de negocio: **toda máquina hay que recaudarla al
menos una vez al mes, y más a menudo si acumula más de 100 € en la bolsa**. Eso pide un
informe hermano que mire `partesvisita` con `recaudacion = 1`, como hace el informe 6. Y con la venta en efectivo de la telemetría se puede ir más lejos: estimar
**cuánto dinero hay ahora mismo en cada máquina** desde la última recaudación, y avisar al
pasar de 100 € sin esperar al mes. Ese sí es un instrumento de cabina.

---

## Informe 23 — Recursos: máquinas sin recaudación desde una fecha dada

**Parámetro**: `Fecha desde`, otra vez con **orden 1**, usado como `{1}`.

Es el informe hermano del 22, y está mejor construido:

```sql
where p.clase not in (10,11,100,101,102,200) and
      m.id not in (select maquinaid from vending.partesvisita
                   where fechacrea >= '{1}' and recaudacion = 1)
```

Excluye las clases que no manejan dinero —fuentes de agua, OCS, compactadoras, máquinas de
cambio, partner y quioscos— y, de paso, **deja fuera las máquinas sin punto de venta**,
porque `p.clase` es nulo para ellas y `NULL not in (...)` no se cumple. El informe 22
debería hacer lo mismo.

**Salida** (desde el 01/09/2026, 24 días): **1.093 máquinas**, ninguna sin PDV.

### El dato importa, y bastante

El parque que maneja efectivo son 3.145 máquinas (informe 20, descontando las clases sin
dinero). Así que **el 34,8% lleva 24 días sin recaudar**, con la regla de negocio en una vez
al mes. No es un incumplimiento todavía, pero a esa fecha un tercio de la flota está al
borde.

| Delegación | Sin recaudar |
|---|---:|
| Madrid - Leganés | 423 |
| Levante - Murcia | 221 |
| Cataluña - Cornellà | 87 |
| Levante - Valencia | 70 |
| Andalucía - Sevilla | 62 |

En Airbus son 177, y **Getafe solo aporta 93** de sus 231 máquinas: el 40% del centro.

Con el único dato de recaudación real que tenemos —mediana de 145 € por recaudación en la
delegación 2 durante agosto— el orden de magnitud sería de unos **150.000 € parados en las
bolsas**. Es una estimación gruesa, de una sola delegación y un solo mes, y no se puede dar
por buena para toda la cartera; pero sirve para dimensionar por qué esto merece un
instrumento propio en la cabina.

### Cruzado con el informe 22

| | |
|---|---:|
| Sin reposición **ni** recaudación | **295** |
| Solo sin recaudar | 798 |
| Solo sin reponer | 83 |

Las 295 que no reciben ninguna de las dos atenciones son la lista corta: máquinas
instaladas a las que hace 24 días que no va nadie.

---

## Informe 24 — Artículos que no están en máquinas

Sin parámetros.

```sql
SELECT a.codigo, a.denomina as nombre
FROM stocks.articulos as a
left join recursos.maquinascanales as mc on mc.articuloid = a.id
left join recursos.maquinascarriles as mr on mr.articuloid = a.id
where a.obsoleto = false and mc.id is null and mr.id is null and a.tipo <> 'R'
```

### Qué hace

Es **higiene de catálogo**. Lista los artículos que siguen dados de alta y activos
(`obsoleto = false`) pero que **no están asignados a ningún hueco de ninguna máquina**: ni
a un canal (`maquinascanales`, las espirales y selecciones) ni a un carril
(`maquinascarriles`). Los dos `left join` con `is null` son la forma de decir "no aparece
en ninguna de las dos tablas". Excluye además los de tipo `R`, que por los ejemplos parecen
recetas o preparados de café, aunque el significado exacto de ese tipo habría que
confirmarlo.

Dicho de otro modo: **la parte del catálogo que no está en ningún planograma**.

### Salida: 362 artículos, y el informe es coherente

Contrastado con el resto de informes:

- **329 de los 362 tienen tarifa de compra** mantenida (informe 2). Son artículos que se
  pueden comprar pero no están colocados en ninguna máquina.
- **Ninguno tiene cargas registradas** (informe 7): cero unidades de 154.312. Es la
  comprobación de que el informe dice la verdad.
- Solo **4 aparecen en las ventas de mayo a agosto**, por 592 € en total (LM Clásico Atún,
  LM Wrap York, LM Clásico Mixto y una barrita). Son productos que se vendieron y después
  salieron de los planogramas.

### Para qué sirve en el cuadro de mando

Catálogo muerto que sigue vivo: cada uno de esos 362 artículos aparece en los desplegables,
en el mantenimiento de tarifas y en los pedidos, y ensucia el trabajo de todo el mundo. La
lista se parte en dos:

- Los que **llevan tiempo sin usarse**: candidatos a marcar como obsoletos.
- Los **recién creados**: artículos nuevos pendientes de asignar a un planograma, que es
  justo lo contrario, trabajo a medio hacer.

Para separarlos hace falta la fecha de alta del artículo, que este informe no trae. Con ella
el indicador sería directo: artículos activos sin planograma y sin movimiento en X meses.

---

## Informe 25 — PDVs: cargas por punto de venta y clase de artículo

**Parámetros**: `Desde Fecha` (0) y `Hasta Fecha` (1).

Tres columnas de cantidad por punto de venta —`frias`, `snack` y `café`— construidas con
tres subconsultas sobre las líneas de carga (`tipo = 'CM'`), cada una filtrando una clase
de artículo distinta.

**Salida** (agosto de 2026): 2.371 puntos de venta.

| Columna | Unidades |
|---|---:|
| frías | 616.207 |
| snack | 319.634 |
| café | 430.600 |

### Aquí sí hay coeficientes

Es la diferencia clave con el informe 7. Las columnas de frías y snack suman unidades tal
cual, pero la de café multiplica por un coeficiente:

```sql
res.cantidad * replace(coe.coeficiente,',','.')::numeric as cant_total
...
inner join importacion.art_bc_coeficiente coe on coe.articuloid = res.artid
```

O sea: el café no se carga en servicios, se carga en kilos de café, de leche en polvo y de
chocolate, y `importacion.art_bc_coeficiente` convierte cada artículo a **servicios
equivalentes**. Por eso la mediana de la columna café (360) es el doble que la de las otras.

Esto completa la respuesta sobre si las cargas son reales: **el informe 7 da la carga
física, el 25 da la carga convertida a servicios para el café**. Son compatibles, no
contradictorios.

Tres avisos sobre ese cálculo:

- **La tabla de coeficientes no es la buena.** `importacion.art_bc_coeficiente` es una
  tabla de importación; el coeficiente vigente es el campo `coeficienteservicios` de
  `stocks.articulos`, que es el que usa el informe 66. La columna de café de este informe
  hay que darla por sospechosa.
- Es un `inner join`, así que **un artículo de café sin coeficiente desaparece sin dejar
  rastro**. Un punto de venta puede aparecer con la columna vacía simplemente porque falta
  el coeficiente, no porque no se haya cargado. El informe 66 corrige esto también.
- La subconsulta del café corta en `'{1} 23:59'` en vez de `'{1} 23:59:59'`: pierde el
  último minuto del día. Es menor, pero hace que la columna de café no cubra exactamente el
  mismo periodo que las otras dos.

### El hallazgo de fondo: hay dos tablas de clases distintas

Cruzando la clase del punto de venta con la columna que trae dato, el mapeo queda claro:

| Clase de PDV | Columna con dato | Filtro del SQL |
|---|---|---|
| BEBIDA CALIENTE (746 PDVs) | solo `café` | `a.clase = 0` |
| BEBIDA FRÍA (664) | solo `frias` | `a.clase = 2` |
| SNK/MULTIPRODUCTO (957) | `frias` y `snack` | `a.clase = 2` y `a.clase = 3` |

Es decir, **`stocks.articulos.clase` usa una codificación distinta de `pdv.clase` y
`mod.clase`**: en artículos, 0 es café, 2 es bebida fría y 3 es snack; en máquinas, 0 es
bebida fría y 2 bebida caliente. A primera vista el SQL parece tener las etiquetas
cambiadas, y no es así. Es una trampa fácil de pisar al escribir la ingesta, y por eso
queda anotada aquí.

### Nota

El `where` final exige que al menos una de las tres columnas tenga dato, así que **los
puntos de venta visitados sin ninguna carga no aparecen**. Para medir visitas sin carga hay
que ir al informe 22.

---

## Informe 66 — Detalle de reposición con carga teórica de caliente

**Parámetros**: `{0}` y `{1}`, fechas.

Es la versión buena del informe 25, y de hecho es el informe de reposiciones que hacía
falta: baja al **detalle por parte de visita**, con fecha, cliente, punto de venta,
**tipo de movimiento**, código de artículo, descripción y cantidad. Al traer `pr.tipo` como
columna sirve a la vez para cargas (`CM`), retiradas por caducidad (`RC`) y cualquier otro
tipo que exista, en lugar de necesitar un informe por tipo como el 7 y el 12.

### El coeficiente correcto

```sql
case
    when coe.coeficienteservicios is null then res.cantidad
    else res.cantidad * coe.coeficienteservicios::numeric
end as cant_total
...
left join stocks.articulos coe on coe.id = res.artid
```

Dos mejoras sobre el informe 25: el coeficiente sale de **`stocks.articulos.coeficienteservicios`**,
que es el campo vigente, y no de la tabla de importación; y el join es `left` con
respaldo, así que **un artículo sin coeficiente conserva su cantidad** en vez de
desaparecer.

### Un problema serio en la construcción

Las dos ramas —artículos de clase distinta de 0, y artículos de café— se unen con **dos
`left join` independientes sobre `pdv.id`**, y luego se elige columna con un `case`. Dos
joins sobre la misma clave producen producto cartesiano: si un punto de venta tiene N
líneas de no-café y M de café, salen **N × M filas**.

Y como el `case` es `when res_bf_sn.tipo is null then res_bc... else res_bf_sn...`, en
todas esas filas `res_bf_sn.tipo` viene informado, así que:

- cada línea de no-café aparece **repetida M veces**, y
- **las líneas de café no aparecen nunca**.

El café solo se ve en los puntos de venta que no tienen ninguna línea de otra clase. Como
las máquinas de bebida caliente suelen llevar solo artículos de clase 0, el informe parece
correcto al mirarlo; **donde falla es en las máquinas combi o en los PDV con varias
máquinas**, que es justo donde interesa.

La construcción correcta no es un join, es un `UNION ALL` de las dos ramas: cada una ya
devuelve las mismas columnas (pdv, fecha, tipo, artículo, cantidad) y no hay nada que
cruzar.

Conviene comprobarlo con una salida real de un punto de venta combi antes de dar por bueno
cualquier número de este informe.

### Otros dos detalles

- Los tres cortes de fecha usan `'{1} 23:59'` en vez de `23:59:59`: se pierde el último
  minuto del día.
- La rama de no-café filtra `a.clase != 0`, que en PostgreSQL **también excluye los
  artículos con clase nula**. Si hay artículos sin clase asignada, no salen por ninguna de
  las dos ramas.

---

## Informe 26 — Total de ventas por PDV, artículo y periodo

**Parámetros**: `Desde` (0), `Hasta` (1) y `NumCentro` (2, numérico y **obligatorio**, sin
comodín, igual que el informe 12).

```sql
select pdvid, articuloid, sum(totnumvtas) ventas_totales, sum(totimpvtas) importe_total_ventas
from vending.partesvisita p
left join vending.partesvisitaventas v on p.id = v.partevisitaid
where p.fechaini >= '{0}' and p.fechaini <= '{1} 23:59:59'
  and p.clientecentroid = (select id from comercial.clientescentros where numcentro = {2})
group by pdvid, articuloid
```

**Salida**: la ejecución de prueba devolvió **cero registros**.

### Esto es la venta por artículo dentro de VenCloud

Y es importante: trae **`cod_art`**, la clave que cruza con los precios de compra del
informe 2 y con las cargas del 7 y el 66. Con este informe el margen por artículo y por
máquina deja de depender de Nayax.

Hay ahora **dos fuentes de venta distintas** dentro de VenCloud, y conviene no mezclarlas:

| | `vending.partesvisitaventas` (informe 26) | `telemetry.telemetrysales` (informe 9) |
|---|---|---|
| Origen | contadores de la máquina leídos en cada visita | transacción de telemetría |
| Detalle | total por artículo entre visitas | venta individual con fecha y hora |
| Trae artículo | sí, `cod_art` | por confirmar |
| Sirve para | margen, consumo, cuadre | series diarias, franjas horarias, medio de pago |

### La trampa del periodo

El filtro es sobre `p.fechaini`, **la fecha de la visita**, no la de la venta. Las ventas
que se imputan a un periodo son las **leídas en las visitas de ese periodo**, y esas ventas
se produjeron entre la visita anterior y esta.

Con rutas que pasan cada dos o tres semanas —como se ve en la recaudación del informe 6—
el desfase puede ser de semanas. Para un total mensual da igual, se compensa; para
comparar un mes contra otro, o para cualquier serie corta, **no vale**: mueve la venta al
día en que pasó el reponedor. Las series diarias tienen que salir de la telemetría.

### Lo que le falta

Lo mismo que al 12: el centro es obligatorio y no admite comodín, así que para una visión
de empresa habría que llamarlo centro a centro. Se arregla con el patrón del informe 7:
`((0 = {2}) or (cn.numcentro = {2}))`.

---

## Informe 28 — Comprobación de IVAs en la recaudación

Sin parámetros, y con el periodo **escrito a fuego**: `where anho = 2024 and mes in (1..7)`.
Como el informe 9, hay que parametrizarlo para que sirva de algo en el día a día.

### Qué hace

Una recaudación es un montón de monedas que mezcla productos al 10% y al 21%. Para
facturarla hay que repartir la base por tipo de IVA, y VenCloud lo hace con un criterio.
Este informe saca ese reparto línea a línea, desde `facturacion.prefacrecaudadetalle`, y
lo pone al lado de dos cosas con las que contrastarlo:

- **`IVA_MAQUINA`**: el tipo configurado en la ficha de la máquina (`clasefacvtaid`:
  1 → 21%, 2 → 10%, 3 → 4%, 4 → 0%).
- **`critcalculo`**: cómo se ha repartido — `1 AUDIT` (datos de auditoría de la máquina),
  `2 CARGAS`, `3 CANALES` (planograma) o `4 MAQUINA` (el tipo único de la ficha).

O sea: es un informe de **control fiscal**, para comprobar que el IVA repercutido en cada
recaudación se ha calculado con un criterio razonable y cuadra.

### La salida (enero a julio de 2024)

149.985 líneas · base **3.527.265,75 €** · cuota **451.646,46 €**.

| Criterio | Líneas |
|---|---:|
| 1 AUDIT | 115.138 (76,8%) |
| 3 CANALES | 22.830 (15,2%) |
| 4 MAQUINA | 11.532 (7,7%) |
| 2 CARGAS | 485 (0,3%) |

Tipos aplicados: 10% en 110.798 líneas, 21% en 34.250 y 0% en 4.937 (28.954,86 € de base).

**La aritmética es impecable**: en las 149.985 líneas, la cuota es exactamente la base por
el tipo. Ahí no hay nada que rascar.

### Dos cosas que sí merecen una mirada

**1. Líneas con criterio MAQUINA cuyo tipo no coincide con el de la máquina: 5.026,
375.070,77 € de base.** Que el tipo aplicado difiera del de la ficha es normal cuando el
reparto es por AUDIT o por CANALES —una misma máquina vende al 10% y al 21%—, y por eso el
15,5% de discrepancia global no dice nada. Pero cuando el criterio es *la máquina*, el tipo
debería ser *el de la máquina*. Casi todas son 21% aplicado sobre máquinas hoy configuradas
al 10%. La explicación más probable es que la ficha haya cambiado después de facturar, o que
se cambiara la máquina de ese punto de venta: el informe lee la configuración **actual**
contra una factura **histórica**. Conviene confirmarlo antes de darlo por error.

**2. 66.347 líneas (44%) no tienen máquina asociada**, con 1.142.767,81 € de base. Son
puntos de venta cuyo `maquinaid` no resuelve hoy. En esas líneas la columna de contraste
viene vacía, así que **casi la mitad del importe no se puede comprobar** con este informe.
Para que sirva de verdad habría que guardar el tipo de IVA vigente en el momento de
facturar, no ir a buscarlo a la ficha.

---

## Informe 29 — Rutas y PDVs: lista

Sin parámetros. Filtra `r.tipo = 0`, o sea un tipo concreto de ruta; hay otros, porque el
informe 20 llegaba a contar 65 rutas distintas y aquí salen 60.

**Salida**: 3.021 filas · **60 rutas** · 3.007 puntos de venta · 185 clientes · 412 centros
· 17 delegaciones.

### Aviso de modelado: el código de ruta no es único

`cod_ruta` se repite entre delegaciones —hay 32 códigos distintos para 60 rutas—, así que
la clave de una ruta es **la delegación más el código**, o su `refexterna`, que sí sale
única (60 valores). Agrupar solo por `cod_ruta` mezcla rutas de provincias distintas; es un
error fácil de cometer y da resultados absurdos.

### Tamaño de las rutas

| | |
|---|---:|
| Mediana | 52 puntos de venta |
| Media | 50 |
| Mayor | 123 (La Paz 01 - Café) |
| Menor | 2 (Ruta 12 - Luis Chávez, Madrid 22 - EDP) |

La mayoría de rutas llevan el nombre del reponedor, lo que permite atribuir trabajo a
personas sin cruzar con nada más.

### Lo que sale al cruzarlo con el censo

- **196 puntos de venta instalados no están en ninguna ruta de tipo 0**, 22 de ellos en
  centros de Airbus. O los cubre otro tipo de ruta, o son máquinas que nadie tiene
  asignadas: hay que mirarlo.
- **14 puntos de venta están en dos rutas a la vez** (por ejemplo C00663, en "Ruta 01
  Fernando Duran Roca" y en "Ruta La Línea 1"). Duplicidad de asignación.
- Hay una **RUTA TEST** con 3 puntos de venta, los tres instalados. Igual que el
  `CLIENTE TEST` del informe 8, hay que excluirla de cualquier indicador.

### Por qué es la base del análisis de rutas

Hasta ahora la ruta solo aparecía como texto en las visitas. Esto da la **asignación
oficial**: qué PDV pertenece a qué ruta. Con ella se puede medir lo que de verdad importa
de una ruta —cobertura, carga de trabajo por reponedor, visitas realizadas frente a puntos
asignados, rentabilidad por ruta— y contrastar la asignación teórica con las visitas reales
del informe de visitas.

---

## Informe 30 — PDVs: historial de instalaciones

Sin parámetros; **conviene añadirle rango de fechas**, porque hoy devuelve el histórico
entero y va a crecer sin parar.

Sale de `vending.pdvshisinstalaciones` y da el **ciclo de vida de cada máquina en cada
punto de venta**: instalación, retirada, y los dos lados de una sustitución. Trae además
fabricante y modelo, número de serie, quién lo ejecutó y notas libres.

Códigos de `tipo`: 0 instalación · 1 retirada · 2 sustitución-instalación · 3
sustitución-retirada.

**Salida**: 4.119 movimientos · 3.219 puntos de venta · 2.505 máquinas · 257 clientes.

| Movimiento | Nº |
|---|---:|
| Retirada de máquina | 2.094 |
| Instalación de máquina | 1.429 |
| Sustitución - instalación | 298 |
| Sustitución - retirada | 298 |

El histórico arranca en julio de 2023 (103 movimientos), y desde ahí: 1.598 en 2024, 1.399
en 2025 y 1.012 en lo que va de 2026. Hay además **4 registros con fecha 01/01/1900** y tres
sueltos de 2017, 2019 y 2022 que habrá que descartar.

### El parque está encogiendo

| Año | Instalaciones | Retiradas | Neto |
|---|---:|---:|---:|
| 2023 (desde julio) | 58 | 27 | **+31** |
| 2024 | 615 | 739 | **−124** |
| 2025 | 465 | 742 | **−277** |
| 2026 (hasta septiembre) | 287 | 583 | **−296** |

Tres años seguidos en negativo y acelerando: unas 700 máquinas netas menos desde 2024. Y
encaja con lo que ya sabíamos por el censo: **1.295 máquinas sin punto de venta**, paradas
en taller o almacén. No son dos hallazgos, son el mismo visto por dos sitios.

La única reserva: si alguna retirada corresponde a una máquina instalada antes de que
existiera el histórico, no tiene instalación que la compense. Eso afectaría sobre todo a
2023 y 2024; en 2025 y 2026 la tendencia debería ser limpia.

### Una cuarta parte de las instalaciones dura menos de un mes

Emparejando instalación y retirada del mismo par máquina-punto de venta salen 463 ciclos
completos:

| | |
|---|---:|
| Mediana de permanencia | 196 días |
| Retiradas antes de 30 días | **114 (24,6%)** |
| Antes de 90 días | 166 (35,9%) |
| Antes de un año | 315 (68,0%) |

Que una de cada cuatro instalaciones se deshaga en menos de un mes es llamativo. Puede ser
material de prueba, instalaciones temporales para eventos, o instalaciones que salen mal —
el dato por sí solo no lo distingue, y las notas libres (1.682 movimientos las tienen)
seguramente lo expliquen.

### Lo que aporta al cuadro de mando

- **Antigüedad de cada máquina en su emplazamiento**, que hasta ahora no teníamos y es la
  variable que falta para leer bien las averías: no es lo mismo una avería en una máquina
  recién instalada que en una que lleva tres años.
- **Fabricante**, por primera vez: NECTA 1.678 movimientos, FAS 706, Sandenvendo 613,
  Azkoyen 475, Bianchi 230, Rhea 90, Dixie Narco 79, Jofemar 72. Cruzado con el informe 8
  permite pasar de "averías por modelo" a "averías por marca y por antigüedad".
- **Rotación del parque** por cliente y por centro: altas, bajas y sustituciones.

Un apunte sobre el dato: **`realizado_por` es casi siempre la misma persona** —Noelia
Moreno Martín firma 3.693 de los 4.119 movimientos, el 90%—, así que ese campo dice quién
lo teclea en VenCloud, no quién fue a la instalación. Para medir trabajo de campo no sirve.

---

## Informe 31 — Recaudaciones por cliente y centro en periodo de visita

**Parámetros**: `Codigo Cliente` (0, numérico, **0 = todos**), `Desde Fecha Visita` (1) y
`Hasta Fecha Visita` (2).

Es la versión útil del informe 6: sin delegación cableada, con comodín de cliente y
agrupando por cliente y centro.

```sql
where pvis.recaudacion = 1
  and pvis.estadocontaje = 1
  and (pvis.fechaejec >= '{1}' and pvis.fechaejec <= '{2} 23:59:59')
  and ((0 = {0}) or (cli.codigo = {0}))
```

**Salida** (septiembre de 2026): **286.344,78 €** en 246 centros de 133 clientes.

| | |
|---|---:|
| Mediana por centro | 245,05 € |
| Máximo | 21.663,89 € (Alhambra) |
| Centros a cero | 11 |

Los grandes son hospitales: Hermanos Trias 18.308 €, Virgen Macarena 15.982 €, Hospital
Clínico 15.727 €, La Paz 14.989 €. **Airbus suma 22.642,96 €** repartidos en solo 6 de sus
9 centros: Getafe 8.184 €, San Pablo Sur 5.756 €, Illescas 3.778 €, Tablada 3.025 €,
CBC 1.459 € y San Pablo Norte 438 €. Albacete e ITC no aparecen.

### Dos cosas que hay que saber antes de usar la cifra

**Es dinero contado, no dinero recogido.** El filtro `estadocontaje = 1` deja fuera las
recaudaciones que todavía no se han contado. Lo que este informe da es la caja ya
verificada; el efectivo recogido y pendiente de contar no aparece por ningún lado. Para el
cuadro de mando interno eso es en sí un indicador: **cuánto hay recaudado sin contar, y
desde cuándo**.

**Hay un `left join` que sobra** (comprobado con el informe 33: no infla, pero tampoco
aporta, así que lo suyo es quitarlo). La consulta se une a
`vending.partesvisitacontajes` pero no usa ninguna columna suya: ni en el `select`, ni en
el `where` —`estadocontaje` sale de `partesvisita`—, ni en el `group by`. Si un parte de
visita tiene varias líneas de contaje (por ejemplo una por denominación de moneda), el join
**multiplica las filas y `sum(pvis.imprecauda)` cuenta ese importe tantas veces como
líneas**.

En los números de septiembre no se ve nada raro —los 8.184 € de Getafe encajan con una
venta mensual del orden de 88.000 € pagada mayormente con tarjeta de empleado—, así que o
la tabla tiene una línea por parte, o el efecto es pequeño. Pero conviene comprobarlo con
un centro concreto, porque el join **no aporta nada**: quitarlo es seguro y elimina el
riesgo.

---

## Informe 33 — Rutas: plan de visitas, visitas, recaudaciones y audits

**Parámetros**: `Desde Fecha` (0) y `Hasta Fecha` (1).

Pone una al lado de otra, por ruta, cuatro cosas: las visitas **planificadas**
(`vending.planvisitas`), las **realizadas** (partes de visita), las que llevaron
**recaudación** con su importe, y las que capturaron **audit** (`estadolec = 2` y `lectura`
no vacía, la lectura de contadores de la máquina).

Es, de largo, el informe más útil que ha aparecido para el cuadro de mando interno: mide
ejecución contra plan, que es lo que no se podía medir con nada de lo anterior.

**Salida** (septiembre de 2026, 73 rutas):

| | | |
|---|---:|---|
| Visitas planificadas | 24.966 | |
| Partes de visita | 20.816 | **83% del plan** |
| Con recaudación | 7.095 | 34% de las visitas |
| Importe recaudado | 286.344,78 € | 40,36 € por visita recaudada |
| **Con audit** | **2.396** | **12% de las visitas** |

### El 12% de audit es el hallazgo

El audit es la lectura de los contadores de la máquina, y es de donde sale la venta por
artículo del informe 26 y el criterio con el que se reparte el IVA en el informe 28. Que
solo se capture en **una de cada ocho visitas** explica de golpe por qué tantos informes de
venta salen vacíos o cojos.

Y hay **7 rutas con visitas y ni un solo audit**, entre ellas una de Airbus:

| Ruta | Visitas sin audit |
|---|---:|
| Madrid 08 Princesa | 536 |
| **Sevilla 6 Airbus S.Pablo Parte H1** | **492** |
| Madrid RTVE Prado | 289 |
| Ruta La Línea 1 | 91 |

### Cumplimiento del plan

Mediana del 88%, pero con mucha dispersión: p10 en 27% y p90 en 132%.

**Cinco rutas planificadas sin una sola visita**: Teruel 4 (152 planificadas), Sevilla Fin
de Semana (92), Princesa Fin de Semana (80), RUTA TEST (57) y Refuerzo José Manuel (30).

**Nueve rutas por debajo del 50%**, y las dos peores son de volumen grande: Ruta 13 Can
Ruti, 317 visitas de 1.197 planificadas (26%), y Ruta 14 Yordy, 385 de 1.406 (27%). Con
planes de más de mil visitas mensuales incumplidos en tres cuartas partes, o el plan está
mal dimensionado o la ruta no se está haciendo; en ambos casos es una pregunta que el panel
debe poner encima de la mesa.

**Cuatro rutas por encima del 150%**, encabezadas por Alhambra Tarde con 323 visitas sobre
76 planificadas (425%). Ahí el plan no describe la realidad.

Y **11 rutas con visitas pero sin ninguna recaudación**, la mayor Figueres 1 con 447
visitas.

### De paso, resuelve la duda del informe 31

Este informe suma **286.344,78 €**, exactamente el mismo importe que el 31, y lo calcula
**sin el `left join` a `partesvisitacontajes`** que allí quedaba pendiente de comprobar. Que
coincidan al céntimo indica que ese join no está inflando nada. Y como el 31 filtra además
`estadocontaje = 1` y da lo mismo, en septiembre prácticamente toda la recaudación estaba
ya contada.

### Nota

El `where` exige `rut.refexterna != ''`, así que las rutas sin referencia externa no
aparecen. Aquí salen 73 rutas, más que las 60 del informe 29, porque este no filtra por
tipo: incluye también las rutas técnicas.

---

## Informe 34 — Máquina: precio medio de venta por periodo

**Parámetros**: `Desde Fecha` (0) y `Hasta Fecha` (1).

### Este informe está roto, y es el peor de los casos

Los parámetros **solo se usan para elegir qué máquinas salen**:

```sql
where maq.id in (select distinct(pvis.maquinaid) from vending.partesvisita pvis
                 where (pvis.fechaejec >= '{0}' and pvis.fechaejec <= '{1} 23:59:59'))
```

Pero la subconsulta que calcula las ventas tiene el periodo **escrito a fuego**:

```sql
where (pvis.fechaejec >= '2024-07-01' and pvis.fechaejec <= '2024-07-31 23:59:59')
```

Es decir: se pide septiembre de 2026 y se obtiene **la lista de máquinas visitadas en
septiembre de 2026 con sus ventas de julio de 2024**. El informe 9 tenía el mismo vicio,
pero allí al menos devolvía vacío y saltaba a la vista. Aquí devuelve cifras con toda la
pinta de ser correctas.

La prueba está en la propia salida: **229 máquinas**, cuando en septiembre hubo 20.816
visitas sobre más de 3.000 puntos de venta. Esas 229 son la intersección de dos periodos
sin relación: máquinas visitadas en septiembre de 2026 **que además** vendieron algo en
julio de 2024. Y los 207.504,14 € y 239.868 unidades que muestra son de julio de 2024.

Se arregla sustituyendo las dos constantes por `'{0}'` y `'{1} 23:59:59'`.

### Lo que mide, cuando funcione

Precio medio por venta de cada máquina, a partir de `cal_totnumvtas` y `cal_totimpvtas`,
que son los totales calculados del parte de visita. Con las cifras de julio de 2024, las
medianas por clase salen coherentes: bebida caliente 0,649 €, bebida fría 0,867 €, snack
0,924 €.

Dicho esto, **es un indicador derivado, no un informe**: teniendo ventas por máquina, el
precio medio se calcula en el cuadro de mando sin pedir nada a VenCloud. Lo que sí vale la
pena conservar de aquí es la idea: el precio medio por máquina y por clase es un buen
detector de tarifa mal configurada o de surtido cambiado sin querer.

---

## Informe 35 — Clientes: precio medio de ventas por periodo y clase de máquina

**Parámetros**: `Desde Fecha` (0) y `Hasta Fecha` (1), y **aquí sí se usan en los dos
sitios**: tanto en la subconsulta que calcula las ventas como en el filtro de clientes. Es
el mismo informe que el 34 pero bien hecho; sirve de plantilla para arreglar aquel.

**Salida** (septiembre de 2026): 133 filas · **65 clientes** · 851.404 unidades ·
**721.484,70 €** · precio medio global **0,8474 €**.

| Clase de máquina | Unidades | Importe | Precio medio |
|---|---:|---:|---:|
| Snack / multiproducto | 313.617 | 352.429,68 € | 1,1238 € |
| Bebidas calientes | 384.087 | 203.982,07 € | 0,5311 € |
| Bebidas frías | 153.700 | 165.072,95 € | 1,0740 € |

El café vende **más unidades que nada** (384.087, el 45%) pero a la mitad de precio, así
que en facturación queda por detrás del snack. Es la tensión clásica del vending: el café
llena la ruta de trabajo y el snack paga las facturas.

Por cliente, **Serunion concentra 324.805,48 €**, el 45% del total; le siguen el Institut
Català de la Salut (71.684 €), Value Retail Las Rozas (65.919 €) y la Alhambra (56.926 €).
Airbus no aparece como cliente porque sus centros cuelgan de Serunion, que es el cliente
10002.

### Cuidado con leer esto como "la venta del mes"

Son las ventas **registradas en los partes de visita** (`cal_totnumvtas` y
`cal_totimpvtas`), no la venta real del periodo. Dos razones para no confundirlas:

1. Solo aparecen **65 clientes**, cuando el informe 31 contabiliza recaudación en 133. La
   mitad de la cartera no tiene ventas registradas en septiembre.
2. Arrastra el mismo desfase que el informe 26: la venta se imputa al parte de visita, o
   sea al día en que pasó el reponedor, no al día en que se vendió.

Como referencia de precio medio y de mix por clase es excelente. Como cifra de negocio del
mes, no.

### Detalle de modelado

Este informe clasifica por **`maqmod.clase`** (la clase del modelo de máquina) mientras que
el 34 usa **`pdv.clase`** (la del punto de venta). Son dos campos distintos que casi siempre
coinciden pero no tienen por qué: un punto de venta puede tener una máquina de otra clase.
Al montar la ingesta hay que elegir uno y ser consistente.

---

## Informe 36 — Seguimiento operativo por ruta, cliente y máquina

**Parámetros**: `Desde Fecha` (0) y `Hasta Fecha` (1), usados correctamente en todas las
subconsultas.

**Es la tabla que el cuadro de mando necesita**: una fila por punto de venta visitado, con
delegación, cliente, centro, dirección completa, máquina, ubicación, ruta y cinco medidas
del periodo —producto cargado, producto retirado, número de ventas, importe de ventas y
recaudación—. Todo lo que hasta ahora estaba repartido en ocho informes, junto y por PDV.

**Salida** (1 al 26 de septiembre de 2026): **2.956 puntos de venta** · 177 clientes · 399
centros · 2.921 máquinas.

| Medida | PDVs con dato | Total |
|---|---:|---:|
| Producto cargado | 2.828 (95,7%) | 2.470.043 unidades |
| Producto retirado | **417 (14,1%)** | 8.743 unidades |
| Número de ventas | 2.956 | 852.339 |
| Importe de ventas | 2.956 | 722.158,92 € |
| Recaudación | 2.956 | 286.344,78 € |

### Cuatro cosas que salen de aquí y de ningún otro sitio

**1. El 86% de los puntos de venta no registra ni una retirada.** Solo 417 de 2.956 anotan
producto retirado. Aplicando el criterio del equipo —una ruta sin caducado es un reponedor
que no lo está marcando— esto deja de ser una métrica de merma y pasa a ser una métrica de
disciplina: son 2.539 puntos de venta donde no se está registrando. Donde sí se registra, la
retirada es el 2,2% de lo cargado (mediana), con un p90 del 15,8%.

**2. El 63% de los puntos de venta visitados no tiene dato de venta.** La mediana de
`totimpvtas` es **cero**: 1.872 de 2.956. Es la otra cara del 12% de audits del informe 33,
ahora medida por punto de venta. Cualquier análisis de venta con estos datos cubre, como
mucho, un tercio del parque.

**3. El efectivo es una parte pequeña del negocio.** En los puntos de venta con venta
registrada, la recaudación es el **9% del importe vendido** (mediana), con un p90 del 48%.
El resto es tarjeta y medios cashless. Y hay **16 puntos de venta donde la recaudación
supera la venta registrada**: o falta venta por registrar, o hay un descuadre. Esa lista,
corta y concreta, es un instrumento de cabina.

**4. Tres tipos de retirada, no uno.** El SQL filtra `RC`, `RM` y `RR`. Hasta ahora solo
conocíamos `RC` (caducidad) por el informe 12; falta saber qué son las otras dos.

### Otros apuntes

- **118 puntos de venta visitados no tienen ruta activa asignada**, en línea con los 196
  sin ruta del informe 29.
- Los totales cuadran con el resto: la recaudación da **exactamente** los mismos
  286.344,78 € que los informes 31 y 33, y las ventas (722.158,92 €) coinciden con el
  informe 35 salvo por los cuatro días de diferencia del rango.
- **El producto cargado mezcla unidades**: 2,47 millones incluye paletinas, vasos y azúcar
  junto a latas y sándwiches, y sin el factor de conversión esa suma no significa gran cosa.
  Para valorar hay que ir por artículo, como en el informe 66.
- El SQL repite cinco veces la misma subconsulta con un `pdvid in (...)` redundante. Funciona,
  pero una sola agregación con cinco columnas haría lo mismo mucho más rápido.

---

## Informe 37 — Comparador de precios: máquina contra audit, por artículo

**Parámetro**: `Código Artículo` (0, **cadena**; es el primero que no es número ni fecha).

Para un artículo dado, recorre todos los canales de máquina donde está asignado
(`recursos.maquinascanales`), se queda con el canal más reciente de cada máquina y pone una
al lado de otra dos cosas:

- **El precio configurado**, calculado con la función `vending.getprecioscanal(...)` en sus
  tres modalidades: `precioef` (efectivo), `preciotp` y `preciotc` (tarjetas).
- **El último precio leído en un audit**, de `vending.partesvisitamaqdetalle`
  (`tic_precioef`, `tic_preciotp`, `tic_preciotc`), tomando solo visitas con `estadolec = 2`
  y lectura no vacía.

Añade `a.puc`, el precio de última compra, así que en la misma fila están el coste y el
precio de venta de cada máquina.

### Para qué sirve

Detecta **máquinas cuyo precio real no coincide con la tarifa**. Es la herramienta que
faltaba para investigar el hallazgo del análisis exploratorio: 121 artículos con precio
distinto según el centro, con casos como PAN AIRBUS de 0,31 € a 2,05 €. Con este informe se
puede ver si eso es tarifa negociada o máquina mal configurada, artículo por artículo.

Y como trae el `puc`, da el margen por máquina sin más cuentas.

### Dos cosas a tener en cuenta

- **Depende de los audits**, y ya sabemos por el informe 33 que solo se capturan en el 12%
  de las visitas. Para muchas máquinas la columna de audit vendrá vacía o con una lectura
  antigua; conviene mirar también la fecha de esa lectura, que el informe no muestra.
- El bloque comentado del SQL revela algo útil sobre la telemetría: lee precios de
  `telemetry.telemetrysales` filtrando `lineaprecio` **2 para efectivo, 1 para tarjeta de
  crédito y 3 para prepago**. Eso explica el `lineaprecio = 1` del informe 9: aquel informe
  solo suma **ventas con tarjeta de crédito**, no toda la venta.

---

## Informe 38 — Resumen de inventario de máquinas según el último inventario en visitas

Sin parámetros. Es el gemelo del informe 20, con una diferencia de fondo: la fecha del
último inventario **no sale de los informes formales de inventario**
(`stocks.infinventarioelementos`) sino de los **inventarios anotados en el parte de visita**
(`vending.partesvisitarecinventarios`). A cambio, no trae valoración.

**Salida**: 3.200 máquinas, las mismas del informe 20.

| | Informe 38 (visitas) | Informe 20 (formal) |
|---|---:|---:|
| Sin inventario nunca | 1.073 (33,5%) | 954 (29,8%) |
| Antigüedad mediana | **397 días** | 485 días |
| Inventariadas en los últimos 30 días | 48 (1,5%) | 18 (0,6%) |
| En el último año | 902 (28,2%) | 828 (25,9%) |

### Son dos registros distintos, y ninguno está completo

Comparando máquina a máquina:

- Coinciden en fecha en **2.694 (84%)**.
- En **219** el inventario de visita es más reciente que el formal; en **20** es al revés.
- **193 máquinas tienen inventario formal pero ninguno en visita**, y **74 al revés**.

Juntando los dos, las máquinas **sin ningún inventario por ninguna vía bajan a 880** (27,5%)
en lugar de las 1.073 o 954 que dice cada informe por separado.

Conclusión para la ingesta: la fecha de último inventario debe ser **la más reciente de las
dos fuentes**, no la de un informe u otro. Y el indicador que importa sigue siendo el mismo
del informe 20: **cuántas máquinas llevan más de X meses sin contar**, que con cualquiera de
las dos medidas es una cifra muy alta.

### Detalle heredado del informe 20

Los dos comparten esta subconsulta para la ruta:

```sql
(select rut.denomina from vending.rutas rut
 left join vending.rutasdetalle rutde on rut.id = rutde.rutaid
 where rutde.pdvid = pdv.id order by tipo asc limit 1) ruta
```

El `limit 1` sobre `order by tipo` devuelve **una ruta cualquiera** cuando el punto de venta
está en varias, y por el informe 29 sabemos que hay 14 en esa situación. Para esos, la ruta
que muestran estos informes no es fiable.

---

## Informe 40 — Máquinas sin canales

Sin parámetros.

Selecciona las máquinas cuyo **modelo es de clase 0, 2 o 9** (fría, caliente, snack), no
obsoleto, y que **no tienen ni una fila en `recursos.maquinascanales`**. A cada una le
adosa la capacidad teórica de su modelo por materia prima, sacada de la plantilla más
reciente (`recursos.maquinasmodelosplantillas`).

**Salida**: **652 máquinas** · 98 modelos.

| Clase | Máquinas | Instaladas en un PDV |
|---|---:|---:|
| Bebida caliente / preparadas | 323 | 113 |
| Bebida fría | 220 | 37 |
| Snack / multiprecio | 109 | 21 |

Las **171 instaladas** son las accionables: están en un punto de venta y no tienen canales
configurados. Las otras 481 están en taller o almacén, donde no tenerlos es normal.

Cuadra con el informe 11: las 652 salen todas como "sin planograma" allí. El 11 cuenta 907
porque no filtra por clase ni por modelo obsoleto.

### El catálogo de materias primas

Los códigos de `tipomateriaprima`, que el informe traduce a columnas:

| | | | |
|---|---|---|---|
| 1 café | 2 azúcar | 3 vaso | 4 paletina |
| 5 leche | 6 soluble | 7 garrafa de agua | 8 cápsula |
| 9 chocolate | 10 infusión | 11 café soluble | 12 café grano |
| 13 toppings | | | |

### Las columnas de capacidad solo valen para las calientes

La CTE que calcula las capacidades filtra `clase = 2`, pero la consulta principal trae
también clases 0 y 9. Resultado: **las 329 máquinas de fría y snack salen con todas las
capacidades vacías**, sin excepción. No es que no tengan capacidad, es que el informe no la
busca para ellas.

De las 323 calientes, 248 traen alguna capacidad; las 75 restantes son modelos sin plantilla
cargada.

### Y para las calientes, "sin canales" probablemente no significa "sin configurar"

Las máquinas de bebida caliente no se configuran por canales sino por **carriles de materia
prima** (`recursos.maquinascarriles`). El propio autor del informe lo tenía en mente: hay un
bloque comentado que iba a comprobar exactamente eso —`select count(id) from
recursos.maquinascarriles where maquinaid = m.id` para marcar "tiene contenedores"— y se
quedó sin terminar.

Así que de las 113 calientes instaladas que el informe señala, buena parte puede estar
perfectamente configurada por carriles. **Conviene terminar ese bloque comentado antes de
usar esta lista como tarea de trabajo**; si no, se manda a alguien a revisar máquinas que
están bien. Para fría y snack, donde el canal sí es la vía, las 58 instaladas sí son
trabajo real.

### Las plantillas tienen errores

Valores imposibles que, al venir de la plantilla del modelo, afectan a todas sus máquinas:

| Materia prima | Valor anómalo | Valores normales |
|---|---:|---|
| infusión | 7.000 | 1 a 3 |
| azúcar | 3.000 | 2 a 4 |
| vaso | 3.000 | 300 a 700 |
| paletina | 2.500 y 3.000 | 300 a 900 |
| cápsula | 1.200 | 6 |
| chocolate | 1.000 | 2 a 3,6 |
| leche | 20 | 2 a 4 |

Y hay 33 máquinas con todas las capacidades a cero.

### Lo que aporta

La **capacidad**, que era una petición pendiente del censo. Con ella, las cargas del informe
66 y la venta, sale la **autonomía**: cuántos días aguanta cada máquina con lo que le cabe.
Es la medida que permite juzgar si una ruta pasa de más o de menos, en vez de discutirlo de
oído. Eso sí, hay que limpiar antes las plantillas y recordar que la capacidad es del
modelo, no de la máquina concreta.

---

## Informe 41 — Listado de coordenadas GPS por dispositivo y fecha

**Parámetros**: `Codigo Dispositivo` (0, numérico), `Desde Fecha` (1) y `Hasta Fecha` (2).

```sql
select fecha::text, coddispositivo, gpslatitud, gpslongitud
from utils.trackinggps
where coddispositivo = {0}
  and (fecha >= '{1}' and fecha <= '{2}')
order by coddispositivo ASC, fecha DESC
```

Cuatro columnas: `fecha`, `coddispositivo`, `gpslatitud`, `gpslongitud`. Son las posiciones
que va dejando el terminal del reponedor, guardadas en `utils.trackinggps`.

**Dos defectos del SQL:**

- El corte superior es `fecha <= '{2}'`, **sin `23:59:59`**. Todos los demás informes lo
  llevan. Aquí eso significa que la fecha "hasta" se interpreta a las 00:00:00 y **el
  último día se pierde entero**.
- Solo devuelve el código de dispositivo. **No hay forma de saber de quién es ese
  terminal**, ni a qué ruta pertenece, así que el informe no se puede cruzar con nada. Le
  falta el enlace con el reponedor o la ruta, que es lo que lo convertiría en información.

**Salida** (dispositivo 3, septiembre de 2026): **43 puntos**.

### La captura es muy parcial

| | |
|---|---|
| Días con dato | **3** (18, 23 y 25 de septiembre) |
| Franja horaria | de 06:22 a 11:00, ninguna tarde |
| Intervalo entre puntos | mediana 5,1 minutos |
| Extensión geográfica | 0,88 km de diagonal |
| Recorrido acumulado | 4,0 km |

Las coordenadas caen todas en el entorno de la Alhambra, en Granada, así que este
dispositivo está asignado a esa ruta. Y con 0,88 km de extensión, **lo que se está
registrando es el movimiento a pie dentro del recinto**, no el desplazamiento entre
clientes.

Tres días de dato en un mes de trabajo significa que, hoy por hoy, **esto no sirve para
analizar rutas**. Es un dispositivo de una ruta concreta y no se puede generalizar al
resto de la flota sin mirar más, pero conviene averiguar si la captura falla en todos los
terminales o solo en este antes de contar con ello para nada.

### Para qué serviría con captura completa

- **Tiempo real en cada punto de venta**, que hoy no se puede medir: sabemos cuándo se
  abre el parte, no cuánto se tarda.
- **Ruta real contra ruta planificada**, que enlaza directamente con el informe 33 y sus
  desviaciones del plan.
- **Prueba de presencia** ante una reclamación de cliente.

### Advertencia

Son **datos de geolocalización de personas trabajadoras**. En un cuadro de mando interno
eso exige base legal, información previa a la plantilla y finalidad acotada; el uso
razonable es agregado —tiempos medios, cobertura de ruta— y no el seguimiento individual.
Conviene decidirlo antes de construir la pantalla, no después.

---

## Informes que conviene encargar

Aprovechando que son consultas SQL a medida:

1. **Ventas con código de artículo, hora y medio de pago.** El campo que desbloquea todo
   lo demás: sin `cod_art` no hay margen, sin hora no hay análisis por franja, sin medio
   de pago no se cuadran las 276 devoluciones. Filtros por rango de fechas y centro.
3. **Dinero acumulado por máquina desde la última recaudación.** El informe 23 ya da qué
   máquinas llevan sin recaudar; lo que falta es cuánto llevan dentro, cruzando la venta en
   efectivo de la telemetría con la fecha de la última recaudación, para avisar al pasar de
   100 € sin esperar al mes.
4. **Maestro de artículos completo**: `cod_art`, denominación, familia, formato, unidades
   por caja o factor de conversión, PVP de tarifa, IVA.
5. **Escandallo de las selecciones de bebida caliente**: qué ingredientes y qué cantidad
   consume cada selección.
6. **Censo de máquinas: resuelto por el informe 10.** Solo falta añadirle el modelo con
   `mod.clase` traducido y la capacidad. El SQL de partida sería este, si se prefiere un
   informe aparte:

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
6. **Planograma por máquina**: canal, artículo asignado y capacidad, que es lo que permite
   distinguir "no había demanda" de "estaba vacío".
