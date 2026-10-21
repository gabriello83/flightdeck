# 67 · Las rutas por áreas

El 19 de octubre de 2026 Gabriele pidió rehacer la página de Rutas (docs/55):

> En el cuadrante RUTAS cuando entro quiero ver las estadísticas nacionales pero con usuario
> nacional quiero ver los cuadrantes de cada área con su porcentaje y luego poder entrar en cada
> ÁREA, poder filtrar por delegación. Quiero ver de cada ÁREA las rutas. De cada ruta quién ha
> hecho la ruta, cuántas máquinas tenía en ruta, cuántas máquinas que tenía programadas no ha
> hecho y cuántas máquinas ha hecho fuera de ruta. Cuántos pasajes vacíos de las máquinas que ha
> hecho. Del ÁREA cuántas llamadas de máquina vacía se han detectado y de qué máquina son. Las
> máquinas que faltan a recaudar en el mes. Si pulsa, listado de las máquinas. Las máquinas que no
> se han repuesto más de 12 días laborales. Si pulsas, las máquinas y cálculo del dinero posible a
> recaudar según promedio de recaudación de las máquinas en los meses anteriores.

## Cómo se recorre

- **La portada** es lo nacional: los seis indicadores del Power BI de visitas pendientes y el mapa
  de España partido en las áreas (las cinco del Power BI, como Incidencias y Furgonetas: Centro,
  Sur, Cataluña, Levante, Norte), en relieve y cada una de su color. Cada área lleva solo su
  cumplimiento de ruta; el resto (en ruta, pendientes) sale al pasar el ratón. Pulsar un área entra
  en ella. CENTRAL cae en «Otra zona», que no tiene sitio en el mapa y va en una placa aparte en el
  mar. Un área que el perfil no ve se queda en gris, sin cifra y sin pulsar. Debajo, la tabla por
  delegación (con su área) y los festivos.
  Las comunidades de cada área: Norte = Galicia, Asturias, Cantabria, País Vasco, Navarra, La Rioja
  y Castilla y León; Centro = Madrid, Castilla-La Mancha, Extremadura y Aragón; Cataluña; Levante =
  Comunidad Valenciana, Murcia y Baleares; Sur = Andalucía. Los trazos van dentro de la página
  (sin bibliotecas ni ficheros de fuera) y salen de `scripts/mapa_areas.py`.
- **Un área**: filtros de delegación y ruta, sus seis indicadores, tres cifras que se pulsan para
  ver su listado (llamadas, por recaudar, sin reponer), las rutas, el donut y la lista máquina a
  máquina. Pulsar una delegación en la portada entra en su área ya filtrada.
- **Un perfil de una sola área** (un usuario con sus delegaciones, docs/65) no tiene portada: entra
  directamente.
- **Periodo**: un día, los siete días hasta él o el mes hasta él. Las cifras se suman día a día:
  en un periodo de varios días son visitas, no máquinas distintas. La lista máquina a máquina solo
  se guarda de la última semana, y la página dice cuántos días del periodo la traen.

## De cada ruta

| Columna | Qué es |
|---|---|
| Quién la hizo | los reponedores con parte de visita real en esa ruta (la ruta del parte) |
| En ruta | las máquinas del plan (D12, informe 184) |
| Hechas / No hechas | del plan, con parte o sin él |
| Fuera de ruta | con parte de esa ruta y fuera del plan |
| Pasaje vacío | visitas sin ninguna línea de reposición (docs/55) |

## Las tres listas de máquinas

Salen de `infra/rutas.py`, que mira la **ventana entera** de los agregados (120 días) y no solo
los siete días del informe general. Son de los puntos de venta activos del censo, con el mismo
filtro que el cuadrado de puntos de venta.

**Llamadas de máquina vacía** = tareas de la SAT con la operación S010 «Reponer distribuidor
automático» o C016 «Selecciones vacías», por su apertura y dentro del periodo, juntas por máquina.
Salen de la foto de M13 (con abierta o cerrada); sin M13, de las tareas de la ventana y sin
estado. Si «detectadas» quería decir alarmas de la telemetría, eso VenCloud no lo trae hoy.

**Por recaudar en el mes** = se recaudó en alguno de los tres meses completos anteriores y en el
mes en curso todavía no. Recaudada es un parte de reponedor con la marca `recaudacion` (informe
105) o un acto de recaudar de la recaudación oficial (informe 132, criterio 3). Hace falta la
marca del parte porque la oficial llega a tandas, cuando se cuentan las bolsas: en octubre de 2026
llegaron el 1, 2, 4, 5, 14 y 16, nada los demás días.

**El dinero** = el efectivo oficial (`imp_recaudado`, criterios 2, 3 y 4, por `anho`/`mes`) de
esos tres meses entre tres. Un mes sin recaudar cuenta como cero: es lo que esa máquina da al mes.
Una máquina sin recaudación oficial en esos meses sale «sin dato», no con un cero.

**Sin reponer** = la última línea de carga (A2, tipo CM) de su matrícula fue hace más de 12 días
laborables, contados hasta ayer: de lunes a viernes y sin los festivos de su delegación
(`config/festivos.json`). Aparte, las activas sin una sola carga en la ventana: muchas no se
reponen (fuentes de agua, café de oficina), pero una de snack aquí es una máquina olvidada.

Con los datos del 18 de octubre de 2026, perfil interno: 2.670 máquinas recaudan; 2.030 ya se
recaudaron en octubre y faltan 640, unos 52.900 € al mes según julio, agosto y septiembre. 205
llevan más de 12 laborables sin carga y 238 activas no tienen ninguna en 120 días (74 de café, 47
fuentes de agua). 294 llamadas de máquina vacía desde el 18 de agosto.

## El fichero

Lo mismo de `cabina/<perfil>/rutas.json.gz` (docs/55) con estas claves más, que escribe
`rutas.Maquinas.bloque` cada noche con el ámbito del perfil:

- `zonas`: el área de cada delegación;
- `quien`: por día, los reponedores de cada «delegación␁ruta»;
- `control_maquinas`: el mes, los tres meses del promedio, cuántas recaudan y cuántas ya, y los
  avisos si falta algún informe (`sin_partes`, `sin_lineas`, `sin_oficial`);
- `por_recaudar`, `sin_reponer`, `nunca_repuestas` y `llamadas`: las listas, cada una en la raíz
  para que se quite entera si al usuario le quitan su tabla (docs/61: `recaudar`, `reponer`,
  `llamadas`).

Unos 220 KB comprimidos para el perfil interno (antes, 170 KB).

Un fichero escrito antes de esta noche no trae las listas: la página lo dice en vez de enseñar
ceros.

Pruebas: `infra/test_rutas.py` (las cuentas), `infra/test_agregados.py` (el ámbito),
`infra/api/test_autorizacion.py` (las tablas quitadas) y `app/comun/prueba_pantallas.js` (la
página en Chromium, claro, oscuro y móvil, sin peticiones fuera del dominio).
