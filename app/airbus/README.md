# Panel de cliente AIRBUS

`index.html` · 28 KB · dieciséis paneles · sin una sola llamada fuera del dominio.

## Sin dominios externos

Requisito de red de AIRBUS: hay redes corporativas que bloquean las aplicaciones que llaman
fuera de su dominio. Así que:

- **Tipografía del sistema**, no Google Fonts.
- **Gráficos en SVG escritos a mano**, sin ninguna librería ni CDN.
- **Los datos salen de `datos/airbus.json`**, del mismo origen.
- **El icono va embebido** como `data:` URI.
- Y la página **lo impone ella misma** con una política CSP en la cabecera:
  `default-src 'self'`.

La única referencia a un dominio externo que queda en el fichero es
`http://www.w3.org/2000/svg`, que es el espacio de nombres de SVG: **no es una descarga**, es un
identificador. Ningún navegador va a buscarlo.

**Pendiente del servidor**: `frame-ancestors 'none'` no vale en un `<meta>`, tiene que ir como
cabecera HTTP en CloudFront. Igual que `Strict-Transport-Security` y `X-Content-Type-Options`.

## Los paneles se reordenan

El cliente los coloca como quiera: arrastrando por el asa, o con las flechas de cada cabecera
—que es lo que funciona en táctil y con teclado—. El orden se guarda por navegador.

Cuando esté el backend, ese orden pasa a guardarse **contra el usuario**, no contra el navegador,
y le sigue entre dispositivos. Es un `PUT /api/preferencias` de una lista de identificadores de
panel; el resto del código no cambia.

Un panel nuevo que se añada más adelante aparece al final del orden guardado en vez de romperlo.

## Qué se enseña y qué no

Dieciséis paneles: evolución diaria, venta por centro, patrón semanal, mix de artículos,
concentración del surtido, rendimiento por máquina, máquinas de menor rendimiento, máquinas sin
venta, incidencias por categoría y por operación, máquinas reincidentes, incidencias por modelo,
visitas por ruta, retorno por visita, preventivos y estado del servicio.

**No se enseña** recaudación, stock ni merma: son internas.

Y hay dos cosas heredadas del cuadro de David que se mantienen a propósito:

- **El umbral de 350 €/mes**, que es una regla de negocio de AIRBUS.
- **Los preventivos como panel propio** — en nuestro modelo salen del D7 con `tipo_tarea = 'E'`.

## Colores

Paleta validada con el script de la guía de visualización, en claro y en oscuro:
azul `#2a78d6`/`#3987e5`, naranja `#eb6834`/`#d95926`, aqua `#1baf7a`/`#199e70`.
Pasan las cinco comprobaciones; el aqua en claro queda por debajo de 3:1 contra el fondo, así que
**lleva siempre etiqueta de valor visible**, que es la compensación que exige la regla.

Los colores de estado (verde, ámbar, rojo) van siempre con texto —«alta», «baja», «revisar»—,
nunca solos.

## El perfil

`perfil-airbus.json` es la ficha que crea el administrador: ámbito —cliente AIRBUS, nueve
centros—, sesiones activas, paneles visibles, el umbral de 350 € y los permisos. El cliente puede
ver, reordenar, exportar y preguntar al asistente; **no** puede enviar WhatsApp ni abrir
incidencias, que son de operaciones.

## Datos

`datos/airbus.json`, del 01/05 al 31/08 de 2026: 778.370,65 € de venta, 1.124.774 unidades,
547 máquinas, 370 referencias, 16.017 visitas y 785 incidencias.

Cuando entre el pipeline, ese fichero lo regenera la carga nocturna y la página no cambia.
