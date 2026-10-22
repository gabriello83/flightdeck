# 56 · La página de incidencias

Es lo que abre el cuadrado de **Incidencias** del informe general (docs/51), que hasta el 16 de
octubre de 2026 se llamaba Averías. Gabriele lo pidió ese día con un Power BI suyo como modelo
(«Control operativo Incidencias 2»):

> Cuando le das al boton averias o incidencia (Cambia el nombre a Incidencia) entres en una pagina
> que tenga un formato como este power BI

`/incidencias/` tiene las dos hojas del Power BI, con los mismos filtros: periodo (último año,
últimos 3 meses, último mes, mes corriente o un intervalo), estado, zona, delegación y centro.

- **Panel de control.** Total de incidencias, tasa de resolución, tiempo de resolución y SLA de 24
  horas, cada uno contra el periodo anterior; el total por zona y delegación; y los diez centros
  con más averías técnicas. Pulsar una delegación o un centro filtra por él. Las devoluciones de
  dinero no entran en ninguna cuenta (Gabriele, 16-oct-2026): el Power BI las tenía como un
  gráfico aparte, y aquí se quitan del estudio entero.
- **Incidencias abiertas.** Seis tarjetas que se pulsan (técnicas, reposición, caducados,
  emergencia sanitaria, fuera de servicio y máquinas críticas), la lista ordenada por prioridad y
  la ficha de la incidencia que se pulsa, con sus notas. La lista se baja en CSV.

## Por áreas y en las últimas 24 horas

El 20 de octubre de 2026 Gabriele pidió que Incidencias se recorra como Rutas (docs/67):

> Averias lo mismo que ruta, entras y te da los cuadrantes separados por area y una vez entrado te
> da todas las informaciones cn mas detalle, separado con area con el percentaje de las llamadas
> pero en las ultimas 24 horas.

- **La portada** son las últimas 24 horas: cuatro cifras nacionales (llamadas, cuántas siguen
  abiertas, cerradas en menos de 24 horas y abiertas ahora) y un cuadrante por área. El número
  grande de cada cuadrante es **la parte de las llamadas** de esas 24 horas que es suya; el borde
  lleva el semáforo del cuadrado (técnicas cerradas ese día en menos de 24 horas). Debajo, las
  llamadas por área y delegación con su porcentaje, y la lista de las llamadas de esas 24 horas.
- **Un área**: lo mismo de esa área (su porcentaje sobre todas las áreas, y el de cada delegación
  sobre el área) y, debajo, todo el detalle de antes (panel de control e incidencias abiertas) ya
  filtrado por el área. Pulsar una delegación filtra todo por ella.
- «Ver el detalle de todas las áreas juntas» es la página de antes, con el filtro de zona
  (`?area=todas`). Un perfil de una sola área no tiene portada: entra directamente.

**Las 24 horas son un día entero, de 0 a 24 h.** La foto de M13 se saca de noche y llega hasta el
final de ayer: las últimas 24 horas con dato son las de ayer. Se puede elegir otro día de los
últimos 31. Desde el cuadrado (`?dia=`) se abre en ese día. **Llamada** = incidencia que entró
ese día, de cualquier tipo (sin devoluciones ni preventivos, como todo lo demás). No cambia el
fichero: la página cuenta con lo que ya trae `incidencias.json.gz`.

Con los datos del 19 de octubre, perfil interno: 68 llamadas; Centro 39,7 %, Cataluña 27,9 %, Sur
17,6 %, Levante 13,2 % y Norte 1,5 %.

## Las cuentas

Como en el Power BI, una incidencia es de un periodo por el día en que **entró**. Los periodos
acaban ayer. El anterior de «mes corriente» es el mismo trozo del mes de antes; el de «últimos 3
meses» y «último año», los tres meses o el año de antes; el de un intervalo, los mismos días justo
antes. Si los datos no llegan al periodo anterior, se dice en vez de comparar.

El periodo **«Cerradas un día»** cuenta otra cosa, la del cuadrado: las averías técnicas que se
**cerraron** ese día, por su fecha de cierre, y cuántas en menos de 24 horas. Es donde se abre la
página desde el cuadrado de Incidencias (`/incidencias/?dia=AAAA-MM-DD`), para que la cifra de la
página sea la del cuadrado (Gabriele, 16-oct-2026: el cuadrado decía 75,5 % y la página abría en
el último año con 57,4 %). Se compara con el día anterior. La tasa de resolución no aplica, porque
todas están cerradas, y el filtro de estado se apaga. Lo único que puede separar la página del
cuadrado es una tarea abierta hace más de 120 días: el cuadrado no la mide (`sin_tarea`) y la
página sí.

| Medida | Cuenta |
|---|---|
| Total | tareas de la SAT, sin la matrícula ficticia (`00SE0000`) ni los preventivos (docs/50) |
| Tasa de resolución | cerradas sobre el total |
| Tiempo de resolución | **mediana** de horas entre apertura y cierre; la media va debajo. El Power BI enseña la media, pero aquí siempre se da la mediana primero: hay tareas de 200 días que la estiran (`reglas.resumen_tiempos`) |
| SLA 24 h | cerradas en menos de 24 horas sobre las cerradas con hora, con el semáforo del cuadrado (verde > 95 %, rojo < 75 %) |

Las marcas de cada incidencia (`infra/incidencias.py`):

| Tarjeta | Cuándo |
|---|---|
| Técnicas | fallo técnico **por la operación** (`reglas.es_fallo_tecnico`), sin solicitudes especiales. El Power BI mira la categoría más siete operaciones de atención al cliente; aquí se usa la regla del resto de la plataforma (docs/41) |
| Reposición | la operación dice «Reponer» (S010) |
| Caducados | operación de producto caducado, o «caduc» en el título o la última nota |
| Emergencia sanitaria | operación de insectos, o insecto, bicho, hormiga, cucaracha, hongos o moho en el texto |
| Fuera de servicio | técnica con una de las operaciones bloqueantes del Power BI. Se buscan por un trozo del nombre, porque VenCloud les pone delante el tipo de máquina |
| Máquinas críticas | tres o más averías técnicas entradas en los últimos 30 días, abiertas o cerradas |
| Devoluciones (fuera) | los códigos de devolución del catálogo (D01, D03, DEV01…) o «DEVOLUC» en la operación. No se escriben en el fichero |

La zona sale del nombre de la delegación: Madrid es Centro, Andalucía es Sur, y Cataluña, Levante y
Norte son ellas mismas. La central es «Otra zona».

La prioridad de la lista es la del Power BI: días abierta (hasta 1, hasta 3, más de 3), si deja la
máquina sin vender, si el centro es del cliente 10002 (Serunion) y si la máquina es crítica.

## Por qué hace falta M13

D7 (tareas) y D8 (eventos) se bajan por la fecha de alta de la tarea, y la extracción solo vuelve
a bajar los tres últimos días. Una tarea que se cierra al cuarto día se queda abierta para siempre
en el crudo. Con eso se sabe cuántas entran, por dónde y de qué tipo, pero no cuántas hay abiertas
ni cuánto se tarda en cerrarlas.

**M13 · EXT_SAT_INCIDENCIAS** (docs/17) es la foto de cada noche: las tareas de los últimos 400
días y todas las que siguen sin cerrar, con su estado de hoy y la hora de apertura y de cierre del
registro de eventos. Mientras no exista, la página dice que falta y enseña solo lo que no depende
del estado: el total, las zonas, los diez centros y las máquinas críticas.

Lo mismo le pasaba al cuadrado: solo veía los cierres de los tres primeros días de cada tarea. Con
M13, los agregados le pasan también sus aperturas y cierres (`escribe_incidencias`), y el cuadrado
cuenta las que se cierran tarde.

## El fichero

`cabina/<perfil>/incidencias.json.gz` lo escriben los agregados cada noche, con el ámbito del perfil
aplicado al escribir. Una fila por incidencia, con los centros, delegaciones, operaciones y técnicos
en listas aparte. El texto (título y última nota), la ubicación y el punto de venta solo viajan en
las abiertas. Las devoluciones no van: ni se cuentan ni se escriben (y sus notas traían datos del
cliente).

Se sirve por `/api/incidencias` tal cual está comprimido, sin abrirlo: con un año del perfil interno
pasaría del límite de respuesta de una Lambda. La misma regla que el cuadrado: perfil de
operaciones o más que vea el cuadrado de Incidencias.

Pruebas: `infra/test_incidencias.py` (marcas, zonas, horas, con y sin M13), `infra/test_agregados.py`
(el ámbito y el cuadrado con los cierres tardíos), `infra/api/test_api.py` (quién la ve) y
`app/comun/prueba_pantallas.js` (la página en Chromium, sin peticiones fuera del dominio).
