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
  con más averías técnicas y con más devoluciones. Pulsar una delegación o un centro filtra por él.
- **Incidencias abiertas.** Seis tarjetas que se pulsan (técnicas, reposición, caducados,
  emergencia sanitaria, fuera de servicio y máquinas críticas), la lista ordenada por prioridad y
  la ficha de la incidencia que se pulsa, con sus notas. La lista se baja en CSV.

## Las cuentas

Como en el Power BI, una incidencia es de un periodo por el día en que **entró**. Los periodos
acaban ayer. El anterior de «mes corriente» es el mismo trozo del mes de antes; el de «últimos 3
meses» y «último año», los tres meses o el año de antes; el de un intervalo, los mismos días justo
antes. Si los datos no llegan al periodo anterior, se dice en vez de comparar.

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
| Devoluciones | los códigos de devolución del catálogo (D01, D03, DEV01…) o «DEVOLUC» en la operación |

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
las abiertas, y nunca en las devoluciones: es el cliente pidiendo su dinero y alguna nota trae sus
datos.

Se sirve por `/api/incidencias` tal cual está comprimido, sin abrirlo: con un año del perfil interno
pasaría del límite de respuesta de una Lambda. La misma regla que el cuadrado: perfil de
operaciones o más que vea el cuadrado de Incidencias.

Pruebas: `infra/test_incidencias.py` (marcas, zonas, horas, con y sin M13), `infra/test_agregados.py`
(el ámbito y el cuadrado con los cierres tardíos), `infra/api/test_api.py` (quién la ve) y
`app/comun/prueba_pantallas.js` (la página en Chromium, sin peticiones fuera del dominio).
