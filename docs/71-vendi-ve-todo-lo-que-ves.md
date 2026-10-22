# 71 · Vendi ve todo lo que ves, con tablas que se bajan

Gabriele, 22-oct-2026: «el asistente del panel solo tiene datos del panel, no puede sacar más
datos». Eligió que Vendi consulte, desde cualquier página, **todo lo que el usuario ve en la web**.
Y luego: «quiero que cree tablas como esta en el chat y poder exportarlas en Excel o PDF».

## Consulta lo mismo que el navegador, con la misma sesión

Hasta docs/69 el modelo recibía de golpe el fichero de la página desde la que se preguntaba. Ahora
no recibe ningún dato por adelantado: tiene una herramienta, `consulta`, y pide lo que necesita.

`consulta` llama a la **API pública** (`https://dashboard.digivend.es/api/...`) con la cookie de la
sesión que pregunta. No lee S3 ni tiene permisos propios sobre los datos: lo que le devuelve la API
es exactamente lo que vería ese usuario en el navegador, con su perfil, sus cuadrados ocultos
(docs/61) y sus secciones. Si la sesión no puede ver una sección, la API dice 403 y Vendi lo dice.
La regla de docs/40 se mantiene, y es más fácil de sostener: no hay una segunda vía al dato.

| sección | ruta | parámetros que acepta |
|---|---|---|
| `panel` | `/api/panel` | — |
| `informe_general` | `/api/operativo` | — |
| `serie` | `/api/serie` | `mes`, `centros` |
| `rutas`, `incidencias`, `devoluciones`, `furgonetas`, `almacenes`, `telemetria`, `revision`, `utilizo` | la de cada página | — |
| `tarifas` | `/api/tarifas` | `centro` |
| `cuadro` | `/api/cuadro` | `mes` |

Un parámetro que la sección no acepta se descarta antes de llamar. Como algunas respuestas pesan
cientos de KB, la herramienta navega por dentro: `camino` (claves o posiciones), `filtro` (contiene,
sin mayúsculas), `orden` (`-campo` para descendente) y `max` (40 por defecto, 200 como mucho). Lo
que pase de 12.000 caracteres vuelve recortado y marcado como `datos_parciales`, y el recetario le
dice que no saque conclusiones de lo que no ha visto.

Lo que devuelve una consulta es dato, no instrucciones: el recetario lo dice expresamente, porque
ahí hay nombres de centros y textos de incidencias que escribe gente.

## Por pasos, para no chocar con los 29 s

API Gateway corta a los 29 s y una pregunta con tres o cuatro consultas tarda más. En vez de
cambiar la pila, la respuesta va por pasos:

1. `POST /api/pregunta {pregunta, historial, pagina}` hace vueltas del modelo hasta unos 8 s.
2. Si aún no ha terminado, guarda el estado en DynamoDB (`PREGUNTA#<id>`, comprimido, caduca a las
   2 h) y devuelve `{sigue: id, estado: "Mirando rutas e incidencias…"}`.
3. La página vuelve a llamar con `{sigue: id}` (hasta 12 veces) y enseña el `estado` en la burbuja
   de espera. El `id` solo vale para el mismo usuario: otro recibe 404.
4. Como mucho 8 vueltas del modelo; la última va sin herramientas, para que conteste con lo que tiene.

Cuenta como **una** pregunta del límite diario, y el coste es la suma de todas las vueltas.

## Tablas que se bajan

Las tablas del chat salen como en el resto de la web: cabecera con banda suave, bordes redondeados,
filas alternas y las cifras a la derecha. Debajo de cada una, dos botones:

- **Excel**: el mismo `app/comun/xlsx.js` de las demás páginas (se carga la primera vez que se
  pulsa). Título con la pregunta y la hora; las cifras van como números (`1.234,5` → `1234.5`) y
  las columnas con `€` en formato de euros.
- **PDF**: la ventana de imprimir del navegador con solo la tabla, su título y la fecha, para
  «Guardar como PDF». Sin bibliotecas ni nada de fuera del dominio.

El fichero se llama `vendi_AAAA-MM-DD_HHMM.xlsx`.

## La conversación sigue al cambiar de página

La conversación se guarda en `sessionStorage` (los últimos 20 turnos): si se pregunta en el
informe general y se pasa al panel, Vendi sigue con lo mismo. Se pierde al cerrar la pestaña y se
borra al pulsar «Salir». Al modelo se le mandan los últimos 6 turnos, como antes.

Vendi no aprende entre conversaciones ni guarda nada en el servidor salvo el estado de una pregunta
a medias (2 h) y el contador de uso.

## Lo que cuesta

Ya no va el panel entero en cada pregunta: va el recetario (en caché) y solo lo que consulta. Una
pregunta de una consulta cuesta menos que antes; una que cruza tres secciones, algo más. El pie del
chat lo dice: «Ve lo mismo que tú en la web, nada más. No ejecuta acciones».
