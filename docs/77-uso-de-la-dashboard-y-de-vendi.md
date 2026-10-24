# 77 · Utilizo: quién usa la dashboard y Vendi, y cuánto gasta

Gabriele, 23-oct-2026: «En el cuadrante utilizo quiero saber quien utiliza la dashboard y cuanto y
también quien utiliza la IA y cuanto gasta».

La página `/utilizo/` lleva ahora tres pestañas: **VenCloud** (lo de siempre, docs/60),
**Dashboard** y **Vendi (IA)**. Cada pestaña pide sus datos la primera vez que se abre. Las tres
tienen la vista de un día o de un mes, el buscador, el detalle de cada persona con su día a día y
su mes a mes, y su Excel.

## Lo que se cuenta

| | qué es |
|---|---|
| **Entrada** | cada vez que alguien entra con su correo y su clave (`/api/acceso` o el primer cambio de clave) |
| **Página vista** | cada página de la dashboard que se abre. Cada página pide `/api/yo` una vez al abrirse, y el navegador dice desde cuál en el `Referer` |
| **Primera · última** | la hora (de España) del primer y del último movimiento del día |
| **Pregunta** | cada mensaje que se le escribe a Vendi, o al muñeco que lleve cada uno (docs/76) |
| **Gasto** | lo que cobra Anthropic por esa pregunta en la API de Claude, en dólares, con los tokens de cada vuelta |

No cuentan como página vista la portada de entrada (`/`), las consultas que hace Vendi por dentro
(van con su user-agent, `digivend-asistente`) ni el `/api/yo` que pide el botón del asistente en
cada página (lleva la cabecera `x-digivend-vista: no`): si contaran, cada página sumaría dos. Una
ruta que no es de la lista de páginas cuenta como «otra», para que un `Referer` raro no llene la
fila de claves inventadas.

Lo que **no** se puede medir es el tiempo que alguien pasa mirando una página, y la página no lo
estima. La sesión dura 12 horas, así que se pueden ver páginas sin volver a entrar: un día con
vistas y cero entradas es normal.

## Desde cuándo

- **La dashboard**, desde que se subió este cambio. Antes no se apuntaba nada (sólo los errores),
  así que de antes no hay datos y la página lo dice: «Se cuenta desde el…».
- **Vendi**, desde el 22-oct-2026, cuando empezó a apuntar su contador de preguntas.

## Dónde vive

En DynamoDB, una fila por persona y día:

- `ACCESO#<correo>`, sk = el día **en España**, con `{entradas, vistas, paginas: {pagina: n},
  primera, ultima}`. La escribe la Lambda de la API.
- `USO#<correo>`, sk = el día **en UTC**, con `{preguntas, gasto_usd}`. La escribe la del
  asistente: es el mismo contador del límite de preguntas por día, por eso va en UTC.

Las dos duran 800 días, como el resto de históricos. Las filas `USO#` duraban 40: las que ya
había las alarga a 800 desde su día la API, la primera vez que alguien abre la pestaña Vendi
(es la única Lambda que las lee todas, y Claude no tiene acceso directo a DynamoDB). Si apuntar el uso falla, se calla: contarlo nunca
tumba la petición que lo cuenta.

## Quién lo ve

`GET /api/utilizo/plataforma` lo sirve sólo a quien ve el cuadrado Utilizo (dirección y
administración, en un perfil sin ámbito: la misma regla de docs/60). Devuelve los últimos 400
días de todas las personas, con su nombre y su perfil. Es lo que hace la gente, no un dato de
cliente, así que no se recorta por ámbito: quien no ve Utilizo no ve nada.

Se prueba con `python3 infra/api/test_api.py` (lo que cuenta y lo que no, los permisos) y en
Chromium con `node app/comun/prueba_pantallas.js`.
