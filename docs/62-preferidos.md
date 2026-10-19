# 62 · Preferidos

Lo pidió Gabriele el 19 de octubre de 2026: que cada tabla o gráfico tenga una estrella que, al
pulsarla, se pone amarilla, como la de favoritos de Chrome; y que todo lo marcado salga en un
cuadrado nuevo, **Preferidos**, donde el usuario ve sólo lo suyo y lo ordena y dimensiona a su gusto.

## Lo que ve el usuario

- **La estrella.** Junto al título de cada tabla y gráfico de las páginas de los cuadrados: rutas,
  incidencias, devoluciones, furgonetas, revisión clientes, almacenes, telemetría, tarifas y
  utilizo. Gris si no está marcada, amarilla si lo está. En las páginas con pestañas (furgonetas,
  revisión) la estrella es la de la pestaña que se ve.
- **El cuadrado Preferidos**, el primero del informe general: cuántas tablas tiene marcadas, y
  lleva a `/preferidos/`.
- **La página `/preferidos/`.** Un recuadro por tabla, en el orden que él elija:
  - se mueve **arrastrando por el asa** ⠿, o con las flechas ← → (también con teclado);
  - **ancho**: media fila o fila entera;
  - **alto**: bajo (340 px, con su propia barra), medio (540 px) o entero (lo que mida la tabla);
  - **Abrir** lleva a su página entera, y la estrella del recuadro lo quita de preferidos.

Todo se guarda solo, en el servidor: lo encuentra igual desde otro ordenador.

## Cómo está hecho

**Cada recuadro es la propia página del cuadrado en su «vista suelta»** (`/rutas/?solo=maquinas`):
sin cabecera, sin pie y sin las demás tablas, sólo sus filtros y esa tabla. Así la tabla se dibuja
con el código de su página, con sus filtros, y no con una copia que se quedaría vieja el día que
cambie la página. Lo hace `app/comun/preferidos.js`, que cada página carga:

- `data-estrella="<tabla>"` dice dónde va la estrella (`*` = la pestaña que se ve);
- `data-tabla="<tabla>"` es la caja de la tabla, la que se queda en la vista suelta;
- `Preferidos.monta(cuadrado, {actual, abre, ocultar})`, al final de la carga de la página.

Las estrellas se vuelven a poner solas cuando la página repinta (un `MutationObserver`).

**Los permisos no cambian.** Cada recuadro pide sus datos a la API como su página, con la sesión
del usuario: ve lo mismo que allí. `/api/preferidos` sólo guarda y devuelve tablas que existen
y que el usuario ve hoy (`autorizacion.preferidos_validos`): si el administrador le quita un
cuadrado o una tabla (docs/61), deja de salirle en preferidos, y vuelve si se la devuelve.

| | |
|---|---|
| `GET /api/preferidos` | `{"preferidos": [{c, t, ancho, alto}], "nombres": {cuadrado: {nombre, tablas}}}` |
| `PUT /api/preferidos` | `{"preferidos": [...]}`; guarda en `PREF#<correo>`, `PREFERIDOS`. Hasta 40 |

## La cabecera de CloudFront

Hasta ahora ninguna página se podía meter en un recuadro (`frame-ancestors 'none'`,
`X-Frame-Options: DENY`). Pasa a `frame-ancestors 'self'` y `SAMEORIGIN`: las páginas de
`dashboard.digivend.es` se pueden incrustar **en el propio dominio** y en ninguna otra web. Es un
cambio de la pila `digivend-web` (`infra/plantilla-web.yaml`, recurso `Cabeceras`, y sólo ese):
sin él, los recuadros salen en blanco.

## Lo que no entra

El panel antiguo (`/panel/`) y el cuadro de mando de los clientes no llevan estrella: el
cuadrado Preferidos es del informe operativo. Puntos de venta, Ventas y Reposiciones llevan al
panel, así que tampoco.
